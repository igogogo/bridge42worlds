#!/usr/bin/env python3
"""Единый граф знаний из четырёх сущностей (теги ⇄ законы ⇄ учёные ⇄ разделы arXiv) →
data/knowledge-graph.json.

Собирает ВСЕ попарные связи в одну типизированную структуру (many-to-many между сущностями),
чтобы на любом графе можно было переключать, какие типы рёбер/узлов показывать.

Узел: {"id": "t:tagid|l:lawid|s:Name|c:catid", "kind": "tag|law|sci|cat", "sub": level/type}.
Ребро: {"a", "b", "t"} где t ∈ {tag-tag, law-law, sci-sci, law-tag, sci-tag, law-sci, cat-tag}
(неориентир., дедуп). Имена НЕ храним — резолвятся на клиенте (тег/закон/учёный — из
tags.json/laws.json/scientists.json; раздел — из /data/arxiv-categories.json, уже используется
поиском для .cat-chip). Раздел↔тег выводится из articles-index.json (какие теги встречаются в
статьях каждого раздела) — прямой связи раздел↔тег нигде не хранится, это агрегат по корпусу.
Офлайн, без API. Источники: data/tags-graph.json, data/laws-graph.json,
lang/{default}/data/scientists.json, data/arxiv-categories.json, lang/{default}/articles-index.json.
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
    cats = _jl("data/arxiv-categories.json")

    nodes = {}
    for tid, n in tg.items():
        nodes[f"t:{tid}"] = {"id": f"t:{tid}", "kind": "tag", "sub": n.get("level", "concept")}
    for lid, n in lg.items():
        nodes[f"l:{lid}"] = {"id": f"l:{lid}", "kind": "law", "sub": n.get("type", "закон")}
    for name in sci:
        nodes[f"s:{name}"] = {"id": f"s:{name}", "kind": "sci", "sub": "sci"}
    for cid in cats:
        nodes[f"c:{cid}"] = {"id": f"c:{cid}", "kind": "cat", "sub": "cat"}

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
    # cat ↔ tag — агрегат по корпусу: раздел статьи связан со всеми тегами этой статьи
    idx = _jl(f"lang/{DEFAULT_LANG}/articles-index.json")
    if isinstance(idx, list):
        for a in idx:
            if a.get("version") != "popular":
                continue
            cat = a.get("primary_category")
            if not cat:
                continue
            for t in a.get("tags", []):
                add(f"c:{cat}", f"t:{t}", "cat-tag")

    # ── КВОТЫ СВЯЗЕЙ (владелец 2026-08-01) ────────────────────────────────────────
    # «Учёный не может быть связан с десятью учёными — только с тремя, с двумя
    # основными законами и тремя тегами. Оставить только существенные».
    #
    # Зачем. Без квот граф превращается в клубок: 8575 рёбер на 773 узла, из них 48% —
    # один-единственный тип «учёный↔тег», а у хабов вроде «спектроскопия» по 229 связей.
    # Читатель видит месиво и не может проследить ни одной мысли — а граф ровно для
    # этого и нужен.
    #
    # Как выбираем «существенные». Веса у рёбер нет, поэтому берём меру важности самого
    # соседа: у тега и закона — число статей (article_count), у учёного — число законов
    # и тегов, где он назван. Связь с общеизвестным узлом информативнее случайной.
    # Квота ДВУСТОРОННЯЯ: ребро остаётся, только если помещается в квоту обоих концов —
    # иначе хаб просто выбрал бы все свои связи первым, и слабый узел снова остался бы
    # без единой.
    QUOTA = {                       # сколько связей одного узла с узлами данного вида
        ("sci", "sci"): 3, ("sci", "law"): 2, ("sci", "tag"): 3,
        ("law", "law"): 3, ("law", "tag"): 4, ("law", "sci"): 3,
        ("tag", "tag"): 4, ("tag", "sci"): 3, ("tag", "law"): 3,
        ("cat", "tag"): 12, ("tag", "cat"): 2,
    }

    def importance(nid):
        kind = nodes[nid]["kind"]
        key = nid[2:]
        if kind == "tag":
            return (tg.get(key) or {}).get("article_count", 0)
        if kind == "law":
            return len((lg.get(key) or {}).get("tags", [])) * 3 + \
                   len((lg.get(key) or {}).get("related", []))
        if kind == "sci":
            s = sci.get(key) or {}
            return len(s.get("related_tags", [])) + len(s.get("laws", [])) * 3
        return 0

    def prune(edge_set):
        """Оставляем существенные: сортируем по важности пары и режем по квотам обоих концов."""
        ranked = sorted(edge_set, key=lambda e: -(importance(e[0]) + importance(e[1])))
        used = {}
        kept = []
        for a, b, t in ranked:
            ka, kb = nodes[a]["kind"], nodes[b]["kind"]
            qa, qb = QUOTA.get((ka, kb)), QUOTA.get((kb, ka))
            if qa is None and qb is None:
                kept.append((a, b, t))
                continue
            na = used.get((a, kb), 0)
            nb = used.get((b, ka), 0)
            if (qa is not None and na >= qa) or (qb is not None and nb >= qb):
                continue
            used[(a, kb)] = na + 1
            used[(b, ka)] = nb + 1
            kept.append((a, b, t))
        return kept

    before = len(edges)
    edges = prune(edges)
    print(f"   квоты связей: {before} → {len(edges)} рёбер (убрано {before - len(edges)})")

    edge_list = [{"a": a, "b": b, "t": t} for (a, b, t) in sorted(edges)]
    out = {"nodes": list(nodes.values()), "edges": edge_list}
    Path("data").mkdir(exist_ok=True)
    Path("data/knowledge-graph.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")

    by_type = {}
    for e in edge_list:
        by_type[e["t"]] = by_type.get(e["t"], 0) + 1
    kinds = {"tag": 0, "law": 0, "sci": 0, "cat": 0}
    for n in nodes.values():
        kinds[n["kind"]] += 1
    print(f"✅ knowledge-graph.json: узлов {len(nodes)} (тег {kinds['tag']}, закон {kinds['law']}, учёный {kinds['sci']}, "
          f"раздел {kinds['cat']}), рёбер {len(edge_list)}")
    print("   по типам: " + " · ".join(f"{k}={v}" for k, v in sorted(by_type.items())))


if __name__ == "__main__":
    main()
