"""단축 코드 생성 등 순수 로직 (DB·네트워크 의존 없음).

F0-4: 외부 의존성 없이 동작해 단위 테스트가 가능해야 한다.
기본 RNG는 암호학적으로 안전한 SystemRandom이지만, 단위 테스트가
시드를 고정해 재현성을 검증할 수 있도록 `rng` 주입을 허용한다.
"""

from __future__ import annotations

import random
import string

# base62 문자 집합: [A-Za-z0-9]
ALPHABET = string.ascii_letters + string.digits
DEFAULT_LENGTH = 7

# 커스텀 별칭 허용 길이 범위.
CUSTOM_ALIAS_MIN_LENGTH = 4
CUSTOM_ALIAS_MAX_LENGTH = 32

# 프로덕션 기본값: 시드 불가능한 암호학적 난수원.
_DEFAULT_RNG = random.SystemRandom()


def generate_short_code(length: int = DEFAULT_LENGTH, *, rng: random.Random | None = None) -> str:
    """지정 길이의 무작위 base62 단축 코드를 반환한다.

    Args:
        length: 코드 길이(기본 7). 양수여야 한다.
        rng: 난수원. 테스트에서 `random.Random(seed)`를 주입하면 재현 가능.
             생략 시 암호학적으로 안전한 SystemRandom 사용.

    Raises:
        ValueError: length가 1 미만인 경우.
    """
    if length < 1:
        raise ValueError(f"length must be >= 1, got {length}")
    source = rng if rng is not None else _DEFAULT_RNG
    return "".join(source.choice(ALPHABET) for _ in range(length))


def is_valid_short_code(code: str) -> bool:
    """문자열이 base62 문자로만 구성된 비어있지 않은 코드인지 검사한다."""
    return len(code) > 0 and all(c in ALPHABET for c in code)


def is_valid_custom_alias(alias: str) -> bool:
    """사용자가 지정한 커스텀 별칭이 유효한지 검사한다.

    유효 조건: 길이 CUSTOM_ALIAS_MIN_LENGTH~CUSTOM_ALIAS_MAX_LENGTH + base62 문자만.
    """
    if not CUSTOM_ALIAS_MIN_LENGTH <= len(alias) <= CUSTOM_ALIAS_MAX_LENGTH:
        return False
    return all(c in ALPHABET for c in alias)
