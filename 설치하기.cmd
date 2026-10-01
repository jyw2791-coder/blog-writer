@echo off
chcp 65001 > nul
echo.
echo ============================================
echo   AI 블로그 작성기 - 설치 및 실행
echo ============================================
echo.

REM Python 설치 여부 확인
python --version > nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo.
    echo 아래 주소에서 Python을 먼저 설치해주세요:
    echo https://www.python.org/downloads/
    echo.
    echo 설치 시 반드시 "Add Python to PATH" 체크 후 설치!
    echo.
    pause
    start https://www.python.org/downloads/
    exit /b 1
)

python --version
echo Python 확인 완료!
echo.

REM 가상환경 생성
if not exist ".venv" (
    echo [1/3] 가상환경 생성 중... (최초 1회만 실행됩니다)
    python -m venv .venv
    if errorlevel 1 (
        echo [오류] 가상환경 생성 실패
        pause
        exit /b 1
    )
    echo 가상환경 생성 완료!
    echo.
)

REM 패키지 설치
echo [2/3] 필요한 패키지 설치 중... (최초 1회만 실행됩니다)
call .venv\Scripts\activate.bat
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [오류] 패키지 설치 실패
    pause
    exit /b 1
)
echo 패키지 설치 완료!
echo.

REM 앱 실행
echo [3/3] 앱 시작 중...
echo.
echo ============================================
echo   브라우저에서 자동으로 앱이 열립니다
echo   열리지 않으면: http://localhost:8501
echo   종료: 이 창을 닫거나 Ctrl+C
echo ============================================
echo.
streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
pause
