# 03 · Phase 2 — 기본 파이프라인 (체크아웃 → 설치 → 테스트)

## 개요
Declarative Jenkinsfile로 최소 파이프라인을 만든다. 목표는 "코드 변경 → 자동으로 의존성 설치 → pytest 실행 → 결과 수집"의 한 사이클을 Jenkins에서 완성하는 것이다. GitHub Actions의 workflow/job/step이 Jenkins의 pipeline/stage/step과 어떻게 대응되는지 직접 비교한다.

## 선행 조건
- Phase 0 완료(테스트가 로컬에서 통과).
- Phase 1 완료(Jenkins 구동 + Docker 에이전트 사용 가능).
- 저장소가 GitHub에 push 되어 있음.

## 구현 기능
1. Declarative Pipeline 골격 (`Jenkinsfile`)
2. Docker 에이전트 지정
3. Checkout stage
4. Setup(의존성 설치) stage
5. Test stage (pytest + JUnit XML)
6. 결과 수집 (post 처리)
7. Jenkins Pipeline 작업(Job) 생성·연결

## 기능별 상세 동작

### F2-1. 파이프라인 골격
- `Jenkinsfile`을 저장소 루트에 둔다.
- `pipeline { agent ... ; options ... ; stages { ... } ; post { ... } }` 구조.
- `options`: `timeout`(예: 20분), `timestamps()`, 빌드 보존 개수 제한.

### F2-2. Docker 에이전트
- `agent { docker { image 'python:3.12-slim' } }` 형태로 전 stage를 Python 컨테이너에서 실행.
- 필요 시 `args`로 캐시 디렉터리 마운트(pip 캐시)로 속도 개선.
- **동작**: 각 빌드가 깨끗한 컨테이너에서 시작 → 환경 오염·"내 PC에선 됐는데" 문제 제거.

### F2-3. Checkout
- 멀티브랜치 전이라면 `checkout scm` 사용.
- 단일 작업이면 Git 설정에서 저장소 URL/브랜치 지정.
- **동작**: 트리거된 커밋의 소스를 워크스페이스로 가져온다.

### F2-4. Setup (의존성 설치)
- 컨테이너 내에서 `pip install --upgrade pip` 후 프로젝트 의존성 설치(`pip install -e .[dev]` 또는 `pip install -r requirements-dev.txt`).
- **동작**: pytest·ruff·mypy 등 테스트에 필요한 도구가 모두 설치된 상태가 된다.
- 속도: pip 캐시 디렉터리를 stage 간 재사용하도록 구성(선택).

### F2-5. Test
- 실행: `pytest --junitxml=reports/junit.xml`.
- 이 단계에서는 커버리지 게이트는 아직 강제하지 않는다(Phase 3에서 도입). 단, `--cov`로 측정만 시작해도 좋다.
- **동작**: 실패 테스트가 있으면 종료 코드가 0이 아니어서 stage가 실패하고 빌드가 빨간색이 된다.

### F2-6. 결과 수집 (post)
- `post { always { junit 'reports/junit.xml' } }`로 테스트 결과를 Jenkins에 등록.
- **동작**: 빌드 페이지에 테스트 개수·실패·추이가 표시되기 시작한다.

### F2-7. Job 생성·연결
- Jenkins에서 "Pipeline" 또는 "Multibranch Pipeline"(Phase 5에서 본격화) 작업 생성.
- "Pipeline script from SCM" → 저장소 지정 → `Jenkinsfile` 경로.
- **동작**: "Build Now"로 수동 실행 시 F2-3~F2-6이 순서대로 수행된다.

## 산출물
- 저장소 루트 `Jenkinsfile` (1차 버전).
- `requirements-dev.txt` 또는 `pyproject.toml`의 dev 의존성 그룹.
- Jenkins에 생성된 Pipeline Job.

## 완료 기준 (Definition of Done)
- [ ] "Build Now"로 빌드가 끝까지 성공(녹색).
- [ ] 빌드 페이지에서 테스트 결과 수·통과/실패가 보인다.
- [ ] 일부 테스트를 일부러 깨뜨리면 빌드가 실패(빨간색)하고 어떤 테스트가 실패했는지 표시됨.
- [ ] 빌드가 `python:3.12-slim` 컨테이너 안에서 실행됨(로그로 확인).
- [ ] 같은 커밋을 두 번 빌드해도 동일 결과(멱등성).

## 함정 / 주의
- **Declarative vs Scripted**: 처음엔 Declarative로 시작한다. Groovy 자유도가 필요할 때만 `script {}` 블록을 부분적으로 쓴다.
- **에이전트 권한**: slim 이미지에 빌드 도구(gcc 등)가 없어 일부 패키지 설치가 실패할 수 있다. 순수 파이썬 휠을 쓰거나 필요한 OS 패키지를 설치한다.
- **워크스페이스 권한**: 컨테이너 UID와 워크스페이스 소유자가 달라 쓰기 오류가 날 수 있다. `-u` 옵션 또는 디렉터리 권한으로 해결.
- **JUnit 경로**: `reports/junit.xml`이 실제로 생성되는지 확인(미생성 시 junit 스텝이 경고/실패).
- **GHA와의 대응 정리**: 학습 노트에 `on: push`↔트리거, `jobs`↔`stages`, `steps`↔`steps`, `uses`↔플러그인/`sh` 대응을 기록해두면 포트폴리오 설명이 풍부해진다.