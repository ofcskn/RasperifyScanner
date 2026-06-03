from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import select, text
from app.config.settings import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def _migrate(conn) -> None:
    """Add columns that were introduced after the initial schema was created."""
    result = await conn.execute(text("PRAGMA table_info(analyses)"))
    existing_cols = {row[1] for row in result.fetchall()}
    if "environment_json" not in existing_cols:
        await conn.execute(text("ALTER TABLE analyses ADD COLUMN environment_json JSON"))


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate(conn)

    if settings.default_username and settings.default_password:
        from app.models.orm import User
        from app.services.auth import auth_service
        async with AsyncSessionLocal() as session:
            existing = await session.execute(select(User).where(User.username == settings.default_username))
            if not existing.scalar_one_or_none():
                await auth_service.create_user(session, settings.default_username, settings.default_password)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
