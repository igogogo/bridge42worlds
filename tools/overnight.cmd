@echo off
REM Ночная накачка архива. Ставится в планировщик задачей b42_overnight, раз в сутки.
REM
REM Зачем расписанием, а не руками. Прямые слова владельца 9 августа: «не забывать разовое
REM переводить в продакшн». То, что гоняется из чьей-то сессии, работает ровно до дня, когда
REM эту сессию не открыли, — а узнаём мы об этом по остановившейся ленте через неделю.
REM
REM Потолок расхода задаёт владелец (4–5 долларов в сутки) и держит сам overnight.py через
REM budget_guard: здесь мы его НЕ дублируем числом. Два места с одним потолком расходятся
REM в первый же раз, когда цифру меняют в одном из них.
REM
REM Дешёвое окно DeepSeek: запускать между 00:30 и 08:00 по нашему времени — ночью цена
REM вдвое ниже. Это не украшение: ровно из этой разницы и берётся половина суточной нормы.

setlocal
set "REPO=C:\Users\nadez\PycharmProjects\bridge42worlds"
set "LOGDIR=%REPO%\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

for /f %%I in ('powershell -NoProfile -Command Get-Date -Format yyyyMMdd_HHmm') do set "STAMP=%%I"

cd /d "%REPO%"
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

python "%REPO%\tools\overnight.py" >> "%LOGDIR%\overnight_%STAMP%.log" 2>&1
set RC=%ERRORLEVEL%

echo [%DATE% %TIME%] overnight rc=%RC% >> "%LOGDIR%\overnight-history.log"

if not "%RC%"=="0" (
  python "%REPO%\tools\status_tg.py" --run-failed overnight %RC% "logs\overnight_%STAMP%.log"
)
endlocal & exit /b %RC%
