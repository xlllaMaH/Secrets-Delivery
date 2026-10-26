import hashlib
import os
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from dotenv import dotenv_values
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import src.models  # noqa: F401
from src.auth.models import RefreshToken
from src.crypto.passwords.hasher import hash_password
from src.database import Base, get_db
from src.main import app
from src.users.models import User

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL") or dotenv_values(".env").get(
    "TEST_DATABASE_URL"
)

EXISTING_EMAIL = "existing@example.com"
EXISTING_USERNAME = "existing_user"
EXISTING_PASSWORD = "correct-test-password1!"


@pytest.fixture
async def engine():
    if not TEST_DATABASE_URL:
        pytest.fail("TEST_DATABASE_URL is not set")
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("TRUNCATE TABLE users CASCADE"))
    yield engine
    await engine.dispose()


@pytest.fixture
async def session_maker(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
async def client(session_maker) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def existing_user(session_maker) -> User:
    async with session_maker() as session:
        user = User(
            id=uuid.uuid4(),
            email=EXISTING_EMAIL,
            username=EXISTING_USERNAME,
            password_hash=await hash_password(EXISTING_PASSWORD),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def login_user(
    client: AsyncClient,
    login: str = EXISTING_EMAIL,
    password: str = EXISTING_PASSWORD,
) -> dict[str, str]:
    response = await client.post(
        "/auth/login", json={"login": login, "password": password}
    )
    assert response.status_code == 200
    return response.json()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def refresh_tokens_revoked_flags(session_maker) -> list[bool]:
    """Для каждого refresh-токена по порядку создания: True, если он погашен."""
    async with session_maker() as session:
        rows = await session.scalars(
            select(RefreshToken).order_by(RefreshToken.created_at)
        )
        return [row.revoked_at is not None for row in rows]


async def set_user_active(session_maker, user_id: uuid.UUID, active: bool) -> None:
    async with session_maker() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(is_active=active)
        )
        await session.commit()


async def expire_refresh_token(session_maker, token: str) -> None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    async with session_maker() as session:
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        await session.commit()


@pytest.fixture
async def tokens(client, existing_user) -> dict[str, str]:
    return await login_user(client)


@pytest.fixture
def auth_headers(tokens) -> dict[str, str]:
    return bearer(tokens["access_token"])
