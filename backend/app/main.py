"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.routers import dashboard, production, wells
from app.seed import seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup. A larger project would use Alembic migrations instead.
    Base.metadata.create_all(bind=engine)
    if get_settings().seed_demo_data:
        with SessionLocal() as db:
            seed_if_empty(db)
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    description="Track daily oil, gas and water production across wells and fields.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(wells.router)
app.include_router(production.router)
app.include_router(dashboard.router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}
