#!/usr/bin/env python3
"""Ночная накачка архива: идём по датам назад и добираем то, чего не хватает.

Владелец 2026-08-08: «просто запускай, пока есть деньги, накачку статей, можно на ночь
поставить — добрать чего не хватает, самое лучшее целиком, что-то среднее экспресс,
догоняем этот год, недостающие пустые разделы… есть там десятка, может больше долларов».

Своей генерации здесь НЕТ. Скрипт только решает, какой день брать следующим, и зовёт
`run.py range` — тот самый, что работает днём. Причина простая: своя копия конвейера
рано или поздно разойдётся с общим и начнёт повторять уже вылеченные болезни.

Что делает за ночь:
  1. Находит дни этого года, где статей меньше нормы, и идёт от свежих к старым.
  2. Каждый день добирает экспрессом — дёшево и быстро, охват важнее глубины.
  3. Следит за деньгами по строке «Статьи» бюджета и останавливается, не доедая её
     до нуля: дневная лента завтра тоже должна на что-то жить.

    python tools/overnight.py --budget 12        потратить не больше $12
    python tools/overnight.py --budget 12 --dry  показать план, ничего не запуская
"""
import argparse
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

# Разделы те же, что в дневном прогоне (tools/daily.cmd): расхождение списков означало бы,
# что ночь и день собирают разный корпус.
CATEGORIES = ("astro-ph.*,gr-qc,hep-th,hep-ph,hep-ex,nucl-th,nucl-ex,quant-ph,"
              "cond-mat.*,physics.*,q-bio.*,math-ph,math.*,cs.LG")
# Норма на день. Меньше — день считается недобранным и попадает в очередь ночи.
NORM = 20
# Сколько оставить на дневную ленту: ночь не должна съесть бюджет статей целиком.
KEEP_FOR_DAILY = 25.0


def coverage():
    """Сколько статей у нас на каждую дату этого года."""
    import collections
    p = ROOT / "lang" / "ru" / "articles-index.json"
    if not p.exists():
        return collections.Counter()
    idx = json.loads(p.read_text(encoding="utf-8"))
    return collections.Counter(a.get("date", "") for a in idx)


def gaps(year=None, norm=NORM):
    """Дни этого года, где статей меньше нормы — от свежих к старым.

    Свежие вперёд намеренно: статья вчерашнего дня ещё ищется людьми и авторами,
    статья мартовская — уже нет.
    """
    year = year or date.today().year
    have = coverage()
    out = []
    d = date.today()
    start = date(year, 1, 1)
    while d >= start:
        s = d.isoformat()
        if have.get(s, 0) < norm:
            out.append((s, have.get(s, 0)))
        d -= timedelta(days=1)
    return out


def spent_on_articles():
    try:
        import budget_guard as bg
        return bg.spend_by_line().get("Статьи", {})
    except Exception:
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=12.0, help="потолок расхода за прогон, $")
    ap.add_argument("--days", type=int, default=40, help="сколько дней взять за ночь")
    ap.add_argument("--per-day", type=int, default=25, help="статей на день")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    art = spent_on_articles()
    left = art.get("остаток", 0.0)
    print(f"бюджет статей: план ${art.get('план', 0):.0f}, потрачено ${art.get('потрачено', 0):.2f}, "
          f"остаток ${left:.2f}")
    allowed = min(args.budget, max(0.0, left - KEEP_FOR_DAILY))
    if allowed <= 0.5:
        print(f"⛔ на ночь денег нет: остаток ${left:.2f}, а на дневную ленту держим ${KEEP_FOR_DAILY:.0f}")
        return 1
    print(f"на ночь разрешено потратить: ${allowed:.2f}")

    todo = gaps()[: args.days]
    if not todo:
        print("✅ пропусков нет — весь год добран до нормы")
        return 0
    print(f"дней к добору: {len(todo)} (из {len(gaps())} недобранных за год)")
    for s, n in todo[:8]:
        print(f"   · {s}: сейчас {n} из {NORM}")

    if args.dry:
        print("\n[сухой прогон] ничего не запускаю")
        return 0

    start_spent = art.get("потрачено", 0.0)
    done = 0
    for s, _n in todo:
        now = spent_on_articles().get("потрачено", start_spent)
        if now - start_spent >= allowed:
            print(f"\n⏹️ потолок ночи выбран (${now - start_spent:.2f}) — останавливаюсь")
            break
        print(f"\n▶️ {s}")
        r = subprocess.run(
            [sys.executable, "run.py", "range", "--from", s, "--to", s,
             "--express", "--limit", str(args.per_day), "--category", CATEGORIES],
            cwd=ROOT, env={**__import__("os").environ, "B42_LEAD": "1", "B42_NO_PUBLISH": "1",
                           "PYTHONIOENCODING": "utf-8"},
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=7200)
        tail = (r.stdout or "").strip().splitlines()[-2:]
        print("   " + " | ".join(x.strip()[:90] for x in tail))
        if r.returncode != 0:
            print(f"   ⚠️ код {r.returncode} — иду дальше, день пропущен")
        else:
            done += 1

    fin = spent_on_articles()
    print(f"\n✅ ночь закончена: обработано дней {done}, "
          f"потрачено ${fin.get('потрачено', 0) - start_spent:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
