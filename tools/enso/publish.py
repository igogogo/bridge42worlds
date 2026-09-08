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
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

# Журнал значений собирается тем же refresh и читается панелью — без него стрелки «с прошлого
# значения» на проде отстают от чисел.
FILES = ["data/enso/latest.json", "data/enso/history.json", "data/enso/glossary.json", "data/enso/journal.json",
         "data/enso/news.json",
         # береговая линия карты: Natural Earth 110m, общественное достояние, атрибуция не нужна
         "data/enso/coast.json",
         # ЭТИХ ТРЁХ ЗДЕСЬ НЕ БЫЛО (найдено 06.09): панель их читает, а выкладка не отправляла.
         # Разметка ссылок обновляется каждую неделю — без неё на сайте висела бы прошлая.
         "data/enso/links.json", "data/enso/chain-ref.json", "data/enso/models-ref.json",
         # облако понятий у каждого якоря панели (concepts_link.py, 08.09)
         "data/enso/concepts.json",
         # КОД ПАНЕЛИ ЕДЕТ ВМЕСТЕ С ДАННЫМИ (проверка Fable 06.09): снимок прошлого прогона ключит
         # риски по id, историю вердиктов с поправками рисует JS — старый enso.js со свежими
         # данными показал бы все риски как «new». Файлы статические, пересборки сайта не нужно.
         "enso.html", "js/enso.js",
         # движок мини-графа понятий — общий с страницами понятий; панель грузит его по кнопке (08.09)
         "js/b42-graph-core.js", "js/b42-mini.js",
         # служебный слой (владелец 06.09): свежее-не-разобранное и журнал прогонов с состоянием источников
         "data/enso/fresh.json", "data/enso/ops.json", "data/enso/runs.json",
         # раздел истории измерений (planet.py): медленные ряды, обновляются ежедневной обёрткой
         "data/enso/planet.json",
         # лента упоминаний (mentions.py) и Ховмёллер (subsurface.godas), тоже из ежедневной обёртки
         "data/enso/mentions.json", "data/enso/hovmoller.json", "data/enso/spectral.json", "data/enso/regions-daily.json", "data/enso/precip.json", "data/enso/radiance.json", "data/enso/neighbours.json", "data/enso/globe.json",
         # кадры анимации разреза прошлых событий (subsurface.py --hov), грузятся по требованию
         "data/enso/sections-1982.json", "data/enso/sections-1997.json", "data/enso/sections-2015.json", "data/enso/sections-2023.json"]
FRESH_FILES = ["data/enso/fresh.json", "data/enso/ops.json", "data/enso/runs.json", "data/enso/planet.json",
               "data/enso/mentions.json", "data/enso/hovmoller.json", "data/enso/spectral.json", "data/enso/regions-daily.json", "data/enso/precip.json", "data/enso/radiance.json", "data/enso/globe.json", "data/enso/sections-1982.json", "data/enso/sections-1997.json", "data/enso/sections-2015.json", "data/enso/sections-2023.json"]


def stamp_asset():
    """Версия скрипта в адресе — от содержимого скрипта, иначе выкладка бессмысленна.

    Дважды за 06.09 файл js/enso.js правили, а `?v=` в enso.html оставался прежним: на
    сайте у вернувшегося читателя оставался СТАРЫЙ скрипт из кэша края, и свежие данные он
    читал старым кодом. Ловушка повторяемая, поэтому проверка стоит прямо перед заливкой,
    а не в чьей-то памяти.
    """
    js = ROOT / "js" / "enso.js"
    html = ROOT / "enso.html"
    if not (js.exists() and html.exists()):
        return
    h = hashlib.md5(js.read_bytes()).hexdigest()[:10]
    t = html.read_text(encoding="utf-8")
    cur = re.search(r"/js/enso\.js\?v=([0-9a-f]+)", t)
    if cur and cur.group(1) == h:
        return
    html.write_text(re.sub(r"/js/enso\.js\?v=[0-9a-f]+", "/js/enso.js?v=" + h, t), encoding="utf-8")
    print(f"версия скрипта поднята: {cur.group(1) if cur else '—'} → {h} (иначе на сайте остался бы прежний код)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--cached", action="store_true", help="без сети, из последних удачных копий")
    ap.add_argument("--refresh", action="store_true",
                    help="сперва обновить данные (иначе выкладывается уже посчитанное)")
    ap.add_argument("--fresh", action="store_true",
                    help="выложить только свежий слой и журнал прогонов (после лёгкого прогона)")
    a = ap.parse_args()
    import ops as OPSLOG

    if a.fresh:
        # Лёгкий прогон не меняет разобранного состояния: на сайт едут только fresh/ops/runs.
        run = OPSLOG.Run("publish-fresh")
        env = dict(os.environ, B42_DEPLOY_OK="1", PYTHONIOENCODING="utf-8")
        rc = subprocess.run([sys.executable, "cloudflare/deploy_r2.py", "--only", *FRESH_FILES], cwd=str(ROOT), env=env).returncode
        run.finish("ok" if rc == 0 else "failed", files=len(FRESH_FILES))
        print("выкладка свежего слоя:", "ок" if rc == 0 else f"код {rc}")
        return rc

    if a.refresh:
        # Пересчёт переписывает вердикт моделью: то, что было просмотрено до этого, на сайт
        # уже не попадёт. Поэтому он не по умолчанию, а по прямой просьбе.
        print("пересчёт перед выкладкой: вердикт будет написан заново")
        import refresh
        cur = refresh.main(fetch=not a.cached, llm=not a.no_llm)
    else:
        cur = json.loads((ROOT / "data" / "enso" / "latest.json").read_text(encoding="utf-8"))
        print("выкладываю посчитанное:", cur.get("stamp"), "(пересчитать — ключ --refresh)")
    s = cur.get("summary") or {}
    print("\n— итог —")
    print(f"индекс {cur['risk_index']} · рисков {len(cur['risks'])} · тревога {'ДА' if cur.get('shout') else 'нет'}"
          f" · саммари {s.get('model')}{' (' + s['error'] + ')' if s.get('error') else ''}")
    print("вердикт:", (s.get("verdict") or "")[:300])
    stale = [k for k, v in cur["sources"].items() if not v["fresh"]]
    if stale:
        print("не ответили источники:", ", ".join(stale))
    if a.dry:
        return 0
    if not a.yes:
        ans = input("Выложить на сайт? [y/N] ").strip().lower()
        if ans not in ("y", "yes", "д", "да"):
            print("не выкладываю")
            return 0
    stamp_asset()
    run = OPSLOG.Run("publish")
    env = dict(os.environ, B42_DEPLOY_OK="1", PYTHONIOENCODING="utf-8")
    rc = subprocess.run([sys.executable, "cloudflare/deploy_r2.py", "--only", *FILES], cwd=str(ROOT), env=env).returncode
    run.finish("ok" if rc == 0 else "failed", stamp=cur.get("stamp"), files=len(FILES),
               reviewed=bool((s.get("review") or {}).get("stamp") == cur.get("stamp")))
    print("выкладка:", "ок" if rc == 0 else f"код {rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
