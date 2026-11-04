import pytest
from httpx import ASGITransport, AsyncClient

from src.main import create_app
from tests.test_settings import make_settings

ALLOWED = "http://ok.com"
OTHER = "http://evil.com"


async def request(app, method: str, url: str, **kwargs):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        return await ac.request(method, url, **kwargs)


async def preflight(app, origin: str):
    return await request(
        app,
        "OPTIONS",
        "/notes",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )


@pytest.mark.parametrize("url", ["/docs", "/redoc", "/openapi.json"])
async def test_docs_are_hidden_by_default(url):
    app = create_app(make_settings())

    assert (await request(app, "GET", url)).status_code == 404


@pytest.mark.parametrize("url", ["/docs", "/redoc", "/openapi.json"])
async def test_docs_are_available_when_enabled(url):
    app = create_app(make_settings(DOCS_ENABLED=True))

    assert (await request(app, "GET", url)).status_code == 200


async def test_cors_is_off_without_origins():
    app = create_app(make_settings())

    response = await preflight(app, ALLOWED)

    assert "access-control-allow-origin" not in response.headers


async def test_cors_allows_listed_origin():
    app = create_app(make_settings(CORS_ORIGINS=f"{ALLOWED}, http://x.com"))

    response = await preflight(app, ALLOWED)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED
    assert "access-control-allow-credentials" not in response.headers


async def test_cors_rejects_unlisted_origin():
    app = create_app(make_settings(CORS_ORIGINS=ALLOWED))

    response = await preflight(app, OTHER)

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


async def test_cors_rejects_disallowed_method():
    app = create_app(make_settings(CORS_ORIGINS=ALLOWED))

    response = await request(
        app,
        "OPTIONS",
        "/notes",
        headers={"Origin": ALLOWED, "Access-Control-Request-Method": "DELETE"},
    )

    assert response.status_code == 400
