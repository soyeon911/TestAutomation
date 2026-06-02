// Phase 3 — 품질 게이트 & 병렬화
// Checkout → Setup(1회 설치) → Quality Gates(Lint·Format·Type·Test 병렬) → 결과 수집.
// 전 stage를 python:3.12-slim 컨테이너(방식 A)에서 실행한다.
// GitHub Actions 대응:  on:push↔Job 트리거 / jobs↔stages / steps↔steps / uses↔플러그인·sh

pipeline {
    agent {
        docker {
            image 'python:3.12-slim'
        }
    }

    options {
        timeout(time: 20, unit: 'MINUTES')   // 무한 대기 방지
        timestamps()                          // 로그에 타임스탬프
        buildDiscarder(logRotator(numToKeepStr: '15'))  // 빌드 보존 개수 제한
    }

    environment {
        // 워크스페이스 안 venv로 격리 설치(uid 1000도 쓰기 가능), pip 캐시는 빌드 간 재사용.
        // 도구는 절대경로($VENV/bin/...)로 호출 → activate/PATH 모호성 제거.
        VENV = "${WORKSPACE}/.venv"
        PIP_CACHE_DIR = "${WORKSPACE}/.pip-cache"
        COV_MIN = '80'   // 커버리지 게이트 기준선 (단계적 상향 가능)
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm   // 트리거된 커밋의 소스를 워크스페이스로 가져온다
            }
        }

        stage('Setup') {
            // 의존성 설치는 선행 단일 stage에서 1회 → 병렬 게이트가 같은 venv를 공유(중복 설치 방지).
            steps {
                sh '''
                    set -e
                    python --version
                    python -m venv "$VENV"
                    "$VENV/bin/pip" install --upgrade pip
                    "$VENV/bin/pip" install -e ".[dev]"
                '''
            }
        }

        stage('Quality Gates') {
            // 4개 독립 검사를 동시에 실행해 총 소요 시간 단축.
            // failFast false: 하나가 실패해도 나머지를 끝까지 돌려 모든 위반을 한 번에 확인.
            failFast false
            parallel {
                stage('Lint') {
                    steps { sh '"$VENV/bin/ruff" check .' }
                }
                stage('Format') {
                    // 검사만(자동수정 아님). 포맷 안 된 파일 있으면 비0 종료 → 실패.
                    steps { sh '"$VENV/bin/ruff" format --check .' }
                }
                stage('Type') {
                    steps { sh '"$VENV/bin/mypy" app' }
                }
                stage('Test') {
                    // 산출물 경로(reports/*)는 다른 게이트와 충돌하지 않는다.
                    steps {
                        sh '''
                            set -e
                            mkdir -p reports
                            "$VENV/bin/pytest" \
                                --junitxml=reports/junit.xml \
                                --cov=app \
                                --cov-report=xml:reports/coverage.xml \
                                --cov-report=term \
                                --cov-fail-under="$COV_MIN"
                        '''
                    }
                }
            }
        }
    }

    post {
        always {
            // 테스트 결과를 Jenkins에 등록 → 빌드 페이지에 개수·실패·추이 표시.
            junit testResults: 'reports/junit.xml', allowEmptyResults: true
            archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
        }
    }
}
