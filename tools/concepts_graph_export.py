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

    # СМЫСЛОВЫЕ РЁБРА для тех, у кого статей нет вовсе. Мощность ребра у нас —
    # число общих статей, и это верно для понятий, добытых из статей. Но константа
    # пришла из формулы, а статистический метод из канона предмета: статей у них
    # ноль, значит ноль и рёбер — в графе они висят отдельными точками. Владелец
    # 27.08: «сирота относительно статьи оправдана, сирот не должно быть
    # относительно связей внутри понятий». Берём соседей из related (их считает
    # супер по близости карточек), вес 1 — слабее любой статейной связи, чтобы
    # калибровка кадра не приняла их за главные.
    linked = {a for a, _b in keep} | {b for _a, b in keep}
    added = 0
    for cid, v in live.items():
        i = idx[cid]
        if i in linked or v.get("articles"):
            continue
        for r in (v.get("related") or [])[:4]:
            j = idx.get(r["id"])
            if j is None or j == i:
                continue
            pair = (min(i, j), max(i, j))
            if pair in keep:
                continue
            keep.add(pair)
            edges.append([pair[0], pair[1], 1])
            added += 1
    if added:
        edges.sort(key=lambda e: (e[0], e[1]))
        print(f"  смысловых рёбер для понятий без статей: {added}")

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

    # раздел arXiv узла — по статьям (владелец 27.08: «через статьи смотреть
    # на граф, фильтровать разделами») — верхнеуровневый архивный префикс
    idx_p = ROOT / "lang" / "ru" / "articles-index.json"
    art_cat = {}
    if idx_p.exists():
        for a in json.loads(idx_p.read_text(encoding="utf-8")):
            c = (a.get("primary_category") or "").split(".")[0]
            if c:
                art_cat[a["id"]] = c
                art_cat[a["id"].split("v")[0]] = c

    def top_cat(v):
        cnt = Counter(art_cat.get(a) for a in v.get("articles") or [])
        cnt.pop(None, None)
        return cnt.most_common(1)[0][0] if cnt else None

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
            # карточка в тултип — «наведись и учись» (обрезка до предложения)
            "card": (v.get("card_en") or "")[:220],
            "cat": top_cat(v),
        })

    # ФОРМУЛЫ — узлами (владелец: «формулы тут должны появиться, всё в блоке»):
    # 642 основных формы, связь формула→понятие с весом = применениям
    fml_p = ROOT.parent / "b42-ml" / "data" / "formulas-linked.json"
    if fml_p.exists():
        bases = json.loads(fml_p.read_text(encoding="utf-8"))["bases"]
        for b in bases:
            fi = len(nodes)
            fname = b.get("name") or b["base_id"].replace("_", " ")
            fcat, fg = None, None
            for c in (b.get("concepts") or []):
                if c["concept"] in idx:
                    ci = idx[c["concept"]]
                    fg = nodes[ci]["g"] if fg is None else fg
                    fcat = nodes[ci]["cat"] if fcat is None else fcat
            nodes.append({
                "id": "f:" + b["base_id"], "en": fname, "ru": "",
                "kind": "formula", "g": fg,
                "n": len(b.get("applications") or []),
                "card": (b.get("latex") or "")[:120],
                "cat": fcat,
            })
            for c in (b.get("concepts") or [])[:4]:
                if c["concept"] in idx:
                    edges.append([idx[c["concept"]], fi,
                                  1 + len(b.get("applications") or [])])
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
