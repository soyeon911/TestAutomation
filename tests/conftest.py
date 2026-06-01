"""공용 픽스처 — 매 테스트마다 새 인메모리 SQLite로 격리(상태 누수 방지)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.db.models import Base
from app.db.session import get_session
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def db_session() -> Iterator[Session]:
    """각 테스트마다 격리된 인메모리 SQLite 세션을 제공하고 종료 시 정리한다."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """get_session 의존성을 인메모리 세션으로 오버라이드한 TestClient (실제 파일 DB 미사용)."""

    def _override_get_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
