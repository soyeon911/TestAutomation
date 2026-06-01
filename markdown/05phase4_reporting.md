# 05 · Phase 4 — 리포트 & 트렌드

## 개요
빌드 결과를 "통과/실패"를 넘어 **시각적 리포트와 추이(trend)**로 만든다. 테스트 결과 트렌드, 커버리지 추이, Allure 상세 리포트를 Jenkins에 연동한다. 빌드를 거듭할수록 그래프가 쌓이는 화면이 이 프로젝트의 포트폴리오 하이라이트가 된다.

## 선행 조건
- Phase 3 완료(게이트가 동작, `reports/junit.xml`·`reports/coverage.xml` 생성됨).
- Phase 1에서 JUnit·Coverage·Allure 플러그인 설치 완료.

## 구현 기능
1. JUnit 테스트 결과 트렌드
2. 커버리지 리포트 & 추이
3. Allure 리포트 연동
4. (선택) pytest-html 단일 리포트
5. 빌드 산출물 보관(아카이브)

## 기능별 상세 동작

### F4-1. JUnit 트렌드
- `post { always { junit 'reports/junit.xml' } }` (Phase 2에서 시작, 여기서 확정).
- **동작**: 빌드별 테스트 총수·실패수·실행시간이 그래프로 누적된다. 실패한 테스트의 이력 추적 가능.

### F4-2. 커버리지 리포트 & 추이
- pytest가 `--cov-report=xml:reports/coverage.xml` 생성(Cobertura 형식).
- Coverage(Code Coverage API) 플러그인의 `recordCoverage` 스텝으로 등록:
  - 파일/패키지별 커버리지 표시.
  - 빌드 간 커버리지 증감 추이 그래프.
- **동작**: PR/커밋마다 커버리지가 떨어졌는지 한눈에 보인다. (선택) 커버리지 감소 시 경고/실패 정책 추가 가능.

### F4-3. Allure 리포트
- pytest 실행에 `--alluredir=reports/allure-results` 추가(allure-pytest 패키지 필요).
- Allure 플러그인의 `allure` 스텝(또는 post)으로 결과 디렉터리를 가리켜 리포트 생성.
- **동작**: 빌드 페이지에서 Allure 리포트 링크 → 스텝·첨부·카테고리별 상세 결과를 시각적으로 확인.
- 풍부화(선택): `@allure.feature`, `@allure.story` 데코레이터로 테스트를 분류해 리포트 가독성을 높인다.

### F4-4. pytest-html (선택)
- `--html=reports/report.html --self-contained-html`로 단일 HTML 리포트 생성.
- Allure가 있으면 중복이므로 선택 사항. 가볍게 공유할 단일 파일이 필요할 때 유용.

### F4-5. 산출물 아카이브
- `archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true`로 리포트 파일을 빌드에 보관.
- **동작**: 빌드 페이지에서 리포트 원본을 다운로드할 수 있다.

## 산출물
- 리포트 연동이 추가된 `Jenkinsfile` (junit + recordCoverage + allure + archiveArtifacts).
- `allure-pytest` 의존성 추가.
- (선택) Allure 분류용 데코레이터가 적용된 테스트.

## 완료 기준 (Definition of Done)
- [ ] 빌드 페이지에 테스트 결과 트렌드 그래프가 보인다.
- [ ] 커버리지 리포트와 빌드 간 추이 그래프가 보인다.
- [ ] Allure 리포트 링크가 생성되고 상세 결과가 열린다.
- [ ] 여러 번 빌드한 뒤 트렌드 그래프에 점이 누적됨을 확인.
- [ ] `reports/` 산출물이 빌드에서 다운로드 가능.

## 함정 / 주의
- **결과 디렉터리 정리**: Allure는 이전 빌드의 `allure-results`가 섞이면 결과가 오염된다. 매 빌드 시작 시 `reports/` 정리(clean) 스텝을 둔다.
- **plugin 버전 ↔ allure CLI**: Allure Jenkins 플러그인이 내부적으로 commandline 도구를 받는다. Manage Jenkins에서 Allure Commandline 설치를 구성해야 리포트가 생성된다.
- **커버리지 형식 불일치**: 플러그인이 기대하는 형식(Cobertura XML)과 pytest 출력이 맞아야 한다. `--cov-report=xml`이 Cobertura 호환이므로 그대로 사용.
- **post 블록 위치**: junit/allure/coverage 수집은 테스트 실패로 stage가 깨져도 실행되도록 `post { always { ... } }`에 둔다(실패 빌드의 결과도 봐야 하므로).