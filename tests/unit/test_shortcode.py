"""단위 테스트 — 순수 로직(app.core.shortcode). DB·네트워크 의존 없음."""

from __future__ import annotations

import random

import pytest
from app.core.shortcode import (
    ALPHABET,
    CUSTOM_ALIAS_MAX_LENGTH,
    CUSTOM_ALIAS_MIN_LENGTH,
    DEFAULT_LENGTH,
    generate_short_code,
    is_valid_custom_alias,
    is_valid_short_code,
)
from hypothesis import given
from hypothesis import strategies as st

pytestmark = pytest.mark.unit


def test_generate_short_code_default_length_returns_seven():
    assert len(generate_short_code()) == DEFAULT_LENGTH


@pytest.mark.parametrize("length", [1, 4, 7, 16, 32])
def test_generate_short_code_returns_requested_length(length: int):
    assert len(generate_short_code(length)) == length


def test_generate_short_code_uses_only_base62_alphabet():
    code = generate_short_code(50)
    assert all(c in ALPHABET for c in code)


@pytest.mark.parametrize("length", [0, -1, -10])
def test_generate_short_code_non_positive_length_raises(length: int):
    with pytest.raises(ValueError, match="length must be >= 1"):
        generate_short_code(length)


def test_generate_short_code_is_reproducible_with_fixed_seed():
    # F0-4: 시드를 고정하면 동일 코드가 재현되어야 한다.
    code_a = generate_short_code(rng=random.Random(42))
    code_b = generate_short_code(rng=random.Random(42))
    assert code_a == code_b


def test_generate_short_code_differs_across_default_calls():
    codes = {generate_short_code() for _ in range(50)}
    assert len(codes) == 50


@pytest.mark.parametrize("code", ["a", "abcd", "Ab3Xz9Q", "0123456789abcdef"])
def test_is_valid_short_code_valid_inputs_return_true(code: str):
    assert is_valid_short_code(code) is True


@pytest.mark.parametrize("code", ["", "has space", "with-dash", "under_score", "슬러그"])
def test_is_valid_short_code_invalid_inputs_return_false(code: str):
    assert is_valid_short_code(code) is False


# --- 커스텀 별칭 검증 ---


@pytest.mark.parametrize(
    "alias",
    ["abcd", "MyAlias", "promo2026", "a" * CUSTOM_ALIAS_MAX_LENGTH],
)
def test_is_valid_custom_alias_valid_inputs_return_true(alias: str):
    assert is_valid_custom_alias(alias) is True


@pytest.mark.parametrize(
    "alias",
    [
        "abc",  # 너무 짧음 (< MIN)
        "a" * (CUSTOM_ALIAS_MAX_LENGTH + 1),  # 너무 김 (> MAX)
        "has space",
        "with-dash",
        "under_score",
        "slash/x",
        "",
    ],
)
def test_is_valid_custom_alias_invalid_inputs_return_false(alias: str):
    assert is_valid_custom_alias(alias) is False


# --- 속성 기반 테스트 (Hypothesis) ---


@given(length=st.integers(min_value=1, max_value=64))
def test_property_generated_code_has_requested_length_and_charset(length: int):
    code = generate_short_code(length)
    assert len(code) == length
    assert all(c in ALPHABET for c in code)


@given(length=st.integers(min_value=CUSTOM_ALIAS_MIN_LENGTH, max_value=CUSTOM_ALIAS_MAX_LENGTH))
def test_property_generated_code_is_always_valid_short_code(length: int):
    # 생성된 코드는 항상 유효한 단축 코드여야 한다(왕복 불변식).
    assert is_valid_short_code(generate_short_code(length)) is True


@given(seed=st.integers())
def test_property_same_seed_yields_same_code(seed: int):
    a = generate_short_code(rng=random.Random(seed))
    b = generate_short_code(rng=random.Random(seed))
    assert a == b


@given(
    text=st.text(
        alphabet=st.characters(blacklist_characters=ALPHABET),
        min_size=1,
        max_size=10,
    )
)
def test_property_non_base62_text_is_invalid(text: str):
    # base62 이외 문자가 1개라도 있으면 무효.
    assert is_valid_short_code(text) is False
