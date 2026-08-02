#!/usr/bin/env python3
"""Письма совета: приглашение в совет и уведомление о новой повестке.

Владелец 2026-08-01: «мне должно прийти приглашение по почте со ссылкой на новый
документ-повестку, а то храним — вот и можно посмотреть все заседания, что решили,
какие предложения» и «чтобы можно было пригласить кого-то просто письмом по ссылке».
Это оно.

Почему письмо, а не уведомление на сайте. Участник совета не обязан заходить к нам
и проверять, не появилась ли повестка. Орган, о заседаниях которого надо догадываться,
не работает. Письмо приходит само — а по ссылке лежит всё, что решили за всю историю.

Личный кабинет — это `/council/`: список всех заседаний, решений и отчётов о сделанном.
Отдельного кабинета с паролем нет намеренно: пароля нет — значит нечему утечь. Ключ
вида B42-XXXX — не пропуск, а способ узнать своё предложение в повестке, где видны
роли, а не имена.

ПО УМОЛЧАНИЮ НИЧЕГО НЕ ОТПРАВЛЯЕТСЯ. Без `--send` скрипт печатает письма в консоль.
Рассылка живым людям — не то действие, которое должно случаться от опечатки в команде.

Запуск:
    python council_invite.py --to кто@почта --lang ru       # показать письмо
    python council_invite.py --to кто@почта --send          # отправить
    python council_invite.py --agenda 2026-08-04            # показать рассылку
    python council_invite.py --agenda 2026-08-04 --send     # разослать участникам
    python council_invite.py --members                      # кто в списке
    python council_invite.py --pull                         # добрать из заявок
"""
import argparse
import json
import re
import smtplib
import ssl
import sys
from datetime import date
from email.message import EmailMessage
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent
DIR = ROOT / "data" / "council"
MEMBERS = DIR / "участники.jsonl"
INBOX = DIR / "входящие.jsonl"
LETTERS = DIR / "письма.json"

SITE = "https://bridge42worlds.academy"
FROM_BOX = "admin@bridge42worlds.academy"   # письма совета идут от администратора
LANGS = ("ru", "en", "es", "ar", "fr")

# Адрес без экзотики, но и без придирок: живые ящики бывают с плюсом и точками.
MAIL_RE = re.compile(r"^[^@\s,;<>]+@[^@\s,;<>]+\.[A-Za-z]{2,}$")


def env():
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


def texts(lang):
    """Тексты писем. Лежат данными, а не в коде: поправить формулировку должно быть
    можно без правки скрипта — и на всех пяти языках сразу, а не только на русском."""
    all_t = json.loads(LETTERS.read_text(encoding="utf-8"))
    return all_t.get(lang) or all_t["ru"]


# ── список участников ────────────────────────────────────────────────────────
# Файл не в git: там почты и ключи живых людей, а репозиторий переживёт и участника,
# и его согласие. Формат — по строке JSON, чтобы дописывать без перезаписи целого.

def members():
    if not MEMBERS.exists():
        return []
    out = []
    for line in MEMBERS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def save_members(rows):
    MEMBERS.parent.mkdir(parents=True, exist_ok=True)
    MEMBERS.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                       encoding="utf-8")


def ours(mail):
    """Наш ли это ящик. Проверка не косметическая: попади `proposal@` в участники —
    рассылка повестки придёт в ящик сбора, и council_collect.py прочитает наше же
    письмо как «предложение живого человека». Совет, который цитирует сам себя,
    бесполезен; поймано на первой же проверке отправки."""
    return (mail or "").strip().lower().endswith("@bridge42worlds.academy")


def remember(mail, lang="ru", name="", token="", note=""):
    """Добавить или обновить участника. Почта — ключ: один человек, одна строка."""
    mail = (mail or "").strip()
    if not MAIL_RE.match(mail) or ours(mail):
        return None
    rows = members()
    for r in rows:
        if r.get("mail", "").lower() == mail.lower():
            for k, v in (("lang", lang), ("name", name), ("token", token)):
                if v and not r.get(k):
                    r[k] = v
            save_members(rows)
            return r
    row = {"mail": mail, "name": name, "lang": lang if lang in LANGS else "ru",
           "token": token, "since": date.today().isoformat(), "note": note,
           "invited": "", "last": ""}
    rows.append(row)
    save_members(rows)
    return row


def pull_from_inbox():
    """Добрать участников из заявок. Человек, приславший заявку с почтой, уже сказал
    «свяжитесь со мной» — второй раз спрашивать согласие незачем, но и подписывать
    молча тех, кто почту не оставил, нельзя."""
    if not INBOX.exists():
        print("заявок нет")
        return 0
    added = 0
    for line in INBOX.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        mail = (r.get("почта") or r.get("email") or "").strip()
        if not MAIL_RE.match(mail):
            continue
        was = any(m.get("mail", "").lower() == mail.lower() for m in members())
        remember(mail, r.get("язык") or r.get("lang") or "ru",
                 r.get("имя") or "", r.get("ключ") or "", note="заявка")
        if not was:
            added += 1
            print(f"  + {mail}")
    print(f"добавлено: {added}")
    return added


# ── письма ───────────────────────────────────────────────────────────────────

def session_file(d):
    f = DIR / f"{d}.json"
    if not f.exists():
        raise SystemExit(f"нет заседания {d} — ищу {f.relative_to(ROOT)}")
    return json.loads(f.read_text(encoding="utf-8"))


