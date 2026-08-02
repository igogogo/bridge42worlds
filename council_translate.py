#!/usr/bin/env python3
"""Перевод строк страницы «изнутри» на языки сайта.

Переводим СТРОКИ, а не разметку: модель, переводя html, рано или поздно съедает
закрывающий тег или переводит имя класса, и страница разъезжается молча. Здесь ей
достаются только тексты, а разметку собирает council_page.py.

Возобновляемо: уже переведённые ключи не трогаем, прерванный прогон просто повторить.

Запуск:
    python council_translate.py            # все языки конфига, чего нет
    python council_translate.py ar         # только арабский
    python council_translate.py ar --dry   # объём, без трат
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "data" / "council"
BASE = SRC / "страница.ru.json"
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
LANGS = [l for l in CONFIG.get("languages", ["ru"]) if l != "ru"]
BATCH = 30

NAME = {"en": "English", "es": "español", "ar": "العربية", "fr": "français",
        "zh": "中文", "de": "Deutsch"}

SYSTEM_TPL = """Ты переводишь интерфейс и текст страницы научно-популярного проекта
bridge42worlds на {name}.

ЖЁСТКИЕ ТРЕБОВАНИЯ:
- Отвечай ТОЛЬКО валидным JSON-объектом: те же ключи, переведённые значения.
- Ключи НЕ переводить и не менять.
- Разметку внутри значений (<b>, </b>) сохранять ровно как есть, на своих местах.
- Числа, суммы, знаки валют и названия ($0,06–0,09, 2110, arXiv, bridge42worlds)
  оставлять как есть. Десятичный разделитель приводи к принятому в языке.
- Тон: спокойный, уважительный к читателю, без канцелярита и рекламных слов.
  Это документ для людей, которых зовут в наблюдательный совет, а не листовка.
- Ничего не добавлять и не пропускать: сколько ключей пришло, столько вернуть.
- Никакого текста вне JSON."""


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    targets = args or LANGS
    base = json.loads(BASE.read_text(encoding="utf-8"))
    print(f"строк в источнике: {len(base)}")

    chat = None
    if not dry:
        from common import chat as _chat
        chat = _chat

    for lang in targets:
        out = SRC / f"страница.{lang}.json"
        have = {}
        if out.exists():
            try:
                have = json.loads(out.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                print(f"{lang}: файл битый, начинаю заново")
        missing = {k: v for k, v in base.items() if k not in have}
        print(f"\n{lang}: не хватает {len(missing)} из {len(base)}")
        if not missing or dry:
            continue

        keys = list(missing)
        for i in range(0, len(keys), BATCH):
            chunk = {k: missing[k] for k in keys[i:i + BATCH]}
            resp = chat("translate_flash",
                        json.dumps(chunk, ensure_ascii=False, indent=1),
                        system=SYSTEM_TPL.format(name=NAME.get(lang, lang)))
            text = (resp.choices[0].message.content or "").strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            try:
                got = json.loads(text)
            except json.JSONDecodeError:
                print(f"    ⚠️ пачка не разобралась ({len(chunk)} ключей) — повтори прогон")
                continue
            # Берём только то, что просили: лишние ключи — выдумка модели.
            good = {k: v for k, v in got.items() if k in chunk and isinstance(v, str) and v.strip()}
            # Разметка обязана уцелеть: если в источнике был <b>, а в переводе нет —
            # значение не принимаем, иначе страница молча потеряет выделение.
            for k in list(good):
                if base[k].count("<b>") != good[k].count("<b>"):
                    print(f"    ⚠️ {k}: потеряна разметка — ключ пропущен, будет по-русски")
                    del good[k]
            have.update(good)
            out.write_text(json.dumps(have, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"    +{len(good)} (всего {len(have)}/{len(base)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
