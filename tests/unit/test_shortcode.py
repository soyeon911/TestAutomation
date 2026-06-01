"""단위 테스트 — 순수 로직(app.core.shortcode). DB·네트워크 의존 없음."""

from __future__ import annotations

import random

import pytest
from app.core.shortcode import (
    ALPHABET,
    DEFAULT_LENGTH,
    generate_short_code,
    is_valid_short_code,
)

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
