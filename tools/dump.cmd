@echo off
REM Обновление локального дампа arXiv. Ставится в планировщик задачей b42_dump,
REM раз в две недели.
REM
REM Зачем отдельной задачей, а не «когда вспомним»: у нас ДВА источника статей и у каждого
REM своя работа (решение владельца 2026-08-04):
REM   · живой API   — ежедневная лента, за позавчера (arXiv досыпает работы с задержкой);
REM   · локальный дамп — догон истории, поиск дыр в покрытии, ретроспектива и вектор.
REM Дамп на 2026-08-04 кончался июлем: пока его не обновляют, любая ретроспектива отстаёт
REM на месяцы, а поиск «чего у нас нет» ищет в устаревшем поле. Обновление бесплатное,
REM забыть о нём — единственный способ его сломать.
REM
REM Русский текст сообщений собирает сам status_tg.py: консоль Windows отдаёт аргументы
REM в OEM-кодировке, и русские строки отсюда уходили в канал кракозябрами (2026-08-04).

setlocal
set "REPO=C:\Users\nadez\PycharmProjects\bridge42worlds"
set "LOGDIR=%REPO%\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

for /f %%I in ('powershell -NoProfile -Command Get-Date -Format yyyyMMdd_HHmm') do set "STAMP=%%I"

cd /d "%REPO%"
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

python "%REPO%\tools\update_arxiv_dump.py" >> "%LOGDIR%\dump_%STAMP%.log" 2>&1
set RC=%ERRORLEVEL%

echo [%DATE% %TIME%] dump rc=%RC% >> "%LOGDIR%\dump-history.log"

if not "%RC%"=="0" (
  python "%REPO%\tools\status_tg.py" --dump-failed %RC% "logs\dump_%STAMP%.log"
)
endlocal & exit /b %RC%
