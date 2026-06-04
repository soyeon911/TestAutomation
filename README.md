# URL Shortener CI

Jenkins 기반 테스트 자동화 파이프라인의 **검증 대상(SUT)** 인 FastAPI URL 단축 서비스.
전체 로드맵은 [`markdown/00overview.md`](markdown/00overview.md) 참고.

## 진행 상황

- [x] **Phase 0** — 타깃 앱 + 3계층 테스트 ([`markdown/01phase0_target_app.md`](markdown/01phase0_target_app.md))
- [x] **Phase 1** — Jenkins 컨트롤러 구동 (Docker) ([`markdown/02phase1jenkins_setup.md`](markdown/02phase1jenkins_setup.md))
- [x] **Phase 2** — 기본 파이프라인 (Jenkinsfile) ([`markdown/03phase2basic_pipeline.md`](markdown/03phase2basic_pipeline.md))
- [x] **Phase 3** — 품질 게이트 & 병렬화 ([`markdown/04phase3quality_gates.md`](markdown/04phase3quality_gates.md))
- [x] **Phase 4** — 리포트 & 트렌드 (JUnit·커버리지·Allure) ([`markdown/05phase4_reporting.md`](markdown/05phase4_reporting.md))
- [x] **Phase 5** — 자동 트리거 (Multibranch + 폴링/웹훅) ([`markdown/06phase5triggers.md`](markdown/06phase5triggers.md))
- [x] **Phase 6 · M3** — Shared Library로 파이프라인 추상화 ([`markdown/07phase6advanced.md`](markdown/07phase6advanced.md))

---

## Phase 0 — 애플리케이션

### 아키텍처
```
app/
├── main.py            # FastAPI 진입점 (lifespan에서 스키마 init)
├── api/routes.py      # 엔드포인트
├── core/shortcode.py  # 순수 로직 (base62 코드 생성, rng 주입으로 재현 가능)
├── db/
│   ├── models.py      # SQLAlchemy 2.x ORM (URLRecord)
│   ├── session.py     # 엔진·세션 (테스트 시 인메모리 교체)
│   └── repository.py  # 리포지토리 패턴 (save/get_by_code/increment_clicks)
└── schemas/url.py     # Pydantic v2 (HttpUrl 검증)

tests/{unit,integration,api}/   # 3계층
```

### 엔드포인트
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 헬스 체크 (스모크 테스트용) |
| POST | `/api/urls` | 단축 코드 발급 (201). 옵션: `custom_alias`(중복 409·형식 400), `expires_in_seconds`(TTL) |
| GET | `/api/urls` | 목록 조회 (`limit`·`offset` 페이지네이션, 최신순) |
| GET | `/api/urls/{code}` | 통계 조회 (`clicks`, `created_at`, `expires_at`) |
| DELETE | `/api/urls/{code}` | 삭제 (204 / 404) |
| GET | `/{code}` | 307 리다이렉트 + 클릭 수 증가. 만료 시 **410 Gone** |

> SUT 확장(2026-06): 커스텀 별칭·만료(TTL)·삭제·목록 기능을 추가하고, 각 기능의 정상/에러/경계
> 케이스 + Hypothesis 속성 기반 테스트를 더해 테스트가 **36 → 89개**(unit 50·integration 12·api 27),
> 커버리지 95%로 늘었다. 만료 비교를 위해 `UTCDateTime` 타입 데코레이터로 SQLite 왕복 시
> timezone-aware(UTC)를 보장한다.

### 로컬 실행 / 테스트
```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 앱 실행
uvicorn app.main:app --reload        # http://127.0.0.1:8000/docs

# 테스트 (3계층 전체)
pytest
pytest -m unit          # 계층별 선택 실행
pytest -m integration
pytest -m api

# 커버리지 (Phase 3에서 게이트화)
pytest --cov=app --cov-report=term-missing

# 린트·포맷·타입 (Phase 3에서 게이트화)
ruff check .
ruff format --check .
mypy app
```

---

## Phase 1 — Jenkins 컨트롤러 (Docker)

**방식 A(Docker 소켓 마운트)** — 컨트롤러가 호스트 Docker로 빌드 에이전트 컨테이너를 띄운다.
플러그인은 [`ci/Dockerfile.jenkins`](ci/Dockerfile.jenkins)에서 **이미지에 사전 설치**되고
설치 마법사는 비활성화되어, 첫 부팅 때 플러그인 다운로드가 필요 없다.

