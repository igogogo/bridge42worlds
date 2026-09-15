# -*- coding: utf-8 -*-
"""Сбор работ о старении и омоложении с bioRxiv и medRxiv.

Владелец 12.09.2026: «меня интересует тот источник биотех архив по насыщению, по работам,
связанным с омоложением и прочей этой тематикой; как будем добирать». И следом: «бери 8».

ЗАЧЕМ ОТДЕЛЬНЫЙ СБОРЩИК, А НЕ РУЧНОЙ ПРИЁМ. Дверь для работ не из arXiv уже есть —
intake.py, и она остаётся единственной: сюда не переезжает ни присвоение номера, ни проверка
на повтор, ни пол по лицензии. Но intake ждёт готовую заготовку, которую собирает тот, кто
читал страницу глазами. Для десятков издателей это верно: у каждого своя вёрстка. У bioRxiv
вёрстку читать не нужно — у него есть машинный вход, и он отдаёт сразу всё: заголовок,
авторов, DOI, рубрику, лицензию и полную аннотацию. Поэтому заготовку здесь собирает код.

ЧТО ЗАМЕРЕНО (неделя 10–16.08.2026, 772 препринта):
  · всего у bioRxiv ~110 работ в сутки;
  · ядро темы старения — 54 за неделю, это ~8 в сутки, ~2800 в год;
  · рубрик у сервера ровно 25, список закрытый — таблица перевода ниже полная.

ДВЕ ЛОВУШКИ, ИЗ-ЗА КОТОРЫХ ВСЁ ЭТО МОГЛО МОЛЧА НЕ РАБОТАТЬ.

1. РУБРИКИ — НЕ КОСМЕТИКА. В vector_select.py нижние 20% по близости к нашему корпусу
   режутся ДО промпта, и обход этого среза (ACCENT) смотрит ровно на primary_category:

       return str(a.get("primary_category") or "").startswith(("q-bio.", "cs."))

   У bioRxiv кодов arXiv нет вообще — там «cell biology» словами. Работа без кода упор не
   получит, а био-работы про старение от нашего физического корпуса дальше всего. Без
   таблицы перевода весь этот поток вырезался бы молча, ещё до того как его увидит модель.
   Поэтому categories[0] здесь ВСЕГДА валидный код q-bio.* (их знает вся таксономия на пяти
   языках — проверено по data/arxiv-categories-*.json).

2. «aging» СИДИТ ВНУТРИ «imaging». Первый замер по подстрокам дал 17% темы старения и
   двадцать «понятий про старение» в реестре — и то и другое оказалось мусором: ловилось
   imaging, packaging, averaging, managing. По границам слов честные числа — 7% и ноль.
   Поэтому отбор ниже идёт только по \\b-границам, и это не придирка, а разница втрое.

СИЛЬНЫЕ И СЛАБЫЕ СЛОВА. Одного «reprogramming» или «age-related» мало: перепрограммирование
клеток бывает и вне геронтологии, «age-related» цепляет любую возрастную выборку. Поэтому
работа проходит, только если у неё есть хотя бы одно СИЛЬНОЕ слово; слабые лишь добавляют
веса при сортировке. На замере это ровно то, что отсекало ботанику и микроскопию.

    python tools/outside/biorxiv.py --days 7              показать, что нашлось
    python tools/outside/biorxiv.py --pool tools/outside/pools/ФАЙЛ.json --min-age 5         --limit 20 --apply --generate                    кусок из готового пула
    python tools/outside/biorxiv.py --days 1 --apply      завести дневную порцию
    python tools/outside/biorxiv.py --days 7 --limit 8 --apply
"""
import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

