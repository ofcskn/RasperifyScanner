"""SchedulerService — Pure Fabrication (GRASP): wraps APScheduler with domain schedule management."""
import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AsyncSessionLocal
from app.models.orm import Schedule

logger = logging.getLogger(__name__)

# Injected by pipeline after startup to avoid circular import
_pipeline_trigger = None


def set_pipeline_trigger(fn):
    global _pipeline_trigger
    _pipeline_trigger = fn


class SchedulerService:
    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()

    def start(self) -> None:
        self._scheduler.start()
        logger.info("SchedulerService started")

    def stop(self) -> None:
        self._scheduler.shutdown(wait=False)

    async def load_persisted_schedules(self) -> None:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            result = await db.execute(select(Schedule).where(Schedule.enabled == True))
            for sched in result.scalars().all():
                self._add_job(sched, delay_first_run=True)

    def _add_job(self, sched: Schedule, delay_first_run: bool = False) -> None:
        job_id = f"schedule_{sched.id}"
        if self._scheduler.get_job(job_id):
            return
        start = datetime.now(timezone.utc) + timedelta(seconds=sched.interval_seconds) if delay_first_run else None
        self._scheduler.add_job(
            self._run_job,
            "interval",
            seconds=sched.interval_seconds,
            id=job_id,
            args=[sched.id],
            replace_existing=True,
            next_run_time=start,
        )

    async def _run_job(self, schedule_id: int) -> None:
        if _pipeline_trigger:
            await _pipeline_trigger(schedule_id)

    async def create_schedule(self, db: AsyncSession, name: str, interval_seconds: int, enabled: bool, alert_threshold: float | None = None) -> Schedule:
        sched = Schedule(name=name, interval_seconds=interval_seconds, enabled=enabled, alert_threshold=alert_threshold)
        db.add(sched)
        await db.commit()
        await db.refresh(sched)
        if enabled:
            self._add_job(sched)
        return sched

    async def update_schedule(self, db: AsyncSession, sched: Schedule, **kwargs) -> Schedule:
        for k, v in kwargs.items():
            if v is not None:
                setattr(sched, k, v)
        await db.commit()
        await db.refresh(sched)
        job_id = f"schedule_{sched.id}"
        if sched.enabled:
            self._scheduler.add_job(
                self._run_job, "interval", seconds=sched.interval_seconds,
                id=job_id, args=[sched.id], replace_existing=True,
            )
        else:
            if self._scheduler.get_job(job_id):
                self._scheduler.remove_job(job_id)
        return sched

    async def delete_schedule(self, db: AsyncSession, sched: Schedule) -> None:
        job_id = f"schedule_{sched.id}"
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
        await db.delete(sched)
        await db.commit()

    async def record_run(self, db: AsyncSession, schedule_id: int, success: bool) -> None:
        from sqlalchemy import select
        result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
        sched = result.scalar_one_or_none()
        if sched:
            sched.last_run = datetime.now(timezone.utc)
            if success:
                sched.success_count += 1
            else:
                sched.fail_count += 1
            await db.commit()
            await self._check_alert(sched)

    async def _check_alert(self, sched: Schedule) -> None:
        total = sched.success_count + sched.fail_count
        if total == 0 or sched.alert_threshold is None:
            return
        fail_rate = sched.fail_count / total
        if fail_rate > sched.alert_threshold:
            logger.warning(
                "Schedule '%s' (id=%d) fail rate %.0f%% exceeds threshold %.0f%%",
                sched.name, sched.id, fail_rate * 100, sched.alert_threshold * 100,
            )
            from app.services.connection import connection_service
            await connection_service.broadcast({
                "event": "alert",
                "schedule_id": sched.id,
                "schedule_name": sched.name,
                "fail_rate": round(fail_rate, 3),
                "alert_threshold": sched.alert_threshold,
            })


scheduler_service = SchedulerService()
