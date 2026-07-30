"""Исполнитель очереди заказов: берёт заказы из D1 и выполняет их на машине с данными.

Почему исполняет машина, а не Worker. Worker — это JavaScript в песочнице без файловой
системы. Наш конвейер на Python, и главное — ему нужно состояние: какие статьи уже есть,
реестры тегов, законов и учёных, шаблоны. Это тысячи файлов на диске. Worker принимает
заказ и показывает статус, работу делает тот, у кого есть данные.

Три типа заказов (схема — schema-queue.sql):
  ask       — вопрос боту-исследователю
  article   — «хочу статью про это»
  translate — «переведи эту статью на мой язык»

Как берётся заказ. Атомарно: одним UPDATE переводим строку из queued в running и только
если она всё ещё queued. Если исполнителей запустят двое, второй просто не получит строку —
без блокировок и без риска сделать работу дважды за наши деньги.

Запуск:
    python cloudflare/queue_worker.py            # один проход по очереди
    python cloudflare/queue_worker.py --loop     # крутиться, проверяя раз в 30 секунд
    python cloudflare/queue_worker.py --dry      # показать, что взял бы, но не исполнять
"""
import os, sys, json, time, argparse, subprocess
from pathlib import Path
import requests
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DB_ID = os.environ.get("D1_QUEUE_ID", "44ca0737-e27f-4cb5-bac8-9b132c935e4d")
MAX_ATTEMPTS = 3          # дальше заказ признаём безнадёжным, а не крутим вечно
POLL_SECONDS = 30


def sql(query, params=None):
    """Запрос к D1 по HTTP. Отдельный слой, чтобы не тащить wrangler в каждый вызов."""
    acc = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    tok = os.environ.get("CLOUDFLARE_API_TOKEN")
    r = requests.post(
        f"https://api.cloudflare.com/client/v4/accounts/{acc}/d1/database/{DB_ID}/query",
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
        json={"sql": query, "params": params or []}, timeout=60)
    d = r.json()
    if not d.get("success"):
        raise RuntimeError(f"D1: {d.get('errors')}")
    return d["result"][0].get("results", [])


def claim_next():
    """Взять следующий заказ. Порядок тот же, что в индексе: приоритет, затем время."""
    rows = sql("""SELECT id, kind, payload, lang, attempts FROM orders
                  WHERE status = 'queued' AND attempts < ?
                  ORDER BY priority, created_at LIMIT 1""", [MAX_ATTEMPTS])
    if not rows:
        return None
    o = rows[0]
    # Условие status='queued' в UPDATE — и есть защита от двух исполнителей: второму
    # просто не достанется строка, никаких блокировок.
    changed = sql("""UPDATE orders SET status='running', started_at=?, attempts=attempts+1
                     WHERE id=? AND status='queued' RETURNING id""", [int(time.time() * 1000), o["id"]])
    return o if changed else None


def finish(order_id, result=None, error=None):
    sql("""UPDATE orders SET status=?, result=?, error=?, finished_at=? WHERE id=?""",
        ["done" if error is None else "failed",
         json.dumps(result, ensure_ascii=False) if result else None,
         error, int(time.time() * 1000), order_id])


def requeue(order_id, why):
    """Вернуть в очередь: временная беда (сеть, занятая модель) — не повод терять заказ.
    Счётчик попыток уже увеличен при взятии, поэтому вечного круга не будет."""
    sql("UPDATE orders SET status='queued', error=? WHERE id=?", [why, order_id])


# ── Исполнение по типам ───────────────────────────────────────────
# Каждый обработчик возвращает словарь-результат либо кидает исключение.

def do_translate(payload, lang):
    arxiv_id, to = payload.get("arxiv_id"), payload.get("to")
    if not (arxiv_id and to):
        raise ValueError("в заказе нет arxiv_id или языка")
    # Точечный перевод одной статьи существующим механизмом проекта.
    code = subprocess.run(
        [sys.executable, "run.py", "translate-one", "--id", arxiv_id, "--lang", to],
        cwd=ROOT, env={**os.environ, "PYTHONIOENCODING": "utf-8"}).returncode
    if code != 0:
        raise RuntimeError(f"перевод завершился с кодом {code}")
    return {"url": f"/lang/{to}/archive/{arxiv_id}/", "arxiv_id": arxiv_id, "lang": to}


