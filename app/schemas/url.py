"""URL 단축 서비스의 요청/응답 Pydantic 모델 (Pydantic v2).

F0-5: HttpUrl 타입으로 스킴(http/https)·형식을 검증한다.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl

from app.core.expiry import MAX_TTL_SECONDS


class URLCreateRequest(BaseModel):
    """URL 등록 요청 본문 (F0-1)."""

    url: HttpUrl = Field(..., description="단축할 원본 URL (http/https)")
    custom_alias: str | None = Field(
        default=None, description="원하는 커스텀 단축 코드(미지정 시 자동 생성)"
    )
    expires_in_seconds: int | None = Field(
        default=None,
        ge=1,
        le=MAX_TTL_SECONDS,
        description="만료까지 초(미지정 시 만료 없음)",
    )


class URLCreateResponse(BaseModel):
    """URL 등록 응답 본문 (F0-1)."""

    short_code: str = Field(..., description="발급된 단축 코드")
    short_url: str = Field(..., description="http://<host>/<code> 형태의 단축 URL")
    original_url: str = Field(..., description="원본 URL")
    expires_at: datetime | None = Field(default=None, description="만료 시각(없으면 null)")


class URLStats(BaseModel):
    """통계 조회 응답 본문 (F0-3)."""

    short_code: str
    original_url: str
    clicks: int = Field(ge=0)
    created_at: datetime
    expires_at: datetime | None = None

    model_config = {"from_attributes": True}
