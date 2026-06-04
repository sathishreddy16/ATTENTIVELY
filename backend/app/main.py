from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api.internal import router as internal_router
from app.api.sessions import router as sessions_router
from app.config import Settings, get_settings
from app.db import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    fastapi_app = FastAPI(title=resolved_settings.app_name, lifespan=lifespan)
    fastapi_app.include_router(sessions_router)
    fastapi_app.include_router(internal_router)

    @fastapi_app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "environment": resolved_settings.app_env}

    return fastapi_app


app = create_app()
