@echo off
REM Календарь совета: пятница --notify (закрыть повестку, уведомить), воскресенье --close
REM (подвести итоги). Ставится в планировщик ДВУМЯ задачами b42_council_notify и
REM b42_council_close с разными аргументами.
REM
REM Почему это в планировщике, а не в чьих-то руках. Заседание 9 августа не состоялось
REM ровно потому, что скрипт был написан «для планировщика», но туда не поставлен:
REM пятница прошла без уведомлений, воскресенье — без итогов, и никто не заметил.
REM Владелец: «должно быть доведено до автомата, без костылей, которые сопровождают
REM каждое завершение работы — это автономный код».

setlocal
set "REPO=C:\Users\nadez\PycharmProjects\bridge42worlds"
set "LOGDIR=%REPO%\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
for /f %%I in ('powershell -NoProfile -Command Get-Date -Format yyyyMMdd_HHmm') do set "STAMP=%%I"

cd /d "%REPO%"
set PYTHONIOENCODING=utf-8
python tools\council_schedule.py %1 >> "%LOGDIR%\council_%STAMP%.log" 2>&1
set RC=%ERRORLEVEL%
echo [%DATE% %TIME%] council %1 rc=%RC% >> "%LOGDIR%\council-history.log"
if not "%RC%"=="0" (
  python tools\status_tg.py --council-failed %RC% "logs\council_%STAMP%.log" 2>nul
)
endlocal & exit /b %RC%
