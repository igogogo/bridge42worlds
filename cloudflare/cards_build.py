"""Наполнение серверного поиска: индексы статей → таблица карточек в D1 + FTS5.

Зачем. Сегодня поиск живёт в браузере: на каждой странице со списком читатель скачивает
lang/<язык>/articles-index*.json — 7,1 МБ по-русски, 89 МБ на все языки и уровни. Больше
всего весит abstract (30%), который на карточке НЕ показывается вообще: он лежит там
единственно ради поиска подстроки. Это и есть работа, которой место на сервере.

Что делает скрипт. Читает те же файлы индексов, из которых сейчас кормится клиент,
и заливает их в D1: карточки — в `cards`, текст для поиска — в `cards_fts`. Дальше
Worker ищет по D1 и Vectorize и отдаёт готовые карточки, а из клиентского индекса
тяжёлое можно убрать (это фаза 2, отдельно).

Дельта по хэшу: если файл индекса не менялся, язык пропускается целиком. Полная заливка
всех пяти языков и трёх уровней — порядка 32 тысяч строк.

    python cloudflare/cards_build.py --schema      # создать таблицы (один раз)
    python cloudflare/cards_build.py               # залить изменившееся
    python cloudflare/cards_build.py --force       # перезалить всё
    python cloudflare/cards_build.py --check       # что лежит в базе сейчас
"""
import os, sys, json, time, hashlib, argparse, unicodedata, re
from pathlib import Path
import requests
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(os.environ.get("B42_DATA_ROOT") or Path(__file__).resolve().parent.parent)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

LANGS = ("ru", "en", "es", "ar", "fr")
# Файлы индексов. Уровень НЕ угадываем по имени файла, а берём из самих записей (поле
# version): базовый файл без суффикса оказался «popular», а не «mini», как читалось по
# названию — залил бы под чужим именем, и клиент не нашёл бы свой уровень. Значение ниже —
# только запасное, если поля вдруг нет.
INDEX_FILES = {"articles-index.json": "popular",
               "articles-index-simple.json": "simple",
               "articles-index-advanced.json": "advanced"}
DB_NAME = "b42-queue"
# Два предела D1, оба замерены вживую, а не взяты из документации:
#   • подстановок (?) на запрос — чуть больше ста: 100 проходит, 200 нет. При 17 колонках
#     это пять строк за раз, то есть 6,5 тысяч обращений на полную заливку — часы. Поэтому
#     значения вшиваем литералами с экранированием кавычек (данные свои, из наших индексов);
#   • длина SQL — между 50 и 100 КБ: 50 проходит, 100 нет.
# Отсюда пачки считаем не по числу строк, а по длине готового SQL с запасом.
SQL_BUDGET = 40 * 1024


# ─────────────────────────── нормализация текста ───────────────────────────
# ВНИМАНИЕ: точно такая же функция живёт в worker.js (normText). Если поменять одну
# и забыть вторую, поиск перестанет находить — молча, без единой ошибки в журнале.
_HARAKAT = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_ALEF = re.compile(r"[آأإٱ]")
# Артикль срезаем, только если после него остаётся не меньше ТРЁХ букв. Замерено на живой
# базе: с порогом в две буквы «الكم» (квант) превращается в «كم» — обиходное «сколько», и
# запрос про кванты начинает притягивать всё подряд. Три буквы сохраняют главный выигрыш
# («الفيزياء» → «فيزياء») и не режут короткие корни.
_WORD_AL = re.compile(r"(?<![؀-ۿ])ال(?=[؀-ۿ]{3,})")
_HAS_AL = re.compile(r"^ال[؀-ۿ]{2,}$")