### 기동 / 정지
```bash
# 최초 또는 이미지(plugins.txt/Dockerfile) 변경 시 — 빌드 포함 기동
docker compose -f ci/docker-compose.yml up -d --build

# 이후 일반 기동
docker compose -f ci/docker-compose.yml up -d

# 웹 UI → http://localhost:8080  (설치 마법사 없이 대시보드로 바로 진입)

# 정지 (볼륨 jenkins_home 유지 → 설정·작업 보존)
docker compose -f ci/docker-compose.yml down

# 완전 초기화 (볼륨까지 삭제 — 설정 전부 소멸, 주의)
docker compose -f ci/docker-compose.yml down -v
```

### 플러그인 (F1-3)
[`ci/plugins.txt`](ci/plugins.txt)의 10개(+의존성)가 빌드 시 `jenkins-plugin-cli`로 사전 설치된다(현재 활성 114개):
Pipeline / Git / GitHub / Docker Pipeline / JUnit / Coverage / Allure / Warnings NG / Blue Ocean / Slack.

> **미러 우회**: 이 네트워크의 외부 IP가 Jenkins 미러 서비스에서 잘못 지오로케이션돼
> 플러그인 다운로드가 도달 불가한 중국 미러(tuna.tsinghua)로 리다이렉트된다.
> 그래서 Dockerfile에서 `JENKINS_UC_DOWNLOAD=https://archives.jenkins.io`로 고정해
> 미러 리다이렉트를 안 타고 `.hpi`를 직접 받는다.

### Docker 에이전트 검증 (완료 기준) ✅
```bash
docker exec jenkins-controller sh -c 'docker run --rm python:3.12-slim python --version'
# → Python 3.12.x 가 출력되면 방식 A 동작 (검증 완료)
```
컨테이너의 `jenkins` 유저가 마운트된 `docker.sock`(Docker Desktop에서 `root:root`)에 접근하도록
compose에 `group_add: ["0"]`을 둔다. Linux 호스트라면 `getent group docker`의 GID로 바꾼다.

### 보안 (학습용 기본값)
설치 마법사를 끄면서 보안 설정도 비활성(localhost 익명 접근)이다. 잠그려면
Manage Jenkins → Security 에서 인증/권한을 설정한다.

### 자격 증명 (F1-5)
GitHub 토큰·웹훅 시크릿·알림 웹훅은 Manage Jenkins → Credentials 에만 저장한다(코드/로그 노출 금지).

---

## Phase 2 — 기본 파이프라인 (Jenkinsfile)

저장소 루트 [`Jenkinsfile`](Jenkinsfile)에 Declarative 파이프라인을 정의한다. 전 stage가
`python:3.12-slim` 컨테이너(방식 A)에서 실행되어 "내 PC에선 됐는데" 문제를 제거한다.

```
Checkout (checkout scm)
  → Setup  (venv 생성 + pip install -e ".[dev]")
  → Test   (pytest --junitxml=reports/junit.xml --cov)
  → post   (junit 결과 등록 + reports 아카이브)
```

핵심 설계:
- **venv 격리 설치**: 에이전트는 uid 1000으로 실행돼 시스템 경로에 쓸 수 없으므로, 워크스페이스 안 `.venv`에 설치한다. pip 캐시(`.pip-cache`)는 빌드 간 재사용.
- **워크스페이스 공유**: docker-workflow 플러그인이 `--volumes-from <컨트롤러>`로 jenkins_home 볼륨을 에이전트에 공유 → 소켓 마운트 환경에서도 워크스페이스 경로가 일치.

### Jenkins 잡
"Pipeline script from SCM" 잡 `url-shortener-ci`가 GitHub repo(`*/main`, `Jenkinsfile`)를 가리킨다.
**"Build Now"** 로 수동 실행하면 위 stage가 순서대로 수행된다.
(잡 설정 참고: [`ci/jenkins-job-url-shortener-ci.xml`](ci/jenkins-job-url-shortener-ci.xml))

