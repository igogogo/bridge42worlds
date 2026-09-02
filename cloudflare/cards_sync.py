#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Карточки статей в D1 — единственный источник для всех списков сайта.

ЗАЧЕМ. Сегодня лента, страницы тегов, законов, учёных и разделов рисуются на клиенте из
`lang/<lang>/articles-index*.json`. Замер 2026-08-25: русский индекс — 3 717 КБ по сети,
три уровня вместе 11 МБ, и качается это при каждом заходе. Файл растёт линейно по архиву:
на 10 000 статей это 5.6 МБ, на 100 000 — 56 МБ. Одна страница ленты в двадцать карточек
весит 7 КБ, и это число не меняется ни на десяти тысячах, ни на ста. Отсюда решение
владельца 2026-08-25: списки отдаёт воркер из D1, клиент не качает ничего, что растёт.

ВТОРАЯ ЦЕЛЬ, ради которой всё и затевалось (владелец в тот же день): «уйти от пересборок
в принципе». Пока теги, законы, похожие и карусель вшиты в страницы, любая правка разметки
означает пересборку 167 981 страницы. Когда статикой остаётся только НАШ ТЕКСТ, а всё
остальное живёт в базе, правка тегов не трогает ни одной страницы.

ПОЧЕМУ ЭТОТ ФАЙЛ ПОЯВИЛСЯ ТОЛЬКО СЕЙЧАС. База `b42-cards` и её схема существуют с 6 августа:
кто-то поднял таблицы, залил треть архива — и на этом всё. Инструмент синхронизации не доехал
ни до репозитория, ни до прода, и девятнадцать дней база стояла с данными от 5 августа,
которых никто не читал. Отсюда правило владельца: доводим до прода, потом заканчиваем.

ЧТО ДЕЛАЕТ. Сверяет содержимое базы с индексами на диске и заливает РАЗНИЦУ. Каждая строка
несёт отпечаток своего содержимого (`h`), поэтому обычный день — это несколько десятков
изменившихся строк, а не перезалив тридцати трёх тысяч.

    python cloudflare/cards_sync.py --check     что разошлось, ничего не меняя
    python cloudflare/cards_sync.py --apply     залить разницу
    python cloudflare/cards_sync.py --apply --full   перезалить с нуля (после смены схемы)
"""
import sys as _s
from pathlib import Path as _P
_s.path.insert(0, str(_P(__file__).resolve().parent.parent))
from tools import runlock as _lock
import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

DB = "b42-cards"
from common import ALL_LANGS  # noqa: E402
LANGS = ALL_LANGS   # список языков один на проект: config.json через common.ALL_LANGS
# Имена файлов — те же, что читает js/search.js (VERSION_INDEX_FILES). Один источник правды:
# если там появится четвёртый уровень, здесь он должен появиться тем же именем.
VERSIONS = {"popular": "", "simple": "-simple", "advanced": "-advanced"}

# Колонки строки карточки. Порядок важен: по нему строится INSERT и считается отпечаток.
COLS = ("id", "lang", "version", "title", "oneliner", "description", "authors", "tags",
        "laws", "scientists", "categories", "primary_category", "date", "url", "image",
        "reading", "express", "km", "mix", "h")


# ─────────────────────────────── доступ к D1 ────────────────────────────────
def _env():
    out = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


_E = _env()
_ACC = _E.get("CLOUDFLARE_ACCOUNT_ID")
_TOK = _E.get("CLOUDFLARE_API_TOKEN")
_BASE = f"https://api.cloudflare.com/client/v4/accounts/{_ACC}/d1/database"
_UUID = {}


def db_uuid(name=DB):
    if name not in _UUID:
        r = requests.get(_BASE, headers={"Authorization": f"Bearer {_TOK}"}, timeout=60).json()
        for d in r.get("result") or []:
            _UUID[d["name"]] = d["uuid"]
    if name not in _UUID:
        raise SystemExit(f"нет базы {name} в аккаунте")
    return _UUID[name]


def q(sql, params=None, tries=4):
    """Один запрос к D1. Ретраи не для красоты: заливка идёт сотнями вызовов подряд,
    и один обрыв сети не должен ронять весь прогон."""
    last = None
    for i in range(tries):
        try:
            r = requests.post(f"{_BASE}/{db_uuid()}/query",
                              headers={"Authorization": f"Bearer {_TOK}"},
                              json={"sql": sql, "params": params or []}, timeout=180)
            j = r.json()
            if j.get("success"):
                return j["result"][0].get("results", [])
            last = json.dumps(j.get("errors"), ensure_ascii=False)
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"D1: {last}")


def lit(v):
    """Значение как литерал SQL.

    Параметры не используем СОЗНАТЕЛЬНО: D1 ограничивает число привязок на запрос, а мы
    вставляем пачками по полсотни строк на девятнадцать колонок — это тысяча привязок,
    которую придётся резать до пачек по пять и получить в десять раз больше вызовов.
    Данные здесь исключительно свои (собранные нашим же генератором), а одинарная кавычка
    экранируется удвоением — единственный способ сломать литерал в SQLite."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v).replace("'", "''")
    # \x00 внутри строки обрывает её на уровне драйвера, а не SQL — вырезаем.
    s = s.replace("\x00", "")
    return "'" + s + "'"


