from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DOCS_ENABLED: bool = False
    CORS_ORIGINS: str = ""

    DATABASE_URL: str
    HASH_CONCURRENCY: int = 4

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL_MINUTES: int = 15
    REFRESH_TOKEN_TTL_DAYS: int = 30

    @property
    def cors_origins_list(self) -> list[str]:
        return [c.strip() for c in self.CORS_ORIGINS.split(",") if c.strip()]


settings = Settings()
