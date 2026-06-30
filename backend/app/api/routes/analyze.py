from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.models.schemas import AnalyzeRequest, AnalysisResponse
from app.services.auth import auth_service
from app.services.pipeline import pipeline

router = APIRouter(prefix="/analyze", tags=["analyze"])
_bearer = HTTPBearer()


def _require_auth(creds: HTTPAuthorizationCredentials = Depends(_bearer)):
    claims = auth_service.decode_token(creds.credentials)
    if not claims or claims.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return claims


@router.post("", status_code=202)
async def submit_analysis(payload: AnalyzeRequest, _: dict = Depends(_require_auth)):
    # Manual scans bypass the motion gate so an explicit user request always
    # yields a persisted, broadcast result — even when the scene is static.
    result = await pipeline.run(frame_base64=payload.frame_base64, prompt=payload.prompt, force=True)
    return result