### GitHub Actions ↔ Jenkins 대응 (학습 노트)
| GitHub Actions | Jenkins (Declarative) |
|----------------|------------------------|
| `on: push` | 잡 트리거 / SCM 폴링 / 웹훅 (Phase 5) |
| `jobs:` | `stages { }` |
| `runs-on` / `container:` | `agent { docker { image } }` |
| `steps:` + `uses:` | `steps { }` + 플러그인 / `sh` |
| `actions/checkout` | `checkout scm` |
| `actions/upload-artifact` | `archiveArtifacts` |
| 테스트 리포트 액션 | `junit` 스텝 (Phase 2/4) |
| 러너(클라우드, GitHub 관리) | 에이전트(자체 호스팅 Docker) |

### 완료 기준 검증 ✅
- [x] 빌드가 `python:3.12-slim` 컨테이너에서 실행됨(로그의 `docker run ... python:3.12-slim` 확인).
- [x] pytest 통과(현재 89개), 빌드 페이지에 테스트 결과 표시(`junit` 등록).
- [x] 같은 커밋 재빌드 시 동일 결과(멱등성 — venv/캐시는 워크스페이스 격리).
- [x] 테스트를 깨뜨리면 종료 코드≠0 으로 stage 실패 → 빌드 빨간색.

---

## Phase 3 — 품질 게이트 & 병렬화

[`Jenkinsfile`](Jenkinsfile)을 확장해 **통과 기준이 있는 관문**으로 만든다. 설치(Setup) 후
4개 검사를 `parallel`로 동시에 실행하고, 하나라도 위반하면 빌드를 실패시킨다.

```
Checkout → Setup ──▶ Quality Gates (parallel, failFast=false)
                        ├─ Lint    : ruff check .
                        ├─ Format  : ruff format --check .
                        ├─ Type    : mypy app
                        └─ Test    : pytest --cov-fail-under=80
```

핵심 설계:
- **단일 설치 + 공유**: Setup에서 venv에 1회 설치 → 4개 병렬 stage가 같은 워크스페이스/venv를 공유(중복 `pip install` 방지). 도구는 `$VENV/bin/...` 절대경로로 호출.
- **failFast=false**: 하나가 실패해도 나머지를 끝까지 실행 → 모든 위반을 한 빌드에서 확인.
- **커버리지 게이트**: `--cov-fail-under=80`(환경변수 `COV_MIN`). 미달 시 pytest가 비0 종료 → 빌드 실패. 기준선은 단계적으로 상향 가능.
- **산출물 분리**: Test만 `reports/`에 junit/coverage XML 생성 → 병렬 stage 간 파일 충돌 없음.
- **검사만, 자동수정 아님**: `ruff format --check`로 확인만 한다. 수정은 로컬/pre-commit에서.

### 완료 기준 검증 ✅
- [x] 4개 게이트가 병렬 실행(Stage View / Blue Ocean에서 4갈래 확인).
- [x] 모든 게이트 통과 시에만 녹색 — 현재 lint/format/type 통과 + 커버리지 94.7%(≥80).
- [x] 병렬 stage 간 산출물 경로 충돌 없음.
- [ ] (수동 확인) 포맷/타입을 깨면 해당 게이트만 실패, 커버리지를 80% 미만으로 떨어뜨리면 실패.

> Warnings NG 경고 추이(F3-7)는 선택 항목으로, 차후 `recordIssues`로 ruff/mypy 결과를 시각화해 추가할 수 있다.

---

## Phase 4 — 리포트 & 트렌드 (JUnit · 커버리지 · Allure)

빌드 결과를 "통과/실패"를 넘어 **시각적 리포트와 추이**로 만든다. 파이프라인을 두 단계로 나눈다:

```
[Build & Quality Gates]  agent: python:3.12-slim (방식 A)
   Checkout → Setup → Quality Gates(병렬) → reports/ 생성 → stash
        │  pytest가 junit.xml + coverage.xml(Cobertura) + allure-results 생성
        ▼
[Report]  agent: 컨트롤러(JDK17 + Allure CLI 사전 설치)
   unstash → junit(트렌드) → recordCoverage(추이) → allure generate → publishHTML → archiveArtifacts
```

