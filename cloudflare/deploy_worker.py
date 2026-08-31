"""Выкладка Worker — единственная команда, которой это делается.

    python cloudflare/deploy_worker.py

Зачем обёртка вместо прямого `npx wrangler deploy`. Замок (predeploy_check.py) полезен
ровно настолько, насколько его невозможно забыть позвать. Отдельным скриптом его забудут
в первый же занятый вечер — как забыли правило 6б, записанное словами, и дважды за сутки
откатили друг другу выкладку. Здесь проверка и выкладка — одно действие.

Что делает: прогоняет замок (не главная ли папка, не отстала ли копия от main, нет ли
незакоммиченного в cloudflare/), и только при чистом результате зовёт wrangler.
"""
import os, sys, subprocess
from pathlib import Path
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
# Токен подхватываем сами. Первая же выкладка этой обёрткой упала: wrangler не видел
# CLOUDFLARE_API_TOKEN, потому что раньше я всегда делал `source .env` руками. Обёртка,
# которая работает только если вызвавший что-то не забыл, — ровно то, от чего мы уходим.
load_dotenv(HERE.parent / ".env")


KNOWN_FLAGS = {"--dev"}


def main():
    # Неизвестный флаг — СТОП, а не «сделаю обычное».
    #
    # 6 августа я запустил эту команду с --dev из ветки, где поддержки --dev ещё не было.
    # Скрипт не знал флага, промолчал и выложил БОЕВОЙ Worker — выкладка без разрешения,
    # ровно то, от чего стоит замок. Виновата не невнимательность: молчаливое игнорирование
    # непонятного аргумента превращает опечатку в выкатку на прод. Здесь цена ошибки
    # односторонняя, поэтому по умолчанию — отказ.
    unknown = [a for a in sys.argv[1:] if a not in KNOWN_FLAGS]
    if unknown:
        print(f"⛔ не знаю аргумент(ы): {' '.join(unknown)}")
        print(f"   Знаю только: {', '.join(sorted(KNOWN_FLAGS))}")
        print("   Ничего не выкладываю: непонятная команда не должна означать выкатку на прод.")
        return 2

    # --dev выкладывает ИСПЫТАТЕЛЬНЫЙ Worker: своё имя, без маршрутов на домен и без
    # расписаний (cloudflare/wrangler.dev.toml). Он никого не обслуживает, поэтому и замок
    # ему не нужен — замок стоит на пути к читателю, а не на пути к проверке.
    dev = "--dev" in sys.argv
    if not dev:
        check = subprocess.run([sys.executable, str(HERE / "predeploy_check.py")],
                               env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        if check.returncode != 0:
            return check.returncode

    cmd = "npx wrangler deploy" + (" --config wrangler.dev.toml" if dev else "")
    print(f"\n▶️  {cmd}\n")
    # shell=True — на Windows npx это .cmd, без оболочки он не находится.
    r = subprocess.run(cmd, cwd=HERE, shell=True, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    print(out)
    if r.returncode == 0:
        return 0

    # КОД УЕХАЛ, А КРАСНЫМ ГОРИТ ОТКАЗ ПО МАРШРУТАМ.
    #
    # У токена нет прав на зону www.bridge42worlds.academy, и wrangler после
    # успешной загрузки воркера падает на попытке ПЕРЕЗАПИСАТЬ маршруты. Маршруты
    # при этом на месте и менять их не требуется — 30 августа проверено на живом
    # проде: воркер отвечал новым кодом, а шаг конвейера считался сбойным.
    #
    # Отличаем одно от другого по собственному отчёту wrangler: есть «Uploaded» и
    # версия — значит воркер выложен. Тогда это предупреждение, а не сбой; но
    # предупреждение громкое, чтобы права однажды выдали и строка ушла.
    # Признак «код уехал» ищем по нескольким строкам, а не по одной паре: у разных
    # версий wrangler отчёт разный. 31 августа шаг снова покраснел, хотя воркер
    # выложился: в отчёте были «Uploaded bridge42worlds» и «Deployed … triggers»,
    # а строки «Current Version ID» — не было вовсе, и проверка её не нашла.
    uploaded = any(m in out for m in
                   ("Current Version ID", "Total Upload", "Deployed bridge42worlds"))         and "Uploaded" in out
    routes_only = uploaded and ("workers/routes" in out or "Authentication error" in out)
    if routes_only:
        print("⚠️  Воркер ВЫЛОЖЕН, но маршруты зоны обновить не удалось: у токена нет "
              "прав на зону. Маршруты и так на месте — это не сбой выкладки.")
        print("   Чтобы строка ушла: дать токену право Zone → Workers Routes → Edit.")
        return 0
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
