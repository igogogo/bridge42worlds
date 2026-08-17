@echo off
REM Дайджест в Telegram-канал: три свежие статьи с обложками. Задача b42_digest.
REM
REM Аудит 16 августа, раздел «дистрибуция»: «дайджест не запущен НИ РАЗУ (нет задачи
REM в планировщике, нет канала); вернувшихся читателей — ноль, людям некуда
REM возвращаться». Инструмент tools/tg_digest.py был готов с 4 августа и ждал ровно
REM этого файла: публикация без ритма читателя не удерживает, а ритм создаёт
REM планировщик, не память человека.
REM
REM Расписание: раз в день в 18:00 — вечер по Заливу, люди листают ленту после работы.
REM Канал по умолчанию — служебный; когда владелец заведёт публичный, поменять одну
REM строку (--chat) здесь.

setlocal
set "REPO=C:\Users\nadez\PycharmProjects\bridge42worlds"
set "LOGDIR=%REPO%\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

for /f %%I in ('powershell -NoProfile -Command Get-Date -Format yyyyMMdd_HHmm') do set "STAMP=%%I"

cd /d "%REPO%"
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

python tools\tg_digest.py --n 3 >> "%LOGDIR%\digest_%STAMP%.log" 2>&1
set RC=%ERRORLEVEL%

echo [%DATE% %TIME%] digest rc=%RC% >> "%LOGDIR%\digest-history.log"

if not "%RC%"=="0" (
  python "%REPO%\tools\status_tg.py" --run-failed digest %RC% "logs\digest_%STAMP%.log"
)
endlocal & exit /b %RC%
