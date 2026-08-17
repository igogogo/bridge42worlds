"""Дайджест в Telegram: несколько статей с обложками, картинкой и ссылкой.

Владелец 2026-08-04: «положи в нашу ленту что-нибудь новенькое, самое интересное. Может,
создать отдельный канал и туда по три-пять статей с картинками — начать вести аккуратно».

Почему инструментом, а не руками: канал живёт ритмом. Пост раз в неделю «когда вспомнили»
читателя не удерживает, а ручная публикация всегда кончается тем, что её перестают делать.
Здесь публикация — команда, которую можно поставить в планировщик.

    python tools/tg_digest.py --dry            показать, что уйдёт, ничего не отправляя
    python tools/tg_digest.py --n 3            три свежие статьи с обложками
    python tools/tg_digest.py --pick ID ID     конкретные статьи
    python tools/tg_digest.py --chat @канал    в другой канал (по умолчанию — наш служебный)

Отбор: свежие статьи, у которых ЕСТЬ обложка и текст карточки. Пост без картинки в ленте
пролистывают не читая — это не про красоту, а про то, увидят ли работу вообще.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import requests

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

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


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def candidates(n, pick=None):
    idx = json.loads((ROOT / "lang/ru/articles-index.json").read_text(encoding="utf-8"))
    seen, out = set(), []
    for a in sorted(idx, key=lambda x: x["date"], reverse=True):
        if a.get("version") != "popular" or a["id"] in seen:
            continue
        seen.add(a["id"])
        if pick and a["id"] not in pick:
            continue
        cover = ROOT / "lang/ru/archive" / a["date"] / a["id"] / "ai.webp"
        if not cover.exists() or not (a.get("description") or "").strip():
            continue
        url = SITE + (a.get("url") or "").replace("/index.html", "/")
        # Ссылка обязана отвечать 200 ДО публикации. Владелец 17 августа: «нажимаю
        # на ссылку — 404». Причина: фабрика сгенерировала статьи в 13:00, выкладки
        # после них не было, а дайджест в 18:00 взял свежайшее из ЛОКАЛЬНОГО индекса
        # и разослал ссылки на страницы, которых на сайте ещё нет. Локальный диск и
        # прод — разные миры; пост в канал — это обещание читателю, и давать его можно
        # только про то, что уже опубликовано. Не отвечает — берём следующую статью.
        try:
            import requests as _rq
            if _rq.head(url, timeout=15, allow_redirects=True).status_code != 200:
                print(f"  ⏭️ {a['id']}: на сайте ещё нет ({url}) — пропускаю")
                continue
        except Exception:
            print(f"  ⏭️ {a['id']}: сайт не ответил — пропускаю")
            continue
        out.append({"id": a["id"], "date": a["date"], "title": a["title"],
                    "text": a["description"], "cover": cover, "url": url})
        if len(out) >= n:
            break
    return out


def post(token, chat, art, dry=False):
    # Подпись: заголовок, живой текст карточки, ссылка. Без хэштегов-простыней и без
    # «читайте далее» — текст карточки и так писался как приглашение, дублировать его
    # призывом значит не доверять собственному тексту.
    cap = (f"<b>{esc(art['title'])}</b>\n\n{esc(art['text'])}\n\n"
           f"<a href=\"{art['url']}\">Читать целиком →</a>")
    if len(cap) > 1024:                      # предел подписи к фото в Telegram
        cut = cap.rfind(". ", 0, 900)
        cap = cap[:cut + 1] + f"\n\n<a href=\"{art['url']}\">Читать целиком →</a>"
    if dry:
        print(f"\n─── {art['id']} ({art['date']}) ───\n{cap}\n[обложка: {art['cover'].name}]")
        return True
    with art["cover"].open("rb") as f:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendPhoto", timeout=60,
                          data={"chat_id": chat, "caption": cap, "parse_mode": "HTML"},
                          files={"photo": f})
    if r.status_code == 200:
        print(f"✅ {art['id']} · {art['title'][:50]}")
        return True
    print(f"❌ {art['id']}: {r.status_code} {r.text[:160]}")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--pick", nargs="*")
    ap.add_argument("--chat")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    e = env()
    token = e.get("TG_BOT_TOKEN")
    chat = args.chat or e.get("TG_CHANNEL_ID") or e.get("TG_CHAT_ID")
    if not args.dry and not (token and chat):
        print("нет TG_BOT_TOKEN / TG_CHAT_ID в .env")
        return 1

    arts = candidates(args.n, set(args.pick) if args.pick else None)
    if not arts:
        print("нечего публиковать: нет свежих статей с обложкой и текстом карточки")
        return 1
    ok = sum(1 for a in arts if post(token, chat, a, args.dry))
    print(f"\n{'показано' if args.dry else 'опубликовано'}: {ok} из {len(arts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
