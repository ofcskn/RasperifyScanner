"""AuthService — Pure Fabrication (GRASP): handles JWT lifecycle and password hashing."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config.settings import settings
from app.models.orm import User

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def hash_password(self, password: str) -> str:
        return _pwd_context.hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        return _pwd_context.verify(plain, hashed)

    def create_access_token(self, subject: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
        return jwt.encode({"sub": subject, "exp": expire, "type": "access"}, settings.secret_key, settings.algorithm)

    def create_refresh_token(self, subject: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        return jwt.encode({"sub": subject, "exp": expire, "type": "refresh"}, settings.secret_key, settings.algorithm)

    def decode_token(self, token: str) -> Optional[dict]:
        try:
            return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        except JWTError:
            return None

    async def authenticate_user(self, db: AsyncSession, username: str, password: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if user and self.verify_password(password, user.hashed_password):
            return user
        return None

    async def create_user(self, db: AsyncSession, username: str, password: str) -> User:
        user = User(username=username, hashed_password=self.hash_password(password))
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


auth_service = AuthService()
