"""단위 테스트 — 만료 순수 로직(app.core.expiry). 시간 주입으로 결정적."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.core.expiry import MAX_TTL_SECONDS, compute_expires_at, is_expired
from hypothesis import given
from hypothesis import strategies as st

pytestmark = pytest.mark.unit

_BASE = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


# --- compute_expires_at ---


def test_compute_expires_at_none_ttl_returns_none():
    assert compute_expires_at(_BASE, None) is None


@pytest.mark.parametrize("ttl", [1, 60, 3600, MAX_TTL_SECONDS])
def test_compute_expires_at_adds_ttl_seconds(ttl: int):
    assert compute_expires_at(_BASE, ttl) == _BASE + timedelta(seconds=ttl)


@pytest.mark.parametrize("ttl", [0, -1, MAX_TTL_SECONDS + 1])
def test_compute_expires_at_out_of_range_raises(ttl: int):
    with pytest.raises(ValueError, match="ttl_seconds must be between"):
        compute_expires_at(_BASE, ttl)


# --- is_expired ---


def test_is_expired_none_never_expires():
    assert is_expired(None, _BASE) is False


def test_is_expired_before_expiry_returns_false():
    expires = _BASE + timedelta(seconds=10)
    assert is_expired(expires, _BASE) is False


def test_is_expired_at_exact_boundary_returns_true():
    # now == expires_at 이면 만료로 본다.
    assert is_expired(_BASE, _BASE) is True


def test_is_expired_after_expiry_returns_true():
    expires = _BASE - timedelta(seconds=1)
    assert is_expired(expires, _BASE) is True


# --- 속성 기반 테스트 (Hypothesis) ---


@given(ttl=st.integers(min_value=1, max_value=MAX_TTL_SECONDS))
def test_property_just_created_is_not_expired(ttl: int):
    # 막 생성된(now == created_at) 항목은 아직 만료되지 않아야 한다.
    expires = compute_expires_at(_BASE, ttl)
    assert is_expired(expires, _BASE) is False


@given(ttl=st.integers(min_value=1, max_value=MAX_TTL_SECONDS))
def test_property_past_expiry_is_expired(ttl: int):
    # 만료 시각을 1초라도 지나면 만료여야 한다.
    expires = compute_expires_at(_BASE, ttl)
    assert expires is not None
    assert is_expired(expires, expires + timedelta(seconds=1)) is True
