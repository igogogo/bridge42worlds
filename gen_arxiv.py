#!/usr/bin/env python3
"""Слой arXiv/PDF: получение статей за день, лицензия, скачивание/парсинг PDF,
отсечение списка литературы (References), извлечение подписей к рисункам.

Чистый листовой модуль (только requests / xml / pypdf), без зависимостей от рендера.
"""

import time
import re
import json
import sys
import threading
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from pypdf import PdfReader

# cp1252-консоль Windows роняет печать ✅/❌ при ручном запуске
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BULK_DIR = Path("data/arxiv-bulk")

# Сюда пишется КАЖДЫЙ неудавшийся запрос к arXiv за прогон. Нужен, потому что отказ
# и «сегодня статей нет» до сих пор выглядели одинаково: пустой список. 1–2 августа 2026
# ночной прогон три дня подряд завершался с кодом «успех» и не делал ни одной статьи —
# лента стояла, и об этом никто не узнал. Отличить одно от другого можно только так:
# запомнить, был ли отказ, и не дать вызывающему решить, что arXiv просто промолчал.
FETCH_FAILURES = []


def _get_with_retry(url, params=None, timeout=30, retries=5):
    """arXiv отдаёт то 429 (перегрузка), то просто зависший коннект без ответа — раньше
    ЛЮБАЯ из этих ошибок валила весь батч (напр. на 13-й день из 31 в диапазоне). Тот же
    нарастающий бэкофф, что и у common.chat() для LLM-вызовов."""
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 429 and attempt < retries:
                wait = 60 + [10, 30][min(attempt - 1, 1)]
                print(f"  ⚠️ arXiv 429 (перегрузка) — retry {attempt}/{retries} через {wait}с")
                time.sleep(wait)
                continue
            return r
        except requests.exceptions.RequestException as e:
            if attempt == retries:
                raise
            # Паузы длиннее прежних. Замер 19 августа: arXiv не отвечал дольше двух
            # минут, а три попытки с паузами 10-30-30 укладывались как раз в это время
            # и сдавались — дневной прогон встал, за сутки не вышло ни одной статьи.
            # Теперь пять попыток и паузы до двух минут: суммарно около четырёх минут
            # ожидания вместо полутора. Ждать дольше дешевле, чем терять день.
            wait = [10, 30, 60, 120, 120][min(attempt - 1, 4)]
            # Со второй попытки идём на зеркало: у arXiv два адреса выдачи, и падают
            # они обычно не одновременно. Меняем в любую сторону — часть наших вызовов
            # уже ходит на es.arxiv.org, и односторонняя замена им бы не помогла.
            if attempt >= 2:
                if "export.arxiv.org" in url:
                    url = url.replace("export.arxiv.org", "es.arxiv.org")
                elif "es.arxiv.org" in url:
                    url = url.replace("es.arxiv.org", "export.arxiv.org")
                print(f"  ↪ пробую другое зеркало: {url.split('/')[2]}")
            print(f"  ⚠️ arXiv connection error: {e} — retry {attempt}/{retries} через {wait}с")
            time.sleep(wait)


_last_call = [0.0]


def _pace(gap=3.0):
    """Выдержка между запросами к живому API. arXiv просит не чаще одного раза в три
    секунды, а периметр дня — это 14 запросов подряд без единой паузы. Пока отказ был
    неотличим от «статей нет», расплата за такую спешку была не видна; теперь видна,
    но правильнее не нарываться. Ждём ровно недостающее, а не фиксированные три секунды."""
    wait = gap - (time.monotonic() - _last_call[0])
    if 0 < wait <= gap:
        time.sleep(wait)
    _last_call[0] = time.monotonic()


def _category_pattern(category):
    """arXiv 'cat:X.*' — wildcard-совпадение по префиксу подкатегорий, 'cat:X' — точное имя."""
    if category.endswith(".*"):
        prefix = re.escape(category[:-2])
        return re.compile(rf'^{prefix}(\..+)?$')
    return re.compile(rf'^{re.escape(category)}$')


