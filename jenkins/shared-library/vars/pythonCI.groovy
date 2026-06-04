#!/usr/bin/env groovy

/**
 * pythonCI — 표준 Python CI 파이프라인을 캡슐화한 공유 라이브러리 스텝 (Phase 6 · M3).
 *
 * 여러 Python 프로젝트가 동일한 CI 표준(격리된 docker 빌드 + 병렬 품질 게이트 + 리포트/트렌드)을
 * 한 줄로 재사용한다. Jenkinsfile 예:
 *
 *     @Library('url-shortener-shared@main') _
 *     pythonCI(image: 'python:3.12-slim', covMin: 80)
 *
 * 동작:
 *   - 단일 node 에서 checkout 후 docker.inside(방식 A)로 빌드 → 워크스페이스가 공유되므로
 *     컨테이너가 만든 reports/ 를 같은 노드의 컨트롤러(Java)가 그대로 읽는다(stash 불필요).
 *   - 품질 게이트(lint/format/type/test)를 병렬 실행하고, 각 게이트를 catchError 로 감싸
 *     실패해도 리포트 단계까지 진행한다(실패 빌드의 결과도 수집).
 *   - 리포트: JUnit 트렌드 + 커버리지 추이(Cobertura) + Allure(HTML 게시) + 산출물 아카이브.
 *
 * @param config.image   빌드 에이전트 docker 이미지 (기본 'python:3.12-slim')
 * @param config.covMin  커버리지 게이트 임계값(%) (기본 80)
 */
def call(Map config = [:]) {
    String image = config.get('image', 'python:3.12-slim')
    String covMin = "${config.get('covMin', 80)}"

    timestamps {
        timeout(time: 20, unit: 'MINUTES') {
            node {
                withEnv([
                    "VENV=${env.WORKSPACE}/.venv",
                    "PIP_CACHE_DIR=${env.WORKSPACE}/.pip-cache",
                    "COV_MIN=${covMin}",
                ]) {
                    stage('Checkout') {
                        checkout scm
                    }

                    // 빌드/게이트는 격리된 docker 컨테이너(방식 A)에서.
                    docker.image(image).inside {
                        stage('Setup') {
                            sh '''
                                set -e
                                rm -rf reports
                                python --version
                                python -m venv "$VENV"
                                "$VENV/bin/pip" install --upgrade pip
                                "$VENV/bin/pip" install -e ".[dev]"
                            '''
                        }
                        stage('Quality Gates') {
                            parallel(
                                'Lint': {
                                    catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                                        sh '"$VENV/bin/ruff" check .'
                                    }
                                },
                                'Format': {
                                    catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                                        sh '"$VENV/bin/ruff" format --check .'
                                    }
                                },
                                'Type': {
                                    catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                                        sh '"$VENV/bin/mypy" app'
                                    }
                                },
                                'Test': {
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
                                },
                                failFast: false,
                            )
                        }
                    }

                    // 리포트는 같은 노드(컨트롤러, JDK + Allure CLI 보유)에서.
                    stage('Report') {
                        junit testResults: 'reports/junit.xml', allowEmptyResults: true
                        recordCoverage(tools: [[parser: 'COBERTURA', pattern: 'reports/coverage.xml']])
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
                        archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
                    }
                }
            }
        }
    }
}
