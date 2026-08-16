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
from common import write_json_atomic


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

    # ── ВЕС СВЯЗИ И ПОРОГ ЗНАЧИМОСТИ ─────────────────────────────────────────────
    # История этого места. 1 августа владелец сказал: «учёный не может быть связан с
    # десятью учёными — только с тремя, с двумя основными законами и тремя тегами,
    # оставить только существенные». Тогда стояла обратная беда: 8575 рёбер на 773 узла,
    # у хаба «спектроскопия» 229 связей, читатель видел месиво. Появились жёсткие квоты.
    #
    # 14 августа владелец увидел следствие: «граф кажется монотонным — количество связей
    # на узел одинаковой мощности, поэтому он отображается как шар; хотелось бы видеть
    # структуру, кластеризованную». И он прав по цифрам: квоты выбрасывали 82% рёбер
    # (12 464 → 2 281) и делали степень почти константой — у разделов медиана равнялась
    # максимуму (12 и 12), у законов 5 при максимуме 10. Когда у всех узлов одинаковое
    # число связей, структуры в графе не может быть по определению: это и есть шар.
    #
    # Лечим не отменой ограничения, а заменой инструмента. Квота говорит «не больше N» —
    # это ограничение по счёту, оно стирает разницу между узлами. Порог говорит «слабее
    # X не берём» — это ограничение по СМЫСЛУ, и оно разницу сохраняет: у хаба остаётся
    # много сильных связей, у периферии мало. Клубок при этом не возвращается, потому что
    # слабые связи отсекаются жёстче прежнего.
    #
    # Вес считаем по корпусу: сколько статей упоминают оба конца ребра. Это честная мера —
    # «Эйнштейн и ОТО» встречаются вместе постоянно, случайный тег с законом один раз.
    # Нормируем по типу ребра (у cat-tag счёт на порядок выше, чем у sci-sci), иначе один
    # порог для всех типов бессмыслен.
    idx_articles = idx if isinstance(idx, list) else []
    pair_cnt = {}
    ent_cnt = {}

    def _ents(a):
        out = []
        for t_ in (a.get("tags") or []):
            out.append(f"t:{t_}")
        for l_ in (a.get("laws") or []):
            out.append(f"l:{l_}")
        for s_ in (a.get("scientists") or []):
            out.append(f"s:{s_}")
        c_ = a.get("primary_category")
        if c_:
            out.append(f"c:{c_}")
        return [x for x in out if x in nodes]

    for a in idx_articles:
        if a.get("version") != "popular":
            continue
        es = _ents(a)
        for e_ in es:
            ent_cnt[e_] = ent_cnt.get(e_, 0) + 1
        for i in range(len(es)):
            for j in range(i + 1, len(es)):
                k = (min(es[i], es[j]), max(es[i], es[j]))
                pair_cnt[k] = pair_cnt.get(k, 0) + 1

    def raw_weight(a, b):
        """Со-встречаемость, нормированная на частоту концов (мера Жаккара).

        Голый счёт совпадений выдавал бы вперёд всё, что связано с самыми частыми
        сущностями, — то есть ту же «важность соседа», от которой мы уходим. Жаккар
        отвечает на другой вопрос: насколько эти двое ходят ПАРОЙ, а не поодиночке.
        """
        n = pair_cnt.get((min(a, b), max(a, b)), 0)
        if not n:
            return 0.0
        ca, cb = ent_cnt.get(a, 0), ent_cnt.get(b, 0)
        denom = ca + cb - n
        return n / denom if denom > 0 else 0.0

    # Нормировка внутри типа: делим на 90-й перцентиль своего типа, чтобы порог был
    # сравним для cat-tag (сотни статей) и sci-sci (единицы).
    by_type_w = {}
    for (a, b, tp) in edges:
        by_type_w.setdefault(tp, []).append(raw_weight(a, b))
    scale = {}
    for tp, arr in by_type_w.items():
        arr = sorted(x for x in arr if x > 0)
        scale[tp] = arr[int(len(arr) * 0.9)] if arr else 1.0
        if not scale[tp]:
            scale[tp] = 1.0

    THRESHOLD = 0.08      # слабее — не связь, а совпадение
    KEEP_MIN = 2          # столько лучших связей узел сохраняет всегда: изолированных быть не должно
    # Колпак должен быть НЕДОСТИЖИМ для обычного узла — иначе он снова стирает разницу,
    # только сверху. Замер на колпаке 40: у всех 60 разделов степень оказалась ровно 40,
    # у тегов 90-й перцентиль тоже 40 — та же плоскость, что была при квотах. Ставим 90:
    # его достигают единицы, и это уже настоящая патология, а не «популярная тема».
    MAX_DEG = 90
    # Связь из справочника, которой нет ни в одной статье (закон записан за учёным, но
    # вместе они у нас пока не встречались), — это не мусор, а структурная правда.
    # Оставляем её с минимальным весом, чтобы раскладка не считала её нулевой.
    MIN_W = 0.04

    def weight(a, b, tp):
        return min(1.0, max(MIN_W, raw_weight(a, b) / scale[tp]))

    def prune(edge_set):
        """Порог по весу + гарантия связности + колпак на хабы.

        Порядок важен. Сначала считаем вес всем, потом каждый узел «бронирует» свои
        KEEP_MIN лучших рёбер — иначе редкая сущность с одной слабой связью выпала бы
        из графа совсем (сейчас таких изолированных 30). Затем добираем всё, что выше
        порога, пока не упрёмся в колпак.
        """
        wt = {}
        for (a, b, tp) in edge_set:
            wt[(a, b, tp)] = weight(a, b, tp)
        by_node = {}
        for (a, b, tp), w in wt.items():
            by_node.setdefault(a, []).append(((a, b, tp), w))
            by_node.setdefault(b, []).append(((a, b, tp), w))
        for k in by_node:
            by_node[k].sort(key=lambda x: -x[1])

        kept, deg = {}, {}

        def take(e, w):
            if e in kept:
                return
            a, b, _ = e
            if deg.get(a, 0) >= MAX_DEG or deg.get(b, 0) >= MAX_DEG:
                return
            kept[e] = w
            deg[a] = deg.get(a, 0) + 1
            deg[b] = deg.get(b, 0) + 1

        for nid, arr in by_node.items():                 # бронь: связность важнее порога
            for e, w in arr[:KEEP_MIN]:
                take(e, w)
        for e, w in sorted(wt.items(), key=lambda x: -x[1]):
            if w >= THRESHOLD:
                take(e, w)
        return kept

    before = len(edges)
    kept = prune(edges)
    edges = set(kept)
    print(f"   порог значимости: {before} → {len(edges)} рёбер (убрано {before - len(edges)})")

    # Вес едет НА КЛИЕНТ: раскладка тянет сильные связи короче, рисует их толще, и
    # структура становится видна глазом. Округляем до сотых — точнее не нужно, а файл
    # отдаётся всем читателям.
    edge_list = [{"a": a, "b": b, "t": t, "w": round(kept[(a, b, t)], 2)}
                 for (a, b, t) in sorted(edges)]
    out = {"nodes": list(nodes.values()), "edges": edge_list}
    Path("data").mkdir(exist_ok=True)
    write_json_atomic(Path("data/knowledge-graph.json"), out, indent=None)

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
