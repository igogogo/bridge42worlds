#!/usr/bin/env python3
"""Описания законов (3 уровня) + формулы + история открытия + учёные
→ data/laws-graph.json + lang/ru/data/laws.json.

Закон — дом формул: формулы одни и те же для всех уровней, различаются только описания.
История открытия называет учёных — это связь закон↔учёный. Каждый закон привязан к тегам
(из laws-list.json). Промт — data/prompts/law-describe.txt; модель — config.agents.laws_describe.
Пачки идут параллельно (workers из config.json → laws).
"""

import json
from pathlib import Path
from string import Template
from concurrent.futures import ThreadPoolExecutor

from common import CONFIG, chat, load_prompt, parse_json_salvage

CFG = CONFIG.get("laws", {})
DESCRIBE_BATCH = CFG.get("describe_batch", 12)
WORKERS = CFG.get("workers", 5)

# Текстовые поля описания закона, которые шлифует refine (id/name/type/формулы/учёных/теги/связи не трогаем).
REFINE_TEXT_FIELDS = ["mini", "practical_application", "description_popular", "fun_fact_popular",
                      "description_simple", "how_it_works_simple", "fun_fact", "description",
                      "history", "how_it_works", "key_problems"]

LAWS_LIST = Path("lang/ru/data/laws-list.json")
SCIENTISTS_PATH = Path("lang/ru/data/scientists.json")
LAWS_RU_PATH = Path("lang/ru/data/laws.json")

if not LAWS_LIST.exists():
    print("❌ lang/ru/data/laws-list.json not found (запусти law_list.py)")
    exit(1)


def lc_first(name):
    """Название закона строчными: имена законов всегда начинаются с родового слова
    (закон/уравнение/теорема/принцип/эффект/теория) — строчим первую букву детерминированно,
    имена собственные внутри («Хаббла», «Нётер») не трогаем."""
    name = (name or "").strip()
    return name[:1].lower() + name[1:] if name else name


def generate_batch(items, batch_num, total, all_ids, scientists_list):
    laws_str = "\n".join(
        f"- {x['ru']} (id: {x['en']}, type: {x.get('type', 'закон')}, tags: {', '.join(x.get('tags', []))})"
        for x in items)
    prompt = Template(load_prompt("law-describe")).safe_substitute(
        n=len(items), scientists=", ".join(scientists_list),
        all_ids=", ".join(all_ids), laws_str=laws_str)
    try:
        r = chat("laws_describe", prompt)
    except Exception as e:
        print(f"    ❌ Пачка {batch_num}/{total}: ошибка API {e}")
        return []
    result = r.choices[0].message.content.strip()
    data = parse_json_salvage(result)
    if data is None:
        print(f"    ❌ Пачка {batch_num}/{total}: JSON не разобран (temp/)")
        Path("temp").mkdir(exist_ok=True)
        Path(f"temp/debug_laws_{batch_num}.txt").write_text(result, encoding="utf-8")
        return []
    laws = data.get("laws", []) if isinstance(data, dict) else data
    print(f"    ✅ Пачка {batch_num}/{total}: {len(laws)}")
    return laws


