#!/usr/bin/env python3
"""Сбор предложений совета из трёх источников — в общий ящик.

Источники и их роли:
  · читатели   — комментарии, оставленные на сайте под статьями и страницами тем;
  · совет      — предложения участников через доску (когда DevOps откроет приём);
  · модель     — предложения от модели как ОТДЕЛЬНОГО члена совета.

Про модель отдельно. Владелец 2026-07-31: у модели своя роль в совете, и она отделена
от администратора. Это не украшение: если предложения модели идут от имени ведущего,
совет теряет возможность с ней не согласиться — спорить с администратором и спорить
с одним из членов совета психологически разные вещи. Поэтому у модели свой голос,
свои предложения и своя пометка.

Про анонимность. В повестке видна РОЛЬ, а не человек: «читатель», «участник совета»,
«модель». Обсуждать надо предложение, а не того, кто его внёс. Ключи участников
остаются в данных для секретаря, но на страницу не выводятся.

Запуск:
    python council_collect.py                 # собрать всё
    python council_collect.py --no-model      # без предложений модели
    python council_collect.py --since 2026-07-25
"""
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent
DIR = ROOT / "data" / "council"
INBOX = DIR / "входящие.jsonl"

# Источники живых людей. С Supabase проект ушёл 2026-08-01 — отзывы и реакции теперь
# в нашей собственной базе D1, а письма в пяти ящиках на домене. Читаем оба.
D1_NAME = "b42-queue"
MAILBOX = "proposal@"          # ящик, заведённый специально под предложения


