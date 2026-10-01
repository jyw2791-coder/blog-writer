@echo off
cd /d "%~dp0"
title AI Blog Writer

echo.
echo ============================================
echo   AI Blog Writer
echo ============================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [Setup needed] Please run "install" script first.
    echo.
    pause
    exit /b 1
)

echo Starting the app...
echo Your browser will open automatically. If not, go to: http://localhost:8501
echo To stop: close this window or press Ctrl+C
echo.

start "" /min cmd /c "timeout /t 2 > nul & start http://localhost:8501"

".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false

echo.
echo [App stopped]
pause
