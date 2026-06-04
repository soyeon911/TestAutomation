// Phase 6 · M3 — 공유 라이브러리로 파이프라인 추상화.
// 표준 Python CI 절차는 jenkins/shared-library/vars/pythonCI.groovy 에 캡슐화돼 있고,
// 이 Jenkinsfile은 그것을 한 줄로 호출한다(여러 프로젝트가 동일 표준 재사용).
// 라이브러리 등록: Manage Jenkins → Global Pipeline Libraries (ci/configure-shared-library.groovy).
@Library('url-shortener-shared@main') _

pythonCI(image: 'python:3.12-slim', covMin: 80)