def _matches_category(cats, pattern):
    return any(pattern.match(c) for c in cats)


def _author_name(parsed):
    last, first, suffix = (parsed + ["", "", ""])[:3]
    name = f"{first} {last}".strip()
    return f"{name} {suffix}".strip() if suffix else name


def fetch_arxiv_local(date_str, category="astro-ph.*"):
    """Ищет статьи за день в локальном чанке (data/arxiv-bulk/{YYYY-MM}.jsonl,
    см. arxiv_bulk_chunk.py) — обходит rate-limit живого arXiv API для
    исторических диапазонов. Возвращает None, если чанк за этот месяц не скачан
    (тогда fetch_arxiv() падает на живой API), иначе список статей (может быть пустым)."""
    chunk = BULK_DIR / f"{date_str[:7]}.jsonl"
    if not chunk.exists():
        return None
    pattern = _category_pattern(category)
    articles = []
    with chunk.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("published") != date_str:
                continue
            cats = d.get("categories") or []
            if not _matches_category(cats, pattern):
                continue
            articles.append({
                "id": d.get("id"),
                "title": d.get("title", ""),
                "summary": d.get("abstract", ""),
                "authors": [_author_name(a) for a in d.get("authors_parsed") or []],
                "published": d.get("published", ""),
                "categories": cats,
                "primary_category": cats[0] if cats else "",
            })
    print(f"  📦 Локальный кэш: {len(articles)} статей")
    return articles


def _bulk_month(aid):
    """Месяц чанка по идентификатору: 2404.01572 → 2024-04, astro-ph/9901001 → 1999-01."""
    aid = re.sub(r"v\d+$", "", (aid or "").strip())
    m = re.match(r"^(\d{2})(\d{2})\.\d{4,5}$", aid)                 # новый вид
    if m:
        return f"20{m.group(1)}-{m.group(2)}"
    m = re.match(r"^[a-z-]+(?:\.[A-Z]{2})?/(\d{2})(\d{2})\d+$", aid)  # старый вид
    if m:
        yy = int(m.group(1))
        return f"{1900 + yy if yy >= 91 else 2000 + yy}-{m.group(2)}"
    return None


_BULK_CACHE = {}


def local_meta(aid):
    """Метаданные одной работы из нашего дампа. None — если её там нет.

    ЗАЧЕМ. Владелец 06.09: «база у нас есть своя и обновляемая». Разбор по списку id ходил
    за заголовком и аннотацией в живой arXiv — по два запроса на работу, и ночью 06.09
    прогон на них встал (шесть работ из восьми потеряны на read timeout к export.arxiv.org).
    В чанке лежит ровно то же самое: id, title, abstract, authors_parsed, categories,
    published. К сети идём только за тем, чего в дампе нет, — за работами свежее выгрузки.

    Чанк месяца читается один раз за процесс и держится словарём: файл на 4–8 тысяч работ,
    это доли секунды и десятки мегабайт, а работы одного прогона обычно из соседних месяцев.
    """
    mon = _bulk_month(aid)
    if not mon:
        return None
    base = re.sub(r"v\d+$", "", (aid or "").strip())
    idx = _BULK_CACHE.get(mon)
    if idx is None:
        chunk = BULK_DIR / f"{mon}.jsonl"
        if not chunk.exists():
            _BULK_CACHE[mon] = {}
            return None
        idx = {}
        try:
            with chunk.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if d.get("id"):
                        idx[d["id"]] = d
        except OSError:
            idx = {}
        _BULK_CACHE[mon] = idx
    d = idx.get(base)
    if not d or not d.get("title"):
        return None
    cats = d.get("categories") or []
    return {
        "id": aid,
        "title": " ".join((d.get("title") or "").split()),
        "summary": " ".join((d.get("abstract") or "").split()),
        "authors": [_author_name(a) for a in d.get("authors_parsed") or []],
        "published": d.get("published", ""),
        "categories": cats,
        "primary_category": cats[0] if cats else "",
        "from_local": True,
    }


