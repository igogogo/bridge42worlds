# -*- coding: utf-8 -*-
"""Локальный сервер с ручками облака — чтобы динамику можно было проверять на месте.

ЗАЧЕМ. Правило владельца: сначала локально, потом прод. Для вёрстки этого хватало —
`python -m http.server 8420` отдаёт файлы, и css видно сразу. Но с переездом списков
в облако половина сайта перестала быть проверяемой локально: страницы сущностей,
автора, похожие работы, а теперь и лента ходят в /api/…, которых у файлового сервера
нет. Модули честно откатываются на вшитый список — и локально ты видишь СТАРОЕ
поведение, думая, что смотришь новое. Это худший вид проверки: она успокаивает.

Здесь те же ручки, что в cloudflare/worker.js, но считают по локальному индексу.
Ответы совпадают по форме поле в поле — иначе смысла нет: заглушка, которая врёт
в мелочи, отправит искать несуществующую ошибку в клиенте.

ЧЕГО ЗДЕСЬ НЕТ. Это не второй воркер и не источник правды. Нет поиска вектором,
почты, совета, квот, авторских заявок — всё, что требует D1, Vectorize или ключей.
Здесь ровно то, что нужно, чтобы увидеть ленту и списки живыми.

ЗАПУСК:  python tools/dev_server.py         (порт 8420, как привыкли)
"""
import argparse
import json
import random
import re
import threading
from collections import Counter, defaultdict
from functools import lru_cache
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
LANGS = ("ru", "en", "es", "ar", "fr")
VERSIONS = {"popular": "articles-index.json",
            "simple": "articles-index-simple.json",
            "advanced": "articles-index-advanced.json"}
FEED_MAX = 60

# Поля карточки — ровно те, что отдаёт воркер (FEED_COLS + feedRow).
CARD_FIELDS = ("id", "date", "url", "title", "oneliner", "description", "authors",
               "tags", "laws", "scientists", "categories", "primary_category",
               "reading", "express", "km", "image")

_lock = threading.Lock()


@lru_cache(maxsize=32)
def index_of(lang, version):
    p = ROOT / "lang" / lang / VERSIONS[version]
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def card(a):
    return {k: a.get(k) for k in CARD_FIELDS}


def feed_params(q):
    g = lambda k, d="": (q.get(k) or [d])[0]
    lang = g("lang") if g("lang") in LANGS else "ru"
    version = g("version") if g("version") in VERSIONS else "popular"
    try:
        limit = max(1, min(int(g("limit", "20")), FEED_MAX))
    except ValueError:
        limit = 20
    try:
        page = max(0, int(g("page", "0")))
    except ValueError:
        page = 0
    return lang, version, limit, page


def handle_feed(q):
    lang, version, limit, page = feed_params(q)
    g = lambda k, d="": (q.get(k) or [d])[0]
    items = list(index_of(lang, version))

    cat = g("cat")[:40]
    if cat:
        # точный раздел (astro-ph.HE) или группа (astro-ph) — как в воркере
        items = [a for a in items
                 if (a.get("primary_category") == cat if "." in cat
                     else str(a.get("primary_category") or "").startswith(cat))]
    # Дата — префикс: год, год-месяц или полная дата (три уровня календаря).
    day = g("date")[:10]
    if re.fullmatch(r"\d{4}(-\d{2}(-\d{2})?)?", day):
        items = [a for a in items if str(a.get("date") or "").startswith(day)]
    ex = g("express")
    if ex in ("0", "1"):
        want = ex == "1"
        items = [a for a in items if bool(a.get("express")) == want]

    sort = g("sort", "mix")
    if sort == "new":
        items.sort(key=lambda a: (a.get("date") or "", a.get("id") or ""), reverse=True)
    elif sort == "old":
        items.sort(key=lambda a: (a.get("date") or "", a.get("id") or ""))
    else:
        # «вперемешку»: у воркера перемешивает столбец mix с суточным зерном, здесь —
        # тот же смысл, устойчивый в пределах дня, чтобы «показать ещё» не дублировало.
        seed = int((ROOT / "data" / "build-info.json").stat().st_mtime) // 86400
        random.Random(seed).shuffle(items)

    total = len(items)
    chunk = items[page * limit:page * limit + limit]
    out = {"items": [card(a) for a in chunk], "page": page, "limit": limit,
           "more": len(chunk) == limit}
    if page == 0:
        out["total"] = total
    return out


def handle_corpus(q):
    lang, version, _, _ = feed_params(q)
    items = index_of(lang, version)
    days, cats = defaultdict(lambda: [0, 0, 0]), Counter()
    total = express = km = 0
    for a in items:
        d = days[a.get("date") or ""]
        d[0] += 1
        total += 1
        if a.get("express"):
            d[1] += 1
            express += 1
        if a.get("km"):
            d[2] += 1
            km += 1
        for c in (a.get("categories") or []):
            cats[c] += 1
    return {"days": dict(days), "cats": dict(cats), "total": total,
            "express": express, "km": km, "full": total - express}