def _env():
    """Доступы из .env. В git их нет и не будет — здесь только чтение файла."""
    f = ROOT / ".env"
    if not f.exists():
        f = ROOT.parent / "bridge42worlds" / ".env"
    if not f.exists():
        return {}
    out = {}
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _d1(sql, env):
    acc, tok = env.get("CLOUDFLARE_ACCOUNT_ID"), env.get("CLOUDFLARE_API_TOKEN")
    if not (acc and tok):
        raise RuntimeError("нет доступов Cloudflare в .env")
    base = f"https://api.cloudflare.com/client/v4/accounts/{acc}/d1/database"
    req = urllib.request.Request(base, headers={"Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=25) as r:
        dbs = json.load(r).get("result") or []
    db = next((d for d in dbs if d.get("name") == D1_NAME), None)
    if not db:
        raise RuntimeError(f"база {D1_NAME} не найдена")
    req = urllib.request.Request(f"{base}/{db['uuid']}/query",
        data=json.dumps({"sql": sql}).encode(), method="POST",
        headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)["result"][0]["results"]

MODEL_SYSTEM = """Ты — член наблюдательного совета научно-популярного проекта bridge42worlds.
Не администратор и не исполнитель: у тебя такой же голос, как у остальных членов совета,
и такое же право предлагать.

Проект: каждый день превращает свежие работы с arXiv в статьи, понятные любому, на пяти
языках, на четырёх глубинах чтения. Живёт на бюджет владельца, некоммерческий. Ежедневно
делает 20–25 коротких разборов по авторским аннотациям; полный разбор по всему тексту
работы вчетверо дороже и делается по заказу читателя.

Предложи вопросы на заседание совета. Требования:
— предлагай то, что улучшит проект для ЧИТАТЕЛЯ, а не то, что удобно разработчикам;
— каждое предложение должно быть проверяемым: понятно, что именно сделать и как понять,
  что стало лучше;
— не повторяй то, что уже есть в списке «уже сделано»;
— не бойся неудобных вопросов: совет для того и нужен, чтобы их задавать;
— пиши по-русски, коротко, человеческим языком, без канцелярита и без слов «оптимизация»,
  «синергия», «экосистема».

Ответ строго JSON: {"предложения": ["текст", "текст", ...]}. Никакого текста вне JSON."""


def from_readers(since):
    """Отзывы с сайта. Владелец 2026-07-31: их тоже обрабатываем и вносим в повестку —
    это голос тех, кто до совета не дошёл, но написал. Форма висит на всех страницах."""
    try:
        rows = _d1("SELECT message AS comment, created_at, page AS base_id, "
                   "lang, email FROM feedback ORDER BY id DESC LIMIT 200", _env())
    except Exception as e:
        print(f"  ⚠️ отзывы с сайта не прочитались ({type(e).__name__}: {e})")
        return []
    out, skipped, lost = [], [], []
    for r in rows:
        text = (r.get("comment") or "").strip()
        if since and (r.get("created_at") or "")[:10] < since:
            continue
        # Текст, потерянный при передаче: сплошные «?» вместо букв. Это НЕ мусор —
        # это чьи-то слова, которые до нас не доехали, и молчать о таком нельзя.
        # Поймано 2026-08-01 на арабском отзыве: 83% вопросительных знаков, ни одной
        # арабской буквы. Сама ручка /api/feedback кодировку держит (проверено живым
        # запросом из браузера), значит ломается ДО неё — почти наверняка это чей-то
        # тест из консоли с однобайтовой кодировкой.
        letters = sum(1 for c in text if c.isalpha())
        if text.count("?") > max(3, len(text) * 0.3) and letters < len(text) * 0.3:
            lost.append(r)
            continue
        # Отсев мусора. Порог по длине и по числу слов: «ууу», «апвп», «test» — это
        # проверки формы, а не мнения. Отсеянное ПЕЧАТАЕМ: тихо выбрасывать чужие слова
        # нельзя, даже если они выглядят ерундой — решать должен человек, а не порог.
        if len(text) < 15 or len(text.split()) < 3:
            skipped.append(text)
            continue
        out.append({"text": text, "role": "читатели",
                    "from": (r.get("email") or "").strip(),
                    "at": (r.get("created_at") or "")[:10],
                    "where": f'{r.get("lang","")}: {r.get("base_id","")}'.strip(": ")})
    if skipped:
        print(f"  отсеяно как проверки формы ({len(skipped)}): "
              + " · ".join(repr(x)[:24] for x in skipped[:8]))
        print("  если среди них есть настоящее — добавь руками во входящие")
    if lost:
        print(f"\n  ⚠️ ОТЗЫВОВ С ПОТЕРЯННЫМ ТЕКСТОМ: {len(lost)}")
        for r in lost:
            print(f'     [{(r.get("created_at") or "")[:16]} · {r.get("lang","")}] '
                  f'{r.get("base_id","")}')
        print("     Слова человека до нас не доехали и восстановлению не подлежат.")
        print("     Ручка кодировку держит — значит ломалось до неё (тест из консоли?).")
    return out


def from_members(since):
    """Предложения участников совета из формы на сайте (ручка /api/council/propose,
    архитектор 2026-08-01). Отдельный источник, а не «ещё одни отзывы»: у этих людей
    есть ключ, они доказали право входа чтением, и их слово по весу другое.

    Без этого источника цепочка рвалась молча: человек нажимал «отправить» на странице
    совета, предложение ложилось в council_proposals — и до повестки не доезжало никогда,
    потому что сборщик про эту таблицу не знал. Форма при этом честно отвечала
    «предложение записано».
    """
    try:
        rows = _d1("SELECT text, created, lang, key FROM council_proposals "
                   "ORDER BY id DESC LIMIT 200", _env())
    except Exception as e:
        # Таблицы может не быть, пока воркер с ручками совета не выкачен на прод.
        # Это не повод рушить сбор, но и молчать нельзя: пустая повестка выглядит
        # так же, как повестка без предложений.
        print(f"  ⚠️ предложения участников не прочитались ({type(e).__name__}: {e})")
        print("     если ручки /api/council ещё не на проде — это ожидаемо")
        return []
    out = []
    for r in rows:
        text = (r.get("text") or "").strip()
        if since and (r.get("created") or "")[:10] < since:
            continue
        if len(text) < 15:
            continue
        out.append({"text": text, "role": "совет",
                    "from": (r.get("key") or "").strip(),
                    "at": (r.get("created") or "")[:10],
                    "where": (r.get("lang") or "")})
    return out


def from_mail(since):
    """Предложения письмами на proposal@. Ящик заведён ровно под это, и письмо —
    самый доступный способ высказаться: не нужен ни ключ, ни аккаунт, ни наш сайт.

    Читаем, но НЕ удаляем и не помечаем прочитанным: почта не наша собственность,
    а канал владельца — сторож tools/mail_watch.py тоже её читает, и портить друг
    другу состояние ящика нельзя."""
    import email, imaplib
    from email.header import decode_header
    env = _env()
    host, port = env.get("MAIL_HOST"), env.get("MAIL_IMAP_PORT")
    users = [u.strip() for u in (env.get("MAIL_USERS") or "").split(",") if u.strip()]
    box = next((u for u in users if u.startswith(MAILBOX)), None)
    if not (host and port and box and env.get("MAIL_PASS")):
        print("  почтовый ящик предложений не настроен — пропускаю")
        return []

    def _text(msg):
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        return part.get_payload(decode=True).decode(
                            part.get_content_charset() or "utf-8", errors="replace")
                    except Exception:
                        continue
            return ""
        try:
            return msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8", errors="replace")
        except Exception:
            return ""

    out = []
    try:
        M = imaplib.IMAP4_SSL(host, int(port), timeout=30)
        M.login(box, env["MAIL_PASS"])
        M.select("INBOX", readonly=True)
        typ, data = M.search(None, "ALL")
        ids = data[0].split()[-50:]
        for i in ids:
            typ, raw = M.fetch(i, "(RFC822)")
            if not raw or not raw[0]:
                continue
            msg = email.message_from_bytes(raw[0][1])
            frm = email.utils.parseaddr(msg.get("From", ""))[1]
            # Свои же служебные письма в повестку не тащим.
            if frm in users:
                continue
            subj = decode_header(msg.get("Subject", ""))[0]
            subj = subj[0].decode(subj[1] or "utf-8", errors="replace") if isinstance(subj[0], bytes) else (subj[0] or "")
            body = _text(msg).strip()
            when = ""
            try:
                when = email.utils.parsedate_to_datetime(msg.get("Date")).date().isoformat()
            except Exception:
                pass
            if since and when and when < since:
                continue
            text = (subj + ". " + body).strip(". ").strip()
            if len(text) < 15:
                continue
            out.append({"text": text[:2000], "role": "письмо", "from": frm,
                        "at": when, "where": MAILBOX})
        M.logout()
    except Exception as e:
        print(f"  ⚠️ почта не прочиталась ({type(e).__name__}: {e})")
        return []
    return out


def done_list():
    done = []
    for f in sorted(DIR.glob("*.json")):
        if f.name.startswith("черновик-"):
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for item in d.get("agenda") or []:
            if item.get("title"):
                done.append(item["title"])
        for x in (d.get("sprint") or {}).get("done") or []:
            done.append(x)
    return done


def from_model(count, done):
    """Ровно столько же предложений, сколько пришло от людей — просьба владельца.
    Модель не должна заглушать живые голоса количеством: у неё один голос из многих."""
    from common import chat, clean_json
    payload = {"сколько предложений нужно": count, "уже сделано": done}
    resp = chat("translate_flash", json.dumps(payload, ensure_ascii=False, indent=1),
                system=MODEL_SYSTEM)
    text = (resp.choices[0].message.content or "").strip()
    data = json.loads(clean_json(text))
    items = data.get("предложения") or []
    today = date.today().isoformat()
    return [{"text": t, "role": "модель", "from": "модель-советник", "at": today}
            for t in items[:count]]


def main():
    args = sys.argv[1:]
    no_model = "--no-model" in args
    since = None
    if "--since" in args:
        try:
            since = args[args.index("--since") + 1]
        except IndexError:
            print("--since без даты"); return 1

    DIR.mkdir(parents=True, exist_ok=True)
    # Уже лежащее во входящих не теряем: собранное раньше могло прийти из доски.
    existing = []
    if INBOX.exists():
        for line in INBOX.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    existing.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    seen = {(i.get("text") or "").strip() for i in existing}

    members = [r for r in from_members(since) if r["text"] not in seen]
    print(f"предложений участников совета: {len(members)}")
    for r in members:
        print(f'  · [{r["from"]}] {r["text"][:70]}')

    readers = [r for r in from_readers(since)
               if r["text"] not in seen and r["text"] not in {x["text"] for x in members}]
    print(f"отзывов с сайта: {len(readers)}")
    for r in readers:
        print(f'  · [{r["where"]}] {r["text"][:70]}')

    known = seen | {x["text"] for x in members} | {x["text"] for x in readers}
    letters = [r for r in from_mail(since) if r["text"] not in known]
    print(f"писем на {MAILBOX}: {len(letters)}")
    for r in letters:
        print(f'  · [{r["from"]}] {r["text"][:70]}')

    readers = members + readers + letters
    human_count = len(readers) + sum(1 for i in existing if i.get("role") != "модель")
    model_items = []
    if not no_model and human_count:
        try:
            model_items = from_model(human_count, done_list())
            print(f"\nпредложений от модели: {len(model_items)} (столько же, сколько от людей)")
            for m in model_items:
                print(f'  · {m["text"][:70]}')
        except Exception as e:
            print(f"  ⚠️ модель не ответила ({type(e).__name__}: {e}) — идём без её предложений")
    elif not human_count:
        print("\nживых предложений нет — модель не зовём: её голос дополняет людей, а не заменяет")

    rows = existing + readers + model_items
    with INBOX.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nво входящих всего: {len(rows)} → {INBOX.relative_to(ROOT)}")
    print("дальше: python council_digest.py <дата заседания>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
