// Phase 2 — 기본 파이프라인 (체크아웃 → 설치 → 테스트 → 결과 수집)
// Declarative Pipeline. 전 stage를 python:3.12-slim 컨테이너(방식 A)에서 실행한다.
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
        VENV = "${WORKSPACE}/.venv"
        PIP_CACHE_DIR = "${WORKSPACE}/.pip-cache"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm   // 트리거된 커밋의 소스를 워크스페이스로 가져온다
            }
        }

        stage('Setup') {
            steps {
                sh '''
                    python --version
                    python -m venv "$VENV"
                    . "$VENV/bin/activate"
                    python -m pip install --upgrade pip
                    pip install -e ".[dev]"
                '''
            }
        }

        stage('Test') {
            steps {
                sh '''
                    . "$VENV/bin/activate"
                    mkdir -p reports
                    pytest --junitxml=reports/junit.xml \
                           --cov=app --cov-report=xml:reports/coverage.xml
                '''
                // 커버리지 게이트는 Phase 3에서 강제. 여기서는 측정만 한다.
            }
        }
    }

    post {
        always {
            // 테스트 결과를 Jenkins에 등록 → 빌드 페이지에 개수·실패·추이 표시.
            junit testResults: 'reports/junit.xml', allowEmptyResults: false
            archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
        }
    }
}
