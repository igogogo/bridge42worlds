#!/usr/bin/env python3
"""Чинит СТРОГУЮ связность графа знаний: каждый тег/закон/учёный должен иметь связь с КАЖДЫМ
из двух других типов, а не просто "не быть полностью изолированным" (см. tag_connectivity_repair.py
для более мягкой проверки). Источник пробелов — generate.compute_connectivity_gaps() (та же
функция, что питает секцию "Связность сущностей" на status.html).

На 2026-07-18 законы уже полностью связаны (laws_no_tag/laws_no_sci пусты) — чинит три реальных
пробела: tags_no_law, tags_no_sci, sci_no_law. Один батч-вызов на каждую категорию (не по одному
элементу — дешевле, и модель видит соседей по домену). Честно возвращает null, если для элемента
реально нет подходящей пары среди существующих — не притягивает связь силой.

Запуск:
    python connectivity_repair.py            # только отчёт (dry-run)
    python connectivity_repair.py --apply     # реально правит (3 LLM-вызова)
"""
import argparse
import json
from pathlib import Path

from common import CONFIG, chat, load_prompt, parse_json_salvage

LANGS = CONFIG.get("languages", ["ru", "en", "es"])
LAWS_LIST_PATH = Path("lang/ru/data/laws-list.json")
LAWS_RU_PATH = Path("lang/ru/data/laws.json")
LAWS_GRAPH_PATH = Path("data/laws-graph.json")
SCIENTISTS_PATH = Path("lang/ru/data/scientists.json")


def request_links(items, items_names, targets, targets_names, items_desc, target_desc, target_pick_desc, items_label, targets_label):
    """items/targets — списки id; *_names — dict id->читаемое название. Возвращает dict source_id->target_id|None.
    Когда id==название (учёные), модель иногда эхом возвращает "id: id" целиком как source_id
    (наблюдалось 2026-07-18 на батче scientists→law) — матчинг терпим к этому через startswith."""
    items_json = json.dumps([f"{i}: {items_names.get(i, i)}" for i in items], ensure_ascii=False)
    targets_json = json.dumps([f"{t}: {targets_names.get(t, t)}" for t in targets], ensure_ascii=False)
    prompt = load_prompt("entity-connectivity-repair").format(
        items_desc=items_desc, target_desc=target_desc, target_pick_desc=target_pick_desc,
        items_label=items_label, targets_label=targets_label,
        items_json=items_json, targets_json=targets_json,
    )
    try:
        r = chat("laws_list", prompt)
    except Exception as e:
        print(f"    ❌ ошибка LLM: {e}")
        return {}
    data = parse_json_salvage(r.choices[0].message.content) or {}
    links = data.get("links", [])
    if not links:
        print(f"    ⚠️ пустой/нераспарсенный ответ модели (0 links) — батч из {len(items)} элементов пропущен целиком")
    target_ids = set(targets)
    out = {}
    for link in links:
        raw_sid, tid = link.get("source_id"), link.get("target_id")
        sid = raw_sid if raw_sid in items else next(
            (i for i in items if isinstance(raw_sid, str) and raw_sid.startswith(i + ":")), None)
        if sid and tid in target_ids:
            out[sid] = tid
        elif sid:
            out[sid] = None
    return out


