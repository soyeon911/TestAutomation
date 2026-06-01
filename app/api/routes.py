"""HTTP 엔드포인트. TestClient 기반 api 테스트(tests/api)의 대상이다."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.shortcode import generate_short_code
from app.db.models import URLRecord
from app.db.repository import URLRepository
from app.db.session import get_session
from app.schemas.url import URLCreateRequest, URLCreateResponse, URLStats

router = APIRouter()

_MAX_CODE_ATTEMPTS = 5


def get_repository(session: Session = Depends(get_session)) -> URLRepository:
    return URLRepository(session)


@router.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """헬스 체크 — 파이프라인 스모크 테스트용."""
    return {"status": "ok"}


@router.post(
    "/api/urls",
    response_model=URLCreateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["urls"],
)
def create_url(
    payload: URLCreateRequest,
    request: Request,
    repo: URLRepository = Depends(get_repository),
) -> URLCreateResponse:
    """원본 URL을 받아 단축 코드를 발급한다 (F0-1)."""
    original_url = str(payload.url)

    # 코드 충돌 시 재생성(F0-1 step 4).
    for _ in range(_MAX_CODE_ATTEMPTS):
        code = generate_short_code()
        if repo.get_by_code(code) is None:
            record = repo.save(URLRecord(short_code=code, original_url=original_url))
            short_url = str(request.base_url).rstrip("/") + "/" + record.short_code
            return URLCreateResponse(
                short_code=record.short_code,
                short_url=short_url,
                original_url=record.original_url,
            )
    raise HTTPException(status_code=500, detail="failed to generate a unique short code")


@router.get("/api/urls/{short_code}", response_model=URLStats, tags=["urls"])
def get_stats(
    short_code: str,
    repo: URLRepository = Depends(get_repository),
) -> URLStats:
    """단축 코드의 통계/메타데이터를 조회한다 (F0-3, 리다이렉트 없음)."""
    record = repo.get_by_code(short_code)
    if record is None:
        raise HTTPException(status_code=404, detail="short code not found")
    return URLStats.model_validate(record)


@router.get("/{short_code}", tags=["urls"])
def redirect(
    short_code: str,
    repo: URLRepository = Depends(get_repository),
) -> RedirectResponse:
    """단축 코드를 원본 URL로 리다이렉트하고 클릭 수를 증가시킨다 (F0-2).

    클릭 수 증가는 리다이렉션 응답 전에 반영된다(통계 정확성).
    """
    record = repo.increment_clicks(short_code)
    if record is None:
        raise HTTPException(status_code=404, detail="short code not found")
    return RedirectResponse(url=record.original_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
