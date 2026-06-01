"""URL 레코드 영속성 접근 계층 (리포지토리 패턴, F0-6).

인터페이스: save(record) / get_by_code(code) / increment_clicks(code).
integration 테스트(tests/integration)의 주 대상이다.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import URLRecord


class URLRepository:
    """URLRecord에 대한 영속성 연산을 캡슐화한다."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, record: URLRecord) -> URLRecord:
        """레코드를 저장하고 갱신된 인스턴스를 반환한다."""
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record

    def get_by_code(self, short_code: str) -> URLRecord | None:
        """단축 코드로 레코드를 조회한다. 없으면 None."""
        stmt = select(URLRecord).where(URLRecord.short_code == short_code)
        return self._session.scalar(stmt)

    def increment_clicks(self, short_code: str) -> URLRecord | None:
        """클릭 수를 1 증가시키고 갱신된 레코드를 반환한다. 없으면 None."""
        record = self.get_by_code(short_code)
        if record is None:
            return None
        record.clicks += 1
        self._session.commit()
        self._session.refresh(record)
        return record
