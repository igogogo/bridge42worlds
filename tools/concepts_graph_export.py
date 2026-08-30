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
# Сколько верхних соседей по смыслу соединять всегда. Четыре — столько же,
# сколько мини-граф показывает вокруг фокуса в первую очередь; больше даёт
# густую сетку из близких по определению понятий, которая забивает связи по
# статьям.
TOP_SEMANTIC = 4


def main():
    doc = json.loads(LIVE.read_text(encoding="utf-8"))
    # Слитые понятия (tools/concept_twins.py) — записи-указатели без статей и
    # связей. В графе они стали бы узлами-сиротами: кружок с именем, от которого
    # не идёт ни одного ребра, потому что всё забрал победитель.
    live = {c: v for c, v in doc["concepts"].items() if not v.get("merged_into")}
    groups_raw = {g: [m for m in ms if m in live]
                  for g, ms in (doc.get("groups") or {}).items()}

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
        # Условие — «нет ни одного ребра», а не «нет статей». Ксенон, эффект
        # Саньяка и ещё двое статьи имеют, но ни одной ОБЩЕЙ с кем-либо: их
        # статьи одиночки, и порог в две статьи связь не даёт. Для графа разницы
        # нет — точка без рёбер одинаково не находится.
        if i in linked:
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

    # СОСЕД ПОКАЗАН — ЗНАЧИТ СВЯЗЬ НАРИСОВАНА. Отдельная беда, найденная владельцем
    # 28.08: «слияние чёрных дыр не связано с чёрной дырой, болтается сиротой».
    # У этой пары ноль общих статей (девять и двадцать, пересечение пусто), а в
    # соседях друг у друга они стоят с весом 0.65 — их роднит смысл, а не общий
    # текст. Страница показывает их рядом, мини-граф берёт узлы из того же списка
    # соседей, но рёбра брал только статейные — и сосед оказывался без линии.
    #
    # Теперь верхние соседи по смыслу получают ребро всегда, независимо от того,
    # есть ли у узла другие связи. Вес 1 — слабее любой статейной, чтобы
    # калибровка кадра не приняла смысловую близость за мощность.
    sem = 0
    for cid, v in live.items():
        i = idx[cid]
        for r in (v.get("related") or [])[:TOP_SEMANTIC]:
            j = idx.get(r["id"])
            if j is None or j == i:
                continue
            pair = (min(i, j), max(i, j))
            if pair in keep:
                continue
            keep.add(pair)
            edges.append([pair[0], pair[1], 1])
            sem += 1
    if sem:
        print(f"  смысловых рёбер «сосед показан — связь нарисована»: {sem}")
    if added:
        edges.sort(key=lambda e: (e[0], e[1]))
        print(f"  смысловых рёбер для понятий без статей: {added}")

    # СВЯЗИ ПО ЗНАНИЮ (tools/link_weaving.py). Третий источник рядом со статьями
    # и вектором: закон и его константа связаны не потому, что встретились в
    # одной работе, а потому, что одна входит в другую. Владелец 28.08: «как ты
    # установишь связь между законом и константой… это работа твоя как
    # интеллекта, а не только что есть в статьях».
    # Вес 1..3 — по силе связи; тип (part_of, case_of, follows…) едет четвёртым
    # элементом ребра: клиент читает первые три и лишнего не замечает, а панель
    # сможет показать, ЧЕМ связаны.
    know = 0
    kn_p = ROOT / "data" / "concept-links-knowledge.json"
    if kn_p.exists():
        try:
            kn = json.loads(kn_p.read_text(encoding="utf-8"))
        except Exception:
            kn = {}
        for cid, links in kn.items():
            i = idx.get(cid)
            if i is None:
                continue
            for lk in links:
                j = idx.get(lk.get("to"))
                if j is None or j == i:
                    continue
                pair = (min(i, j), max(i, j))
                if pair in keep:
                    continue
                keep.add(pair)
                edges.append([pair[0], pair[1], int(lk.get("w") or 2),
                              lk.get("rel") or "same_area"])
                know += 1
        if know:
            print(f"  связей по знанию: {know}")

    # группы: членство из supers (первая группа понятия)
    gids = sorted(groups_raw, key=lambda g: -len(groups_raw[g]))
    gindex = {g: i for i, g in enumerate(gids)}

    def group_of(cid):
        sups = live[cid].get("supers") or []
        return gindex.get(str(sups[0])) if sups else None

    # НАЗВАНИЯ ГРУПП — человеческие, из data/group-names.json (tools/group_names.py).
    # Раньше подписью служила склейка трёх участников — «течение жидкости ·
    # гидродинамика · поверхностное натяжение». Это не название, а первые строки
    # списка: по нему нельзя понять ни чем область занимается, ни чем отличается
    # от соседней, а с обзора групп начинается весь граф знаний (владелец 28.08:
    # «название группы мне ни о чём не говорит»). Склейка остаётся запасным
    # вариантом — на случай, если группу ещё не назвали.
    gnames = {}
    gn_p = ROOT / "data" / "group-names.json"
    if gn_p.exists():
        try:
            gnames = json.loads(gn_p.read_text(encoding="utf-8"))
        except Exception:
            gnames = {}

    def members_label(gid, lang):
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

    def label(gid, lang):
        g = gnames.get(str(gid)) or {}
        return g.get(f"name_{lang}") or g.get("name_en") or members_label(gid, lang)

    def note(gid, lang):
        g = gnames.get(str(gid)) or {}
        return g.get(f"note_{lang}") or g.get("note_en") or ""

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
        # ИМЕНА ВСЕХ ЯЗЫКОВ, а не пара ru/en. Мини-граф стоит на КАЖДОЙ странице
        # статьи и берёт имена отсюда: пока в узле лежали только ru и en, испанец
        # с французом читали испанскую статью, а понятия под ней — по-английски,
        # хотя имена на их языке есть у всех 3 609 понятий. Поле names весит
        # около двухсот килобайт на весь граф и снимает вопрос о шестом языке.
        _nm = v.get("names") or {}
        nodes.append({
            "id": cid,
            "en": _nm.get("en") or cid.replace("_", " "),
            "ru": _nm.get("ru") or "",
            "names": {l: t for l, t in _nm.items() if t},
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
    # УЧЁНЫЕ — узлами (владелец 28.08: «есть ли в графе опция включить учёных,
    # иконка для них, можно ли включать-выключать»). Связь «понятие ↔ кто его
    # открыл или развил» у нас в данных была, а в графе не показывалась вовсе:
    # ноль узлов этого класса. Между тем именно вокруг имён область собирается
    # понятнее всего — видно, кто держит поле.
    #
    # Вес ребра — сколько наших статей связывают учёного с этим понятием, то же
    # мерило, что у связей между понятиями. Берём по четыре сильнейших понятия
    # на человека: полный список даёт Эйнштейну сотню рёбер и превращает кадр в
    # ёжика.
    # ВЕС СО СКИДКОЙ НА ХАБНОСТЬ. Считать по числу упоминаний нельзя: Эйнштейн
    # поминается в сотнях работ, и сильнейшими его связями выходили «транзитный
    # метод» и LIGO — просто потому, что это самые многолюдные понятия корпуса,
    # а не потому, что он к ним причастен. Делим на корень из числа статей
    # понятия — тот же приём, что уже стоит в разметке: частое понятие должно
    # доказывать связь весомее, чем редкое.
    sci_link = defaultdict(list)
    for cid, v in live.items():
        n_arts = max(1, len(v.get("articles") or []))
        scs = v.get("scientists") or []
        # ДОЛЯ ВНИМАНИЯ внутри понятия: сколько этого имени среди всех имён,
        # привязанных к понятию. Одной скидки на хабность мало — она починила
        # Хокинга и Шрёдингера, но не самые частые имена: Эйнштейн поминается по
        # всей астрофизике, а «Hubble» вообще тянет за собой снимки телескопа
        # Хаббла, и Эдвин Хаббл оказывался связан с пульсарами. Доля отвечает на
        # другой вопрос — не «часто ли он здесь», а «его ли это место».
        total = sum(x.get("n") or 0 for x in scs) or 1
        for sc in scs:
            nm = (sc.get("name") or "").strip()
            if nm and cid in idx:
                raw = sc.get("n") or 0
                share = raw / total
                score = share * (raw ** 0.5) / (n_arts ** 0.25)
                sci_link[nm].append((score, raw, idx[cid]))
    n_sci = 0
    for nm, lst in sci_link.items():
        lst.sort(reverse=True)
        si = len(nodes)
        top = lst[:4]
        # раздел и область берём у самого характерного понятия: учёный садится
        # там, где работал, а не в общей куче
        first = nodes[top[0][2]] if top else {}
        nodes.append({
            "id": "s:" + nm, "en": nm, "ru": "",
            "kind": "scientist", "g": first.get("g"),
            "n": sum(raw for _s, raw, _i in lst),
            "card": "", "cat": first.get("cat"),
        })
        n_sci += 1
        for _score, raw, ci in top:
            edges.append([ci, si, max(1, int(raw))])
    if n_sci:
        print(f"  учёных узлами: {n_sci}")

    # note_* — строка «о чём эта область»: панель графа показывает её под
    # названием, чтобы круг на обзоре объяснял себя сам.
    groups = [{"id": g, "label_en": label(g, "en"), "label_ru": label(g, "ru"),
               "note_en": note(g, "en"), "note_ru": note(g, "ru"),
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
