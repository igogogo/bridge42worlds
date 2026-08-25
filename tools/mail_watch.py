"""Сторож почты: новое письмо → сообщение в наш Telegram-канал. Ни одно не пропустим.

Владелец 2026-07-31: «целевая аудитория — арабский мир, это АВТОРЫ; они найдут себя
на сайте и будут писать на почту. Будь готов, мониторь, отвечать; чтобы письмо не
прошло незамеченным».

    python tools/mail_watch.py            один проход: что нового — в канал
    python tools/mail_watch.py --loop     крутиться (по умолчанию раз в 120 с)
    python tools/mail_watch.py --list     показать последние письма, ничего не слать

Доступы — из .env (MAIL_HOST/MAIL_USER/MAIL_PASS, IMAP 993 SSL). Файл вне git.
Прочитанность писем НЕ трогаем: помечать письмо прочитанным должен человек, а не
сторож — иначе владелец увидит пустой ящик и решит, что писем не было. Что уже
показано, помним у себя в temp/mail-seen.json по UID.
"""
import argparse
import email
import imaplib
import json
import os
import sys
import time
from email.header import decode_header, make_header
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SEEN = ROOT / "temp" / "mail-seen.json"


def env():
    out = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return {**out, **os.environ}


def hdr(raw):
    """Заголовки писем приходят закодированными (=?utf-8?B?...?=) — разворачиваем,
    иначе в канал уедет абракадабра вместо арабского имени автора."""
    try:
        return str(make_header(decode_header(raw or "")))
    except Exception:
        return raw or ""


def body_snippet(msg, limit=400):
    """Первые строки текста. Ищем text/plain; если письмо только в HTML — грубо
    снимаем теги: нам нужен смысл в уведомлении, а не вёрстка."""
    import re
    text = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                text = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
                break
        if not text:
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    html = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
                    text = re.sub(r"<[^>]+>", " ", html)
                    break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            text = payload.decode(msg.get_content_charset() or "utf-8", "replace")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def tg(text):
    # Общий выключатель канала (tools/tg_silence.py). Владелец 25 августа: «выруби
    # все сообщения в ленту, пока ждём ML». Дело при этом продолжается — молчит
    # только рапорт.
    try:
        import sys as _s
        from pathlib import Path as _P
        _r = str(_P(__file__).resolve().parent.parent)
        if _r not in _s.path:
            _s.path.insert(0, _r)
        from tools.tg_silence import guard as _guard
        if _guard(text):
            return False
    except ImportError:
        pass
    e = env()
    token, chat = e.get("TG_BOT_TOKEN"), e.get("TG_CHAT_ID")
    if not (token and chat):
        print("⚠️ Telegram не настроен — печатаю в консоль:\n" + text)
        return False
    import requests
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", timeout=20,
                          json={"chat_id": chat, "text": text[:4000], "parse_mode": "HTML",
                                "disable_web_page_preview": True})
        return r.status_code == 200
    except Exception as ex:
        print(f"⚠️ уведомление не ушло: {ex}")
        return False


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def is_machine_mail(msg, frm, subj):
    """Письмо от машины, а не от человека: в канал такому не место.

    Владелец 12 августа: «потом туда сыплется какой-то мусор типа „недоставлено, почта“».
    Сторож заведён ради писем авторов — одно такое письмо ценнее сотни просмотров. Но
    рядом с ними в ящик валятся отчёты о недоставке, автоответы и рассылки, и в канале
    они выглядят одинаково. Когда в ленте уведомлений шум, настоящее письмо в ней тонет —
    ровно то, от чего сторож и должен защищать.

    Проверяем по служебным заголовкам (их ставит почтовый сервер, подделать нечем) и по
    адресу отправителя. Тему смотрим последней и только по точным оборотам: «недоставлено»
    может быть и в письме живого человека.
    """
    # Стандартные заголовки автоматической почты: RFC 3834 и практика рассылок.
    for h in ("Auto-Submitted", "X-Auto-Response-Suppress", "List-Unsubscribe",
              "List-Id", "Precedence"):
        v = (msg.get(h) or "").lower()
        if not v:
            continue
        if h == "Auto-Submitted" and v.startswith("no"):
            continue          # auto-submitted: no — это обычное человеческое письмо
        if h == "Precedence" and v not in ("bulk", "list", "junk", "auto_reply"):
            continue
        return True
    low = (frm or "").lower()
    if any(w in low for w in ("mailer-daemon", "postmaster@", "noreply", "no-reply",
                              "donotreply", "bounce", "notification")):
        return True
    s = (subj or "").lower()
    return any(w in s for w in (
        "undelivered mail", "delivery status notification", "mail delivery failed",
        "returned to sender", "delivery has failed", "out of office",
        "автоматический ответ", "недоставлено", "доставка не удалась"))


def load_seen():
    try:
        return set(json.loads(SEEN.read_text(encoding="utf-8")))
    except Exception:
        return set()


def save_seen(seen):
    SEEN.parent.mkdir(exist_ok=True)
    SEEN.write_text(json.dumps(sorted(seen)[-500:]), encoding="utf-8")


def boxes():
    """Все наши ящики, а не один. Опубликованы в about на пяти языках — значит, писать
    могут на любой, и молчать не должен ни один (владелец 2026-07-31: «адреса у тебя
    в about, должны быть все»). Пароль общий; список — в .env через запятую."""
    e = env()
    raw = e.get("MAIL_USERS") or e.get("MAIL_USER") or ""
    return [b.strip() for b in raw.split(",") if b.strip()]


def check(list_only=False, quiet=False):
    total = 0
    for box in boxes():
        try:
            total += check_box(box, list_only=list_only, quiet=quiet)
        except Exception as ex:
            print(f"⚠️ {box}: {type(ex).__name__} {ex}")
    return 0


