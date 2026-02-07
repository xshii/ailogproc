pipeline {
    agent any

    stages {
        stage('准备环境') {
            steps {
                sh '''
                    python3 -m pip install --upgrade pip
                    pip install -r requirements.txt
                    pip install pylint ruff
                '''
            }
        }

        stage('并行检查') {
            parallel {
                stage('代码格式检查') {
                    steps {
                        sh '''
                            echo "========== Ruff 格式检查 =========="
                            ruff format --check src/ main.py
                            echo "========== Ruff Linter =========="
                            ruff check src/ main.py
                        '''
                    }
                }

                stage('代码质量检查') {
                    steps {
                        sh '''
                            echo "========== Pylint 质量检查 =========="
                            pylint src/ main.py --rcfile=.pylintrc
                        '''
                    }
                }
            }
        }
    }

    post {
        success {
            echo '✅ 所有检查通过！'
        }
        failure {
            echo '❌ 部分检查失败，请查看上方具体失败的 stage'
        }
    }
}
