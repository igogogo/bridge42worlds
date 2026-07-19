#!/usr/bin/env python3
"""Описания тегов (3 уровня, история, проблемы, учёные, формулы, связи)
→ data/tags-graph.json + lang/ru/data/tags.json.

Описывает ОБА яруса: активные (tags-list.json) + образовательные (tags-list-educational.json).
Образовательные помечаются "educational": true в графе. Пачки идут ПАРАЛЛЕЛЬНО (workers из
config.json → tags). Промт — data/prompts/tag-describe.txt; модель — config.agents.tags_describe.
Связи (related) делаются двусторонними и чистятся от висящих ссылок.
"""

import json, argparse
from pathlib import Path
from string import Template
from concurrent.futures import ThreadPoolExecutor

from common import CONFIG, chat, load_prompt, parse_json_salvage

CFG = CONFIG.get("tags", {})
DESCRIBE_BATCH = CFG.get("describe_batch", 20)
WORKERS = CFG.get("workers", 5)

# Текстовые поля описания тега, которые шлифует refine (id/name/формулы/учёных/связи не трогаем).
REFINE_TEXT_FIELDS = ["mini", "practical_application", "description_popular", "fun_fact_popular",
                      "description_simple", "history_simple", "how_it_works_simple", "description",
                      "history", "how_it_works", "key_problems", "fun_fact"]

ACTIVE_PATH = Path("lang/ru/data/tags-list.json")
EDU_PATH = Path("lang/ru/data/tags-list-educational.json")
SCIENTISTS_PATH = Path("lang/ru/data/scientists.json")
LAWS_PATH = Path("lang/ru/data/laws-list.json")
TAGS_RU_PATH = Path("lang/ru/data/tags.json")

if not ACTIVE_PATH.exists():
    print("❌ lang/ru/data/tags-list.json not found (запусти tag_list.py)")
    exit(1)


def lc_name(name):
    """Тег строчными, кроме имён собственных. Безопасная эвристика: строчим первую букву,
    только если имя однословное ИЛИ второе слово уже строчное (тогда первое — не имя собственное).
    «Спектроскопия»→«спектроскопия», но «Джеймс Уэбб» (второе слово с большой) не трогаем."""
    name = (name or "").strip()
    if not name:
        return name
    words = name.split()
    if len(words) == 1 or (len(words) >= 2 and words[1][:1].islower()):
        return name[:1].lower() + name[1:]
    return name


def generate_batch(tag_items, batch_num, total, all_en_ids, scientists_list, laws_names):
    tags_str = "\n".join(f"- {t['ru']} (en_id: {t['en']}, type: {t.get('type', 'concept')})" for t in tag_items)
    laws_str = ", ".join(laws_names[:50]) if laws_names else "(законов пока нет)"
    prompt = Template(load_prompt("tag-describe")).safe_substitute(
        n=len(tag_items), scientists=", ".join(scientists_list[:50]),
        all_ids=", ".join(all_en_ids), tags_str=tags_str, laws=laws_str)
    try:
        r = chat("tags_describe", prompt)
    except Exception as e:
        print(f"    ❌ Пачка {batch_num}/{total}: ошибка API {e}")
        return []
    result = r.choices[0].message.content.strip()
    data = parse_json_salvage(result)
    if data is None:
        print(f"    ❌ Пачка {batch_num}/{total}: JSON не разобран (temp/)")
        Path("temp").mkdir(exist_ok=True)
        Path(f"temp/debug_tags_{batch_num}.txt").write_text(result, encoding="utf-8")
        return []
    tags = data.get("tags", []) if isinstance(data, dict) else data
    print(f"    ✅ Пачка {batch_num}/{total}: {len(tags)}")
    return tags


