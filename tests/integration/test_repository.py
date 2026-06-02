"""통합 테스트 — 리포지토리 + 인메모리 DB (F0-7)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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


# --- 만료 시각 영속성 (UTCDateTime 왕복) ---


def test_expires_at_roundtrip_is_timezone_aware_utc(db_session: Session):
    repo = URLRepository(db_session)
    expires = datetime.now(UTC) + timedelta(hours=1)
    record = URLRecord(short_code="exp1234", original_url="https://x.com", expires_at=expires)
    repo.save(record)

    fetched = repo.get_by_code("exp1234")

    assert fetched is not None
    assert fetched.expires_at is not None
    # SQLite 왕복 후에도 tz-aware(UTC)여야 만료 비교가 가능하다.
    assert fetched.expires_at.tzinfo is not None
    assert fetched.expires_at == expires


def test_expires_at_defaults_to_none(db_session: Session):
    repo = URLRepository(db_session)
    repo.save(_make())
    assert repo.get_by_code("abc1234").expires_at is None


# --- 삭제 ---


def test_delete_existing_returns_true_and_removes(db_session: Session):
    repo = URLRepository(db_session)
    repo.save(_make())

    assert repo.delete("abc1234") is True
    assert repo.get_by_code("abc1234") is None


def test_delete_unknown_returns_false(db_session: Session):
    repo = URLRepository(db_session)
    assert repo.delete("missing") is False


# --- 목록 / 페이지네이션 ---


def test_list_records_returns_newest_first(db_session: Session):
    repo = URLRepository(db_session)
    for i in range(3):
        repo.save(_make(f"https://example.com/{i}", f"code00{i}"))

    records = repo.list_records(limit=10, offset=0)

    assert [r.short_code for r in records] == ["code002", "code001", "code000"]


def test_list_records_respects_limit_and_offset(db_session: Session):
    repo = URLRepository(db_session)
    for i in range(5):
        repo.save(_make(f"https://example.com/{i}", f"code00{i}"))

    page = repo.list_records(limit=2, offset=1)

    # 최신순(code004, code003, code002, ...)에서 offset=1, limit=2 → code003, code002
    assert [r.short_code for r in page] == ["code003", "code002"]


def test_list_records_empty_returns_empty_list(db_session: Session):
    repo = URLRepository(db_session)
    assert repo.list_records(limit=10, offset=0) == []
