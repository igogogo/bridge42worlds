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

# Тот же публичный ключ, что у страниц сайта: он анонимный и предназначен для чтения
# из браузера. Ничего секретного здесь нет — секретным был бы служебный ключ.
SB_URL = "https://gyfdyfbuolnciaqxgybx.supabase.co/rest/v1"
SB_KEY = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd5ZmR5"
          "ZmJ1b2xuY2lhcXhneWJ4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI3OTk0MzQsImV4cCI6MjA5ODM3NTQzNH0"
          ".rKsgWoj5ubRpkvElPfELOn-G9StW5RSOkxBbpvFyWc4")

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


def sb_get(path):
    req = urllib.request.Request(f"{SB_URL}/{path}",
                                 headers={"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def from_readers(since):
    """Комментарии с сайта. Владелец 2026-07-31: их тоже обрабатываем и вносим
    в повестку отдельным пунктом — это голос тех, кто до совета не дошёл, но написал."""
    try:
        rows = sb_get("feedback?select=comment,created_at,base_id,entity_type"
                      "&comment=not.is.null&order=created_at.desc&limit=200")
    except Exception as e:
        print(f"  ⚠️ комментарии с сайта не прочитались ({type(e).__name__}: {e})")
        return []
    out, skipped = [], []
    for r in rows:
        text = (r.get("comment") or "").strip()
        if since and (r.get("created_at") or "")[:10] < since:
            continue
        # Отсев мусора. Порог по длине и по числу слов: «ууу», «апвп», «test» — это
        # проверки формы, а не мнения. Отсеянное ПЕЧАТАЕМ: тихо выбрасывать чужие слова
        # нельзя, даже если они выглядят ерундой — решать должен человек, а не порог.
        if len(text) < 15 or len(text.split()) < 3:
            skipped.append(text)
            continue
        out.append({"text": text, "role": "читатели", "from": "",
                    "at": (r.get("created_at") or "")[:10],
                    "where": f'{r.get("entity_type","")}: {r.get("base_id","")}'.strip(": ")})
    if skipped:
        print(f"  отсеяно как проверки формы ({len(skipped)}): "
              + " · ".join(repr(x)[:24] for x in skipped[:8]))
        print("  если среди них есть настоящее — добавь руками во входящие")
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
    from common import chat
    payload = {"сколько предложений нужно": count, "уже сделано": done}
    resp = chat("translate_flash", json.dumps(payload, ensure_ascii=False, indent=1),
                system=MODEL_SYSTEM)
    text = (resp.choices[0].message.content or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    data = json.loads(text)
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

    readers = [r for r in from_readers(since) if r["text"] not in seen]
    print(f"комментариев с сайта: {len(readers)}")
    for r in readers:
        print(f'  · [{r["where"]}] {r["text"][:70]}')

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
