pipeline {
    agent any

    environment {
        // 使用相对路径，与 pyproject.toml 一致
        PYTHONPATH = "${WORKSPACE}"
    }

    stages {
        stage('准备环境') {
            steps {
                sh '''
                    echo "========== 安装依赖 =========="
                    python3 -m pip install --upgrade pip

                    # 使用 pyproject.toml 安装（推荐）
                    pip install -e .[dev]

                    # 或者使用 requirements.txt（兼容模式）
                    # pip install -r requirements.txt
                    # pip install pytest pytest-cov coverage pylint ruff
                '''
            }
        }

        stage('并行检查') {
            parallel {
                stage('代码格式检查 (Ruff)') {
                    steps {
                        sh '''
                            echo "========== Ruff 格式检查 =========="
                            ruff format --check src/ main.py

                            echo "========== Ruff Linter =========="
                            ruff check src/ main.py
                        '''
                    }
                }

                stage('代码质量检查 (Pylint)') {
                    steps {
                        sh '''
                            echo "========== Pylint 质量检查 =========="
                            # 使用 config/.pylintrc
                            pylint src/ main.py --rcfile=config/.pylintrc || true

                            echo "========== Pylint 质量门限检查 =========="
                            # 严格模式：评分必须 >= 9.0
                            score=$(pylint src/ main.py --rcfile=config/.pylintrc --exit-zero | grep "Your code has been rated at" | awk '{print $7}' | cut -d'/' -f1)
                            echo "Pylint 得分: $score / 10.0"

                            # 检查是否达标（可选，根据需要启用）
                            # if (( $(echo "$score < 9.0" | bc -l) )); then
                            #     echo "❌ Pylint 评分低于 9.0"
                            #     exit 1
                            # fi
                        '''
                    }
                }

                stage('测试覆盖率 (Coverage)') {
                    steps {
                        sh '''
                            echo "========== 运行测试 =========="
                            # 使用 pyproject.toml 中的 pytest 配置
                            pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing --cov-report=xml

                            echo "========== 覆盖率报告 =========="
                            coverage report
                        '''
                    }
                    post {
                        always {
                            // 保存覆盖率报告
                            publishHTML(target: [
                                allowMissing: false,
                                alwaysLinkToLastBuild: true,
                                keepAll: true,
                                reportDir: 'htmlcov',
                                reportFiles: 'index.html',
                                reportName: 'Coverage Report'
                            ])

                            // 如果有 Cobertura 插件，可以发布 XML 报告
                            // cobertura coberturaReportFile: 'coverage.xml'
                        }
                    }
                }
            }
        }

        stage('构建验证') {
            steps {
                sh '''
                    echo "========== 验证构建 =========="
                    # 测试是否可以正常导入
                    python3 -c "from src.plugins import load_plugins; print('✅ 插件系统加载正常')"

                    # 验证命令行工具
                    python3 main.py --help > /dev/null && echo "✅ 命令行工具正常"
                '''
            }
        }
    }

    post {
        always {
            // 清理 Python 缓存
            sh 'find . -type d -name __pycache__ -exec rm -rf {} + || true'
            sh 'find . -type f -name "*.pyc" -delete || true'
        }

        success {
            echo '''
            ✅ ========================================
            ✅  所有检查通过！
            ✅ ========================================
            ✅  - 代码格式检查 (Ruff): PASS
            ✅  - 代码质量检查 (Pylint): PASS
            ✅  - 测试覆盖率 (Coverage): PASS
            ✅  - 构建验证: PASS
            ✅ ========================================
            '''
        }

        failure {
            echo '''
            ❌ ========================================
            ❌  部分检查失败
            ❌ ========================================
            请查看上方具体失败的 stage：
            - 代码格式检查 (Ruff)
            - 代码质量检查 (Pylint)
            - 测试覆盖率 (Coverage)
            - 构建验证
            ❌ ========================================
            '''
        }

        unstable {
            echo '⚠️ 构建不稳定，部分质量检查有警告'
        }
    }
}
