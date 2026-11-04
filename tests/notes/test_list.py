import pytest

from tests.conftest import bearer
from tests.notes.helpers import (
    create_note_via_api,
    expire_note,
    get_note,
    other_user_headers,
    reveal_url,
)

URL = "/notes"


async def burn_note(client, note: dict) -> None:
    response = await client.post(reveal_url(note["token"]), json={"key": note["key"]})
    assert response.status_code == 200


async def archive_note_via_api(client, headers, note_id: str) -> None:
    response = await client.post(f"{URL}/{note_id}/archive", headers=headers)
    assert response.status_code == 200


async def test_list_requires_auth(client):
    assert (await client.get(URL)).status_code == 401


async def test_list_rejects_invalid_token(client):
    response = await client.get(URL, headers=bearer("not-a-jwt"))

    assert response.status_code == 401


async def test_list_empty(client, auth_headers):
    response = await client.get(URL, headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


async def test_list_newest_first(client, auth_headers):
    for title in ("first", "second", "third"):
        await create_note_via_api(client, auth_headers, title=title)

    body = (await client.get(URL, headers=auth_headers)).json()

    assert [item["title"] for item in body["items"]] == ["third", "second", "first"]


async def test_list_splits_active_and_archive(client, auth_headers, session_maker):
    await create_note_via_api(client, auth_headers, title="active")
    burned = await create_note_via_api(client, auth_headers, title="burned")
    expired = await create_note_via_api(client, auth_headers, title="expired")
    archived = await create_note_via_api(client, auth_headers, title="archived")

    await burn_note(client, burned)
    await expire_note(session_maker, expired["token"])
    archived_id = (await get_note(session_maker, archived["token"])).id
    await archive_note_via_api(client, auth_headers, str(archived_id))

    active = (await client.get(URL, headers=auth_headers)).json()
    archive = (await client.get(f"{URL}?status=archive", headers=auth_headers)).json()

    assert active["total"] == 1
    assert [(i["title"], i["status"]) for i in active["items"]] == [
        ("active", "active")
    ]
    assert archive["total"] == 3
    assert {(i["title"], i["status"]) for i in archive["items"]} == {
        ("burned", "consumed"),
        ("expired", "expired"),
        ("archived", "archived"),
    }


async def test_list_status_defaults_to_active(client, auth_headers):
    await create_note_via_api(client, auth_headers)

    default = (await client.get(URL, headers=auth_headers)).json()
    explicit = (await client.get(f"{URL}?status=active", headers=auth_headers)).json()

    assert default == explicit


async def test_list_archived_wins_over_consumed(client, auth_headers, session_maker):
    note = await create_note_via_api(client, auth_headers)
    await burn_note(client, note)
    note_id = (await get_note(session_maker, note["token"])).id
    await archive_note_via_api(client, auth_headers, str(note_id))

    body = (await client.get(f"{URL}?status=archive", headers=auth_headers)).json()

    assert body["items"][0]["status"] == "archived"


async def test_list_pagination(client, auth_headers):
    for index in range(5):
        await create_note_via_api(client, auth_headers, title=str(index))

    page = (await client.get(f"{URL}?limit=2&offset=1", headers=auth_headers)).json()

    assert page["total"] == 5
    assert [item["title"] for item in page["items"]] == ["3", "2"]


async def test_list_offset_beyond_total(client, auth_headers):
    await create_note_via_api(client, auth_headers)

    body = (await client.get(f"{URL}?offset=10", headers=auth_headers)).json()

    assert body == {"items": [], "total": 1}


@pytest.mark.parametrize(
    "query",
    ["limit=0", "limit=101", "offset=-1", "status=foo"],
)
async def test_list_rejects_invalid_params(client, auth_headers, query):
    response = await client.get(f"{URL}?{query}", headers=auth_headers)

    assert response.status_code == 422


async def test_list_does_not_expose_secret_data(client, auth_headers):
    await create_note_via_api(client, auth_headers)

    item = (await client.get(URL, headers=auth_headers)).json()["items"][0]

    assert set(item) == {
        "id",
        "title",
        "status",
        "max_views",
        "views_count",
        "created_at",
        "expires_at",
        "consumed_at",
        "archived_at",
    }


async def test_list_shows_only_own_notes(client, auth_headers):
    await create_note_via_api(client, auth_headers, title="mine")
    other = await other_user_headers(client)
    await create_note_via_api(client, other, title="theirs")

    mine = (await client.get(URL, headers=auth_headers)).json()
    theirs = (await client.get(URL, headers=other)).json()

    assert [i["title"] for i in mine["items"]] == ["mine"]
    assert [i["title"] for i in theirs["items"]] == ["theirs"]
