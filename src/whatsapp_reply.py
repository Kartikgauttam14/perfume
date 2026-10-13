"""Single-worker template replies from the authenticated WhatsApp inbox."""

import asyncio
import json
import logging
import sqlite3
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from src.config import settings

logger = logging.getLogger(__name__)


def template_payload(recipient: str) -> dict:
    """The approved shop_now template has an image header and no body variables."""
    image = ({"id": settings.WHATSAPP_TEMPLATE_IMAGE_ID}
             if settings.WHATSAPP_TEMPLATE_IMAGE_ID
             else {"link": settings.WHATSAPP_TEMPLATE_IMAGE_URL})
    if not image.get("id") and not image.get("link", "").startswith("https://"):
        raise ValueError("Set a WhatsApp image media ID or public HTTPS image URL")
    return {
        "messaging_product": "whatsapp", "to": recipient, "type": "template",
        "template": {
            "name": settings.WHATSAPP_TEMPLATE_NAME,
            "language": {"code": settings.WHATSAPP_TEMPLATE_LANGUAGE},
            "components": [{"type": "header", "parameters": [{"type": "image", "image": image}]}],
        },
    }


def claim_message() -> tuple[str, dict] | None:
    """Claim atomically before sending; uncertain sends are never retried blindly."""
    if not settings.WHATSAPP_INBOX_PATH.exists():
        return None
    with sqlite3.connect(settings.WHATSAPP_INBOX_PATH, timeout=10) as db:
        db.execute("BEGIN IMMEDIATE")
        table = db.execute("SELECT name FROM sqlite_master WHERE name='whatsapp_events'").fetchone()
        if not table:
            return None
        row = db.execute("SELECT event_key,payload FROM whatsapp_events "
                         "WHERE kind='messages' AND processed=0 ORDER BY rowid LIMIT 1").fetchone()
        if not row:
            return None
        event = json.loads(row[1])
        try:
            age = time.time() - int(event.get("timestamp", 0))
        except (TypeError, ValueError):
            age = float("inf")
        eligible = (0 <= age < 86400 and event.get("from")
                    and event.get("type") not in ("reaction", "system", "unsupported")
                    and not event.get("errors"))
        db.execute("UPDATE whatsapp_events SET processed=? WHERE event_key=?",
                   (2 if eligible else 3, row[0]))
        return (row[0], event) if eligible else None


def finish_message(key: str, state: int) -> None:
    with sqlite3.connect(settings.WHATSAPP_INBOX_PATH, timeout=10) as db:
        db.execute("UPDATE whatsapp_events SET processed=? WHERE event_key=?", (state, key))


async def send_next(client: httpx.AsyncClient) -> bool:
    claimed = await run_in_threadpool(claim_message)
    if claimed is None:
        return False
    key, event = claimed
    url = (f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
           f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages")
    try:
        response = await client.post(
            url, headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
            json=template_payload(event["from"]),
        )
        # Do not log response bodies, tokens, phone numbers, or message content.
        if response.is_success:
            await run_in_threadpool(finish_message, key, 1)
            logger.info("WhatsApp template accepted by Meta")
        else:
            await run_in_threadpool(finish_message, key, -1)
            logger.error("WhatsApp template rejected: HTTP %s", response.status_code)
    except (httpx.HTTPError, ValueError):
        await run_in_threadpool(finish_message, key, -1)
        logger.error("WhatsApp template send failed; review before retrying")
    return True


async def reply_worker() -> None:
    async with httpx.AsyncClient(timeout=20) as client:
        while True:
            try:
                sent = await send_next(client)
            except Exception:
                logger.error("WhatsApp inbox worker failed; check storage configuration")
                sent = False
            await asyncio.sleep(0.2 if sent else 2)


@asynccontextmanager
async def whatsapp_lifespan(app: FastAPI) -> AsyncIterator[None]:
    task = None
    if settings.WHATSAPP_AUTO_REPLY_ENABLED:
        if not all((settings.WHATSAPP_ACCESS_TOKEN, settings.META_APP_SECRET,
                    settings.WHATSAPP_VERIFY_TOKEN, settings.WHATSAPP_PHONE_NUMBER_ID)):
            raise RuntimeError("WhatsApp auto replies require credentials and webhook configuration")
        template_payload("configuration-check")
        task = asyncio.create_task(reply_worker())
    try:
        yield
    finally:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
