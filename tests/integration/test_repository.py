"""통합 테스트 — 리포지토리 + 인메모리 DB (F0-7)."""

from __future__ import annotations

import pytest
from app.db.models import URLRecord
from app.db.repository import URLRepository
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def _make(url: str = "https://example.com", code: str = "abc1234") -> URLRecord:
    return URLRecord(short_code=code, original_url=url)


def test_save_then_get_by_code_returns_same_record(db_session: Session):
    repo = URLRepository(db_session)
    saved = repo.save(_make())

    fetched = repo.get_by_code(saved.short_code)

    assert fetched is not None
    assert fetched.short_code == "abc1234"
    assert fetched.original_url == "https://example.com"
    assert fetched.clicks == 0
    assert fetched.created_at is not None


def test_get_by_code_unknown_returns_none(db_session: Session):
    repo = URLRepository(db_session)
    assert repo.get_by_code("missing") is None


def test_increment_clicks_increases_counter(db_session: Session):
    repo = URLRepository(db_session)
    repo.save(_make())

    repo.increment_clicks("abc1234")
    record = repo.increment_clicks("abc1234")

    assert record is not None
    assert record.clicks == 2


def test_increment_clicks_unknown_returns_none(db_session: Session):
    repo = URLRepository(db_session)
    assert repo.increment_clicks("missing") is None


def test_save_multiple_records_are_independent(db_session: Session):
    repo = URLRepository(db_session)
    repo.save(_make("https://a.com", "code001"))
    repo.save(_make("https://b.com", "code002"))

    assert repo.get_by_code("code001").original_url == "https://a.com"
    assert repo.get_by_code("code002").original_url == "https://b.com"
