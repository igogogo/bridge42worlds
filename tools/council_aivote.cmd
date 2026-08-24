@echo off
REM Голосование ИИ-участников + напоминание людям. Суббота 10:00 — между рассылкой
REM повестки (пт) и закрытием (вс 21:00). До 2026-08-24 шага НЕ БЫЛО в расписании:
REM ai_vote запускали руками, и заседание 23.08 закрылось с нулём голосов — все
REM 16 вопросов уехали на следующую неделю. Автомат обязан голосовать сам.
setlocal
set "REPO=C:\Users\nadez\PycharmProjects\bridge42worlds"
set "LOGDIR=%REPO%\logs"
for /f %%I in ('powershell -NoProfile -Command Get-Date -Format yyyyMMdd_HHmm') do set "STAMP=%%I"
cd /d "%REPO%"
set PYTHONIOENCODING=utf-8
python tools\council_ai_vote.py >> "%LOGDIR%\council-aivote_%STAMP%.log" 2>&1
python tools\council_remind.py >> "%LOGDIR%\council-aivote_%STAMP%.log" 2>&1
endlocal
