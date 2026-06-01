# 00 · 프로젝트 개요 (Master Spec)

## 1. 프로젝트 한 줄 정의
Jenkins 기반 테스트 자동화 파이프라인을 구축하고, 그 검증 대상(SUT)으로 직접 만든 Python(FastAPI) URL 단축 서비스를 사용한다. GitHub Actions로 이미 해본 테스트 자동화를, 자체 호스팅·플러그인·에이전트 개념이 있는 Jenkins로 재구성하며 차이를 체득하는 것이 핵심 목표다.

## 2. 목표
- **포트폴리오**: 단위/통합/API 테스트가 모두 존재하는 실제적 서비스 + 품질 게이트가 있는 파이프라인 + 시각적 리포트 트렌드.
- **실무 적용 준비**: 커버리지 게이트, 병렬 stage, Docker 에이전트, 웹훅 트리거, 알림 등 실무 파이프라인 구성 요소를 직접 다룬다.

## 3. 기술 스택 (확정)
| 영역 | 선택 | 비고 |
|------|------|------|
| 언어 | Python 3.12 | 다중 버전 매트릭스는 Phase 6 |
| 웹 프레임워크 | FastAPI | TestClient로 API 테스트 용이 |
| 데이터 검증 | Pydantic v2 | URL 검증에 활용 |
| 영속성 | SQLite + SQLAlchemy 2.x | 테스트 시 인메모리로 교체 |
| 테스트 러너 | pytest | 코어 |
| 커버리지 | pytest-cov | XML/HTML 리포트 |
| 린트·포맷 | ruff | lint + format 통합 |
| 타입 체크 | mypy | |
| 다중 환경 | tox 또는 nox | Phase 6 |
| 리포트 | Allure + JUnit XML | Jenkins 플러그인 연동 |
| 보안 스캔 | bandit | 선택 |
| CI/CD | Jenkins LTS (Docker) | 자체 호스팅 |
| 빌드 에이전트 | Docker (`python:3.12-slim`) | 컨트롤러 오염 방지 |

## 4. 문서 ↔ 로드맵 단계 매핑
| 문서 | 로드맵 단계 | 한 줄 요약 |
|------|------------|-----------|
| `01phase0target_app.md` | Phase 0 | 검증 대상 FastAPI 앱 + 3계층 테스트 |
| `02phase1jenkins_setup.md` | Phase 1 | Docker로 Jenkins 컨트롤러 구동·플러그인 |
| `03phase2basic_pipeline.md` | Phase 2 | 체크아웃→설치→pytest 기본 파이프라인 |
| `04phase3quality_gates.md` | Phase 3 | 린트·타입·커버리지 게이트 + 병렬화 |
| `05phase4reporting.md` | Phase 4 | JUnit·커버리지·Allure 리포트 트렌드 |
| `06phase5triggers.md` | Phase 5 | 웹훅/Multibranch 자동 트리거 |
| `07phase6advanced.md` | Phase 6 | Docker 에이전트·매트릭스·공유 라이브러리·알림·배포 |

각 문서는 **개요 / 선행 조건 / 구현 기능 / 기능별 상세 동작 / 산출물 / 완료 기준 / 함정** 형식을 공통으로 따른다. 한 단계의 "완료 기준"을 모두 충족해야 다음 단계로 넘어간다.

## 5. 권장 저장소 구조 (최종 형태)
```
url-shortener-ci/
├── app/                      # FastAPI 애플리케이션 (Phase 0)
│   ├── main.py               # 앱 진입점, 라우터 등록
│   ├── api/                  # 라우터 (엔드포인트)
│   ├── core/                 # 단축 코드 생성·검증 등 순수 로직
│   ├── db/                   # 세션, 모델, 리포지토리
│   └── schemas/              # Pydantic 모델
├── tests/
│   ├── unit/                 # 순수 로직 (DB·네트워크 없음)
│   ├── integration/          # 리포지토리 + DB
│   └── api/                  # TestClient 엔드포인트
├── reports/                  # junit.xml, coverage.xml, allure 결과 (gitignore)
├── ci/
│   ├── Dockerfile.jenkins    # Python 포함 커스텀 Jenkins 이미지 (선택)
│   └── docker-compose.yml    # Jenkins 구동 (Phase 1)
├── jenkins/
│   └── shared-library/       # 공유 라이브러리 (Phase 6)
├── Jenkinsfile               # 파이프라인 정의 (Phase 2~6에서 점진적 확장)
├── pyproject.toml            # 의존성·ruff·mypy·pytest·coverage 설정 일원화
├── tox.ini                   # 다중 환경 (Phase 6)
└── docs/                     # 본 구현 문서들
```

## 6. 공통 규칙 (Conventions)
- **브랜치**: `main`(보호) + `feature/*`. 각 단계는 별도 feature 브랜치에서 작업 후 PR/머지.
- **설정 일원화**: ruff·mypy·pytest·coverage 설정은 모두 `pyproject.toml`에 둔다(파일 분산 금지).
- **커버리지 기준선**: Phase 3에서 80%로 시작, 단계가 올라갈수록 상향 가능.
- **테스트 명명**: `test_<대상>_<상황>_<기대결과>` 형식 권장.
- **파이프라인 멱등성**: 어떤 stage든 재실행 시 동일 결과가 나와야 한다(상태 누수 금지).
- **비밀값**: GitHub 토큰·웹훅 시크릿 등은 Jenkins Credentials에만 저장(코드/로그 노출 금지).

## 7. 진행 방식
필요한 단계의 문서를 그대로 전달하면 해당 문서의 "구현 기능 / 산출물 / 완료 기준"에 따라 코드를 작성한다. 한 번에 한 단계씩 진행하는 것을 권장한다.