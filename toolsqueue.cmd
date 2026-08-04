@echo off
REM Исполнитель очереди заказов. Ставится в планировщик задачей b42_queue.
REM
REM До этого держался скрытым процессом и умер бы с первой перезагрузкой — а кнопка
REM «перевести статью» уже на проде и принимает заказы. То есть мы обещали читателю
REM работу, которую некому делать (находка разработчика 2026-07-31).
REM
REM Живёт В РЕПОЗИТОРИИ по той же причине, что и daily.cmd: обёртка во временной папке
REM сессии не переживает перезагрузку, и задача тихо перестаёт запускаться.

setlocal
set "REPO=C:\Users\nadez\PycharmProjects\bridge42worlds"
set "LOGDIR=%REPO%\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

cd /d "%REPO%"
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

REM --loop: крутится и проверяет очередь раз в 30 секунд. Задача запускается при старте
REM машины и перезапускается при падении — то есть процесс живёт всегда.
REM Отметка «жив» пишется внутри скрипта: по ней сторож понимает, что исполнитель на месте.
python cloudflare\queue_worker.py --loop >> "%LOGDIR%\queue-worker.log" 2>&1
set RC=%ERRORLEVEL%

echo [%DATE% %TIME%] queue rc=%RC% >> "%LOGDIR%\queue-history.log"
endlocal & exit /b %RC%
