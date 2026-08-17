#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Векторная сверка справочников: мёртвое, дубли, дыры, связи.

Волна 14 августа, формулировка владельца: «сейчас приходит в зависимости от тех статей,
которые мы грузим; наш вектор может сделать итерацию для обновления справочников,
перестройки их связей, чтобы добиваться синхронности контента и справочников
и их адекватности».

ЧЕМ ПРЕДСТАВЛЕНА СУЩНОСТЬ. Не своим названием, а СЛЕДОМ В КОРПУСЕ: тег «чёрная дыра» —
это центроид векторов всех статей, которые им помечены. Название не векторизуется
вовсе, и на то две причины. Во-первых, это бесплатно: вектора статей уже посчитаны,
на счету $1.62, и тратить его на 739 коротких строк незачем. Во-вторых, вектор названия
отвечает на вопрос «похожи ли слова», а нам нужно «про одно ли они в наших статьях» —
это разные вопросы, и второй здесь правильный.

ПОЧЕМУ РЕШАЕТ НЕ ГЕОМЕТРИЯ. Вектор умеет вычёркивать, но не умеет выбирать — на этом
я в проекте ошиблась четырежды. Поэтому здесь нет порога «косинус выше 0.9 значит дубль».
Есть три независимых свидетельства на пару — пересечение пула статей, косинус центроидов,
общие слова в названиях — и они печатаются рядом, а решение остаётся за человеком
или за моделью. Файл называется предложением, а не правкой: справочники этот проход
не меняет.

ЕСТЬ ПРОВЕРКА, КОТОРУЮ МОЖНО ПРОВАЛИТЬ. Среди пар есть заведомые дубли — те, где одно
название содержится в другом или отличается окончанием (`black_hole` и `black_holes`).
Если ранжирование по геометрии не поднимает их наверх, оно ранжирует что-то другое,
и это будет видно в отчёте, а не спрятано.

    python refs_audit.py
    python refs_audit.py --out data/refs-audit.json --holes 80
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(ROOT))

STOP = {"of", "the", "and", "in", "a", "law", "effect", "theory", "quantum", "model"}


def jl(p):
    q = pathlib.Path(p)
    return json.loads(q.read_text(encoding="utf-8")) if q.exists() else {}


def words(s):
    return {w for w in re.split(r"[^a-z0-9]+", s.lower()) if w and w not in STOP}


def obvious_pair(a, b):
    """Заведомый дубль по названию: одно входит в другое или отличается окончанием.
    Используется как контроль ранжирования, а не как правило слияния."""
    x, y = a.lower().replace("-", "_"), b.lower().replace("-", "_")
    if x in y or y in x:
        return True
    return x.rstrip("s") == y.rstrip("s") and x != y