def find_arxiv_paper(topic):
    """Тема читателя → конкретная статья arXiv. Мы не пишем статьи из головы: каждая наша
    статья — пересказ конкретной работы, иначе нечего показать как источник.

    Берём свежайшую по релевантности: читатель просит тему, а не «что-нибудь древнее».
    Домен arXiv намеренно es.arxiv.org — export не отвечал (см. грабли проекта)."""
    import xml.etree.ElementTree as ET
    q = f'all:"{topic}"' if " " in topic else f"all:{topic}"
    r = requests.get("http://es.arxiv.org/api/query", timeout=40, params={
        "search_query": q, "start": 0, "max_results": 5,
        "sortBy": "relevance", "sortOrder": "descending"})
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        return None
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for e in root.findall("atom:entry", ns):
        idnode = e.find("atom:id", ns)
        if idnode is None:
            continue
        return {
            "id": idnode.text.split("/abs/")[-1].split("v")[0],
            "title": (e.find("atom:title", ns).text or "").strip().replace("\n", " "),
        }
    return None


def do_article(payload, lang):
    """«Хочу статью про это». Путь написан целиком и проверяем, но по умолчанию ВЫКЛЮЧЕН:
    каждый прогон стоит денег, а потолок на это не назначен — решение архитектора (вопросы
    в отчёте от 2026-07-30). Включается одной переменной, правка кода не нужна:
        ORDERS_ARTICLE_ENABLED=1 python cloudflare/queue_worker.py
    Заказы тем временем принимаются и копятся в очереди — ничего не теряется."""
    if os.environ.get("ORDERS_ARTICLE_ENABLED", "0") != "1":
        raise NotImplementedError(
            "генерация по заказу выключена: ждём решения по потолку расхода")

    arxiv_id = payload.get("hint_arxiv_id")
    title = None
    if not arxiv_id:
        topic = str(payload.get("topic") or "").strip()
        if not topic:
            raise ValueError("в заказе нет ни темы, ни arxiv_id")
        found = find_arxiv_paper(topic)
        if not found:
            # Честный отказ лучше выдуманной статьи: читателю покажем, что не нашли работу.
            raise ValueError(f"на arXiv не нашлось работы по теме «{topic}»")
        arxiv_id, title = found["id"], found["title"]

    code = subprocess.run(
        [sys.executable, "run.py", "ids", arxiv_id],
        cwd=ROOT, env={**os.environ, "PYTHONIOENCODING": "utf-8"}).returncode
    if code != 0:
        raise RuntimeError(f"генерация завершилась с кодом {code}")
    return {"arxiv_id": arxiv_id, "title": title, "url": f"/lang/{lang}/archive/"}


def do_ask(payload, lang):
    # Вопрос боту исполняет Worker: у него уже есть вектор и модель, и читатель ждёт ответа
    # сейчас, а не через тридцать секунд. Сюда заказ попадает, только если Worker не смог.
    raise NotImplementedError("вопросы боту исполняет Worker, а не очередь")


HANDLERS = {"translate": do_translate, "article": do_article, "ask": do_ask}


def run_once(dry=False):
    o = claim_next()
    if not o:
        return False
    payload = json.loads(o["payload"] or "{}")
    print(f"заказ {o['id'][:8]} · {o['kind']} · попытка {o['attempts'] + 1}")
    if dry:
        print("   (пробный проход — не исполняю)")
        requeue(o["id"], None)
        return True
    try:
        result = HANDLERS[o["kind"]](payload, o.get("lang") or "ru")
        finish(o["id"], result=result)
        print("   готово")
    except NotImplementedError as e:
        # Не ошибка исполнения, а осознанно невключённая ветка — не крутим повторно.
        finish(o["id"], error=str(e))
        print(f"   отложено: {e}")
    except Exception as e:
        if o["attempts"] + 1 >= MAX_ATTEMPTS:
            finish(o["id"], error=str(e)[:400])
            print(f"   провал окончательно: {e}")
        else:
            requeue(o["id"], str(e)[:400])
            print(f"   вернул в очередь: {e}")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", action="store_true", help="крутиться, а не один проход")
    ap.add_argument("--dry", action="store_true", help="показать, но не исполнять")
    a = ap.parse_args()
    if not a.loop:
        if not run_once(a.dry):
            print("очередь пуста")
        sys.exit(0)
    print(f"исполнитель запущен, проверяю очередь раз в {POLL_SECONDS} с")
    while True:
        try:
            while run_once(a.dry):
                pass
        except Exception as e:
            print(f"сбой прохода: {e}")
        time.sleep(POLL_SECONDS)
