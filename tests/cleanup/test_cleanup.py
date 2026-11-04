from sqlalchemy import func, select

import src.cleanup.__main__ as cleanup_command
from src.auth.models import RefreshToken
from src.cleanup.service import run_cleanup
from tests.conftest import expire_refresh_token, login_user
from tests.notes.helpers import (
    create_note_via_api,
    expire_note,
    get_note,
    reveal_url,
)


async def cleanup(session_maker):
    async with session_maker() as session:
        return await run_cleanup(session)


async def count_refresh_tokens(session_maker) -> int:
    async with session_maker() as session:
        return await session.scalar(select(func.count()).select_from(RefreshToken))


async def test_cleanup_on_empty_database(session_maker):
    stats = await cleanup(session_maker)

    assert tuple(stats) == (0, 0)


async def test_cleanup_wipes_payload_of_expired_note(
    client, auth_headers, session_maker
):
    note = await create_note_via_api(client, auth_headers)
    await expire_note(session_maker, note["token"])

    stats = await cleanup(session_maker)

    assert stats.notes == 1
    stored = await get_note(session_maker, note["token"])
    assert stored is not None
    assert stored.payload is None


async def test_cleanup_keeps_expired_note_in_archive(
    client, auth_headers, session_maker
):
    note = await create_note_via_api(client, auth_headers, title="old")
    await expire_note(session_maker, note["token"])

    await cleanup(session_maker)

    archive = (await client.get("/notes?status=archive", headers=auth_headers)).json()
    assert [(i["title"], i["status"]) for i in archive["items"]] == [("old", "expired")]


async def test_cleanup_does_not_touch_active_note(client, auth_headers, session_maker):
    note = await create_note_via_api(client, auth_headers)

    stats = await cleanup(session_maker)

    assert stats.notes == 0
    assert (await get_note(session_maker, note["token"])).payload is not None
    response = await client.post(reveal_url(note["token"]), json={"key": note["key"]})
    assert response.status_code == 200


async def test_cleanup_does_not_count_already_wiped_note(
    client, auth_headers, session_maker
):
    note = await create_note_via_api(client, auth_headers)
    await client.post(reveal_url(note["token"]), json={"key": note["key"]})
    await expire_note(session_maker, note["token"])

    stats = await cleanup(session_maker)

    assert stats.notes == 0


async def test_cleanup_is_idempotent(client, auth_headers, session_maker):
    note = await create_note_via_api(client, auth_headers)
    await expire_note(session_maker, note["token"])

    first = await cleanup(session_maker)
    second = await cleanup(session_maker)

    assert first.notes == 1
    assert tuple(second) == (0, 0)


async def test_cleanup_deletes_only_expired_refresh_tokens(
    client, tokens, session_maker
):
    second = await login_user(client)
    assert await count_refresh_tokens(session_maker) == 2
    await expire_refresh_token(session_maker, tokens["refresh_token"])

    stats = await cleanup(session_maker)

    assert stats.tokens == 1
    assert await count_refresh_tokens(session_maker) == 1
    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": second["refresh_token"]}
    )
    assert refreshed.status_code == 200


async def test_cleanup_keeps_revoked_but_unexpired_refresh_token(
    client, tokens, session_maker
):
    await client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})

    stats = await cleanup(session_maker)

    assert stats.tokens == 0
    assert await count_refresh_tokens(session_maker) == 1


async def test_cleanup_deletes_revoked_and_expired_refresh_token(
    client, tokens, session_maker
):
    await client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    await expire_refresh_token(session_maker, tokens["refresh_token"])

    stats = await cleanup(session_maker)

    assert stats.tokens == 1
    assert await count_refresh_tokens(session_maker) == 0


async def test_cleanup_command_runs_and_reports(session_maker, monkeypatch, capsys):
    monkeypatch.setattr(cleanup_command, "async_session_maker", session_maker)

    await cleanup_command.main()

    output = capsys.readouterr().out
    assert "wiped notes: 0, deleted refresh tokens: 0" in output