def diff_text(prev, cur, holes):
    """Что изменилось со времени прошлого прогона — человеческим текстом.

    Пустой diff это тоже результат и он печатается словами: «без изменений» значит,
    что справочники за неделю не поехали, а не что инструмент не отработал.
    """
    if not prev:
        lines = ["📚 Сверка справочников — первый прогон, сравнивать не с чем."]
    else:
        lines = ["📚 Сверка справочников за неделю"]
    for k in ("tag", "law", "sci"):
        c = (cur.get("kinds") or {}).get(k) or {}
        o = (prev.get("kinds") or {}).get(k) or {}
        if not c:
            continue
        human = {"tag": "теги", "law": "законы", "sci": "учёные"}[k]
        dead_now = {x["id"] for x in c.get("dead", [])}
        dead_was = {x["id"] for x in o.get("dead", [])}
        dup_now = {(x["a"], x["b"]) for x in c.get("duplicates", [])}
        dup_was = {(x["a"], x["b"]) for x in o.get("duplicates", [])}
        bits = []
        if dead_now - dead_was:
            bits.append(f"без опоры прибавилось {len(dead_now - dead_was)}")
        if dead_was - dead_now:
            bits.append(f"обрели опору {len(dead_was - dead_now)}")
        if dup_now - dup_was:
            bits.append(f"новых кандидатов в дубли {len(dup_now - dup_was)}")
        lines.append(f"· {human}: всего {c.get('total')}, "
                     + ("; ".join(bits) if bits else "без изменений"))
    hw = len(prev.get("holes") or [])
    if hw != len(holes):
        lines.append(f"· дыр без покрытия: {hw} → {len(holes)}")
    else:
        lines.append(f"· дыр без покрытия: {len(holes)}, без изменений")
    lines.append("Файл: data/refs-audit.json. Это предложение, "
                 "справочники не изменены.")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    # По умолчанию — в свою копию: результат коммитит тот, кто его получил.
    ap.add_argument("--out", default=str(ROOT / "data" / "refs-audit.json"))
    ap.add_argument("--holes", type=int, default=80, help="сколько кластеров статей резать")
    ap.add_argument("--cover", type=float, default=0.40,
                    help="доля кластера, ниже которой считаем его непокрытым")
    ap.add_argument("--pairs", type=int, default=25, help="сколько пар печатать")
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--notify", action="store_true",
                    help="отправить diff с прошлым прогоном в канал")
    args = ap.parse_args()

    import numpy as np
    import vecstore
    import field_build as fb

    tg = jl(MAIN / "data/tags-graph.json").get("graph", {})
    lg = jl(MAIN / "data/laws-graph.json").get("graph", {})
    sc = jl(MAIN / f"lang/{args.lang}/data/scientists.json")
    idx = jl(MAIN / f"lang/{args.lang}/articles-index.json")
    print(f"справочники: тегов {len(tg)} · законов {len(lg)} · учёных {len(sc)}")

    # Статья → сущности. Версии одной работы схлопываем: справочник живёт на уровне
    # работы, а не пересказа, иначе популярная и экспресс-версия считались бы дважды.
    art = {}
    for a in idx:
        # Номер в индексе идёт С ВЕРСИЕЙ (2505.00266v1), в поле — без. Долг прошлой
        # волны: без приведения к одному виду тысяча работ не находила свой вектор,
        # и все числа этого отчёта были занижены примерно на пятую часть.
        aid = fb._base_id(str(a.get("id") or ""))
        if not aid:
            continue
        r = art.setdefault(aid, {"tags": set(), "laws": set(), "sci": set()})
        r["tags"] |= set(a.get("tags") or [])
        r["laws"] |= set(a.get("laws") or [])
        r["sci"] |= set(a.get("scientists") or [])
    print(f"статей в индексе {len(idx)} · различных работ {len(art)}")

    # Поле читается как memmap, строки берутся поштучно. С latest=True numpy
    # материализует всю матрицу 1 556 983 × 1024 — три гигабайта ради пяти тысяч строк,
    # и прогон падает по памяти. Порядок поиска папки — как в analytics_v2: своя,
    # затем копия ML, затем переменная окружения.
    from analytics_v2 import _field_dir
    ids, M = vecstore.load(_field_dir() / "field", mmap=True)
    rowof = {}
    for i, s in enumerate(ids):
        rowof[fb._base_id(s)] = i     # позже встреченное затирает раннее — как latest
    have = {a for a in art if a in rowof}
    print(f"из них с вектором в поле: {len(have)}")

    order = sorted(have)
    X = np.empty((len(order), M.shape[1]), dtype=np.float32)
    for i, a in enumerate(order):
        X[i] = M[rowof[a]]
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
    pos = {a: k for k, a in enumerate(order)}

    KINDS = (("tag", tg, "tags"), ("law", lg, "laws"), ("sci", sc, "sci"))
    result = {"built": "2026-08-15", "articles": len(have), "kinds": {}}

    for kind, book, field in KINDS:
        # След сущности: какие работы её несут.
        pool = {name: set() for name in book}
        for aid, r in art.items():
            if aid not in pos:
                continue
            for e in r[field]:
                if e in pool:
                    pool[e].add(aid)

        names = [n for n in book]
        cent = np.zeros((len(names), X.shape[1]), dtype=np.float32)
        size = np.zeros(len(names), dtype=np.int32)
        for k, n in enumerate(names):
            js = [pos[a] for a in pool[n]]
            size[k] = len(js)
            if js:
                v = X[js].mean(0)
                cent[k] = v / (np.linalg.norm(v) + 1e-9)

        dead = sorted(((n, len(pool[n])) for n in names if len(pool[n]) <= 1),
                      key=lambda r: r[1])
        print(f"\n{'=' * 78}\n{kind.upper()} · {len(names)} сущностей\n{'=' * 78}")
        print(f"  без опоры в статьях (0-1 работа): {len(dead)}")
        for n, c in dead[:8]:
            ex = next(iter(pool[n]), "")
            print(f"    {n[:52]:<54} работ {c}" + (f"  ({ex})" if ex else ""))
        if len(dead) > 8:
            print(f"    … ещё {len(dead) - 8}")

        # ДУБЛИ. Кандидаты — только пары с общими работами: без пересечения пула
        # разговор о слиянии беспредметен, а перебор сокращается на порядки.
        live = [k for k in range(len(names)) if size[k] >= 2]
        by_art = {}
        for k in live:
            for a in pool[names[k]]:
                by_art.setdefault(a, []).append(k)
        seen = set()
        cands = []
        for a, ks in by_art.items():
            if len(ks) > 60:
                continue
            for i in range(len(ks)):
                for j in range(i + 1, len(ks)):
                    p = (ks[i], ks[j]) if ks[i] < ks[j] else (ks[j], ks[i])
                    if p in seen:
                        continue
                    seen.add(p)
                    A, B = pool[names[p[0]]], pool[names[p[1]]]
                    inter = len(A & B)
                    if inter < 2:
                        continue
                    jac = inter / len(A | B)
                    cos = float(cent[p[0]] @ cent[p[1]])
                    wa, wb = words(names[p[0]]), words(names[p[1]])
                    nam = len(wa & wb) / max(1, min(len(wa), len(wb)))
                    cands.append((p[0], p[1], jac, cos, nam, inter))
        # ДВА РАЗНЫХ ЯВЛЕНИЯ, А НЕ ОДНО — это показал первый же прогон. У тегов
        # ранжирование по геометрии поднимает наверх настоящие дубли (20 заведомых
        # из 25 первых), а у учёных и законов — СОАВТОРОВ: Пензиас и Уилсон, Халс
        # и Тейлор, Майор и Кело, Жаккар до 0.94 и косинус до 0.999. Слить их значило бы
        # разрушить справочник. «Всегда встречаются вместе» для людей означает
        # совместную работу, а не тождество, и геометрия этих двух случаев не различает
        # в принципе — ей нечем.
        #
        # Поэтому в дубли идут только пары со свидетельством ПО НАЗВАНИЮ, а геометрия
        # его подтверждает. Пары без такого свидетельства уходят в отдельный список
        # с другим смыслом: это не ошибка справочника, а факт о корпусе — эти сущности
        # у нас нигде не встречаются порознь. Сливать их запрещено.
        named = [c for c in cands
                 if obvious_pair(names[c[0]], names[c[1]]) or c[4] > 0]
        named.sort(key=lambda r: -(r[4] * 2 + r[2] + r[3]))
        insep = [c for c in cands
                 if not obvious_pair(names[c[0]], names[c[1]]) and c[4] == 0
                 and c[2] >= 0.30]
        insep.sort(key=lambda r: -r[2])
        obvious = [c for c in cands if obvious_pair(names[c[0]], names[c[1]])]
        top = named[:args.pairs]
        hit = sum(1 for c in top if obvious_pair(names[c[0]], names[c[1]]))
        print(f"\n  пар с общими работами: {len(cands)}")
        print(f"  кандидатов в дубли (есть свидетельство по названию): {len(named)}")
        print(f"  из них заведомых: {len(obvious)} · попало в первые "
              f"{args.pairs}: {hit}")
        for c in top[:8]:
            mark = "  ← заведомый" if obvious_pair(names[c[0]], names[c[1]]) else ""
            print(f"    {names[c[0]][:30]:<32} + {names[c[1]][:30]:<32}")
            print(f"      общих {c[5]:>3} · Жаккар {c[2]:.2f} · косинус {c[3]:.3f} · "
                  f"слова {c[4]:.2f}{mark}")
        if insep:
            print(f"\n  НЕРАЗДЕЛИМЫЕ ПАРЫ — не дубли, сливать нельзя ({len(insep)}):")
            for c in insep[:5]:
                print(f"    {names[c[0]][:30]:<32} + {names[c[1]][:30]:<32}"
                      f"  Жаккар {c[2]:.2f}")

        result["kinds"][kind] = {
            "total": len(names),
            "dead": [{"id": n, "articles": c} for n, c in dead],
            "duplicates": [{"a": names[c[0]], "b": names[c[1]], "shared": c[5],
                            "jaccard": round(c[2], 3), "cosine": round(c[3], 3),
                            "name_overlap": round(c[4], 2),
                            "obvious": obvious_pair(names[c[0]], names[c[1]])}
                           for c in named[:200]],
            # Отдельным списком и с другим смыслом: слияние здесь запрещено.
            "inseparable": [{"a": names[c[0]], "b": names[c[1]], "shared": c[5],
                             "jaccard": round(c[2], 3), "cosine": round(c[3], 3),
                             "note": "никогда не встречаются порознь; для людей это "
                                     "соавторство, а не тождество — не сливать"}
                            for c in insep[:120]],
            "obvious_in_top": {"n_obvious": len(obvious), "in_top": hit,
                               "top": args.pairs},
        }

        # СВЯЗИ. Пересчёт от фактической со-встречаемости, а не от момента заведения.
        if kind == "tag":
            rel_now = {n: set(book[n].get("related") or []) for n in names}
            co = {}
            for aid, r in art.items():
                if aid not in pos:
                    continue
                ts = sorted(t for t in r["tags"] if t in rel_now)
                for i in range(len(ts)):
                    for j in range(i + 1, len(ts)):
                        co[(ts[i], ts[j])] = co.get((ts[i], ts[j]), 0) + 1
            # НОРМИРОВКА СИММЕТРИЧНАЯ, А НЕ ПО МЕНЬШЕМУ ПУЛУ. С делением на меньший
            # пул тег из трёх статей, все из которых про чёрные дыры, получает вес 1.0
            # и въезжает в соседи к чёрной дыре первым номером. Первый прогон выдал
            # ровно это: «black_hole — derivative», «quantum_entanglement —
            # functional_analysis». Корень тот же, что у хабов в поле: редкая сущность
            # выигрывает у частой не связью, а малым знаменателем.
            #
            # Здесь знаменатель — корень из произведения пулов (косинус встречаемости),
            # плюс порог опоры: пара должна встретиться не меньше MIN_CO раз, а обе
            # сущности иметь не меньше MIN_N работ. Без порога любая случайная
            # со-встречаемость единожды выглядит как связь.
            MIN_CO, MIN_N = 3, 5
            k_of = {n: k for k, n in enumerate(names)}
            nb = {n: [] for n in names}
            for (a, b), c in co.items():
                ia, ib = k_of[a], k_of[b]
                if c < MIN_CO or size[ia] < MIN_N or size[ib] < MIN_N:
                    continue
                w = c / float(np.sqrt(float(size[ia]) * float(size[ib])))
                nb[a].append((b, w))
                nb[b].append((a, w))
            add, drop = [], []
            for n in names:
                top_new = {b for b, w in sorted(nb[n], key=lambda x: -x[1])[:8]
                           if w >= 0.12}
                add += [(n, b, round(dict(nb[n]).get(b, 0.0), 3))
                        for b in top_new - rel_now[n]]
                # Снимать связь у сущности без опоры нельзя: у неё просто нет статей,
                # по которым связь можно было бы подтвердить, и молчание — не довод.
                drop += [(n, b, 0.0) for b in rel_now[n] - top_new
                         if b in k_of and size[k_of[b]] >= MIN_N and size[k_of[n]] >= MIN_N]
            print(f"\n  связи по со-встречаемости (опора ≥{MIN_CO} работ, "
                  f"пул ≥{MIN_N}): добавить {len(add)}, снять {len(drop)}")
            for a, b, w in sorted(add, key=lambda r: -r[2])[:6]:
                print(f"    + {a} — {b}  вес {w}")
            result["kinds"][kind]["links_add"] = [
                {"a": a, "b": b, "w": w}
                for a, b, w in sorted(add, key=lambda r: -r[2])[:400]]
            result["kinds"][kind]["links_drop"] = [
                {"a": a, "b": b} for a, b, _ in drop[:400]]

    # ДЫРЫ. Плотный кластер статей, который не покрыт ни одним тегом или законом.
    print(f"\n{'=' * 78}\nДЫРЫ · кластеры статей без покрытия справочником\n{'=' * 78}")
    from sklearn.cluster import KMeans
    km = KMeans(n_clusters=args.holes, n_init=4, random_state=0).fit(X)
    lab = km.labels_
    holes = []
    for c in range(args.holes):
        members = [order[k] for k in np.where(lab == c)[0]]
        if len(members) < 8:
            continue
        cnt = {}
        for a in members:
            for t in art[a]["tags"] | art[a]["laws"]:
                cnt[t] = cnt.get(t, 0) + 1
        best, share = ("", 0.0)
        if cnt:
            best = max(cnt, key=cnt.get)
            share = cnt[best] / len(members)
        if share < args.cover:
            holes.append({"cluster": int(c), "articles": len(members),
                          "best_cover": best, "share": round(share, 2),
                          "examples": members[:5]})
    holes.sort(key=lambda h: (-h["articles"], h["share"]))
    print(f"  кластеров {args.holes} · непокрытых (лучший тег держит < "
          f"{args.cover * 100:.0f}%): {len(holes)}")
    for h in holes[:8]:
        print(f"    кластер {h['cluster']:>3} · статей {h['articles']:>3} · "
              f"лучший тег «{h['best_cover']}» держит {h['share'] * 100:.0f}%")
    print("\n  Название новой сущности здесь НЕ придумывается: это работа модели,")
    print("  и делать её надо строго по опоре из перечисленных работ. При $1.62")
    print("  на счету шаг отложен — список кандидатов готов и ждёт.")
    result["holes"] = holes

    # СРАВНЕНИЕ С ПРОШЛЫМ ПРОГОНОМ. Волна 14 августа просила diff «добавлено / слито /
    # удалено / переподвешено»: рост справочников должен быть виден, а не происходить
    # молча. Сам список из ста строк в канал слать бессмысленно — туда идёт то,
    # что ИЗМЕНИЛОСЬ с прошлой недели, и только оно.
    p = pathlib.Path(args.out)
    prev = {}
    if p.exists():
        try:
            prev = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
    diff = diff_text(prev, result, holes)
    p.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{'=' * 78}")
    print("ЧТО ИЗМЕНИЛОСЬ С ПРОШЛОГО ПРОГОНА")
    print(f"{'=' * 78}")
    print(diff)
    if args.notify:
        import subprocess
        msg = MAIN / "logs" / "refs-diff.txt"
        msg.parent.mkdir(exist_ok=True)
        msg.write_text(diff, encoding="utf-8")
        try:
            subprocess.run([sys.executable, str(MAIN / "tools" / "status_tg.py"),
                            "--file", str(msg)], cwd=str(MAIN), timeout=120)
            print("отчёт ушёл в канал")
        except Exception as ex:
            print(f"в канал не ушло: {type(ex).__name__}")
    print(f"\n{'=' * 78}")
    print(f"ИТОГ: предложение, а не правка. Справочники этим проходом не изменены.")
    for k in result["kinds"]:
        r = result["kinds"][k]
        print(f"  {k:<5} мёртвых {len(r['dead']):>3} · в дубли "
              f"{len(r['duplicates']):>3} (заведомых в первых "
              f"{r['obvious_in_top']['top']}: {r['obvious_in_top']['in_top']}) · "
              f"неразделимых {len(r['inseparable']):>3}")
    print(f"  дыр без покрытия: {len(holes)}")
    print(f"\n→ {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
