@echo off
chcp 65001 > nul
echo.
echo ====================================
echo   AI 블로그 작성 도우미 시작
echo ====================================
echo.

if not exist ".venv" (
    echo [1/3] 가상환경 생성 중...
    python -m venv .venv
)

echo [2/3] 패키지 설치 확인 중...
call .venv\Scripts\activate.bat
pip install -r requirements.txt -q

echo [3/3] 앱 실행 중...
echo.
echo 브라우저에서 http://localhost:8501 으로 접속하세요
echo 종료하려면 Ctrl+C 를 누르세요
echo.
streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
