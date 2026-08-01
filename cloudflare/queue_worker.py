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

# Где лежат данные проекта. По умолчанию — рядом со скриптом, но если исполнителя запускают
# из рабочей копии (worktree), данных там нет: собранный сайт и архив статей живут только
# в главной папке. Тогда путь задаётся явно:
#     B42_DATA_ROOT=C:\...\bridge42worlds python cloudflare/queue_worker.py
# Без этого генерация молча создала бы пустое дерево в стороне и «сделала» бы статью,
# которой никто не увидит.
DATA_ROOT = Path(os.environ.get("B42_DATA_ROOT") or ROOT)

DB_ID = os.environ.get("D1_QUEUE_ID", "44ca0737-e27f-4cb5-bac8-9b132c935e4d")
MAX_ATTEMPTS = 3          # дальше заказ признаём безнадёжным, а не крутим вечно
POLL_SECONDS = 30


def tg(text):
    """Сообщение в общий канал. Молчит, если канал не настроен, и никогда не роняет прогон:
    недоставленное уведомление — не повод считать, что работа не сделана."""
    token, chat = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")
    if not (token and chat):
        return
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", timeout=20,
                      json={"chat_id": chat, "parse_mode": "HTML", "text": text})
    except Exception:
        pass


_cap_notified = set()


def notify_cap_reached(msg):
    """Сообщаем о потолке ОДИН раз в сутки, а не на каждый заказ в очереди: иначе при десяти
    ждущих заказах канал получит десять одинаковых сообщений подряд."""
    day = time.strftime("%Y-%m-%d")
    if day in _cap_notified:
        return
    _cap_notified.add(day)
    tg(f"🛑 <b>Потолок статей на сегодня</b>\n{msg}\nЗаказы ждут в очереди до завтра.")


class DailyCapReached(Exception):
    """Суточный потолок статей исчерпан. Отдельный тип, а не общая ошибка: заказ надо вернуть
    в очередь до завтра, а не отправлять в повторные попытки и не признавать провалившимся."""


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


STUCK_MINUTES = 45      # дольше самого долгого честного заказа (генерация статьи ~10 мин)


