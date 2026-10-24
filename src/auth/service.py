import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.exceptions import InvalidCredentials, InvalidToken
from src.auth.models import RefreshToken
from src.auth.schemas import TokenPair
from src.config import settings
from src.crypto.passwords import hash_password, verify_password
from src.users.models import User
from src.users.service import get_user_by_email

_dummy_hash: str | None = None

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_TTL_MINUTES),
        "type": "access"
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


async def _issue_token(db: AsyncSession, user: User) -> TokenPair:
    refresh_token = secrets.token_urlsafe(32)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=_hash_token(refresh_token),
            expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS)
        )
    )

    await db.commit()
    return TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=refresh_token
    )


async def login(db: AsyncSession, email: str, password: str) -> TokenPair:
    global _dummy_hash

    user = await get_user_by_email(db, email.lower())

    if user is None:
        if _dummy_hash is None:
            _dummy_hash = await hash_password("dummy-password")
        await verify_password(password, _dummy_hash)
        raise InvalidCredentials

    if not await verify_password(password, user.password_hash) or not user.is_active:
        raise InvalidCredentials

    return await _issue_token(db, user)


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub"]}
        )
    except jwt.PyJWTError:
        raise InvalidToken

    if payload.get("type") != "access":
        raise InvalidToken

    return payload["sub"]