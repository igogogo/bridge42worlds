#!/usr/bin/env python3
"""Чинит ИЗОЛИРОВАННЫЕ активные теги — на которые не ссылается НИ ОДИН закон и НИ ОДИН
учёный (обратное направление к law_tags_repair.py/scientist_tags_repair.py: те чинят
закон/учёного без тегов, этот — тег без закона/учёного). Такой тег висит в графе знаний
изолированным узлом без единой связи.

Один батч-вызов на все изолированные теги сразу (не по одному — дешевле и ЛУЧШЕ, модель
видит соседние теги и не путает похожие домены). Честно возвращает null, если для тега
реально нет подходящего закона/учёного среди существующих — не притягивает связь силой.

Запуск:
    python tag_connectivity_repair.py            # только отчёт (dry-run)
    python tag_connectivity_repair.py --apply     # реально правит (1 LLM-вызов)
"""
import argparse
import json
from pathlib import Path

from common import CONFIG, chat, load_prompt, parse_json_salvage

TAGS_PATH = Path("lang/ru/data/tags-list.json")
LAWS_PATH = Path("lang/ru/data/laws-list.json")
SCIENTISTS_PATH = Path("lang/ru/data/scientists.json")
LAWS_GRAPH_PATH = Path("data/laws-graph.json")
LANGS = CONFIG.get("languages", ["ru", "en", "es"])


def find_isolated(tags, laws, scientists):
    active_ids = {t["en"] for t in tags}
    from_laws = set()
    for l in laws:
        from_laws.update(l.get("tags", []))
    from_sci = set()
    for s in scientists.values():
        from_sci.update(s.get("related_tags", []))
    return sorted(active_ids - from_laws - from_sci)


def main():
    ap = argparse.ArgumentParser(description="Чинит изолированные теги (без закона/учёного)")
    ap.add_argument("--apply", action="store_true", help="реально править (1 LLM-вызов), без флага — только отчёт")
    args = ap.parse_args()

    tags = json.loads(TAGS_PATH.read_text(encoding="utf-8"))
    laws = json.loads(LAWS_PATH.read_text(encoding="utf-8"))
    scientists = json.loads(SCIENTISTS_PATH.read_text(encoding="utf-8"))

    isolated = find_isolated(tags, laws, scientists)
    if not isolated:
        print("✅ Все активные теги связаны хотя бы с одним законом или учёным.")
        return

    print(f"⚠️ {len(isolated)}/{len(tags)} активных тегов без связи ни с одним законом, ни с учёным:")
    for t in isolated:
        print(f"   {t}")

    if not args.apply:
        print("\nℹ️  Запусти с --apply, чтобы восстановить связи через LLM (1 батч-вызов).")
        return

    prompt = load_prompt("tag-connectivity-repair").format(
        tags_json=json.dumps(isolated, ensure_ascii=False),
        laws_json=json.dumps([{"id": l["en"], "name": l["ru"]} for l in laws], ensure_ascii=False),
        scientists_json=json.dumps(list(scientists.keys()), ensure_ascii=False),
    )
    try:
        r = chat("laws_list", prompt)
        data = parse_json_salvage(r.choices[0].message.content) or {}
        links = data.get("links", [])
    except Exception as e:
        print(f"   ❌ ошибка LLM: {e}")
        return

    law_by_id = {l["en"]: l for l in laws}
    fixed_laws, fixed_sci, skipped = {}, {}, []
    for link in links:
        tag, ttype, tid = link.get("tag"), link.get("target_type"), link.get("target_id")
        if tag not in isolated:
            continue
        if ttype == "law" and tid in law_by_id:
            law = law_by_id[tid]
            if tag not in law.get("tags", []):
                law["tags"] = sorted(set(law.get("tags", [])) | {tag})
            fixed_laws[tid] = law["tags"]
            print(f"   ✅ {tag} → закон {tid}")
        elif ttype == "scientist" and tid in scientists:
            s = scientists[tid]
            if tag not in s.get("related_tags", []):
                s["related_tags"] = sorted(set(s.get("related_tags", [])) | {tag})
            fixed_sci[tid] = s["related_tags"]
            print(f"   ✅ {tag} → учёный {tid}")
        else:
            skipped.append(tag)
            print(f"   ⚠️ {tag}: LLM не нашла подходящей связи, пропущено")

    if fixed_laws:
        LAWS_PATH.write_text(json.dumps(laws, ensure_ascii=False, indent=2), encoding="utf-8")
        if LAWS_GRAPH_PATH.exists():
            graph_doc = json.loads(LAWS_GRAPH_PATH.read_text(encoding="utf-8"))
            graph = graph_doc.get("graph", {})
            for lid, new_tags in fixed_laws.items():
                if lid in graph:
                    graph[lid]["tags"] = new_tags
            graph_doc["graph"] = graph
            LAWS_GRAPH_PATH.write_text(json.dumps(graph_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    if fixed_sci:
        SCIENTISTS_PATH.write_text(json.dumps(scientists, ensure_ascii=False, indent=2), encoding="utf-8")

    # Страницы законов/учёных рендерятся из lang/{lang}/data/laws.json и scientists.json
    # (снимки, сделанные law_describe.py/на момент генерации) — без синхронизации починенные
    # связи не отразились бы на живых страницах (тот же баг, что чинили в law_tags_repair.py).
    for lang in LANGS:
        lp = Path(f"lang/{lang}/data/laws.json")
        if lp.exists() and fixed_laws:
            data = json.loads(lp.read_text(encoding="utf-8"))
            changed = False
            for lid, new_tags in fixed_laws.items():
                if lid in data and data[lid].get("tags") != new_tags:
                    data[lid]["tags"] = new_tags
                    changed = True
            if changed:
                lp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        sp = Path(f"lang/{lang}/data/scientists.json")
        if sp.exists() and fixed_sci:
            data = json.loads(sp.read_text(encoding="utf-8"))
            changed = False
            for sid, new_tags in fixed_sci.items():
                if sid in data and data[sid].get("related_tags") != new_tags:
                    data[sid]["related_tags"] = new_tags
                    changed = True
            if changed:
                sp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n✅ Починено {len(fixed_laws) + len(fixed_sci)}/{len(isolated)} тегов "
          f"({len(fixed_laws)} → законы, {len(fixed_sci)} → учёные, {len(skipped)} честно пропущено).")
    print("   Дальше: python run.py html")


if __name__ == "__main__":
    main()
