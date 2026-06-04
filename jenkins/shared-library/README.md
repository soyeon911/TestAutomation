# Jenkins Shared Library — `url-shortener-shared`

Phase 6 · M3. 표준 Python CI 파이프라인을 재사용 가능한 공유 라이브러리로 추출한 것.

## 구조
```
jenkins/shared-library/
└── vars/
    └── pythonCI.groovy   # pythonCI() 글로벌 스텝
```
> 공유 라이브러리 루트는 `jenkins/shared-library`(이 디렉터리)다. Jenkins 전역 라이브러리 설정에서
> **Library Path = `jenkins/shared-library`** 로 지정하므로 `vars/`·`src/`·`resources/`가 이 아래에 온다.

## Jenkins 등록 (Manage Jenkins → System → Global Pipeline Libraries)
- Name: `url-shortener-shared`
- Default version: `main`
- Retrieval method: Modern SCM → Git → `https://github.com/soyeon911/TestAutomation.git`
- **Library Path**: `jenkins/shared-library`

(이 저장소는 [`ci/configure-shared-library.groovy`](../../ci/configure-shared-library.groovy)로 코드로 등록한다.)

## 사용
프로젝트 루트 `Jenkinsfile`:
```groovy
@Library('url-shortener-shared@main') _
pythonCI(image: 'python:3.12-slim', covMin: 80)
```

## `pythonCI()` 가 하는 일
1. `checkout scm` → `docker.image(image).inside { }` 로 격리 빌드(방식 A).
2. 병렬 품질 게이트: `ruff check` / `ruff format --check` / `mypy app` / `pytest`(+커버리지 게이트 `covMin`).
   각 게이트는 `catchError` 로 감싸 실패해도 리포트까지 진행.
3. 같은 노드(컨트롤러, Java + Allure CLI)에서 리포트: JUnit 트렌드 · 커버리지 추이(Cobertura) ·
   Allure HTML 게시 · `reports/**` 아카이브.

## 가치
여러 프로젝트가 동일 CI 표준을 한 줄로 재사용한다. 파이프라인 로직 변경이 라이브러리 한 곳에
집중되어 유지보수가 쉽다(파이프라인 추상화·재사용).
