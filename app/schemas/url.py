"""URL 단축 서비스의 요청/응답 Pydantic 모델 (Pydantic v2).

F0-5: HttpUrl 타입으로 스킴(http/https)·형식을 검증한다.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class URLCreateRequest(BaseModel):
    """URL 등록 요청 본문 (F0-1)."""

    url: HttpUrl = Field(..., description="단축할 원본 URL (http/https)")


class URLCreateResponse(BaseModel):
    """URL 등록 응답 본문 (F0-1)."""

    short_code: str = Field(..., description="발급된 단축 코드")
    short_url: str = Field(..., description="http://<host>/<code> 형태의 단축 URL")
    original_url: str = Field(..., description="원본 URL")


class URLStats(BaseModel):
    """통계 조회 응답 본문 (F0-3)."""

    short_code: str
    original_url: str
    clicks: int = Field(ge=0)
    created_at: datetime

    model_config = {"from_attributes": True}