# ─────────────────────────────── схема ──────────────────────────────────────
SCHEMA = [
    # Таблица уже существует с 6 августа; здесь только то, чего в ней нет.
    "ALTER TABLE cards ADD COLUMN km INTEGER DEFAULT 0",
    "ALTER TABLE cards ADD COLUMN h TEXT",
    # Порядок «вперемешку» — любимый режим ленты по умолчанию. Считать его случайным
    # в запросе нельзя: при листании второй страницы порядок пересобрался бы, и
    # читатель увидел бы одни карточки дважды, а другие ни разу. Поэтому у каждой
    # строки есть своё постоянное число, а «перемешивание» — это сдвиг по нему на
    # семя дня: порядок устойчив внутри дня и меняется назавтра.
    "ALTER TABLE cards ADD COLUMN mix INTEGER DEFAULT 0",
    "CREATE INDEX IF NOT EXISTS cards_mix ON cards(lang, version, mix)",
    "CREATE INDEX IF NOT EXISTS cards_feed ON cards(lang, version, date DESC)",
    "CREATE INDEX IF NOT EXISTS cards_cat ON cards(lang, version, primary_category, date DESC)",
    # Авторы отдельной таблицей и БЕЗ языка с уровнем. Если хранить их в общей строке,
    # у статьи с десятью соавторами получается десять строк на каждый из пятнадцати
    # сочетаний языка и уровня — сто пятьдесят строк ради одной работы. Связь «автор —
    # работа» от языка не зависит: она одна, а карточка к ней подбирается запросом.
    """CREATE TABLE IF NOT EXISTS card_authors (
         akey TEXT NOT NULL,          -- ключ автора: фамилия + все инициалы (panov|ad)
         id   TEXT NOT NULL,          -- arXiv id работы
         date TEXT,                   -- дата нашей публикации, по ней сортируется страница
         PRIMARY KEY (akey, id)
       )""",
    # Идентификатор автора в Semantic Scholar. Кладём В СХЕМУ СРАЗУ, а не колонкой-времянкой:
    # стратег 25.08 — это будущая опора и для развода однофамильцев, и для авторской рассылки.
    # Заполняет его отдельный проход (ребро «работа → автор» от S2), здесь только место под него.
    # Правило склейки, им же предложенное и принятое: объединяем ТОЛЬКО при совпадении
    # s2_author_id; всё остальное держим раздельно. «Лучше две страницы, чем одна с чужими
    # работами» — слова владельца, доведённые до механики.
    "ALTER TABLE card_authors ADD COLUMN s2_author_id TEXT",
    # Имя автора в записи S2. Нужно как ЗАГОЛОВОК группы на странице: у S2 имя часто
    # полнее нашего («Alexander D. Panov» против «A. Panov»), и человеку, пришедшему
    # по клику на имя, именно оно помогает понять, который из трёх однофамильцев его.
    "ALTER TABLE card_authors ADD COLUMN s2_name TEXT",
    "CREATE INDEX IF NOT EXISTS card_authors_s2 ON card_authors(s2_author_id)",
    "CREATE INDEX IF NOT EXISTS card_authors_key ON card_authors(akey, date DESC)",
    # Портфель автора в arXiv целиком — из реестра по дампу (tools/author_record). Нужен
    # странице автора для честной строки «столько-то работ в arXiv, из них у нас столько»
    # и для серых столбиков под нашими на диаграмме лет.
    """CREATE TABLE IF NOT EXISTS author_refs (
         akey        TEXT PRIMARY KEY,
         arxiv_total INTEGER,
         first_year  TEXT, last_year TEXT,
         by_year     TEXT,           -- {"1999": 2, ...}
         ours_by_year TEXT
       )""",
]


