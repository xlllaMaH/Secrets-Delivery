import jwt
import pytest
from sqlalchemy import select

from src.auth.models import RefreshToken
from src.config import settings
from tests.conftest import (
    EXISTING_EMAIL,
    EXISTING_PASSWORD,
    EXISTING_USERNAME,
    refresh_tokens_revoked_flags,
    set_user_active,
)

URL = "/auth/login"


def credentials(login: str, password: str = EXISTING_PASSWORD) -> dict[str, str]:
    return {"login": login, "password": password}


@pytest.mark.parametrize(
    "login",
    [EXISTING_EMAIL, EXISTING_EMAIL.upper(), EXISTING_USERNAME],
    ids=["email", "email_upper_case", "username"],
)
async def test_login_success(client, existing_user, login):
    response = await client.post(URL, json=credentials(login))

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_username_is_case_sensitive(client, existing_user):
    response = await client.post(URL, json=credentials(EXISTING_USERNAME.upper()))

    assert response.status_code == 401


@pytest.mark.parametrize("login", [EXISTING_EMAIL, EXISTING_USERNAME])
async def test_login_wrong_password(client, existing_user, login):
    response = await client.post(URL, json=credentials(login, "wrong-password"))

    assert response.status_code == 401


@pytest.mark.parametrize("login", ["nobody", "nobody@example.com"])
async def test_login_unknown_user(client, existing_user, login):
    response = await client.post(URL, json=credentials(login))

    assert response.status_code == 401


async def test_login_errors_do_not_reveal_which_part_is_wrong(client, existing_user):
    wrong_password = await client.post(
        URL, json=credentials(EXISTING_EMAIL, "wrong-password")
    )
    unknown_user = await client.post(URL, json=credentials("nobody@example.com"))

    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json()


async def test_login_inactive_user(client, existing_user, session_maker):
    await set_user_active(session_maker, existing_user.id, False)

    response = await client.post(URL, json=credentials(EXISTING_EMAIL))

    assert response.status_code == 401


@pytest.mark.parametrize(
    "body",
    [
        {"login": "", "password": EXISTING_PASSWORD},
        {"login": EXISTING_EMAIL, "password": ""},
        {"password": EXISTING_PASSWORD},
        {"login": EXISTING_EMAIL},
    ],
    ids=["empty_login", "empty_password", "missing_login", "missing_password"],
)
async def test_login_invalid_request(client, existing_user, body):
    response = await client.post(URL, json=body)

    assert response.status_code == 422


async def test_login_access_token_claims(client, existing_user):
    response = await client.post(URL, json=credentials(EXISTING_EMAIL))

    claims = jwt.decode(
        response.json()["access_token"],
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )
    assert claims["sub"] == str(existing_user.id)
    assert claims["type"] == "access"
    assert claims["exp"] > claims["iat"]


async def test_login_stores_only_refresh_token_hash(
    client, existing_user, session_maker
):
    response = await client.post(URL, json=credentials(EXISTING_EMAIL))
    refresh_token = response.json()["refresh_token"]

    async with session_maker() as session:
        stored = (await session.scalars(select(RefreshToken))).all()

    assert len(stored) == 1
    assert stored[0].user_id == existing_user.id
    assert stored[0].token_hash != refresh_token
    assert len(stored[0].token_hash) == 64
    assert stored[0].revoked_at is None


async def test_login_twice_creates_two_active_sessions(
    client, existing_user, session_maker
):
    await client.post(URL, json=credentials(EXISTING_EMAIL))
    await client.post(URL, json=credentials(EXISTING_USERNAME))

    assert await refresh_tokens_revoked_flags(session_maker) == [False, False]
