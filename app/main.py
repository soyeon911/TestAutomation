"""앱 진입점 — 라우터 등록 및 기동 시 스키마 초기화."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.db.session import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="URL Shortener CI", version="0.1.0", lifespan=lifespan)
app.include_router(router)
