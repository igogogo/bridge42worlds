@echo off
REM Обновление витрины и отчёт по читателям. Ставится в планировщик задачей b42_stats.
REM
REM Владелец 2026-08-06: «сделай, чтобы мы видели и обновлялось каждые 8 часов»,
REM «в канал каждый день надо писать сколько посетителей, сколько страниц посмотрели —
REM это сейчас важный момент, надо контролировать».
REM
REM Почему это отдельная задача, а не хвост ночного прогона: ночной прогон делает статьи
REM и стоит денег, а этот — только пересчёт по локальным данным и выкладка нескольких
REM файлов, без единого обращения к модели. Его можно гонять часто и не думать о цене.
REM
REM Расписание: каждые 8 часов. Сообщение в канал уходит с КАЖДОГО прогона — владелец
REM просил видеть числа, а не догадываться, обновилось ли.

setlocal
set "REPO=C:\Users\nadez\PycharmProjects\bridge42worlds"
set "LOGDIR=%REPO%\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

for /f %%I in ('powershell -NoProfile -Command Get-Date -Format yyyyMMdd_HHmm') do set "STAMP=%%I"

cd /d "%REPO%"
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

python tools\stats_refresh.py >> "%LOGDIR%\stats_%STAMP%.log" 2>&1
set RC=%ERRORLEVEL%

echo [%DATE% %TIME%] stats rc=%RC% >> "%LOGDIR%\stats-history.log"

REM Неудача пересчёта — тоже новость: молчащая витрина выглядит как работающая.
if not "%RC%"=="0" (
  python "%REPO%\tools\status_tg.py" "stats refresh failed rc=%RC% see logs\stats_%STAMP%.log"
)
endlocal & exit /b %RC%
