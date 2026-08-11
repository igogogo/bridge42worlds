#!/usr/bin/env python3
"""Поле: поиск по ВСЕМУ arXiv, а не только по тому, что мы успели разобрать.

Владелец 11 августа: «ищем вектором, находим, пишем наши рекомендации, по пути находим
опоры, из них пакетом делаем экспресс — и не только по существующим, а по всему полю.
Сразу вытаскиваем куст на основе рекомендаций; они тоже применимы к вектору, круг
замыкается».

Почему не «просто вектор по 3 млн». Посчитано 11 августа: построить эмбеддинги всех
3.13 млн аннотаций стоит $8.83 разово — копейки. Упирается в хранение: 3.2 млрд измерений
в Cloudflare Vectorize это $128 в месяц, при всём бюджете проекта $200. Держать их у себя
можно только после переезда на VPS.

Поэтому здесь двухступенчатый поиск, который работает уже сегодня и денег почти не стоит:

    слова (SQLite FTS5 по 3.13 млн аннотаций, локально, бесплатно)
      → 300 кандидатов
      → смысл (bge-m3 только для этих трёхсот, $0.0009 на статью)
      → 5 ближайших

Первая ступень грубая — она ловит по словам и пропускает работы, где то же самое названо
иначе. Вторая это чинит: среди трёхсот кандидатов вектор выбирает по смыслу. Полный
векторный проход по 3 млн был бы точнее на первом шаге, но стоит $128 в месяц, а разница
на нашей задаче — «нашли 5 из 300» против «нашли 5 из 3 млн» — не окупает.

    python tools/field.py build              разово: индекс по data/arxiv-bulk (~20 мин)
    python tools/field.py bush 2310.15936    куст вокруг статьи: что есть рядом во всём arXiv
    python tools/field.py bush ID --new 5    только те, которых у нас ещё нет
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv                                       # noqa: E402

load_dotenv(ROOT / ".env")

BULK = ROOT / "data" / "arxiv-bulk"
DB = ROOT / "data" / "arxiv-field.sqlite"
EMBED_MODEL = "bge-m3"
VECTOR_INDEX = "b42-articles"
CANDIDATES = 300          # сколько тянем словами, прежде чем смотреть смыслом
EMBED_BATCH = 50

# Слова, которые есть в каждой второй аннотации и потому ничего не отбирают.
_STOP = set("""a an the and or of in on for to with we our this that these those is are was
were be been being by from as at it its their his her they them he she which what when where
how why can could may might will would shall should must have has had do does did not no nor
but if then than so such using use used show shows shown study studies present presents
propose proposed method methods result results paper work approach based new novel also
between within while during about into over under more most less least first second third
one two three four five six seven eight nine ten""".split())


def _months():
    return sorted(BULK.glob("*.jsonl"))


def build():
    """Строит FTS5-индекс. Разово: дамп меняется раз в месяц, не чаще."""
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=OFF")
    con.execute("PRAGMA synchronous=OFF")
    # Contentless FTS5: сам текст не храним — он уже лежит в дампе, и дублировать 2.9 ГБ
    # незачем. Держим только соответствие «строка индекса → id + файл месяца», чтобы
    # вернуться за аннотацией, когда она понадобится.
    con.execute("CREATE TABLE doc (rowid INTEGER PRIMARY KEY, aid TEXT, mon TEXT)")
    con.execute("CREATE VIRTUAL TABLE fts USING fts5(txt, content='')")
    n = 0
    t0 = time.time()
    for f in _months():
        rows, docs = [], []
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                aid = r.get("id")
                if not aid:
                    continue
                n += 1
                docs.append((n, aid, f.stem))
                rows.append((n, f"{r.get('title', '')} {r.get('abstract', '')}"))
        con.executemany("INSERT INTO doc(rowid, aid, mon) VALUES (?,?,?)", docs)
        con.executemany("INSERT INTO fts(rowid, txt) VALUES (?,?)", rows)
        con.commit()
        print(f"  {f.stem}: {len(rows)} — всего {n}", flush=True)
    con.execute("CREATE INDEX idx_aid ON doc(aid)")
    con.commit()
    con.close()
    size = DB.stat().st_size / 1e9
    print(f"✅ поле построено: {n} работ, {size:.1f} ГБ, {time.time() - t0:.0f} с")
    return 0


def _terms(text, limit=24):
    """Слова для запроса: редкие важнее частых, поэтому общие выбрасываем.

    Порядок сохраняем — заголовок идёт первым и его слова точнее описывают работу, чем
    середина аннотации.
    """
    seen, out = set(), []
    for w in re.findall(r"[a-zA-Z][a-zA-Z\-]{3,}", text.lower()):
        w = w.strip("-")
        if len(w) < 4 or w in _STOP or w in seen:
            continue
        seen.add(w)
        out.append(w)
        if len(out) >= limit:
            break
    return out


def search_words(text, limit=CANDIDATES, exclude=()):
    """Первая ступень: кандидаты по словам, ранжирование bm25 самой SQLite."""
    if not DB.exists():
        print(f"нет {DB.name} — сначала: python tools/field.py build")
        return []
    terms = _terms(text)
    if not terms:
        return []
    # Каждое слово в кавычках: без них FTS5 читает «one-dimensional» как выражение
    # с оператором и падает на «no such column: dimensional».
    q = " OR ".join(f'"{t}"' for t in terms)
    con = sqlite3.connect(DB)
    try:
        rows = con.execute(
            "SELECT d.aid, d.mon FROM fts JOIN doc d ON d.rowid = fts.rowid "
            "WHERE fts MATCH ? ORDER BY bm25(fts) LIMIT ?", (q, limit * 2)).fetchall()
    except sqlite3.OperationalError as ex:
        print(f"  ⚠️ запрос к полю не прошёл: {ex}")
        return []
    finally:
        con.close()
    ex = set(exclude)
    return [(a, m) for a, m in rows if a not in ex][:limit]


def _abstracts(pairs):
    """Аннотации кандидатов — из дампа, по одному проходу на файл месяца."""
    by_mon = {}
    for aid, mon in pairs:
        by_mon.setdefault(mon, set()).add(aid)
    got = {}
    for mon, ids in by_mon.items():
        f = BULK / f"{mon}.jsonl"
        if not f.exists():
            continue
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("id") in ids:
                    got[r["id"]] = (r.get("title", ""), " ".join((r.get("abstract") or "").split()),
                                    r.get("categories") or [], r.get("published", ""))
                    if len(got) >= sum(len(v) for v in by_mon.values()):
                        break
    return got


def _cf():
    acc = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    tok = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not (acc and tok):
        raise RuntimeError("нет CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN")
    return acc, {"Authorization": f"Bearer {tok}"}


def embed(texts):
    """Эмбеддинги пачками. 429 и пятисотые — не сбой, а занятая общая модель: ждём."""
    import requests
    acc, h = _cf()
    out = []
    for i in range(0, len(texts), EMBED_BATCH):
        chunk = [t[:2000] for t in texts[i:i + EMBED_BATCH]]
        for attempt in range(6):
            r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{acc}"
                              f"/ai/run/@cf/baai/{EMBED_MODEL}",
                              headers=h, json={"text": chunk}, timeout=120)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(min(2 ** attempt, 30))
                continue
            j = r.json()
            if not j.get("success"):
                raise RuntimeError(f"Workers AI: {j.get('errors')}")
            out.extend(j["result"]["data"])
            break
        else:
            raise RuntimeError("Workers AI недоступна после шести попыток")
    return out


def _cos(a, b):
    s = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return s / (na * nb) if na and nb else 0.0


def _ours():
    """Идентификаторы того, что уже разобрано, — вместе с версией и без неё."""
    ours = set()
    for p in ROOT.glob("lang/ru/archive/*/*/data.json"):
        aid = p.parent.name
        ours.add(aid)
        ours.add(re.sub(r"v\d+$", "", aid))
    return ours


def bush(aid, want=5, only_new=False, quiet=False):
    """Куст вокруг работы: что лежит рядом во всём arXiv, а не только у нас."""
    hits = list(ROOT.glob(f"lang/ru/archive/*/{aid}/data.json"))
    if not hits:
        print(f"нет статьи {aid}")
        return []
    d = json.loads(hits[0].read_text(encoding="utf-8"))
    seed = f"{d.get('original_title', '')} {d.get('abstract_orig', '')}".strip()
    if not seed:
        print(f"{aid}: нет оригинального названия и аннотации "
              f"(сначала: python tools/abstract_orig.py {aid})")
        return []

    ours = _ours()
    cands = search_words(seed, exclude={aid, re.sub(r'v\d+$', '', aid)})
    if not cands:
        print(f"{aid}: поле не дало кандидатов")
        return []
    meta = _abstracts(cands)
    ids = [a for a, _ in cands if a in meta]
    if not quiet:
        print(f"  словами найдено {len(cands)}, аннотации есть у {len(ids)}")

    vecs = embed([seed] + [f"{meta[i][0]} {meta[i][1]}" for i in ids])
    base, rest = vecs[0], vecs[1:]
    scored = sorted(((_cos(base, v), i) for i, v in zip(ids, rest)), reverse=True)

    out = []
    for score, i in scored:
        have = i in ours or re.sub(r"v\d+$", "", i) in ours
        if only_new and have:
            continue
        title, abstract, cats, pub = meta[i]
        out.append({"id": i, "score": round(score, 3), "title": title,
                    "categories": cats, "published": pub, "have": have})
        if len(out) >= want:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "bush"])
    ap.add_argument("aid", nargs="?")
    ap.add_argument("--new", type=int, default=0, help="сколько НОВЫХ работ вернуть")
    ap.add_argument("--want", type=int, default=8)
    args = ap.parse_args()

    if args.cmd == "build":
        return build()

    if not args.aid:
        print("нужен id статьи")
        return 2
    rows = bush(args.aid, want=args.new or args.want, only_new=bool(args.new))
    for r in rows:
        mark = "  " if r["have"] else "НОВОЕ"
        print(f"{r['score']:.3f} {mark} {r['id']} · {', '.join(r['categories'][:2])} · "
              f"{r['title'][:80]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
