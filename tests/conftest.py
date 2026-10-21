import os
import uuid
from collections.abc import AsyncGenerator

import pytest
from dotenv import dotenv_values
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import src.models  # noqa: F401
from src.crypto.passwords import hash_password
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
