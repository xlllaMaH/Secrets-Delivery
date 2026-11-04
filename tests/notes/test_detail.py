import uuid

import pytest

from tests.notes.helpers import (
    create_note_with_id,
    expire_note,
    other_user_headers,
    reveal_url,
)

NOT_FOUND = {"detail": "Note not found"}


async def test_detail_success(client, auth_headers, session_maker):
    note, note_id = await create_note_with_id(
        client, auth_headers, session_maker, title="Wi-Fi", max_views=3
    )

    response = await client.get(f"/notes/{note_id}", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == note_id
    assert body["title"] == "Wi-Fi"
    assert body["status"] == "active"
    assert body["max_views"] == 3
    assert body["views_count"] == 0
    assert body["consumed_at"] is None
    assert body["archived_at"] is None
    assert note["token"] not in response.text
    assert note["key"] not in response.text


async def test_detail_requires_auth(client, auth_headers, session_maker):
    _, note_id = await create_note_with_id(client, auth_headers, session_maker)

    assert (await client.get(f"/notes/{note_id}")).status_code == 401


async def test_detail_shows_consumed(client, auth_headers, session_maker):
    note, note_id = await create_note_with_id(client, auth_headers, session_maker)
    await client.post(reveal_url(note["token"]), json={"key": note["key"]})

    body = (await client.get(f"/notes/{note_id}", headers=auth_headers)).json()

    assert body["status"] == "consumed"
    assert body["views_count"] == 1
    assert body["consumed_at"] is not None


async def test_detail_shows_expired(client, auth_headers, session_maker):
    note, note_id = await create_note_with_id(client, auth_headers, session_maker)
    await expire_note(session_maker, note["token"])

    body = (await client.get(f"/notes/{note_id}", headers=auth_headers)).json()

    assert body["status"] == "expired"


async def test_detail_of_other_users_note_is_404(client, auth_headers, session_maker):
    _, note_id = await create_note_with_id(client, auth_headers, session_maker)
    other = await other_user_headers(client)

    response = await client.get(f"/notes/{note_id}", headers=other)

    assert response.status_code == 404
    assert response.json() == NOT_FOUND


async def test_detail_unknown_id_is_404(client, auth_headers):
    response = await client.get(f"/notes/{uuid.uuid4()}", headers=auth_headers)

    assert response.status_code == 404
    assert response.json() == NOT_FOUND


@pytest.mark.parametrize("note_id", ["abc", "123"])
async def test_detail_invalid_id_is_422(client, auth_headers, note_id):
    response = await client.get(f"/notes/{note_id}", headers=auth_headers)

    assert response.status_code == 422
