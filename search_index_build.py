#!/usr/bin/env python3
"""Лёгкий индекс поиска: lang/{lang}/search-index.json.

Зачем отдельный файл. Искать хочется сразу по всему — статьи, понятия, законы, учёные,
разделы, — но полные справочники весят слишком много: индекс статей 5,9 МБ, теги 4,4 МБ.
Тянуть это в браузер ради поиска нельзя, особенно с телефона. Поэтому здесь остаётся только
то, по чему ищем и что показываем строкой результата, и ничего больше.

Формат — плоский список записей, по одной на сущность:

    {"t":"tag", "id":"accretion_disk", "n":"аккреционный диск", "c":142}
    {"t":"law", "id":"kepler_laws",    "n":"Законы Кеплера",    "c":12}
    {"t":"sci", "id":"Johannes Kepler","n":"Johannes Kepler",   "s":"1571–1630", "c":3,
                "a":["Кеплер","Иоганн Кеплер"]}
    {"t":"sec", "id":"astro-ph.CO",    "n":"Космология",        "c":88}
    {"t":"art", "id":"2607.00742",     "n":"Заголовок",         "d":"2026-07-01"}

Поля короткие намеренно: на двух с половиной тысячах записей длина ключей заметна в весе.
`id` служит и адресом (страницу собирает сама выдача), и латинским псевдонимом для поиска —
человек может набрать `entropy` на русской версии и должен найти «энтропию».

`a` и `nl` — только у учёных. В справочнике имя учёного всегда латиницей, поэтому арабский
читатель и не находил существующего Эйнштейна, и видел его в выдаче как «Albert Einstein»
(обе половины нашёл QA). `a` — формы имени, по которым ищем, включая склонения; `nl` —
та единственная форма, которую показываем вместо латиницы. Откуда берутся — scientist_aliases().

Счётчики статей считаются ТЕМИ ЖЕ правилами, что и на самих страницах, иначе поиск будет
обещать одно, а страница показывать другое:
  · тег     — статья несёт этот тег;
  · закон   — теги статьи пересекаются с тегами закона (generate.generate_law_page);
  · учёный  — учёный указан в `scientists` статьи (generate.generate_scientist_page);
  · раздел  — категория указана в `categories` статьи.
Везде учитываются только записи version == "popular": в индексе статья лежит по разу
на каждый уровень чтения, а искать её надо один раз.

Фактический вес на 2026-07-30 (2,8–2,9 тыс. записей на язык): ru 384 КБ, ar 343 КБ,
es 289 КБ, en 265 КБ — укладывается в оговорённые 400 КБ, но у русского запас невелик:
имена-синонимы учёных добавили около 17 КБ. Основной вклад дают статьи
(две тысячи заголовков); если однажды перестанет помещаться, резать надо их, а не
справочники: понятий, законов и учёных всего около 850 на язык.

Запуск:
    python search_index_build.py           # все языки из config.json
    python search_index_build.py ru        # один язык
"""

import json
import re
import sys
from pathlib import Path

from common import LANGUAGES

# Подпись у маркера учёного в тексте статьи: [scientist:Albert Einstein]Эйнштейна[/scientist].
SCI_MARKER = re.compile(r"\[scientist:([^\]]+)\]([^\[]{1,60})\[/scientist\]")

# Письменность языка. Подпись берём только в «своей» письменности: в арабских текстах у нас
# местами остались русские подписи маркеров (известный слой утечки перевода), и без этого
# фильтра в арабский индекс приезжает «Альбертом Эйнштейном» — вес есть, пользы нет.
SCRIPTS = {
    "ru": re.compile(r"[А-Яа-яЁё]"),
    "ar": re.compile(r"[؀-ۿ]"),
    "en": re.compile(r"[A-Za-z]"),
    "es": re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]"),
}
MAX_ALIASES = 8          # больше в строку результата всё равно не поместится
MAX_ALIAS_WORDS = 2      # «Альберт Эйнштейн» — да, «общая теория относительности» — нет

# Синонимы имён собираем только там, где письменность читателя отличается от латиницы.
# На английском и испанском имя из справочника уже верное («Henri Poincaré»), а фильтр
# письменности там ничего не отсекает — и в синонимы лезли случайные латинские
# словосочетания из тех же предложений («persistent homology» вместо Пуанкаре).
NON_LATIN_LANGS = {"ru", "ar", "zh", "cn", "ja", "ko", "hi", "el", "he", "uk", "sr", "bg"}

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


