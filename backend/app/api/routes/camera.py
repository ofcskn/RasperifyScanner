import asyncio

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.auth import auth_service
from app.services.camera import camera_service

router = APIRouter(prefix="/camera", tags=["camera"])
_bearer = HTTPBearer()

_CONNECT_TIMEOUT = 5.0   # seconds to wait for the capture thread to confirm open
_CONNECT_POLL   = 0.1    # poll interval


def _require_auth(creds: HTTPAuthorizationCredentials = Depends(_bearer)):
    claims = auth_service.decode_token(creds.credentials)
    if not claims or claims.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return claims


@router.post("/connect")
async def connect_camera(_: dict = Depends(_require_auth)):
    camera_service.start()
    # The capture thread needs ~1-2 s to open the camera and set _capture_ok.
    # Poll briefly so the response reflects the real connection state instead
    # of always returning False while the thread is still warming up.
    elapsed = 0.0
    while not camera_service.is_connected and elapsed < _CONNECT_TIMEOUT:
        await asyncio.sleep(_CONNECT_POLL)
        elapsed += _CONNECT_POLL
    return {"connected": camera_service.is_connected}


@router.post("/disconnect")
async def disconnect_camera(_: dict = Depends(_require_auth)):
    camera_service.stop()
    return {"connected": False}
