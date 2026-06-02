from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.database import init_db
from app.services.scheduler import scheduler_service
from app.services.pipeline import scheduled_pipeline_trigger
from app.services.scheduler import set_pipeline_trigger

from app.api.routes import auth, analyze, results, schedules, health
from app.api import websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    set_pipeline_trigger(scheduled_pipeline_trigger)
    scheduler_service.start()
    await scheduler_service.load_persisted_schedules()
    yield
    scheduler_service.stop()


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
app.include_router(websocket.router)
