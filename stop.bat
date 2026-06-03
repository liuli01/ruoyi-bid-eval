@echo off
chcp 65001 >nul

echo Stopping ruoyi-bid-eval backend...

set COUNT=0
for /f "tokens=5" %%p in ('netstat -ano ^| findstr LISTEN ^| findstr ":9100 "') do (
    taskkill /F /PID %%p >nul 2>&1
    set /a COUNT=COUNT+1
)

if %COUNT% equ 0 (
    echo  No backend process found on port 9100.
) else (
    echo  Stopped %COUNT% process(es).
)

pause
