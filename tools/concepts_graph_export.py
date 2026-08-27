# -*- coding: utf-8 -*-
"""Данные визуального графа понятий → data/concepts-graph.json.

Владелец 27.08: «визуальный граф для понятий… внутренние связи, мощность рёбер,
обусловленная статьями, разные элементы, дриллдауны, панель навигации, режим 3D».

Вес ребра — ЧИСЛО ОБЩИХ СТАТЕЙ двух понятий (не векторная близость: то, что
реально стоит рядом в корпусе). Считается инвертированным индексом статья →
понятия; ребро остаётся, если w >= 2, и режется до топ-12 на узел — иначе
хабы («чёрная дыра») тянут сотни рёбер и кадр нечитаем.

Пока статикой на клиента — «на клиенте потренируемся»; в динамике тот же JSON
будет отдавать воркер кадрами.

    {"nodes": [{"id","en","ru","kind","g","n"}],      g = индекс группы
     "edges": [[a,b,w]],                              индексы узлов
     "groups": [{"id","label_en","label_ru","members":[...]}]}

    python tools/concepts_graph_export.py
"""
import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "concepts-graph.json"
LIVE = ROOT / "data" / "concepts-live.json"

EDGE_MIN = 2      # меньше двух общих статей — совпадение, не связь
TOP_PER_NODE = 12


def main():
    doc = json.loads(LIVE.read_text(encoding="utf-8"))
    live = doc["concepts"]
    groups_raw = doc.get("groups") or {}

    cids = sorted(live)
    idx = {c: i for i, c in enumerate(cids)}

    # вес рёбер: инвертированный индекс статья → понятия
    by_art = defaultdict(list)
    for cid, v in live.items():
        for aid in v.get("articles") or []:
            by_art[aid].append(idx[cid])
    w = Counter()
    for members in by_art.values():
        if len(members) < 2 or len(members) > 60:
            continue          # статья с 60+ понятиями — разметочный шум, не свидетель
        for a, b in combinations(sorted(members), 2):
            w[(a, b)] += 1

    # топ-12 на узел, порог 2
    per_node = defaultdict(list)
    for (a, b), n in w.items():
        if n >= EDGE_MIN:
            per_node[a].append((n, b))
            per_node[b].append((n, a))
    keep = set()
    for a, lst in per_node.items():
        for n, b in sorted(lst, reverse=True)[:TOP_PER_NODE]:
            keep.add((min(a, b), max(a, b)))
    edges = [[a, b, w[(a, b)]] for a, b in sorted(keep)]

    # группы: членство из supers (первая группа понятия)
    gids = sorted(groups_raw, key=lambda g: -len(groups_raw[g]))
    gindex = {g: i for i, g in enumerate(gids)}

    def group_of(cid):
        sups = live[cid].get("supers") or []
        return gindex.get(str(sups[0])) if sups else None

    def label(gid, lang):
        members = sorted(groups_raw[gid],
                         key=lambda m: -len(live.get(m, {}).get("articles", [])))
        names = []
        for m in members[:3]:
            v = live.get(m)
            if v:
                names.append((v.get("names") or {}).get(lang)
                             or (v.get("names") or {}).get("en")
                             or m.replace("_", " "))
        return " · ".join(names) or str(gid)

    nodes = []
    for cid in cids:
        v = live[cid]
        nodes.append({
            "id": cid,
            "en": (v.get("names") or {}).get("en") or cid.replace("_", " "),
            "ru": (v.get("names") or {}).get("ru") or "",
            "kind": v.get("kind") or "concept",
            "g": group_of(cid),
            "n": len(v.get("articles") or []),
        })
    groups = [{"id": g, "label_en": label(g, "en"), "label_ru": label(g, "ru"),
               "members": [idx[m] for m in groups_raw[g] if m in idx]}
              for g in gids]

    OUT.write_text(json.dumps({"nodes": nodes, "edges": edges, "groups": groups},
                              ensure_ascii=False), encoding="utf-8")
    kb = OUT.stat().st_size // 1024
    print(f"✅ граф: {len(nodes)} узлов, {len(edges)} рёбер, {len(groups)} групп"
          f" → {OUT.name} ({kb} КБ)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
