"""Runtime configuration API.

GET returns the user-facing knobs; PATCH applies changes live (where cheap),
persists them to config/scanner.yml so they survive restarts, and reapplies them
to the detection and AI services.
"""
import logging
import os

import yaml
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config.settings import settings
from app.models.schemas import ConfigResponse, ConfigUpdateRequest
from app.services.ai.multi_provider import multi_ai_service
from app.services.auth import auth_service
from app.services.detection.service import detection_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])
_bearer = HTTPBearer()

_YAML_CANDIDATES = ["config/scanner.yml", "../config/scanner.yml", "/config/scanner.yml"]


def _require_auth(creds: HTTPAuthorizationCredentials = Depends(_bearer)):
    claims = auth_service.decode_token(creds.credentials)
    if not claims or claims.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return claims


def _current() -> ConfigResponse:
    return ConfigResponse(
        camera_source=settings.camera_source,
        camera_rotation=settings.camera_rotation,
        detection_enabled=settings.detection_enabled,
        detection_conf_threshold=settings.detection_conf_threshold,
        detection_iou_threshold=settings.detection_iou_threshold,
        detection_interval_seconds=settings.detection_interval_seconds,
        counting_min_hits=settings.counting_min_hits,
        counting_person_alert_threshold=settings.counting_person_alert_threshold,
        ollama_enabled=settings.ollama_enabled,
        ollama_model=settings.ollama_model,
        analysis_default_interval_seconds=settings.analysis_default_interval_seconds,
        allow_cloud=settings.allow_cloud,
        store_frames=settings.store_frames,
    )


def _persist(changes: dict) -> None:
    """Merge changed keys into the first existing scanner.yml (or create one)."""
    path = next((p for p in _YAML_CANDIDATES if os.path.exists(p)), _YAML_CANDIDATES[0])
    data = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    data.update(changes)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh, sort_keys=False)
    except Exception as exc:
        logger.warning("Could not persist config to %s: %s", path, exc)


@router.get("", response_model=ConfigResponse)
async def get_config(_claims=Depends(_require_auth)):
    return _current()


@router.patch("", response_model=ConfigResponse)
async def update_config(payload: ConfigUpdateRequest, _claims=Depends(_require_auth)):
    changes = payload.model_dump(exclude_none=True)
    if not changes:
        return _current()

    for key, value in changes.items():
        setattr(settings, key, value)

    # Apply live where it's cheap.
    if "detection_enabled" in changes:
        detection_service.set_enabled(changes["detection_enabled"])
    if "detection_conf_threshold" in changes or "detection_iou_threshold" in changes:
        detection_service.apply_thresholds(
            conf=changes.get("detection_conf_threshold"),
            iou=changes.get("detection_iou_threshold"),
        )
    # Provider-affecting changes: rebuild the provider registry.
    if any(k in changes for k in ("ollama_model", "allow_cloud")):
        multi_ai_service.reload()

    _persist(changes)
    return _current()
