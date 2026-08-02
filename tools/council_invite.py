"""Пригласить в совет: выдать ключ и отправить ссылку письмом.

Владелец 2026-08-02: «в совет приглашаем не за просмотры, а за внятное участие —
особенно авторов работ, которые мы разобрали; за ящиком автора следи внимательно,
там в ответ можно приглашать сразу».

    python tools/council_invite.py --email автор@универ.edu --name "Dr. Ahmed"
    python tools/council_invite.py --name "Стратег" --kind ai        (без почты)
    python tools/council_invite.py --email … --lang en               (письмо по-английски)

Что делает: просит у Worker'а новый ключ (ручка /api/council/mint, закрыта админ-
секретом), затем — если дан адрес — отправляет короткое письмо со ссылкой. Ссылка
открывает кабинет без пароля.

Почему ключ выдаёт сервер, а не мы локально: ключ должен сразу существовать в базе,
иначе человек перейдёт по ссылке и получит «вы не участник» — худшее первое впечатление.
"""
import argparse
import os
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
SITE = "https://bridge42worlds.academy"

LETTER = {
    "ru": ("Приглашение в наблюдательный совет bridge42worlds",
           "Здравствуйте!\n\n"
           "Мы разбираем научные работы простым языком и переводим их на пять языков.\n"
           "У проекта есть наблюдательный совет — небольшой круг людей, которые решают,\n"
           "куда ему двигаться: что делать дальше, на что тратить, чего не делать никогда.\n\n"
           "Мы приглашаем вас. Не за число прочитанных страниц, а потому что вы в теме\n"
           "по существу.\n\n"
           "Вход по ссылке, пароль не нужен:\n  {link}\n\n"
           "Внутри: текущая повестка, голосование, ваши предложения. Заседания —\n"
           "по воскресеньям, уведомления за два дня. Отказаться можно молча: просто\n"
           "не переходите по ссылке.\n\n"
           "bridge42worlds"),
    "en": ("Invitation to the bridge42worlds observers' council",
           "Hello,\n\n"
           "We explain scientific papers in plain language and publish them in five languages.\n"
           "The project has an observers' council — a small circle of people who decide where\n"
           "it goes: what to build next, what to spend on, what never to do.\n\n"
           "We are inviting you. Not for the number of pages read, but because you know\n"
           "the subject.\n\n"
           "Enter by link, no password:\n  {link}\n\n"
           "Inside: the current agenda, voting, your proposals. Meetings are on Sundays,\n"
           "notices two days ahead. Declining is silent — just don't follow the link.\n\n"
           "bridge42worlds"),
}


def env():
    out = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return {**out, **os.environ}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--email")
    ap.add_argument("--name", default="")
    ap.add_argument("--kind", default="human", choices=["human", "ai"])
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--no-mail", action="store_true", help="только выдать ключ, письмо не слать")
    args = ap.parse_args()

    e = env()
    tok = e.get("COUNCIL_ADMIN_TOKEN")
    if not tok:
        print("❌ нет COUNCIL_ADMIN_TOKEN в .env — секрет задаёт DevOps в Worker и кладёт сюда")
        return 1
    import requests
    try:
        r = requests.post(f"{SITE}/api/council/mint", timeout=25,
                          headers={"x-b42-admin": tok, "content-type": "application/json"},
                          json={"name": args.name, "email": args.email or "", "kind": args.kind})
    except Exception as ex:
        print(f"❌ ключ не выдан: {ex}")
        return 1
    if r.status_code != 200:
        print(f"❌ ключ не выдан ({r.status_code}): {r.text[:200]}")
        return 1
    d = r.json()
    print(f"✅ ключ: {d['key']}\n   ссылка: {d['link']}")

    if args.email and not args.no_mail:
        subj, body = LETTER.get(args.lang, LETTER["en"])
        from council_mail import send
        ok = send(args.email, subj, body.format(link=d["link"]),
                  sender=(e.get("MAIL_USERS", "").split(",")[0].strip() or None))
        print("✅ письмо отправлено" if ok else "⚠️ письмо не ушло — ссылку отправьте вручную")
    return 0


if __name__ == "__main__":
    sys.exit(main())
