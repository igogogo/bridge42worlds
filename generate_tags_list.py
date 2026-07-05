#!/usr/bin/env python3
"""Списки тегов для Bridge For Two Worlds.

Два яруса:
  • active      — теги для ГЕНЕРАЦИИ статей (идут в промт). → lang/ru/data/tags-list.json
  • educational — справочные физ/мат понятия ТОЛЬКО для облака/графа (обучающая карта),
                  в промт статей НЕ идут. → lang/ru/data/tags-list-educational.json

Количества и размеры пачек берутся из config.json → "tags".
Образовательные генерируются пачками параллельно (их много), с дедупом и исключением уже собранных.
Аргументы: --active-only / --educational-only (по умолчанию — оба).
"""

import os, sys, json, re, argparse
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

CFG = json.loads(Path("config.json").read_text(encoding="utf-8")).get("tags", {})
ACTIVE_COUNT = CFG.get("active_count", 120)
EDU_COUNT = CFG.get("educational_count", 300)
LIST_BATCH = CFG.get("list_batch", 60)
WORKERS = CFG.get("workers", 5)

ACTIVE_PATH = Path("lang/ru/data/tags-list.json")
EDU_PATH = Path("lang/ru/data/tags-list-educational.json")


def slugify(s):
    s = s.strip().lower()
    s = re.sub(r"[\s_]+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    return s


def normalize_ids(tags, seen_ids):
    """ID тега — slug для URL/имён файлов. Нормализуем и разрешаем коллизии."""
    out = []
    for t in tags:
        slug = slugify(t.get("en", ""))
        if not slug:
            continue
        if slug in seen_ids:
            i = 2
            while f"{slug}_{i}" in seen_ids:
                i += 1
            slug = f"{slug}_{i}"
        seen_ids.add(slug)
        t["en"] = slug
        out.append(t)
    return out


def gen_active():
    print(f"🏷️  Активные теги (для статей): цель {ACTIVE_COUNT}")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"Создай список из {ACTIVE_COUNT} ключевых понятий физики и астрономии для широкой аудитории.\n\n"
                "Для каждого укажи:\n"
                "- ru: русское название\n"
                "- en: английский ID (слова через пробел, нижний регистр; аббревиатуры ЗАГЛАВНЫМИ: JWST, LIGO, CERN)\n"
                "- type: object | method | instrument | concept | substance\n\n"
                "Распределение:\n"
                "- object (~30): только популярные. экзопланета, чёрная дыра, нейтронная звезда, галактика, "
                "квазар, пульсар, сверхновая, комета, астероид, красный карлик, белый карлик, Солнце, "
                "туманность, скопление галактик, метеорит, экзолуна, пояс астероидов...\n"
                "НЕ включай: узкие типы звёзд, специфичные объекты.\n\n"
                "- method (~10): только базовые. спектроскопия, транзитный метод, гравитационное линзирование, "
                "фотометрия, радиоастрономия, коллайдер, компьютерное моделирование...\n\n"
                "- instrument (~5): ТОЛЬКО самые известные. JWST, Hubble, LIGO, Большой адронный коллайдер, телескоп.\n\n"
                "- concept (~48): БОЛЬШЕ фундаментальных понятий:\n"
                "  Квантовая механика: суперпозиция, квантовая запутанность, принцип неопределённости, "
                "туннельный эффект, корпускулярно-волновой дуализм, квантовое поле, коллапс волновой функции, "
                "квантовая телепортация, квантовый компьютер...\n"
                "  Относительность: скорость света, замедление времени, гравитационные волны, "
                "кротовая нора, искривление пространства-времени...\n"
                "  Космология: Большой взрыв, тёмная материя, тёмная энергия, расширение Вселенной, "
                "реликтовое излучение, мультивселенная, инфляция...\n"
                "  Общее: энтропия, антиматерия, теория струн, стандартная модель, "
                "бозон Хиггса, кварк-глюонная плазма, гравитация, электромагнетизм, "
                "ядерный синтез, радиоактивность, сверхпроводимость...\n\n"
                "- substance (~20): водород, гелий, углерод, кислород, железо, вода, метан, "
                "аммиак, углекислый газ, кремний, лёд, пыль, аминокислоты, фосфин, озон...\n\n"
                "Ответь JSON-объектом:\n"
                '{"tags": [{"ru": "квантовая запутанность", "en": "quantum entanglement", "type": "concept"}, ...]}'
            )}
        ],
        temperature=0.5, max_tokens=8000, response_format={"type": "json_object"}
    )
    tags = json.loads(response.choices[0].message.content.strip()).get("tags", [])
    tags = normalize_ids(tags, set())
    ACTIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_PATH.write_text(json.dumps(tags, ensure_ascii=False, indent=2), encoding="utf-8")
    types = {}
    for t in tags:
        types[t.get("type", "?")] = types.get(t.get("type", "?"), 0) + 1
    print(f"✅ tags-list.json: {len(tags)} активных · {', '.join(f'{k}={v}' for k, v in sorted(types.items()))}")
    return tags


