#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Отпечатки авторских адресов в облако — чтобы сверять, но не хранить.

ЗАДАЧА. Владелец 25 августа: у автора на его странице должно быть пять действий — «всё
верно», «не хватает моей статьи», «вон тот автор тоже я», «эта статья не моя», «уберите мою
страницу». Всё это работает только по письму с аккредитованного адреса. И отдельно, его же
словами: «его почту не кладём в открытый доступ… но почту не показываем».

ПРОТИВОРЕЧИЕ, из которого пришлось выходить. Письмо шлёт воркер, а адреса живут только на
этой машине (data/authors-contacts.jsonl закрыт и от git, и от публикации — 25 августа мы
поймали, что он едва не уехал в открытый доступ). Положить адреса в D1 значит завести вторую
копию персональных данных в системе, из которой они уже один раз чуть не утекли.

ВЫХОД: в облако уходит НЕ адрес, а его односторонний отпечаток. Восстановить из отпечатка
адрес нельзя, а сверить введённый — можно. Человек на странице вводит свою почту, воркер
считает отпечаток и сличает с тем, что стоит в его же статье; совпало — письмо уходит на
адрес, который он сам и назвал. У нас в облаке адреса нет ни секунды.

Побочно это закрывает и рассылочную пушку: чтобы вызвать письмо на чужой адрес, надо этот
адрес уже знать — а кто знает, тот и без нас напишет напрямую.

КЛЮЧ. Отпечаток считается на SERVICE_KEY — он есть и в .env, и у воркера. Разделение
назначений через приставку «b42-author-email:»: один секрет, разные пространства, и отпечаток
отсюда бесполезен где-либо ещё.

    python tools/author_claims.py            сколько отпечатков уедет
    python tools/author_claims.py --apply    завести таблицы и залить
"""
import argparse
import hashlib
import hmac
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "cloudflare"))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

CONTACTS = ROOT / "data" / "authors-contacts.jsonl"
PREFIX = "b42-author-email:"

SCHEMA = [
    # Отпечатки адресов. Ни одного адреса, только их хэши: сверять достаточно, хранить нельзя.
    """CREATE TABLE IF NOT EXISTS author_emails (
         akey TEXT NOT NULL,        -- ключ автора (panov|ad)
         h    TEXT NOT NULL,        -- HMAC-SHA256 адреса на SERVICE_KEY с приставкой
         PRIMARY KEY (akey, h)
       )""",
    # Заявки: что человек попросил и дошёл ли он по ссылке из письма.
    """CREATE TABLE IF NOT EXISTS author_claims (
         token   TEXT PRIMARY KEY,  -- случайный, живёт в ссылке письма
         akey    TEXT NOT NULL,
         person  TEXT,              -- person_id группы, к которой относится просьба
         action  TEXT NOT NULL,     -- confirm / add / merge / remove / withdraw
         target  TEXT,              -- arXiv id или чужой person_id — смотря по действию
         state   TEXT NOT NULL,     -- sent / applied / manual / expired
         created TEXT NOT NULL,
         applied TEXT
       )""",
    "CREATE INDEX IF NOT EXISTS author_claims_key ON author_claims(akey, created DESC)",
    # Подтверждённое — верхний ярус истины. Форму заказал стратег; адресов здесь НЕТ
    # намеренно: подтверждению адрес не нужен, а держать почты в ещё одном месте незачем.
    """CREATE TABLE IF NOT EXISTS author_confirms (
         akey    TEXT NOT NULL,
         person  TEXT,
         claim   TEXT NOT NULL,     -- mine / not_mine / withdraw
         target  TEXT,
         source  TEXT NOT NULL,     -- page / mail
         created TEXT NOT NULL
       )""",
    "CREATE INDEX IF NOT EXISTS author_confirms_key ON author_confirms(akey)",
]


def env():
    out = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def norm(addr):
    """Адрес к сравнимому виду — та же чистка, что в person_merge: из PDF приходит знак
    сноски, приклеенный спереди («1panov@…»), и без неё отпечатки не сойдутся."""
    a = (addr or "").strip().lower()
    return a.lstrip("0123456789*†‡§¶,;")


def fingerprint(addr, key):
    return hmac.new(key.encode("utf-8"), (PREFIX + norm(addr)).encode("utf-8"),
                    hashlib.sha256).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    import cards_sync as cs
    key = env().get("SERVICE_KEY")
    if not key:
        print("нет SERVICE_KEY в .env — отпечатки считать не на чем")
        return 1
    if not CONTACTS.exists():
        print("нет data/authors-contacts.jsonl — реестр адресов собирает стратег")
        return 1

    pairs = set()
    with CONTACTS.open(encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
            except Exception:
                continue
            for e in (d.get("emails") or []):
                k, a = e.get("akey"), norm(e.get("email"))
                if k and a and "@" in a:
                    pairs.add((k, fingerprint(a, key)))

    print(f"отпечатков к заливке: {len(pairs)} "
          f"(авторов: {len({k for k, _ in pairs})})")
    if not args.apply:
        print("ничего не менялось — добавь --apply")
        return 0

    for sql in SCHEMA:
        cs.q(sql)
    have = {(r["akey"], r["h"]) for r in cs.q("SELECT akey, h FROM author_emails")}
    new = sorted(pairs - have)
    print(f"из них новых: {len(new)}")
    for i in range(0, len(new), 120):
        part = new[i:i + 120]
        vals = ",".join(f"({cs.lit(k)},{cs.lit(h)})" for k, h in part)
        cs.q(f"INSERT OR IGNORE INTO author_emails (akey, h) VALUES {vals}")
        print(f"      … {min(i + 120, len(new))}/{len(new)}")
    print(f"\nв облаке отпечатков: {cs.q('SELECT COUNT(*) n FROM author_emails')[0]['n']}")
    print("адресов в облако не уехало ни одного")
    return 0


if __name__ == "__main__":
    sys.exit(main())