def ensure_schema():
    for sql in SCHEMA:
        try:
            q(sql)
        except RuntimeError as e:
            # «duplicate column name» — колонка уже добавлена прошлым прогоном. Это не ошибка:
            # ALTER TABLE ... ADD COLUMN не умеет IF NOT EXISTS в SQLite.
            if "duplicate column" not in str(e):
                raise


# ─────────────────────────────── строки ─────────────────────────────────────
_KM = None


def km_map():
    """Какие статьи разобраны машиной знаний — по первоисточнику, а не по индексу.

    Поле `km` сборщик индекса пишет, но в живых файлах его НЕТ ни у одной записи: индекс
    обновляется по частям, и записи хранят форму того дня, когда их писали, — а `km`
    появился позже последней полной пересборки. Страница автора без этого показывала бы
    «с разбором: 0» у всех, и заметить это можно было бы только глазами.

    Читаем сами data.json: 6 678 файлов за семь секунд, один раз на прогон. После полной
    пересборки индекс понесёт `km` сам, и эта подпорка станет просто подтверждением.
    """
    global _KM
    if _KM is None:
        _KM = {}
        for f in (ROOT / "lang" / "ru" / "archive").glob("*/*/data.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if d.get("id"):
                _KM[d["id"]] = 1 if (d.get("recommend") or {}) else 0
        print(f"  разборов машины знаний в архиве: {sum(_KM.values())} из {len(_KM)}")
    return _KM


def _j(v):
    return json.dumps(v or [], ensure_ascii=False, separators=(",", ":"))


def row_of(a, lang, version):
    r = {
        "id": a.get("id", ""), "lang": lang, "version": version,
        "title": a.get("title", ""), "oneliner": a.get("oneliner", ""),
        "description": a.get("description", ""),
        "authors": _j(a.get("authors")), "tags": _j(a.get("tags")),
        "laws": _j(a.get("laws")), "scientists": _j(a.get("scientists")),
        "categories": _j(a.get("categories")),
        "primary_category": a.get("primary_category", ""),
        "date": a.get("date", ""), "url": a.get("url", ""),
        # image в индексе — булево «обложка есть». Храним как есть: клиент по нему решает,
        # резервировать ли место под картинку, а сам адрес собирается из даты и id.
        "image": "0" if a.get("image") is False else "1",
        "reading": int(a.get("reading") or 0),
        "express": 1 if a.get("express") else 0,
        # индекс может быть старым и не нести km — тогда берём из data.json (см. km_map)
        "km": 1 if (a.get("km") or km_map().get(a.get("id", ""), 0)) else 0,
        # постоянное число строки: тот же id — то же место в перемешанном порядке
        "mix": int(hashlib.md5(a.get("id", "").encode()).hexdigest()[:8], 16) % 1000003,
    }
    h = hashlib.md5("\x1f".join(str(r[c]) for c in COLS if c != "h").encode("utf-8")).hexdigest()[:16]
    r["h"] = h
    return r


def load_disk(lang, version):
    p = ROOT / "lang" / lang / f"articles-index{VERSIONS[version]}.json"
    if not p.exists():
        return {}
    try:
        idx = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  ⚠️ {p.name}: {type(e).__name__} — пропускаю")
        return {}
    out = {}
    for a in idx:
        if not a.get("id"):
            continue
        out[a["id"]] = row_of(a, lang, version)
    return out


_MIGRATED = None


def load_db(lang, version):
    """Отпечатки строк, которые уже лежат в базе.

    Терпимо к старой схеме: колонка `h` появилась вместе с этим инструментом, а таблица
    существует с 6 августа. Если колонки нет, --check обязан работать и честно сказать,
    что нужна миграция, а не падать: проверка на то и проверка, чтобы её можно было
    запустить на чём угодно."""
    global _MIGRATED
    if _MIGRATED is False:
        return {}
    try:
        rows = q("SELECT id, h FROM cards WHERE lang = ? AND version = ?", [lang, version])
    except RuntimeError as e:
        if "no such column" not in str(e):
            raise
        _MIGRATED = False
        print("  ⚠️ в базе старая схема (нет колонки h) — миграция выполнится при --apply;"
              " пока считаю всё изменившимся")
        return {}
    _MIGRATED = True
    return {r["id"]: r.get("h") for r in rows}


# ─────────────────────────────── заливка ────────────────────────────────────
# Размер пачки и число потоков подобраны замером, а не на глаз. Один вызов к D1 идёт
# 912 мс — это сеть, а не база: при пачках по сорок строк и трёх вызовах на пачку первая
# заливка ста тысяч карточек заняла бы два часа. Три команды склеиваются в один вызов
# (D1 их принимает), пачка укрупнена, вызовы идут параллельно.
# Пачка считается В БАЙТАХ, а не в строках: D1 обрывает слишком длинную команду
# («statement too long»), а карточки разнородны — у статьи с полусотней соавторов строка
# в разы длиннее обычной. Пачка по числу строк ломается ровно на таких, и ломается не
# сразу, а на середине заливки.
MAX_SQL = 45_000      # символов на одну команду; предел D1 выше, но запас нужен на fts
BATCH = 400           # верхняя граница строк в пачке — на случай очень коротких карточек
WORKERS = 6


# ПИСЬМЕННОСТИ БЕЗ ПРОБЕЛОВ В ПОЛНОТЕКСТЕ.
#
# cards_fts токенизируется через unicode61: он режет текст по не-буквам. В китайском
# между словами разделителей нет вовсе, и всё предложение становится ОДНИМ токеном —
# поиск по слову не найдёт ничего. Проверено в живом D1 31 августа.
#
# Trigram-токенизатор D1 принимает, но он индексирует ТРОЙКИ знаков и не находит
# запросов короче трёх символов: 黑洞 «чёрная дыра» и 恒星 «звезда» — по два знака,
# 熵 «энтропия» — один. Для научных терминов это приговор.
#
# Поэтому разделяем иероглифы пробелом ПРИ ЗАПИСИ: тогда нынешний токенизатор видит
# каждый знак словом, а запрос ищется фразой. Замер на живом D1: находит от одного
# знака. Схема, таблица и ручка остаются прежними; остальные языки не затронуты.
import re as _re

_CJK = _re.compile(
    r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]")


def fts_body(text, lang):
    """Тело для полнотекста. Для языков без пробелов — по знаку через пробел."""
    if lang not in ("zh", "ja") or not text:
        return text
    # Латиница, цифры и знаки препинания остаются как есть: разрывать «LIGO» или
    # «2.4 ГэВ» посимвольно значило бы сломать поиск ровно по тому, что ищут чаще
    # всего в научном тексте.
    return _CJK.sub(lambda m: " " + m.group(0) + " ", text)


# ТЕЛО ПОЛНОТЕКСТА НЕ ТРОГАЕМ, И ЭТО ОСОЗНАННО. Была попытка (01.09) дописать в него
# авторов, учёных и понятия — чтобы поиск находил статьи по связкам. Работало бы, но
# стоило бы переписи всех 101 235 строк полнотекста при том, что сами карточки не
# менялись ни на байт. Владелец: «не понимаю, почему опять пересборка, мы ничего не
# трогаем в карточках — думай, как обойти свои пересборки».
#
# Обошли: связки уже лежат в базе отдельными таблицами — concepts (имена понятий на
# пяти языках), concept_arts (111 тысяч связей понятие→работа), card_authors (94 тысячи
# связей автор→работа). Поиск спрашивает их запросом (worker.js, handleWordSearch), а
# не хранит их копию в третьем месте. Ни одной новой записи.

def _chunk_sql(part, lang, version):
    """Одна пачка — один вызов: вставка карточек, чистка их старых записей в полнотексте
    и вставка новых. Полнотекст держим в том же ритме: строка без своего текста в fts —
    это статья, которую не найти словами, и заметить такое можно только жалобой читателя."""
    cols = ",".join(COLS)
    vals = ",".join("(" + ",".join(lit(r[c]) for c in COLS) + ")" for r in part)
    ids = ",".join(lit(r["id"]) for r in part)
    fts = ",".join(
        "(" + lit(fts_body(" ".join((r["title"], r["oneliner"], r["description"])), lang)) + "," +
        lit(r["id"]) + "," + lit(lang) + "," + lit(version) + ")" for r in part)
    return (f"INSERT OR REPLACE INTO cards ({cols}) VALUES {vals};"
            f"DELETE FROM cards_fts WHERE id IN ({ids}) AND lang = {lit(lang)}"
            f" AND version = {lit(version)};"
            f"INSERT INTO cards_fts (body, id, lang, version) VALUES {fts};")


def push(rows, lang, version):
    """Вставляет/обновляет строки. INSERT OR REPLACE, потому что ключ (id,lang,version)
    первичный: повторная заливка той же статьи не плодит дублей."""
    from concurrent.futures import ThreadPoolExecutor
    parts, cur, size = [], [], 0
    for r in rows:
        # длина строки в SQL прикидывается по её содержимому: точный подсчёт стоил бы
        # сборки литералов дважды, а промах в пару процентов покрыт запасом MAX_SQL
        w = sum(len(str(r[c])) for c in COLS) + 60
        if cur and (size + w > MAX_SQL or len(cur) >= BATCH):
            parts.append(cur)
            cur, size = [], 0
        cur.append(r)
        size += w
    if cur:
        parts.append(cur)
    done = [0]

    def one(part):
        q(_chunk_sql(part, lang, version))
        done[0] += len(part)
        if done[0] % 1000 < len(part):
            print(f"      … {done[0]}/{len(rows)}")

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(one, parts))
    if rows:
        print(f"      залито {len(rows)} строк          ")
    return len(rows)


