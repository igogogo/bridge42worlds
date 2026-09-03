#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Обновление дашборда Эль-Ниньо на сайте одной командой: пересчёт → выкладка JSON.

Владелец 03.09: «обновлять в полуавтоматическом режиме под твоим супервайзом, когда
скажу». Поэтому здесь нет планировщика: команду запускает ведущая сессия, глазами
смотрит итог (тревоги, саммари) и только потом выкладывает. Сайт не пересобирается:
страница читает data/enso/latest.json и history.json с нашего домена, обновить их —
значит обновить дашборд.

    python tools/enso/publish.py            # сеть + модель, показать итог, спросить, выложить
    python tools/enso/publish.py --yes      # без вопроса
    python tools/enso/publish.py --dry      # пересчитать и показать, не выкладывать
    python tools/enso/publish.py --no-llm   # без модели (саммари прежнее, с пометкой)
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

FILES = ["data/enso/latest.json", "data/enso/history.json", "data/enso/glossary.json"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--cached", action="store_true", help="без сети, из последних удачных копий")
    a = ap.parse_args()

    import refresh
    cur = refresh.main(fetch=not a.cached, llm=not a.no_llm)
    s = cur.get("summary") or {}
    print("\n— итог —")
    print(f"индекс {cur['risk_index']} · рисков {len(cur['risks'])} · тревога {'ДА' if cur.get('shout') else 'нет'}"
          f" · саммари {s.get('model')}{' (' + s['error'] + ')' if s.get('error') else ''}")
    print("вердикт:", (s.get("verdict") or "")[:300])
    stale = [k for k, v in cur["sources"].items() if not v["fresh"]]
    if stale:
        print("несвежие источники:", ", ".join(stale))
    if a.dry:
        return 0
    if not a.yes:
        ans = input("Выложить на сайт? [y/N] ").strip().lower()
        if ans not in ("y", "yes", "д", "да"):
            print("не выкладываю")
            return 0
    env = dict(os.environ, B42_DEPLOY_OK="1", PYTHONIOENCODING="utf-8")
    rc = subprocess.run([sys.executable, "cloudflare/deploy_r2.py", "--only", *FILES], cwd=str(ROOT), env=env).returncode
    print("выкладка:", "ок" if rc == 0 else f"код {rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
