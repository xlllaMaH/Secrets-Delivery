from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.auth.router import router as auth_router
from src.config import Settings, settings
from src.health.router import router as health_router
from src.notes.router import router as notes_router
from src.users.router import router as users_router


def create_app(app_settings: Settings = settings) -> FastAPI:
    docs = app_settings.DOCS_ENABLED
    app = FastAPI(
        title="Secret Delivery",
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
    )

    origins = app_settings.cors_origins_list
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type"],
            allow_credentials=False,
        )

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(notes_router)
    app.include_router(health_router)

    return app


app = create_app()