def drop(ids, lang, version):
    for i in range(0, len(ids), 400):
        part = ids[i:i + 400]
        inlist = ",".join(lit(x) for x in part)
        q(f"DELETE FROM cards WHERE lang = {lit(lang)} AND version = {lit(version)} "
          f"AND id IN ({inlist});"
          f"DELETE FROM cards_fts WHERE lang = {lit(lang)} AND version = {lit(version)} "
          f"AND id IN ({inlist});")
    return len(ids)


# ─────────────────────────────── авторы ─────────────────────────────────────
def sync_author_refs(apply):
    """Портфели авторов: только те ключи, что есть в card_authors, — остальным страница
    не нужна. Разница по отпечатку не считается: строк ~15 тыс., полная перезаливка раз
    в день дешевле бухгалтерии."""
    p = ROOT / "data" / "author-records.json"
    if not p.exists():
        return 0
    try:
        recs = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return 0
    keys = {r["akey"] for r in q("SELECT DISTINCT akey FROM card_authors")}
    rows = []
    for k in keys:
        r = recs.get(k)
        if not r:
            continue
        rows.append((k, int(r.get("arxiv_total") or 0),
                     str(r.get("first_year") or ""), str(r.get("last_year") or ""),
                     json.dumps(r.get("arxiv_by_year") or {}, ensure_ascii=False),
                     json.dumps(r.get("ours_by_year") or {}, ensure_ascii=False)))
    if apply and rows:
        for i in range(0, len(rows), 80):
            part = rows[i:i + 80]
            vals = ",".join("(" + ",".join(lit(v) for v in r) + ")" for r in part)
            q("INSERT OR REPLACE INTO author_refs "
              f"(akey, arxiv_total, first_year, last_year, by_year, ours_by_year) VALUES {vals}")
        print(f"      портфелей авторов: {len(rows)}")
    return len(rows)


