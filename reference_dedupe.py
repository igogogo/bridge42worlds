"""
Дедупликация справочников: теги / законы / учёные.

Проблема: активный и образовательный ярусы тегов (tag_list.py) растут независимо
друг от друга и не сверяются между собой — один и тот же тег может быть предложен
и туда, и туда (подтверждённый случай: exoplanet, superconductivity,
cosmic_microwave_background, entropy, neutrino, redshift — 6 тегов с ОДИНАКОВЫМ en-id
в обоих списках). Та же логика применима к законам (один список, но рост через
несколько раундов) и учёным (словарь по имени-ключу).

Находит дубли по нормализованному русскому имени (без LLM — чистое сравнение строк),
выбирает канонический id и сливает остальные в него: убирает лишние записи из
списков/описаний, чистит дублирующий узел в *-graph.json (объединяя article_count/
related/scientists), и переписывает все ссылки на потерянный id каноническим —
в data.json статей (tags/main_tag/extra_tags на всех уровнях и языках),
в laws-list.json/laws-graph.json (поле tags), в scientists.json (related_tags).

Запуск:
    python reference_dedupe.py            # только отчёт (dry-run)
    python reference_dedupe.py --apply     # реально правит файлы
"""
import argparse
import json
from pathlib import Path

CONFIG = json.loads(Path("config.json").read_text(encoding="utf-8"))
LANGS = CONFIG.get("languages", ["ru", "en", "es"])
DEFAULT_LANG = CONFIG.get("default_lang", "ru")