핵심 설계 (이 단계의 까다로운 부분 = 포트폴리오 포인트):
- **Java 분리**: Allure CLI는 Java가 필요한데 테스트 에이전트(`python:3.12-slim`)엔 Java가 없다. 그래서 **빌드/테스트는 docker 에이전트, 리포트 생성은 Java가 있는 컨트롤러**에서 하고, `reports/`를 `stash`/`unstash`로 넘긴다.
- **Allure CLI 사전 설치**: 설치된 Jenkins Allure 플러그인이 신버전(`org.allurereport`)이라 클래식 `allure` 스텝이 없다. 그래서 컨트롤러 이미지([`ci/Dockerfile.jenkins`](ci/Dockerfile.jenkins))에 Allure CLI를 직접 구워넣고 `allure generate`로 정적 HTML을 만든 뒤 **HTML Publisher**로 게시한다(미러 무관한 Maven Central에서 받음).
- **CSP 완화**: Jenkins 기본 CSP가 publishHTML로 게시한 Allure 리포트의 JS/CSS를 차단한다. localhost 학습용으로 `-Dhudson.model.DirectoryBrowserSupport.CSP=`로 완화([`ci/docker-compose.yml`](ci/docker-compose.yml)).
- **실패해도 리포트**: 각 게이트를 `catchError`로 감싸 위반 시 빌드는 빨갛게 표시하되 Report 단계까지 진행 → 실패 빌드의 결과도 본다.
- **결과 오염 방지**: Setup에서 `rm -rf reports`로 이전 빌드의 `allure-results` 잔재 제거.

### 완료 기준 검증 ✅
- [x] 테스트 결과 트렌드(`junit`, 89개), 커버리지 리포트+추이(`recordCoverage`, Cobertura) 생성.
- [x] **Allure 리포트 링크 생성·렌더링**(HTTP 200), 상세 결과 열림.
- [x] `reports/**`(junit/coverage/allure) 빌드 산출물로 다운로드 가능.
- [x] 빌드를 거듭하면 트렌드 그래프에 점이 누적.

---

## Phase 5 — 자동 트리거 (Multibranch + 폴링/웹훅)

"Build Now"를 사람이 누르는 대신, 코드 변경이 빌드를 자동으로 일으키게 한다.

> **환경 제약**: Jenkins가 `localhost:8080`이라 GitHub가 인터넷에서 직접 웹훅을 보낼 수 없다.
> 그래서 이 환경에서 실제 검증 가능한 트리거는 **Multibranch 주기 스캔**과 **SCM 폴링**이고,
> 진짜 웹훅은 터널(smee/ngrok)이 있어야 한다.

### Multibranch Pipeline (검증됨 ✅)
`url-shortener-mb` 잡(Multibranch)이 GitHub 저장소를 **Git branch source**로 스캔해
`Jenkinsfile`이 있는 브랜치를 자동 발견하고 각자 빌드한다. (설정: [`ci/jenkins-job-url-shortener-mb.xml`](ci/jenkins-job-url-shortener-mb.xml))

- **주기 스캔**: `H/2 * * * *`(2분) — 웹훅 없이도 새 커밋/브랜치를 발견해 빌드.
- **자동 트리거 확인**: `main`이 자동 발견되어 빌드됐고, 트리거 원인이 **"Branch indexing"**(사람이 누르지 않음).
- **공개 저장소**라 토큰 없이 `git ls-remote`로 브랜치 발견.
- **고아 정리**: 삭제된 브랜치의 잡은 자동 정리(orphaned item strategy).

**새 브랜치 자동 발견 테스트** (직접 해보기):
```bash
git switch -c feature/demo
git commit --allow-empty -m "trigger multibranch"
git push -u origin feature/demo
# → 2분 내 url-shortener-mb 에 feature%2Fdemo 잡이 자동 생성·빌드됨
#    (즉시 보려면 잡 페이지에서 "Scan Multibranch Pipeline Now")
```

### SCM 폴링 (단일 잡 대안)
단일 `url-shortener-ci` 잡을 자동화하려면 `Jenkinsfile`에 폴링 트리거를 추가한다:
```groovy
options { ... }
triggers { pollSCM('H/5 * * * *') }   // 5분마다 새 커밋 확인, 있으면 빌드
```
웹훅 없이 동작하지만 지연이 있다. (Multibranch 스캔과 역할이 겹치므로 둘 중 하나만)

