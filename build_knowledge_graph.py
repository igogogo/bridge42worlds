#!/usr/bin/env python3
"""Единый граф знаний из трёх сущностей (теги ⇄ законы ⇄ учёные) → data/knowledge-graph.json.

Собирает ВСЕ попарные связи в одну типизированную структуру (many-to-many между 3 сущностями),
чтобы на любом графе можно было переключать, какие типы рёбер/узлов показывать.

Узел: {"id": "t:tagid|l:lawid|s:Name", "kind": "tag|law|sci", "sub": level/type}.
Ребро: {"a", "b", "t"} где t ∈ {tag-tag, law-law, sci-sci, law-tag, sci-tag, law-sci} (неориентир., дедуп).
Имена НЕ храним — резолвятся на клиенте из tags.json/laws.json/scientists.json (язык-агностично).
Офлайн, без API. Источники: data/tags-graph.json, data/laws-graph.json, lang/{default}/data/scientists.json.
"""

import json
from pathlib import Path

from common import DEFAULT_LANG


def _jl(p):
    p = Path(p)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def main():
    tg = _jl("data/tags-graph.json").get("graph", {})
    lg = _jl("data/laws-graph.json").get("graph", {})
    sci = _jl(f"lang/{DEFAULT_LANG}/data/scientists.json")

    nodes = {}
    for tid, n in tg.items():
        nodes[f"t:{tid}"] = {"id": f"t:{tid}", "kind": "tag", "sub": n.get("level", "concept")}
    for lid, n in lg.items():
        nodes[f"l:{lid}"] = {"id": f"l:{lid}", "kind": "law", "sub": n.get("type", "закон")}
    for name in sci:
        nodes[f"s:{name}"] = {"id": f"s:{name}", "kind": "sci", "sub": "sci"}

    edges = set()  # (min,max,type) — неориентированные, дедуп

    def add(a, b, t):
        if a in nodes and b in nodes and a != b:
            edges.add((min(a, b), max(a, b), t))

    # tag ↔ tag
    for tid, n in tg.items():
        for r in n.get("related", []):
            add(f"t:{tid}", f"t:{r}", "tag-tag")
    # law ↔ law
    for lid, n in lg.items():
        for r in n.get("related", []):
            add(f"l:{lid}", f"l:{r}", "law-law")
    # law ↔ tag, law ↔ sci (открыли), law ↔ sci (оказали влияние — отдельный тип ребра,
    # см. закон↔учёный полнота: Пуанкаре/Лоренц у теории относительности, Гук у законов
    # Ньютона — не первооткрыватели, но реальный вклад не должен теряться из графа)
    for lid, n in lg.items():
        for t in n.get("tags", []):
            add(f"l:{lid}", f"t:{t}", "law-tag")
        for s in n.get("scientists", []):
            add(f"l:{lid}", f"s:{s}", "law-sci")
        for s in n.get("influenced_by", []):
            add(f"l:{lid}", f"s:{s}", "law-influence")
    # sci ↔ tag (объединяем из учёных и из тегов)
    for name, s in sci.items():
        for t in s.get("related_tags", []):
            add(f"s:{name}", f"t:{t}", "sci-tag")
    for tid, n in tg.items():
        for s in n.get("scientists", []):
            add(f"s:{s}", f"t:{tid}", "sci-tag")
    # sci ↔ sci — выводим из общих законов (соавторы открытия)
    law_scis = {}
    for lid, n in lg.items():
        ss = [s for s in n.get("scientists", []) if f"s:{s}" in nodes]
        for i in range(len(ss)):
            for j in range(i + 1, len(ss)):
                add(f"s:{ss[i]}", f"s:{ss[j]}", "sci-sci")

    edge_list = [{"a": a, "b": b, "t": t} for (a, b, t) in sorted(edges)]
    out = {"nodes": list(nodes.values()), "edges": edge_list}
    Path("data").mkdir(exist_ok=True)
    Path("data/knowledge-graph.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")

    by_type = {}
    for e in edge_list:
        by_type[e["t"]] = by_type.get(e["t"], 0) + 1
    kinds = {"tag": 0, "law": 0, "sci": 0}
    for n in nodes.values():
        kinds[n["kind"]] += 1
    print(f"✅ knowledge-graph.json: узлов {len(nodes)} (тег {kinds['tag']}, закон {kinds['law']}, учёный {kinds['sci']}), рёбер {len(edge_list)}")
    print("   по типам: " + " · ".join(f"{k}={v}" for k, v in sorted(by_type.items())))


if __name__ == "__main__":
    main()
