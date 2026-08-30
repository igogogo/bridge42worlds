# -*- coding: utf-8 -*-
"""Реестр знаний в облако: понятия, формулы и кадры графа → D1 (b42-cards).

Владелец 27.08: «делай воркер — понятия, формулы, граф — всё на dev». До этого
воркер знал только старую модель (теги/законы/учёные): страницы понятий волны 5
жили статикой, а живых списков, поиска по понятиям и кадров графа в облаке не
было вовсе.

ЧТО КЛАДЁМ (новые таблицы, старые не трогаются ни на строку — прод продолжает
работать на своих):

  concepts        карточка понятия: класс, имена ru/en, определение, счётчики,
                  группы, полная запись (JSON), системы единиц
  concept_links   взвешенные связи понятие↔понятие (соседи) и понятие↔формула
  concept_arts    какие статьи держат понятие (для живого списка на странице)
  formulas        основная форма: латех, карточка, анатомия (JSON), системы
  graph_frames    ГОТОВЫЕ кадры графа: обзор и по группе — считать их на лету
                  в воркере нельзя (28 тысяч рёбер), а отдавать 1.4 МБ файла
                  каждому читателю — то же расточительство, от которого мы
                  уходили в ленте

Кадры считает та же логика, что рисует граф локально (tools/concepts_graph_export),
поэтому вид в облаке и на диске совпадает по построению, а не по случайности.

    python cloudflare/concepts_sync.py --schema      создать таблицы
    python cloudflare/concepts_sync.py               залить всё
    python cloudflare/concepts_sync.py --frames      только кадры графа
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from common import ALL_LANGS

DB = "b42-cards"
BATCH = 40
# Потолок длины одного SQL-запроса к D1. Замер 28.08: сорок строк с полными
# карточками и переводами дают около двухсот килобайт — это уже 400 в ответ.
# Шестьдесят тысяч символов проходят с запасом.
SQL_BUDGET = 60000


def env(k):
    v = os.environ.get(k)
    if v:
        return v
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith(k + "="):
                return line.split("=", 1)[1].strip()
    return None


def d1(sql, tries=4):
    """Запрос к D1 через REST. Тот же путь, каким ходит cards_sync."""
    acc = env("CLOUDFLARE_ACCOUNT_ID") or env("R2_ACCOUNT_ID")
    tok = env("CLOUDFLARE_API_TOKEN")
    dbid = env("D1_CARDS_ID") or "f865c642-7478-4a52-930b-9b47f2b4a7fb"
    url = (f"https://api.cloudflare.com/client/v4/accounts/{acc}"
           f"/d1/database/{dbid}/query")
    last = None
    for i in range(tries):
        req = urllib.request.Request(
            url, data=json.dumps({"sql": sql}).encode("utf-8"),
            headers={"Authorization": f"Bearer {tok}",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read().decode("utf-8"))
            if d.get("success"):
                return d["result"]
            last = json.dumps(d.get("errors"), ensure_ascii=False)[:300]
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"D1: {last}")


def lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (dict, list)):
        v = json.dumps(v, ensure_ascii=False)
    return "'" + str(v).replace("'", "''").replace("\x00", "") + "'"


SCHEMA = [
    """CREATE TABLE IF NOT EXISTS concepts (
         id       TEXT PRIMARY KEY,   -- black_hole
         kind     TEXT,               -- phenomenon | law | math | statistics | unit …
         name_ru  TEXT, name_en TEXT,
         card     TEXT,               -- определение одним предложением (эпиграф)
         n_arts   INTEGER DEFAULT 0,  -- опора: сколько статей
         n_links  INTEGER DEFAULT 0,  -- сколько связей
         groups   TEXT,               -- [12, 30] — индексы групп
         cat      TEXT,               -- главный раздел arXiv его статей
         full_en  TEXT,               -- полная запись (JSON: описание/история/…)
         full_ru  TEXT,               -- её перевод
         systems  TEXT,               -- системы единиц (для unit/quantity)
         value    TEXT,               -- число константы: «1.602176634e-19»
         unit     TEXT,               -- её единица: «coulomb»
         symbol   TEXT,               -- её символ: «e»
         section  TEXT,               -- раздел по смыслу: statistics | constant | …
         part     TEXT,               -- часть раздела: «Проверка гипотез»
         names    TEXT                -- {"ru":…, "en":…, "es":…} — ВСЕ языки одним полем
       )""",
    # ПОЛНАЯ ЗАПИСЬ — СТРОКОЙ НА ЯЗЫК, А НЕ СТОЛБЦОМ НА ЯЗЫК. Столбцы full_en и
    # full_ru появились, когда языков было два, и с тех пор испанец, араб и француз
    # открывали понятие по-английски: переводы существуют (3 040–3 058 карточек на
    # каждом), но доехать им было некуда. Шестой язык добавил бы шестой столбец и
    # шестую ветку в воркере; здесь язык — значение, а не имя поля, и добавление
    # языка перестаёт быть правкой схемы.
    """CREATE TABLE IF NOT EXISTS concept_full (
         id   TEXT NOT NULL,
         lang TEXT NOT NULL,
         body TEXT,
         PRIMARY KEY (id, lang)
       )""",
    "CREATE INDEX IF NOT EXISTS concepts_kind ON concepts(kind, n_arts DESC)",
    "CREATE INDEX IF NOT EXISTS concepts_arts ON concepts(n_arts DESC)",
    """CREATE TABLE IF NOT EXISTS concept_links (
         a TEXT NOT NULL, b TEXT NOT NULL,
         w REAL,                      -- вес связи
         kind TEXT,                   -- 'c' понятие↔понятие, 'f' понятие↔формула
         PRIMARY KEY (a, b, kind)
       )""",
    "CREATE INDEX IF NOT EXISTS concept_links_a ON concept_links(a, w DESC)",
    """CREATE TABLE IF NOT EXISTS concept_arts (
         cid TEXT NOT NULL, id TEXT NOT NULL, date TEXT,
         PRIMARY KEY (cid, id)
       )""",
    "CREATE INDEX IF NOT EXISTS concept_arts_cid ON concept_arts(cid, date DESC)",
    """CREATE TABLE IF NOT EXISTS formulas (
         id      TEXT PRIMARY KEY,
         name    TEXT, latex TEXT, card TEXT,
         n_apps  INTEGER DEFAULT 0,
         anatomy TEXT,                -- переменные/константы/операторы/применимость
         systems TEXT                 -- та же форма в СИ/СГС/планковской
       )""",
    "CREATE INDEX IF NOT EXISTS formulas_apps ON formulas(n_apps DESC)",
    """CREATE TABLE IF NOT EXISTS graph_frames (
         key  TEXT PRIMARY KEY,       -- 'overview' | 'g:12' | 'ego:black_hole'
         data TEXT,                   -- готовый JSON кадра
         n    INTEGER                 -- узлов в кадре
       )""",
    # ── ГРАФ БЕЗ ГОТОВЫХ КАДРОВ ───────────────────────────────────────────────
    # Кадр группы и обзор лежали в graph_frames готовыми JSON-ами, и их
    # приходилось пересчитывать после каждой правки реестра — отдельным шагом
    # ночной цепочки, о который легко споткнуться (владелец 28.08: «а разве это
    # не динамика, зачем их обновлять?»). Здесь три маленькие таблицы, из
    # которых воркер собирает любой кадр запросом, как уже собирает эго-кадр.
    """CREATE TABLE IF NOT EXISTS concept_groups (
         gid INTEGER NOT NULL, cid TEXT NOT NULL,
         PRIMARY KEY (gid, cid)
       )""",
    "CREATE INDEX IF NOT EXISTS concept_groups_g ON concept_groups(gid)",
    "CREATE INDEX IF NOT EXISTS concept_groups_c ON concept_groups(cid)",
    """CREATE TABLE IF NOT EXISTS graph_groups (
         gid      INTEGER PRIMARY KEY,
         label_ru TEXT, label_en TEXT,
         note_ru  TEXT, note_en  TEXT,   -- «о чём эта область»
         n_con    INTEGER DEFAULT 0,     -- сколько понятий
         n_arts   INTEGER DEFAULT 0      -- сумма статей — размер круга на обзоре
       )""",
    """CREATE TABLE IF NOT EXISTS graph_group_links (
         a INTEGER NOT NULL, b INTEGER NOT NULL,
         w INTEGER,                      -- сколько связей между областями
         PRIMARY KEY (a, b)
       )""",
]

# Колонки, добавленные к уже существующей таблице. CREATE TABLE IF NOT EXISTS их
# не добавит: таблица есть, и запрос просто ничего не делает — новые поля молча
# не доезжают в облако. ALTER на существующую колонку отвечает «duplicate column»,
# и это ожидаемый ответ при повторном прогоне, а не сбой.
MIGRATIONS = [
    "ALTER TABLE concepts ADD COLUMN value TEXT",
    "ALTER TABLE concepts ADD COLUMN unit TEXT",
    "ALTER TABLE concepts ADD COLUMN symbol TEXT",
    "ALTER TABLE concepts ADD COLUMN section TEXT",
    "ALTER TABLE concepts ADD COLUMN part TEXT",
    "ALTER TABLE concepts ADD COLUMN names TEXT",
    "CREATE INDEX IF NOT EXISTS concepts_section ON concepts(section, n_arts DESC)",
]


def ensure_schema():
    for sql in SCHEMA + MIGRATIONS:
        try:
            d1(sql)
        except RuntimeError as e:
            # ALTER на уже существующую колонку D1 отдаёт голый 400 без текста —
            # распознать по сообщению нельзя, поэтому про миграции молчим: они
            # и задуманы как «добавить, если ещё нет».
            if sql.startswith("ALTER TABLE"):
                continue
            if "duplicate column" not in str(e).lower():
                print(f"  ⚠️ {sql[:52]}… → {e}")
    print("схема: таблицы на месте")


def load():
    live = json.loads((ROOT / "data/concepts-live.json").read_text(encoding="utf-8"))
    graph = json.loads((ROOT / "data/concepts-graph.json").read_text(encoding="utf-8"))
    an = {}
    p = ROOT / "data/formula-anatomy.json"
    if p.exists():
        an = json.loads(p.read_text(encoding="utf-8"))
    bases = json.loads((ROOT.parent / "b42-ml/data/formulas-linked.json")
                       .read_text(encoding="utf-8"))["bases"]
    return live, graph, an, bases


# Какие таблицы лить. Флаг --only объявлялся, но нигде не проверялся: докатка
# после обрыва честно перезаливала всё с начала (поймано 28.08, когда нужно было
# добавить только таблицы областей).
ONLY = None
ONLY_TABLES = {
    "concepts": {"concepts", "concept_full"},
    "links": {"concept_links"},
    "arts": {"concept_arts"},
    "formulas": {"formulas"},
    "groups": {"concept_groups", "graph_groups", "graph_group_links"},
}


def push(table, cols, rows, label):
    if ONLY and table not in ONLY_TABLES.get(ONLY, set()):
        return
    """Пачками ПО ОБЪЁМУ, а не по числу строк.

    Считать строками можно, пока строки одинаковые. Здесь они разные: у понятия
    с полной записью и русским переводом одна строка весит под пять килобайт, а
    у понятия без карточки — сотню байт. Сорок таких тяжёлых строк дают запрос
    на двести килобайт, и D1 отвечает 400 — ночью 28.08 на этом встала вся
    заливка реестра, когда полных карточек стало 3077 вместо 980.

    Поэтому пачку набираем по длине готового SQL и держим под лимитом; число
    строк в ней плавает само.
    """
    n, i = 0, 0
    while i < len(rows):
        chunk, size = [], 0
        while i < len(rows) and len(chunk) < BATCH:
            piece = "(" + ",".join(lit(v) for v in rows[i]) + ")"
            if chunk and size + len(piece) > SQL_BUDGET:
                break
            chunk.append(piece)
            size += len(piece) + 1
            i += 1
        d1(f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES "
           + ",".join(chunk))
        n += len(chunk)
        if n % 400 < len(chunk):
            print(f"  {label}: {n}/{len(rows)}", flush=True)
    print(f"  ✓ {label}: {n}")


def build_frames(live, graph):
    """Кадры графа — тем же построением, что рисует локальный движок."""
    nodes, edges = graph["nodes"], graph["edges"]
    groups = graph.get("groups") or []
    idx = {nd["id"]: i for i, nd in enumerate(nodes)}
    adj = defaultdict(list)
    for a, b, w in ((e[0], e[1], e[2]) for e in edges):
        adj[a].append((b, w))
        adj[b].append((a, w))

    frames = []
    # обзор: 50 групп, рёбра — суммарная мощность между группами (топ-4 на группу)
    gw = Counter()
    for a, b, w in ((e[0], e[1], e[2]) for e in edges):
        ga, gb = nodes[a].get("g"), nodes[b].get("g")
        if ga is None or gb is None or ga == gb:
            continue
        gw[(min(ga, gb), max(ga, gb))] += w
    per = defaultdict(list)
    for (a, b), w in gw.items():
        per[a].append((w, b))
        per[b].append((w, a))
    keep = {}
    for a, lst in per.items():
        for w, b in sorted(lst, reverse=True)[:4]:
            keep[(min(a, b), max(a, b))] = w
    ov_nodes = []
    for i, g in enumerate(groups):
        n_arts = sum(nodes[m]["n"] for m in g["members"] if m < len(nodes))
        ov_nodes.append({"gi": i, "label_ru": g.get("label_ru") or g.get("label_en"),
                         "label_en": g.get("label_en"), "n": n_arts,
                         "size": len(g["members"])})
    frames.append(("overview", {"nodes": ov_nodes,
                                "edges": [[a, b, w] for (a, b), w in keep.items()]},
                   len(ov_nodes)))

    # кадр каждой группы: члены + мостики наружу + её формулы
    for gi, g in enumerate(groups):
        mem = [m for m in g["members"] if m < len(nodes)]
        inset = set(mem)
        outside = {}
        fml = {}
        for m in mem:
            for b, w in adj[m]:
                if b in inset:
                    continue
                if nodes[b]["kind"] == "formula":
                    fml[b] = max(fml.get(b, 0), w)
                else:
                    outside[b] = max(outside.get(b, 0), w)
        ids = mem[:]
        ids += [b for b, _ in sorted(outside.items(), key=lambda kv: -kv[1])[:12]]
        ids += [b for b, _ in sorted(fml.items(), key=lambda kv: -kv[1])[:8]]
        pos = {v: i for i, v in enumerate(ids)}
        fn = [{"id": nodes[v]["id"], "ru": nodes[v].get("ru"), "en": nodes[v]["en"],
               "kind": nodes[v]["kind"], "n": nodes[v]["n"],
               "card": (nodes[v].get("card") or "")[:220],
               "cat": nodes[v].get("cat"), "out": v not in inset}
              for v in ids]
        seen, fe = set(), []
        for v in ids:
            for b, w in adj[v]:
                if b not in pos:
                    continue
                k = (min(pos[v], pos[b]), max(pos[v], pos[b]))
                if k not in seen:
                    seen.add(k)
                    fe.append([k[0], k[1], w])
        frames.append((f"g:{gi}", {"nodes": fn, "edges": fe}, len(fn)))
    return frames


def main():
    ap = argparse.ArgumentParser(description="Реестр знаний → D1")
    ap.add_argument("--schema", action="store_true")
    ap.add_argument("--frames", action="store_true")
    ap.add_argument("--only",
                    choices=["arts", "formulas", "concepts", "links", "groups"],
                    help="залить одну таблицу (докатка после обрыва)")
    a = ap.parse_args()
    global ONLY
    ONLY = a.only

    ensure_schema()
    if a.schema:
        return 0

    live, graph, an, bases = load()
    C = live["concepts"]
    gnode = {nd["id"]: nd for nd in graph["nodes"]}

    # Слитые понятия (tools/concept_twins.py) в облако не льём: это записи-указатели
    # без статей, связей и карточки. В D1 они дали бы пустые строки в поиске и в
    # облаке — предмет, у которого всё забрал победитель. Страница на них отвечает
    # переадресацией, и этого достаточно.
    C = {cid: v for cid, v in C.items() if not v.get("merged_into")}

    if not a.frames:
        rows = []
        for cid, v in C.items():
            g = gnode.get(cid) or {}
            rows.append([
                cid, v.get("kind") or "concept",
                (v.get("names") or {}).get("ru"), (v.get("names") or {}).get("en"),
                v.get("card_en") or "", len(v.get("articles") or []),
                len(v.get("related") or []), v.get("supers") or [], g.get("cat"),
                v.get("full"), (v.get("full_i18n") or {}).get("ru"),
                {k: v[k] for k in ("systems", "si_definition", "units_by_system")
                 if v.get(k)} or None,
                # константа без числа в динамике — то же, что на статике: пустая
                # страница вместо ответа, за которым на неё пришли
                v.get("value"), v.get("unit"), v.get("symbol"),
                v.get("section"), v.get("section_part"),
                v.get("names") or None,
            ])
        push("concepts", ["id", "kind", "name_ru", "name_en", "card", "n_arts",
                          "n_links", "groups", "cat", "full_en", "full_ru",
                          "systems", "value", "unit", "symbol", "section",
                          "part", "names"], rows, "понятия")

        # Полные записи по языкам. Английская — исходная (v["full"]), остальные
        # лежат переводами в full_i18n. Язык, которого у понятия нет, строкой не
        # становится: воркер откатится к английской.
        full_rows = []
        for cid, v in C.items():
            if v.get("full"):
                full_rows.append([cid, "en", v["full"]])
            for lang, body in (v.get("full_i18n") or {}).items():
                if body and lang != "en" and lang in ALL_LANGS:
                    full_rows.append([cid, lang, body])
        push("concept_full", ["id", "lang", "body"], full_rows, "полные записи")

        links = []
        for cid, v in C.items():
            for r in (v.get("related") or [])[:10]:
                links.append([cid, r["id"], r["w"], "c"])
            for f in (v.get("formulas") or [])[:6]:
                links.append([cid, f["id"], 1.0, "f"])
        push("concept_links", ["a", "b", "w", "kind"], links, "связи")

        # кэп 60 статей на понятие: страница показывает 40 и листает постранично,
        # а полные 200 дают 67 тысяч строк вместо 64 — лишние минуты заливки
        # ради хвоста, которого никто не пролистает
        arts = []
        for cid, v in C.items():
            for aid in (v.get("articles") or [])[:60]:
                arts.append([cid, aid, None])
        push("concept_arts", ["cid", "id", "date"], arts, "статьи понятий")

        # ГРУППЫ ТАБЛИЦАМИ, А НЕ ГОТОВЫМИ КАДРАМИ. Членство, паспорт области и
        # связи между областями — три маленькие таблицы (3.6 тысячи строк, 50 и
        # около полутора сотен), из которых воркер соберёт и обзор, и кадр
        # группы прямо в запросе. Пересчитывать кадры после каждой правки
        # реестра больше не нужно: данные обновились — кадр обновился.
        gm, gmeta, glinks = [], [], {}
        gnodes = graph.get("groups") or []
        node_group = {}
        for gi, g in enumerate(gnodes):
            n_arts = 0
            for m in g.get("members") or []:
                cid = graph["nodes"][m]["id"] if m < len(graph["nodes"]) else None
                if not cid:
                    continue
                gm.append([gi, cid])
                node_group.setdefault(m, gi)
                n_arts += graph["nodes"][m].get("n") or 0
            gmeta.append([gi, g.get("label_ru"), g.get("label_en"),
                          g.get("note_ru"), g.get("note_en"),
                          len(g.get("members") or []), n_arts])
        # связи между областями: сколько рёбер идёт из одной в другую
        for e in graph["edges"]:
            ga, gb = node_group.get(e[0]), node_group.get(e[1])
            if ga is None or gb is None or ga == gb:
                continue
            k = (min(ga, gb), max(ga, gb))
            glinks[k] = glinks.get(k, 0) + 1
        push("concept_groups", ["gid", "cid"], gm, "членство в областях")
        push("graph_groups", ["gid", "label_ru", "label_en", "note_ru", "note_en",
                              "n_con", "n_arts"], gmeta, "паспорта областей")
        push("graph_group_links", ["a", "b", "w"],
             [[a, b, w] for (a, b), w in glinks.items()], "связи областей")

        frows = []
        for b in bases:
            rec = an.get(b["base_id"]) or {}
            frows.append([b["base_id"], b.get("name") or b["base_id"],
                          b.get("latex"), b.get("card"),
                          len(b.get("applications") or []),
                          {k: rec[k] for k in ("variables", "constants", "operators",
                                               "description", "history",
                                               "applicability", "ru")
                           if rec.get(k)} or None,
                          rec.get("unit_systems") or None])
        push("formulas", ["id", "name", "latex", "card", "n_apps", "anatomy",
                          "systems"], frows, "формулы")

    # ГОТОВЫЕ КАДРЫ БОЛЬШЕ НЕ ЛЬЁМ. Обзор, кадр области и эго-кадр воркер собирает
    # запросом из concept_groups / graph_groups / graph_group_links — с 28.08, когда
    # владелец спросил «а разве это не динамика, зачем их обновлять». Таблица
    # graph_frames осталась в схеме как запасной путь для ключей, которых запрос не
    # знает, но заливать в неё весь граф незачем: сегодня она уронила синхронизацию
    # с HTTP 400 — один кадр области перевалил за размер запроса к D1, и упало это
    # ПОСЛЕ того, как всё нужное уже легло.
    print(f"✅ облако знает: {len(C)} понятий, {len(bases)} формул; "
          f"кадры графа собираются запросом")
    return 0


if __name__ == "__main__":
    sys.exit(main())
