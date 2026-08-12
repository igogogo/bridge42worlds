@echo off
REM Фабрика: единственный конвейерный прогон в сутки. Задача планировщика b42_factory.
REM
REM Заменяет собой три задачи, которые делили одно дерево и не знали друг о друге:
REM b42_overnight (01:00), b42_daily (03:30), b42_upkeep (06:30). 12 августа ночной
REM прогон шёл до 10:26 и физически накрыл окна обоих остальных — upkeep запустился
REM поверх работающей генерации, и в логе честно написано «идёт пересборка сайта,
REM публикация в R2 не удалась». Пока денег было много, это выглядело как «просто
REM подождём»; на остатке в полтора доллара стало видно, что решать, ЧТО делать
REM сегодня, должен один хозяин с бюджетом перед глазами.
REM
REM ВРЕМЯ. 13:00, а не ночь. Причина не в удобстве: хвост суток arXiv закрывает по UTC,
REM и запрос в 01:00 локального (22:00 UTC предыдущего дня) честно возвращает ноль
REM статей — проверено по temp/2026-08-11/arxiv-api.xml. Ночной прогон годами добирал
REM историю из дампа, а свежий день брать было нечем.
REM
REM Дешёвое окно DeepSeek (00:30-08:00) сейчас роли не играет: тарифных окон у v4 нет,
REM подтверждено оплатой (см. common.guard_peak). Вернут — включим B42_PEAK_ENFORCE=1.

setlocal
set "REPO=C:\Users\nadez\PycharmProjects\bridge42worlds"
set "LOGDIR=%REPO%\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

for /f %%I in ('powershell -NoProfile -Command Get-Date -Format yyyyMMdd_HHmm') do set "STAMP=%%I"

cd /d "%REPO%"
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
REM Пересборку сайта фабрика делает сама последним шагом — значит она и есть ведущая.
set B42_LEAD=1

REM Подъём сторожей: оба (почта и очередь заказов) — долгоживущие процессы, которые
REM однажды убило закрытием консоли, и 43 часа никто не читал почту. Start-ScheduledTask
REM прав администратора не требует и живого не трогает.
powershell -NoProfile -Command "foreach($t in 'b42_mail_temp','b42_queue'){ if((Get-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue).State -ne 'Running'){ Start-ScheduledTask -TaskName $t } }" >nul 2>&1

python "%REPO%\tools\factory.py" >> "%LOGDIR%\factory_%STAMP%.log" 2>&1
set RC=%ERRORLEVEL%

echo [%DATE% %TIME%] factory rc=%RC% >> "%LOGDIR%\factory-history.log"

if not "%RC%"=="0" (
  python "%REPO%\tools\status_tg.py" --run-failed factory %RC% "logs\factory_%STAMP%.log"
)
endlocal & exit /b %RC%