def gen_edu_batch(need, exclude):
    """Одна пачка образовательных тегов, исключая уже известные названия."""
    excl = ", ".join(sorted(exclude)[:400])
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"Создай список из {need} СПРАВОЧНЫХ понятий физики и математики для обучающей карты знаний. "
                    "Это не для генерации новостных статей, а для образовательного облака/графа — поэтому охват ШИРЕ "
                    "и глубже, включая математику (разделы, теоремы, методы, объекты) и более специальные физические понятия.\n\n"
                    "Для каждого укажи:\n"
                    "- ru: русское название\n"
                    "- en: английский ID (слова через пробел, нижний регистр; аббревиатуры ЗАГЛАВНЫМИ)\n"
                    "- type: object | method | instrument | concept | substance | math\n\n"
                    "Охватывай разделы: механика, термодинамика, электродинамика, оптика, квантовая теория, "
                    "физика частиц, теория поля, ядерная и атомная физика, конденсированное состояние, "
                    "астрофизика, космология; математика: анализ, алгебра, геометрия, топология, теория вероятностей, "
                    "дифференциальные уравнения, теория чисел, математическая логика.\n\n"
                    + (f"НЕ включай эти уже собранные понятия: {excl}\n\n" if exclude else "")
                    + "Ответь JSON-объектом:\n"
                    '{"tags": [{"ru": "топология", "en": "topology", "type": "math"}, ...]}'
                )}
            ],
            temperature=0.6, max_tokens=6000, response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content.strip()).get("tags", [])
    except Exception as e:
        print(f"    ⚠️ пачка образовательных: ошибка {e}")
        return []


def gen_educational(active_tags):
    print(f"\n📚 Образовательные теги (только для облака/графа): цель {EDU_COUNT}")
    # Возобновление: подхватываем уже собранные
    collected = {}
    if EDU_PATH.exists():
        try:
            for t in json.loads(EDU_PATH.read_text(encoding="utf-8")):
                collected[t["en"]] = t
            print(f"   Продолжаем: уже есть {len(collected)}")
        except json.JSONDecodeError:
            pass
    seen_ids = {t["en"] for t in active_tags} | set(collected.keys())
    # исключаем по русским названиям (модель оперирует ими) + по id
    exclude_names = {t.get("ru", "") for t in active_tags} | {t.get("ru", "") for t in collected.values()}

    rounds = 0
    while len(collected) < EDU_COUNT and rounds < 30:
        rounds += 1
        remaining = EDU_COUNT - len(collected)
        n_batches = min(WORKERS, max(1, -(-remaining // LIST_BATCH)))  # ceil
        per = min(LIST_BATCH, -(-remaining // n_batches))
        with ThreadPoolExecutor(max_workers=n_batches) as ex:
            results = list(ex.map(lambda _: gen_edu_batch(per, exclude_names),
                                  range(n_batches)))
        added = 0
        for batch in results:
            for t in normalize_ids(batch, seen_ids):
                if t["en"] in collected:
                    continue
                t["educational"] = True
                collected[t["en"]] = t
                exclude_names.add(t.get("ru", ""))
                added += 1
        print(f"   Раунд {rounds}: +{added} (всего {len(collected)}/{EDU_COUNT})")
        # сохраняем после каждого раунда (возобновляемость)
        EDU_PATH.write_text(json.dumps(list(collected.values())[:EDU_COUNT],
                                       ensure_ascii=False, indent=2), encoding="utf-8")
        if added == 0:
            print("   Новых не приходит — останавливаюсь.")
            break
    print(f"✅ tags-list-educational.json: {len(collected)} образовательных")
    return list(collected.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--active-only", action="store_true")
    ap.add_argument("--educational-only", action="store_true")
    args = ap.parse_args()

    if args.educational_only:
        active = json.loads(ACTIVE_PATH.read_text(encoding="utf-8")) if ACTIVE_PATH.exists() else []
        gen_educational(active)
    elif args.active_only:
        gen_active()
    else:
        active = gen_active()
        gen_educational(active)


if __name__ == "__main__":
    main()
