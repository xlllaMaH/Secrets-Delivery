import uuid

from tests.notes.helpers import (
    create_note_with_id,
    expire_note,
    get_note,
    other_user_headers,
    reveal_url,
)

NOT_FOUND = {"detail": "Note not found"}


async def test_archive_success(client, auth_headers, session_maker):
    _, note_id = await create_note_with_id(client, auth_headers, session_maker)

    response = await client.post(f"/notes/{note_id}/archive", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == note_id
    assert body["status"] == "archived"
    assert body["archived_at"] is not None


async def test_archive_revokes_link_and_wipes_payload(
    client, auth_headers, session_maker
):
    note, note_id = await create_note_with_id(client, auth_headers, session_maker)

    await client.post(f"/notes/{note_id}/archive", headers=auth_headers)

    response = await client.post(reveal_url(note["token"]), json={"key": note["key"]})
    assert response.status_code == 404
    assert (await get_note(session_maker, note["token"])).payload is None


async def test_archive_moves_note_to_archive_list(client, auth_headers, session_maker):
    _, note_id = await create_note_with_id(client, auth_headers, session_maker)

    await client.post(f"/notes/{note_id}/archive", headers=auth_headers)

    active = (await client.get("/notes", headers=auth_headers)).json()
    archive = (await client.get("/notes?status=archive", headers=auth_headers)).json()
    assert active["total"] == 0
    assert [item["id"] for item in archive["items"]] == [note_id]


async def test_archive_is_idempotent(client, auth_headers, session_maker):
    _, note_id = await create_note_with_id(client, auth_headers, session_maker)
    url = f"/notes/{note_id}/archive"

    first = await client.post(url, headers=auth_headers)
    second = await client.post(url, headers=auth_headers)

    assert second.status_code == 200
    assert second.json()["archived_at"] == first.json()["archived_at"]


async def test_archive_burned_and_expired_notes(client, auth_headers, session_maker):
    burned, burned_id = await create_note_with_id(client, auth_headers, session_maker)
    await client.post(reveal_url(burned["token"]), json={"key": burned["key"]})
    expired, expired_id = await create_note_with_id(client, auth_headers, session_maker)
    await expire_note(session_maker, expired["token"])

    for note_id in (burned_id, expired_id):
        response = await client.post(f"/notes/{note_id}/archive", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "archived"


async def test_archive_requires_auth(client, auth_headers, session_maker):
    _, note_id = await create_note_with_id(client, auth_headers, session_maker)

    assert (await client.post(f"/notes/{note_id}/archive")).status_code == 401


async def test_archive_other_users_note_is_404_and_note_stays_intact(
    client, auth_headers, session_maker
):
    note, note_id = await create_note_with_id(client, auth_headers, session_maker)
    other = await other_user_headers(client)

    response = await client.post(f"/notes/{note_id}/archive", headers=other)

    assert response.status_code == 404
    assert response.json() == NOT_FOUND
    stored = await get_note(session_maker, note["token"])
    assert stored.archived_at is None
    assert stored.payload is not None
    assert (
        await client.post(reveal_url(note["token"]), json={"key": note["key"]})
    ).status_code == 200


async def test_archive_unknown_id_is_404(client, auth_headers):
    response = await client.post(f"/notes/{uuid.uuid4()}/archive", headers=auth_headers)

    assert response.status_code == 404
    assert response.json() == NOT_FOUND
