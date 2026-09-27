@echo off
chcp 65001 >nul 2>&1
title Lix CLI - 构建 EXE

echo.
echo   ╔══════════════════════════════════════╗
echo   ║   Lix CLI EXE 构建脚本         ║
echo   ╚══════════════════════════════════════╝
echo.

:: 检测 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

:: 安装 PyInstaller
echo [1/3] 安装 PyInstaller...
pip install pyinstaller --quiet
if %errorlevel% neq 0 (
    echo [错误] PyInstaller 安装失败
    pause
    exit /b 1
)

:: 编译 EXE
echo [2/3] 正在编译 launcher.exe ...
pyinstaller --onefile --name launcher --clean --noconfirm launcher.py
if %errorlevel% neq 0 (
    echo [错误] 编译失败
    pause
    exit /b 1
)

:: 完成
echo [3/3] 编译完成！
echo.
echo   EXE 位置: dist\launcher.exe
echo.
pause
