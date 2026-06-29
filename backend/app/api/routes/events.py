"""Events / logs API — recent operational events for the frontend Logs view."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.orm import Event
from app.models.schemas import EventListResponse, EventResponse
from app.services.auth import auth_service

router = APIRouter(prefix="/events", tags=["events"])
_bearer = HTTPBearer()


def _require_auth(creds: HTTPAuthorizationCredentials = Depends(_bearer)):
    claims = auth_service.decode_token(creds.credentials)
    if not claims or claims.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return claims


@router.get("", response_model=EventListResponse)
async def list_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    kind: str | None = None,
    db: AsyncSession = Depends(get_db),
    _claims=Depends(_require_auth),
):
    stmt = select(Event)
    count_stmt = select(sqlfunc.count(Event.id))
    if kind:
        stmt = stmt.where(Event.kind == kind)
        count_stmt = count_stmt.where(Event.kind == kind)

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(Event.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    return EventListResponse(
        items=[EventResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
