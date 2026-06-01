"""DB 엔진·세션 팩토리. 테스트 시 인메모리 SQLite로 교체된다(F0-6)."""

from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./url_shortener.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """스키마를 생성한다(앱 기동 시 1회)."""
    Base.metadata.create_all(bind=engine)


def get_session() -> Iterator[Session]:
    """FastAPI 의존성: 요청 단위 세션을 제공하고 종료 시 닫는다.

    테스트에서는 dependency_overrides로 인메모리 세션으로 교체된다.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