SEEN = HERE / "biorxiv-seen.json"
DRAFTS = HERE / "drafts"
# Кэш скачанных недель. В data/ ему не место: data/ публикуется целиком.
CACHE = HERE / "cache"
# Без своего User-Agent сервер отдаёт 403 на полный текст (API при этом отвечает и голому
# запросу — разные ворота). Представляемся честно и с обратным адресом.
UA = {"User-Agent": "bridge42worlds/1.0 (+https://bridge42worlds.com; bridge42worlds@gmail.com)"}
THIN_TEXT = 2000          # столько же, сколько сторожит intake.py
RETRY_MAX = 5             # столько раз ждём неготовый полный текст, потом сдаёмся

# ── тема ─────────────────────────────────────────────────────────────────────
# СИЛЬНЫЕ: вне геронтологии почти не встречаются. Хотя бы одно обязано быть.
STRONG = re.compile(r"""(?ix) \b(?:
      ag e? ing                      # aging / ageing — словом целиком, не внутри imaging
    | senescen \w*  | senolytic \w*
    | longevity     | life \s? span  | health \s? span
    | rejuvenat \w* | telomer \w*
    | geroprotect \w* | geroscience | gerontolog \w*
    | progeri \w*
    | biological \s+ age
    | epigenetic \s+ (?:clock|age)
)\b""")
# СЛАБЫЕ: рядом с темой, но сами по себе не про старение. Только вес при сортировке.
WEAK = re.compile(r"""(?ix) \b(?:
      (?:partial \s+)? reprogramming | yamanaka
    | age- (?:related|associated|dependent)
    | aged \s+ (?:mice|rats|animals|tissue\w*)
    | old (?:er)? \s+ (?:mice|rats|animals|adults)
    | caloric \s+ restriction | dietary \s+ restriction | rapamycin | metformin
    | mitochondrial \s+ (?:decline|dysfunction)
    | autophagy | proteostasis | stem \s+ cell \s+ exhaustion
    | regenerat \w*
)\b""")