def local_atom(meta):
    """Тот же ответ, что отдала бы ручка api/query, — собранный из нашей базы.

    Файл arxiv-atom.xml в папке статьи в контенте не участвует, но из него берёт авторский
    абстракт бэкфилл аннотаций (generate.backfill_abstracts). Поэтому не оставляем его
    пустым, когда данные есть на диске: пишем ту же структуру, что парсит бэкфилл.
    """
    def esc(t):
        return (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    auth = "".join(f"<author><name>{esc(n)}</name></author>" for n in meta.get("authors") or [])
    cats = "".join(f'<category term="{esc(c)}"/>' for c in meta.get("categories") or [])
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">\n'
        "<!-- собрано из нашего дампа arXiv (data/arxiv-bulk), без обращения к сети -->\n"
        "<entry>"
        f"<id>http://arxiv.org/abs/{esc(meta.get('id'))}</id>"
        f"<title>{esc(meta.get('title'))}</title>"
        f"<summary>{esc(meta.get('summary'))}</summary>"
        f"<published>{esc(meta.get('published'))}</published>"
        f"{auth}{cats}"
        f'<arxiv:primary_category term="{esc(meta.get("primary_category"))}"/>'
        "</entry>\n</feed>\n")


# ── arXiv ──
def fetch_arxiv(date_str, category="astro-ph.*"):
    local = fetch_arxiv_local(date_str, category)
    if local:
        return local
    # Пустой список из чанка — НЕ повод верить, что статей нет: у сырьевой выгрузки arXiv
    # лаг в дни/недели, и чанк месяца может кончаться серединой месяца. Именно так конвейер
    # молча простоял 13 дней (16–29 июля 2026): чанк июля существовал, дни после 16-го в нём
    # отсутствовали, и ночной прогон честно находил ноль. Пусто в кэше → проверяем живой API.
    if local is not None:
        print("  📦 Кэш пуст за этот день — падаю на живой arXiv API (лаг выгрузки)")
    _pace()
    f = f"{date_str.replace('-', '')}0000"
    t = f"{date_str.replace('-', '')}2359"
    url = "https://es.arxiv.org/api/query"
    params = {
        "search_query": f"cat:{category} AND submittedDate:[{f} TO {t}]",
        "start": 0, "max_results": 200,
        "sortBy": "submittedDate", "sortOrder": "descending"
    }
    try:
        r = _get_with_retry(url, params=params, timeout=30)
    except requests.exceptions.RequestException as e:
        print(f"  ❌ arXiv API: не удалось получить ответ после ретраев ({e})")
        FETCH_FAILURES.append(f"{category}: сеть — {type(e).__name__}")
        return []
    Path(f"temp/{date_str}").mkdir(parents=True, exist_ok=True)
    Path(f"temp/{date_str}/arxiv-api.xml").write_text(r.text, encoding="utf-8")

    if not r.text or r.status_code != 200:
        # 429 сюда доходит, только когда исчерпаны ретраи: значит arXiv нас душит всерьёз,
        # и это НЕ «статей нет».
        print(f"  ❌ arXiv API error: status {r.status_code}")
        FETCH_FAILURES.append(f"{category}: HTTP {r.status_code}")
        return []
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        print("  ❌ arXiv API: ответ пришёл, но это не XML")
        FETCH_FAILURES.append(f"{category}: ответ не XML")
        return []

    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    articles = []
    for e in root.findall("atom:entry", ns):
        try:
            aid = e.find("atom:id", ns).text.split("/abs/")[-1]
            cats = list(dict.fromkeys(
                c.get("term") for c in e.findall("atom:category", ns) if c.get("term")))
            primary = e.find("arxiv:primary_category", ns)
            primary_cat = primary.get("term", "") if primary is not None else (cats[0] if cats else "")
            articles.append({
                "id": aid,
                # " ".join(split()) вместо replace("\n", " "): arXiv переносит строки
                # ВМЕСТЕ С ОТСТУПОМ, и простая замена оставляла «слово   слово» —
                # три пробела посреди заголовка. На странице это читается как разрыв
                # (владелец поймал 12 августа), и попадало в 2% заголовков архива.
                "title": " ".join(e.find("atom:title", ns).text.split()),
                "summary": " ".join(e.find("atom:summary", ns).text.split()),
                "authors": [a.find("atom:name", ns).text for a in e.findall("atom:author", ns)],
                "published": e.find("atom:published", ns).text,
                "categories": cats,
                "primary_category": primary_cat,
            })
        except Exception:
            pass
    # Галочку ставим только тогда, когда есть чему радоваться. Ноль со знаком «успех»
    # три ночи подряд и был причиной, по которой простой ленты никто не заметил.
    print(f"  {'✅' if articles else '·'} Found: {len(articles)} articles")
    return articles


