@echo off
REM Полный отчёт за вчерашние сутки в канал. Владелец встаёт в 4 утра — отчёт должен
REM ждать его к этому времени, а не приходить вечером по незакрытому дню.
set REPO=%~dp0..
cd /d "%REPO%"
python "%REPO%\tools\daily_report.py" --send >> "%REPO%\logs\report_%DATE:~-4%%DATE:~3,2%%DATE:~0,2%.log" 2>&1
