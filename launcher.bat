@echo off
chcp 65001 >nul 2>&1
title 小狸 Pro-CLI v5.1.2

echo.
echo   ╔══════════════════════════════════════╗
echo   ║   小狸 Pro-CLI 启动器 v5.1.2       ║
echo   ║   正在检测环境...                   ║
echo   ╚══════════════════════════════════════╝
echo.

:: 检测 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python 环境
    echo 请先安装 Python 3.10+: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检测 Python 版本
for /f "tokens=2 delims= " %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo [OK] Python %PYVER%

:: 检测依赖并启动
echo [启动] 正在启动小狸 Pro-CLI...
echo.
python "%~dp0launcher.py" %*

if %errorlevel% neq 0 (
    echo.
    echo [错误] 启动失败，请检查日志
    pause
)
