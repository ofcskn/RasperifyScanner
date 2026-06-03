import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.orm import Analysis, DetectionResult, IntensityMetric
from app.models.schemas import AnalysisResponse, DetectionItem, MetricItem, AnalysisListResponse, EnvironmentScanSchema
from app.services.auth import auth_service

router = APIRouter(prefix="/results", tags=["results"])
_bearer = HTTPBearer()


def _require_auth(creds: HTTPAuthorizationCredentials = Depends(_bearer)):
    claims = auth_service.decode_token(creds.credentials)
    if not claims or claims.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return claims


def _to_response(analysis: Analysis) -> AnalysisResponse:
    env = EnvironmentScanSchema(**analysis.environment_json) if analysis.environment_json else None
    return AnalysisResponse(
        id=analysis.id,
        frame_id=analysis.frame_id,
        provider=analysis.provider,
        raw_response=analysis.raw_response,
        environment_scan=env,
        created_at=analysis.created_at,
        detections=[
            DetectionItem(
                object_name=d.object_name,
                confidence=d.confidence,
                bbox=json.loads(d.bbox_json) if d.bbox_json else None,
            )
            for d in analysis.detections
        ],
        metrics=[MetricItem(metric_name=m.metric_name, value=m.value) for m in analysis.metrics],
    )


def _build_conditions(date_from, date_to, object_name, min_confidence, environment_type=None):
    conditions = []
    if date_from:
        conditions.append(Analysis.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        conditions.append(Analysis.created_at < datetime.fromisoformat(date_to) + timedelta(days=1))
    if object_name or min_confidence is not None:
        det_conditions = []
        if object_name:
            det_conditions.append(DetectionResult.object_name.ilike(f"%{object_name}%"))
        if min_confidence is not None:
            det_conditions.append(DetectionResult.confidence >= min_confidence)
        subq = select(DetectionResult.analysis_id).where(*det_conditions).distinct()
        conditions.append(Analysis.id.in_(subq))
    if environment_type:
        conditions.append(
            sqlfunc.json_extract(Analysis.environment_json, "$.environment_type") == environment_type
        )
    return conditions


@router.get("", response_model=AnalysisListResponse)
async def list_results(
    page: int = 1,
    page_size: int = 20,
    date_from: str | None = None,
    date_to: str | None = None,
    object_name: str | None = None,
    min_confidence: float | None = None,
    environment_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(_require_auth),
):
    conditions = _build_conditions(date_from, date_to, object_name, min_confidence, environment_type)
    offset = (page - 1) * page_size

    count_q = select(sqlfunc.count(Analysis.id))
    if conditions:
        count_q = count_q.where(*conditions)
    total_result = await db.execute(count_q)
    total = total_result.scalar_one()

    data_q = select(Analysis).order_by(Analysis.created_at.desc()).offset(offset).limit(page_size)
    if conditions:
        data_q = data_q.where(*conditions)
    result = await db.execute(data_q)
    items = [_to_response(a) for a in result.scalars().unique().all()]
    return AnalysisListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{result_id}", response_model=AnalysisResponse)
async def get_result(result_id: int, db: AsyncSession = Depends(get_db), _: dict = Depends(_require_auth)):
    result = await db.execute(select(Analysis).where(Analysis.id == result_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Result not found")
    return _to_response(analysis)
