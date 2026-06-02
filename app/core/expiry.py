"""만료(TTL) 관련 순수 로직 (DB·네트워크 의존 없음).

시간을 인자로 주입받아 결정적으로 테스트할 수 있게 한다(시간 의존성 제거).
"""

from __future__ import annotations

from datetime import datetime, timedelta

MAX_TTL_SECONDS = 60 * 60 * 24 * 365  # 1년


def compute_expires_at(created_at: datetime, ttl_seconds: int | None) -> datetime | None:
    """생성 시각과 TTL(초)로 만료 시각을 계산한다.

    Args:
        created_at: 기준 시각.
        ttl_seconds: 만료까지 초. None 이면 만료 없음(None 반환).

    Raises:
        ValueError: ttl_seconds 가 1 미만이거나 MAX_TTL_SECONDS 초과인 경우.
    """
    if ttl_seconds is None:
        return None
    if not 1 <= ttl_seconds <= MAX_TTL_SECONDS:
        raise ValueError(f"ttl_seconds must be between 1 and {MAX_TTL_SECONDS}, got {ttl_seconds}")
    return created_at + timedelta(seconds=ttl_seconds)


def is_expired(expires_at: datetime | None, now: datetime) -> bool:
    """주어진 시각(now) 기준으로 만료되었는지 판정한다.

    expires_at 이 None 이면 영구(만료 안 함). now 가 expires_at 이상이면 만료.
    """
    if expires_at is None:
        return False
    return now >= expires_at
