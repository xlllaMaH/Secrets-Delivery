import pytest
from sqlalchemy.exc import OperationalError

from src.database import get_db
from src.main import app


class BrokenSession:
    def __init__(self, error: Exception):
        self.error = error

    async def execute(self, *args, **kwargs):
        raise self.error


def break_database(error: Exception) -> None:
    async def broken_get_db():
        yield BrokenSession(error)

    app.dependency_overrides[get_db] = broken_get_db


async def test_health_ok(client):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_does_not_require_auth(client):
    assert (await client.get("/health")).status_code == 200


@pytest.mark.parametrize(
    "error",
    [
        ConnectionRefusedError("connection refused"),
        OperationalError("SELECT 1", {}, Exception("server closed the connection")),
    ],
    ids=["os_error", "sqlalchemy_error"],
)
async def test_health_returns_503_when_database_is_down(client, error):
    break_database(error)

    response = await client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}


async def test_health_does_not_leak_error_details(client):
    break_database(ConnectionRefusedError("postgres://admin:secret@db:5432"))

    response = await client.get("/health")

    assert "secret" not in response.text
    assert "postgres" not in response.text
