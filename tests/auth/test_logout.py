from tests.conftest import bearer, login_user, refresh_tokens_revoked_flags

URL = "/auth/logout"


async def logout(client, token: str):
    return await client.post(URL, json={"refresh_token": token})


async def test_logout_success(client, existing_user, tokens, session_maker):
    response = await logout(client, tokens["refresh_token"])

    assert response.status_code == 204
    assert response.content == b""
    assert await refresh_tokens_revoked_flags(session_maker) == [True]


async def test_logout_refresh_token_stops_working(client, existing_user, tokens):
    await logout(client, tokens["refresh_token"])

    response = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert response.status_code == 401


async def test_logout_is_idempotent(client, existing_user, tokens):
    first = await logout(client, tokens["refresh_token"])
    second = await logout(client, tokens["refresh_token"])

    assert first.status_code == second.status_code == 204


async def test_logout_unknown_token(client, existing_user, tokens, session_maker):
    response = await logout(client, "unknown-token")

    assert response.status_code == 204
    assert await refresh_tokens_revoked_flags(session_maker) == [False]


async def test_logout_does_not_affect_other_sessions(
    client, existing_user, tokens, session_maker
):
    other_session = await login_user(client)

    await logout(client, tokens["refresh_token"])

    assert await refresh_tokens_revoked_flags(session_maker) == [True, False]
    response = await client.post(
        "/auth/refresh", json={"refresh_token": other_session["refresh_token"]}
    )
    assert response.status_code == 200


async def test_logout_access_token_stays_valid_until_expiration(
    client, existing_user, tokens
):
    await logout(client, tokens["refresh_token"])

    response = await client.get("/users/me", headers=bearer(tokens["access_token"]))

    assert response.status_code == 200


async def test_logout_empty_token(client, existing_user, tokens):
    response = await logout(client, "")

    assert response.status_code == 422