def jload(path, default):
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def jsave(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def norm(name):
    return " ".join((name or "").strip().lower().split())


def find_dupe_groups(entries):
    """entries: список (id, ru_name, source_score) -> {norm_name: [id, ...]} только группы len>1"""
    groups = {}
    for eid, name in entries:
        groups.setdefault(norm(name), []).append(eid)
    return {k: v for k, v in groups.items() if len(v) > 1}


# ---------------------------------------------------------------- ТЕГИ ----

def load_tag_context():
    active = jload("lang/ru/data/tags-list.json", [])
    edu = jload("lang/ru/data/tags-list-educational.json", [])
    graph_doc = jload("data/tags-graph.json", {"graph": {}})
    graph = graph_doc.get("graph", {})
    active_ids = {t["en"] for t in active}
    return active, edu, graph_doc, graph, active_ids


def pick_tag_canonical(ids, active_ids, graph):
    def score(eid):
        node = graph.get(eid, {})
        return (eid in active_ids, node.get("article_count", 0) or 0, eid)
    return sorted(ids, key=score, reverse=True)[0]


def dedupe_tags(apply_):
    active, edu, graph_doc, graph, active_ids = load_tag_context()

    # Случай A: ОДИН И ТОТ ЖЕ id одновременно в active и educational (list-level
    # коллизия — оба яруса независимо предложили один и тот же тег). Тут не нужен
    # редирект id (id один), нужно просто убрать лишнюю запись из educational-списка
    # и снять ошибочный флаг "educational" с узла графа (тег реально активный).
    edu_ids = {t["en"] for t in edu}
    overlap = sorted(active_ids & edu_ids)

    # Случай B: РАЗНЫЕ id с одинаковым нормализованным именем (после схлопывания
    # случая A, чтобы не путать его с этим) — полноценный редирект ссылок.
    unique_ids = {}
    for t in active:
        unique_ids[t["en"]] = t["ru"]
    for t in edu:
        unique_ids.setdefault(t["en"], t["ru"])
    groups = find_dupe_groups(list(unique_ids.items()))

    report = []
    id_map = {}  # loser -> keeper (случай B)
    for name, ids in groups.items():
        ids = sorted(set(ids))
        if len(ids) < 2:
            continue
        keep = pick_tag_canonical(ids, active_ids, graph)
        losers = [i for i in ids if i != keep]
        report.append((name, keep, losers))
        for l in losers:
            id_map[l] = keep

    if overlap:
        print(f"🏷️  Теги: {len(overlap)} id одновременно в active и educational (дубль списка): {overlap}")
    if report:
        print(f"🏷️  Теги: найдено {len(report)} групп дублей с разными id (одинаковое имя)")
        for name, keep, losers in report:
            print(f"   «{name}»: оставляем `{keep}`, убираем {losers}")
    if not overlap and not report:
        print("🏷️  Теги: дублей не найдено")

    if not apply_:
        return {**id_map, **{o: o for o in overlap}}

    # применяем случай A
    if overlap:
        edu = [t for t in edu if t["en"] not in overlap]
        for eid in overlap:
            node = graph.get(eid)
            if node is not None:
                node.pop("educational", None)
        jsave("lang/ru/data/tags-list-educational.json", edu)
        print(f"   ↳ убрано {len(overlap)} записей из tags-list-educational.json, очищен флаг educational в графе")

    loser_ids = set(id_map)

    # 1) списки
    active = [t for t in active if t["en"] not in loser_ids]
    edu = [t for t in edu if t["en"] not in loser_ids]
    jsave("lang/ru/data/tags-list.json", active)
    jsave("lang/ru/data/tags-list-educational.json", edu)

    # 2) описания по языкам
    for lang in LANGS:
        path = f"lang/{lang}/data/tags.json"
        data = jload(path, {})
        changed = False
        for l, keep in id_map.items():
            if l in data:
                if keep not in data:
                    data[keep] = data[l]
                del data[l]
                changed = True
        if changed:
            jsave(path, data)

    # 3) граф: слить узлы, почистить related у всех соседей
    active_ids_after = {t["en"] for t in active}
    for l, keep in id_map.items():
        lnode = graph.pop(l, None)
        if lnode is None:
            continue
        knode = graph.setdefault(keep, {})
        knode["article_count"] = (knode.get("article_count", 0) or 0) + (lnode.get("article_count", 0) or 0)
        knode["related"] = sorted(set(knode.get("related", [])) | set(lnode.get("related", [])) - {keep})
        knode["scientists"] = sorted(set(knode.get("scientists", [])) | set(lnode.get("scientists", [])))
        if keep in active_ids_after:
            knode.pop("educational", None)
        elif lnode.get("educational") or knode.get("educational"):
            knode["educational"] = True
    for eid, node in graph.items():
        if "related" in node:
            node["related"] = sorted({id_map.get(r, r) for r in node["related"]} - {eid})
    graph_doc["graph"] = graph
    jsave("data/tags-graph.json", graph_doc)

    _redirect_tag_refs_in_laws(id_map, apply_)
    _redirect_tag_refs_in_scientists(id_map, apply_)
    _redirect_tag_refs_in_articles(id_map)

    return {**id_map, **{o: o for o in overlap}}


def _redirect_tag_refs_in_laws(id_map, apply_):
    path = "lang/ru/data/laws-list.json"
    laws = jload(path, [])
    changed = False
    for law in laws:
        tags = law.get("tags", [])
        new_tags = sorted({id_map.get(t, t) for t in tags})
        if new_tags != sorted(tags):
            law["tags"] = new_tags
            changed = True
    if changed:
        jsave(path, laws)

    graph_path = "data/laws-graph.json"
    doc = jload(graph_path, {"graph": {}})
    graph = doc.get("graph", {})
    changed = False
    for node in graph.values():
        tags = node.get("tags", [])
        new_tags = sorted({id_map.get(t, t) for t in tags})
        if new_tags != sorted(tags):
            node["tags"] = new_tags
            changed = True
    if changed:
        doc["graph"] = graph
        jsave(graph_path, doc)

    # generate_law_page() рендерит теги закона из lang/{lang}/data/laws.json (снимок с момента
    # описания в law_describe.py), НЕ из laws-list.json — без этой синхронизации страница закона
    # продолжала бы показывать смёрженный id как есть.
    tags_by_id = {l["en"]: l["tags"] for l in laws}
    for lang in LANGS:
        p = f"lang/{lang}/data/laws.json"
        data = jload(p, {})
        changed = False
        for lid, tags in tags_by_id.items():
            if lid in data and data[lid].get("tags") != tags:
                data[lid]["tags"] = tags
                changed = True
        if changed:
            jsave(p, data)


def _redirect_tag_refs_in_scientists(id_map, apply_):
    path = "lang/ru/data/scientists.json"
    sci = jload(path, {})
    changed = False
    for entry in sci.values():
        rt = entry.get("related_tags", [])
        if not rt:
            continue
        new_rt = sorted({id_map.get(t, t) for t in rt})
        if new_rt != sorted(rt):
            entry["related_tags"] = new_rt
            changed = True
    if changed:
        jsave(path, sci)


def _redirect_tag_refs_in_articles(id_map):
    files = list(Path("lang/ru/archive").glob("*/*/data.json"))
    n_changed = 0
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        changed = False

        tags = data.get("tags", [])
        new_tags = sorted({id_map.get(t, t) for t in tags})
        if new_tags != sorted(tags):
            data["tags"] = new_tags
            changed = True

        if data.get("main_tag") in id_map:
            data["main_tag"] = id_map[data["main_tag"]]
            changed = True

        for version in ("popular", "simple", "advanced"):
            block = data.get(version, {})
            if not isinstance(block, dict):
                continue
            for lang, vdata in block.items():
                if not isinstance(vdata, dict):
                    continue
                if vdata.get("main_tag") in id_map:
                    vdata["main_tag"] = id_map[vdata["main_tag"]]
                    changed = True
                extra = vdata.get("extra_tags")
                if extra:
                    new_extra = [id_map.get(t, t) for t in extra]
                    if new_extra != extra:
                        vdata["extra_tags"] = new_extra
                        changed = True

        if changed:
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            n_changed += 1
    if n_changed:
        print(f"   ↳ обновлено {n_changed} data.json статей")


# ---------------------------------------------------------------- ЗАКОНЫ ----

def dedupe_laws(apply_):
    path = "lang/ru/data/laws-list.json"
    laws = jload(path, [])
    graph_doc = jload("data/laws-graph.json", {"graph": {}})
    graph = graph_doc.get("graph", {})
    laws_desc = jload("lang/ru/data/laws.json", {})

    entries = [(l["en"], l["ru"]) for l in laws]
    groups = find_dupe_groups(entries)
    if not groups:
        print("⚖️  Законы: дублей не найдено")
        return {}

    def score(eid):
        desc = laws_desc.get(eid, {})
        has_desc = bool(desc.get("description_advanced") or desc.get("description"))
        node = graph.get(eid, {})
        return (has_desc, len(node.get("tags", [])), eid)

    report = []
    id_map = {}
    for name, ids in groups.items():
        ids = sorted(set(ids))
        keep = sorted(ids, key=score, reverse=True)[0]
        losers = [i for i in ids if i != keep]
        report.append((name, keep, losers))
        for l in losers:
            id_map[l] = keep

    print(f"⚖️  Законы: найдено {len(report)} групп дублей")
    for name, keep, losers in report:
        print(f"   «{name}»: оставляем `{keep}`, убираем {losers}")

    if not apply_:
        return id_map

    loser_ids = set(id_map)
    laws = [l for l in laws if l["en"] not in loser_ids]
    jsave(path, laws)

    for lang in LANGS:
        p = f"lang/{lang}/data/laws.json"
        data = jload(p, {})
        changed = False
        for l, keep in id_map.items():
            if l in data:
                if keep not in data:
                    data[keep] = data[l]
                del data[l]
                changed = True
        if changed:
            jsave(p, data)

    for l, keep in id_map.items():
        lnode = graph.pop(l, None)
        if lnode is None:
            continue
        knode = graph.setdefault(keep, {})
        knode["tags"] = sorted(set(knode.get("tags", [])) | set(lnode.get("tags", [])))
        knode["scientists"] = sorted(set(knode.get("scientists", [])) | set(lnode.get("scientists", [])))
        knode["related"] = sorted(set(knode.get("related", [])) | set(lnode.get("related", [])) - {keep})
    for eid, node in graph.items():
        if "related" in node:
            node["related"] = sorted({id_map.get(r, r) for r in node["related"]} - {eid})
    graph_doc["graph"] = graph
    jsave("data/laws-graph.json", graph_doc)

    return id_map


# --------------------------------------------------------------- УЧЁНЫЕ ----

def dedupe_scientists(apply_):
    path = "lang/ru/data/scientists.json"
    sci = jload(path, {})
    entries = [(k, v.get("name", k)) for k, v in sci.items()]
    groups = find_dupe_groups(entries)
    if not groups:
        print("👨‍🔬 Учёные: дублей не найдено")
        return {}

    def score(key):
        v = sci.get(key, {})
        return (bool(v.get("biography")), len(v.get("related_tags", [])), key)

    report = []
    id_map = {}
    for name, keys in groups.items():
        keys = sorted(set(keys))
        keep = sorted(keys, key=score, reverse=True)[0]
        losers = [k for k in keys if k != keep]
        report.append((name, keep, losers))
        for l in losers:
            id_map[l] = keep

    print(f"👨‍🔬 Учёные: найдено {len(report)} групп дублей")
    for name, keep, losers in report:
        print(f"   «{name}»: оставляем `{keep}`, убираем {losers}")

    if not apply_:
        return id_map

    loser_keys = set(id_map)
    for k in loser_keys:
        sci.pop(k, None)
    jsave(path, sci)

    for lang in LANGS:
        if lang == DEFAULT_LANG:
            continue
        p = f"lang/{lang}/data/scientists.json"
        data = jload(p, {})
        changed = False
        for l in loser_keys:
            if l in data:
                del data[l]
                changed = True
        if changed:
            jsave(p, data)

    # ссылки на учёных в data.json статей — поле scientists (top-level + версии)
    files = list(Path("lang/ru/archive").glob("*/*/data.json"))
    n_changed = 0
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        changed = False
        sci_list = data.get("scientists", [])
        new_list = [id_map.get(s, s) for s in sci_list]
        if new_list != sci_list:
            data["scientists"] = sorted(set(new_list))
            changed = True
        for version in ("popular", "simple", "advanced"):
            block = data.get(version, {})
            if not isinstance(block, dict):
                continue
            for vdata in block.values():
                if not isinstance(vdata, dict):
                    continue
                vs = vdata.get("scientists")
                if vs:
                    new_vs = [id_map.get(s, s) for s in vs]
                    if new_vs != vs:
                        vdata["scientists"] = new_vs
                        changed = True
        if changed:
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            n_changed += 1
    if n_changed:
        print(f"   ↳ обновлено {n_changed} data.json статей")

    # ссылки на учёных в laws-list.json / tags-graph.json / laws-graph.json
    for path2, key in (("data/tags-graph.json", "graph"), ("data/laws-graph.json", "graph")):
        doc = jload(path2, {"graph": {}})
        graph = doc.get(key, {})
        changed = False
        for node in graph.values():
            sc = node.get("scientists", [])
            new_sc = sorted({id_map.get(s, s) for s in sc})
            if new_sc != sorted(sc):
                node["scientists"] = new_sc
                changed = True
        if changed:
            doc[key] = graph
            jsave(path2, doc)

    return id_map


def main():
    ap = argparse.ArgumentParser(description="Дедупликация тегов/законов/учёных")
    ap.add_argument("--apply", action="store_true", help="реально править файлы (без флага — только отчёт)")
    args = ap.parse_args()

    print(f"{'🔧 ПРИМЕНЯЮ ИЗМЕНЕНИЯ' if args.apply else '👀 DRY-RUN (только отчёт, для правки — запусти с --apply)'}\n")

    tag_map = dedupe_tags(args.apply)
    law_map = dedupe_laws(args.apply)
    sci_map = dedupe_scientists(args.apply)

    total = len(tag_map) + len(law_map) + len(sci_map)
    if args.apply and total:
        print(f"\n✅ Готово: слито {len(tag_map)} тегов, {len(law_map)} законов, {len(sci_map)} учёных.")
        print("   Дальше: python run.py html   (пересобрать индексы/HTML с чистыми ссылками)")
    elif not args.apply and total:
        print(f"\nℹ️  Всего {total} дублей найдено. Запусти с --apply, чтобы применить.")
    else:
        print("\n✅ Дублей не найдено — справочники чистые.")


if __name__ == "__main__":
    main()
