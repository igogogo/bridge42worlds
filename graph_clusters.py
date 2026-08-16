#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Совпадает ли Лувен на взвешенном графе с кластерами, которые уже посчитала аналитика.

Волна 14 августа: «В cooc уже есть номер кластера c. Прогнать Лувена на взвешенном графе
и сказать, совпадает ли разбиение. Если да — берём готовое и не считаем дважды».

Вопрос поставлен правильно, а вот ответ «да/нет» на него дать нельзя, и это надо сказать
сразу. Два разбиения строятся на РАЗНЫХ графах: аналитика кластеризует со-встречаемость
внутри одного вида сущностей (тег с тегом, учёный с учёным), а граф знаний связывает
четыре вида между собой. Совпадать целиком им не с чего. Осмысленный вопрос — насколько
они согласны ТАМ, ГДЕ ПЕРЕСЕКАЮТСЯ, и ответ на него числовой.

ЧЕМ МЕРЯЕТСЯ СОГЛАСИЕ. Скорректированная взаимная информация и индекс Рэнда: обе меры
не зависят от нумерации кластеров (кластер 3 у одного и кластер 7 у другого — одно и то же,
если состав совпал) и обе имеют ноль на случайном разбиении. Именно поэтому здесь нет
«доли совпавших меток»: она растёт сама по себе при разном числе кластеров и обманывает.

КОНТРОЛЬ. Рядом считается то же согласие для СЛУЧАЙНОГО разбиения на столько же
кластеров. Без него любое число выглядит убедительным.

    python graph_clusters.py
    python graph_clusters.py --res 1.0
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def jl(p):
    q = pathlib.Path(p)
    return json.loads(q.read_text(encoding="utf-8")) if q.exists() else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=float, default=1.0, help="разрешение Лувена")
    ap.add_argument("--out", default=str(MAIN / "data" / "graph-clusters.json"))
    args = ap.parse_args()

    import numpy as np
    import networkx as nx
    from sklearn.metrics import adjusted_mutual_info_score, adjusted_rand_score

    g = jl(MAIN / "data/knowledge-graph.json")
    kind = {n["id"]: n["kind"] for n in g["nodes"]}
    G = nx.Graph()
    G.add_nodes_from(kind)
    for e in g["edges"]:
        w = float(e.get("w") or 0.0)
        if w > 0:
            G.add_edge(e["a"], e["b"], weight=w)
    print(f"граф: узлов {G.number_of_nodes()} · рёбер {G.number_of_edges()}")
    comps = list(nx.connected_components(G))
    print(f"компонент связности: {len(comps)} · крупнейшая {max(len(c) for c in comps)}")

    part = nx.community.louvain_communities(G, weight="weight", seed=0,
                                            resolution=args.res)
    lou = {}
    for ci, c in enumerate(part):
        for n in c:
            lou[n] = ci
    sizes = sorted((len(c) for c in part), reverse=True)
    print(f"Лувен: сообществ {len(part)} · размеры {sizes[:10]}"
          f"{' …' if len(sizes) > 10 else ''}")
    print(f"модулярность: {nx.community.modularity(G, part, weight='weight'):.3f}")

    out = {"built": "2026-08-15", "louvain_communities": len(part),
           "modularity": round(nx.community.modularity(G, part, weight="weight"), 4),
           "agreement": {}}

    rng = np.random.default_rng(0)
    for src, prefix in (("tags-cooc.json", "t:"), ("scientists-cooc.json", "s:")):
        d = jl(MAIN / f"data/analytics/{src}")
        ent = d.get("entities") or []
        pairs = [(prefix + e["id"], e["c"]) for e in ent
                 if prefix + e["id"] in lou and e.get("c") is not None]
        if len(pairs) < 30:
            print(f"\n{src}: пересечение мало ({len(pairs)}) — сравнивать нечего")
            continue
        a = np.array([lou[n] for n, _ in pairs])
        b = np.array([c for _, c in pairs])
        ami = adjusted_mutual_info_score(b, a)
        ari = adjusted_rand_score(b, a)
        # Контроль: случайное разбиение на столько же кластеров.
        r = rng.integers(0, max(b) + 1, size=len(b))
        ami_r = adjusted_mutual_info_score(b, r)
        ari_r = adjusted_rand_score(b, r)
        print(f"\n{src}: общих узлов {len(pairs)} · "
              f"кластеров аналитики {len(set(b.tolist()))}")
        print(f"  согласие с Лувеном:  AMI {ami:.3f}   ARI {ari:.3f}")
        print(f"  случайное разбиение: AMI {ami_r:.3f}   ARI {ari_r:.3f}")
        verdict = ("совпадают в основном" if ami > 0.55 else
                   "согласны частично" if ami > 0.25 else "разные разбиения")
        print(f"  вывод: {verdict}")
        out["agreement"][src] = {"nodes": len(pairs), "ami": round(float(ami), 4),
                                 "ari": round(float(ari), 4),
                                 "ami_random": round(float(ami_r), 4),
                                 "verdict": verdict}

    # Проекция кластера на узлы справочников делает ровно то, о чём просила волна:
    # соединяет граф с кластерами статей. Здесь она сохраняется как метка узла,
    # чтобы раскладка могла красить по ней.
    out["node_cluster"] = {n: int(c) for n, c in sorted(lou.items())}
    by_kind = {}
    for n, c in lou.items():
        by_kind.setdefault(kind.get(n, "?"), set()).add(c)
    print(f"\nсообществ, в которых представлен вид:")
    for k, cs in sorted(by_kind.items()):
        print(f"  {k:<5} {len(cs)}")
    mixed = sum(1 for c in part
                if len({kind.get(n, '?') for n in c}) >= 3)
    print(f"смешанных сообществ (три и более вида): {mixed} из {len(part)}")
    out["mixed_communities"] = mixed

    pathlib.Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    print(f"\n→ {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
