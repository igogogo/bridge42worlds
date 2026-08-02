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

REM Лог со штампом времени: общий файл держит открытым ранее запущенный экземпляр,
REM и тогда перенаправление падает, а строка с python не выполняется вовсе (поймано
REM на живом запуске 2026-08-01 — задача возвращала 0 при пустом логе).
for /f %%I in ('powershell -NoProfile -Command Get-Date -Format yyyyMMdd_HHmm') do set "STAMP=%%I"

cd /d "%REPO%"
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

python tools\mail_watch.py --loop >> "%LOGDIR%\mail-watch_%STAMP%.log" 2>&1
set RC=%ERRORLEVEL%

echo [%DATE% %TIME%] mail rc=%RC% >> "%LOGDIR%\mail-history.log"
endlocal & exit /b %RC%
