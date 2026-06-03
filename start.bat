@echo off
chcp 65001 >nul
title ruoyi-bid-eval

set BACKEND_DIR=%~dp0ruoyi-fastapi-backend
set LOG_FILE=%~dp0app.log

echo 1. Stopping old processes...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr LISTEN ^| findstr ":9100 "') do taskkill /F /PID %%p >nul 2>&1

echo 2. Waiting for port release...
timeout /t 3 /nobreak >nul

echo 3. Starting backend...
cd /d "%BACKEND_DIR%"
start "ruoyi-bid-eval" /B "%BACKEND_DIR%\.venv\Scripts\python.exe" "%BACKEND_DIR%\app.py" > "%LOG_FILE%" 2>&1

echo 4. Waiting for startup (20s)...
timeout /t 20 /nobreak >nul

echo.
echo ========================================
echo  Backend started
echo  Log: %LOG_FILE%
echo  API: http://localhost:9100/docs
echo ========================================
echo.
pause
