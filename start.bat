@echo off
chcp 65001 >nul
title 智分宝 · 智能垃圾分类检测系统

echo ============================================
echo     智分宝 · 智能垃圾分类检测系统
echo ============================================
echo.

cd /d "%~dp0"

echo 🔍 正在启动，请稍候...
echo.

python main.py %*

if %errorlevel% neq 0 (
    echo.
    echo ⚠ 程序异常退出，错误码：%errorlevel%
    echo 请尝试运行：pip install -r requirements.txt
    pause
)
