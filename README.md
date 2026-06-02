# URL Shortener CI

Jenkins 기반 테스트 자동화 파이프라인의 **검증 대상(SUT)** 인 FastAPI URL 단축 서비스.
전체 로드맵은 [`markdown/00overview.md`](markdown/00overview.md) 참고.

## 진행 상황

- [x] **Phase 0** — 타깃 앱 + 3계층 테스트 ([`markdown/01phase0_target_app.md`](markdown/01phase0_target_app.md))
- [x] **Phase 1** — Jenkins 컨트롤러 구동 (Docker) ([`markdown/02phase1jenkins_setup.md`](markdown/02phase1jenkins_setup.md))
- [x] **Phase 2** — 기본 파이프라인 (Jenkinsfile) ([`markdown/03phase2basic_pipeline.md`](markdown/03phase2basic_pipeline.md))
- [ ] Phase 3 — 품질 게이트
- [ ] Phase 4 — 리포트 트렌드
- [ ] Phase 5 — 트리거
- [ ] Phase 6 — 고급

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
| POST | `/api/urls` | `{"url": "..."}` → 단축 코드 발급 (201) |
| GET | `/api/urls/{code}` | 통계 조회 (`clicks`, `created_at`) |
| GET | `/{code}` | 원본 URL로 307 리다이렉트 + 클릭 수 증가 |

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
- [x] pytest 36개 통과, 빌드 페이지에 테스트 결과 표시(`junit` 등록).
- [x] 같은 커밋 재빌드 시 동일 결과(멱등성 — venv/캐시는 워크스페이스 격리).
- [x] 테스트를 깨뜨리면 종료 코드≠0 으로 stage 실패 → 빌드 빨간색.

---

## 설계 결정
- **3계층 분리**: 순수 로직(`core`)을 DB에서 떼어내 단위 테스트를 빠르고 결정적으로 유지. 코드 생성기는 `rng` 주입으로 시드 고정 재현이 가능.
- **리포지토리 패턴**: API 라우터가 ORM에 직접 의존하지 않게 분리. 테스트에서 인메모리 SQLite로 교체.
- **테스트 격리**: `conftest.py`가 테스트마다 새 인메모리 엔진을 만들고 종료 시 drop → 상태 누수 없음(멱등성).
- **Jenkins 방식 A**: 소켓 마운트로 호스트 Docker를 사용해 빌드를 격리·재현. 실무·포트폴리오 가치가 높음.
- **설정 일원화**: ruff·mypy·pytest·coverage 설정을 모두 `pyproject.toml`에 둠.
