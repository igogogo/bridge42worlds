@echo off
REM Сторож почты. Ставится в планировщик задачей b42_mail_temp.
REM
REM ⚠️ ВРЕМЕННАЯ задача — отсюда суффикс _temp в имени. Решение архитектора 2026-08-01:
REM принцип «ничего на машине владельца» нарушаем сознательно, потому что до переезда
REM в Containers несколько дней, а пропущенное письмо арабского автора (наша целевая
REM аудитория) стоит дороже этих дней. При переезде задачу СНЯТЬ — строка про это
REM стоит в плане переезда, ищите по имени b42_mail_temp.

setlocal
set "REPO=C:\Users\nadez\PycharmProjects\bridge42worlds"
set "LOGDIR=%REPO%\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

cd /d "%REPO%"
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

python tools\mail_watch.py --loop >> "%LOGDIR%\mail-watch.log" 2>&1
set RC=%ERRORLEVEL%

echo [%DATE% %TIME%] mail rc=%RC% >> "%LOGDIR%\mail-history.log"
endlocal & exit /b %RC%