# ── рубрики → коды q-bio.* ───────────────────────────────────────────────────
# Список рубрик у bioRxiv закрытый: на неделе 10–16.08 их было ровно 25, и это весь
# словарь сервера. medRxiv держит свой, клинический — он дописан ниже. Незнакомая рубрика
# уходит в q-bio.OT, а не теряется: пусть лучше работа попадёт в «прочее», чем исчезнет.
CAT_MAP = {
    # bioRxiv
    "neuroscience": "q-bio.NC",
    "animal behavior and cognition": "q-bio.NC",
    "cell biology": "q-bio.CB",
    "developmental biology": "q-bio.CB",
    "immunology": "q-bio.CB",
    "genomics": "q-bio.GN",
    "genetics": "q-bio.GN",
    "bioinformatics": "q-bio.QM",
    "biophysics": "q-bio.BM",
    "biochemistry": "q-bio.BM",
    "molecular biology": "q-bio.MN",
    "systems biology": "q-bio.MN",
    "synthetic biology": "q-bio.MN",
    "microbiology": "q-bio.PE",
    "ecology": "q-bio.PE",
    "evolutionary biology": "q-bio.PE",
    "zoology": "q-bio.PE",
    "paleontology": "q-bio.PE",
    "cancer biology": "q-bio.TO",
    "physiology": "q-bio.TO",
    "pathology": "q-bio.TO",
    "plant biology": "q-bio.OT",
    "bioengineering": "q-bio.OT",
    "pharmacology and toxicology": "q-bio.OT",
    "scientific communication and education": "q-bio.OT",
    # medRxiv — все 48 рубрик, снятые с живого месяца (01–13.09.2026, 839 работ).
    # Список неполным быть не должен: незнакомая рубрика уходит в «прочее», и работа
    # оказывается в разделе, где её никто не найдёт. На первом же прогоне так осело три
    # штуки — спортивная медицина, лучевая диагностика и медицина боли.
    # Клиническая медицина почти вся ложится в q-bio.TO (ткани и органы): это про орган и
    # его работу. Что про население — в PE, что про мозг и поведение — в NC, что про
    # метод и данные — в QM, а организационное и этическое — в OT.
    "geriatric medicine": "q-bio.TO",
    "neurology": "q-bio.NC",
    "psychiatry and clinical psychology": "q-bio.NC",
    "pain medicine": "q-bio.NC",
    "addiction medicine": "q-bio.NC",
    "anesthesia": "q-bio.NC",
    "epidemiology": "q-bio.PE",
    "public and global health": "q-bio.PE",
    "infectious diseases": "q-bio.PE",
    "hiv aids": "q-bio.PE",
    "occupational and environmental health": "q-bio.PE",
    "genetic and genomic medicine": "q-bio.GN",
    "health informatics": "q-bio.QM",
    "radiology and imaging": "q-bio.QM",
    "allergy and immunology": "q-bio.CB",
    "oncology": "q-bio.TO",
    "cardiovascular medicine": "q-bio.TO",
    "endocrinology": "q-bio.TO",
    "pediatrics": "q-bio.TO",
    "rehabilitation medicine and physical therapy": "q-bio.TO",
    "ophthalmology": "q-bio.TO",
    "intensive care and critical care medicine": "q-bio.TO",
    "obstetrics and gynecology": "q-bio.TO",
    "surgery": "q-bio.TO",
    "nutrition": "q-bio.TO",
    "dermatology": "q-bio.TO",
    "respiratory medicine": "q-bio.TO",
    "gastroenterology": "q-bio.TO",
    "otolaryngology": "q-bio.TO",
    "rheumatology": "q-bio.TO",
    "sexual and reproductive health": "q-bio.TO",
    "emergency medicine": "q-bio.TO",
    "urology": "q-bio.TO",
    "hematology": "q-bio.TO",
    "dentistry and oral medicine": "q-bio.TO",
    "orthopedics": "q-bio.TO",
    "transplantation": "q-bio.TO",
    "sports medicine": "q-bio.TO",
    "nephrology": "q-bio.TO",
    "pharmacology and therapeutics": "q-bio.OT",
    "health systems and quality improvement": "q-bio.OT",
    "primary care research": "q-bio.OT",
    "health policy": "q-bio.OT",
    "health economics": "q-bio.OT",
    "medical education": "q-bio.OT",
    "nursing": "q-bio.OT",
    "medical ethics": "q-bio.OT",
}
FALLBACK_CAT = "q-bio.OT"

# ── лицензии ─────────────────────────────────────────────────────────────────
# Сервер отдаёт короткий код, а класс у нас считает gen_arxiv.license_class() по АДРЕСУ.
# Переводим код в канонический адрес и дальше не решаем ничего сами: класс считает тот же
# код, что и для arXiv, а пол «только пересказ» ставит intake.
LICENCE_URL = {
    "cc_by": "https://creativecommons.org/licenses/by/4.0/",
    "cc_by_sa": "https://creativecommons.org/licenses/by-sa/4.0/",
    "cc_by_nc": "https://creativecommons.org/licenses/by-nc/4.0/",
    "cc_by_nd": "https://creativecommons.org/licenses/by-nd/4.0/",
    "cc_by_nc_nd": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
    "cc0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "cc0_ng": "https://creativecommons.org/publicdomain/zero/1.0/",
    # «Лицензии нет» — это НЕ пустое поле. У intake пустой адрес означает «забыли
    # заполнить», и работа отбивается; так 23% корпуса (каждая четвёртая) молча
    # отваливались бы каждый день. Ставим реальную страницу условий: на ней сервер
    # и пишет «все права защищены, повторное использование без разрешения запрещено».
    # license_class() читает её как «no», intake опускает на пол «только пересказ» —
    # ровно то поведение, ради которого пол и заводили. Подставляется по серверу:
    # у медархива своя такая страница, и врать про чужую нельзя.
    "cc_no": "https://www.{host}/about/FAQ#license",
}

