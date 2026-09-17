@echo off
rem Pivot-proximity alert launcher. Double-click to run.
rem   Watches detected SEPA candidates; alerts when price is within 2% below pivot.
rem   It never buys - it only tells you when to place a reservation.
rem Stop: Ctrl+C in this window, or just close it.
rem NOTE: keep this file ASCII-only. cmd reads .bat as cp949 before chcp runs,
rem       so UTF-8 Korean here gets mangled into stray command separators.
chcp 65001 >nul
cd /d C:\Users\hanul\playground\my-stock
python -X utf8 scripts\pivot_alert.py --interval 60 --until 20:00 -v %*
echo.
echo Stopped. Press any key to close.
pause >nul