def sync_authors(apply):
    """Связь «автор — работа». Ключ считает тот же код, что строит страницы авторов
    (tools/author_record.key_from_display), иначе страница и лента разойдутся в том,
    кого считать одним человеком, — а это ровно тот баг с четырьмя Пановыми под одним
    ключом, который владелец поймал 24 августа."""
    from tools.author_record import key_from_display
    # ИСТОЧНИК — ГРАФ АВТОРОВ, а не индекс лент.
    #
    # Индекс — файл для браузера, и в нём авторы обрезались (пятьдесят на работу).
    # Страницы же строятся из графа, где авторы ВСЕ. Отсюда расхождение, которое
    # владелец увидел 31 августа на /lang/en/authors/U_Kolb.html: страница есть,
    # а списка работ и статистики нет. Замер: 46 991 автор в графе против 30 315 в
    # облаке — шестнадцать с половиной тысяч человек с пустой страницей. У работы
    # 2511.14407 таких двести семьдесят шесть из трёхсот двадцати шести.
    #
    # Потолок в индексе снят тем же решением, но полагаться на индекс здесь всё
    # равно неправильно: он про то, что качает читатель, а не про то, кто автор.
    graph_p = ROOT / "data" / "authors-graph.json"
    p = ROOT / "lang" / "ru" / "articles-index.json"
    if not p.exists():
        return 0, 0
    idx = json.loads(p.read_text(encoding="utf-8"))
    when = {a["id"]: a.get("date", "") for a in idx}
    want = {}
    if graph_p.exists():
        graph = json.loads(graph_p.read_text(encoding="utf-8"))
        for name, v in graph.items():
            k = key_from_display(name)
            if not k:
                continue
            for aid in (v.get("articles") or []):
                # Дата нужна для сортировки списка работ; берём из индекса, а работу,
                # которой в индексе нет, не берём вовсе — её карточки в облаке тоже нет.
                if aid in when:
                    want[(k, aid)] = when[aid]
        print(f"      источник: граф авторов ({len(graph)} человек)")
    else:
        print("      ⚠️ графа авторов нет — беру индекс (авторы там обрезаны)")
        for a in idx:
            for name in (a.get("authors") or []):
                k = key_from_display(name)
                if k:
                    want[(k, a["id"])] = a.get("date", "")
    try:
        have = {(r["akey"], r["id"]) for r in q("SELECT akey, id FROM card_authors")}
    except RuntimeError as e:
        # Таблицы ещё нет — тот же случай, что с колонкой h: проверка обязана работать
        # на старой схеме и честно показать объём предстоящей заливки.
        if "no such table" not in str(e):
            raise
        have = set()
    add = [(k, i, d) for (k, i), d in want.items() if (k, i) not in have]
    gone = [x for x in have if x not in want]
    if apply and add:
        for i in range(0, len(add), BATCH):
            part = add[i:i + BATCH]
            vals = ",".join(f"({lit(k)},{lit(idx_)},{lit(d)})" for k, idx_, d in part)
            q(f"INSERT OR REPLACE INTO card_authors (akey, id, date) VALUES {vals}")
            print(f"      … авторы {min(i + BATCH, len(add))}/{len(add)}", end="\r")
        print(f"      добавлено связей: {len(add)}          ")
    if apply and gone:
        for i in range(0, len(gone), 200):
            part = gone[i:i + 200]
            cond = " OR ".join(f"(akey={lit(k)} AND id={lit(x)})" for k, x in part)
            q(f"DELETE FROM card_authors WHERE {cond}")
    return len(add), len(gone)


