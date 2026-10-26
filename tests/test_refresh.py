import asyncio

from tests.conftest import (
    bearer,
    expire_refresh_token,
    login_user,
    refresh_tokens_revoked_flags,
    set_user_active,
)

URL = "/auth/refresh"


async def refresh(client, token: str):
    return await client.post(URL, json={"refresh_token": token})


async def test_refresh_success(client, existing_user, tokens, session_maker):
    response = await refresh(client, tokens["refresh_token"])

    assert response.status_code == 200
    new_tokens = response.json()
    assert new_tokens["token_type"] == "bearer"
    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    assert new_tokens["access_token"]
    assert await refresh_tokens_revoked_flags(session_maker) == [True, False]


async def test_refresh_new_access_token_works(client, existing_user, tokens):
    response = await refresh(client, tokens["refresh_token"])
    new_access_token = response.json()["access_token"]

    me = await client.get("/users/me", headers=bearer(new_access_token))

    assert me.status_code == 200
    assert me.json()["id"] == str(existing_user.id)


async def test_refresh_new_refresh_token_can_be_used_again(
    client, existing_user, tokens
):
    first = (await refresh(client, tokens["refresh_token"])).json()

    second = await refresh(client, first["refresh_token"])

    assert second.status_code == 200


async def test_refresh_reuse_revokes_all_tokens(
    client, existing_user, tokens, session_maker
):
    new_tokens = (await refresh(client, tokens["refresh_token"])).json()

    reuse = await refresh(client, tokens["refresh_token"])

    assert reuse.status_code == 401
    assert await refresh_tokens_revoked_flags(session_maker) == [True, True]
    after_alarm = await refresh(client, new_tokens["refresh_token"])
    assert after_alarm.status_code == 401


async def test_refresh_reuse_revokes_other_sessions_of_same_user(
    client, existing_user, tokens
):
    other_session = await login_user(client)
    await refresh(client, tokens["refresh_token"])

    await refresh(client, tokens["refresh_token"])

    response = await refresh(client, other_session["refresh_token"])
    assert response.status_code == 401


async def test_refresh_reuse_does_not_affect_other_users(client, existing_user, tokens):
    await client.post(
        "/auth/register",
        json={
            "email": "other@example.com",
            "username": "other_user",
            "password": "Other_password1!",
        },
    )
    other_user = await login_user(client, "other_user", "Other_password1!")
    await refresh(client, tokens["refresh_token"])

    await refresh(client, tokens["refresh_token"])

    response = await refresh(client, other_user["refresh_token"])
    assert response.status_code == 200


async def test_refresh_unknown_token(client, existing_user, tokens, session_maker):
    response = await refresh(client, "unknown-token")

    assert response.status_code == 401
    assert await refresh_tokens_revoked_flags(session_maker) == [False]


async def test_refresh_expired_token(client, existing_user, tokens, session_maker):
    await expire_refresh_token(session_maker, tokens["refresh_token"])

    response = await refresh(client, tokens["refresh_token"])

    assert response.status_code == 401


async def test_refresh_expired_token_does_not_revoke_other_sessions(
    client, existing_user, tokens, session_maker
):
    other_session = await login_user(client)
    await expire_refresh_token(session_maker, tokens["refresh_token"])

    await refresh(client, tokens["refresh_token"])

    response = await refresh(client, other_session["refresh_token"])
    assert response.status_code == 200


async def test_refresh_inactive_user(client, existing_user, tokens, session_maker):
    await set_user_active(session_maker, existing_user.id, False)

    response = await refresh(client, tokens["refresh_token"])

    assert response.status_code == 401
    assert await refresh_tokens_revoked_flags(session_maker) == [True]


async def test_refresh_empty_token(client, existing_user, tokens):
    response = await refresh(client, "")

    assert response.status_code == 422


async def test_refresh_missing_token(client, existing_user, tokens):
    response = await client.post(URL, json={})

    assert response.status_code == 422


async def test_refresh_concurrent_requests_only_one_wins(client, existing_user, tokens):
    responses = await asyncio.gather(
        *[refresh(client, tokens["refresh_token"]) for _ in range(5)]
    )

    statuses = sorted(response.status_code for response in responses)
    assert statuses == [200, 401, 401, 401, 401]