### 웹훅 (프로덕션 방식 — 터널 필요)
push 즉시 빌드하려면 GitHub 웹훅을 쓴다. localhost는 도달 불가하므로 터널로 중계:
```bash
# smee.io 예시
npx smee-client -u https://smee.io/<your-channel> -t http://localhost:8080/github-webhook/
# 또는: ngrok http 8080  → 공인 URL 을 GitHub Settings→Webhooks 에 /github-webhook/ 로 등록
```

### 커밋 상태 보고 (선택)
빌드 결과를 GitHub 커밋/PR 체크로 표시하려면 **GitHub PAT**(repo + status 권한)를
Manage Jenkins → Credentials 에 등록하고 브랜치 소스를 GitHub source로 바꾼다.
브랜치 보호 규칙의 "상태 통과 필수"와 결합하면 통과해야 머지되는 흐름이 된다.

### 완료 기준 검증
- [x] Multibranch가 `main`을 자동 발견·빌드(트리거 원인 "Branch indexing").
- [x] 주기 스캔으로 사람이 누르지 않아도 빌드 시작.
- [ ] (직접) `feature/*` push 시 자동 발견 — 위 절차로 확인.
- [ ] (선택) 웹훅(터널)으로 push 즉시 빌드 / 커밋 상태 표시.

---

## Phase 6 · M3 — Shared Library (파이프라인 추상화)

문서가 포트폴리오 가치 1순위로 꼽은 모듈. 표준 CI 절차를 **공유 라이브러리**로 추출해
`Jenkinsfile`을 **두 줄**로 만들었다("파이프라인을 추상화·재사용했다"는 설계 역량 증명).

**Before (Phase 4·5)**: `Jenkinsfile`에 ~90줄의 선언적 파이프라인.
**After (M3)**:
```groovy
@Library('url-shortener-shared@main') _
pythonCI(image: 'python:3.12-slim', covMin: 80)
```

- 표준 절차는 [`jenkins/shared-library/vars/pythonCI.groovy`](jenkins/shared-library/vars/pythonCI.groovy)에 캡슐화.
- 전역 라이브러리 등록은 [`ci/configure-shared-library.groovy`](ci/configure-shared-library.groovy)로 **코드화**(Library Path = `jenkins/shared-library` 서브디렉터리).
- **구조 개선**: scripted로 단일 `node`에서 `docker.inside`(방식 A) 빌드 → 같은 워크스페이스를 컨트롤러가 읽어 리포트 → Phase 4의 `stash`/`unstash`가 불필요해져 더 단순해졌다. 커버리지 소스 페인팅도 워크스페이스에 소스가 있어 정상 동작.
- 파라미터(`image`, `covMin`)로 다른 Python 프로젝트가 동일 표준을 재사용 가능. (확장: `pythonCI`에 버전 리스트를 받아 M2 매트릭스로 발전 가능.)

> 검증: CI 로직은 동등한 인라인 scripted 파이프라인으로 녹색 확인(89 passed·커버리지·Allure). 라이브러리는 GitHub `main`의 `jenkins/shared-library`에서 로드되므로, 이 변경을 push한 뒤 `url-shortener-ci`/`url-shortener-mb` 빌드로 최종 확인한다.

### 완료 기준 (M3)
- [x] `Jenkinsfile`이 공유 라이브러리 호출로 간결해짐(2줄).
- [x] 동일 라이브러리를 다른 프로젝트가 재사용 가능(파라미터화).
- [ ] (push 후) 라이브러리를 불러 빌드가 녹색.

---

## 설계 결정
- **3계층 분리**: 순수 로직(`core`)을 DB에서 떼어내 단위 테스트를 빠르고 결정적으로 유지. 코드 생성기는 `rng` 주입으로 시드 고정 재현이 가능.
- **리포지토리 패턴**: API 라우터가 ORM에 직접 의존하지 않게 분리. 테스트에서 인메모리 SQLite로 교체.
- **테스트 격리**: `conftest.py`가 테스트마다 새 인메모리 엔진을 만들고 종료 시 drop → 상태 누수 없음(멱등성).
- **Jenkins 방식 A**: 소켓 마운트로 호스트 Docker를 사용해 빌드를 격리·재현. 실무·포트폴리오 가치가 높음.
- **설정 일원화**: ruff·mypy·pytest·coverage 설정을 모두 `pyproject.toml`에 둠.
