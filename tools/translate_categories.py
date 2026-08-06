#!/usr/bin/env python3
"""Названия и описания разделов arXiv на языки сайта.

Зачем скрипт, а не разовый прогон. Файлы data/arxiv-categories-<язык>.json и
data/arxiv-category-descriptions-<язык>.json были сделаны один раз руками для ru/es/ar.
Когда появился пятый язык, никто про них не вспомнил — француз получал английские
названия разделов, а js на каждой французской странице ходил за несуществующим файлом
и ловил 404. Ровно та же болезнь, что с хардкодом списка языков: разовая работа,
которую нельзя повторить командой, обязательно отстанет.

Источники: data/arxiv-taxonomy-en.json (155 разделов, имена) и
data/arxiv-category-descriptions.json (описания, их меньше — только основные).
Возобновляемо: уже переведённые ключи не трогаем, так что прерванный прогон
можно просто повторить.

Запуск:
    python tools/translate_categories.py            # все языки из config.json, чего нет
    python tools/translate_categories.py fr         # только французский
    python tools/translate_categories.py fr --dry   # показать объём, не тратя денег
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
LANGS = CONFIG.get("languages", ["ru"])
SOURCE_LANG = "en"          # база и есть английская — её не переводим
BATCH = 40                  # ключей за один вызов: длинные описания в один запрос не влезут

LANG_NAME = {"ru": "русском", "es": "испанском", "ar": "арабском", "fr": "французском",
             "zh": "китайском", "de": "немецком", "pt": "португальском"}


def _load(path, default=None):
    p = DATA / path
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {} if default is None else default


def _system(lang):
    name = LANG_NAME.get(lang, lang)
    return (
        f"Ты переводишь названия и описания разделов научного архива arXiv на {name} язык.\n"
        f"ЖЁСТКИЕ ТРЕБОВАНИЯ:\n"
        f"- Отвечай ТОЛЬКО валидным JSON-объектом: те же ключи, переведённые значения.\n"
        f"- Ключи (astro-ph.CO, cs.AI и т.п.) НЕ переводить и не менять.\n"
        f"- Термины физики и математики переводить принятыми в языке терминами, "
        f"а не буквально; общепринятые латинские сокращения оставлять как есть.\n"
        f"- Ничего не добавлять и не пропускать: сколько ключей пришло, столько вернуть.\n"
        f"- Никакого текста вне JSON."
    )


def translate_chunk(chunk, lang, chat):
    # translate_flash, а не translate: названия разделов — короткие термины, дорогая
    # модель тут ничего не добавляет (та же логика, что у slim-перевода тиров).
    resp = chat("translate_flash", json.dumps(chunk, ensure_ascii=False, indent=1),
                system=_system(lang))
    # chat() возвращает ответ целиком (объект SDK), а не строку — текст лежит внутри.
    text = (resp.choices[0].message.content or "").strip()
    try:
        out = json.loads(clean_json(text))
    except json.JSONDecodeError:
        print(f"    ⚠️ модель вернула не JSON — пропускаю пачку из {len(chunk)}")
        return {}
    # Берём только те ключи, что просили: лишнее — выдумка модели.
    return {k: v for k, v in out.items() if k in chunk and isinstance(v, str) and v.strip()}


def fill(src, out_name, lang, dry, chat):
    have = _load(out_name)
    missing = {k: v for k, v in src.items() if k not in have}
    if not missing:
        print(f"  {out_name}: полон ({len(have)})")
        return 0
    print(f"  {out_name}: не хватает {len(missing)} из {len(src)}")
    if dry:
        return len(missing)
    keys = list(missing)
    for i in range(0, len(keys), BATCH):
        chunk = {k: missing[k] for k in keys[i:i + BATCH]}
        got = translate_chunk(chunk, lang, chat)
        have.update(got)
        (DATA / out_name).write_text(json.dumps(have, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
        print(f"    +{len(got)} (всего {len(have)})")
    return len(missing)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    targets = args or [l for l in LANGS if l != SOURCE_LANG]

    names = _load("arxiv-taxonomy-en.json")
    descs = _load("arxiv-category-descriptions.json")
    if not names:
        print("нет data/arxiv-taxonomy-en.json — переводить нечего")
        return 1
    print(f"источник: {len(names)} названий, {len(descs)} описаний")

    chat = None
    if not dry:
        from common import chat as _chat, clean_json
        chat = _chat

    total = 0
    for lang in targets:
        if lang == SOURCE_LANG:
            continue
        print(f"\n{lang}:")
        total += fill(names, f"arxiv-categories-{lang}.json", lang, dry, chat)
        total += fill(descs, f"arxiv-category-descriptions-{lang}.json", lang, dry, chat)
    print(f"\n{'нужно перевести' if dry else 'переведено'} ключей: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
