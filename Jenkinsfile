@Library('platform-shared-library@v1') _

pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }

    environment {
        AWS_REGION         = 'us-east-1'
        ECR_REGISTRY       = '267423569109.dkr.ecr.us-east-1.amazonaws.com'
        ECR_REPOSITORY     = 'shopeasy-product-service'
        SERVICE_NAME       = 'product-service'
        HELM_CHART         = 'helm-charts/charts/microservice'
        ARTIFACTS_BUCKET   = 'shopeasy-artifacts-267423569109-us-east-1'
        SONAR_PROJECT_KEY  = 'shopeasy-product-service'
        PLATFORM_CONFIG    = 'platform-config'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                checkoutPlatformDeps()
                script {
                    env.GIT_SHA = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                    env.IMAGE_TAG = "${env.BUILD_VERSION ?: '1.0.0'}-${env.GIT_SHA}"
                    env.LOCAL_IMAGE = "${ECR_REPOSITORY}:${env.IMAGE_TAG}"
                }
            }
        }

        stage('Security & Quality') {
            parallel {
                stage('Secret Scan') {
                    steps {
                        secretScan configFile: "${PLATFORM_CONFIG}/gitleaks/.gitleaks.toml"
                    }
                }
                stage('Lint') {
                    steps {
                        sh 'pip install flake8 && flake8 . --max-line-length=120 || true'
                    }
                }
                stage('Unit Tests') {
                    steps {
                        sh '''
                            pip install -r requirements.txt -r requirements-dev.txt
                            pytest tests/ -v --junitxml=reports/junit.xml
                        '''
                    }
                    post {
                        always {
                            junit 'reports/junit.xml'
                        }
                    }
                }
            }
        }

        stage('SonarQube') {
            steps {
                sonarScan projectKey: env.SONAR_PROJECT_KEY, sources: '.'
            }
        }

        stage('Dependency Scan') {
            steps {
                dependencyScan projectName: env.SERVICE_NAME, severity: 'high'
            }
        }

        stage('Terraform Scan') {
            when { expression { fileExists('terraform') } }
            steps {
                terraformScan terraformDir: 'terraform'
            }
        }

        stage('Build Once') {
            steps {
                dockerBuild imageName: env.LOCAL_IMAGE, context: '.'
            }
        }

        stage('Container Security') {
            parallel {
                stage('Trivy Scan') {
                    steps {
                        trivyScan imageRef: env.LOCAL_IMAGE, severity: 'HIGH,CRITICAL', exitCode: '1'
                    }
                }
                stage('Generate SBOM') {
                    steps {
                        script {
                            env.SBOM_FILE = generateSBOM imageRef: env.LOCAL_IMAGE
                        }
                    }
                }
            }
        }

        stage('Sign & Push to ECR') {
            steps {
                script {
                    cosignSign imageRef: env.LOCAL_IMAGE
                    env.IMAGE_DIGEST = pushToEcr(
                        imageRef: env.LOCAL_IMAGE,
                        repository: env.ECR_REPOSITORY,
                        tag: env.IMAGE_TAG
                    )
                    env.FULL_IMAGE = "${ECR_REGISTRY}/${ECR_REPOSITORY}@${env.IMAGE_DIGEST}"
                }
            }
        }

        stage('Deploy Development') {
            steps {
                script {
                    deployHelm(
                        release: env.SERVICE_NAME,
                        chartPath: env.HELM_CHART,
                        namespace: 'shopeasy-dev',
                        valuesFile: 'helm-charts/values-dev.yaml',
                        imageRepository: "${ECR_REGISTRY}/${ECR_REPOSITORY}",
                        imageTag: env.IMAGE_TAG,
                        imageDigest: env.IMAGE_DIGEST,
                        servicePort: 5000,
                        extraSet: '--set env[0].name=ENVIRONMENT --set env[0].value=dev'
                    )
                    archivePromotion(
                        service: env.SERVICE_NAME,
                        environment: 'dev',
                        manifest: """{"service":"${SERVICE_NAME}","environment":"dev","imageTag":"${IMAGE_TAG}","imageDigest":"${IMAGE_DIGEST}","gitSha":"${GIT_SHA}"}"""
                    )
                }
            }
        }

        stage('Smoke Test Dev') {
            steps {
                smokeTest healthUrl: 'http://product-service.shopeasy-dev.svc.cluster.local:5000/health'
            }
        }

        stage('Approve QA') {
            steps {
                timeout(time: 1, unit: 'HOURS') {
                    input message: 'Deploy same image to QA?', ok: 'Promote to QA'
                }
            }
        }

        stage('Deploy QA') {
            steps {
                script {
                    deployHelm(
                        release: env.SERVICE_NAME,
                        namespace: 'shopeasy-qa',
                        valuesFile: 'helm-charts/values-qa.yaml',
                        imageRepository: "${ECR_REGISTRY}/${ECR_REPOSITORY}",
                        imageTag: env.IMAGE_TAG,
                        imageDigest: env.IMAGE_DIGEST,
                        servicePort: 5000
                    )
                    archivePromotion service: env.SERVICE_NAME, environment: 'qa',
                        manifest: """{"service":"${SERVICE_NAME}","environment":"qa","imageDigest":"${IMAGE_DIGEST}"}"""
                }
            }
        }

        stage('Regression Tests QA') {
            steps {
                sh 'pytest tests/integration/ -v || true'
            }
        }

        stage('Deploy UAT & ZAP') {
            steps {
                script {
                    deployHelm(
                        release: env.SERVICE_NAME,
                        namespace: 'shopeasy-uat',
                        valuesFile: 'helm-charts/values-uat.yaml',
                        imageRepository: "${ECR_REGISTRY}/${ECR_REPOSITORY}",
                        imageTag: env.IMAGE_TAG,
                        imageDigest: env.IMAGE_DIGEST,
                        servicePort: 5000
                    )
                }
            }
        }

        stage('OWASP ZAP') {
            steps {
                zapScan targetUrl: 'https://uat.shopeasy.example.com/api/products'
            }
        }

        stage('Approve Production') {
            steps {
                timeout(time: 4, unit: 'HOURS') {
                    input message: 'Deploy SAME digest to Production?', ok: 'Deploy Prod', submitter: 'platform-leads'
                }
            }
        }

        stage('Deploy Production') {
            steps {
                script {
                    deployHelm(
                        release: env.SERVICE_NAME,
                        namespace: 'shopeasy-prod',
                        valuesFile: 'helm-charts/values-prod.yaml',
                        imageRepository: "${ECR_REGISTRY}/${ECR_REPOSITORY}",
                        imageTag: env.IMAGE_TAG,
                        imageDigest: env.IMAGE_DIGEST,
                        servicePort: 5000
                    )
                    archivePromotion service: env.SERVICE_NAME, environment: 'prod',
                        manifest: """{"service":"${SERVICE_NAME}","environment":"prod","imageDigest":"${IMAGE_DIGEST}","previousDigest":""}"""
                }
            }
        }
    }

    post {
        always {
            cleanWs()
        }
        success {
            notifySlack color: 'good', message: "✅ ${SERVICE_NAME} ${IMAGE_TAG} promoted to prod (digest ${IMAGE_DIGEST})"
            emailext subject: "SUCCESS: ${JOB_NAME} #${BUILD_NUMBER}",
                     body: "Build succeeded. Image digest: ${IMAGE_DIGEST}",
                     to: '${DEFAULT_RECIPIENTS}'
        }
        failure {
            notifySlack color: 'danger', message: "❌ ${SERVICE_NAME} build ${BUILD_NUMBER} FAILED"
            emailext subject: "FAILED: ${JOB_NAME} #${BUILD_NUMBER}",
                     body: "Security scan or deploy failed. No promotion occurred.",
                     to: '${DEFAULT_RECIPIENTS}'
        }
    }
}
