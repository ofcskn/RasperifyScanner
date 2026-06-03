import asyncio
import base64
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.models.database import init_db, AsyncSessionLocal
from app.models.orm import Schedule
from app.services.camera import camera_service
from app.services.connection import connection_service
from app.services.scheduler import scheduler_service
from app.services.pipeline import scheduled_pipeline_trigger
from app.services.scheduler import set_pipeline_trigger
from app.utils.image import resize_and_encode

from app.api.routes import auth, analyze, results, schedules, health, camera
from app.api import websocket

logger = logging.getLogger(__name__)

_DEFAULT_SCHEDULE_NAME = "Environment Scan"
_DEFAULT_SCHEDULE_INTERVAL = 300  # 5 minutes
_LIVE_FRAME_INTERVAL = 1.0  # seconds between live frame broadcasts
_LIVE_THUMB_WIDTH = 480
_LIVE_THUMB_HEIGHT = 270
_LIVE_THUMB_QUALITY = 60


async def _live_frame_broadcaster() -> None:
    """Broadcast live camera frames to WebSocket clients when the camera is active.

    Uses get_latest_frame() (queue read) instead of capture_now() so we never
    touch the picamera2 object from the event-loop thread — _run() owns it exclusively.
    PIL resize runs in an executor to avoid blocking the event loop.
    """
    loop = asyncio.get_running_loop()
    while True:
        try:
            if camera_service._running and connection_service.connection_count > 0:
                frame = camera_service.get_latest_frame()
                if frame is not None:
                    raw = base64.b64decode(frame.frame_base64)
                    thumb = await loop.run_in_executor(
                        None,
                        lambda b=raw: resize_and_encode(
                            b, _LIVE_THUMB_WIDTH, _LIVE_THUMB_HEIGHT, _LIVE_THUMB_QUALITY
                        ),
                    )
                    await connection_service.broadcast({
                        "event": "live_frame",
                        "frame_id": frame.frame_id,
                        "frame_thumbnail": thumb,
                    })
        except Exception as exc:
            logger.warning("Live frame broadcast error: %s", exc)
        await asyncio.sleep(_LIVE_FRAME_INTERVAL)


async def _seed_default_schedule() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Schedule).limit(1))
        if result.scalar_one_or_none() is not None:
            return
        sched = Schedule(
            name=_DEFAULT_SCHEDULE_NAME,
            interval_seconds=_DEFAULT_SCHEDULE_INTERVAL,
            enabled=True,
        )
        db.add(sched)
        await db.commit()
        await db.refresh(sched)
        scheduler_service._add_job(sched)
        logger.info("Seeded default '%s' schedule (every %ds)", _DEFAULT_SCHEDULE_NAME, _DEFAULT_SCHEDULE_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    set_pipeline_trigger(scheduled_pipeline_trigger)
    scheduler_service.start()
    await scheduler_service.load_persisted_schedules()
    await _seed_default_schedule()
    live_task = asyncio.create_task(_live_frame_broadcaster())
    yield
    scheduler_service.stop()
    live_task.cancel()
    try:
        await live_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="RasperifyScanner API",
    description="AI-powered Raspberry Pi camera environment scanner",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = "/api/v1"
app.include_router(auth.router, prefix=api_prefix)
app.include_router(analyze.router, prefix=api_prefix)
app.include_router(results.router, prefix=api_prefix)
app.include_router(schedules.router, prefix=api_prefix)
app.include_router(health.router, prefix=api_prefix)
app.include_router(camera.router, prefix=api_prefix)
app.include_router(websocket.router)
