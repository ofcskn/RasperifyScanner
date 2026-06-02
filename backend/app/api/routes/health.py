import time
from fastapi import APIRouter
from app.models.schemas import HealthResponse, AdapterStatus
from app.services.camera import camera_service
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

    return HealthResponse(
        status="ok",
        camera_connected=camera_service.is_connected,
        active_adapter=active.name if active else None,
        adapters=[
            AdapterStatus(name=a.name, interface=a.interface, up=a.up, ip=a.ip)
            for a in adapters_info
        ],
        cpu_percent=cpu_percent,
        memory_percent=memory_percent,
        uptime_seconds=time.time() - _start_time,
    )
