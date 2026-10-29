from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select, update

from src.notes.models import Note
from tests.conftest import bearer


async def create_note_via_api(
    client: AsyncClient, headers: dict[str, str], **payload
) -> dict:
    payload.setdefault("text", "my secret")
    response = await client.post("/notes", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


def reveal_url(token: str) -> str:
    return f"/notes/{token}/reveal"


async def get_note(session_maker, token: str) -> Note:
    async with session_maker() as session:
        return await session.scalar(select(Note).where(Note.token == token))


async def update_note(session_maker, token: str, **values) -> None:
    async with session_maker() as session:
        await session.execute(update(Note).where(Note.token == token).values(**values))
        await session.commit()


async def expire_note(session_maker, token: str) -> None:
    await update_note(
        session_maker, token, expires_at=datetime.now(UTC) - timedelta(seconds=1)
    )


async def other_user_headers(client: AsyncClient) -> dict[str, str]:
    credentials = {
        "email": "other@example.com",
        "username": "other_user",
        "password": "Other_password1!",
    }
    response = await client.post("/auth/register", json=credentials)
    assert response.status_code == 201
    login = await client.post(
        "/auth/login",
        json={"login": credentials["email"], "password": credentials["password"]},
    )
    assert login.status_code == 200
    return bearer(login.json()["access_token"])
