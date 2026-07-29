"""Связывает уроки курса с контентом сайта: теги, законы, учёные и релевантные статьи.

Работает БЕЗ обращения к модели — простым сопоставлением текста урока с нашими справочниками
(214 тегов, 121+ закон, 177+ учёных) и подбором статей по совпавшим тегам. То, что в ТЗ просили
у специалиста, можно закрыть автоматически — данные для этого у нас уже есть.

Записывает в JSON урока:
    "tags": [...], "laws": [...], "scientists": [...],
    "examples_from_articles": [{"id": ..., "why": "совпадение по теме: ..."}]

Запуск:
    python course_link.py --check     # что нашлось, без записи
    python course_link.py             # записать привязки в уроки
"""
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

LANG = "ru"
LESSONS = Path("data/theory/courses")


def site_root():
    """Где лежат справочники сайта.

    Теги, законы, учёные и индекс статей живут в СОБРАННОМ сайте (`lang/**`), а он по правилам
    не хранится в git — в рабочем дереве роли его просто нет. Поэтому ищем: сначала здесь,
    затем по B42_SITE_ROOT, затем в соседних деревьях того же репозитория."""
    probe = f"lang/{LANG}/data/tags-list.json"
    if Path(probe).exists():
        return Path(".")
    env = os.environ.get("B42_SITE_ROOT")
    if env and (Path(env) / probe).exists():
        return Path(env)
    parent = Path("..")
    if parent.exists():
        for sib in sorted(parent.iterdir()):
            if sib.is_dir() and (sib / probe).exists():
                return sib
    raise SystemExit(
        "Не найдены справочники сайта (" + probe + ").\n"
        "Они появляются только после сборки. Укажите дерево, где она есть:\n"
        "    B42_SITE_ROOT=../bridge42worlds python course_link.py --check")


ROOT = Path(".")   # корень со справочниками; выставляется в main()


def norm(s):
    return re.sub(r"[^а-яёa-z0-9 ]+", " ", (s or "").lower())


def load_refs():
    tags = json.loads((ROOT / f"lang/{LANG}/data/tags-list.json").read_text(encoding="utf-8"))
    tag_names = {t["en"]: (t.get("ru") or t["en"]) for t in tags}
    laws_p = ROOT / f"lang/{LANG}/data/laws-list.json"
    laws = json.loads(laws_p.read_text(encoding="utf-8")) if laws_p.exists() else []
    law_names = {}
    for l in laws:
        if isinstance(l, dict):
            law_names[l.get("id") or l.get("en") or l.get("name", "")] = l.get("name") or l.get("ru") or ""
    sci_p = ROOT / f"lang/{LANG}/data/scientists.json"
    sci = json.loads(sci_p.read_text(encoding="utf-8")) if sci_p.exists() else {}
    return tag_names, law_names, sci


def lesson_text(d):
    ru = d.get(LANG) or {}
    parts = []

    def walk(v):
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    walk(ru)
    return norm(" ".join(parts))


# Слова, которые встречаются в любом тексте и дают ложные привязки («вода» в уроке про молекулы —
# это не тег «вода»). Требуем от них более строгих условий.
_TOO_COMMON = {"water", "light", "energy", "time", "space", "mass", "force", "field", "gas", "heat",
               "temperature", "pressure", "atom", "particle", "wave", "hydrogen", "helium", "carbon"}


def match(text, names, limit, min_hits=2):
    """Сопоставление текста урока со справочником. Точность важнее полноты: одно случайное
    совпадение общего слова не должно вешать на урок чужой тег."""
    found = []
    for key, name in names.items():
        n = norm(name)
        if len(n) < 5:
            continue
        # многословные названия ищем целиком, однословные — по основе (без 2 последних букв)
        needle = n if " " in n else (n[:-2] if len(n) > 6 else n)
        if not needle or needle not in text:
            continue
        hits = text.count(needle)
        # общее слово принимаем, только если оно встречается заметно часто (тема урока, а не фон)
        if key in _TOO_COMMON and hits < 3:
            continue
        if hits < min_hits and " " not in n:
            continue
        found.append((key, hits))
    found.sort(key=lambda x: -x[1])
    return [k for k, _ in found[:limit]]


def articles_for(tags, idx, limit=3):
    """Релевантные статьи: у которых больше всего пересечений с тегами урока, свежие вперёд."""
    scored = []
    for a in idx:
        common = set(a.get("tags") or []) & set(tags)
        if common:
            scored.append((len(common), a.get("date", ""), a["id"], sorted(common)))
    scored.sort(reverse=True)
    out, seen = [], set()
    for n, date, aid, common in scored:
        base = aid.split("v")[0]
        if base in seen:
            continue
        seen.add(base)
        out.append({"id": aid, "why": "совпадение по теме: " + ", ".join(common[:3])})
        if len(out) >= limit:
            break
    return out


def main():
    global ROOT
    ROOT = site_root()
    check = "--check" in sys.argv
    tag_names, law_names, sci = load_refs()
    idx = json.loads((ROOT / f"lang/{LANG}/articles-index.json").read_text(encoding="utf-8"))
    seen_ids, uniq = set(), []
    for a in idx:
        if a["id"] not in seen_ids:
            seen_ids.add(a["id"])
            uniq.append(a)

    lessons = sorted(f for f in LESSONS.rglob("*.json") if f.name[0].isdigit())
    stats = Counter()
    for f in lessons:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        text = lesson_text(d)
        if not text:
            continue
        tags = match(text, tag_names, 6)
        laws = match(text, law_names, 3)
        scientists = match(text, {k: k for k in sci}, 3)
        arts = articles_for(tags, uniq) if tags else []

        stats["tags"] += bool(tags)
        stats["laws"] += bool(laws)
        stats["scientists"] += bool(scientists)
        stats["articles"] += bool(arts)

        if check:
            print(f"{f.parent.name}/{f.name}: теги {tags[:4]} · законы {laws[:2]} · статей {len(arts)}")
            continue

        if tags:
            d["tags"] = tags
        if laws:
            d["laws"] = laws
        if scientists:
            d["scientists"] = scientists
        if arts:
            d["examples_from_articles"] = arts
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\nуроков: {len(lessons)} | с тегами: {stats['tags']} · с законами: {stats['laws']} "
          f"· с учёными: {stats['scientists']} · со статьями: {stats['articles']}")
    if not check:
        print("привязки записаны в JSON уроков")


if __name__ == "__main__":
    main()