# ── License ──
def license_label(lic_url):
    """Человеческое имя лицензии по её адресу.

    До 2026-08-18 всё, что не CC BY 4.0, подписывалось «CC BY» — и 2786 статей под
    arXiv nonexclusive-distrib (это НЕ свободная лицензия, права даны только arXiv)
    носили чужую этикетку. Ссылка вела на верный адрес, но слова врали; на производной
    работе неверно названная лицензия хуже, чем никакая.
    """
    u = lic_url or ""
    if "by-nc-nd/4.0" in u:
        return "CC BY-NC-ND 4.0"
    if "by-nc-sa/4.0" in u:
        return "CC BY-NC-SA 4.0"
    if "by-nc/4.0" in u:
        return "CC BY-NC 4.0"
    if "by-sa/4.0" in u:
        return "CC BY-SA 4.0"
    if "by/4.0" in u:
        return "CC BY 4.0"
    if "zero/1.0" in u:
        return "CC0 1.0"
    if "nonexclusive-distrib" in u:
        return "arXiv non-exclusive"
    return "license"


# Лицензии, под которыми работу МОЖНО разобрать своими словами, но НЕЛЬЗЯ перерабатывать
# авторский текст и изображения. NC — некоммерческое использование (наш сайт без рекламы
# и платного доступа), ND — запрет производных.
#
# Что именно это разрешает нам. Копирайт защищает выражение, а не факты и идеи: пересказ
# работы своими словами — это наша собственная работа, а не производная от чужой (так живёт
# вся научная журналистика). Дословная авторская аннотация показывается неизменной, с именем
# автора и ссылкой на источник — это разрешённое распространение оригинала. А вот перевод
# авторских подписей к рисункам — уже переработка чужого текста, и её мы не делаем: у таких
# работ рисунки из PDF не берём вовсе, обложка у статьи своя.
ANALYSIS_ONLY = ("by-nc-nd/4.0", "by-nc-sa/4.0", "by-nc/4.0")


def license_class(lic_url):
    """free — свободная переработка; analysis — только собственный разбор; no — не берём."""
    u = lic_url or ""
    if not u:
        return "no"
    if any(a in u for a in ("by/4.0", "by-sa/4.0", "zero/1.0")):
        return "free"
    # arXiv non-exclusive-distrib — НЕ свободная лицензия. Она даёт право распространять
    # работу одному только arXiv; третьим лицам она не даёт ничего сверх цитирования.
    # Пересказ своими словами законен (идеи и факты не охраняются), а воспроизводить
    # авторские рисунки нельзя. С 18.08 она стояла в списке «свободных», и под этой
    # ошибкой на сайт ушли рисунки 2 137 работ (владелец 02.09: «мы берём то, что
    # открытое; то, что нет — пересказываем, но тогда без картинок»).
    if any(a in u for a in ANALYSIS_ONLY) or "nonexclusive-distrib" in u:
        return "analysis"
    return "no"


