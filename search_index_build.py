#!/usr/bin/env python3
"""Лёгкий индекс поиска: lang/{lang}/search-index.json.

Зачем отдельный файл. Искать хочется сразу по всему — статьи, понятия, законы, учёные,
разделы, — но полные справочники весят слишком много: индекс статей 5,9 МБ, теги 4,4 МБ.
Тянуть это в браузер ради поиска нельзя, особенно с телефона. Поэтому здесь остаётся только
то, по чему ищем и что показываем строкой результата, и ничего больше.

Формат — плоский список записей, по одной на сущность:

    {"t":"tag", "id":"accretion_disk", "n":"аккреционный диск", "c":142}
    {"t":"law", "id":"kepler_laws",    "n":"Законы Кеплера",    "c":12}
    {"t":"sci", "id":"Johannes Kepler","n":"Иоганн Кеплер",     "s":"1571–1630", "c":3}
    {"t":"sec", "id":"astro-ph.CO",    "n":"Космология",        "c":88}
    {"t":"art", "id":"2607.00742",     "n":"Заголовок",         "d":"2026-07-01"}

Поля короткие намеренно: на двух с половиной тысячах записей длина ключей заметна в весе.
`id` служит и адресом (страницу собирает сама выдача), и латинским псевдонимом для поиска —
человек может набрать `entropy` на русской версии и должен найти «энтропию».

Счётчики статей считаются ТЕМИ ЖЕ правилами, что и на самих страницах, иначе поиск будет
обещать одно, а страница показывать другое:
  · тег     — статья несёт этот тег;
  · закон   — теги статьи пересекаются с тегами закона (generate.generate_law_page);
  · учёный  — учёный указан в `scientists` статьи (generate.generate_scientist_page);
  · раздел  — категория указана в `categories` статьи.
Везде учитываются только записи version == "popular": в индексе статья лежит по разу
на каждый уровень чтения, а искать её надо один раз.

Фактический вес на 2026-07-30 (2,8–2,9 тыс. записей на язык): ru 367 КБ, ar 332 КБ,
es 287 КБ, en 261 КБ — укладывается в оговорённые 400 КБ. Основной вклад дают статьи
(две тысячи заголовков); если однажды перестанет помещаться, резать надо их, а не
справочники: понятий, законов и учёных всего около 850 на язык.

Запуск:
    python search_index_build.py           # все языки из config.json
    python search_index_build.py ru        # один язык
"""

import json
import sys
from pathlib import Path

from common import LANGUAGES

LANG_DIR = "lang"
CATEGORIES_FILE = "data/arxiv-categories.json"


def _load(path, default):
    p = Path(path)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _name_of(entry):
    """В локалях раздел встречается и строкой, и объектом {name, description}."""
    return entry.get("name") if isinstance(entry, dict) else entry


def _categories(lang):
    """Названия разделов на языке страницы.

    Список кодов — объединение ВСЕХ справочников, а не только базового: в нём 64 записи,
    а в локализованных 156. Если брать за основу базовый, английский читатель не найдёт
    девяносто с лишним разделов, которые на сайте существуют. Имя берём из локали языка,
    затем из базового, в последнюю очередь показываем сам код.
    """
    base = _load(CATEGORIES_FILE, {})
    loc = _load(f"data/arxiv-categories-{lang}.json", {})
    codes = set(base) | set(loc)
    for other in Path("data").glob("arxiv-categories-*.json"):
        codes |= set(_load(other, {}))
    return {code: _name_of(loc.get(code)) or base.get(code) or code for code in sorted(codes)}


def build_lang(lang):
    articles = [a for a in _load(f"{LANG_DIR}/{lang}/articles-index.json", [])
                if a.get("version") == "popular"]
    tags = _load(f"{LANG_DIR}/{lang}/data/tags.json", {})
    laws = _load(f"{LANG_DIR}/{lang}/data/laws.json", {})
    scientists = _load(f"{LANG_DIR}/{lang}/data/scientists.json", {})
    categories = _categories(lang)

    tag_count, sci_count, sec_count = {}, {}, {}
    for a in articles:
        for t in a.get("tags") or []:
            tag_count[t] = tag_count.get(t, 0) + 1
        for s in a.get("scientists") or []:
            sci_count[s] = sci_count.get(s, 0) + 1
        for c in a.get("categories") or []:
            sec_count[c] = sec_count.get(c, 0) + 1

    rows = []
    for tid, data in tags.items():
        rows.append({"t": "tag", "id": tid, "n": data.get("name") or tid,
                     "c": tag_count.get(tid, 0)})
    for lid, data in laws.items():
        law_tags = set(data.get("tags") or [])
        count = sum(1 for a in articles if law_tags & set(a.get("tags") or []))
        rows.append({"t": "law", "id": lid, "n": data.get("name") or lid, "c": count})
    for sid, data in scientists.items():
        row = {"t": "sci", "id": sid, "n": data.get("name") or sid,
               "c": sci_count.get(sid, 0)}
        if data.get("lifespan"):
            row["s"] = data["lifespan"]
        rows.append(row)
    for code, name in categories.items():
        rows.append({"t": "sec", "id": code, "n": name, "c": sec_count.get(code, 0)})
    for a in articles:
        rows.append({"t": "art", "id": a["id"], "n": a.get("title") or a["id"],
                     "d": a.get("date", "")})

    out = Path(LANG_DIR) / lang / "search-index.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    # separators без пробелов: на 2,7 тыс. записей лишний пробел после каждой запятой — это
    # десятки килобайт на ровном месте.
    out.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return rows, out.stat().st_size


def main():
    targets = [sys.argv[1]] if len(sys.argv) > 1 else list(LANGUAGES)
    for lang in targets:
        if not (Path(LANG_DIR) / lang).exists():
            print(f"⏭️ {lang}: нет папки языка — пропускаю")
            continue
        rows, size = build_lang(lang)
        kinds = {}
        for r in rows:
            kinds[r["t"]] = kinds.get(r["t"], 0) + 1
        parts = " · ".join(f"{k} {v}" for k, v in sorted(kinds.items()))
        print(f"🔎 {lang}: {len(rows)} записей ({parts}) — {size / 1024:.0f} КБ")


if __name__ == "__main__":
    main()
