@echo off
rem KIS auto-buy bot launcher (DRYRUN - no real orders). Double-click to run.
rem Stop: Ctrl+C in this window, or create file scripts\autobuy\_run\KILL
chcp 65001 >nul
cd /d C:\Users\hanul\playground\my-stock-master
echo ============================================
echo   KIS Auto-Buy Bot  [ DRYRUN - no real order ]
echo   New buys 09:05-15:20, uptrend only.
echo   Stop: Ctrl+C
echo ============================================
echo.
python -X utf8 scripts\autobuy\runner.py
echo.
echo ============================================
echo   Bot stopped. Press any key to close.
echo ============================================
pause >nul
