"""Письма участникам совета: повестка, итоги, еженедельная сверка.

Владелец 2026-08-01: «если вошли — напоминать по почте статусы и отчёты; моя почта
igoldobin@gmail.com». Почта у участника необязательна: без неё членство работает
полностью, письмо — услуга для тех, кто его попросил.

Письма шлёт ФАБРИКА, а не Worker: у Worker'а нет SMTP, а у нас есть ящик на домене
(reg.ru, порт 587). Список адресов берётся из базы совета через ручку Worker'а —
в git адресов нет и быть не должно.

    python tools/council_mail.py --agenda        разослать повестку ближайшего заседания
    python tools/council_mail.py --results       разослать итоги последнего заседания
    python tools/council_mail.py --weekly        еженедельная сверка: что сделано, что решается
    python tools/council_mail.py --test АДРЕС    одно письмо себе, ничего массового

Каждое письмо содержит ссылку с ключом — переход открывает кабинет без пароля.
"""
import argparse
import json
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://bridge42worlds.academy"


def env():
    out = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return {**out, **os.environ}


def send(to, subject, body, sender=None):
    e = env()
    host = e.get("MAIL_HOST")
    user = sender or (e.get("MAIL_USERS", "").split(",")[0].strip() or e.get("MAIL_USER"))
    pw = e.get("MAIL_PASS")
    if not (host and user and pw):
        print("❌ нет доступов к почте в .env")
        return False
    msg = EmailMessage()
    msg["From"] = f"bridge42worlds <{user}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(host, int(e.get("MAIL_SMTP_PORT", 587)), timeout=30) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(user, pw)
            s.send_message(msg)
        return True
    except Exception as ex:
        print(f"❌ {to}: {type(ex).__name__} {ex}")
        return False


def meeting():
    p = ROOT / "data" / "council" / "upcoming.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def letter_agenda(m, key):
    lines = [f"Заседание наблюдательного совета {m.get('date','')}", ""]
    lines.append("На повестке:")
    for q in (m.get("agenda") or []):
        lines.append(f"  · {q.get('title','')}")
    lines += ["",
              "Проголосовать и предложить своё — по ссылке (пароль не нужен):",
              f"  {SITE}/council.html?key={key}", "",
              "Голос можно изменить до закрытия заседания.",
              "Если письма не нужны — ответьте одним словом «не надо», и мы уберём адрес."]
    return "\n".join(lines)


def letter_weekly(m, key):
    return "\n".join([
        "Сверка недели · bridge42worlds", "",
        f"Ближайшее заседание: {m.get('date','—')}, вопросов на повестке: {len(m.get('agenda') or [])}.",
        "",
        "Что нового и что решается — в вашем кабинете:",
        f"  {SITE}/council.html?key={key}", "",
        "Отчёт о сделанном за неделю собирается из истории правок — он открыт на странице совета.",
    ])


def members():
    """Адреса берём у Worker'а, а не из git: это личные данные живых людей."""
    import requests
    e = env()
    tok = e.get("COUNCIL_ADMIN_TOKEN", "")
    try:
        r = requests.get(f"{SITE}/api/council/members", headers={"x-b42-admin": tok}, timeout=20)
        if r.status_code == 200:
            return r.json().get("members", [])
        print(f"⚠️ список участников недоступен ({r.status_code}) — нужна ручка /api/council/members у DevOps")
    except Exception as ex:
        print(f"⚠️ список участников не получен: {ex}")
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agenda", action="store_true")
    ap.add_argument("--results", action="store_true")
    ap.add_argument("--weekly", action="store_true")
    ap.add_argument("--test", metavar="ADDR", help="одно письмо на адрес, без рассылки")
    ap.add_argument("--key", default="B42-DEMO-DEMO-DEMO", help="ключ для ссылки в тестовом письме")
    args = ap.parse_args()
    m = meeting()

    if args.test:
        body = letter_agenda(m, args.key) if not args.weekly else letter_weekly(m, args.key)
        ok = send(args.test, f"Наблюдательный совет: заседание {m.get('date','')}", body)
        print("✅ письмо отправлено" if ok else "❌ не отправлено")
        return 0 if ok else 1

    people = [p for p in members() if p.get("email")]
    if not people:
        print("некому слать: ни у кого нет почты (это нормально — она необязательна)")
        return 0
    subj = {True: f"Совет: итоги заседания {m.get('date','')}"}.get(args.results) or \
           (f"Совет: сверка недели" if args.weekly else f"Совет: повестка {m.get('date','')}")
    n = 0
    for p in people:
        body = letter_weekly(m, p["key"]) if args.weekly else letter_agenda(m, p["key"])
        if send(p["email"], subj, body):
            n += 1
    print(f"✅ отправлено писем: {n} из {len(people)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
