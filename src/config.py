from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DOCS_ENABLED: bool = False
    CORS_ORIGINS: str = ""

    DATABASE_URL: str
    HASH_CONCURRENCY: int = Field(default=4, ge=1)

    JWT_SECRET: str
    JWT_ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"
    ACCESS_TOKEN_TTL_MINUTES: int = Field(default=15, ge=1)
    REFRESH_TOKEN_TTL_DAYS: int = Field(default=30, ge=1)

    @field_validator("JWT_SECRET")
    @classmethod
    def check_jwt_secret(cls, value: str) -> str:
        if len(value) < MIN_JWT_SECRET_LENGTH:
            raise ValueError(
                f"JWT_SECRET must be at least {MIN_JWT_SECRET_LENGTH} characters"
            )
        return value

    @field_validator("CORS_ORIGINS")
    @classmethod
    def check_cors_origins(cls, value: str) -> str:
        if "*" in value:
            raise ValueError("CORS_ORIGINS must list exact origins, '*' is not allowed")
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [c.strip() for c in self.CORS_ORIGINS.split(",") if c.strip()]


settings = Settings()
