from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.auth import auth_service
from app.services.camera import camera_service

router = APIRouter(prefix="/camera", tags=["camera"])
_bearer = HTTPBearer()


def _require_auth(creds: HTTPAuthorizationCredentials = Depends(_bearer)):
    claims = auth_service.decode_token(creds.credentials)
    if not claims or claims.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return claims


@router.post("/connect")
async def connect_camera(_: dict = Depends(_require_auth)):
    camera_service.start()
    return {"connected": camera_service.is_connected}


@router.post("/disconnect")
async def disconnect_camera(_: dict = Depends(_require_auth)):
    camera_service.stop()
    return {"connected": False}