# ─────────────────────────────── главное ────────────────────────────────────
def main():
    _lock.acquire("d1", "карточки статей в облако")
    # Общий замок (tools/freeze.py): пока стоит, прогоны не начинаются.
    try:
        import sys as _s
        from pathlib import Path as _P
        _r = str(_P(__file__).resolve().parent.parent)
        if _r not in _s.path:
            _s.path.insert(0, _r)
        from tools.freeze import guard as _frozen
        _frozen("заливка карточек")
    except ImportError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="показать расхождение, не менять")
    ap.add_argument("--apply", action="store_true", help="залить разницу")
    ap.add_argument("--full", action="store_true", help="перезалить всё, не глядя на отпечатки")
    ap.add_argument("--lang", nargs="*", default=list(LANGS))
    args = ap.parse_args()
    if not (args.check or args.apply):
        print("укажи --check или --apply")
        return 1
    if not (_ACC and _TOK):
        print("нет CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN в .env")
        return 1

    if args.apply:
        ensure_schema()

    total_new = total_upd = total_del = 0
    for lang in args.lang:
        for version in VERSIONS:
            disk = load_disk(lang, version)
            if not disk:
                continue
            have = {} if args.full else load_db(lang, version)
            new = [r for i, r in disk.items() if i not in have]
            upd = [r for i, r in disk.items() if i in have and have[i] != r["h"]]
            gone = [i for i in have if i not in disk]
            total_new += len(new)
            total_upd += len(upd)
            total_del += len(gone)
            mark = "" if (new or upd or gone) else "  ✓ совпадает"
            print(f"  {lang}/{version:9} на диске {len(disk):5}, в базе {len(have):5}"
                  f" · новых {len(new)}, изменилось {len(upd)}, лишних {len(gone)}{mark}")
            if args.apply and (new or upd):
                push(new + upd, lang, version)
            if args.apply and gone:
                drop(gone, lang, version)
            if args.apply:
                q("INSERT OR REPLACE INTO cards_state (key, hash, rows, updated) "
                  "VALUES (?, ?, ?, datetime('now'))",
                  [f"{lang}/{version}",
                   hashlib.md5("".join(sorted(r["h"] for r in disk.values())).encode()).hexdigest(),
                   len(disk)])

    a_add, a_gone = sync_authors(args.apply)
    n_refs = sync_author_refs(args.apply)
    print(f"\n  авторы: связей добавить {a_add}, убрать {a_gone}")
    print(f"  портфелей arXiv: {n_refs}")
    print(f"\nитого: новых {total_new}, изменилось {total_upd}, лишних {total_del}"
          + ("" if args.apply else "  (ничего не менялось — это --check)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
