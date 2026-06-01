# 06 · Phase 5 — 자동 트리거 (웹훅 & Multibranch)

## 개요
지금까지는 "Build Now"로 수동 실행했다. 이 단계에서 코드 push가 자동으로 빌드를 일으키게 만든다. 핵심 난관은 **GitHub 웹훅이 로컬 Jenkins에 도달해야 한다**는 점이다(로컬은 공인 IP가 없음). 터널링 또는 SCM 폴링으로 해결한다. 더불어 Multibranch Pipeline으로 브랜치별 자동 빌드를, 커밋 상태 보고로 GitHub PR에 체크 표시를 띄운다.

## 선행 조건
- Phase 2~4 완료(파이프라인이 리포트까지 동작).
- GitHub 저장소 + 개인 액세스 토큰(또는 GitHub App).

## 구현 기능
1. GitHub 자격 증명 등록
2. 웹훅 도달 경로 확보 (터널 또는 폴링)
3. push 시 자동 트리거
4. Multibranch Pipeline 구성
5. 커밋/PR 상태 보고
6. (선택) PR 전용 검증

## 기능별 상세 동작

### F5-1. GitHub 자격 증명
- Manage Jenkins → Credentials에 GitHub PAT(repo·status 권한) 등록.
- 웹훅 시크릿 문자열도 별도 Credential로 등록.
- **동작**: 파이프라인이 비공개 저장소 체크아웃·커밋 상태 보고에 사용.

### F5-2. 웹훅 도달 경로 (핵심 난관)
세 가지 선택지:
- **옵션 1 — 터널(권장 학습)**: ngrok 또는 Cloudflare Tunnel로 `http://localhost:8080`을 공인 URL로 노출. GitHub 웹훅 URL을 `https://<tunnel>/github-webhook/`으로 설정.
  - 장점: 실제 웹훅 흐름을 그대로 경험. 단점: 무료 터널은 URL이 매번 바뀔 수 있음(고정 도메인 옵션 고려).
- **옵션 2 — SCM 폴링**: Jenkins가 주기적으로 저장소를 폴링(`pollSCM 'H/2 * * * *'`). 웹훅 불필요.
  - 장점: 외부 노출 없음, 가장 단순. 단점: 지연·불필요한 폴링(실무 대비 학습성 낮음).
- **옵션 3 — 공개 호스트 배포**: 클라우드 VM에 Jenkins를 올려 진짜 공인 URL 사용(가장 실무적, 비용·관리 부담).

**결정**: 옵션 1(터널)을 기본으로, 터널이 불안정할 때 옵션 2(폴링)로 폴백.

### F5-3. 자동 트리거
- 웹훅 방식: GitHub → Jenkins `/github-webhook/` 수신 → 해당 Job 빌드 트리거.
- 폴링 방식: `triggers { pollSCM('H/2 * * * *') }`.
- **동작**: main 또는 feature 브랜치에 push하면 수 초~수 분 내 빌드가 자동 시작된다.

### F5-4. Multibranch Pipeline
- "Multibranch Pipeline" Job 생성 → GitHub 소스 + 자격 증명 지정.
- Jenkins가 `Jenkinsfile`이 있는 브랜치를 자동 발견해 브랜치별 파이프라인 생성.
- **동작**: 새 브랜치를 만들고 push하면 자동으로 해당 브랜치용 빌드가 생긴다. PR도 발견 가능(설정에 따라).

### F5-5. 커밋/PR 상태 보고
- GitHub 플러그인이 빌드 시작/성공/실패를 커밋 상태(commit status)로 GitHub에 보고.
- **동작**: GitHub PR 화면에 ✓/✗ 체크가 표시되어, 통과해야 머지할 수 있는 흐름(브랜치 보호 규칙과 결합)을 만든다.

### F5-6. PR 전용 검증 (선택)
- PR 대상 빌드에서만 추가 검사(예: 더 엄격한 게이트)를 돌리는 조건 분기(`when { changeRequest() }`).

## 산출물
- 트리거가 추가된 `Jenkinsfile`(`triggers` 또는 멀티브랜치 설정).
- Jenkins Multibranch Pipeline Job.
- GitHub 저장소의 웹훅 설정(옵션 1 선택 시).
- 터널 실행 절차 문서(옵션 1) 또는 폴링 설정 기록(옵션 2).

## 완료 기준 (Definition of Done)
- [ ] 코드 push → 사람이 버튼을 누르지 않아도 빌드가 자동 시작됨.
- [ ] 새 feature 브랜치 push 시 멀티브랜치에서 해당 브랜치 빌드가 자동 생성됨.
- [ ] GitHub 커밋/PR에 빌드 상태(성공/실패)가 표시됨.
- [ ] (옵션 1) 웹훅 전달 로그가 Jenkins/GitHub 양쪽에서 확인됨.

## 함정 / 주의
- **터널 URL 변동**: ngrok 무료는 재시작 시 URL이 바뀌어 웹훅이 깨진다. 고정 도메인 또는 Cloudflare Tunnel 고정 호스트네임 사용 고려.
- **웹훅 경로**: 끝의 슬래시(`/github-webhook/`)와 경로가 정확해야 한다. 누락 시 404.
- **시크릿 검증**: 웹훅 시크릿을 설정하면 Jenkins 쪽에서도 동일 시크릿을 알아야 한다(불일치 시 거부).
- **폴링 남용**: 폴링 주기를 너무 짧게(매분) 잡으면 자원 낭비. `H/2`처럼 분산·완화.
- **권한 범위**: PAT는 최소 권한(repo + status)만. 광범위 권한 토큰은 지양.
- **브랜치 보호와 결합**: 커밋 상태만으로는 머지를 막지 못한다. GitHub 브랜치 보호 규칙에서 "상태 통과 필수"를 켜야 실효가 있다.