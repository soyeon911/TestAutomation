"""SQLAlchemy 2.x ORM 모델."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class Base(DeclarativeBase):
    """선언적 베이스."""


class UTCDateTime(TypeDecorator[datetime]):
    """항상 timezone-aware UTC 로 저장/조회하는 DateTime.

    SQLite의 DateTime(timezone=True)는 조회 시 naive 를 돌려줘 aware 비교(만료 판정)에서
    TypeError 를 낸다. 이 타입은 bind/result 양쪽에서 UTC tzinfo 를 보장한다.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class URLRecord(Base):
    """단축 코드 ↔ 원본 URL 매핑 레코드."""

    __tablename__ = "url_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    short_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    original_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_utcnow)
    # 만료 시각. None 이면 만료 없음(영구).
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
