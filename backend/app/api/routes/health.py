import time
from fastapi import APIRouter
from app.config.settings import settings
from app.models.schemas import HealthResponse, AdapterStatus, DetectorStatus, OllamaStatus
from app.services.camera import camera_service
from app.services.detection.service import detection_service
from app.services.network.manager import network_manager

router = APIRouter(prefix="/health", tags=["health"])

_start_time = time.time()


@router.get("", response_model=HealthResponse)
async def health():
    adapters_info = network_manager.probe_all()
    active = network_manager.active_adapter()

    cpu_percent = None
    memory_percent = None
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent
    except ImportError:
        pass

    detector = DetectorStatus(
        backend=detection_service.detector_name,
        available=detection_service.available,
        enabled=settings.detection_enabled,
    )

    ollama_info = {"reachable": False, "model_present": False,
                   "model": settings.ollama_model, "host": settings.ollama_host}
    if settings.ollama_enabled:
        from app.services.ai.ollama import OllamaProvider
        try:
            ollama_info = await OllamaProvider().health()
        except Exception:
            pass
    ollama = OllamaStatus(
        enabled=settings.ollama_enabled,
        reachable=bool(ollama_info.get("reachable")),
        model=ollama_info.get("model", settings.ollama_model),
        model_present=bool(ollama_info.get("model_present")),
        host=ollama_info.get("host", settings.ollama_host),
    )

    return HealthResponse(
        status="ok",
        camera_connected=camera_service.is_connected,
        camera_source=settings.camera_source,
        active_adapter=active.name if active else None,
        adapters=[
            AdapterStatus(name=a.name, interface=a.interface, up=a.up, ip=a.ip)
            for a in adapters_info
        ],
        cpu_percent=cpu_percent,
        memory_percent=memory_percent,
        uptime_seconds=time.time() - _start_time,
        detector=detector,
        ollama=ollama,
    )
