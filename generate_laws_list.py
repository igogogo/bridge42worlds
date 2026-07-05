#!/usr/bin/env python3
"""Реестр законов/принципов/теорем/эффектов для Bridge For Two Worlds.

Закон — сущность-зонтик (type: закон | принцип | теорема | эффект | уравнение).
«Законы для тегов — то же, что теги для статей»: каждый закон привязан к тегам-понятиям.
Формула — лишь отображение закона (генерится позже в generate_laws.py), поэтому здесь
только имя + тип + связанные теги.

Количество и пачки — из config.json → "laws". → lang/ru/data/laws-list.json
Генерится пачками параллельно, с дедупом и исключением уже собранных.
"""

import os, sys, json, re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from openai import OpenAI

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

load_dotenv()
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not DEEPSEEK_API_KEY:
    print("❌ DEEPSEEK_API_KEY not set")
    exit(1)

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
SYSTEM_PROMPT = Path("data/prompts/system.txt").read_text(encoding="utf-8")

CFG = json.loads(Path("config.json").read_text(encoding="utf-8")).get("laws", {})
COUNT = CFG.get("count", 50)
LIST_BATCH = CFG.get("list_batch", 40)
WORKERS = CFG.get("workers", 5)

LAWS_PATH = Path("lang/ru/data/laws-list.json")
ACTIVE_TAGS = Path("lang/ru/data/tags-list.json")
EDU_TAGS = Path("lang/ru/data/tags-list-educational.json")


def slugify(s):
    s = s.strip().lower()
    s = re.sub(r"[\s_]+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    return s


def normalize_ids(laws, seen_ids):
    out = []
    for law in laws:
        slug = slugify(law.get("en", ""))
        if not slug:
            continue
        if slug in seen_ids:
            i = 2
            while f"{slug}_{i}" in seen_ids:
                i += 1
            slug = f"{slug}_{i}"
        seen_ids.add(slug)
        law["en"] = slug
        out.append(law)
    return out


def load_tag_ids():
    ids = []
    for p in (ACTIVE_TAGS, EDU_TAGS):
        if p.exists():
            ids += [t["en"] for t in json.loads(p.read_text(encoding="utf-8"))]
    return ids


def gen_batch(need, tag_ids, exclude):
    excl = ", ".join(sorted(exclude)[:300])
    try:
        r = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"Составь список из {need} ФУНДАМЕНТАЛЬНЫХ законов, принципов, теорем и эффектов "
                    "физики, астрономии и математики — тех, что образуют каркас науки и достойны отдельной "
                    "образовательной карточки с формулой.\n\n"
                    "Для каждого укажи:\n"
                    "- ru: русское название (напр. «Закон всемирного тяготения», «Принцип неопределённости», "
                    "«Теорема Нётер», «Эффект Доплера»)\n"
                    "- en: английский ID (слова через пробел, нижний регистр)\n"
                    "- type: закон | принцип | теорема | эффект | уравнение\n"
                    "- tags: 2-5 английских id понятий, к которым относится закон, ТОЛЬКО из списка ниже\n\n"
                    "Охватывай: механику, гравитацию, термодинамику, электродинамику, оптику, "
                    "квантовую механику, физику частиц, теорию относительности, космологию, "
                    "статистическую физику; ключевые математические теоремы, используемые в физике.\n\n"
                    f"Доступные id тегов (используй ТОЛЬКО их в поле tags):\n{', '.join(tag_ids)}\n\n"
                    + (f"НЕ включай уже собранные: {excl}\n\n" if exclude else "")
                    + "Ответь JSON-объектом:\n"
                    '{"laws": [{"ru": "Закон всемирного тяготения", "en": "law of universal gravitation", '
                    '"type": "закон", "tags": ["gravity", "mass"]}, ...]}'
                )}
            ],
            temperature=0.5, max_tokens=6000, response_format={"type": "json_object"}
        )
        return json.loads(r.choices[0].message.content.strip()).get("laws", [])
    except Exception as e:
        print(f"    ⚠️ пачка законов: ошибка {e}")
        return []


def main():
    tag_ids = load_tag_ids()
    if not tag_ids:
        print("❌ нет tags-list.json — сначала generate_tags_list.py")
        exit(1)
    valid_tags = set(tag_ids)
    print(f"⚖️  Законы: цель {COUNT}, доступно тегов {len(tag_ids)}, пачки по {LIST_BATCH}, потоков {WORKERS}")

    collected = {}
    if LAWS_PATH.exists():
        try:
            for law in json.loads(LAWS_PATH.read_text(encoding="utf-8")):
                collected[law["en"]] = law
            print(f"   Продолжаем: уже есть {len(collected)}")
        except json.JSONDecodeError:
            pass
    seen_ids = set(collected.keys())
    exclude_names = {law.get("ru", "") for law in collected.values()}

    rounds = 0
    while len(collected) < COUNT and rounds < 20:
        rounds += 1
        remaining = COUNT - len(collected)
        n_batches = min(WORKERS, max(1, -(-remaining // LIST_BATCH)))
        per = min(LIST_BATCH, -(-remaining // n_batches))
        with ThreadPoolExecutor(max_workers=n_batches) as ex:
            results = list(ex.map(lambda _: gen_batch(per, tag_ids, exclude_names), range(n_batches)))
        added = 0
        for batch in results:
            for law in normalize_ids(batch, seen_ids):
                if law["en"] in collected:
                    continue
                law["tags"] = [t for t in law.get("tags", []) if t in valid_tags]  # чистим от невалидных
                collected[law["en"]] = law
                exclude_names.add(law.get("ru", ""))
                added += 1
        print(f"   Раунд {rounds}: +{added} (всего {len(collected)}/{COUNT})")
        LAWS_PATH.parent.mkdir(parents=True, exist_ok=True)
        LAWS_PATH.write_text(json.dumps(list(collected.values())[:COUNT], ensure_ascii=False, indent=2), encoding="utf-8")
        if added == 0:
            print("   Новых не приходит — останавливаюсь.")
            break

    types = {}
    for law in collected.values():
        types[law.get("type", "?")] = types.get(law.get("type", "?"), 0) + 1
    print(f"✅ laws-list.json: {len(collected)} законов · {', '.join(f'{k}={v}' for k, v in sorted(types.items()))}")


if __name__ == "__main__":
    main()
