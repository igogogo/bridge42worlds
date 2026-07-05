#!/usr/bin/env python3
"""Описания тегов (история, проблемы, учёные, формулы, связи) → data/tags-graph.json + lang/ru/data/tags.json.

Описывает ОБА яруса: активные (tags-list.json) + образовательные (tags-list-educational.json).
Образовательные помечаются "educational": true в графе (для отдельного типа карточек в облаке/графе).
Пачки описаний идут ПАРАЛЛЕЛЬНО (workers из config.json → tags). Связи (related) делаются
двусторонними и чистятся от висящих ссылок.
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


load_dotenv()
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not DEEPSEEK_API_KEY:
    print("❌ DEEPSEEK_API_KEY not set")
    exit(1)

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
SYSTEM_PROMPT = Path("data/prompts/system.txt").read_text(encoding="utf-8")

CFG = json.loads(Path("config.json").read_text(encoding="utf-8")).get("tags", {})
DESCRIBE_BATCH = CFG.get("describe_batch", 20)
WORKERS = CFG.get("workers", 5)

ACTIVE_PATH = Path("lang/ru/data/tags-list.json")
EDU_PATH = Path("lang/ru/data/tags-list-educational.json")
SCIENTISTS_PATH = Path("lang/ru/data/scientists.json")
TAGS_RU_PATH = Path("lang/ru/data/tags.json")

if not ACTIVE_PATH.exists():
    print("❌ lang/ru/data/tags-list.json not found (запусти generate_tags_list.py)")
    exit(1)


def generate_batch(tag_items, batch_num, total, all_en_ids, scientists_list):
    tags_str = "\n".join(f"- {t['ru']} (en_id: {t['en']}, type: {t.get('type', 'concept')})" for t in tag_items)
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"Создай образовательные мини-статьи для {len(tag_items)} понятий физики, математики и астрономии.\n\n"
                    "Для каждого понятия создай описания ТРЁХ УРОВНЕЙ СЛОЖНОСТИ:\n\n"
                    "POPULAR (максимально простой, для школьника):\n"
                    "- description_popular: 1-2 простых предложения бытовым языком с аналогией из жизни\n"
                    "- fun_fact_popular: один занятный факт простыми словами (1 предложение)\n\n"
                    "SIMPLE (средний, для взрослого неспециалиста):\n"
                    "- description_simple: описание с аналогией из жизни (2-3 предложения)\n"
                    "- history_simple: кратко кто открыл и когда (1-2 предложения)\n"
                    "- how_it_works_simple: как проявляется (1-2 предложения с аналогией)\n"
                    "- fun_fact: интересный факт (1 предложение)\n\n"
                    "ADVANCED (подробный, полный):\n"
                    "- description: развёрнутое описание (3-5 предложений)\n"
                    "- history: история открытия — кто, когда, как развивалось (3-4 предложения). "
                    f"Упомяни связанных учёных если они есть в списке: {', '.join(scientists_list[:50])}.\n"
                    "- how_it_works: как это работает (3-4 предложения)\n"
                    "- key_problems: 1-2 ключевые нерешённые проблемы (массив строк)\n"
                    "- formulas: 0-2 ключевые формулы [{description, latex, meaning}]\n\n"
                    "ОБЩИЕ поля (одни для всех уровней):\n"
                    "- id: английский ID (скопируй точно из входных данных)\n"
                    "- name: русское название (скопируй точно)\n"
                    "- scientists: 0-3 имени учёных ТОЛЬКО из списка выше\n"
                    f"- related_tags: 3-5 английских id ТОЛЬКО из: {', '.join(all_en_ids)}\n\n"
                    "Понятия для обработки:\n"
                    f"{tags_str}\n\n"
                    'Ответь JSON-объектом:\n'
                    '{"tags": [{\n'
                    '  "id": "black_hole", "name": "Чёрная дыра",\n'
                    '  "description_popular": "...", "fun_fact_popular": "...",\n'
                    '  "description_simple": "...", "history_simple": "...", "how_it_works_simple": "...", "fun_fact": "...",\n'
                    '  "description": "...", "history": "...", "how_it_works": "...",\n'
                    '  "key_problems": ["..."],\n'
                    '  "formulas": [{"description": "...", "latex": "R_s = \\\\frac{2GM}{c^2}", "meaning": "..."}],\n'
                    '  "scientists": ["Stephen Hawking"],\n'
                    '  "related_tags": ["event_horizon", "singularity"]\n'
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
        Path(f"temp/debug_tags_{batch_num}.txt").write_text(result, encoding="utf-8")
        return []
    tags = data.get("tags", []) if isinstance(data, dict) else data
    print(f"    ✅ Пачка {batch_num}/{total}: {len(tags)}")
    return tags


def symmetrize(graph):
    """Связи related делаем двусторонними и чистим от несуществующих/самоссылок."""
    g = graph["graph"]
    for tid, node in g.items():
        node["related"] = [r for r in dict.fromkeys(node.get("related", [])) if r in g and r != tid]
    for tid, node in g.items():
        for r in list(node["related"]):
            back = g[r].setdefault("related", [])
            if tid not in back:
                back.append(tid)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--educational-only", action="store_true",
                    help="описать только образовательные (активные оставить как есть)")
    args = ap.parse_args()

    active = json.loads(ACTIVE_PATH.read_text(encoding="utf-8"))
    edu = json.loads(EDU_PATH.read_text(encoding="utf-8")) if EDU_PATH.exists() else []
    edu_ids = {t["en"] for t in edu}

    tags_input = (edu if args.educational_only else active + edu)
    type_map = {t["en"]: t.get("type", "concept") for t in active + edu}
    all_en_ids = [t["en"] for t in active + edu]

    scientists = json.loads(SCIENTISTS_PATH.read_text(encoding="utf-8")) if SCIENTISTS_PATH.exists() else {}
    scientists_list = list(scientists.keys())

    print(f"🏷️  Описания тегов: {len(tags_input)} понятий "
          f"(активных {len(active)}, образовательных {len(edu)}), "
          f"пачки по {DESCRIBE_BATCH}, потоков {WORKERS}")

    batches = [tags_input[i:i + DESCRIBE_BATCH] for i in range(0, len(tags_input), DESCRIBE_BATCH)]
    total = len(batches)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        results = list(ex.map(
            lambda ib: generate_batch(ib[1], ib[0] + 1, total, all_en_ids, scientists_list),
            list(enumerate(batches))))
    all_tags = [t for batch in results for t in batch]
    print(f"\n✅ Описано: {len(all_tags)}")

    Path("data").mkdir(exist_ok=True)
    Path("lang/ru/data").mkdir(parents=True, exist_ok=True)

    # В educational-only режиме дополняем существующий граф, иначе строим заново
    graph = {"graph": {}}
    ru = {}
    if args.educational_only and Path("data/tags-graph.json").exists():
        graph = json.loads(Path("data/tags-graph.json").read_text(encoding="utf-8"))
        if TAGS_RU_PATH.exists():
            ru = json.loads(TAGS_RU_PATH.read_text(encoding="utf-8"))

    for t in all_tags:
        tid = (t.get("id") or "").strip()
        if not tid:
            continue
        graph["graph"][tid] = {
            "level": type_map.get(tid, "concept"),
            "related": t.get("related_tags", []),
            "article_count": graph["graph"].get(tid, {}).get("article_count", 0),
            "scientists": t.get("scientists", []),
            "educational": tid in edu_ids,
        }
        ru[tid] = {
            "name": t.get("name", ""),
            "description_popular": t.get("description_popular", ""),
            "fun_fact_popular": t.get("fun_fact_popular", ""),
            "description_simple": t.get("description_simple", ""),
            "history_simple": t.get("history_simple", ""),
            "how_it_works_simple": t.get("how_it_works_simple", ""),
            "description": t.get("description", ""),
            "history": t.get("history", ""),
            "how_it_works": t.get("how_it_works", ""),
            "key_problems": t.get("key_problems", []),
            "fun_fact": t.get("fun_fact", ""),
            "formulas": t.get("formulas", []),
            "scientists": t.get("scientists", []),
            "related_tags": t.get("related_tags", []),
            "educational": tid in edu_ids,
        }

    symmetrize(graph)
    Path("data/tags-graph.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    TAGS_RU_PATH.write_text(json.dumps(ru, ensure_ascii=False, indent=2), encoding="utf-8")

    n_edu = sum(1 for n in graph["graph"].values() if n.get("educational"))
    relations = sum(len(n["related"]) for n in graph["graph"].values())
    print(f"✅ tags-graph.json: {len(graph['graph'])} тегов ({n_edu} образовательных), связей {relations}")
    print(f"✅ lang/ru/data/tags.json")


if __name__ == "__main__":
    main()
