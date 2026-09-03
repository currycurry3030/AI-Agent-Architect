@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
title rag-lab

set PY=
where py >nul 2>&1 && set PY=py -3
if not defined PY (
    where python >nul 2>&1 && set PY=python
)
if not defined PY (
    echo.
    echo 파이썬을 찾지 못했습니다. 보조강사를 불러 주세요.
    echo.
    pause
    exit /b 1
)

%PY% app.py

echo.
echo 앱이 종료되었습니다.
pause