@echo off
REM Дотяжка экспрессов до полного разбора. Задача планировщика b42_uplift, 16:30.
REM
REM ПОЧЕМУ ОТДЕЛЬНАЯ ЗАДАЧА, А НЕ ШАГ ДНЕВНОГО ПРОГОНА. Дневной стартует в 03:30 и
REM работает часами — серединой он попадает в пиковый тариф DeepSeek (по Кувейту это
REM 04:00-07:00 и 09:00-13:00). На шести тысячах работ разница между пиком и дешёвым
REM окном около $110, и ради неё заход стоит отдельно.
REM
REM ТЕМП. Сто работ в сутки, шестьдесят дней (владелец 2026-09-01: «да растяни на два
REM хоть месяца»). Возобновляемость встроена: дотянутая работа перестаёт быть экспрессом
REM и в очередь больше не попадает — пропущенный день ничего не ломает, он лишь сдвигает
REM конец кампании на день.
REM
REM --wait, а не отказ по пику: молчаливый отказ каждый день означал бы кампанию, которая
REM никогда не двигается. Инструмент ждёт окна и отмечается в логе, чтобы ожидание нельзя
REM было спутать с зависанием.
REM
REM Замок дерева берёт сам инструмент (tools/runlock.py): если рядом идёт дневной прогон
REM или недельный, заход честно откажется, а не полезет писать те же файлы.

setlocal
set "REPO=C:\Users\nadez\PycharmProjects\bridge42worlds"
set "LOGDIR=%REPO%\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

REM wmic из Windows 11 выпилен — штамп через powershell (та же грабля, что у daily.cmd).
for /f %%I in ('powershell -NoProfile -Command Get-Date -Format yyyyMMdd_HHmm') do set "STAMP=%%I"

cd /d "%REPO%"
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

python tools\deep_uplift.py --limit 100 --wait --workers 12 >> "%LOGDIR%\uplift_%STAMP%.log" 2>&1
set RC=%ERRORLEVEL%

echo [%DATE% %TIME%] uplift rc=%RC% >> "%LOGDIR%\uplift-history.log"

if not "%RC%"=="0" (
  python "%REPO%\tools\status_tg.py" --run-failed uplift %RC% "logs\uplift_%STAMP%.log"
)
endlocal & exit /b %RC%
