#!/usr/bin/env python3
"""Описания законов (3 уровня) + формулы + история открытия + учёные
→ data/laws-graph.json + lang/ru/data/laws.json.

Закон — дом формул: формулы одни и те же для всех уровней, различаются только описания.
История открытия называет учёных — это связь закон↔учёный. Каждый закон привязан к тегам
(из laws-list.json). Пачки идут параллельно (workers из config.json → laws).
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


def parse_json_salvage(text):
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


load_dotenv()
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not DEEPSEEK_API_KEY:
    print("❌ DEEPSEEK_API_KEY not set")
    exit(1)

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
SYSTEM_PROMPT = Path("data/prompts/system.txt").read_text(encoding="utf-8")

CFG = json.loads(Path("config.json").read_text(encoding="utf-8")).get("laws", {})
DESCRIBE_BATCH = CFG.get("describe_batch", 12)
WORKERS = CFG.get("workers", 5)

LAWS_LIST = Path("lang/ru/data/laws-list.json")
SCIENTISTS_PATH = Path("lang/ru/data/scientists.json")
LAWS_RU_PATH = Path("lang/ru/data/laws.json")

if not LAWS_LIST.exists():
    print("❌ lang/ru/data/laws-list.json not found (запусти generate_laws_list.py)")
    exit(1)


def generate_batch(items, batch_num, total, all_ids, scientists_list):
    laws_str = "\n".join(
        f"- {x['ru']} (id: {x['en']}, type: {x.get('type', 'закон')}, tags: {', '.join(x.get('tags', []))})"
        for x in items)
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"Создай образовательные карточки для {len(items)} законов/принципов/теорем физики.\n\n"
                    "Для каждого — описания ТРЁХ УРОВНЕЙ СЛОЖНОСТИ (формулы ОДНИ И ТЕ ЖЕ для всех уровней, "
                    "различается только текст описания):\n\n"
                    "POPULAR (для школьника):\n"
                    "- description_popular: 1-2 простых предложения с бытовой аналогией, что закон утверждает\n"
                    "- fun_fact_popular: занятный факт простыми словами (1 предложение)\n\n"
                    "SIMPLE (для взрослого неспециалиста):\n"
                    "- description_simple: суть закона с аналогией (2-3 предложения)\n"
                    "- how_it_works_simple: где проявляется, пример (1-2 предложения)\n"
                    "- fun_fact: интересный факт (1 предложение)\n\n"
                    "ADVANCED (полный, образовательный):\n"
                    "- description: строгая формулировка и смысл (3-5 предложений)\n"
                    "- history: ИСТОРИЯ ОТКРЫТИЯ — кто, когда, как пришли к закону, кто развивал (3-5 предложений). "
                    f"Обязательно называй учёных; если они есть в списке — пиши точно как там: {', '.join(scientists_list[:60])}.\n"
                    "- how_it_works: как применяется, границы применимости (3-4 предложения)\n"
                    "- key_problems: 0-2 нюанса/ограничения/открытых вопроса (массив строк)\n\n"
                    "ОБЩИЕ поля:\n"
                    "- id: английский ID (скопируй точно из входных данных)\n"
                    "- name: русское название (скопируй точно)\n"
                    "- formulas: 1-3 ключевые формулы этого закона [{description, latex, meaning}] "
                    "(latex без окружения $$; экранируй обратные слэши)\n"
                    "- scientists: имена учёных-первооткрывателей (те, кого назвал в history; из списка выше если есть)\n"
                    "- tags: скопируй список tags из входных данных\n"
                    f"- related_laws: 0-3 id других законов из этого списка: {', '.join(all_ids)}\n\n"
                    "Законы для обработки:\n"
                    f"{laws_str}\n\n"
                    'Ответь JSON-объектом:\n'
                    '{"laws": [{\n'
                    '  "id": "law_of_universal_gravitation", "name": "Закон всемирного тяготения",\n'
                    '  "description_popular": "...", "fun_fact_popular": "...",\n'
                    '  "description_simple": "...", "how_it_works_simple": "...", "fun_fact": "...",\n'
                    '  "description": "...", "history": "...", "how_it_works": "...", "key_problems": ["..."],\n'
                    '  "formulas": [{"description": "Сила тяготения", "latex": "F = G\\\\frac{m_1 m_2}{r^2}", "meaning": "..."}],\n'
                    '  "scientists": ["Isaac Newton"], "tags": ["gravity", "mass"], "related_laws": ["newtons_second_law"]\n'
                    '}]}'
                )}
            ],
            temperature=0.5, max_tokens=16000, response_format={"type": "json_object"}
        )
    except Exception as e:
        print(f"    ❌ Пачка {batch_num}/{total}: ошибка API {e}")
        return []
    result = response.choices[0].message.content.strip()
    data = parse_json_salvage(result)
    if data is None:
        print(f"    ❌ Пачка {batch_num}/{total}: JSON не разобран (temp/)")
        Path("temp").mkdir(exist_ok=True)
        Path(f"temp/debug_laws_{batch_num}.txt").write_text(result, encoding="utf-8")
        return []
    laws = data.get("laws", []) if isinstance(data, dict) else data
    print(f"    ✅ Пачка {batch_num}/{total}: {len(laws)}")
    return laws


def symmetrize(graph):
    g = graph["graph"]
    for lid, node in g.items():
        node["related"] = [r for r in dict.fromkeys(node.get("related", [])) if r in g and r != lid]
    for lid, node in g.items():
        for r in list(node["related"]):
            back = g[r].setdefault("related", [])
            if lid not in back:
                back.append(lid)


def main():
    laws_in = json.loads(LAWS_LIST.read_text(encoding="utf-8"))
    type_map = {x["en"]: x.get("type", "закон") for x in laws_in}
    tags_map = {x["en"]: x.get("tags", []) for x in laws_in}
    all_ids = [x["en"] for x in laws_in]

    scientists = json.loads(SCIENTISTS_PATH.read_text(encoding="utf-8")) if SCIENTISTS_PATH.exists() else {}
    scientists_list = list(scientists.keys())

    print(f"⚖️  Описания законов: {len(laws_in)} законов, пачки по {DESCRIBE_BATCH}, потоков {WORKERS}")
    batches = [laws_in[i:i + DESCRIBE_BATCH] for i in range(0, len(laws_in), DESCRIBE_BATCH)]
    total = len(batches)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        results = list(ex.map(
            lambda ib: generate_batch(ib[1], ib[0] + 1, total, all_ids, scientists_list),
            list(enumerate(batches))))
    all_laws = [x for batch in results for x in batch]
    print(f"\n✅ Описано: {len(all_laws)}")

    Path("data").mkdir(exist_ok=True)
    Path("lang/ru/data").mkdir(parents=True, exist_ok=True)

    graph = {"graph": {}}
    ru = {}
    for law in all_laws:
        lid = (law.get("id") or "").strip()
        if not lid:
            continue
        tags = law.get("tags") or tags_map.get(lid, [])
        graph["graph"][lid] = {
            "type": type_map.get(lid, "закон"),
            "tags": tags,
            "scientists": law.get("scientists", []),
            "related": law.get("related_laws", []),
        }
        ru[lid] = {
            "name": law.get("name", ""),
            "type": type_map.get(lid, "закон"),
            "description_popular": law.get("description_popular", ""),
            "fun_fact_popular": law.get("fun_fact_popular", ""),
            "description_simple": law.get("description_simple", ""),
            "how_it_works_simple": law.get("how_it_works_simple", ""),
            "fun_fact": law.get("fun_fact", ""),
            "description": law.get("description", ""),
            "history": law.get("history", ""),
            "how_it_works": law.get("how_it_works", ""),
            "key_problems": law.get("key_problems", []),
            "formulas": law.get("formulas", []),
            "scientists": law.get("scientists", []),
            "tags": tags,
            "related_laws": law.get("related_laws", []),
        }

    symmetrize(graph)
    Path("data/laws-graph.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    LAWS_RU_PATH.write_text(json.dumps(ru, ensure_ascii=False, indent=2), encoding="utf-8")

    relations = sum(len(n["related"]) for n in graph["graph"].values())
    n_formulas = sum(len(v.get("formulas", [])) for v in ru.values())
    print(f"✅ laws-graph.json: {len(graph['graph'])} законов, связей {relations}, формул {n_formulas}")
    print(f"✅ lang/ru/data/laws.json")


if __name__ == "__main__":
    main()
