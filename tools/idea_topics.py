#!/usr/bin/env python3
"""Откуда берутся темы фабрики идей — четыре источника, и каждый назван.

Владелец 31.08 спросил про страницу идей: «там разделы у нас от кластеризации
понятий или откуда». Ответ был — ниоткуда: список тем писался рукой. Это годится
для первых сорока тем и не годится дальше: фабрика должна питаться тем, что у нас
уже есть, а не тем, что кто-то вспомнил.

Четыре пласта, от прикладного к глубокому:

  applied  — рука. Вода, солнце, коррозия: то, за чем к нам придёт инженерный
             факультет. Кластеризация такого не родит — у нас про это почти нет
             статей, — а спрос настоящий. Остаётся списком.
  core     — рука. Наше ядро: где опоры будут из архива, со ссылками на сайт.
  area     — 50 областей, которые машина знаний собрала САМА: понятия сбились в
             группы вектором, DeepSeek дал группам имена. Это карта того, что мы
             действительно знаем, и она пересобирается каждую неделю.
  demand   — спрос машины знаний: понятия, у которых страница есть, а статей под
             ней мало. Идея по такому понятию — заодно и заказ на разбор.

    python tools/idea_topics.py            собрать список и опись
    python tools/idea_topics.py --show     показать, ничего не записывая
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

HAND = ROOT / "data" / "idea-topics.txt"
GROUPS = ROOT / "data" / "group-names.json"
OUT_TXT = ROOT / "data" / "idea-topics-all.txt"
OUT_JSON = ROOT / "data" / "idea-topics.json"

# Сколько понятий из спроса брать темами. Спрос — тысячи; писать идеи по всем и
# долго, и незачем: берём самые «дозревшие», у которых уже есть 2-4 статьи.
DEMAND_TOP = 20
DEMAND_MIN_ARTS = 2

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def hand():
    """Рукописный список. Заголовки-разделители внутри файла делят его на пласты:
    первый — прикладное, дальше — наше ядро."""
    out, kind = [], "applied"
    if not HAND.exists():
        return out
    for line in HAND.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#"):
            if "ядро" in line:
                kind = "core"
            elif "прикладн" in line:
                kind = "applied"
            continue
        if line:
            out.append({"topic": line, "origin": kind})
    return out


def areas():
    """Области машины знаний — те самые 50 групп."""
    if not GROUPS.exists():
        return []
    g = json.loads(GROUPS.read_text(encoding="utf-8"))
    out = []
    for gid, v in g.items():
        name = (v or {}).get("name_ru") or (v or {}).get("name_en")
        if name:
            out.append({"topic": name.strip().lower(), "origin": "area",
                        "note": (v or {}).get("note_ru", ""), "gid": gid})
    return out


def hungry():
    """Понятия, которым не хватает статей: идея по ним — ещё и заказ на разбор."""
    try:
        import strata
        want = strata.demand()
    except Exception as e:
        print(f"  ⚠ спрос недоступен ({e}) — пласт пропущен")
        return []
    # Однословные и нерусские имена темой не годятся: «частота», «проекция»,
    # «anode» — это ярлык, а не дело, за которое можно взяться. Просим два русских
    # слова и больше: «квантовые материалы», «оценка плотности ядра».
    def usable(v):
        nm = str(v.get("name") or "")
        words = [w for w in nm.split() if len(w) > 2]
        return (len(words) >= 2 and (v.get("arts") or 0) >= DEMAND_MIN_ARTS
                and sum(c.isalpha() and c.lower() in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
                        for c in nm) > len(nm) / 2)

    rows = [v for v in want.values() if usable(v)]
    rows.sort(key=lambda v: -(v.get("arts") or 0))
    return [{"topic": str(r["name"]).strip().lower(), "origin": "demand",
             "note": f"понятие с опорой из {r['arts']} статей"}
            for r in rows[:DEMAND_TOP]]


def main():
    rows, seen = [], set()
    for part in (hand(), areas(), hungry()):
        for r in part:
            k = r["topic"].strip().lower()
            # Тема, пришедшая двумя путями, остаётся за первым: рука точнее
            # автоматики в формулировке, а область — точнее спроса в широте.
            if k in seen:
                continue
            seen.add(k)
            rows.append(r)
    tally = {}
    for r in rows:
        tally[r["origin"]] = tally.get(r["origin"], 0) + 1
    if "--show" in sys.argv:
        for r in rows:
            print(f"  {r['origin']:8} {r['topic']}")
    else:
        OUT_TXT.write_text(
            "# Собран tools/idea_topics.py — правится не здесь, а в data/idea-topics.txt\n"
            + "\n".join(r["topic"] for r in rows) + "\n", encoding="utf-8")
        OUT_JSON.write_text(json.dumps({"topics": rows}, ensure_ascii=False, indent=1),
                            encoding="utf-8")
    print(f"✅ тем: {len(rows)} · " + " · ".join(f"{k} {v}" for k, v in tally.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
