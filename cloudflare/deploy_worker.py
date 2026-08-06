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


def main():
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
    return subprocess.run(cmd, cwd=HERE, shell=True).returncode


if __name__ == "__main__":
    sys.exit(main())
