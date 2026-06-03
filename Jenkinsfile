// Phase 4 — 리포트 & 트렌드
// 구조: 빌드/게이트는 python:3.12-slim 에이전트(방식 A)에서, 리포트 생성은 Java가 있는
//       컨트롤러에서 실행한다(Allure CLI는 Java 필요). reports/ 는 stash 로 넘긴다.
// 게이트는 catchError 로 감싸 실패해도 빌드를 빨갛게 표시하면서 리포트 stage까지 진행한다.

pipeline {
    agent none

    options {
        timeout(time: 20, unit: 'MINUTES')
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '15'))
        skipDefaultCheckout(true)   // 스테이지별 agent 자동 체크아웃 방지(필요한 곳만 명시)
    }

    stages {
        stage('Build & Quality Gates') {
            agent { docker { image 'python:3.12-slim' } }
            environment {
                VENV = "${WORKSPACE}/.venv"
                PIP_CACHE_DIR = "${WORKSPACE}/.pip-cache"
                COV_MIN = '80'
            }
            stages {
                stage('Checkout') {
                    steps { checkout scm }
                }
                stage('Setup') {
                    steps {
                        sh '''
                            set -e
                            rm -rf reports          # 이전 빌드의 allure-results 오염 방지
                            python -m venv "$VENV"
                            "$VENV/bin/pip" install --upgrade pip
                            "$VENV/bin/pip" install -e ".[dev]"
                        '''
                    }
                }
                stage('Quality Gates') {
                    // 4개 검사 병렬. 각 게이트를 catchError 로 감싸 실패해도 리포트까지 진행.
                    failFast false
                    parallel {
                        stage('Lint') {
                            steps {
                                catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                                    sh '"$VENV/bin/ruff" check .'
                                }
                            }
                        }
                        stage('Format') {
                            steps {
                                catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                                    sh '"$VENV/bin/ruff" format --check .'
                                }
                            }
                        }
                        stage('Type') {
                            steps {
                                catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                                    sh '"$VENV/bin/mypy" app'
                                }
                            }
                        }
                        stage('Test') {
                            steps {
                                catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                                    sh '''
                                        set -e
                                        mkdir -p reports
                                        "$VENV/bin/pytest" \
                                            --junitxml=reports/junit.xml \
                                            --cov=app \
                                            --cov-report=xml:reports/coverage.xml \
                                            --cov-report=term \
                                            --cov-fail-under="$COV_MIN" \
                                            --alluredir=reports/allure-results
                                    '''
                                }
                            }
                        }
                    }
                }
            }
            post {
                always {
                    // 리포트 산출물을 컨트롤러(Report) stage로 넘긴다.
                    stash name: 'reports', includes: 'reports/**', allowEmpty: true
                }
            }
        }

        stage('Report') {
            agent any   // 컨트롤러(JDK17 + Allure CLI 사전 설치) — Allure 리포트 생성에 Java 필요.
            steps {
                unstash 'reports'
                // JUnit 트렌드: 빌드별 테스트 수·실패·시간 누적.
                junit testResults: 'reports/junit.xml', allowEmptyResults: true
                // 커버리지 리포트 & 추이(Cobertura).
                recordCoverage(tools: [[parser: 'COBERTURA', pattern: 'reports/coverage.xml']])
                // Allure 정적 HTML 리포트 생성(컨트롤러 이미지에 allure CLI 사전 설치) 후 게시.
                sh '''
                    if [ -d reports/allure-results ]; then
                        allure generate reports/allure-results -o reports/allure-report --clean
                    fi
                '''
                publishHTML(target: [
                    reportName: 'Allure Report',
                    reportDir: 'reports/allure-report',
                    reportFiles: 'index.html',
                    keepAll: true,
                    alwaysLinkToLastBuild: true,
                    allowMissing: true,
                ])
                // 리포트 원본 보관(다운로드 가능).
                archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
            }
        }
    }
}
