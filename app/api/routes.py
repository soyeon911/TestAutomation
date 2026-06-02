"""HTTP 엔드포인트. TestClient 기반 api 테스트(tests/api)의 대상이다."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.expiry import compute_expires_at, is_expired
from app.core.shortcode import generate_short_code, is_valid_custom_alias
from app.db.models import URLRecord
from app.db.repository import URLRepository
from app.db.session import get_session
from app.schemas.url import URLCreateRequest, URLCreateResponse, URLStats

router = APIRouter()

_MAX_CODE_ATTEMPTS = 5


def get_repository(session: Session = Depends(get_session)) -> URLRepository:
    return URLRepository(session)


def _build_short_url(request: Request, short_code: str) -> str:
    return str(request.base_url).rstrip("/") + "/" + short_code


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
    """원본 URL을 받아 단축 코드를 발급한다.

    - custom_alias 지정 시: 형식 검증(400) + 중복 검사(409).
    - expires_in_seconds 지정 시: 만료 시각을 계산해 저장.
    """
    original_url = str(payload.url)
    created_at = datetime.now(UTC)
    expires_at = compute_expires_at(created_at, payload.expires_in_seconds)

    if payload.custom_alias is not None:
        # 사용자가 코드를 직접 지정한 경우.
        if not is_valid_custom_alias(payload.custom_alias):
            raise HTTPException(status_code=400, detail="invalid custom_alias format")
        if repo.get_by_code(payload.custom_alias) is not None:
            raise HTTPException(status_code=409, detail="custom_alias already in use")
        record = repo.save(
            URLRecord(
                short_code=payload.custom_alias,
                original_url=original_url,
                created_at=created_at,
                expires_at=expires_at,
            )
        )
        return URLCreateResponse(
            short_code=record.short_code,
            short_url=_build_short_url(request, record.short_code),
            original_url=record.original_url,
            expires_at=record.expires_at,
        )

    # 자동 생성: 코드 충돌 시 재생성.
    for _ in range(_MAX_CODE_ATTEMPTS):
        code = generate_short_code()
        if repo.get_by_code(code) is None:
            record = repo.save(
                URLRecord(
                    short_code=code,
                    original_url=original_url,
                    created_at=created_at,
                    expires_at=expires_at,
                )
            )
            return URLCreateResponse(
                short_code=record.short_code,
                short_url=_build_short_url(request, record.short_code),
                original_url=record.original_url,
                expires_at=record.expires_at,
            )
    raise HTTPException(status_code=500, detail="failed to generate a unique short code")


@router.get("/api/urls", response_model=list[URLStats], tags=["urls"])
def list_urls(
    repo: URLRepository = Depends(get_repository),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[URLStats]:
    """등록된 단축 URL을 최신순으로 페이지네이션해 조회한다."""
    records = repo.list_records(limit=limit, offset=offset)
    return [URLStats.model_validate(r) for r in records]


@router.get("/api/urls/{short_code}", response_model=URLStats, tags=["urls"])
def get_stats(
    short_code: str,
    repo: URLRepository = Depends(get_repository),
) -> URLStats:
    """단축 코드의 통계/메타데이터를 조회한다 (리다이렉트 없음)."""
    record = repo.get_by_code(short_code)
    if record is None:
        raise HTTPException(status_code=404, detail="short code not found")
    return URLStats.model_validate(record)


@router.delete("/api/urls/{short_code}", status_code=status.HTTP_204_NO_CONTENT, tags=["urls"])
def delete_url(
    short_code: str,
    repo: URLRepository = Depends(get_repository),
) -> None:
    """단축 코드를 삭제한다. 없으면 404."""
    if not repo.delete(short_code):
        raise HTTPException(status_code=404, detail="short code not found")


@router.get("/{short_code}", tags=["urls"])
def redirect(
    short_code: str,
    repo: URLRepository = Depends(get_repository),
) -> RedirectResponse:
    """단축 코드를 원본 URL로 리다이렉트하고 클릭 수를 증가시킨다.

    - 없는 코드: 404.
    - 만료된 코드: 410 Gone (클릭 수 증가 안 함).
    - 정상: 클릭 수 증가 후 307 리다이렉트.
    """
    record = repo.get_by_code(short_code)
    if record is None:
        raise HTTPException(status_code=404, detail="short code not found")
    if is_expired(record.expires_at, datetime.now(UTC)):
        raise HTTPException(status_code=410, detail="short code has expired")
    repo.increment_clicks(short_code)
    return RedirectResponse(url=record.original_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
