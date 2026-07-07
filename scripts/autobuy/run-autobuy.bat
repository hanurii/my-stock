@echo off
rem KIS 자동매수 봇 실행 런처 (dryrun — 실주문 안 나감)
rem 더블클릭하면 실행됩니다. 중단: 이 창에서 Ctrl+C, 또는 scripts\autobuy\_run\KILL 파일 생성.
chcp 65001 >nul
cd /d C:\Users\hanul\playground\my-stock-master
echo ============================================
echo   KIS 자동매수 봇 (dryrun) 시작
echo   - 실주문 안 나감(로그만)
echo   - 장중(09:05~15:20 신규매수), 상승추세일 때만 가동
echo   중단: Ctrl+C
echo ============================================
echo.
python -X utf8 scripts\autobuy\runner.py
echo.
echo ============================================
echo   봇 종료됨. 창을 닫으려면 아무 키나 누르세요.
echo ============================================
pause >nul
