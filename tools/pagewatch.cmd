@echo off
REM Сторож живой страницы. Ставится в планировщик задачей b42_pagewatch, раз в час.
REM
REM Что он ловит и почему этого не ловил никто другой. 14 августа главная не показала
REM ни одной статьи на всех пяти языках, отдаваясь с кодом 200. Наши сторожа смотрят
REM свежесть данных и доступность файлов — оба были довольны. Лента рисуется javascript'ом
REM уже в браузере, и увидеть её отсутствие можно только браузером.
REM
REM Раз в час, а не раз в сутки: заметил владелец, к середине дня. Час — это цена
REM пустой главной, которую мы согласны платить; сутки — уже нет.
REM
REM Проверка бесплатная: модель не зовётся, страницы скачиваются с нашего же сайта.

setlocal
set "REPO=C:\Users\nadez\PycharmProjects\bridge42worlds"
set "LOGDIR=%REPO%\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

for /f %%I in ('powershell -NoProfile -Command Get-Date -Format yyyyMMdd_HHmm') do set "STAMP=%%I"

cd /d "%REPO%"
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

REM Сторож сам пишет в канал, когда находит беду, — status_tg отсюда не зовём,
REM иначе о неудаче сообщат дважды разными словами.
python "%REPO%\tools\page_watch.py" --quiet >> "%LOGDIR%\pagewatch_%STAMP%.log" 2>&1
set RC=%ERRORLEVEL%

echo [%DATE% %TIME%] pagewatch rc=%RC% >> "%LOGDIR%\pagewatch-history.log"
endlocal & exit /b %RC%
