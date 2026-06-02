from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.orm import Schedule
from app.models.schemas import ScheduleCreateRequest, ScheduleUpdateRequest, ScheduleResponse
from app.services.auth import auth_service
from app.services.scheduler import scheduler_service

router = APIRouter(prefix="/schedules", tags=["schedules"])
_bearer = HTTPBearer()


def _require_auth(creds: HTTPAuthorizationCredentials = Depends(_bearer)):
    claims = auth_service.decode_token(creds.credentials)
    if not claims or claims.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return claims


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(db: AsyncSession = Depends(get_db), _: dict = Depends(_require_auth)):
    result = await db.execute(select(Schedule).order_by(Schedule.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=ScheduleResponse, status_code=201)
async def create_schedule(payload: ScheduleCreateRequest, db: AsyncSession = Depends(get_db), _: dict = Depends(_require_auth)):
    return await scheduler_service.create_schedule(db, payload.name, payload.interval_seconds, payload.enabled, payload.alert_threshold)


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(schedule_id: int, payload: ScheduleUpdateRequest, db: AsyncSession = Depends(get_db), _: dict = Depends(_require_auth)):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    sched = result.scalar_one_or_none()
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return await scheduler_service.update_schedule(db, sched, **payload.model_dump(exclude_none=True))


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(schedule_id: int, db: AsyncSession = Depends(get_db), _: dict = Depends(_require_auth)):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    sched = result.scalar_one_or_none()
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await scheduler_service.delete_schedule(db, sched)
