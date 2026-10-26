import uuid

from sqlalchemy import select

from src.users.models import User
from tests.conftest import EXISTING_EMAIL, EXISTING_PASSWORD, EXISTING_USERNAME

URL = "/auth/register"

VALID = {
    "email": "valid_email@example.com",
    "username": "valid_user",
    "password": "Valid_password1!",
}


async def test_register_success(client):
    response = await client.post(URL, json=VALID)

    assert response.status_code == 201

    body = response.json()
    assert body["email"] == VALID["email"]
    assert body["username"] == VALID["username"]
    assert "password" not in body
    assert "password_hash" not in body
    assert uuid.UUID(body["id"])


async def test_register_stores_argon2_hash(client, session_maker):
    await client.post(URL, json=VALID)

    async with session_maker() as session:
        user = await session.scalar(select(User).where(User.email == VALID["email"]))

    assert user is not None
    assert user.password_hash.startswith("$argon2id$")
    assert user.password_hash != VALID["password"]


async def test_register_email_is_lowercased(client):
    response = await client.post(
        URL, json={**VALID, "email": "New_Valid_email@Example.Com"}
    )

    assert response.status_code == 201
    assert response.json()["email"] == "new_valid_email@example.com"


async def test_register_duplicate_username(client, existing_user):
    response = await client.post(URL, json={**VALID, "username": EXISTING_USERNAME})

    assert response.status_code == 409


async def test_register_duplicate_email(client, existing_user):
    response = await client.post(URL, json={**VALID, "email": EXISTING_EMAIL})

    assert response.status_code == 409


async def test_register_duplicate_username_and_email(client, existing_user):
    response = await client.post(
        URL,
        json={
            "email": EXISTING_EMAIL,
            "username": EXISTING_USERNAME,
            "password": EXISTING_PASSWORD,
        },
    )

    assert response.status_code == 409


async def test_register_duplicate_email_different_case(client, existing_user):
    response = await client.post(URL, json={**VALID, "email": EXISTING_EMAIL.upper()})

    assert response.status_code == 409


async def test_register_invalid_email(client):
    response = await client.post(URL, json={**VALID, "email": "invalid_email@"})

    assert response.status_code == 422


async def test_register_short_password(client):
    response = await client.post(URL, json={**VALID, "password": "pswrd"})

    assert response.status_code == 422


async def test_register_invalid_username_chars(client):
    response = await client.post(URL, json={**VALID, "username": "b@d chars!"})

    assert response.status_code == 422


async def test_register_missing_fields(client):
    response = await client.post(URL, json={"email": VALID["email"]})

    assert response.status_code == 422
