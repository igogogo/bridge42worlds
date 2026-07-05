#!/usr/bin/env python3
"""Переводит справочники (tags.json, scientists.json) с языка по умолчанию
на остальные языки из config.json.

Возобновляемый: результат пишется после каждой пачки, уже переведённые записи
не переводятся повторно. Добавили язык в config.json → просто запустите ещё раз.

Запуск:
    python translate_reference.py        # все языки из config.json
    python translate_reference.py de     # только конкретный язык
"""

import os, sys, json, time, re
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

load_dotenv()
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not API_KEY:
    print("❌ DEEPSEEK_API_KEY not set")
    sys.exit(1)

config = json.loads(Path("config.json").read_text(encoding="utf-8"))
LANGUAGES = config.get("languages", ["ru", "en"])
DEFAULT_LANG = config.get("default_lang", "ru")

LANG_NAMES = {
    "ru": "Russian", "en": "English", "cn": "Chinese", "zh": "Chinese",
    "fr": "French", "de": "German", "es": "Spanish", "it": "Italian",
    "pt": "Portuguese", "ja": "Japanese", "ko": "Korean", "ar": "Arabic",
    "hi": "Hindi", "tr": "Turkish", "pl": "Polish", "nl": "Dutch",
}

client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
SYSTEM_PROMPT = Path("data/prompts/system.txt").read_text(encoding="utf-8")

BATCH = 5  # записей за один запрос (уменьшено из-за трёхуровневых описаний)


def parse_json_salvage(text):
    """json.loads с восстановлением обрезанного ответа."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    last = text.rfind("},")
    if last != -1:
        for tail in ("}}", "]}"):
            try:
                return json.loads(text[:last + 1] + tail)
            except json.JSONDecodeError:
                continue
    return None


def translate_chunk(chunk, lang_name):
    prompt = (
        f"Переведи значения всех текстовых полей этих записей с русского на {lang_name}.\n"
        "СТРОГО сохрани структуру JSON: те же ключи верхнего уровня, те же поля, те же типы.\n"
        "НЕ переводи и НЕ изменяй: ключи объектов, поля id, related_tags, scientists, latex.\n"
        "Имена в поле name переводи так, как это принято в целевом языке.\n\n"
        f"{json.dumps(chunk, ensure_ascii=False)}\n\n"
        'Ответь JSON-объектом: {"items": { ...те же ключи с переведёнными записями... }}'
    )
    r = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        temperature=0.3, max_tokens=16000, response_format={"type": "json_object"}
    )
    data = parse_json_salvage(r.choices[0].message.content)
    if data is None: return {}
    items = data.get("items", data)
    return items if isinstance(items, dict) else {}


targets = [sys.argv[1]] if len(sys.argv) > 1 else [l for l in LANGUAGES if l != DEFAULT_LANG]
print(f"🌐 Перевод справочников: {DEFAULT_LANG} → {', '.join(targets)}")

for fname in ["tags.json", "scientists.json", "laws.json"]:
    src_path = Path(f"lang/{DEFAULT_LANG}/data/{fname}")
    if not src_path.exists():
        print(f"⏭️ {src_path} не найден — пропускаю")
        continue
    source = json.loads(src_path.read_text(encoding="utf-8"))

    for lang in targets:
        lang_name = LANG_NAMES.get(lang, lang)
        out_path = Path(f"lang/{lang}/data/{fname}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        done = {}
        if out_path.exists():
            try:
                done = json.loads(out_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                done = {}
        missing = [k for k in source if k not in done]
        if not missing:
            print(f"✅ {lang}/{fname}: уже полный ({len(done)})")
            continue
        print(f"🌐 {lang}/{fname}: осталось {len(missing)} записей → {lang_name}")

        for i in range(0, len(missing), BATCH):
            chunk = {k: source[k] for k in missing[i:i + BATCH]}
            try:
                items = translate_chunk(chunk, lang_name)
            except Exception as e:
                print(f"   ❌ пачка {i // BATCH + 1}: {e} — пауза 5с")
                time.sleep(5)
                continue
            merged = 0
            for k, v in items.items():
                if k in source:
                    done[k] = v
                    merged += 1
            out_path.write_text(json.dumps(done, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"   +{merged} ({len(done)}/{len(source)})")
            time.sleep(1)

print("🎉 Готово!")
