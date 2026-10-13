"""Authenticated Meta webhook ingress with a durable, deduplicated inbox."""

import hashlib
import hmac
import json
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from starlette.concurrency import run_in_threadpool

from src.config import settings

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp"])


def store_events(payload: dict, path: Path, phone_id: str) -> None:
    """Commit before acknowledging Meta so retries cannot lose incoming events."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=10) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS whatsapp_events (
            event_key TEXT PRIMARY KEY, kind TEXT NOT NULL,
            payload TEXT NOT NULL, received_at TEXT DEFAULT CURRENT_TIMESTAMP,
            processed INTEGER NOT NULL DEFAULT 0)""")
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if value.get("metadata", {}).get("phone_number_id") != phone_id:
                    continue
                for kind in ("messages", "statuses"):
                    for event in value.get(kind, []):
                        if not event.get("id"):
                            continue
                        key = f"{kind}:{event['id']}"
                        if kind == "statuses":
                            key += f":{event.get('status')}:{event.get('timestamp')}"
                        db.execute(
                            "INSERT OR IGNORE INTO whatsapp_events(event_key,kind,payload) VALUES(?,?,?)",
                            (key, kind, json.dumps(event)),
                        )


@router.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(request: Request) -> str:
    token = settings.WHATSAPP_VERIFY_TOKEN
    if not token:
        raise HTTPException(503, "WhatsApp webhook is not configured")
    query = request.query_params
    if (query.get("hub.mode") != "subscribe"
            or not hmac.compare_digest(query.get("hub.verify_token", ""), token)
            or "hub.challenge" not in query):
        raise HTTPException(403, "Verification failed")
    return query["hub.challenge"]


@router.post("/webhook")
async def receive_webhook(request: Request) -> dict:
    secret = settings.META_APP_SECRET
    if not secret or not settings.WHATSAPP_PHONE_NUMBER_ID:
        raise HTTPException(503, "WhatsApp webhook is not configured")
    raw = await request.body()
    signature = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(request.headers.get("x-hub-signature-256", ""), signature):
        raise HTTPException(401, "Invalid signature")
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict) or not isinstance(payload.get("entry", []), list):
            raise ValueError("Invalid event")
        if payload.get("object") != "whatsapp_business_account":
            raise ValueError("Invalid object")
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, "Invalid webhook payload")
    await run_in_threadpool(store_events, payload, settings.WHATSAPP_INBOX_PATH,
                            settings.WHATSAPP_PHONE_NUMBER_ID)
    return {"status": "received"}
