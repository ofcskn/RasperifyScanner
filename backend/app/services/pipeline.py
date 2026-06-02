"""AnalysisPipelineController — Controller + Creator (GRASP).

Orchestrates: capture frame → motion check → AI analysis → persist to DB → broadcast via WebSocket.
"""
import base64
import io
import json
import logging
import os
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AsyncSessionLocal
from app.models.orm import Analysis, DetectionResult, IntensityMetric
from app.services.ai.multi_provider import multi_ai_service
from app.services.camera import camera_service
from app.services.connection import connection_service

logger = logging.getLogger(__name__)

_MOTION_THRESHOLD = float(os.getenv("MOTION_THRESHOLD", "5.0"))
_MOTION_SIZE = (64, 64)


def _frame_diff(prev_b64: str, curr_b64: str) -> float:
    from PIL import Image, ImageChops
    def _open(b64: str) -> Image.Image:
        return Image.open(io.BytesIO(base64.b64decode(b64))).convert("L").resize(_MOTION_SIZE)
    diff = ImageChops.difference(_open(prev_b64), _open(curr_b64))
    pixels = list(diff.getdata())
    return sum(pixels) / len(pixels)


class AnalysisPipelineController:
    def __init__(self) -> None:
        self._last_frame_b64: str | None = None

    async def run(self, frame_base64: str | None = None, prompt: str | None = None, schedule_id: int | None = None) -> dict:
        """Capture (or accept) a frame, analyze, persist, and broadcast."""
        if frame_base64 is None:
            frame = camera_service.capture_now()
            frame_id = frame.frame_id
            frame_base64 = frame.frame_base64
        else:
            frame_id = str(uuid.uuid4())

        motion_detected = True
        if self._last_frame_b64 is not None:
            try:
                diff = _frame_diff(self._last_frame_b64, frame_base64)
                if diff < _MOTION_THRESHOLD:
                    logger.debug("Motion below threshold (%.2f < %.2f), skipping analysis", diff, _MOTION_THRESHOLD)
                    motion_detected = False
            except Exception as exc:
                logger.warning("Motion detection error: %s", exc)
        self._last_frame_b64 = frame_base64

        if not motion_detected:
            return {"event": "no_motion", "frame_id": frame_id, "motion_detected": False}

        result = await multi_ai_service.analyze(frame_base64, prompt)
        motion_detected = True

        async with AsyncSessionLocal() as db:
            analysis = Analysis(
                frame_id=frame_id,
                provider=result.provider,
                raw_response=result.raw_response,
            )
            db.add(analysis)
            await db.flush()

            for det in result.detections:
                db.add(DetectionResult(
                    analysis_id=analysis.id,
                    object_name=det.object_name,
                    confidence=det.confidence,
                    bbox_json=json.dumps(det.bbox) if det.bbox else None,
                ))
            for name, value in result.metrics.items():
                db.add(IntensityMetric(analysis_id=analysis.id, metric_name=name, value=value))

            await db.commit()
            await db.refresh(analysis)
            analysis_id = analysis.id

        broadcast_payload = {
            "event": "analysis_complete",
            "id": analysis_id,
            "frame_id": frame_id,
            "provider": result.provider,
            "motion_detected": motion_detected,
            "detections": [
                {"object_name": d.object_name, "confidence": d.confidence, "bbox": d.bbox}
                for d in result.detections
            ],
            "metrics": result.metrics,
        }
        await connection_service.broadcast(broadcast_payload)

        if schedule_id is not None:
            from app.services.scheduler import scheduler_service
            async with AsyncSessionLocal() as db:
                await scheduler_service.record_run(db, schedule_id, success=True)

        return broadcast_payload


pipeline = AnalysisPipelineController()  # singleton with motion state


async def scheduled_pipeline_trigger(schedule_id: int) -> None:
    try:
        await pipeline.run(schedule_id=schedule_id)
    except Exception as exc:
        logger.error("Scheduled pipeline run failed for schedule %d: %s", schedule_id, exc)
        from app.services.scheduler import scheduler_service
        async with AsyncSessionLocal() as db:
            await scheduler_service.record_run(db, schedule_id, success=False)