def sync_lang_field(base_path_tmpl, entity_id, field, new_value):
    """Пишет новое значение поля в lang/{lang}/data/{base}.json для всех языков (снимки,
    сделанные describe-скриптами на момент генерации — страницы рендерятся из них, не из
    laws-list.json/scientists.json напрямую)."""
    for lang in LANGS:
        p = Path(base_path_tmpl.format(lang=lang))
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        if entity_id in data:
            data[entity_id][field] = new_value
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Чинит теги/законы/учёных без связи с КАЖДЫМ другим типом сущности")
    ap.add_argument("--apply", action="store_true", help="реально править (до 3 LLM-вызовов), без флага — только отчёт")
    args = ap.parse_args()

    import generate
    gaps = generate.compute_connectivity_gaps()
    tags_no_law, tags_no_sci, sci_no_law = gaps["tags_no_law"], gaps["tags_no_sci"], gaps["sci_no_law"]

    print(f"⚖️  Теги без закона: {len(tags_no_law)}/{gaps['n_tags']}")
    print(f"👨‍🔬 Теги без учёного: {len(tags_no_sci)}/{gaps['n_tags']}")
    print(f"⚖️  Учёные без закона: {len(sci_no_law)}/{gaps['n_sci']}")
    if not (tags_no_law or tags_no_sci or sci_no_law):
        print("✅ Строгая связность уже полная — нечего чинить.")
        return
    if not args.apply:
        print("\nℹ️  Запусти с --apply, чтобы восстановить связи через LLM (до 3 батч-вызовов).")
        return

    laws_list = json.loads(LAWS_LIST_PATH.read_text(encoding="utf-8")) if LAWS_LIST_PATH.exists() else []
    laws_ru = json.loads(LAWS_RU_PATH.read_text(encoding="utf-8")) if LAWS_RU_PATH.exists() else {}
    scientists = json.loads(SCIENTISTS_PATH.read_text(encoding="utf-8")) if SCIENTISTS_PATH.exists() else {}
    tags_loc_path = Path("lang/ru/data/tags.json")
    tags_ru = json.loads(tags_loc_path.read_text(encoding="utf-8")) if tags_loc_path.exists() else {}
    graph_doc = json.loads(LAWS_GRAPH_PATH.read_text(encoding="utf-8")) if LAWS_GRAPH_PATH.exists() else {"graph": {}}
    laws_graph = graph_doc.get("graph", {})

    law_ids = [l["en"] for l in laws_list]
    law_names = {l["en"]: l["ru"] for l in laws_list}
    tag_names = {tid: v.get("name", tid) for tid, v in tags_ru.items()}
    sci_ids = list(scientists.keys())

    fixed_law_tags, fixed_law_sci, fixed_sci_tags = {}, {}, {}

    if tags_no_law:
        print(f"\n🔗 Подбираю законы для {len(tags_no_law)} тегов...")
        links = request_links(
            tags_no_law, tag_names, law_ids, law_names,
            items_desc="теги", target_desc="ни одним законом", target_pick_desc="закон",
            items_label="Теги", targets_label="Существующие законы")
        for tag, lid in links.items():
            if not lid:
                print(f"   ⚠️ {tag}: LLM не нашла подходящего закона, пропущено")
                continue
            law = next((l for l in laws_list if l["en"] == lid), None)
            if not law:
                continue
            law["tags"] = sorted(set(law.get("tags", [])) | {tag})
            fixed_law_tags[lid] = law["tags"]
            print(f"   ✅ {tag} → закон {lid}")

    if tags_no_sci:
        print(f"\n🔗 Подбираю учёных для {len(tags_no_sci)} тегов...")
        links = request_links(
            tags_no_sci, tag_names, sci_ids, {s: s for s in sci_ids},
            items_desc="теги", target_desc="ни одним учёным", target_pick_desc="учёный",
            items_label="Теги", targets_label="Существующие учёные")
        for tag, sid in links.items():
            if not sid:
                print(f"   ⚠️ {tag}: LLM не нашла подходящего учёного, пропущено")
                continue
            s = scientists.get(sid)
            if not s:
                continue
            s["related_tags"] = sorted(set(s.get("related_tags", [])) | {tag})
            fixed_sci_tags[sid] = s["related_tags"]
            print(f"   ✅ {tag} → учёный {sid}")

    if sci_no_law:
        print(f"\n🔗 Подбираю законы для {len(sci_no_law)} учёных...")
        links = request_links(
            sci_no_law, {s: s for s in sci_no_law}, law_ids, law_names,
            items_desc="учёные", target_desc="ни одним законом", target_pick_desc="закон",
            items_label="Учёные", targets_label="Существующие законы")
        for sid, lid in links.items():
            if not lid:
                print(f"   ⚠️ {sid}: LLM не нашла подходящего закона, пропущено")
                continue
            L = laws_ru.get(lid)
            if not L:
                continue
            L["scientists"] = sorted(set(L.get("scientists", [])) | {sid})
            fixed_law_sci[lid] = L["scientists"]
            print(f"   ✅ {sid} → закон {lid}")

    if fixed_law_tags:
        LAWS_LIST_PATH.write_text(json.dumps(laws_list, ensure_ascii=False, indent=2), encoding="utf-8")
        for lid, new_tags in fixed_law_tags.items():
            if lid in laws_graph:
                laws_graph[lid]["tags"] = new_tags
        sync = fixed_law_tags
        for lang in LANGS:
            p = Path(f"lang/{lang}/data/laws.json")
            if not p.exists():
                continue
            data = json.loads(p.read_text(encoding="utf-8"))
            changed = False
            for lid, new_tags in sync.items():
                if lid in data and data[lid].get("tags") != new_tags:
                    data[lid]["tags"] = new_tags
                    changed = True
            if changed:
                p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    if fixed_law_sci:
        LAWS_RU_PATH.write_text(json.dumps(laws_ru, ensure_ascii=False, indent=2), encoding="utf-8")
        for lid, new_sci in fixed_law_sci.items():
            if lid in laws_graph:
                laws_graph[lid]["scientists"] = new_sci
        for lang in LANGS:
            p = Path(f"lang/{lang}/data/laws.json")
            if not p.exists():
                continue
            data = json.loads(p.read_text(encoding="utf-8"))
            changed = False
            for lid, new_sci in fixed_law_sci.items():
                if lid in data and data[lid].get("scientists") != new_sci:
                    data[lid]["scientists"] = new_sci
                    changed = True
            if changed:
                p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    if fixed_law_tags or fixed_law_sci:
        graph_doc["graph"] = laws_graph
        LAWS_GRAPH_PATH.write_text(json.dumps(graph_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    if fixed_sci_tags:
        SCIENTISTS_PATH.write_text(json.dumps(scientists, ensure_ascii=False, indent=2), encoding="utf-8")
        for lang in LANGS:
            p = Path(f"lang/{lang}/data/scientists.json")
            if not p.exists():
                continue
            data = json.loads(p.read_text(encoding="utf-8"))
            changed = False
            for sid, new_tags in fixed_sci_tags.items():
                if sid in data and data[sid].get("related_tags") != new_tags:
                    data[sid]["related_tags"] = new_tags
                    changed = True
            if changed:
                p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    total_fixed = len(fixed_law_tags) + len(fixed_sci_tags) + len(fixed_law_sci)
    total_gaps = len(tags_no_law) + len(tags_no_sci) + len(sci_no_law)
    print(f"\n✅ Починено {total_fixed}/{total_gaps} связей.")
    print("   Дальше: python run.py html (обновить страницы + knowledge-graph.json)")


if __name__ == "__main__":
    main()