def norm_text(s):
    """Единая нормализация для тела поиска и для запроса.

    Латиница и кириллица: регистр и составные символы. Арабский: огласовки, татвиль,
    варианты алифа/йа/та-марбуты и ведущий артикль «ال». Последнее — главное: без него
    «الفيزياء» и «فيزياء» для FTS5 разные слова, и половина запросов не находит ничего."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", str(s)).lower()
    s = _HARAKAT.sub("", s)
    s = _ALEF.sub("ا", s)
    s = s.replace("ى", "ي").replace("ة", "ه")
    s = _WORD_AL.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


# ─────────────────────────────── D1 по API ─────────────────────────────────
class D1:
    def __init__(self):
        self.acc = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or os.environ.get("R2_ACCOUNT_ID")
        tok = os.environ.get("CLOUDFLARE_API_TOKEN")
        if not (self.acc and tok):
            raise SystemExit("нет CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN")
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {tok}"
        self.uuid = self._find_db()

    def _find_db(self):
        r = self.s.get(f"https://api.cloudflare.com/client/v4/accounts/{self.acc}/d1/database",
                       timeout=60).json()
        for d in r.get("result", []):
            if d["name"] == DB_NAME:
                return d["uuid"]
        raise SystemExit(f"база {DB_NAME} не найдена")

    def sql(self, sql, params=None, tries=4):
        url = (f"https://api.cloudflare.com/client/v4/accounts/{self.acc}"
               f"/d1/database/{self.uuid}/query")
        body = {"sql": sql}
        if params:
            body["params"] = params
        for attempt in range(tries):
            r = self.s.post(url, json=body, timeout=180)
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(min(2 ** attempt, 20))
                continue
            j = r.json()
            if not j.get("success"):
                raise RuntimeError(json.dumps(j.get("errors"), ensure_ascii=False)[:300])
            return j["result"][0].get("results", [])
        raise RuntimeError("D1 не ответила после повторов")


# ───────────────────────────────── данные ──────────────────────────────────
def read_index(lang, fname):
    p = ROOT / "lang" / lang / fname
    if not p.exists():
        return None, None
    raw = p.read_bytes()
    d = json.loads(raw.decode("utf-8"))
    arr = d if isinstance(d, list) else (d.get("articles") or list(d.values())[0])
    return arr, hashlib.md5(raw).hexdigest()


def as_json(v):
    return json.dumps(v or [], ensure_ascii=False)


def row_of(a, lang, version):
    return (
        a.get("id", ""), lang, version,
        a.get("title", ""), a.get("oneliner", ""), a.get("description", ""),
        as_json(a.get("authors")), as_json(a.get("tags")), as_json(a.get("laws")),
        as_json(a.get("scientists")), as_json(a.get("categories")),
        a.get("primary_category", ""), a.get("date", ""), a.get("url", ""),
        a.get("image", ""), int(a.get("reading") or 0), 1 if a.get("express") else 0,
    )


def body_of(a):
    """Тело поиска: всё, по чему сегодня ищет клиент, включая невидимое на карточке.

    Плюс отдельный хвост из арабских слов В ИСХОДНОМ виде — с артиклем. Нормализация
    режет артикль, и без этого хвоста слово, у которого корень короче трёх букв, стало бы
    ненаходимым в своей же словарной форме. Хвост дешёвый: только слова на «ال», без
    повторов."""
    parts = [a.get("title"), a.get("oneliner"), a.get("description"),
             a.get("abstract"), a.get("threads")]
    parts += [" ".join(a.get("authors") or []), " ".join(a.get("tags") or [])]
    raw = " ".join(p for p in parts if p)
    body = norm_text(raw)
    keep = {w for w in norm_text_keep_al(raw).split() if _HAS_AL.match(w)}
    return body + (" " + " ".join(sorted(keep)) if keep else "")


def norm_text_keep_al(s):
    """Та же нормализация, но без срезания артикля."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", str(s)).lower()
    s = _HARAKAT.sub("", s)
    s = _ALEF.sub("ا", s)
    s = s.replace("ى", "ي").replace("ة", "ه")
    return re.sub(r"\s+", " ", s).strip()


def lit(v):
    """Значение как литерал SQLite. Управляющие символы выкидываем: в тексте статьи им
    делать нечего, а нулевой байт рвёт запрос целиком."""
    if isinstance(v, int):
        return str(v)
    s = "" if v is None else str(v)
    s = "".join(c for c in s if c >= " " or c == "\n")
    return "'" + s.replace("'", "''") + "'"