def check_box(user, list_only=False, quiet=False):
    e = env()
    host, pw = e.get("MAIL_HOST"), e.get("MAIL_PASS")
    if not (host and user and pw):
        print("❌ нет доступов к почте в .env (MAIL_HOST/MAIL_USERS/MAIL_PASS)")
        return 0
    M = imaplib.IMAP4_SSL(host, int(e.get("MAIL_IMAP_PORT", 993)), timeout=30)
    M.login(user, pw)
    M.select("INBOX")
    # По UID, а не по номеру: номера съезжают при удалении письма, UID — нет.
    typ, data = M.uid("search", None, "ALL")
    uids = data[0].split()
    seen = load_seen()
    fresh = [u for u in uids if f"{user}:{u.decode()}" not in seen]
    if list_only:
        print(f"— {user}: писем {len(uids)}")
        for u in uids[-10:]:
            typ, d = M.uid("fetch", u, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            msg = email.message_from_bytes(d[0][1])
            print(f"  [{u.decode()}] {hdr(msg.get('Date'))[:31]} | {hdr(msg.get('From'))[:40]} | {hdr(msg.get('Subject'))[:60]}")
        M.logout()
        return 0
    sent = skipped = 0
    for u in fresh:
        # PEEK — не помечаем прочитанным: это дело человека, а не сторожа
        typ, d = M.uid("fetch", u, "(BODY.PEEK[])")
        if not d or not d[0]:
            continue
        msg = email.message_from_bytes(d[0][1])
        frm, subj = hdr(msg.get("From")), hdr(msg.get("Subject"))
        # Машинную почту помечаем прочитанной и в канал не отправляем — иначе настоящее
        # письмо автора тонет в отчётах о недоставке.
        if is_machine_mail(msg, frm, subj):
            seen.add(f"{user}:{u.decode()}")
            skipped += 1
            continue
        body = body_snippet(msg)
        # Письма на author@ — главный канал приглашений в совет (владелец 2026-08-02:
        # «следи внимательно за ящиком, где я автор, — там в ответ можно приглашать сразу»).
        # Автор, подтвердивший работу, ценнее сотни просмотров: он знает предмет и уже
        # заинтересован. Помечаем такое письмо отдельно, чтобы оно не потерялось в потоке.
        author_box = user.split("@")[0].lower() in ("author", "proposal")
        looks_author = author_box or any(
            w in (subj + " " + body).lower()
            for w in ("author", "my paper", "our paper", "arxiv", "مؤلف", "автор статьи"))
        head = ("👤 <b>АВТОР ПИШЕТ</b> — можно приглашать в совет ответом\n"
                if looks_author else "📨 <b>Письмо</b>\n")
        text = (f"{head}Ящик: {esc(user)}\nОт: {esc(frm)}\nТема: {esc(subj)}\n\n{esc(body)}")
        if tg(text):
            sent += 1
        seen.add(f"{user}:{u.decode()}")
    save_seen(seen)
    M.logout()
    if not quiet:
        print(f"{user}: писем {len(uids)}, новых {len(fresh)}, уведомлений {sent}"
              + (f", машинных пропущено {skipped}" if skipped else ""))
    return sent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", action="store_true", help="крутиться постоянно")
    ap.add_argument("--every", type=int, default=120, help="период опроса в секундах")
    ap.add_argument("--list", action="store_true", help="показать последние письма и выйти")
    args = ap.parse_args()
    if not args.loop:
        return check(list_only=args.list)
    print(f"сторож почты запущен, опрос раз в {args.every} с")
    # Отметка «я жив» в KV (добавлено DevOps'ом 2026-08-01, условие архитектора).
    # Сторож, который молча умер, выглядит ровно как сторож, у которого всё спокойно —
    # и узнаём мы об этом от автора, чьё письмо никто не прочитал. Отметку проверяет
    # cron-Worker и пишет в канал, если она устарела.
    sys.path.insert(0, str(ROOT / "cloudflare"))
    try:
        from heartbeat import beat
    except Exception:
        def beat(_name):
            return False

    # ГЛАВНОЕ ИСПРАВЛЕНИЕ 2026-08-09. Раньше отметка ставилась ПОСЛЕ каждого круга,
    # удался опрос или нет. То есть она означала «процесс жив», а мы читали её как
    # «почта проверяется» — а это разные вещи. 9 августа сеть отвалилась
    # (gaierror 11001), сторож два с половиной часа честно крутился, каждый круг падал
    # и каждый круг бодро отмечался живым. Тревога не сработала ни разу, письмо автора
    # с работой пролежало непрочитанным, и забрал его человек руками.
    #
    # Теперь отметка ставится ТОЛЬКО после удачного опроса. Сеть пропала — отметка
    # стареет — Worker через час говорит в канал. Сигнал стал означать то, что от него
    # ждут: не «я запущен», а «я делаю дело».
    fails = 0
    while True:
        try:
            check(quiet=True)
            if fails:
                print(f"✅ связь восстановилась после {fails} неудачных попыток")
            fails = 0
            beat("mail")
            delay = args.every
        except Exception as ex:
            fails += 1
            print(f"⚠️ опрос не удался ({fails}): {type(ex).__name__} {ex}")
            # Отступ при повторных неудачах: сеть, которой нет, не станет доступнее
            # оттого, что мы дёргаем её каждые две минуты. Потолок — десять минут,
            # чтобы возвращение сети замечалось быстро, а не через полчаса.
            delay = min(args.every * (2 ** min(fails, 3)), 600)
        time.sleep(delay)


if __name__ == "__main__":
    sys.exit(main())