def invite_letter(lang, name=""):
    t = texts(lang)
    hi = t["hi_name"].format(name=name) if name else t["hi"]
    body = "\n".join([
        hi, "",
        t["inv_1"], "",
        t["inv_2"], "",
        t["inv_rules"],
        "  · " + t["rule_1"],
        "  · " + t["rule_2"],
        "  · " + t["rule_3"], "",
        t["inv_read"] + f"  {SITE}/council.html",
        t["inv_arch"] + f"  {SITE}/council/", "",
        t["inv_key"], "",
        t["sign"],
    ])
    return t["inv_subject"], body


def agenda_letter(lang, data, name=""):
    """Письмо о новой повестке.

    Ключи в файлах заседаний английские (`date`, `number`, `agenda`, `title`) — это
    не мелочь: первая версия читала русские, получала пустоту и молча слала письмо
    «повестка №? готова, вопросов нет». Молчаливый откат — худший класс ошибок
    в этом проекте, поэтому пустая повестка теперь просто останавливает рассылку.
    """
    t = texts(lang)
    d = data.get("date") or ""
    num = data.get("number") or "?"
    items = [i.get("title") or "" for i in (data.get("agenda") or [])]
    items = [x for x in items if x]
    if not (d and items):
        raise SystemExit(f"заседание {d or '?'}: повестка пуста — рассылать нечего")
    hi = t["hi_name"].format(name=name) if name else t["hi"]
    lines = [hi, "", t["ag_1"].format(num=num, date=d), ""]
    for i, title in enumerate(items, 1):
        lines.append(f"  {i}. {title}")
    lines += ["", t["ag_link"] + f"  {SITE}/council/{d}.html",
              t["inv_arch"] + f"  {SITE}/council/", "",
              t["ag_say"] + f"  {FROM_BOX.replace('admin@', 'proposal@')}", "",
              t["sign"]]
    return t["ag_subject"].format(num=num, date=d), "\n".join(lines)


def send(to, subject, body, e, really):
    """Отправка. Без --send письмо печатается и никуда не идёт."""
    if not really:
        print(f"\n{'─' * 68}\nкому:  {to}\nтема:  {subject}\n{'─' * 68}\n{body}")
        return True
    msg = EmailMessage()
    msg["From"] = FROM_BOX
    msg["To"] = to
    msg["Subject"] = subject
    msg["Reply-To"] = FROM_BOX.replace("admin@", "proposal@")
    msg.set_content(body, charset="utf-8")
    host, port = e.get("MAIL_HOST"), int(e.get("MAIL_SMTP_PORT") or 587)
    with smtplib.SMTP(host, port, timeout=30) as S:
        S.ehlo()
        S.starttls(context=ssl.create_default_context())
        S.login(FROM_BOX, e["MAIL_PASS"])
        S.send_message(msg)
    print(f"  ✅ {to}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", help="пригласить одного человека по почте")
    ap.add_argument("--name", default="", help="как обратиться")
    ap.add_argument("--lang", default="ru", choices=LANGS)
    ap.add_argument("--agenda", help="разослать участникам повестку YYYY-MM-DD")
    ap.add_argument("--members", action="store_true", help="показать список")
    ap.add_argument("--pull", action="store_true", help="добрать участников из заявок")
    ap.add_argument("--send", action="store_true", help="действительно отправить")
    a = ap.parse_args()

    if a.members:
        rows = members()
        print(f"участников: {len(rows)}")
        for r in rows:
            mark = "приглашён" if r.get("invited") else "—"
            print(f"  {r['mail']:<40} {r.get('lang','ru')}  {mark}")
        return
    if a.pull:
        pull_from_inbox()
        return

    e = env()
    if a.send and not e.get("MAIL_PASS"):
        raise SystemExit("нет доступа к почте в .env — отправлять нечем")

    if a.to:
        subject, body = invite_letter(a.lang, a.name)
        send(a.to, subject, body, e, a.send)
        if a.send:
            row = remember(a.to, a.lang, a.name)
            if row:
                rows = members()
                for r in rows:
                    if r["mail"].lower() == a.to.lower():
                        r["invited"] = date.today().isoformat()
                save_members(rows)
        else:
            print(f"\n{'─' * 68}\nэто показ. Отправить — добавь --send")
        return

    if a.agenda:
        data = session_file(a.agenda)
        rows = members()
        if not rows:
            print("список участников пуст — некому слать. Смотри --pull")
            subject, body = agenda_letter(a.lang, data)
            send("(некому)", subject, body, e, False)
            return
        ok = 0
        for r in rows:
            subject, body = agenda_letter(r.get("lang", "ru"), data, r.get("name", ""))
            try:
                send(r["mail"], subject, body, e, a.send)
                ok += 1
            except Exception as ex:              # один плохой адрес не рвёт рассылку
                print(f"  ⚠️ {r['mail']}: {type(ex).__name__}: {ex}")
        if a.send:
            for r in rows:
                r["last"] = a.agenda
            save_members(rows)
            print(f"\nразослано: {ok} из {len(rows)}")
        else:
            print(f"\n{'─' * 68}\nэто показ на {len(rows)} адресов. Разослать — добавь --send")
        return

    ap.print_help()


if __name__ == "__main__":
    main()
