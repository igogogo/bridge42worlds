#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Обвязка страниц в облако: связи, сводки сущностей и «бока» статьи.

ЗАЧЕМ ОДНИМ ИНСТРУМЕНТОМ, А НЕ ПЯТЬЮ. Владелец 25 августа: «предлагаю всю динамику
реализовать, потому что автор просто частный случай, а то потом будешь менять — так сразу
решишь задачу в целом». И он прав: страница тега, закона, учёного, раздела и автора — это
одна и та же задача «дай карточки, связанные вот с этим, страницами», а обвязка статьи —
«дай то, что относится вот к этой работе». Разные они только в источнике связи.

ЧТО ЭТО УБИРАЕТ С КЛИЕНТА. Сегодня читатель качает файлы, которые растут вместе с архивом:
articles-index в трёх уровнях (11 МБ по сети), search-index (229 КБ), authors-graph (1.3 МБ),
related-vec (160 КБ), tags-lite, laws-lite, scientists-lite, tag-laws, carousel. На 100 000
статей это десятки мегабайт на каждый заход. Страница из облака весит семь килобайт и не
растёт вовсе.

ВТОРАЯ ЦЕЛЬ, ради которой всё затевалось: уйти от пересборок. Пока теги и похожие вшиты в
страницы, правка разметки означает перегенерацию 167 981 страницы. Когда в HTML остаётся
только наш текст, изменение связей не трогает ни одного файла.

ТАБЛИЦЫ
  card_links   — связь «сущность → работа» для тегов, законов, учёных и разделов.
                 Авторы живут отдельно (card_authors): у них есть своя личность —
                 s2_author_id, person_id, — которой у тега быть не может.
  entity_stats — сводка сущности: сколько работ, каких, по годам, верхние разделы.
                 Считается здесь, а не запросом на лету: график по годам у автора с сотней
                 работ — это группировка, которую незачем повторять на каждый заход.
  article_side — обвязка одной работы: похожие, цитируемые нами, кадры карусели.

    python cloudflare/frame_sync.py --check
    python cloudflare/frame_sync.py --apply
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "cloudflare"))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

import cards_sync as cs

