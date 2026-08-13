#!/usr/bin/env python3
"""Лёгкие справочники для браузера: только то, что читатель реально видит.

Замер 13 августа, что качается при заходе на главную:

    lang/ru/articles-index-advanced.json   11.0 МБ
    lang/ru/articles-index.json             9.9 МБ
    lang/ru/articles-index-simple.json      9.0 МБ
    lang/ru/data/tags.json                  4.5 МБ
    lang/ru/data/scientists.json            0.6 МБ
                                         ─────────
                                          ~34 МБ

Владелец 13 августа: «что у нас тормозит для индекса реализации, там расходы вырастут?
У нас пользователей сейчас немного». Расходы не вырастут — Workers Paid уже оплачен и его
норма на три порядка больше нашего трафика. Тормозило другое: страница читает справочники
ЦЕЛИКОМ, хотя показывает из них одно-два поля.

Из tags.json браузер берёт `name` и одно описание для подсказки — остальные двадцать полей
(история, как работает, формулы, сырьё для генерации, промпты картинок) нужны СТРАНИЦЕ
тега, а не ленте. Отсюда файл на 4.5 МБ ради 368 названий.

Здесь мы готовим `*-lite.json`: имя, тип и описание, обрезанное до размера подсказки.
Полные справочники остаются на месте — страницы тегов и законов читают их как раньше.

    python tools/lite_refs.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANGS = ("ru", "en", "es", "ar", "fr")
TIP = 260          # столько знаков влезает в подсказку; остальное всё равно обрезается


def lite_tags(d):
    out = {}
    for k, v in d.items():
        if not isinstance(v, dict):
            continue
        row = {"name": v.get("name", k)}
        for f in ("description_popular", "description_simple", "description"):
            s = (v.get(f) or "").strip()
            if s:
                row[f] = s[:TIP]
        out[k] = row
    return out


def lite_laws(d):
    out = {}
    for k, v in d.items():
        if not isinstance(v, dict):
            continue
        row = {"name": v.get("name", k)}
        if v.get("type"):
            row["type"] = v["type"]
        for f in ("description_popular", "description_simple", "description"):
            s = (v.get(f) or "").strip()
            if s:
                row[f] = s[:TIP]
        out[k] = row
    return out


def lite_sci(d):
    out = {}
    for k, v in d.items():
        if not isinstance(v, dict):
            continue
        row = {"name": v.get("name", k)}
        for f in ("lifespan", "description"):
            s = (v.get(f) or "").strip()
            if s:
                row[f] = s[:TIP] if f == "description" else s
        out[k] = row
    return out


MAKERS = {"tags.json": lite_tags, "laws.json": lite_laws, "scientists.json": lite_sci}


def main():
    saved = 0
    for lang in LANGS:
        for name, fn in MAKERS.items():
            src = ROOT / "lang" / lang / "data" / name
            if not src.exists():
                continue
            try:
                d = json.loads(src.read_text(encoding="utf-8"))
            except Exception as ex:
                print(f"  ⚠️ {lang}/{name}: {type(ex).__name__}")
                continue
            out = fn(d)
            dst = src.with_name(name.replace(".json", "-lite.json"))
            dst.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
            was, now = src.stat().st_size, dst.stat().st_size
            saved += was - now
            print(f"  {lang}/{dst.name}: {was/1e6:.2f} → {now/1e6:.2f} МБ")
    print(f"✅ экономия на одном заходе: {saved/1e6/len(LANGS):.1f} МБ "
          f"(суммарно по языкам {saved/1e6:.1f} МБ)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