def scientist_aliases(lang, known_names):
    """Имена учёных на языке страницы — из подписей к маркерам в текстах статей.

    Зачем. В справочнике `scientists.json` поле `name` не переведено ни на один язык (там
    всегда латиница), поэтому арабский читатель набирает «أينشتاين» и не находит ничего —
    учёного, который на сайте есть. Переводить справочник — отдельная задача и деньги;
    но локализованные имена у нас УЖЕ написаны: авторы текстов размечают упоминания
    маркером, и подпись внутри маркера — это имя на языке статьи.

    Подписи грязные, и это осознанный размен. Внутри маркера встречаются склонения
    («Гауссом»), инициалы («В. Рубин») и словосочетания вокруг имени («формула Эйнштейна»,
    «LIGO»). Склонения для поиска по подстроке полезны, словосочетания — шум, поэтому
    отсекаем: чужую письменность, длину больше двух слов, совпадение с названием тега или
    закона (по ним ищут сущность, а не человека). Из оставшегося берём восемь самых частых:
    настоящее имя встречается в корпусе десятки раз, случайная обёртка — единицы.

    Полное решение — перевести `name` в справочнике; тогда этот сбор станет необязательным.
    """
    if lang not in NON_LATIN_LANGS:
        return {}
    script = SCRIPTS.get(lang)
    freq = {}
    root = Path(LANG_DIR) / "ru" / "archive"     # data.json лежит только у языка-источника
    if not root.exists():
        return {}
    for f in root.glob("*/*/data.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for tier in ("popular", "simple", "advanced"):
            branch = data.get(tier)
            if not isinstance(branch, dict):
                continue
            text = branch.get(lang)
            if not text:
                continue
            for sid, label in SCI_MARKER.findall(json.dumps(text, ensure_ascii=False)):
                label = " ".join(label.split())
                if not label or label == sid or len(label) > 40:
                    continue
                if len(label.split()) > MAX_ALIAS_WORDS:
                    continue
                if script and not script.search(label):
                    continue
                if label.lower() in known_names:
                    continue
                by_sci = freq.setdefault(sid, {})
                by_sci[label] = by_sci.get(label, 0) + 1
    return {sid: [lbl for lbl, _ in sorted(labels.items(), key=lambda kv: (-kv[1], kv[0]))[:MAX_ALIASES]]
            for sid, labels in freq.items()}


# Окончания косвенных падежей русского имени: «Альбертом», «Марией», «Исаака». В подписях
# они встречаются чаще именительного (в тексте о человеке пишут «работа Эйнштейна»), поэтому
# по одной частоте показывать нельзя — вышло бы «Марией Кюри» в заголовке карточки.
RU_OBLIQUE = ("ом", "ем", "ой", "ей", "ым", "им", "ую", "ого", "ому", "ых", "ами")


def display_name(sid, aliases):
    """Какую из форм имени ПОКАЗЫВАТЬ в выдаче.

    Искать по склонениям полезно, а показывать «Эйнштейна» нельзя — нужна та форма, что
    выглядит именем. Берём подпись с тем же числом слов, что у самого учёного: у «Albert
    Einstein» это «Альберт Эйнштейн», а не «Эйнштейном» и не короткое «Эйнштейн». Среди
    равных отбрасываем явно косвенные падежи по окончанию первого слова — грубо, но на
    именах работает, а полноценной морфологии ради одной строки в выдаче не нужно.
    Ничего не подошло — показываем латиницу из справочника, она хотя бы верна.
    """
    if not aliases:
        return None
    want = len(sid.split())
    same = [a for a in aliases if len(a.split()) == want]
    direct = [a for a in same if not a.split()[0].lower().endswith(RU_OBLIQUE)]
    return (direct or same or aliases)[0]


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
    # Названия понятий и законов на этом языке — фильтр для подписей маркеров: подпись,
    # совпадающая с тегом или законом, размечает сущность, а не человека.
    entity_names = {(d.get("name") or "").strip().lower()
                    for d in list(tags.values()) + list(laws.values())}
    entity_names.discard("")
    aliases = scientist_aliases(lang, entity_names)
    for sid, data in scientists.items():
        row = {"t": "sci", "id": sid, "n": data.get("name") or sid,
               "c": sci_count.get(sid, 0)}
        if data.get("lifespan"):
            row["s"] = data["lifespan"]
        alt = aliases.get(sid) or []
        if alt:
            row["a"] = alt          # по этим строкам ищем
            shown = display_name(sid, alt)
            if shown:
                row["nl"] = shown   # а это показываем вместо латиницы, если нашлась форма имени
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
