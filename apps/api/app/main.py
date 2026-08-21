from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine
from app.models import Base
from app.routers import admin, auth, billing, catalog, internal, support, tenants, whatsapp

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_tables:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title=f"{settings.app_name} API",
    version="0.1.0",
    docs_url="/docs" if settings.app_env != "production" else None,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "If-Match", "X-CSRF-Token"],
)
app.include_router(auth.router, prefix="/v1")
app.include_router(admin.router, prefix="/v1")
app.include_router(tenants.router, prefix="/v1")
app.include_router(billing.router, prefix="/v1")
app.include_router(catalog.router, prefix="/v1")
app.include_router(support.router, prefix="/v1")
app.include_router(whatsapp.router, prefix="/v1")
app.include_router(internal.router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}
