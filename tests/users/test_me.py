import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import delete

from src.config import settings
from src.users.models import User
from tests.conftest import EXISTING_EMAIL, EXISTING_USERNAME, bearer, set_user_active

URL = "/users/me"


def make_token(
    sub: str,
    *,
    secret: str | None = None,
    expires_in: timedelta = timedelta(minutes=5),
    token_type: str = "access",
) -> str:
    now = datetime.now(UTC)
    payload = {"sub": sub, "iat": now, "exp": now + expires_in, "type": token_type}
    return jwt.encode(
        payload, secret or settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )


async def test_me_success(client, existing_user, auth_headers):
    response = await client.get(URL, headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(existing_user.id)
    assert body["email"] == EXISTING_EMAIL
    assert body["username"] == EXISTING_USERNAME
    assert "password_hash" not in body
    assert "password" not in body


async def test_me_without_token(client, existing_user):
    response = await client.get(URL)

    assert response.status_code == 401


async def test_me_garbage_token(client, existing_user):
    response = await client.get(URL, headers=bearer("garbage"))

    assert response.status_code == 401


async def test_me_wrong_auth_scheme(client, existing_user, tokens):
    headers = {"Authorization": f"Basic {tokens['access_token']}"}

    response = await client.get(URL, headers=headers)

    assert response.status_code == 401


async def test_me_tampered_token(client, existing_user, tokens):
    token = tokens["access_token"]
    header, payload, signature = token.split(".")
    tampered = f"{header}.{payload}.{'A' * len(signature)}"

    response = await client.get(URL, headers=bearer(tampered))

    assert response.status_code == 401


async def test_me_expired_token(client, existing_user):
    token = make_token(str(existing_user.id), expires_in=timedelta(minutes=-1))

    response = await client.get(URL, headers=bearer(token))

    assert response.status_code == 401


async def test_me_token_signed_with_other_secret(client, existing_user):
    token = make_token(str(existing_user.id), secret="x" * 64)

    response = await client.get(URL, headers=bearer(token))

    assert response.status_code == 401


async def test_me_unsigned_token(client, existing_user):
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(existing_user.id),
            "exp": now + timedelta(minutes=5),
            "type": "access",
        },
        None,
        algorithm="none",
    )

    response = await client.get(URL, headers=bearer(token))

    assert response.status_code == 401


async def test_me_token_without_expiration(client, existing_user):
    token = jwt.encode(
        {"sub": str(existing_user.id), "type": "access"},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )

    response = await client.get(URL, headers=bearer(token))

    assert response.status_code == 401


async def test_me_wrong_token_type(client, existing_user):
    token = make_token(str(existing_user.id), token_type="refresh")

    response = await client.get(URL, headers=bearer(token))

    assert response.status_code == 401


async def test_me_refresh_token_is_not_accepted(client, existing_user, tokens):
    response = await client.get(URL, headers=bearer(tokens["refresh_token"]))

    assert response.status_code == 401


@pytest.mark.parametrize(
    "sub",
    ["not-a-uuid", str(uuid.uuid4())],
    ids=["sub_not_uuid", "unknown_user_id"],
)
async def test_me_invalid_subject(client, existing_user, sub):
    response = await client.get(URL, headers=bearer(make_token(sub)))

    assert response.status_code == 401


async def test_me_inactive_user(client, existing_user, auth_headers, session_maker):
    await set_user_active(session_maker, existing_user.id, False)

    response = await client.get(URL, headers=auth_headers)

    assert response.status_code == 401


async def test_me_deleted_user(client, existing_user, auth_headers, session_maker):
    async with session_maker() as session:
        await session.execute(delete(User).where(User.id == existing_user.id))
        await session.commit()

    response = await client.get(URL, headers=auth_headers)

    assert response.status_code == 401