def refine_batch(items, batch_num, total):
    """Рефлексивная шлифовка описаний пачки законов: улучшаем только текстовые поля,
    структуру (id/name/type/формулы/учёных/теги/связи) сохраняем из оригинала. При сбое — оригинал."""
    payload = [{"id": x.get("id"), "name": x.get("name"),
                **{k: x.get(k) for k in REFINE_TEXT_FIELDS if k in x}} for x in items]
    prompt = Template(load_prompt("law-refine")).safe_substitute(
        n=len(items), laws_json=json.dumps(payload, ensure_ascii=False))
    try:
        r = chat("laws_describe", prompt, temperature=0.5)
    except Exception as e:
        print(f"    ⚠️ refine пачка {batch_num}/{total}: API {e} — без шлифовки")
        return items
    data = parse_json_salvage(r.choices[0].message.content.strip())
    refined = (data.get("laws", []) if isinstance(data, dict) else data) or []
    by_id = {(x.get("id") or "").strip(): x for x in refined if isinstance(x, dict)}
    out = []
    for x in items:
        rr = by_id.get((x.get("id") or "").strip())
        if rr:
            raw = {k: x.get(k) for k in REFINE_TEXT_FIELDS if x.get(k)}  # сырое ДО шлифовки — для сравнения
            x = {**x, **{k: rr[k] for k in REFINE_TEXT_FIELDS if rr.get(k)}, "raw": raw}
        out.append(x)
    print(f"    ✦ refine пачка {batch_num}/{total}: {len(refined)}")
    return out


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
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="переописать ВСЕ (по умолчанию — только законы без описания, догенерация)")
    ap.add_argument("--refine", action="store_true",
                    help="рефлексивная шлифовка описаний после генерации")
    ap.add_argument("--reflight", action="store_true",
                    help="повторно пришлифовать УЖЕ прошлифованные (refined=True) исправленным промтом, "
                         "БЕЗ re-описания с нуля — дёшево, для починки бага в старом law-refine.txt")
    args = ap.parse_args()

    ru = json.loads(LAWS_RU_PATH.read_text(encoding="utf-8")) if LAWS_RU_PATH.exists() else {}

    if args.reflight:
        targets = [{"id": tid, **v} for tid, v in ru.items() if v.get("refined")]
        print(f"✦ Re-шлифовка {len(targets)} ранее прошлифованных законов исправленным промтом (без re-описания)...")
        if targets:
            batches = [targets[i:i + DESCRIBE_BATCH] for i in range(0, len(targets), DESCRIBE_BATCH)]
            with ThreadPoolExecutor(max_workers=WORKERS) as ex:
                results = list(ex.map(lambda ib: refine_batch(ib[1], ib[0] + 1, len(batches)), list(enumerate(batches))))
            for x in [y for batch in results for y in batch]:
                tid = x.get("id")
                if tid in ru:
                    for k in REFINE_TEXT_FIELDS:
                        if x.get(k):
                            ru[tid][k] = x[k]
            LAWS_RU_PATH.write_text(json.dumps(ru, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ Re-прошлифовано {len(targets)} законов")
        return

    laws_in = json.loads(LAWS_LIST.read_text(encoding="utf-8"))
    type_map = {x["en"]: x.get("type", "закон") for x in laws_in}
    tags_map = {x["en"]: x.get("tags", []) for x in laws_in}
    all_ids = [x["en"] for x in laws_in]

    scientists = json.loads(SCIENTISTS_PATH.read_text(encoding="utf-8")) if SCIENTISTS_PATH.exists() else {}
    scientists_list = list(scientists.keys())

    # Существующие граф/описания — для ИНКРЕМЕНТАЛЬНОЙ догенерации.
    graph = json.loads(Path("data/laws-graph.json").read_text(encoding="utf-8")) if Path("data/laws-graph.json").exists() else {"graph": {}}

    to_describe = laws_in if args.force else [x for x in laws_in if not (ru.get(x["en"]) or {}).get("description")]
    print(f"⚖️  Описания законов: описываю {len(to_describe)}/{len(laws_in)} "
          f"({'--force: все' if args.force else 'догенерация недостающих'}), пачки по {DESCRIBE_BATCH}, потоков {WORKERS}")

    if to_describe:
        batches = [to_describe[i:i + DESCRIBE_BATCH] for i in range(0, len(to_describe), DESCRIBE_BATCH)]
        total = len(batches)
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            results = list(ex.map(
                lambda ib: generate_batch(ib[1], ib[0] + 1, total, all_ids, scientists_list),
                list(enumerate(batches))))
        new_desc = [x for batch in results for x in batch]
        print(f"\n✅ Описано новых: {len(new_desc)}")
        if args.refine and new_desc:
            print(f"  ✦ Шлифовка описаний ({len(new_desc)}, пачки по {DESCRIBE_BATCH}, потоков {WORKERS})...")
            rbatches = [new_desc[i:i + DESCRIBE_BATCH] for i in range(0, len(new_desc), DESCRIBE_BATCH)]
            with ThreadPoolExecutor(max_workers=WORKERS) as ex:
                rres = list(ex.map(
                    lambda ib: refine_batch(ib[1], ib[0] + 1, len(rbatches)),
                    list(enumerate(rbatches))))
            new_desc = [x for batch in rres for x in batch]
        for law in new_desc:
            lid = (law.get("id") or "").strip()
            if not lid:
                continue
            tags = law.get("tags") or tags_map.get(lid, [])
            ru[lid] = {
                "name": lc_first(law.get("name", "")),
                "type": type_map.get(lid, "закон"),
                "mini": law.get("mini", ""),
                "practical_application": law.get("practical_application", ""),
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
                "refined": args.refine,
                "raw": law.get("raw", {}),
            }
    else:
        print("   Все законы уже описаны — нечего догенерировать (--force чтобы переописать).")

    Path("data").mkdir(exist_ok=True)
    Path("lang/ru/data").mkdir(parents=True, exist_ok=True)

    # Граф: узел на КАЖДЫЙ закон из реестра (даже не описанный).
    for x in laws_in:
        lid = x["en"]
        desc = ru.get(lid, {})
        graph["graph"][lid] = {
            "type": type_map.get(lid, "закон"),
            "tags": desc.get("tags") or tags_map.get(lid, []),
            "scientists": desc.get("scientists", []),
            "related": desc.get("related_laws", graph["graph"].get(lid, {}).get("related", [])),
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
