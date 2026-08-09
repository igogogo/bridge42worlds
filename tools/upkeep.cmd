@echo off
REM Уход за архивом после пополнения: разметка вектором + починка связей графа.
REM Ставится в планировщик задачей b42_upkeep, раз в сутки, ПОСЛЕ окна генерации.
REM
REM Почему две работы одной задачей, а не двумя. Обе нужны ровно после того, как архив
REM пополнился, и обе бесполезны, если он не пополнялся. Разнесённые по разным расписаниям,
REM они однажды разъедутся во времени — и починка графа отработает до разметки, то есть
REM по вчерашним связям. Порядок здесь важнее экономии одной строки в планировщике.
REM
REM Модель не зовётся ни там, ни там: разметка идёт по уже посчитанным векторам, починка —
REM по существующим связям. Значит задача бесплатная и её не надо согласовывать с бюджетом.

setlocal
set "REPO=C:\Users\nadez\PycharmProjects\bridge42worlds"
set "LOGDIR=%REPO%\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

for /f %%I in ('powershell -NoProfile -Command Get-Date -Format yyyyMMdd_HHmm') do set "STAMP=%%I"

cd /d "%REPO%"
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

python "%REPO%\tools\tag_by_vector.py" >> "%LOGDIR%\upkeep_%STAMP%.log" 2>&1
set RC=%ERRORLEVEL%

REM Починку графа запускаем ДАЖЕ если разметка споткнулась: она чинит то, что уже есть,
REM и от неудачи предыдущего шага хуже не станет. А вот код неудачи запоминаем — иначе
REM «упало первое, отработало второе» отчитается как успех.
python "%REPO%\tools\graph_repair.py" >> "%LOGDIR%\upkeep_%STAMP%.log" 2>&1
if not "%ERRORLEVEL%"=="0" set RC=%ERRORLEVEL%

echo [%DATE% %TIME%] upkeep rc=%RC% >> "%LOGDIR%\upkeep-history.log"

if not "%RC%"=="0" (
  python "%REPO%\tools\status_tg.py" --run-failed upkeep %RC% "logs\upkeep_%STAMP%.log"
)
endlocal & exit /b %RC%
