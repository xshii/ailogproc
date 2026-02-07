@echo off
REM Python venv setup script for Windows
REM No miniconda required, uses system Python

setlocal EnableDelayedExpansion

set VENV_NAME=venv

echo ==========================================
echo   Python venv 环境设置脚本 (Windows)
echo   不需要 miniconda，使用系统 Python
echo ==========================================
echo.

REM 查找合适的 Python
set PYTHON_CMD=
for %%p in (python3.12 python3.11 python3.10 python3.9 python3 python) do (
    where %%p >nul 2>&1
    if !errorlevel! equ 0 (
        for /f "tokens=2" %%v in ('%%p --version 2^>^&1') do (
            set VERSION=%%v
        )
        REM 简单检查版本（假设 3.9+ 都可以）
        echo 找到 Python: %%p (!VERSION!)
        set PYTHON_CMD=%%p
        goto :python_found
    )
)

:python_found
if "%PYTHON_CMD%"=="" (
    echo.
    echo 未找到 Python 3.9 或更高版本
    echo.
    echo 请从以下网址下载并安装 Python:
    echo https://www.python.org/downloads/
    echo.
    echo 安装时请勾选 "Add Python to PATH"
    exit /b 1
)

echo 使用 Python: %PYTHON_CMD% (%VERSION%)
echo.

REM 检查虚拟环境是否存在
if exist "%VENV_NAME%" (
    echo 虚拟环境 '%VENV_NAME%' 已存在
    set /p response="是否删除并重建? (y/N): "
    if /i "!response!"=="y" (
        echo 删除现有环境...
        rmdir /s /q "%VENV_NAME%"
    )
)

REM 创建虚拟环境
if not exist "%VENV_NAME%" (
    echo.
    echo 创建虚拟环境...
    %PYTHON_CMD% -m venv %VENV_NAME%
    if !errorlevel! neq 0 (
        echo 创建虚拟环境失败
        exit /b 1
    )
    echo 虚拟环境创建完成
)

REM 激活虚拟环境并安装依赖
echo.
echo 安装项目依赖...
call %VENV_NAME%\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ==========================================
echo 环境设置完成!
echo ==========================================
echo.
echo 激活环境：
echo   %VENV_NAME%\Scripts\activate
echo.
echo 运行示例：
echo   %VENV_NAME%\Scripts\activate
echo   python main.py examples\templates\template_a_column.xlsx examples\logs\sample_log_opsch.txt
echo.
echo 退出环境：
echo   deactivate
echo ==========================================

endlocal
