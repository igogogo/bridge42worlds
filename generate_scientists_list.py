#!/usr/bin/env python3
"""Генерирует список учёных с привязкой к тегам.

Крутится, пока не соберёт TOTAL_SCIENTISTS уникальных: каждой пачке передаётся
список уже собранных имён («не повторяй»), обрезанный JSON восстанавливается
до последнего полного объекта.
"""

import os, json, time, random, re
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not DEEPSEEK_API_KEY:
    print("❌ DEEPSEEK_API_KEY not set")
    exit(1)

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

SYSTEM_PROMPT = Path("data/prompts/system.txt").read_text(encoding="utf-8")

# ── НАСТРОЙКИ (из config.json → "scientists") ──
_SCFG = json.loads(Path("config.json").read_text(encoding="utf-8")).get("scientists", {})
TOTAL_SCIENTISTS = _SCFG.get("total", 100)         # сколько всего учёных нужно
PER_REQUEST = _SCFG.get("per_request", 5)          # сколько учёных за один запрос к API
MAX_REQUESTS = _SCFG.get("max_requests", 80)       # предохранитель от бесконечного цикла
SAMPLE_TAGS = _SCFG.get("sample_tags", 20)         # сколько случайных тегов подмешивать в запрос
# ─────────────────

TAGS_PATH = Path("lang/ru/data/tags-list.json")
if not TAGS_PATH.exists():
    print("❌ lang/ru/data/tags-list.json not found.")
    exit(1)

tags = json.loads(TAGS_PATH.read_text(encoding="utf-8"))
all_en = [t["en"] for t in tags]

Path("temp").mkdir(exist_ok=True)

print(f"👨‍🔬 Bridge For Two Worlds — генератор учёных")
print(f"   Всего нужно: {TOTAL_SCIENTISTS}")
print(f"   За запрос: {PER_REQUEST}")


def parse_json_salvage(text):
    """json.loads с восстановлением обрезанного ответа: срезаем до последнего полного объекта."""
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
        for tail in ("]}", "]"):
            try:
                return json.loads(text[:last + 1] + tail)
            except json.JSONDecodeError:
                continue
    return None


collected = {}  # id -> данные учёного (порядок вставки сохраняется)

# Возобновление: подхватываем уже собранных из прошлого запуска
EXISTING = Path("lang/ru/data/scientists.json")
if EXISTING.exists():
    try:
        for sid, s in json.loads(EXISTING.read_text(encoding="utf-8")).items():
            collected[sid] = {**s, "id": sid}
        print(f"   Продолжаем: уже есть {len(collected)}")
    except json.JSONDecodeError:
        pass

request_num = 0

while len(collected) < TOTAL_SCIENTISTS and request_num < MAX_REQUESTS:
    request_num += 1
    need = min(PER_REQUEST, TOTAL_SCIENTISTS - len(collected))
    sample_tags = random.sample(all_en, min(SAMPLE_TAGS, len(all_en)))
    tags_str = ", ".join(sample_tags)
    exclusion = ""
    if collected:
        exclusion = "\n\nЭти учёные УЖЕ ЕСТЬ в списке — НЕ включай их снова: " + ", ".join(collected.keys())

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Создай мини-биографии {need} великих учёных связанных с этими тегами: {tags_str}\n\n"
                        "Я конечно уважаю Эйнштейна и Ньютона но не надо забывать о Пуанкаре, Лоренце и Гуке, "
                        "которые на самом деле давали идеи. Делай упор на физиков, которые действительно шли "
                        "по своему пути — типа Сюдзи Накамуры, который придумал синий лазер. Люблю такие истории.\n\n"
                        "Для каждого укажи:\n"
                        "- id: имя на английском (оригинал, не переводи)\n"
                        "- name: имя на русском\n"
                        "- lifespan: годы жизни\n"
                        "- description: развёрнутое описание вклада (4-6 предложений на русском)\n"
                        "- biography: краткая биография — где учился, где работал (2-3 предложения)\n"
                        "- key_discoveries: 2-3 ключевых открытия с пояснениями (на русском)\n"
                        "- fields: 2-3 области науки (на русском)\n"
                        f"- related_tags: 2-3 английских id ТОЛЬКО из этого списка: {tags_str}\n"
                        "- quote: известные цитаты (на русском)\n"
                        "- fun_fact: интересные факты (на русском)\n"
                        f"{exclusion}\n\n"
                        'Ответь JSON-объектом:\n'
                        '{"scientists": [{"id": "Isaac Newton", ...}]}'
                    )
                }
            ],
            temperature=0.5,
            max_tokens=5000,
            response_format={"type": "json_object"}
        )
    except Exception as e:
        print(f"  ⚠️ Запрос {request_num}: ошибка API: {e} — пауза 5с и продолжаем")
        time.sleep(5)
        continue

    result = response.choices[0].message.content.strip()
    data = parse_json_salvage(result)
    if data is None:
        print(f"  ❌ Запрос {request_num}: JSON не разобран (сохранил в temp/debug_scientists_{request_num}.txt)")
        Path(f"temp/debug_scientists_{request_num}.txt").write_text(result, encoding="utf-8")
        continue

    batch = data.get("scientists", []) if isinstance(data, dict) else data
    added = 0
    for s in batch:
        sid = (s.get("id") or "").strip()
        if sid and sid not in collected:
            collected[sid] = s
            added += 1
    print(f"  ✅ Запрос {request_num}: +{added} новых (всего {len(collected)}/{TOTAL_SCIENTISTS})")
    if len(collected) < TOTAL_SCIENTISTS:
        time.sleep(1)

# Сохраняем
scientists_dict = {}
for sid, s in list(collected.items())[:TOTAL_SCIENTISTS]:
    scientists_dict[sid] = {
        "name": s.get("name", sid),
        "lifespan": s.get("lifespan", ""),
        "description": s.get("description", ""),
        "biography": s.get("biography", ""),
        "key_discoveries": s.get("key_discoveries", []),
        "fields": s.get("fields", []),
        "quote": s.get("quote", ""),
        "fun_fact": s.get("fun_fact", ""),
        "related_tags": s.get("related_tags", [])
    }

Path("lang/ru/data").mkdir(parents=True, exist_ok=True)
Path("lang/ru/data/scientists.json").write_text(
    json.dumps(scientists_dict, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"✅ lang/ru/data/scientists.json: {len(scientists_dict)} учёных")
if len(scientists_dict) < TOTAL_SCIENTISTS:
    print(f"⚠️ Собрано меньше цели ({len(scientists_dict)}/{TOTAL_SCIENTISTS}) — просто перезапустите скрипт")