def revive_stuck():
    """Возвращает в очередь заказы, застрявшие в `running`.

    Находка разработчика 2026-07-31, и она серьёзнее, чем «потерялся один заказ»: если
    исполнитель умер между взятием и завершением, строка остаётся `running` навсегда,
    а частичный индекс дедупликации не отпускает пару (статья, язык). Значит повторный
    заказ той же статьи склеится с мертвецом и будет ждать вечно — читатель нажимает
    кнопку, мы отвечаем «уже в работе», и работа не идёт никогда.

    Порог с запасом: 45 минут дольше любого честного заказа, поэтому живой прогон
    у нас не отберут. Счётчик попыток не трогаем — он уже увеличен при взятии, и
    безнадёжный заказ всё равно остановится по MAX_ATTEMPTS."""
    edge = int(time.time() * 1000) - STUCK_MINUTES * 60_000
    rows = sql("""UPDATE orders SET status='queued',
                         error='исполнитель не завершил заказ — вернули в очередь'
                   WHERE status='running' AND started_at < ? RETURNING id""", [edge])
    if rows:
        print(f"вернул в очередь зависших: {len(rows)}")
    return len(rows)


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
        cwd=DATA_ROOT, env={**os.environ, "PYTHONIOENCODING": "utf-8"}).returncode
    if code != 0:
        raise RuntimeError(f"перевод завершился с кодом {code}")

    # Адрес ищем по диску, как и в do_article. Раньше здесь собирался путь без даты —
    # `/lang/{to}/archive/{id}/`, — а настоящий адрес всегда с датой. Разработчику это
    # не мешало (он по ссылке не ходит), но любой следующий потребитель получил бы 404.
    # Находка разработчика, 2026-07-31.
    found = next(DATA_ROOT.glob(f"lang/ru/archive/*/{arxiv_id}"), None)
    day = found.parent.name if found else None
    url = f"/lang/{to}/archive/{day}/{arxiv_id}/" if day else None
    return {"url": url, "arxiv_id": arxiv_id, "lang": to}


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
    """«Хочу статью про это». Включено 2026-07-30 с потолком владельца: 10 статей в сутки
    на весь проект (не на человека). Потолок и выключатель — настройками, без правки кода:
        ORDERS_ARTICLE_ENABLED=0     полностью выключить
        ORDERS_ARTICLE_DAILY_CAP=10  сменить потолок
    Потолок считается по факту исполненных за сутки, а не по числу принятых заказов:
    отклонённые и упавшие денег не стоили, наказывать за них следующего незачем."""
    if os.environ.get("ORDERS_ARTICLE_ENABLED", "1") == "0":
        raise NotImplementedError("генерация по заказу выключена настройкой")

    cap = int(os.environ.get("ORDERS_ARTICLE_DAILY_CAP", "10"))
    since = int(time.time() * 1000) - 86400_000
    done_today = sql("""SELECT COUNT(*) AS n FROM orders
                        WHERE kind='article' AND status='done' AND finished_at > ?""", [since])
    n = done_today[0]["n"] if done_today else 0
    if n >= cap:
        # Не ошибка и не вина заказа — просто на сегодня всё. Возвращаем в очередь:
        # завтра тот же заказ исполнится первым, читателю ничего переделывать не надо.
        raise DailyCapReached(f"на сегодня потолок статей исчерпан ({n} из {cap})")

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
        cwd=DATA_ROOT, env={**os.environ, "PYTHONIOENCODING": "utf-8"}).returncode
    if code != 0:
        raise RuntimeError(f"генерация завершилась с кодом {code}")

    # Настоящий адрес статьи знает только генератор: дату он берёт из метаданных arXiv,
    # а не из сегодняшнего дня. Ищем, куда она легла, вместо того чтобы гадать.
    found_dir = next(DATA_ROOT.glob(f"lang/ru/archive/*/{arxiv_id}"), None)
    if not found_dir:
        raise RuntimeError("генератор отработал, но статьи на диске нет")
    day = found_dir.parent.name
    url = f"/lang/{lang}/archive/{day}/{arxiv_id}/"

    # Честность про видимость. `run.py ids` сайт НЕ публикует — по правилам проекта публикация
    # это выпуск, а не побочный эффект, и делает его ведущая сессия после приёмки. Значит
    # статья готова, но читателю ещё не видна. Говорим об этом прямо, иначе он пойдёт по
    # ссылке и упрётся в 404, решив, что мы соврали.
    return {"arxiv_id": arxiv_id, "title": title, "url": url, "awaiting_publish": True}


def do_ask(payload, lang):
    # Вопрос боту исполняет Worker: у него уже есть вектор и модель, и читатель ждёт ответа
    # сейчас, а не через тридцать секунд. Сюда заказ попадает, только если Worker не смог.
    raise NotImplementedError("вопросы боту исполняет Worker, а не очередь")


HANDLERS = {"translate": do_translate, "article": do_article, "ask": do_ask}


def run_once(dry=False):
    # Сначала подбираем брошенное, потом берём новое: иначе зависший заказ так и лежит,
    # пока кто-нибудь не заметит его вручную — а заметит он его по жалобе читателя.
    revive_stuck()
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
    except DailyCapReached as e:
        # Потолок на сегодня. Заказ возвращается в очередь и попытка не засчитывается —
        # иначе три занятых дня подряд «съели» бы заказ, ничего не сделав.
        sql("UPDATE orders SET status='queued', attempts=attempts-1, error=? WHERE id=?",
            [str(e), o["id"]])
        print(f"   {e} — заказ ждёт завтра")
        notify_cap_reached(str(e))
        return False        # дальше по очереди не идём: потолок общий, следующим тоже нельзя
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
    from heartbeat import beat
    while True:
        try:
            while run_once(a.dry):
                pass
        except Exception as e:
            print(f"сбой прохода: {e}")
        # Отмечаемся живыми ПОСЛЕ прохода, а не до: отметка должна означать «я работаю»,
        # а не «я запустился». Сторож молчания в Worker проверяет её раз в сутки.
        beat("queue")
        time.sleep(POLL_SECONDS)