# Работы двух серверов лежат на РАЗНЫХ доменах, а машинный вход у них общий и отвечает
# одинаково. Адрес работы собирается из DOI, и захардкоженный biorxiv.org увёл бы каждую
# медицинскую работу на чужой сайт — ссылка «первоисточник» вела бы в никуда. Поле server
# в записи и говорит, чей это препринт.
HOST = {"biorxiv": "biorxiv.org", "medrxiv": "medrxiv.org"}


def host_of(server):
    return HOST.get((server or "").strip().lower(), "biorxiv.org")


def log(m):
    print(m, flush=True)


# ── сеть ─────────────────────────────────────────────────────────────────────

def _get(url, tries=6, timeout=120):
    """Ответ сервера байтами. Сеть у препринт-серверов капризная — отступаем и повторяем.

    Шесть попыток, а не три, и отступ растёт: на длинном сборе (три месяца — это около
    шестисот запросов) сервер один раз обязательно ответит 504. Три попытки по три
    секунды такую заминку не пересиживают, и полтора часа работы уходят в никуда —
    ровно это и случилось 14.09.
    """
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
            if i < tries - 1:
                time.sleep(min(60, 5 * 2 ** i))
    raise last


def _fetch_window(server, frm, to):
    """Записи сервера за один промежуток. Страница — 30 записей, курсор по смещению."""
    out, seen, cur, total = [], set(), 0, None
    while True:
        url = f"https://api.biorxiv.org/details/{server}/{frm}/{to}/{cur}"
        d = json.loads(_get(url).decode("utf-8", "replace"))
        if total is None:
            total = int((d.get("messages") or [{}])[0].get("total", 0))
        rows = d.get("collection") or []
        if not rows:
            break
        for a in rows:
            if a.get("doi") not in seen:
                seen.add(a.get("doi"))
                out.append(a)
        cur += 30
        if cur >= total:
            break
    return out