# Лицензии из НАШЕГО индекса, без обращений к arXiv.
#
# Владелец 2026-08-19: «зачем нам лезть в архив, у нас же есть база — потом заливаем,
# потом вектор обновляем, потом ищем; нам API arXiv-то зачем». Он прав: data/arxiv-index.jsonl
# содержит 713 256 записей вида id → лицензия, собранных из того же дампа. А конвейер
# при этом спрашивал OAI-ручку по каждой статье отдельно: на пять тысяч статей в год это
# пять тысяч запросов с трёхсекундной выдержкой, то есть четыре часа ожидания и столько же
# поводов упасть по таймауту — ровно то, из-за чего 19 августа встал дневной прогон.
#
# Индекс читается один раз за процесс и держится в памяти: 700 тысяч коротких ключей.
# Строки лицензий интернируются — их всего шесть разных на весь arXiv, и без этого
# словарь весил бы втрое больше. К сети идём ТОЛЬКО за тем, чего в индексе нет:
# за работами свежее последнего обновления дампа.
# Соединение — СВОЁ У КАЖДОГО ПОТОКА. sqlite не даёт пользоваться объектом из
# чужого потока, и одно соединение на процесс валило разбор лицензий, как только
# статьи дня пошли пачкой: «SQLite objects created in a thread can only be used
# in that same thread» (29.08, прогон за 26 августа). Ошибка глушилась выше по
# стеку, и работа просто оставалась без лицензии из базы — то есть уезжала
# спрашивать её у arXiv по сети, хотя ответ лежал на диске.
_LIC_TL = threading.local()
_LIC_BUILD = threading.Lock()
_LIC_PATH = Path("data/arxiv-index.jsonl")
_LIC_SQLITE = Path("data/arxiv-licenses.sqlite")


