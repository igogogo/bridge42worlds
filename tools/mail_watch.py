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


def load_seen():
    try:
        return set(json.loads(SEEN.read_text(encoding="utf-8")))
    except Exception:
        return set()


def save_seen(seen):
    SEEN.parent.mkdir(exist_ok=True)
    SEEN.write_text(json.dumps(sorted(seen)[-500:]), encoding="utf-8")


def check(list_only=False, quiet=False):
    e = env()
    host, user, pw = e.get("MAIL_HOST"), e.get("MAIL_USER"), e.get("MAIL_PASS")
    if not (host and user and pw):
        print("❌ нет доступов к почте в .env (MAIL_HOST/MAIL_USER/MAIL_PASS)")
        return 1
    M = imaplib.IMAP4_SSL(host, int(e.get("MAIL_IMAP_PORT", 993)), timeout=30)
    M.login(user, pw)
    M.select("INBOX")
    # По UID, а не по номеру: номера съезжают при удалении письма, UID — нет.
    typ, data = M.uid("search", None, "ALL")
    uids = data[0].split()
    seen = load_seen()
    fresh = [u for u in uids if u.decode() not in seen]
    if list_only:
        for u in uids[-10:]:
            typ, d = M.uid("fetch", u, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            msg = email.message_from_bytes(d[0][1])
            print(f"  [{u.decode()}] {hdr(msg.get('Date'))[:31]} | {hdr(msg.get('From'))[:40]} | {hdr(msg.get('Subject'))[:60]}")
        M.logout()
        return 0
    sent = 0
    for u in fresh:
        # PEEK — не помечаем прочитанным: это дело человека, а не сторожа
        typ, d = M.uid("fetch", u, "(BODY.PEEK[])")
        if not d or not d[0]:
            continue
        msg = email.message_from_bytes(d[0][1])
        frm, subj = hdr(msg.get("From")), hdr(msg.get("Subject"))
        text = f"📨 <b>Письмо на {esc(user)}</b>\nОт: {esc(frm)}\nТема: {esc(subj)}\n\n{esc(body_snippet(msg))}"
        if tg(text):
            sent += 1
        seen.add(u.decode())
    save_seen(seen)
    M.logout()
    if not quiet:
        print(f"писем в ящике {len(uids)}, новых для нас {len(fresh)}, отправлено уведомлений {sent}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", action="store_true", help="крутиться постоянно")
    ap.add_argument("--every", type=int, default=120, help="период опроса в секундах")
    ap.add_argument("--list", action="store_true", help="показать последние письма и выйти")
    args = ap.parse_args()
    if not args.loop:
        return check(list_only=args.list)
    print(f"сторож почты запущен, опрос раз в {args.every} с")
    while True:
        try:
            check(quiet=True)
        except Exception as ex:
            print(f"⚠️ опрос не удался: {type(ex).__name__} {ex}")
        time.sleep(args.every)


if __name__ == "__main__":
    sys.exit(main())
