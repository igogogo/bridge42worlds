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
REM Дешёвое окно DeepSeek изменилось 16 августа 2026: теперь оно задано не «ночью», а
REM часами UTC — см. блок про расписание ниже. Прежняя формулировка «между 00:30 и 08:00»
REM устарела и вводила бы в заблуждение: часть этого промежутка стала как раз пиковой.

REM РАСПИСАНИЕ: 19:00 местного (UTC+3), а не 01:00, с 16 августа 2026.
REM
REM DeepSeek с 16.08.2026 считает по-разному часы пик и остальное время: вне пика ровно
REM вдвое дешевле. Пик по UTC — 01:00-04:00 и 06:00-10:00, у нас это 04:00-07:00 и
REM 09:00-13:00 местного. Прежний старт в 01:00 давал три часа работы (04:00-07:00) по
REM двойному тарифу — на нашем профиле это лишние доллары каждую ночь ни за что.
REM Старт в 19:00 даёт девять часов подряд вне пика: 19:00 вечера до 04:00 утра.
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
