@echo off
rem Morning brief launcher. Double-click to run.
rem   Reads last night's US close, computes each sector's excess return over the
rem   S&P500, and lists today's watch-list stocks in the leading sectors with
rem   their pivot prices. Saves a dated file for later scoring.
rem   It never buys - read it and decide for yourself.
rem
rem Best time: 07:00-08:00 KST.
rem   US closes 05:00 (DST) or 06:00 KST; NXT pre-market opens 08:00.
rem   Finish by 08:50 to leave time for placing reservations.
rem
rem Takes about 40 seconds - it fetches ~60 US tickers one by one.
rem
rem NOTE: keep this file ASCII-only. cmd reads .bat as cp949 before chcp runs,
rem       so UTF-8 Korean here gets mangled into stray command separators.
chcp 65001 >nul
cd /d C:\Users\hanul\playground\my-stock
echo.
echo Fetching last night's US close. This takes about 40 seconds...
echo.
python -X utf8 scripts\build_morning_brief.py --save %*
if errorlevel 1 (
  echo.
  echo FAILED. Common causes:
  echo   - public\data\sector-map.json missing
  echo       fix: python -X utf8 scripts\build_sector_map.py --save
  echo   - no network, or FinanceDataReader cannot reach Yahoo
)
echo.
echo Press any key to close.
pause >nul