def refine_batch(items, batch_num, total):
    """Рефлексивная шлифовка описаний пачки тегов: улучшаем только текстовые поля,
    структуру (id/name/формулы/учёных/связи) сохраняем из оригинала. При сбое — оригинал."""
    payload = [{"id": t.get("id"), "name": t.get("name"),
                **{k: t.get(k) for k in REFINE_TEXT_FIELDS if k in t}} for t in items]
    prompt = Template(load_prompt("tag-refine")).safe_substitute(
        n=len(items), tags_json=json.dumps(payload, ensure_ascii=False))
    try:
        r = chat("tags_describe", prompt, temperature=0.5)
    except Exception as e:
        print(f"    ⚠️ refine пачка {batch_num}/{total}: API {e} — без шлифовки")
        return items
    data = parse_json_salvage(r.choices[0].message.content.strip())
    refined = (data.get("tags", []) if isinstance(data, dict) else data) or []
    by_id = {(x.get("id") or "").strip(): x for x in refined if isinstance(x, dict)}
    out = []
    for t in items:
        rr = by_id.get((t.get("id") or "").strip())
        if rr:
            raw = {k: t.get(k) for k in REFINE_TEXT_FIELDS if t.get(k)}  # сырое ДО шлифовки — для сравнения
            t = {**t, **{k: rr[k] for k in REFINE_TEXT_FIELDS if rr.get(k)}, "raw": raw}
        out.append(t)
    print(f"    ✦ refine пачка {batch_num}/{total}: {len(refined)}")
    return out


