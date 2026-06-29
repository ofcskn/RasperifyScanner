"""Event logging — persists operational events and broadcasts them live.

Single entry point (`record_event`) so the pipeline, camera, and provider layers
all log the same way: write an Event row, then push an `event` WebSocket message
for the frontend Events/Logs view.
"""
from __future__ import annotations

import logging

from app.models.database import AsyncSessionLocal
from app.models.orm import Event
from app.services.connection import connection_service

logger = logging.getLogger(__name__)


async def record_event(kind: str, message: str, severity: str = "info", data: dict | None = None) -> None:
    try:
        async with AsyncSessionLocal() as db:
            event = Event(kind=kind, message=message, severity=severity, data_json=data)
            db.add(event)
            await db.commit()
            await db.refresh(event)
            created_at = event.created_at
            event_id = event.id
    except Exception as exc:  # logging must never break the caller
        logger.error("Failed to persist event %s: %s", kind, exc)
        return

    try:
        await connection_service.broadcast({
            "event": "event",
            "id": event_id,
            "kind": kind,
            "severity": severity,
            "message": message,
            "data": data,
            "created_at": created_at.isoformat() if created_at else None,
        })
    except Exception as exc:
        logger.warning("Failed to broadcast event %s: %s", kind, exc)
