#!/usr/bin/env python3
"""Повестка совета — на английский. Один рабочий язык вместо половинчатой многоязычности.

Решение владельца 15 августа: «оставляем всё по-английски, комменты можно по-русски или
на любом языке — это прям напиши там, где форма».

Почему так. До этого у совета интерфейс был переведён на пять языков (445 строк), а
содержание — повестка, вопросы, варианты — существовало только по-русски. Араб видел
арабские кнопки и русский текст вопроса: обещание языком оболочки, которого не давали
по существу. Один рабочий язык честнее и дешевле; продукт (статьи) остаётся на пяти.

Переводим ТЕКСТЫ, а не структуру: id вопросов и вариантов не трогаем — по ним считаются
голоса и заморозки, и подмена идентификатора обнулила бы уже поданные голоса.

    python tools/agenda_to_en.py                  перевести ближайшее заседание
    python tools/agenda_to_en.py --dry            показать объём, ничего не тратя
    python tools/agenda_to_en.py --file data/council/2026-08-16.json
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SYSTEM = (
    "You translate the agenda of an observers' council from Russian into English.\n\n"
    "This is a working document for people who will vote on it, not marketing copy. "
    "Keep it plain, concrete and short. Preserve the author's directness: if the Russian "
    "says a метрика doesn't work, the English says it doesn't work.\n\n"
    "Rules:\n"
    "• Translate ONLY the values of the fields given. Never invent, drop or merge items.\n"
    "• Keep numbers, dates, AUC values, money and proper names exactly as they are.\n"
    "• Keep arXiv section codes (astro-ph.CO and the like) untouched.\n"
    "• No em dashes in the English text; use commas, colons or full stops.\n"
    "• Return ONLY JSON of the same shape you received."
)


def translate(payload):
    from common import chat, clean_json
    resp = chat("translate_flash", json.dumps(payload, ensure_ascii=False, indent=1),
                system=SYSTEM)
    return json.loads(clean_json((resp.choices[0].message.content or "").strip()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="data/council/upcoming.json")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    p = ROOT / args.file
    d = json.loads(p.read_text(encoding="utf-8"))
    agenda = d.get("agenda") or []
    if not agenda:
        print("повестка пуста")
        return 1

    # Отдаём модели только тексты, с идентификаторами как якорями.
    payload = {"items": [{
        "id": q.get("id"),
        "title": q.get("title", ""),
        "body": q.get("body", ""),
        "origin": q.get("origin", ""),
        "options": [{"id": o.get("id"), "label": o.get("label", ""), "note": o.get("note", "")}
                    for o in (q.get("options") or []) if isinstance(o, dict)],
    } for q in agenda]}
    chars = len(json.dumps(payload, ensure_ascii=False))
    print(f"вопросов {len(agenda)}, символов {chars}")
    if args.dry:
        return 0

    out = translate(payload)
    by_id = {x.get("id"): x for x in (out.get("items") or [])}
    n = 0
    for q in agenda:
        t = by_id.get(q.get("id"))
        if not t:
            print(f"  ⚠️ {q.get('id')}: перевода нет — оставляю как было")
            continue
        # Русский оригинал сохраняем: он нужен для сверки и для писем тем, кто читает
        # по-русски. Потерять исходник ради перевода — потерять возможность проверить.
        for f in ("title", "body", "origin"):
            if t.get(f):
                q[f + "_ru"] = q.get(f, "")
                q[f] = t[f]
        opts = {o.get("id"): o for o in (t.get("options") or [])}
        for o in (q.get("options") or []):
            src = opts.get(o.get("id"))
            if not src:
                continue
            for f in ("label", "note"):
                if src.get(f):
                    o[f + "_ru"] = o.get(f, "")
                    o[f] = src[f]
        n += 1
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ переведено вопросов: {n} → {p.relative_to(ROOT)}")

    # Файл заседания и upcoming — одно и то же содержимое, держим их в одном состоянии.
    mate = ROOT / "data" / "council" / f"{d.get('date')}.json"
    if mate.exists() and mate != p:
        mate.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"   и {mate.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