def symmetrize(graph):
    """Связи related двусторонние + чистка от несуществующих/самоссылок."""
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
    ap.add_argument("--force", action="store_true",
                    help="переописать ВСЕ (по умолчанию — только теги без описания, догенерация)")
    ap.add_argument("--only", default="",
                    help="переописать ТОЛЬКО один тег по english id, остальные не трогать — "
                         "для точечной починки/проверки без --force на всё")
    ap.add_argument("--ids", default="",
                    help="переописать СПИСОК тегов через запятую (english id) — как --only, но "
                         "пакетно, для точечного бэкфилла N конкретных тегов без --force на всё")
    ap.add_argument("--refine", action="store_true",
                    help="рефлексивная шлифовка описаний после генерации")
    ap.add_argument("--reflight", action="store_true",
                    help="повторно пришлифовать УЖЕ прошлифованные (refined=True) исправленным промтом, "
                         "БЕЗ re-описания с нуля — дёшево, для починки бага в старом tag-refine.txt")
    args = ap.parse_args()

    ru = json.loads(TAGS_RU_PATH.read_text(encoding="utf-8")) if TAGS_RU_PATH.exists() else {}

    if args.reflight:
        targets = [{"id": tid, **v} for tid, v in ru.items() if v.get("refined")]
        print(f"✦ Re-шлифовка {len(targets)} ранее прошлифованных тегов исправленным промтом (без re-описания)...")
        if targets:
            batches = [targets[i:i + DESCRIBE_BATCH] for i in range(0, len(targets), DESCRIBE_BATCH)]
            with ThreadPoolExecutor(max_workers=WORKERS) as ex:
                results = list(ex.map(lambda ib: refine_batch(ib[1], ib[0] + 1, len(batches)), list(enumerate(batches))))
            for t in [x for batch in results for x in batch]:
                tid = t.get("id")
                if tid in ru:
                    for k in REFINE_TEXT_FIELDS:
                        if t.get(k):
                            ru[tid][k] = t[k]
            TAGS_RU_PATH.write_text(json.dumps(ru, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ Re-прошлифовано {len(targets)} тегов")
        return

    active = json.loads(ACTIVE_PATH.read_text(encoding="utf-8"))
    edu = json.loads(EDU_PATH.read_text(encoding="utf-8")) if EDU_PATH.exists() else []
    edu_ids = {t["en"] for t in edu}

    tags_input = (edu if args.educational_only else active + edu)
    type_map = {t["en"]: t.get("type", "concept") for t in active + edu}
    domain_map = {t["en"]: t.get("domain", "") for t in active + edu}
    all_en_ids = [t["en"] for t in active + edu]

    scientists = json.loads(SCIENTISTS_PATH.read_text(encoding="utf-8")) if SCIENTISTS_PATH.exists() else {}
    scientists_list = list(scientists.keys())
    laws_names = [l["ru"] for l in json.loads(LAWS_PATH.read_text(encoding="utf-8"))] if LAWS_PATH.exists() else []

    # Существующие граф/описания — для ИНКРЕМЕНТАЛЬНОЙ догенерации (не трогаем уже описанное).
    graph = json.loads(Path("data/tags-graph.json").read_text(encoding="utf-8")) if Path("data/tags-graph.json").exists() else {"graph": {}}

    if args.only:
        to_describe = [t for t in tags_input if t["en"] == args.only]
        if not to_describe:
            print(f"❌ --only {args.only}: такого id нет в списках тегов")
            return
    elif args.ids:
        wanted = {x.strip() for x in args.ids.split(",") if x.strip()}
        to_describe = [t for t in tags_input if t["en"] in wanted]
        missing = wanted - {t["en"] for t in to_describe}
        if missing:
            print(f"❌ --ids: не найдены в списках тегов: {sorted(missing)}")
            return
    else:
        to_describe = tags_input if args.force else [t for t in tags_input if not (ru.get(t["en"]) or {}).get("description")]
    label = ('--only ' + args.only if args.only else '--ids: ' + str(len(to_describe)) + ' тегов' if args.ids
             else '--force: все' if args.force else 'догенерация недостающих')
    print(f"🏷️  Описания тегов: описываю {len(to_describe)}/{len(tags_input)} ({label}), "
          f"пачки по {DESCRIBE_BATCH}, потоков {WORKERS}")

    if to_describe:
        batches = [to_describe[i:i + DESCRIBE_BATCH] for i in range(0, len(to_describe), DESCRIBE_BATCH)]
        total = len(batches)
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            results = list(ex.map(
                lambda ib: generate_batch(ib[1], ib[0] + 1, total, all_en_ids, scientists_list, laws_names),
                list(enumerate(batches))))
        new_desc = [t for batch in results for t in batch]
        print(f"\n✅ Описано новых: {len(new_desc)}")
        if args.refine and new_desc:
            print(f"  ✦ Шлифовка описаний ({len(new_desc)}, пачки по {DESCRIBE_BATCH}, потоков {WORKERS})...")
            rbatches = [new_desc[i:i + DESCRIBE_BATCH] for i in range(0, len(new_desc), DESCRIBE_BATCH)]
            with ThreadPoolExecutor(max_workers=WORKERS) as ex:
                rres = list(ex.map(
                    lambda ib: refine_batch(ib[1], ib[0] + 1, len(rbatches)),
                    list(enumerate(rbatches))))
            new_desc = [t for batch in rres for t in batch]
        for t in new_desc:
            tid = (t.get("id") or "").strip()
            if not tid:
                continue
            ru[tid] = {
                "name": lc_name(t.get("name", "")),
                "mini": t.get("mini", ""),
                "practical_application": t.get("practical_application", ""),
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
                "refined": args.refine,
                "raw": t.get("raw", {}),
            }
    else:
        print("   Все теги уже описаны — нечего догенерировать (--force чтобы переописать).")

    Path("data").mkdir(exist_ok=True)
    Path("lang/ru/data").mkdir(parents=True, exist_ok=True)

    # Граф: узел на КАЖДЫЙ тег из списков (даже не описанный), article_count сохраняем.
    # "related"/"scientists" ОБЪЕДИНЯЕМ с уже накопленным в графе (union), не перезаписываем —
    # иначе повторный прогон этого скрипта (даже обычный top-up) тихо стирает связи, наращенные
    # отдельно через run.py evolve/connectivity-repair (баг найден 2026-07-18, см. TODO.md).
    for t in (active + edu):
        tid = t["en"]
        prev = graph["graph"].get(tid, {})
        desc = ru.get(tid, {})
        graph["graph"][tid] = {
            "level": type_map.get(tid, "concept"),
            "domain": domain_map.get(tid, "") or prev.get("domain", ""),
            "related": sorted(set(desc.get("related_tags", [])) | set(prev.get("related", []))),
            "article_count": prev.get("article_count", 0),
            "scientists": sorted(set(desc.get("scientists", [])) | set(prev.get("scientists", []))),
            "educational": tid in edu_ids,
        }

    symmetrize(graph)
    Path("data/tags-graph.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    TAGS_RU_PATH.write_text(json.dumps(ru, ensure_ascii=False, indent=2), encoding="utf-8")

    n_edu = sum(1 for n in graph["graph"].values() if n.get("educational"))
    relations = sum(len(n["related"]) for n in graph["graph"].values())
    n_described = sum(1 for v in ru.values() if v.get("description"))
    print(f"✅ tags-graph.json: {len(graph['graph'])} тегов ({n_edu} образоват.), связей {relations}, описано {n_described}")
    print(f"✅ lang/ru/data/tags.json")


if __name__ == "__main__":
    main()
