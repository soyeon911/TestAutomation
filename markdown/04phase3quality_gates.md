# 04 · Phase 3 — 품질 게이트 & 병렬화

## 개요
파이프라인을 "테스트만 돌리는 것"에서 "통과 기준이 있는 관문(quality gate)"으로 끌어올린다. 린트·포맷·타입·커버리지를 검사하고, 기준 미달 시 빌드를 실패시킨다. 또한 독립적인 검사를 `parallel`로 동시에 실행해 빌드 시간을 단축한다. 실무 파이프라인의 핵심이 이 단계다.

## 선행 조건
- Phase 2 완료(기본 파이프라인이 녹색).
- `pyproject.toml`에 ruff·mypy·pytest·coverage 설정이 들어갈 준비.

## 구현 기능
1. 린트 게이트 (ruff check)
2. 포맷 게이트 (ruff format --check)
3. 타입 게이트 (mypy)
4. 커버리지 게이트 (pytest-cov, 임계값)
5. 검사 병렬 실행
6. 게이트 위반 시 빌드 실패 정책
7. (선택) 경고 집계 (Warnings NG)

## 기능별 상세 동작

### F3-1. 린트 게이트
- 실행: `ruff check . --output-format=junit > reports/ruff.xml` (또는 기본 출력 + Warnings NG 파서).
- **정책**: lint 오류가 1건이라도 있으면 stage 실패.
- 규칙 셋은 `pyproject.toml`의 `[tool.ruff]`에서 관리.

### F3-2. 포맷 게이트
- 실행: `ruff format --check .`.
- **동작**: 포맷되지 않은 파일이 있으면 종료 코드 비0 → stage 실패. (자동 수정이 아니라 "검사"만 한다 — CI는 강제, 수정은 로컬/pre-commit에서.)

### F3-3. 타입 게이트
- 실행: `mypy app`.
- 설정은 `[tool.mypy]`. 시작은 느슨하게(`ignore_missing_imports = true`), 점차 엄격하게(`strict = true`) 상향 가능.
- **정책**: 타입 오류 발생 시 stage 실패.

### F3-4. 커버리지 게이트
- 실행: `pytest --cov=app --cov-report=xml:reports/coverage.xml --cov-report=term --cov-fail-under=80 --junitxml=reports/junit.xml`.
- **정책**: 라인 커버리지가 80% 미만이면 `--cov-fail-under`가 비0 종료 → 빌드 실패.
- 기준선(80%)은 `pyproject.toml` 또는 파이프라인 파라미터로 관리해 단계적으로 상향.

### F3-5. 병렬 실행
- `stage('Quality') { parallel { stage('Lint'){...} stage('Format'){...} stage('Type'){...} stage('Test'){...} } }` 구조.
- **동작**: 4개 검사가 동시에 수행되어 총 소요 시간이 직렬 대비 단축된다.
- 주의: 동일 워크스페이스를 공유하므로 산출물 경로(`reports/*`)가 서로 충돌하지 않게 분리한다.

### F3-6. 실패 정책
- 어느 한 병렬 stage라도 실패하면 전체 빌드 실패.
- `parallel`에 `failFast true`를 줄지 결정: 빠른 피드백을 원하면 true(하나 실패 시 나머지 중단), 모든 위반을 한 번에 보려면 false. **권장: false** (모든 게이트 결과를 한 번에 확인).

### F3-7. 경고 집계 (선택)
- Warnings Next Generation 플러그인으로 ruff/mypy 결과를 파싱해 빌드별 경고 추이를 시각화.
- `recordIssues` 스텝 사용. 품질 추이가 그래프로 쌓여 포트폴리오 가치 상승.

## 산출물
- 확장된 `Jenkinsfile` (병렬 Quality stage).
- `pyproject.toml`의 `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]`, `[tool.coverage.*]` 설정.
- `reports/` 산출물(junit.xml, coverage.xml, ruff/mypy 결과).

## 완료 기준 (Definition of Done)
- [ ] 4개 게이트(lint·format·type·coverage)가 병렬로 실행됨(빌드 그래프로 확인).
- [ ] 일부러 포맷을 깨거나 타입 오류를 넣으면 해당 게이트만 실패하고 빌드가 빨간색.
- [ ] 커버리지를 80% 미만으로 떨어뜨리면 빌드가 실패.
- [ ] 모든 게이트 통과 시에만 빌드가 녹색.
- [ ] 병렬 stage 간 산출물 경로 충돌이 없음.

## 함정 / 주의
- **`sh` 종료 코드**: 한 stage에서 여러 명령을 `&&` 없이 나열하면 중간 실패가 무시될 수 있다. 명령별로 stage/step을 분리하거나 `set -e`를 명확히 한다.
- **포맷 게이트 == 자동수정 아님**: CI에서 `ruff format`(수정)을 돌려 커밋하는 패턴은 피한다. 검사만 하고, 수정은 개발자가 로컬/pre-commit에서.
- **커버리지 측정 범위**: `--cov=app`으로 앱 코드만 측정한다. 테스트 코드까지 포함하면 수치가 왜곡된다.
- **병렬과 캐시**: 병렬 stage가 각자 pip install을 하면 비효율적. 설치를 선행 단일 stage에서 하고 결과를 공유하거나, 캐시를 활용한다.
- **게이트 기준의 점진 상향**: 처음부터 mypy strict + 커버리지 95%로 잡으면 진척이 막힌다. 낮게 시작해 단계적으로 올린다.