"""
Main entry point for the FastAPI application.
"""

import subprocess
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.api import auth
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import async_session_factory
from app.services.admin_service import bootstrap_admins

logger = setup_logging("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    except subprocess.CalledProcessError:
        logger.exception("Migration failed")
    app.state.settings = settings
    app.state.valkey = Redis.from_url(settings.valkey_url, decode_responses=False)
    async with async_session_factory() as session:
        count = await bootstrap_admins(session, settings.bootstrap_admin_ids)
        if count:
            logger.info("Bootstrapped %d admin(s) on startup", count)
    yield
    await app.state.valkey.aclose()


app = FastAPI(title="TG Scheduler API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}


def main():
    import uvicorn

    uvicorn.run(
        "app.main_api:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.api_reload,
    )


if __name__ == "__main__":
    main()
