@echo off
REM Ежедневное пополнение ленты. Ставится в планировщик задачей b42_daily.
REM Живёт В РЕПОЗИТОРИИ, а не во временной папке сессии: прежняя обёртка лежала
REM в temp/claude/... — она пережила бы не всякую перезагрузку, а сама задача была
REM ОДНОРАЗОВОЙ (сработала 22 июля, результат 1) и больше не запускалась. Это и есть
REM вторая причина 13-дневного простоя, рядом с пустым кэшем arXiv (закрыт 30 июля).

setlocal
set "REPO=C:\Users\nadez\PycharmProjects\bridge42worlds"
set "LOGDIR=%REPO%\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value 2^>nul') do set "DT=%%I"
set "STAMP=%DT:~0,8%_%DT:~8,4%"

cd /d "%REPO%"
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
REM B42_LEAD не ставим: daily не пересобирает сайт целиком, страж html его и не касается.
REM Публикация в R2 идёт последним шагом самой команды — отдельного вызова не нужно.
python run.py daily --limit 20 --category "astro-ph.*,gr-qc,hep-th,quant-ph,cond-mat.*,physics.*" >> "%LOGDIR%\daily_%STAMP%.log" 2>&1
set RC=%ERRORLEVEL%

REM Хвост лога — в общий журнал, чтобы одним файлом видеть историю прогонов
echo [%DATE% %TIME%] daily rc=%RC% >> "%LOGDIR%\daily-history.log"
endlocal & exit /b %RC%
