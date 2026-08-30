#!/usr/bin/env python3
"""Названия и пояснения областей понятий — на все языки проекта.

Пятьдесят областей (data/group-names.json) написаны машиной по составу каждой
группы: «Квантовая информатика», «Гидродинамика и турбулентность». Хранились они
парой name_ru/name_en, и это видно читателю сразу: испанец открывает /concepts/,
видит заголовок «Conceptos» — и под ним пятьдесят английских названий. Код при
этом ни при чём: страницы давно спрашивают name_{lang} и лишь откатываются на
английский. Не хватало данных.

Перевод берём общим путём: тот же chat, та же модель перевода справочников, тот
же список языков из config.json. Своего переводчика здесь заводить нельзя —
их у нас и так больше, чем нужно.

Возобновляемый: язык, который уже переведён, пропускается. Добавили язык в
config.json — просто запустите ещё раз.

    python tools/group_names_translate.py --check   чего не хватает (бесплатно)
    python tools/group_names_translate.py           перевести недостающее
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from common import ALL_LANGS, chat, clean_json          # noqa: E402

SRC = ROOT / "data" / "group-names.json"
# Русский — исходник, английский написан вместе с ним.
BASE = ("ru", "en")
BATCH = 10          # областей в одном запросе: короткие тексты, длинный ответ не нужен

LANG_NAME = {"es": "Spanish", "ar": "Arabic", "fr": "French", "zh": "Chinese",
             "de": "German", "it": "Italian", "pt": "Portuguese"}


def missing(data, lang):
    """Области, у которых нет имени на этом языке."""
    return [k for k, v in data.items() if not (v.get(f"name_{lang}") or "").strip()]


def translate(data, keys, lang):
    """Пачка областей на один язык. Возвращает {ключ: (имя, пояснение)}."""
    items = []
    for k in keys:
        v = data[k]
        items.append({"id": k,
                      "name": v.get("name_en") or v.get("name_ru") or k,
                      "note": v.get("note_en") or v.get("note_ru") or ""})
    target = LANG_NAME.get(lang, lang)
    prompt = (
        f"Переведи на {target} названия и пояснения областей физики.\n\n"
        "ПРАВИЛА:\n"
        "1. Название области — это термин, а не фраза: переводи так, как эту область\n"
        "   называют в научной литературе на этом языке, а не буквально.\n"
        "2. Пояснение — одно-два предложения, тот же смысл и та же длина.\n"
        "3. Ничего не добавляй от себя и не сокращай. Имена собственные и\n"
        "   общепринятые латинские сокращения оставляй как есть.\n"
        "4. Ответ — только JSON, без пояснений вокруг.\n\n"
        f"ОБЛАСТИ:\n{json.dumps(items, ensure_ascii=False, indent=1)}\n\n"
        'Ответь: {"items": [{"id": "...", "name": "...", "note": "..."}]}'
    )
    r = chat("translate_ref", prompt,
             system="Ты научный переводчик. Переводишь термины так, как их "
                    "называют в литературе на языке перевода.")
    got = json.loads(clean_json(r.choices[0].message.content))
    out = {}
    for x in got.get("items") or []:
        i = str(x.get("id") or "")
        if i in data and (x.get("name") or "").strip():
            out[i] = (x["name"].strip(), (x.get("note") or "").strip())
    return out


def main():
    ap = argparse.ArgumentParser(description="Перевод названий областей понятий")
    ap.add_argument("--check", action="store_true", help="только посчитать, ничего не звать")
    ap.add_argument("--lang", help="только этот язык")
    a = ap.parse_args()

    if not SRC.exists():
        print("data/group-names.json нет — сначала tools/group_names.py --run")
        return 1
    data = json.loads(SRC.read_text(encoding="utf-8"))
    langs = [a.lang] if a.lang else [l for l in ALL_LANGS if l not in BASE]

    plan = {l: missing(data, l) for l in langs}
    for l in langs:
        print(f"{l}: без названия {len(plan[l])} из {len(data)}")
    if a.check:
        return 0

    total = 0
    for l in langs:
        keys = plan[l]
        for i in range(0, len(keys), BATCH):
            chunk = keys[i:i + BATCH]
            try:
                got = translate(data, chunk, l)
            except Exception as ex:
                print(f"  {l}: пачка не сошлась — {type(ex).__name__}: {ex}")
                continue
            for k, (name, note) in got.items():
                data[k][f"name_{l}"] = name
                if note:
                    data[k][f"note_{l}"] = note
                total += 1
            # Пишем после каждой пачки: прогон можно оборвать и продолжить.
            SRC.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                           encoding="utf-8")
            print(f"  {l}: {min(i + BATCH, len(keys))}/{len(keys)}", flush=True)
    print(f"✅ переведено областей: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
