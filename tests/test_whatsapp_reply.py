import asyncio
import sqlite3
import time

import httpx
import pytest

from src.whatsapp import store_events
from src.whatsapp_reply import claim_message, send_next, template_payload, settings


@pytest.fixture
def configured(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_INBOX_PATH", tmp_path / "inbox.db")
    monkeypatch.setattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "123")
    monkeypatch.setattr(settings, "WHATSAPP_ACCESS_TOKEN", "test-only-token")
    monkeypatch.setattr(settings, "WHATSAPP_TEMPLATE_IMAGE_URL", "https://example.com/product.jpg")
    monkeypatch.setattr(settings, "WHATSAPP_TEMPLATE_IMAGE_ID", "")


def queue_message(message_id="m1", timestamp=None, kind="text"):
    event = {"id": message_id, "from": "10000000000", "type": kind,
             "timestamp": str(timestamp or int(time.time()))}
    payload = {"entry": [{"changes": [{"value": {
        "metadata": {"phone_number_id": "123"}, "messages": [event],
        "statuses": [{"id": "status1", "status": "delivered", "timestamp": "1"}]
    }}]}]}
    store_events(payload, settings.WHATSAPP_INBOX_PATH, "123")


def test_payload_header_and_missing_image(configured, monkeypatch):
    template = template_payload("10000000000")["template"]
    assert template["name"] == "shop_now" and template["language"]["code"] == "en"
    assert template["components"][0]["parameters"][0]["image"] == {"link": "https://example.com/product.jpg"}
    monkeypatch.setattr(settings, "WHATSAPP_TEMPLATE_IMAGE_URL", "")
    with pytest.raises(ValueError):
        template_payload("10000000000")


def test_duplicate_webhook_sends_once_and_ignores_status(configured):
    queue_message()
    queue_message()
    sent = []
    def handler(request):
        sent.append(request)
        return httpx.Response(200, json={"messages": [{"id": "out1"}]})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            assert await send_next(client)
            assert not await send_next(client)
    asyncio.run(run())
    assert len(sent) == 1
    assert sent[0].url.path.endswith("/123/messages")
    with sqlite3.connect(settings.WHATSAPP_INBOX_PATH) as db:
        assert db.execute("SELECT processed FROM whatsapp_events WHERE kind='messages'").fetchone()[0] == 1


def test_old_messages_and_reactions_are_skipped(configured):
    queue_message(timestamp=int(time.time()) - 86401)
    queue_message("m2", kind="reaction")
    assert claim_message() is None
    assert claim_message() is None


@pytest.mark.parametrize("mode", ["rejected", "timeout"])
def test_failure_is_not_automatically_repeated(configured, mode):
    queue_message(kind="image")
    def handler(request):
        if mode == "timeout":
            raise httpx.ReadTimeout("ambiguous delivery", request=request)
        return httpx.Response(400)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            assert await send_next(client)
            assert not await send_next(client)
    asyncio.run(run())
    with sqlite3.connect(settings.WHATSAPP_INBOX_PATH) as db:
        assert db.execute("SELECT processed FROM whatsapp_events WHERE kind='messages'").fetchone()[0] == -1
