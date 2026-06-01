# 02 · Phase 1 — Jenkins 컨트롤러 구동 (Docker)

## 개요
자체 호스팅 Jenkins 컨트롤러를 Docker로 띄운다. GitHub Actions와의 첫 번째 본질적 차이가 여기다 — 러너 인프라를 내가 운영한다. 이후 단계의 파이프라인이 Docker 에이전트(`python:3.12-slim`)에서 실행되도록, 컨트롤러가 호스트 Docker를 쓸 수 있게 구성하는 것까지가 이 단계의 범위다.

## 선행 조건
- 호스트에 Docker / Docker Compose 설치.
- Phase 0 저장소가 Git 원격(GitHub)에 올라가 있으면 좋음(필수는 아님; Phase 2부터 필요).

## 구현 기능
1. Jenkins 컨트롤러 컨테이너 구동 (영속 볼륨)
2. 초기 설정 (admin 계정, 권장 플러그인)
3. 프로젝트 전용 플러그인 설치
4. Docker 에이전트 사용 가능하도록 Docker 접근 구성
5. 자격 증명(Credentials) 등록 준비

## 기능별 상세 동작

### F1-1. 컨트롤러 구동 (`ci/docker-compose.yml`)
- 이미지: `jenkins/jenkins:lts-jdk17`.
- 포트: `8080`(웹 UI), `50000`(인바운드 에이전트).
- 볼륨: `jenkins_home`을 명명 볼륨으로 영속화(컨테이너 재생성에도 설정 유지).
- 재시작 정책: `unless-stopped`.
- **동작 검증**: `http://localhost:8080` 접속 시 초기 설정 화면이 뜬다.

### F1-2. 초기 설정
- 초기 admin 비밀번호 확인:
  - `docker exec <container> cat /var/jenkins_home/secrets/initialAdminPassword`
- "Install suggested plugins" 선택.
- admin 사용자 생성(아이디/비밀번호 기록은 Credentials 매니저나 안전한 곳에).
- Jenkins URL을 `http://localhost:8080`으로 설정.

### F1-3. 프로젝트 전용 플러그인
다음 플러그인을 설치한다(이후 단계에서 사용):
- **Pipeline** (suggested에 포함) — Jenkinsfile 파이프라인.
- **Git / GitHub** — SCM 연동, 커밋 상태 보고(Phase 5).
- **Docker Pipeline** — `agent { docker { ... } }` 사용(Phase 2~).
- **JUnit** — 테스트 결과 트렌드(Phase 2/4).
- **Coverage** (Code Coverage API) — 커버리지 트렌드(Phase 4).
- **Allure** — Allure 리포트(Phase 4).
- **Warnings Next Generation** — ruff/mypy 경고 집계(Phase 3).
- **Blue Ocean** (선택) — 파이프라인 시각화.
- **Slack Notification** 또는 Discord 연동(Phase 6).

### F1-4. Docker 에이전트 사용 구성 (중요)
이후 파이프라인은 컨트롤러를 더럽히지 않기 위해 Docker 컨테이너 안에서 실행한다. 두 가지 방식 중 하나를 택한다.

- **방식 A (권장 시작점) — Docker 소켓 마운트**: compose에서 호스트의 `/var/run/docker.sock`을 컨트롤러에 마운트하고, 컨테이너 내부에 docker CLI를 둔다. 그러면 파이프라인이 호스트 Docker로 `python:3.12-slim` 컨테이너를 띄워 빌드한다.
  - 장점: 단순, 문서 풍부. 단점: 소켓 마운트는 권한이 넓다(학습 환경에선 수용 가능).
- **방식 B — Python 포함 커스텀 Jenkins 이미지(`ci/Dockerfile.jenkins`)**: `jenkins/jenkins:lts` 위에 Python 3.12를 설치해 컨트롤러에서 직접 pytest를 돌린다.
  - 장점: 소켓 불필요. 단점: 컨트롤러 오염, 다중 버전 매트릭스(Phase 6) 확장성 낮음.

**결정**: 방식 A를 기본으로 한다(실무·포트폴리오 가치가 높음). 방식 B는 fallback으로 문서에 남겨둔다.

### F1-5. Credentials 등록 준비
- GitHub 접근용 토큰, 웹훅 시크릿(Phase 5), 알림 웹훅(Phase 6)을 저장할 자리만 미리 확인.
- 이 단계에서는 등록 위치(Manage Jenkins → Credentials)만 숙지하면 됨.

## 산출물
- `ci/docker-compose.yml` (컨트롤러 정의, 볼륨, 포트, 소켓 마운트).
- (방식 B 선택 시) `ci/Dockerfile.jenkins`.
- `docs` 또는 README에 "Jenkins 기동/정지/초기 비밀번호 확인" 절차 기록.

## 완료 기준 (Definition of Done)
- [ ] `docker compose up -d` 후 `http://localhost:8080`에서 로그인 가능.
- [ ] 컨테이너를 재생성해도 설정(작업·플러그인)이 유지됨(볼륨 영속 확인).
- [ ] F1-3 플러그인이 모두 설치됨.
- [ ] 파이프라인에서 `sh 'docker run --rm python:3.12-slim python --version'`이 성공(방식 A 검증) 또는 컨트롤러에서 `python --version` 성공(방식 B).

## 함정 / 주의
- **권한**: 소켓 마운트 시 Jenkins 컨테이너 사용자가 docker 그룹/소켓에 접근 가능해야 한다(권한 오류 빈번).
- **데이터 유실**: 볼륨을 명명 볼륨이 아닌 익명/바인드로 잘못 잡으면 재생성 시 설정이 날아간다.
- **플러그인 버전 호환**: LTS 라인과 플러그인 버전이 안 맞으면 경고가 뜬다. 가능하면 한 번에 최신으로 맞춘다.
- **포트 충돌**: 8080이 이미 점유돼 있으면 호스트 포트를 변경한다(예: `8081:8080`).