def handle_find(q):
    """Поиск словами — грубее воркерова FTS5, но той же формы ответа."""
    lang, version, limit, page = feed_params(q)
    words = [w for w in re.split(r"\s+", ((q.get("q") or [""])[0]).lower()) if len(w) > 1][:6]
    items = index_of(lang, version)
    if not words:
        return {"items": [], "page": page, "limit": limit, "more": False, "total": 0}
    hits = []
    for a in items:
        hay = " ".join(str(a.get(k) or "") for k in ("title", "oneliner", "description")).lower()
        n = sum(1 for w in words if w in hay)
        if n:
            hits.append((n, a))
    hits.sort(key=lambda t: (-t[0], t[1].get("date") or ""), reverse=False)
    chunk = hits[page * limit:page * limit + limit]
    return {"items": [card(a) for _, a in chunk], "page": page, "limit": limit,
            "more": len(chunk) == limit, "total": len(hits)}


@lru_cache(maxsize=1)
def related_map():
    p = ROOT / "data" / "related-vec.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def handle_side(q):
    """Обвязка статьи: похожие и «мы писали» одним ответом — как в воркере.

    У воркера источник — таблица article_side, здесь — data/related-vec.json, из
    которого она и залита. Форма ответа та же: готовые карточки, а не идентификаторы.
    """
    lang, version, _, _ = feed_params(q)
    raw_id = ((q.get("id") or [""])[0])[:24]
    # Идентификаторы живут в ДВУХ видах: старые без суффикса версии (0905.0049),
    # новые с ним (2608.20327v1). Воркер спрашивает базу про оба; здесь то же самое,
    # иначе половина архива молча остаётся без похожих.
    bare = raw_id.split("v")[0]
    m = related_map()
    rel = m.get(raw_id) or m.get(bare) or m.get(bare + "v1") or []
    ids = []
    for r in rel[:12]:
        # элементы бывают словарями {id, score} и голыми строками — та же ловушка,
        # на которой однажды в базу легли обрывки «{'id': '17…»
        ids.append(r.get("id") if isinstance(r, dict) else r)
    want = set(ids) | {i.split("v")[0] for i in ids}
    by = {}
    for a in index_of(lang, version):
        i = a.get("id")
        if i in want or i.split("v")[0] in want:
            by[i] = a
            by[i.split("v")[0]] = a
    seen, out = set(), []
    for i in ids:
        a = by.get(i) or by.get(i.split("v")[0])
        if a and a["id"] not in seen:
            seen.add(a["id"])
            out.append(card(a))
    return {"related": out, "cited": [], "frames": 0}


ROUTES = {"/api/feed": handle_feed, "/api/corpus": handle_corpus,
          "/api/find": handle_find, "/api/side": handle_side}


class Server(ThreadingHTTPServer):
    # Windows по умолчанию позволяет ВТОРОМУ процессу сесть на занятый порт, и тогда
    # запросы разбираются между ними как повезёт. Обошлось это дорого: дважды я мерила
    # страницу, которую отдавал старый процесс, и дважды искала ошибку не там.
    # Пусть второй запуск падает громко.
    allow_reuse_address = False


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        """Локально ничего не кэшируем.

        28.08: правка меню в js/search.js была на месте, а браузер полчаса
        показывал старое — и выглядело это как «правка не сделана». На проде
        свежесть держат заголовки воркера (пять минут), но при разработке даже
        пять минут превращают проверку в гадание.
        """
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, fmt, *args):
        # Тихо: в консоли важны только ошибки ручек, а не поток запросов за картинками.
        if "/api/" in (self.path or ""):
            super().log_message(fmt, *args)

    def do_GET(self):
        u = urlparse(self.path)
        fn = ROUTES.get(u.path)
        if not fn:
            return super().do_GET()
        try:
            with _lock:
                body = json.dumps(fn(parse_qs(u.query)), ensure_ascii=False).encode("utf-8")
        except Exception as e:
            body = json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8")
            self.send_response(500)
        else:
            self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        # Кэш НЕ ставим: локально важно видеть правку сразу, а не через пять минут.
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main():
    ap = argparse.ArgumentParser(description="Локальный сайт с ручками облака")
    ap.add_argument("--port", type=int, default=8420)
    args = ap.parse_args()
    try:
        srv = Server(("", args.port), Handler)
    except OSError as e:
        print(f"порт {args.port} занят — сначала останови прежний сервер ({e})")
        raise SystemExit(1)
    print(f"сайт с ручками: http://localhost:{args.port}")
    print("  /api/feed  /api/corpus  /api/find   (остальное — файлы)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nостановлен")


if __name__ == "__main__":
    main()
