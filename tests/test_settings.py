import pytest
from pydantic import ValidationError

from src.config import Settings

VALID = {
    "DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/db",
    "JWT_SECRET": "a" * 32,
}


def make_settings(**overrides) -> Settings:
    return Settings(_env_file=None, **{**VALID, **overrides})


def test_valid_settings_use_defaults():
    s = make_settings()

    assert s.DOCS_ENABLED is False
    assert s.CORS_ORIGINS == ""
    assert s.HASH_CONCURRENCY == 4
    assert s.JWT_ALGORITHM == "HS256"
    assert s.ACCESS_TOKEN_TTL_MINUTES == 15
    assert s.REFRESH_TOKEN_TTL_DAYS == 30


@pytest.mark.parametrize("algorithm", ["HS256", "HS384", "HS512"])
def test_allowed_jwt_algorithms(algorithm):
    assert make_settings(JWT_ALGORITHM=algorithm).JWT_ALGORITHM == algorithm


def test_jwt_secret_of_minimum_length_is_accepted():
    assert make_settings(JWT_SECRET="a" * 32).JWT_SECRET == "a" * 32


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("JWT_SECRET", ""),
        ("JWT_SECRET", "a" * 31),
        ("JWT_SECRET", "add long urlsafe string"),
        ("JWT_ALGORITHM", "none"),
        ("JWT_ALGORITHM", "HS25"),
        ("JWT_ALGORITHM", "RS256"),
        ("HASH_CONCURRENCY", 0),
        ("HASH_CONCURRENCY", -1),
        ("ACCESS_TOKEN_TTL_MINUTES", 0),
        ("REFRESH_TOKEN_TTL_DAYS", 0),
        ("CORS_ORIGINS", "*"),
        ("CORS_ORIGINS", "http://a.com,*"),
    ],
)
def test_invalid_value_is_rejected_with_field_name(field, value):
    with pytest.raises(ValidationError) as error:
        make_settings(**{field: value})

    assert field in str(error.value)


@pytest.mark.parametrize("missing", ["DATABASE_URL", "JWT_SECRET"])
def test_required_setting_is_enforced(missing):
    values = {k: v for k, v in VALID.items() if k != missing}

    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", []),
        (" ", []),
        (",,", []),
        ("http://a.com", ["http://a.com"]),
        ("http://a.com,http://b.com", ["http://a.com", "http://b.com"]),
        (" http://a.com , ,http://b.com, ", ["http://a.com", "http://b.com"]),
    ],
)
def test_cors_origins_list(raw, expected):
    assert make_settings(CORS_ORIGINS=raw).cors_origins_list == expected
