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
# Импорт common работает из любой папки, а не только из корня репозитория.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
from common import ALL_LANGS  # noqa: E402
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


POSTED = ROOT / "data" / "digest-posted.json"


def load_posted():
    """Что уже уходило в канал. Владелец 2026-08-24: «в каналы сыпятся одни и те же
    статьи уже третий раз».

    Причина была в том, что памяти не существовало вовсе: набор seen жил внутри одного
    запуска и защищал только от дубля в пределах одного поста. Каждый вечер дайджест
    брал три самые свежие статьи с обложкой — и пока поток стоял, это были одни и те же
    три. Теперь опубликованное помнится по каналам и языкам."""
    if not POSTED.exists():
        return {}
    try:
        return json.loads(POSTED.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_posted(state):
    POSTED.parent.mkdir(parents=True, exist_ok=True)
    tmp = POSTED.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(POSTED)


def candidates(n, pick=None, lang="ru", already=()):
    idx = json.loads((ROOT / f"lang/{lang}/articles-index.json").read_text(encoding="utf-8"))
    seen, out = set(), []
    for a in sorted(idx, key=lambda x: x["date"], reverse=True):
        if a.get("version") != "popular" or a["id"] in seen:
            continue
        seen.add(a["id"])
        # Уже публиковали — пропускаем. Исключение: явный --pick, когда человек
        # сознательно просит повторить конкретную работу.
        if not pick and a["id"] in already:
            continue
        if pick and a["id"] not in pick:
            continue
        cover = ROOT / "lang/ru/archive" / a["date"] / a["id"] / "ai.webp"  # обложки живут у ru
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
        # Лицензия исходной работы — в подпись поста (владелец 18.08: «в канале тоже
        # должна быть ссылка на лицензию»). Пост — та же публикация, что и страница:
        # атрибуция и ссылка на условия должны ехать вместе с контентом, а не
        # оставаться только на сайте.
        lic_url, lic_name = "", ""
        dj = ROOT / f"lang/{lang}/archive" / a["date"] / a["id"] / "data.json"
        try:
            d = json.loads(dj.read_text(encoding="utf-8"))
            lic_url = d.get("license") or d.get("license_url") or ""
            lic_name = d.get("license_name") or ""
        except Exception:
            pass
        out.append({"id": a["id"], "date": a["date"], "title": a["title"],
                    "text": a["description"], "cover": cover, "url": url,
                    "lic_url": lic_url, "lic_name": lic_name})
        if len(out) >= n:
            break
    return out


LINK_TEXT = {"ru": "Читать целиком →", "en": "Read the full story →",
             "ar": "اقرأ المقال كاملاً ←", "es": "Leer completo →", "fr": "Lire en entier →"}


def post(token, chat, art, dry=False, lang="ru"):
    # Подпись: заголовок, живой текст карточки, ссылка. Без хэштегов-простыней и без
    # «читайте далее» — текст карточки и так писался как приглашение, дублировать его
    # призывом значит не доверять собственному тексту.
    link = LINK_TEXT.get(lang, LINK_TEXT["ru"])
    # Строка атрибуции: наш пересказ — производная работа, ссылка на оригинал и его
    # лицензию обязана ехать в каждом посте, а не оставаться только на сайте.
    src = f"arXiv:{art['id']}"
    lic = (f" · <a href=\"{art['lic_url']}\">{esc(art['lic_name'] or 'license')}</a>"
           if art.get("lic_url") else "")
    tail = (f"\n\n<a href=\"{art['url']}\">{link}</a>\n"
            f"<a href=\"https://arxiv.org/abs/{art['id']}\">{src}</a>{lic}")
    cap = f"<b>{esc(art['title'])}</b>\n\n{esc(art['text'])}" + tail
    if len(cap) > 1024:                      # предел подписи к фото в Telegram
        cut = cap.rfind(". ", 0, 1000 - len(tail))
        cap = cap[:cut + 1] + tail
    if dry:
        print(f"\n─── {art['id']} ({art['date']}) ───\n{cap}\n[обложка: {art['cover'].name}]")
        return True
    # Общий выключатель канала (tools/tg_silence.py) — владелец 25 августа.
    try:
        import sys as _s
        from pathlib import Path as _P
        _r = str(_P(__file__).resolve().parent.parent)
        if _r not in _s.path:
            _s.path.insert(0, _r)
        from tools.tg_silence import guard as _guard
        if _guard(art["title"]):
            return True
    except ImportError:
        pass
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
    # Язык дайджеста: канал @bridge42worlds_en завёл владелец 18.08. Индексы и тексты
    # карточек уже существуют на пяти языках, поэтому второй канал — это параметр,
    # а не вторая система. Ссылка ведёт на страницу того же языка.
    ap.add_argument("--lang", default="ru", choices=ALL_LANGS)
    args = ap.parse_args()

    e = env()
    token = e.get("TG_BOT_TOKEN")
    chat = args.chat or e.get("TG_CHANNEL_ID") or e.get("TG_CHAT_ID")
    if not args.dry and not (token and chat):
        print("нет TG_BOT_TOKEN / TG_CHAT_ID в .env")
        return 1

    # Ключ памяти — канал плюс язык: у русского и английского каналов свои очереди,
    # и одна работа законно уходит в оба, но в каждый по одному разу.
    state = load_posted()
    key = f"{chat or 'dry'}|{args.lang}"
    already = set(state.get(key, []))

    arts = candidates(args.n, set(args.pick) if args.pick else None,
                      lang=args.lang, already=already)
    if not arts:
        print("нечего публиковать: новых статей с обложкой и текстом карточки нет "
              f"(уже опубликовано за всё время: {len(already)})")
        return 1
    sent = []
    for a in arts:
        if post(token, chat, a, args.dry, lang=args.lang):
            sent.append(a["id"])
    # Запоминаем только то, что РЕАЛЬНО ушло: сухой прогон и неудачные отправки память
    # не портят, иначе одна ошибка Telegram навсегда похоронила бы статью.
    if sent and not args.dry:
        state[key] = sorted(already | set(sent))
        save_posted(state)
    ok = len(sent)
    print(f"\n{'показано' if args.dry else 'опубликовано'}: {ok} из {len(arts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
