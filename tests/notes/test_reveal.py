import asyncio
from datetime import UTC, datetime

import pytest

from tests.conftest import bearer
from tests.notes.helpers import (
    create_note_via_api,
    expire_note,
    get_note,
    other_user_headers,
    reveal_url,
    update_note,
)

NOT_FOUND = {"detail": "Note not found"}


async def test_reveal_roundtrip(client, auth_headers):
    note = await create_note_via_api(client, auth_headers, text="пароль 🔐 123")

    response = await client.post(reveal_url(note["token"]), json={"key": note["key"]})

    assert response.status_code == 200
    assert response.json() == {"text": "пароль 🔐 123"}


async def test_reveal_does_not_require_auth(client, auth_headers):
    note = await create_note_via_api(client, auth_headers)

    response = await client.post(reveal_url(note["token"]), json={"key": note["key"]})

    assert response.status_code == 200


async def test_reveal_is_not_cached(client, auth_headers):
    note = await create_note_via_api(client, auth_headers)

    response = await client.post(reveal_url(note["token"]), json={"key": note["key"]})

    assert response.headers["cache-control"] == "no-store"


async def test_reveal_burns_after_max_views(client, auth_headers, session_maker):
    note = await create_note_via_api(client, auth_headers, max_views=2)
    url = reveal_url(note["token"])
    body = {"key": note["key"]}

    assert (await client.post(url, json=body)).status_code == 200
    stored = await get_note(session_maker, note["token"])
    assert stored.views_count == 1
    assert stored.payload is not None
    assert stored.consumed_at is None

    assert (await client.post(url, json=body)).status_code == 200
    stored = await get_note(session_maker, note["token"])
    assert stored.views_count == 2
    assert stored.payload is None
    assert stored.consumed_at is not None

    response = await client.post(url, json=body)
    assert response.status_code == 404
    assert response.json() == NOT_FOUND


async def test_reveal_single_view_by_default(client, auth_headers):
    note = await create_note_via_api(client, auth_headers)
    url = reveal_url(note["token"])

    assert (await client.post(url, json={"key": note["key"]})).status_code == 200
    assert (await client.post(url, json={"key": note["key"]})).status_code == 404


@pytest.mark.parametrize(
    "key",
    [
        "A" * 43,
        "not base64 !!!",
        "abc",
        "ключ" * 11,
    ],
    ids=["wrong_key", "not_base64", "too_short", "non_ascii"],
)
async def test_reveal_with_bad_key_is_not_counted(
    client, auth_headers, session_maker, key
):
    note = await create_note_via_api(client, auth_headers)
    url = reveal_url(note["token"])

    response = await client.post(url, json={"key": key})

    assert response.status_code == 404
    assert response.json() == NOT_FOUND
    stored = await get_note(session_maker, note["token"])
    assert stored.views_count == 0
    assert stored.payload is not None

    assert (await client.post(url, json={"key": note["key"]})).status_code == 200


async def test_reveal_with_key_of_another_note(client, auth_headers):
    first = await create_note_via_api(client, auth_headers)
    second = await create_note_via_api(client, auth_headers)

    response = await client.post(
        reveal_url(first["token"]), json={"key": second["key"]}
    )

    assert response.status_code == 404


async def test_reveal_unknown_token(client):
    response = await client.post(reveal_url("unknown-token"), json={"key": "A" * 43})

    assert response.status_code == 404
    assert response.json() == NOT_FOUND


async def test_reveal_expired_note(client, auth_headers, session_maker):
    note = await create_note_via_api(client, auth_headers)
    await expire_note(session_maker, note["token"])

    response = await client.post(reveal_url(note["token"]), json={"key": note["key"]})

    assert response.status_code == 404
    assert response.json() == NOT_FOUND
    assert (await get_note(session_maker, note["token"])).views_count == 0


async def test_reveal_archived_note(client, auth_headers, session_maker):
    note = await create_note_via_api(client, auth_headers)
    await update_note(session_maker, note["token"], archived_at=datetime.now(UTC))

    response = await client.post(reveal_url(note["token"]), json={"key": note["key"]})

    assert response.status_code == 404
    assert response.json() == NOT_FOUND


async def test_reveal_owner_views_are_not_counted(client, auth_headers, session_maker):
    note = await create_note_via_api(client, auth_headers)
    url = reveal_url(note["token"])

    for _ in range(5):
        response = await client.post(
            url, json={"key": note["key"]}, headers=auth_headers
        )
        assert response.status_code == 200

    stored = await get_note(session_maker, note["token"])
    assert stored.views_count == 0
    assert stored.payload is not None
    assert stored.consumed_at is None

    assert (await client.post(url, json={"key": note["key"]})).status_code == 200


async def test_reveal_owner_with_wrong_key_gets_404(client, auth_headers):
    note = await create_note_via_api(client, auth_headers)

    response = await client.post(
        reveal_url(note["token"]), json={"key": "A" * 43}, headers=auth_headers
    )

    assert response.status_code == 404


async def test_reveal_by_other_user_is_counted(client, auth_headers, session_maker):
    note = await create_note_via_api(client, auth_headers, max_views=3)
    other = await other_user_headers(client)

    response = await client.post(
        reveal_url(note["token"]), json={"key": note["key"]}, headers=other
    )

    assert response.status_code == 200
    assert (await get_note(session_maker, note["token"])).views_count == 1


async def test_reveal_with_invalid_access_token_is_rejected(
    client, auth_headers, session_maker
):
    note = await create_note_via_api(client, auth_headers)

    response = await client.post(
        reveal_url(note["token"]),
        json={"key": note["key"]},
        headers=bearer("not-a-jwt"),
    )

    assert response.status_code == 401
    stored = await get_note(session_maker, note["token"])
    assert stored.views_count == 0
    assert stored.payload is not None


@pytest.mark.parametrize(
    "payload",
    [{}, {"key": ""}, {"key": "A" * 129}],
    ids=["no_key", "empty_key", "key_too_long"],
)
async def test_reveal_rejects_invalid_body(client, auth_headers, payload):
    note = await create_note_via_api(client, auth_headers)

    response = await client.post(reveal_url(note["token"]), json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize("max_views", [1, 3])
async def test_reveal_parallel_requests_respect_limit(
    client, auth_headers, session_maker, max_views
):
    note = await create_note_via_api(client, auth_headers, max_views=max_views)
    url = reveal_url(note["token"])

    responses = await asyncio.gather(
        *(client.post(url, json={"key": note["key"]}) for _ in range(20))
    )

    codes = sorted(r.status_code for r in responses)
    assert codes == [200] * max_views + [404] * (20 - max_views)
    stored = await get_note(session_maker, note["token"])
    assert stored.views_count == max_views
    assert stored.payload is None
