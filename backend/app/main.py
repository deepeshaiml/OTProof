from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.db import Base, SessionLocal, engine
from app.models import Advisory, Asset  # noqa: F401 — register mapped tables


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Local quickstart creates a schema; deployments should run `alembic upgrade head` first.
    Base.metadata.create_all(engine)
    if get_settings().demo_mode:
        db = SessionLocal()
        try:
            if db.query(Asset).count() == 0 and db.query(Advisory).count() == 0:
                from app.seed_demo import seed

                seed()
        finally:
            db.close()
    yield


app = FastAPI(
    title="OTProof API",
    version="0.1.0",
    description="Passive, read-only OT inventory and public advisory applicability assurance MVP.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(router)
