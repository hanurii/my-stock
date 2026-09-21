@echo off
rem Close-source check. Double-click to run.
rem   Compares FDR close vs KIS regular-session close across the watch list.
rem   Answers one question: did 2026-09-21 split overnight, as predicted?
rem   The pass/fail thresholds were frozen in the script on 2026-09-21 22:50,
rem   before any result was seen. Do not edit them after the fact.
rem Takes about 60 seconds.
rem NOTE: ASCII-only. cmd reads .bat as cp949 before chcp runs.
chcp 65001 >nul
cd /d C:\Users\hanul\playground\my-stock
echo.
echo Comparing close-price sources. This takes about a minute...
echo.
python -X utf8 scripts\check_close_source.py %*
echo.
echo Press any key to close.
pause >nul