LANG = "ru"          # связи от языка не зависят: тег у работы один, названия переводятся

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS card_links (
         kind TEXT NOT NULL,        -- tag / law / sci / cat
         key  TEXT NOT NULL,        -- идентификатор сущности
         id   TEXT NOT NULL,        -- arXiv id работы
         date TEXT,
         PRIMARY KEY (kind, key, id)
       )""",
    "CREATE INDEX IF NOT EXISTS card_links_e ON card_links(kind, key, date DESC)",
    """CREATE TABLE IF NOT EXISTS entity_stats (
         kind    TEXT NOT NULL,
         key     TEXT NOT NULL,
         total   INTEGER, express INTEGER, km INTEGER,
         first   TEXT, last TEXT,
         by_year TEXT,              -- {"2024": 3, ...} — столбики графика
         cats    TEXT,              -- [["astro-ph.HE", 10], ...] верхние разделы
         PRIMARY KEY (kind, key)
       )""",
    """CREATE TABLE IF NOT EXISTS article_side (
         id       TEXT PRIMARY KEY,
         related  TEXT,             -- [id, ...] по смыслу, порядок значим
         cited    TEXT,             -- [id, ...] из цитируемого мы разбирали
         frames   INTEGER DEFAULT 0 -- кадров карусели
       )""",
]

KINDS = {"tag": "tags", "law": "laws", "sci": "scientists", "cat": "categories"}


def load_index():
    p = ROOT / "lang" / LANG / "articles-index.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def build_links(idx):
    """Связи и сводки. Считаются по индексу — тому же источнику, из которого собраны
    карточки: если брать из разных мест, страница тега и карточка в ленте однажды покажут
    разные наборы, и объяснить это будет нечем."""
    links = set()
    agg = defaultdict(lambda: {"total": 0, "express": 0, "km": 0,
                               "first": "", "last": "", "by_year": Counter(),
                               "cats": Counter()})
    # km в живом индексе пуст у всех записей (индекс обновляется по частям, поле моложе
    # последней полной пересборки) — берём из первоисточника, как это уже делает cards_sync.
    km = cs.km_map()
    seen = set()
    for a in idx:
        aid = a.get("id")
        if not aid or aid in seen:
            continue
        seen.add(aid)
        a_km = 1 if (a.get("km") or km.get(aid, 0)) else 0
        date = a.get("date", "")
        year = date[:4]
        for kind, field in KINDS.items():
            for key in (a.get(field) or []):
                key = str(key)[:80]
                if not key:
                    continue
                links.add((kind, key, aid, date))
                s = agg[(kind, key)]
                s["total"] += 1
                s["express"] += 1 if a.get("express") else 0
                s["km"] += a_km
                if year:
                    s["by_year"][year] += 1
                if not s["first"] or date < s["first"]:
                    s["first"] = date
                if date > s["last"]:
                    s["last"] = date
                pc = a.get("primary_category") or ""
                if pc:
                    s["cats"][pc] += 1
    return links, agg


def build_side(idx):
    """Обвязка статьи. Источники — те же файлы, что сегодня качает читатель; после переезда
    они останутся только на машине, как рабочие."""
    rel = {}
    p = ROOT / "data" / "related-vec.json"
    if p.exists():
        try:
            rel = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            rel = {}
    cited = {}
    p = ROOT / "data" / "cited-ours.json"
    if p.exists():
        try:
            cited = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            cited = {}
    frames = {}
    p = ROOT / "data" / "carousel.json"
    if p.exists():
        try:
            frames = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            frames = {}

    def _ids(v):
        """Список идентификаторов из чего угодно. В related-vec.json элементы — словари
        {'id':…, 'score':…}; первая версия резала их как строки и в базу легли обрывки
        "{'id': '1703.082…" — поймано первым же запросом к /api/side."""
        if isinstance(v, dict):
            v = v.get("ids") or []
        out2 = []
        for x in (v or []):
            if isinstance(x, dict):
                x = x.get("id") or ""
            x = str(x).strip()
            if x:
                out2.append(x[:24])
        return out2[:12]

    out = {}
    for a in idx:
        aid = a.get("id")
        if not aid or aid in out:
            continue
        r = _ids(rel.get(aid))
        c = _ids(cited.get(aid))
        n = frames.get(aid) or 0
        if r or c or n:
            out[aid] = (json.dumps(r, ensure_ascii=False),
                        json.dumps(c, ensure_ascii=False),
                        int(n))
    return out


def push(rows, sql_head, cols_n, batch=90):
    n = 0
    for i in range(0, len(rows), batch):
        part = rows[i:i + batch]
        vals = ",".join("(" + ",".join(cs.lit(v) for v in r) + ")" for r in part)
        cs.q(f"{sql_head} VALUES {vals}")
        n += len(part)
        if n % 3600 < batch:
            print(f"      … {n}/{len(rows)}")
    return n


def main():
    # Общий замок (tools/freeze.py): пока стоит, прогоны не начинаются.
    try:
        import sys as _s
        from pathlib import Path as _P
        _r = str(_P(__file__).resolve().parent.parent)
        if _r not in _s.path:
            _s.path.insert(0, _r)
        from tools.freeze import guard as _frozen
        _frozen("заливка обвязки")
    except ImportError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not (args.check or args.apply):
        print("укажи --check или --apply")
        return 1

    idx = load_index()
    print(f"записей в индексе: {len(idx)}")
    links, agg = build_links(idx)
    side = build_side(idx)
    print(f"связей сущность-работа: {len(links)}")
    print(f"сущностей со сводкой:   {len(agg)}")
    for k in KINDS:
        print(f"   {k:4} {len({e for e in agg if e[0] == k})}")
    print(f"статей с обвязкой:      {len(side)}")

    if not args.apply:
        print("\nничего не менялось — это --check")
        return 0

    for sql in SCHEMA:
        cs.q(sql)
    # Полная перезапись связей: их немного, а вычислять разницу по четырём видам сущностей
    # дороже, чем залить заново. Порядок — сначала стереть, потом залить: обратный оставил бы
    # висеть связи с удалённых тегов, и страница показывала бы работы, которых там нет.
    cs.q("DELETE FROM card_links")
    n = push(sorted(links), "INSERT OR REPLACE INTO card_links (kind, key, id, date)", 4)
    print(f"  связей залито: {n}")

    cs.q("DELETE FROM entity_stats")
    rows = []
    for (kind, key), s in agg.items():
        rows.append((kind, key, s["total"], s["express"], s["km"], s["first"], s["last"],
                     json.dumps(dict(sorted(s["by_year"].items())), ensure_ascii=False),
                     json.dumps(s["cats"].most_common(6), ensure_ascii=False)))
    n = push(rows, "INSERT OR REPLACE INTO entity_stats "
                   "(kind, key, total, express, km, first, last, by_year, cats)", 9, batch=40)
    print(f"  сводок залито: {n}")

    cs.q("DELETE FROM article_side")
    rows = [(aid, r, c, f) for aid, (r, c, f) in side.items()]
    n = push(rows, "INSERT OR REPLACE INTO article_side (id, related, cited, frames)", 4, batch=60)
    print(f"  обвязок залито: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
