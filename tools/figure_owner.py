# -*- coding: utf-8 -*-
"""Чья это схема: карта «родная тема» и список шагов с чужой картинкой.

Повод. Схемы в js/figures.js вызываются без аргументов и рисуют фиксированный сюжет. Пока схему
берёт её собственная тема, всё честно. Но схему `result` (ящик с молекулами, манометр и подпись
PV = nRT) сейчас зовут 27 шагов из двенадцати тем — и под шагом про замедление времени у читателя
стоит уравнение состояния идеального газа. Проверка молчит: имя схемы существует, JSON валиден.

Как считаем «родную» тему: та, где схема встречается чаще всего; при равенстве — та, что раньше
в дереве. Это грубо, но для отчёта достаточно: спорные случаи всё равно смотрит человек.

    python tools/figure_owner.py              сводка: какие схемы разошлись по темам
    python tools/figure_owner.py --steps      каждый шаг с чужой схемой (файл, номер, о чём шаг)
    python tools/figure_owner.py --topic atom только по одной теме
"""
import collections
import glob
import io
import json
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = "data/theory/courses"


def order():
    """Порядок тем в дереве — им разрешаем ничью при выборе родной темы."""
    try:
        idx = json.loads(io.open(ROOT + "/index.json", encoding="utf-8").read())
        return {t["id"]: t.get("n", 99) for t in idx["topics"]}
    except Exception:
        return {}


def collect():
    use = collections.defaultdict(list)
    for f in sorted(glob.glob(ROOT + "/*/[0-9]*.json")):
        p = f.replace("\\", "/")
        topic = p.split("/")[-2]
        try:
            d = json.loads(io.open(f, encoding="utf-8").read())
        except Exception:
            continue
        ru = d.get("ru") or {}
        for i, s in enumerate((ru.get("derivation") or {}).get("steps") or [], 1):
            if s.get("figure"):
                use[s["figure"]].append({
                    "topic": topic, "lesson": d.get("id"), "n": i,
                    "text": (s.get("text") or "")[:160],
                    "latex": (s.get("latex") or "")[:80],
                })
    return use


def main():
    n = order()
    use = collect()
    only = sys.argv[sys.argv.index("--topic") + 1] if "--topic" in sys.argv else None
    steps = "--steps" in sys.argv

    home, alien = {}, []
    for fig, rows in use.items():
        cnt = collections.Counter(r["topic"] for r in rows)
        best = max(cnt.items(), key=lambda kv: (kv[1], -n.get(kv[0], 99)))[0]
        home[fig] = best
        for r in rows:
            if r["topic"] != best:
                alien.append((fig, best, r))

    if steps:
        for fig, best, r in sorted(alien, key=lambda x: (x[2]["topic"], x[2]["lesson"], x[2]["n"])):
            if only and r["topic"] != only:
                continue
            print("%s/%s шаг %d" % (r["topic"], r["lesson"], r["n"]))
            print("   схема %-14s (родная тема: %s)" % (fig, best))
            print("   шаг о чём: %s" % r["text"])
            if r["latex"]:
                print("   формула:   %s" % r["latex"])
        print("\nвсего шагов с чужой схемой: %d" % len([1 for _, _, r in alien
                                                       if not only or r["topic"] == only]))
        return 0

    spread = {f: collections.Counter(r["topic"] for r in use[f]) for f in use}
    multi = {f: c for f, c in spread.items() if len(c) > 1}
    print("схем в ходу: %d | разошлись по темам: %d | шагов с чужой схемой: %d"
          % (len(use), len(multi), len(alien)))
    for f, c in sorted(multi.items(), key=lambda kv: -sum(kv[1].values())):
        чужих = sum(v for t, v in c.items() if t != home[f])
        print("  %-14s всего %2d | родная %-15s | чужих %2d | темы: %s"
              % (f, sum(c.values()), home[f], чужих,
                 ", ".join("%s×%d" % (t, v) for t, v in c.most_common())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
