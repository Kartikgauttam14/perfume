import hashlib
import hmac
import json
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.whatsapp import router, settings, store_events


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "test-verify")
    monkeypatch.setattr(settings, "META_APP_SECRET", "test-secret")
    monkeypatch.setattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "123")
    monkeypatch.setattr(settings, "WHATSAPP_INBOX_PATH", tmp_path / "inbox.db")
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_challenge_and_rejection(client):
    params = {"hub.mode": "subscribe", "hub.verify_token": "test-verify", "hub.challenge": "987"}
    response = client.get("/api/whatsapp/webhook", params=params)
    assert response.status_code == 200 and response.text == "987"
    params["hub.verify_token"] = "wrong"
    assert client.get("/api/whatsapp/webhook", params=params).status_code == 403


def test_authenticated_delivery_deduplication_and_status(client):
    payload = {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": {
        "metadata": {"phone_number_id": "123"},
        "messages": [{"id": "m1", "type": "text", "text": {"body": "Hello"}}],
        "statuses": [{"id": "s1", "status": "delivered", "timestamp": "1"}],
    }}]}]}
    raw = json.dumps(payload).encode()
    headers = {"x-hub-signature-256": "sha256=" + hmac.new(b"test-secret", raw, hashlib.sha256).hexdigest()}
    for _ in range(2):
        assert client.post("/api/whatsapp/webhook", content=raw, headers=headers).status_code == 200
    with sqlite3.connect(settings.WHATSAPP_INBOX_PATH) as db:
        assert db.execute("SELECT COUNT(*) FROM whatsapp_events").fetchone()[0] == 2
    assert client.post("/api/whatsapp/webhook", content=raw).status_code == 401


def test_unconfigured_and_malformed(client, monkeypatch):
    raw = b"not json"
    signature = "sha256=" + hmac.new(b"test-secret", raw, hashlib.sha256).hexdigest()
    assert client.post("/api/whatsapp/webhook", content=raw,
                       headers={"x-hub-signature-256": signature}).status_code == 400
    monkeypatch.setattr(settings, "META_APP_SECRET", "")
    assert client.post("/api/whatsapp/webhook", content=b"{}").status_code == 503


def test_other_phone_is_ignored(tmp_path):
    path = tmp_path / "inbox.db"
    store_events({"entry": [{"changes": [{"value": {
        "metadata": {"phone_number_id": "other"}, "messages": [{"id": "m1"}]
    }}]}]}, path, "123")
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM whatsapp_events").fetchone()[0] == 0