def _lic_db():
    """Лицензии в sqlite: 3,1 млн работ, поиск за микросекунды и почти без памяти.

    Первая версия держала индекс словарём в памяти. На 713 тысячах записей это ещё
    проходило, но полный индекс — 3 100 507 работ и 454 МБ текста: столько памяти
    отнимать у процесса, который параллельно собирает сайт, нельзя. sqlite из стандартной
    библиотеки решает это без единой зависимости: файл строится один раз за минуту,
    дальше живёт рядом с индексом и обновляется вместе с ним.
    """
    db = getattr(_LIC_TL, "db", None)
    if db is not None:
        return db
    import sqlite3
    # Строит базу ОДИН поток: остальные ждут на замке и застают готовый файл.
    with _LIC_BUILD:
        fresh = (_LIC_SQLITE.exists() and _LIC_PATH.exists()
                 and _LIC_SQLITE.stat().st_mtime >= _LIC_PATH.stat().st_mtime)
        if not fresh and _LIC_PATH.exists():
            print("  📇 строю базу лицензий из индекса (один раз)...")
            tmp = _LIC_SQLITE.with_suffix(".tmp")
            tmp.unlink(missing_ok=True)
            con = sqlite3.connect(tmp)
            con.execute("CREATE TABLE lic (id TEXT PRIMARY KEY, l TEXT)")
            rows, n = [], 0
            with _LIC_PATH.open(encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    try:
                        d = json.loads(line)
                    except Exception:
                        continue
                    rows.append((d.get("id", ""), d.get("l") or ""))
                    if len(rows) >= 50000:
                        con.executemany("INSERT OR REPLACE INTO lic VALUES (?,?)", rows)
                        n += len(rows); rows = []
            if rows:
                con.executemany("INSERT OR REPLACE INTO lic VALUES (?,?)", rows)
                n += len(rows)
            con.commit(); con.close()
            tmp.replace(_LIC_SQLITE)
            print(f"  📇 база лицензий готова: {n} работ")
    if _LIC_SQLITE.exists():
        _LIC_TL.db = sqlite3.connect(f"file:{_LIC_SQLITE}?mode=ro", uri=True)
    return getattr(_LIC_TL, "db", None)


def local_license(arxiv_id):
    """Лицензия из нашей базы. None — если работы там нет (значит, свежее дампа)."""
    db = _lic_db()
    if db is None:
        return None
    base = re.sub(r"v\d+$", "", arxiv_id or "")
    row = db.execute("SELECT l FROM lic WHERE id = ?", (base,)).fetchone()
    return row[0] if row else None


def get_license(arxiv_id):
    try:
        r = _get_with_retry("https://es.arxiv.org/oai2", params={
            "verb": "GetRecord", "identifier": f"oai:arXiv.org:{arxiv_id}", "metadataPrefix": "arXiv"
        }, timeout=10)
        return r.text
    except requests.exceptions.RequestException:
        return None


def is_allowed_license(xml_text):
    if not xml_text:
        return False, None
    try:
        root = ET.fromstring(xml_text)
        lic = root.find(".//{http://arxiv.org/OAI/arXiv/}license")
        if lic is None:
            return False, None
        lic_url = lic.text
        allowed = ["by/4.0", "by-sa/4.0", "zero/1.0", "nonexclusive-distrib/1.0"]
        return any(a in lic_url for a in allowed), lic_url
    except Exception:
        return False, None


# ── PDF ──
PDF_DIR = Path("temp")


def pdf_ok(p):
    """Годен ли файл в кэше: есть, не обрубок, начинается подписью PDF.

    Без проверки кэш врёт. Убитый прогон (сон машины, Ctrl+C) оставлял в temp/ файл на
    несколько килобайт, следующий прогон видел «PDF уже есть» и отдавал разбору пустой
    текст — работа выходила без рисунков и без полного текста, молча.
    """
    try:
        if not p.exists() or p.stat().st_size < 10_000:
            return False
        with p.open("rb") as f:
            return f.read(5).startswith(b"%PDF")
    except OSError:
        return False


def pdf_cached(aid):
    """Путь к годному файлу в кэше или None."""
    p = PDF_DIR / f"{aid}.pdf"
    return p if pdf_ok(p) else None


def prefetch_pdfs(ids, log=print):
    """Забрать PDF списка работ в кэш ДО разбора (владелец 06.09).

    Зачем отдельным шагом. Скачивание — единственное, что нельзя взять из нашей базы, и
    единственное место, где прогон зависит от чужой доступности. Внутри генерации его
    неудача стоит всей работы: разбор, перевод и разметка не начнутся вовсе. Здесь
    неудача стоит ровно одного файла, а работа просто уходит в конец очереди.

    Идём по одному, а не пачкой: arXiv ограничивает частоту, и параллельная качка тех же
    двух-двадцати мегабайт скорее приблизит отказ, чем ускорит прогон. Готовое из кэша
    пропускаем — на повторе прогона шаг отрабатывает мгновенно.
    """
    need = [i for i in ids if not pdf_cached(i)]
    if not need:
        log(f"  📥 PDF: все {len(ids)} уже в кэше")
        return {"ready": len(ids), "got": 0, "failed": []}
    got, failed = 0, []
    for aid in need:
        try:
            download_pdf(aid)
            got += 1
        except Exception as e:                                   # noqa: BLE001
            failed.append(aid)
            log(f"  📥 PDF {aid}: не скачался ({type(e).__name__}) — попробуем позже")
    log(f"  📥 PDF: в кэше {len(ids) - len(failed)} из {len(ids)}"
        + (f", не далось {len(failed)}" if failed else ""))
    return {"ready": len(ids) - len(failed), "got": got, "failed": failed}


def download_pdf(aid):
    p = PDF_DIR / f"{aid}.pdf"
    p.parent.mkdir(exist_ok=True)
    # Времянка чистится ЗДЕСЬ, при каждом обращении — а не отдельной задачей, которую
    # забудут поставить. Найдено 18 августа: temp/ не чистил никто с июля, 6306 PDF
    # съели 27 ГБ и оставили на диске 8.6 — следующая ночная накачка встала бы по
    # месту. Копия PDF у каждой статьи лежит в её папке (original.pdf), поэтому
    # времянка старше двух суток — чистый дубль. Двое суток, а не сутки: параллельный
    # прогон может держать вчерашний файл.
    import time as _t
    cutoff = _t.time() - 2 * 86400
    for old_pdf in list(p.parent.glob("*.pdf")) + list(p.parent.glob("*.part")):
        try:
            if old_pdf.stat().st_mtime < cutoff:
                old_pdf.unlink()
        except OSError:
            pass                     # занят параллельным прогоном — заберём в следующий раз
    if not pdf_ok(p):
        # Обрубок от убитого прогона в кэше не остаётся: либо годный файл, либо ничего.
        p.unlink(missing_ok=True)
        # Через общий ретрай, а не голым requests.get: в файле есть _get_with_retry,
        # и все обращения к arXiv идут через него — кроме этого, единственного. Прогон
        # 2026-07-31 потерял на этом две статьи: ReadTimeout при скачивании PDF ронял
        # статью целиком, хотя повтор через десяток секунд проходит. Класс ошибки тот же,
        # что у 429 и обрыва связи, которые здесь давно обрабатываются.
        data = _get_with_retry(f"https://arxiv.org/pdf/{aid}.pdf", timeout=60).content
        # Пишем через времянку: прогон, убитый на середине записи, не должен оставлять
        # в кэше файл, который следующий прогон примет за целый.
        tmp = p.with_suffix(".part")
        tmp.write_bytes(data)
        tmp.replace(p)
    return p


def parse_pdf(path):
    # Берём ВЕСЬ текст статьи (без ограничения по числу страниц) — модели скармливаем полностью.
    try:
        r = PdfReader(str(path))
        t = ""
        imgs = []
        for pg in r.pages:
            pt = pg.extract_text()
            if pt:
                t += pt + "\n"
            try:
                for img in pg.images:
                    imgs.append(img.data)
            except Exception:
                pass
        return t, imgs
    except Exception:
        return "", []


# Заголовок списка литературы: строка вида "References"/"REFERENCES"/"Bibliography".
REF_HEADING = re.compile(
    r'\n[ \t]*(?:\d+[.\)]?[ \t]*)?(?:References?|REFERENCES|Bibliography|BIBLIOGRAPHY|References and Notes)[ \t]*\n')
ARXIV_ID_RE = re.compile(r'ar[Xx]iv:\s*(\d{4}\.\d{4,5})')


def split_references(text):
    """Отделяет список литературы (References/Bibliography) от тела статьи.
    Возвращает (body, references). Заголовок ищем в ПОСЛЕДНЕЙ части документа и режем по
    ПОСЛЕДНЕМУ совпадению — чтобы упоминание 'references' в тексте не обрезало тело раньше времени.
    Список литературы ест до ~20% токенов и для генерации статьи бесполезен."""
    cut = None
    for m in REF_HEADING.finditer(text):
        if m.start() > len(text) * 0.4:  # только во второй половине — там реальный список в конце статьи
            cut = m
    if cut:
        return text[:cut.start()].rstrip(), text[cut.end():].strip()
    return text, ""


def extract_ref_arxiv_ids(references):
    """arXiv id цитируемых работ из списка литературы — на будущее для привязки к релевантным статьям."""
    return list(dict.fromkeys(m.group(1) for m in ARXIV_ID_RE.finditer(references or "")))


def clean_article_text(text):
    """Тело статьи БЕЗ списка литературы и голых URL — то, что уходит в промт."""
    body, _ = split_references(text)
    return re.sub(r'https?://\S+', '', body)


def extract_captions(text, limit=12):
    """Достаёт подписи к рисункам из текста PDF ('Figure N: ...' / 'Fig. N. ...').
    Возвращает список подписей по возрастанию номера рисунка — для сопоставления с картинками по порядку."""
    caps = {}
    for m in re.finditer(r'(?:Figure|Fig)\.?\s*(\d{1,3})\s*[\.:]\s*([^\n]{10,300})', text):
        n = int(m.group(1))
        cap = re.sub(r'\s+', ' ', m.group(2)).strip()
        if n not in caps and len(cap) > 12:
            caps[n] = cap
    return [caps[n] for n in sorted(caps)][:limit]
