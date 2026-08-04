"""Очередь на полную сборку: какие экспресс-статьи дорастить до полного разбора.

Владелец 2026-08-04: «смотри, кто куда ходит; если ходят — переводи в лист ожидания на
полную сборку, чтобы это было автоматом. Экспресс хорошо, но полные тоже надо выращивать —
лучшие из лучших. А каким путём их искать, ML расскажет — даже если кликов не было».

Два источника, и второй важнее первого:

1. **ЧИТАЮТ** — статью открывают, значит она нужна людям. Прямой и честный сигнал.
   Ограничение сегодня: за неделю у нас 50 уникальных посетителей, статьи открывали 3 раза.
   На таком трафике одного этого источника мало — сигнал есть, но его почти нет.

2. **«БРИЛЛИАНТЫ» — наше мнение** (`data/diamonds.json`, готовит ML). Не «лучшее в науке»
   по цитированиям: ML показал числом, что верх списка по цитированиям — это релизы данных,
   описания приборов и обзоры миссий. Ищем недооценённое и необычное. Пока трафика мало,
   этот источник — основной.

Полная сборка стоит $0.039 против $0.0098 у экспресса, то есть вчетверо дороже. Поэтому
дорастить всё нельзя и не нужно: выбираем то, что читают или что того стоит.

    python tools/upgrade_queue.py --plan            показать очередь, ничего не делать
    python tools/upgrade_queue.py --run 5           дорастить пять верхних
    python tools/upgrade_queue.py --min-views 3     порог по читателям

Реюз оплаченного включён по умолчанию (`run.py regen`): текст экспресса, переводы аннотации
и подписей, обложка FLUX не создаются заново — платим только за то, чего не было.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import requests

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://bridge42worlds.academy"
QUEUE = ROOT / "data" / "upgrade-queue.json"
ID_RE = re.compile(r"/archive/\d{4}-\d{2}-\d{2}/([^/]+)/")


def views(days=30):
    """Сколько раз открывали каждую статью. Язык не различаем: интерес к работе один,
    на каком языке её прочли — вопрос аудитории, а не ценности статьи."""
    out = {}
    try:
        r = requests.get(f"{SITE}/api/stats?days={days}", timeout=30)
        for p in (r.json().get("byPath") or []):
            m = ID_RE.search(p.get("path", ""))
            if m:
                out[m.group(1)] = out.get(m.group(1), 0) + int(p.get("n", 0))
    except Exception as e:
        print(f"⚠️ статистика недоступна ({type(e).__name__}) — работаем по «бриллиантам»")
    return out


def diamonds():
    """Наше мнение о ценности — список от ML. Пока его нет, источник просто пуст:
    очередь тогда работает на одних читателях, а не выдумывает себе кандидатов."""
    p = ROOT / "data" / "diamonds.json"
    if not p.exists():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(d, dict):
            return {k: float(v) for k, v in d.items()}
        return {x["id"]: float(x.get("score", 1)) for x in d}
    except Exception:
        return {}


def express_articles():
    """Экспресс-статьи: только их имеет смысл доращивать. У полных разбор уже есть."""
    out = {}
    for p in (ROOT / "lang/ru/archive").glob("*/*/data.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not d.get("express"):
            continue
        v = (d.get("popular", {}) or {}).get("ru") or (d.get("simple", {}) or {}).get("ru") or {}
        out[p.parent.name] = {"title": v.get("title", p.parent.name), "date": d.get("date", "")}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--run", type=int, default=0)
    ap.add_argument("--min-views", type=int, default=2)
    ap.add_argument("--days", type=int, default=30)
    args = ap.parse_args()

    exp = express_articles()
    vs = views(args.days)
    dm = diamonds()

    rows = []
    for aid, meta in exp.items():
        v = vs.get(aid, 0)
        d = dm.get(aid, 0)
        if v < args.min_views and not d:
            continue
        # Читатели весомее нашего мнения: живой человек открыл статью — это факт,
        # а «бриллиант» пока гипотеза. Но при нулевом трафике гипотеза лучше пустоты.
        rows.append({"id": aid, "views": v, "diamond": round(d, 3),
                     "score": v * 10 + d, **meta})
    rows.sort(key=lambda x: -x["score"])

    QUEUE.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"экспресс-статей {len(exp)} · с читателями {sum(1 for r in rows if r['views'])} · "
          f"из «бриллиантов» {sum(1 for r in rows if r['diamond'])} · в очереди {len(rows)}")
    for r in rows[:12]:
        why = f"читали {r['views']}" if r["views"] else f"бриллиант {r['diamond']}"
        print(f"  {why:>16} · {r['date']} · {r['title'][:52]}")
    if not rows:
        print("\nОчередь пуста. Это не поломка: статьи почти не открывают (за неделю "
              "50 уникальных), а список «бриллиантов» от ML ещё не готов. Появится любой "
              "из двух источников — очередь наполнится сама.")
        return 0

    if args.run:
        print(f"\nдоращиваю {min(args.run, len(rows))} статей до полного разбора…")
        for r in rows[:args.run]:
            print(f"\n▶ {r['id']} · {r['title'][:50]}")
            subprocess.run([sys.executable, "run.py", "regen", r["id"]], cwd=str(ROOT))
    else:
        print(f"\nочередь записана: {QUEUE}. Дорастить: --run N")
    return 0


if __name__ == "__main__":
    sys.exit(main())
