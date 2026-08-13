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


def results(meeting_date):
    """Итоги голосования с сайта. Пусто — значит никто не голосовал, и это тоже итог."""
    import requests
    try:
        r = requests.get(f"{SITE}/api/council/results",
                         params={"meeting": meeting_date}, timeout=20)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def letter_results(m, key):
    """Письмо с ИТОГАМИ — то, чего у нас не было вовсе.

    До 13 августа `--results` слал ровно ту же повестку, что и в пятницу: тема письма
    называлась «итоги», а текст звал голосовать по уже закрытому заседанию. Владелец
    писал прямо: «как прошло заседание комитета, ничего не прислали — ни решений, ни
    напоминаний». Теперь письмо отвечает на единственный вопрос, ради которого его
    открывают: что решили.

    Голоса берём с сайта, а не из файла заседания: в файле они появляются только после
    закрытия, а закрытие и рассылка идут одним прогоном.
    """
    date = m.get("date", "")
    res = (results(date) or {}).get("results") or {}
    members = (results(date) or {}).get("members") or 0
    lines = [f"Итоги заседания наблюдательного совета {date}", ""]

    decided, skipped = [], []
    for q in (m.get("agenda") or []):
        qid = q.get("id")
        tally = res.get(qid) or {}
        if not tally:
            skipped.append(q)
            continue
        # Подписи вариантов — из самой повестки: в базе лежат идентификаторы, а человеку
        # нужны слова. Без этого письмо сообщало бы «o2: 1 голос».
        names = {}
        for o in (q.get("options") or []):
            if isinstance(o, dict):
                names[str(o.get("id"))] = str(o.get("label") or o.get("id"))
        best = max(tally.items(), key=lambda kv: kv[1])
        total = sum(tally.values())
        decided.append((q, best, total, names))

    if decided:
        lines.append("Решения:")
        for q, (choice, n), total, names in decided:
            label = names.get(choice, {"yes": "за", "no": "против",
                                       "abstain": "воздержались"}.get(choice, choice))
            lines.append(f"  · {q.get('title','')}")
            lines.append(f"      {label} — {n} из {total}")
        lines.append("")
    if skipped:
        lines.append("Перенесено (никто не проголосовал):")
        for q in skipped:
            lines.append(f"  · {q.get('title','')}")
        lines.append("")

    # Замороженные вопросы — отдельным разделом, с причиной и без имени заморозившего.
    # Владелец 13 августа: заморозка «снимает вопрос с голосования», его «надо обработать
    # и пробовать переформулировать на следующее заседание с объяснением, почему не
    # принято решение». Умолчать об этом в письме значит оставить людей в уверенности,
    # что вопрос просто потеряли.
    frz = frozen(date)
    if frz:
        lines.append("Снято с голосования (заморожено участником совета):")
        for qid, f in frz.items():
            q = next((x for x in (m.get("agenda") or []) if x.get("id") == qid), {})
            lines.append(f"  · {q.get('title', qid)}")
            for why in (f.get("why") or []):
                lines.append(f"      причина: {why}")
            lines.append("      вернётся на следующее заседание в переформулированном виде"
                         if not f.get("quorum")
                         else "      заморожен повторно — решение примет кворум ИИ-участников")
        lines.append("")

    # План работ: что мы делаем по итогам. Без него письмо сообщает, что мы поговорили.
    plan = m.get("sprint") or []
    if plan:
        lines.append("План работ на неделю:")
        for item in plan:
            lines.append(f"  · {item if isinstance(item, str) else item.get('title', '')}")
        lines.append("")

    nxt = m.get("next_meeting") or {}
    if nxt:
        lines.append(f"Следующее заседание: {nxt.get('date', '—')}.")
        for q in (nxt.get("questions") or []):
            lines.append(f"  · {q}")
        lines.append("")

    lines += [f"Участников в совете: {members}." if members else "",
              "Полные итоги и все предложения — в вашем кабинете:",
              f"  {SITE}/council.html?key={key}", "",
              "Решение можно оспорить: напишите в ответ, вопрос вернётся на следующее заседание."]
    return "\n".join(x for x in lines if x is not None)


def frozen(date):
    """Что заморожено на заседании — с сайта, без имён."""
    import requests
    try:
        r = requests.get(f"{SITE}/api/council/frozen?meeting={date}", timeout=20)
        return (r.json() or {}).get("frozen") or {} if r.ok else {}
    except Exception:
        return {}


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
    """Адреса берём у Worker'а, а не из git: это личные данные живых людей.

    ВОЗВРАЩАЕТ None ПРИ СБОЕ, [] — только при честном «список получен, он пуст».
    Находка стратега 2026-08-06: ручки не существовало (405), сбой возвращался пустым
    списком, и рассылка печатала успокоительное «ни у кого нет почты» при живом адресе
    владельца в базе. Различие «не получили» / «пусто» — это разница между тревогой
    и нормой; смешаешь — любой будущий сбой рассылки будет выглядеть нормой."""
    import requests
    e = env()
    tok = e.get("COUNCIL_ADMIN_TOKEN", "")
    if not tok:
        print("❌ нет COUNCIL_ADMIN_TOKEN в .env — список участников недоступен")
        return None
    try:
        r = requests.get(f"{SITE}/api/council/members", headers={"x-b42-admin": tok}, timeout=20)
        if r.status_code == 200:
            return r.json().get("members", [])
        print(f"❌ список участников недоступен: HTTP {r.status_code}")
    except Exception as ex:
        print(f"❌ список участников не получен: {ex}")
    return None


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
        body = (letter_results(m, args.key) if args.results else
                letter_weekly(m, args.key) if args.weekly else
                letter_agenda(m, args.key))
        ok = send(args.test, f"Наблюдательный совет: заседание {m.get('date','')}", body)
        print("✅ письмо отправлено" if ok else "❌ не отправлено")
        return 0 if ok else 1

    got = members()
    if got is None:
        # Сбой получения — ТРЕВОГА, не норма: код 1 наверх (планировщик увидит) и крик
        # в канал — рассылка совета не имеет права умирать молча.
        try:
            import subprocess
            subprocess.run([sys.executable, str(ROOT / "tools" / "status_tg.py"),
                            "⛔ <b>Рассылка совета НЕ ушла</b>: список участников недоступен. "
                            "Письма не отправлены никому."], timeout=60)
        except Exception:
            pass
        return 1
    people = [p for p in got if p.get("email")]
    if not people:
        print("список получен: участников с почтой нет (почта необязательна) — слать некому")
        return 0
    subj = {True: f"Совет: итоги заседания {m.get('date','')}"}.get(args.results) or \
           (f"Совет: сверка недели" if args.weekly else f"Совет: повестка {m.get('date','')}")
    n = 0
    for p in people:
        body = (letter_results(m, p["key"]) if args.results else
                letter_weekly(m, p["key"]) if args.weekly else
                letter_agenda(m, p["key"]))
        if send(p["email"], subj, body):
            n += 1
    print(f"✅ отправлено писем: {n} из {len(people)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
