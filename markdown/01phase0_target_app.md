# 01 · Phase 0 — 검증 대상 애플리케이션 (URL 단축 서비스)

## 개요
파이프라인이 검증할 대상(SUT, System Under Test)을 만든다. 작지만 **단위·통합·API** 세 층위의 테스트를 모두 자연스럽게 보여줄 수 있는 FastAPI URL 단축 서비스를 구현한다. 이 단계의 목표는 "테스트하기 좋은 구조"를 만드는 것이지, 화려한 기능이 아니다.

## 선행 조건
- 없음 (프로젝트 시작점)
- 로컬에 Python 3.12, `pip`/`venv` 사용 가능

## 구현 기능
1. URL 등록 API
2. 리디렉션 API
3. 통계 조회 API
4. 단축 코드 생성 로직 (순수 함수)
5. URL 검증 로직
6. 영속성 계층 (리포지토리 패턴, 테스트 시 교체 가능)
7. 3계층 테스트 스위트

## 기능별 상세 동작

### F0-1. URL 등록 — `POST /api/urls`
- **요청 본문**: `{ "url": "<원본 URL>" }`
- **동작**:
  1. Pydantic이 `url` 필드를 `HttpUrl`로 검증한다.
  2. 유효하면 단축 코드를 생성한다(F0-4).
  3. (원본 URL, 코드, 생성 시각, 클릭 수=0)를 저장한다(F0-6).
  4. 동일 코드가 이미 존재하면 재생성한다(충돌 처리).
- **응답**: `201 Created`, 본문 `{ "short_code": "...", "short_url": "http://<host>/<code>", "original_url": "..." }`
- **검증 실패**: 잘못된 URL → `422 Unprocessable Entity` (FastAPI 기본 검증 응답).

### F0-2. 리디렉션 — `GET /{short_code}`
- **동작**:
  1. 코드로 원본 URL을 조회한다.
  2. 존재하면 클릭 수를 1 증가시키고 원본 URL로 리디렉션한다.
  3. 존재하지 않으면 `404 Not Found`.
- **응답**: 존재 시 `307 Temporary Redirect`(`Location` 헤더에 원본 URL). 없으면 `404`.
- **주의**: 클릭 수 증가는 리디렉션 응답 전에 반영되어야 한다(통계 정확성).

### F0-3. 통계 조회 — `GET /api/urls/{short_code}`
- **동작**: 코드로 레코드를 조회해 메타데이터를 반환한다.
- **응답**: `200 OK`, `{ "short_code": "...", "original_url": "...", "clicks": <int>, "created_at": "<ISO8601>" }`. 없으면 `404`.

### F0-4. 단축 코드 생성 (순수 함수, `app/core/`)
- **입력**: 길이(기본 7), 문자 집합(base62: `[A-Za-z0-9]`).
- **동작**: 지정 길이의 무작위 base62 문자열을 반환한다. 외부 의존성(DB·시간) 없이 동작해야 단위 테스트가 가능하다.
- **검증 포인트(단위 테스트 대상)**: 반환 길이, 허용 문자만 포함, 난수 시드 고정 시 재현성.

### F0-5. URL 검증 (`app/schemas/`)
- Pydantic 모델에서 `HttpUrl` 타입으로 스킴(http/https)·형식을 검증한다.
- **검증 포인트**: 스킴 없는 문자열, 빈 문자열, 비-URL 텍스트는 거부.

### F0-6. 영속성 계층 (리포지토리 패턴, `app/db/`)
- `UrlRepository` 인터페이스: `save(record)`, `get_by_code(code)`, `increment_clicks(code)`.
- 기본 구현은 SQLAlchemy + SQLite 파일 DB.
- **핵심 요구사항**: FastAPI 의존성 주입(`Depends`)으로 세션/리포지토리를 주입해, **테스트에서 인메모리 SQLite로 손쉽게 교체**할 수 있어야 한다. 이 교체 가능성이 통합·API 테스트의 전제다.

### F0-7. 테스트 스위트 (3계층)
- **`tests/unit/`** — DB·네트워크 없이 동작.
  - 코드 생성기: 길이·문자집합·재현성.
  - URL 검증: 유효/무효 케이스 파라미터화(`@pytest.mark.parametrize`).
- **`tests/integration/`** — 인메모리 SQLite로 실제 리포지토리 검증.
  - `save` 후 `get_by_code`로 동일 레코드 반환.
  - `increment_clicks` 호출 시 클릭 수 정확히 증가.
  - 없는 코드 조회 시 `None`/예외 처리.
- **`tests/api/`** — `fastapi.testclient.TestClient` + 의존성 오버라이드로 인메모리 DB 사용.
  - F0-1: 유효 URL 등록 → 201 + 코드 반환.
  - F0-1: 잘못된 URL → 422.
  - F0-2: 등록된 코드 → 307 + 올바른 `Location`.
  - F0-2: 없는 코드 → 404.
  - F0-2 후 F0-3: 리디렉션 1회 후 통계 clicks == 1.

## 산출물
- `app/` 하위 애플리케이션 코드 (main, api, core, db, schemas).
- `tests/unit`, `tests/integration`, `tests/api` 테스트.
- `pyproject.toml`: 의존성 + pytest/coverage/ruff/mypy 설정 골격.
- `requirements.txt` 또는 `pyproject` 의존성 그룹.
- `README.md`: 로컬 실행·테스트 방법.

## 완료 기준 (Definition of Done)
- [ ] `uvicorn app.main:app`으로 앱이 기동되고 세 엔드포인트가 수동 호출로 동작.
- [ ] `pytest`가 로컬에서 전부 통과.
- [ ] `pytest --cov=app`으로 커버리지 측정이 되고, 라인 커버리지 80% 이상.
- [ ] 단위 테스트가 DB 없이 독립 실행됨(네트워크/파일 의존 없음).
- [ ] API 테스트가 의존성 오버라이드로 인메모리 DB를 사용(실제 파일 DB 미사용).
- [ ] `ruff check .`, `ruff format --check .`, `mypy app` 통과(설정은 최소 수준이라도).

## 함정 / 주의
- **상태 누수**: 테스트 간 DB가 공유되면 클릭 수 테스트가 깨진다. fixture에서 매 테스트마다 새 인메모리 DB를 만들고 정리한다.
- **시간 의존성**: `created_at`을 직접 비교하지 말고 "존재 여부/타입"만 검증하거나 시간을 주입 가능하게 한다.
- **난수 의존성**: 코드 생성 단위 테스트는 시드를 고정하거나 속성(길이·문자집합)만 검증한다.
- **과설계 금지**: 인증·캐시·레이트리밋 등은 넣지 않는다. 테스트 계층을 보여주는 게 목적이다.