def fetch_range(server, frm, to, step_days=7):
    """Все записи сервера за промежуток. Окно режется на недели, каждая ложится в кэш.

    ЗАЧЕМ КУСКАМИ И С КЭШЕМ. Три месяца с двух серверов — это восемнадцать тысяч записей и
    около шестисот запросов подряд. 14.09 такой сбор шёл полтора часа и умер на 504:
    сервер икнул, попытки кончились, и всё скачанное пропало, потому что держалось в
    памяти. Теперь неделя — единица работы: скачали, положили на диск, пошли дальше.
    Повторный запуск читает готовые недели с диска и продолжает с первой недостающей,
    так что обрыв стоит одну неделю, а не весь сбор.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    out, seen = [], set()
    a, b = date.fromisoformat(frm), date.fromisoformat(to)
    weeks, cur = [], a
    while cur <= b:
        end = min(cur + timedelta(days=step_days - 1), b)
        weeks.append((cur.isoformat(), end.isoformat()))
        cur = end + timedelta(days=1)
    log(f"  {server}: {frm}…{to} — {len(weeks)} кусков по {step_days} дн.")
    for i, (f1, f2) in enumerate(weeks, 1):
        cf = CACHE / f"{server}-{f1}-{f2}.json"
        if cf.exists():
            try:
                rows = json.loads(cf.read_text(encoding="utf-8"))
                log(f"    [{i}/{len(weeks)}] {f1}…{f2}: {len(rows)} из кэша")
            except (OSError, json.JSONDecodeError):
                rows = None
        else:
            rows = None
        if rows is None:
            rows = _fetch_window(server, f1, f2)
            cf.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
            log(f"    [{i}/{len(weeks)}] {f1}…{f2}: {len(rows)} скачано")
        for r in rows:
            if r.get("doi") not in seen:
                seen.add(r.get("doi"))
                out.append(r)
    log(f"  {server}: уникальных работ {len(out)}")
    return out


# ── отбор ────────────────────────────────────────────────────────────────────

def _blob(a):
    return (a.get("title") or "") + "\n" + (a.get("abstract") or "")


def score(a):
    """Насколько работа в теме. Ноль — не наша.

    Заголовок весит втрое: «Cellular senescence is associated with age-related loss of liver
    zonation» — это про старение, а та же пара слов, один раз мелькнувшая в обсуждении, ещё
    ничего не значит. Считаем РАЗНЫЕ слова, а не повторы: десять раз сказанное «aging» не
    делает работу более геронтологической, чем связка «senescence + telomere + lifespan».
    """
    title, abstract = a.get("title") or "", a.get("abstract") or ""
    strong_t = {m.group(0).lower() for m in STRONG.finditer(title)}
    strong_a = {m.group(0).lower() for m in STRONG.finditer(abstract)}
    if not (strong_t or strong_a):
        return 0                      # без сильного слова не берём вовсе
    weak_t = {m.group(0).lower() for m in WEAK.finditer(title)}
    weak_a = {m.group(0).lower() for m in WEAK.finditer(abstract)}
    return (3 * len(strong_t) + len(strong_a - strong_t)
            + 2 * len(weak_t) + 0.5 * len(weak_a - weak_t))


# ── полный текст ─────────────────────────────────────────────────────────────

_TAG = re.compile(r"<[^>]+>")
_DROP = re.compile(r"(?is)<(ref-list|back|fn-group|table-wrap|supplementary-material)\b.*?</\1>")


_EMAIL_TAG = re.compile(r"(?is)<email[^>]*>(.*?)</email>")
_MAILTO = re.compile(r"(?i)[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def jats_contacts(xml):
    """Адреса авторов для переписки из шапки JATS. Пустой список — законный ответ.

    ЗАЧЕМ. Письма авторам берут адрес из fulltext.txt — так устроен реестр контактов
    (tools/author_contacts.py), и для arXiv это работает: адрес напечатан на первой
    странице PDF, и он попадает в текст. У JATS шапка ОТДЕЛЬНО от тела: авторы, их
    институты и адреса лежат в <front>, а мы брали только <body>. Замер 15.09: адрес
    нашёлся в 1% наших био-работ против 74% у arXiv — то есть рассылка по биологии была
    бы невозможна, и причина была бы невидима.

    Машинный вход сервера адресов не отдаёт вовсе: там имя автора для переписки и его
    институт, но не почта. Единственный источник — эта шапка.
    """
    front = re.search(r"(?is)<front\b.*?</front>", xml)
    if not front:
        return []
    seen, out = set(), []
    for raw in _EMAIL_TAG.findall(front.group(0)):
        for m in _MAILTO.findall(re.sub(r"<[^>]+>", " ", raw)):
            a = m.strip().lower()
            if a not in seen:
                seen.add(a)
                out.append(a)
    return out


def jats_text(url):
    """Текст работы из JATS XML источника.

    У bioRxiv вход ЧИЩЕ, чем у arXiv: там PDF, который надо вытряхивать (и он бывает под
    сорок мегабайт), здесь размеченный XML с разделами. Выкидываем список литературы,
    служебные блоки и таблицы — в пересказ они не идут, а объём съедают.

    Шапку с адресами приписываем в начало: файл читает реестр контактов, и без неё
    рассылка по био-работам не с чем работать (см. jats_contacts).
    """
    x = _get(url).decode("utf-8", "replace")
    head = ""
    mails = jats_contacts(x)
    if mails:
        head = "Corresponding author(s): " + ", ".join(mails) + "\n\n"
    body = re.search(r"(?is)<body\b[^>]*>(.*)</body>", x)
    if not body:
        return ""
    t = _DROP.sub(" ", body.group(1))
    # Заголовки разделов помечаем переводом строки, иначе «Introduction Aging is…» слипается.
    t = re.sub(r"(?is)</title>", "</title>\n", t)
    t = re.sub(r"(?is)</(p|sec|abstract)>", "</\\1>\n", t)
    t = _TAG.sub(" ", t)
    t = t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n\n", t)
    return head + t.strip()


# ── заготовка для intake ─────────────────────────────────────────────────────

def _authors(s):
    """«Cherifi, K.; Matoori, S.» → [«K. Cherifi», «S. Matoori»].

    Реестр авторов строит ключ из фамилии и инициалов, и порядок ему важен: сервер пишет
    фамилию первой, а у нас везде принято имя первым — как приходит с arXiv.
    """
    out = []
    for part in (s or "").split(";"):
        part = part.strip().rstrip(".,")
        if not part:
            continue
        if "," in part:
            last, first = part.split(",", 1)
            last, first = last.strip(), first.strip()
            out.append(f"{first} {last}".strip() if first else last)
        else:
            out.append(part)
    return out


def draft(a):
    """Запись сервера → заготовка в том виде, какой ждёт intake.py."""
    doi = a.get("doi") or ""
    ver = str(a.get("version") or "1")
    cat = (a.get("category") or "").strip().lower()
    code = CAT_MAP.get(cat, FALLBACK_CAT)
    server = a.get("server") or "bioRxiv"
    host = host_of(server)
    return {
        "title": " ".join((a.get("title") or "").split()),
        "date": a.get("date") or "",
        "abstract": " ".join((a.get("abstract") or "").split()),
        "url": f"https://www.{host}/content/{doi}v{ver}",
        "doi": doi,
        "licence_url": LICENCE_URL.get(a.get("license") or "", "").format(host=host),
        "licence": a.get("license") or "",
        # Код q-bio первым — по нему конвейер узнаёт область (см. ловушку 1 в шапке).
        # Рубрику сервера храним рядом, словами: она понадобится, когда будем смотреть,
        # откуда что пришло, а в categories ей нельзя — там только валидные коды.
        "categories": [code],
        "source_category": cat,
        "authors": _authors(a.get("authors")),
        "org": server,
        "kind": "preprint",
        "jatsxml": a.get("jatsxml") or "",
        "corresponding": a.get("author_corresponding") or "",
        "institution": a.get("author_corresponding_institution") or "",
    }


# ── состояние ────────────────────────────────────────────────────────────────

def _id_for(doi):
    """Номер, который intake присвоил работе с этим DOI. None — если записи нет."""
    for p in (HERE / "works").glob("*.json"):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if rec.get("doi") and rec["doi"] == doi:
            return rec.get("id") or p.stem
    return None


def load_seen():
    try:
        return json.loads(SEEN.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_seen(d):
    SEEN.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


# ── главное ──────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Сбор работ о старении с bioRxiv/medRxiv")
    ap.add_argument("--days", type=int, default=1, help="окно в сутках назад от вчера")
    ap.add_argument("--from", dest="frm", help="начало окна YYYY-MM-DD")
    ap.add_argument("--to", help="конец окна YYYY-MM-DD")
    ap.add_argument("--limit", type=int, default=8, help="сколько взять (владелец: 8 в сутки)")
    ap.add_argument("--server", default="biorxiv", choices=("biorxiv", "medrxiv", "both"))
    ap.add_argument("--apply", action="store_true", help="завести работы; без ключа — показ")
    ap.add_argument("--generate", action="store_true",
                    help="после приёма сразу разобрать (для шага в дневном прогоне)")
    ap.add_argument("--dump", metavar="ФАЙЛ",
                    help="выгрузить ВСЕХ кандидатов в JSON и выйти (отбор идёт отдельно)")
    ap.add_argument("--pool", metavar="ФАЙЛ",
                    help="брать кандидатов из выгруженного пула, а не из сети")
    ap.add_argument("--min-age", type=int, default=0, metavar="ДНЕЙ",
                    help="не трогать работы моложе стольких дней (полный текст "
                         "у свежих ещё не выложен)")
    a = ap.parse_args()

    seen = load_seen()

    def fresh(doi):
        """ВИДЕЛИ — НЕ ЗНАЧИТ ВЗЯЛИ. Полный текст у свежего препринта появляется не сразу:
        обе работы от 13.09 на прогоне 14.09 пришли с пустым XML. Записывать такую в
        «обработано» нельзя — причина временная, а исключение вышло бы вечным, и работа не
        вернулась бы никогда. Пропускаем только взятые и тех, кто не дался много раз
        подряд: иначе битая работа каждый день тянула бы на себя лишний запрос."""
        was = seen.get(doi)
        return not (was and (was.get("taken") or int(was.get("tries") or 0) >= RETRY_MAX))

    # ИСТОЧНИК КАНДИДАТОВ: ПУЛ ИЛИ СЕТЬ. Три месяца с двух серверов — это 18 тысяч записей
    # и больше часа опроса: машинный вход отдаёт по 30 штук за раз. Платить этот час каждый
    # раз, когда берём очередной кусок, незачем — собрали однажды в файл, дальше читаем
    # оттуда мгновенно. Владелец 14.09: «у нас будет целый пул, будем частями обрабатывать».
    #
    # Дальше обе дороги одинаковы: кандидат — это пара (вес, заготовка). Заготовку из сети
    # собирает draft(), а в пуле она уже лежит готовой.
    if a.pool:
        pool = json.loads(Path(a.pool).read_text(encoding="utf-8"))
        cand = [(float(d.get("score") or 0), d) for d in pool if fresh(d.get("doi"))]
        log(f"ПУЛ {a.pool}: кандидатов {len(pool)}, "
            f"не тронутых {len(cand)}")
    else:
        to = a.to or (date.today() - timedelta(days=1)).isoformat()
        frm = a.frm or (date.fromisoformat(to) - timedelta(days=a.days - 1)).isoformat()
        servers = ("biorxiv", "medrxiv") if a.server == "both" else (a.server,)
        log(f"ОКНО {frm}…{to}, серверы: {', '.join(servers)}")
        rows = []
        for srv in servers:
            rows += fetch_range(srv, frm, to)
        log(f"  всего записей: {len(rows)}")
        cand = [(sc, draft(r)) for r in rows
                for sc in (score(r),) if sc and fresh(r.get("doi"))]
        log(f"  в теме старения: {len(cand)} (после вычета уже виденных)")
    # ПОРОГ ЗРЕЛОСТИ. Полный текст в JATS появляется НЕ вместе с препринтом, а спустя
    # несколько дней. Замер 14.09 на выборке в двадцать работ: пропущено десять, и все
    # десять по пустому тексту, с датами, сбитыми в хвост — 13.09 пять штук, 12.09 две,
    # 11.09 одна, 10.09 две. То есть чем свежее работа, тем вероятнее, что брать её рано.
    #
    # Дневному шагу порог не нужен и вреден: там свежесть и есть смысл, а отвалившиеся
    # возвращаются сами по счётчику попыток. А вот при разборе пула это чистая потеря —
    # берём двадцать, получаем десять. Поэтому ключ, а не жёсткое правило.
    if a.min_age > 0:
        edge = (date.today() - timedelta(days=a.min_age)).isoformat()
        was = len(cand)
        cand = [(sc, d) for sc, d in cand if (d.get("date") or "9999") <= edge]
        if was != len(cand):
            log(f"  порог зрелости {a.min_age} дн. (до {edge}): "
                f"отложено {was - len(cand)}, осталось {len(cand)}")
    cand.sort(key=lambda x: -x[0])

    from gen_arxiv import license_class

    # ВЫГРУЗКА ВСЕХ КАНДИДАТОВ. Порог по словам отвечает на вопрос «про старение ли это»,
    # но не на вопрос «стоит ли это читать». Когда из трёх месяцев набирается полтысячи
    # работ, а взять нужно полсотни, выбирать должен тот, кто видит все заголовки и
    # аннотации сразу. Печать в консоль для этого не годится — нужен файл.
    if a.dump:
        rows = []
        for sc, d in cand:
            d = dict(d)
            d["score"] = round(sc, 2)
            d["licence_class"] = license_class(d["licence_url"]) or "no"
            if d["licence_class"] == "no":
                d["licence_class"] = "analysis"
            d.pop("fulltext", None)
            rows.append(d)
        Path(a.dump).write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                                encoding="utf-8")
        log(f"\nвыгружено кандидатов: {len(rows)} → {a.dump}")
        return 0

    take = cand[:a.limit]
    log(f"\nБЕРЁМ {len(take)} из {len(cand)}:\n")
    for i, (sc, d) in enumerate(take, 1):
        cls = license_class(d["licence_url"]) or "no"
        cls = "analysis" if cls == "no" else cls
        log(f"{i:2}. [{sc:4.1f}] {d['categories'][0]:9} {cls:8} {d['title'][:88]}")
        log(f"      {d['org']} · {d.get('source_category')} · {d['date']} · "
            f"авторов {len(d['authors'])}")
    if len(cand) > len(take):
        log(f"\nне взято в этот раз: {len(cand) - len(take)} (остаются в очереди)")
        for sc, d in cand[len(take):len(take) + 5]:
            log(f"      [{sc:4.1f}] {(d.get('title') or '')[:86]}")

    if not a.apply:
        log("\nэто показ. Завести: добавь --apply")
        return 0

    DRAFTS.mkdir(parents=True, exist_ok=True)
    done, failed = [], []
    for sc, d in take:
        d = dict(d)
        log(f"\n▶ {d['title'][:80]}")
        try:
            txt = jats_text(d["jatsxml"]) if d["jatsxml"] else ""
        except Exception as e:
            txt = ""
            log(f"   ⚠️  полный текст не дался ({type(e).__name__}): {str(e)[:100]}")
        if len(txt) < THIN_TEXT:
            # Без полного текста разбирать нечего: одна аннотация даст пустой пересказ, а
            # за PDF на arXiv генератор сходит впустую — этой работы там нет.
            log(f"   ⛔ текста {len(txt)} знаков — пропускаю, заведём когда XML появится")
            failed.append((d, f"текст {len(txt)}"))
            continue
        d["fulltext"] = txt
        log(f"   текст {len(txt)} знаков из JATS")
        p = DRAFTS / f"{(d['doi'] or 'x').replace('/', '_')}.json"
        p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        rc = subprocess.run([sys.executable, "-X", "utf8", "tools/outside/intake.py",
                             str(p), "--apply"], cwd=str(ROOT)).returncode
        if rc != 0:
            failed.append((d, f"intake код {rc}"))
            continue
        seen[d["doi"]] = {"date": d["date"], "title": d["title"][:120], "taken": True}
        done.append(d)

    for d, why in failed:
        was = seen.get(d["doi"]) or {}
        seen[d["doi"]] = {"date": d["date"], "title": d["title"][:120],
                          "taken": False, "why": why,
                          "tries": int(was.get("tries") or 0) + 1}
    save_seen(seen)

    log(f"\n✅ заведено {len(done)}, пропущено {len(failed)}")
    ids = [i for i in (_id_for(d["doi"]) for d in done) if i]
    if not ids:
        return 0
    if not a.generate:
        log(f"дальше: python run.py ids {' '.join(ids)}")
        return 0

    # Разбор — тем же конвейером, что и arXiv. Замок дерева здесь НЕ берём: в дневном
    # прогоне он уже взят full_run и передан нам через окружение, а руками сборщик
    # зовут при свободном дереве. Постинга нет никогда: наружу работы уходят общим
    # шагом в конце цепочки, и решать это за владельца сборщику не положено.
    log(f"\n▶ разбор: {' '.join(ids)}")
    rc = subprocess.run([sys.executable, "-X", "utf8", "-u", "run.py", "ids"] + ids
                        + ["--no-post"], cwd=str(ROOT)).returncode
    log(f"разбор закончился, код {rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