def send_in_batches(db, head, rows):
    """Шлёт INSERT пачками, укладываясь в предел длины SQL. Одна строка длиннее бюджета
    поедет одна — и если она не влезет даже так, D1 честно скажет об этом, а не молча
    потеряет статью."""
    buf, size = [], 0
    for r in rows:
        if buf and size + len(r) > SQL_BUDGET:
            db.sql(head + ",".join(buf))
            buf, size = [], 0
        buf.append(r)
        size += len(r) + 1
    if buf:
        db.sql(head + ",".join(buf))


def fill(db, lang, version, arr):
    db.sql("DELETE FROM cards WHERE lang=? AND version=?", [lang, version])
    db.sql("DELETE FROM cards_fts WHERE lang=? AND version=?", [lang, version])
    send_in_batches(
        db,
        "INSERT INTO cards (id,lang,version,title,oneliner,description,authors,tags,"
        "laws,scientists,categories,primary_category,date,url,image,reading,express) VALUES ",
        ["(" + ",".join(lit(v) for v in row_of(a, lang, version)) + ")" for a in arr])
    send_in_batches(
        db, "INSERT INTO cards_fts (body,id,lang,version) VALUES ",
        ["(" + ",".join(lit(v) for v in (body_of(a), a.get("id", ""), lang, version)) + ")"
         for a in arr])
    return len(arr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", action="store_true", help="создать таблицы")
    ap.add_argument("--force", action="store_true", help="перезалить всё, игнорируя хэши")
    ap.add_argument("--check", action="store_true", help="что лежит в базе сейчас")
    ap.add_argument("--only", help="только этот язык")
    a = ap.parse_args()
    db = D1()

    if a.schema:
        sql = (Path(__file__).resolve().parent / "schema-cards.sql").read_text(encoding="utf-8")
        # D1 принимает по одному выражению за раз. Комментарии режем ДО разбиения по «;»,
        # а не после: точка с запятой внутри русского комментария иначе рвёт файл посреди
        # фразы, и в базу уезжает кусок пояснения вместо SQL (поймано первым же прогоном).
        clean = "\n".join(l for l in sql.splitlines() if not l.strip().startswith("--"))
        for stmt in [s.strip() for s in clean.split(";") if s.strip()]:
            db.sql(stmt)
        print("✅ таблицы созданы")
        return 0

    if a.check:
        rows = db.sql("SELECT lang, version, COUNT(*) n FROM cards GROUP BY lang, version "
                      "ORDER BY lang, version")
        for r in rows:
            print(f"  {r['lang']}/{r['version']:9} {r['n']:6} карточек")
        st = db.sql("SELECT COUNT(*) n FROM cards_fts")
        print(f"  тело поиска: {st[0]['n']} записей")
        return 0

    state = {r["key"]: r["hash"] for r in db.sql("SELECT key, hash FROM cards_state")}
    total = 0
    for lang in LANGS:
        if a.only and lang != a.only:
            continue
        for fname, fallback in INDEX_FILES.items():
            arr, h = read_index(lang, fname)
            if arr is None:
                print(f"  {lang}/{fallback}: файла нет — пропуск")
                continue
            version = (arr[0].get("version") if arr else None) or fallback
            key = f"{lang}/{version}"
            if not a.force and state.get(key) == h:
                print(f"  {lang}/{version}: не менялся")
                continue
            t = time.time()
            n = fill(db, lang, version, arr)
            db.sql("INSERT INTO cards_state (key,hash,rows,updated) VALUES (?,?,?,datetime('now')) "
                   "ON CONFLICT(key) DO UPDATE SET hash=excluded.hash, rows=excluded.rows, "
                   "updated=excluded.updated", [key, h, n])
            print(f"  {lang}/{version}: залито {n} за {time.time() - t:.0f} с")
            total += n
    print(f"✅ карточки в D1: обновлено {total} строк" if total else "✅ всё уже свежее")
    return 0


if __name__ == "__main__":
    sys.exit(main())
