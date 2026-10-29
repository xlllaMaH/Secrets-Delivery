from datetime import UTC, datetime, timedelta

import pytest

from src.notes.constants import (
    DEFAULT_MAX_VIEWS,
    DEFAULT_TTL_HOURS,
    MAX_TEXT_LENGTH,
    MAX_TITLE_LENGTH,
    MAX_TTL_HOURS,
    MAX_VIEWS_LIMIT,
    MIN_TTL_HOURS,
)
from tests.conftest import bearer
from tests.notes.helpers import get_note

URL = "/notes"


async def test_create_note_success(client, auth_headers):
    response = await client.post(URL, json={"text": "hello"}, headers=auth_headers)

    assert response.status_code == 201
    body = response.json()
    assert len(body["token"]) == 22
    assert len(body["key"]) == 43
    assert body["max_views"] == DEFAULT_MAX_VIEWS
    assert set(body) == {"token", "key", "expires_at", "max_views"}


async def test_create_note_is_not_cached(client, auth_headers):
    response = await client.post(URL, json={"text": "hello"}, headers=auth_headers)

    assert response.headers["cache-control"] == "no-store"


async def test_create_note_default_expiry(client, auth_headers):
    before = datetime.now(UTC)
    response = await client.post(URL, json={"text": "hello"}, headers=auth_headers)

    expires_at = datetime.fromisoformat(response.json()["expires_at"])
    expected = before + timedelta(hours=DEFAULT_TTL_HOURS)
    assert abs((expires_at - expected).total_seconds()) < 10


async def test_create_note_stores_encrypted_payload(
    client, auth_headers, session_maker, existing_user
):
    text = "very-recognizable-plaintext"
    response = await client.post(URL, json={"text": text}, headers=auth_headers)
    body = response.json()

    note = await get_note(session_maker, body["token"])

    assert note.owner_id == existing_user.id
    assert note.views_count == 0
    assert note.consumed_at is None
    assert note.archived_at is None
    assert text.encode() not in note.payload
    assert body["key"].encode() not in note.payload
    assert len(note.payload) == 12 + len(text) + 16


async def test_create_note_saves_title(client, auth_headers, session_maker):
    response = await client.post(
        URL, json={"text": "hello", "title": "Wi-Fi"}, headers=auth_headers
    )

    note = await get_note(session_maker, response.json()["token"])
    assert note.title == "Wi-Fi"


async def test_create_note_tokens_and_keys_are_unique(client, auth_headers):
    first = (await client.post(URL, json={"text": "a"}, headers=auth_headers)).json()
    second = (await client.post(URL, json={"text": "a"}, headers=auth_headers)).json()

    assert first["token"] != second["token"]
    assert first["key"] != second["key"]


async def test_create_note_requires_auth(client):
    response = await client.post(URL, json={"text": "hello"})

    assert response.status_code == 401


async def test_create_note_rejects_invalid_token(client):
    response = await client.post(
        URL, json={"text": "hello"}, headers=bearer("not-a-jwt")
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {"text": ""},
        {"text": "x" * (MAX_TEXT_LENGTH + 1)},
        {},
        {"text": "hello", "title": "t" * (MAX_TITLE_LENGTH + 1)},
        {"text": "hello", "expires_in_hours": MIN_TTL_HOURS - 1},
        {"text": "hello", "expires_in_hours": MAX_TTL_HOURS + 1},
        {"text": "hello", "max_views": 0},
        {"text": "hello", "max_views": MAX_VIEWS_LIMIT + 1},
    ],
    ids=[
        "empty_text",
        "text_too_long",
        "no_text",
        "title_too_long",
        "ttl_too_small",
        "ttl_too_large",
        "zero_views",
        "too_many_views",
    ],
)
async def test_create_note_rejects_invalid_input(client, auth_headers, payload):
    response = await client.post(URL, json=payload, headers=auth_headers)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"text": "x" * MAX_TEXT_LENGTH},
        {"text": "hello", "title": "t" * MAX_TITLE_LENGTH},
        {"text": "hello", "expires_in_hours": MIN_TTL_HOURS},
        {"text": "hello", "expires_in_hours": MAX_TTL_HOURS},
        {"text": "hello", "max_views": 1},
        {"text": "hello", "max_views": MAX_VIEWS_LIMIT},
    ],
    ids=[
        "max_text",
        "max_title",
        "min_ttl",
        "max_ttl",
        "min_views",
        "max_views",
    ],
)
async def test_create_note_accepts_boundary_values(client, auth_headers, payload):
    response = await client.post(URL, json=payload, headers=auth_headers)

    assert response.status_code == 201
