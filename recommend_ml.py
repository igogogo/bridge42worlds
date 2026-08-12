#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ML-часть рекомендаций авторам: соседи, отсев натяжек, «где рядом пусто».

Для `tools/recommend.py` ведущей сессии. Три функции, каждая закрывает свой её вопрос:

    neighbors(aid, k=10)        соседи по вектору напрямую, без похода в /api/search
    rerank_neighbors(...)       второй фильтр: отсев формальных соседей-натяжек
    drill_hint(aid)             «рядом с вашей работой в науке густо, а у нас пусто»

ПОЧЕМУ СОСЕДИ СЧИТАЮТСЯ ЗДЕСЬ, А НЕ ЧЕРЕЗ ПОИСК. Сейчас `recommend.py` ищет соседей
текстовым запросом через `/api/search`. Это работает, но делает лишний круг: у статьи
УЖЕ есть вектор, а запрос заново превращается в вектор из обрезанного текста. Разница
не только в цене — в точности. Вектор запроса строится по 1200 знакам тела, вектор
статьи — по всему, что мы про неё знаем; это разные точки, и вторая ближе к истине.

Локальная матрица вместо Vectorize `queryByVectorId`. Причина простая: у нас 2124
статьи, это матрица 2124 × 1024, восемь мегабайт. Умножение занимает миллисекунды,
стоит ноль и не расходует дневную квоту Workers AI, которую делит с ним живой поиск
на сайте. `queryByVectorId` понадобился бы на миллионах — у нас их нет и не будет:
статей столько, сколько мы написали.

ЧТО ЛУЧШЕ ДЛЯ СОСЕДЕЙ — АННОТАЦИЯ ИЛИ ПОЛНЫЙ ТЕКСТ. Замер 8 августа на поиске
(800 вопросов) дал аннотацию заметно лучше: 52,0% против 44,3%. Но это ДРУГАЯ задача —
там вопрос человека против статьи, а здесь статья против статьи. Померил и эту
(`compare_sources()`, 120 статей): аннотации 59,1% против 56,7% у тел при равном числе
соседей. Разница мала, покрытие — нет: аннотационных векторов 2124, полнотекстовых
3203. Отсюда режим «auto»: аннотация, где есть, тело — где нет. Подробности в neighbors().
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
_CACHE = {}


def _load(source):
    """Матрица векторов + список id. Читается один раз на процесс."""
    import numpy as np
    if source in _CACHE:
        return _CACHE[source]
    name = {"abstract": "articles", "fulltext": "fulltext"}[source]
    vecs, ids = [], []
    with (DATA / f"embeddings-{name}.jsonl").open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("vec"):
                vecs.append(r["vec"])
                ids.append(str(r["id"]).split(":", 1)[-1])
    M = np.asarray(vecs, dtype=np.float32)
    M /= np.linalg.norm(M, axis=1, keepdims=True) + 1e-9
    _CACHE[source] = (M, ids, {a: i for i, a in enumerate(ids)})
    return _CACHE[source]


def _base(aid):
    """arXiv-id без версии: 2506.03282v2 и 2506.03282 — одна работа.

    Раздел сохраняем: до 2007 года номера шли отдельно в каждом разделе, и
    `astro-ph/9909003` с `hep-th/9909003` — разные работы (см. field_build._base_id,
    там это стоило одной ложной тревоги о повреждении поля). Наши статьи все новые,
    так что здесь это про запас — но запас дешёвый, а ошибка тихая.
    """
    s = str(aid).strip().split(":", 1)[-1]
    return s.split("v")[0] if "v" in s[-3:] else s


def neighbors(aid, k=10, source="auto", min_sim=0.45):
    """Ближайшие статьи к данной. Возвращает [{id, sim}], убывание сходства.

    ИСТОЧНИК ПО УМОЛЧАНИЮ — «auto», и это вывод из замера, а не осторожность.
    Сравнил на 120 статьях, где ground truth даёт независимый механизм (реранкер
    подтверждает связь или нет):

        при равном числе соседей (топ-5)   аннотации 59,1% · тела 56,7%
        при общем пороге 0,45              поровну 50,1%, но тела отдают 6,8
                                           соседа на статью против 9,8

    Разница в пределах пары пунктов — решающего преимущества нет ни у кого, и
    выбирать «или-или» неправильно. Зато у источников разное ПОКРЫТИЕ: вектор
    аннотации есть у 2124 статей, вектор тела — у 3203. Поэтому берём аннотацию,
    когда она есть (она чуть точнее), и тело для тысячи с лишним статей, которых
    в первом индексе просто нет. Так покрытие максимальное, а точность лучшая
    из доступных на каждой статье.

    `min_sim` оставлен тем же, что у ведущей (0,45), чтобы переключение источника
    ничего не меняло, кроме источника. На нашей шкале это низкий порог — медиана
    близости любых двух наших статей около 0,55, — но он и не должен отсекать:
    отсекает второй этаж, rerank_neighbors().

    Своя статья из выдачи убирается по базовому id, а не по строке: в индексе она
    может лежать с версией, и сравнение строк вернуло бы её первым же соседом.
    """
    import numpy as np
    key = _base(aid)
    if source == "auto":
        for s in ("abstract", "fulltext"):
            _, _, p = _load(s)
            if key in p:
                source = s
                break
        else:
            return []
    M, ids, pos = _load(source)
    i = pos.get(key)
    if i is None:
        i = next((j for j, a in enumerate(ids) if _base(a) == key), None)
    if i is None:
        return []
    sim = M @ M[i]
    out = []
    for j in np.argsort(-sim):
        if _base(ids[j]) == key:
            continue
        s = float(sim[j])
        if s < min_sim or len(out) >= k:
            break
        out.append({"id": ids[j], "sim": round(s, 4)})
    return out


def rerank_neighbors(text, cands, keep=5, min_score=0.05, model="8B"):
    """Второй этаж: отсев формальных соседей-натяжек. Решает вопрос 2 ведущей.

    ЗАЧЕМ ВТОРОЙ ЭТАЖ. Вектор отвечает «про то же ли это», и на вопрос «стоит ли
    автору это читать» он ответить не может: он видел два текста порознь. Так статья
    про квантовую телепортацию энергии получила в соседи работу про «квантовую
    телепатию» — общая лексика, разный предмет. Реранкер читает оба текста ВМЕСТЕ
    и на этот вопрос отвечает; на нашем отборе кандидатов дня он дал 82% сохранённых
    находок против 52% у случайного среза (rerank_eval.py, 20 дней).

    `text` — текст исходной статьи (заголовок + описание). Он же служит запросом:
    вопрос «насколько эта работа — продолжение вот этой» задаётся напрямую.

    При любом сбое возвращаем кандидатов как были: рекомендация без второго этажа
    хуже, чем рекомендация, но лучше, чем упавший разбор статьи.
    """
    if not cands:
        return cands, "соседей нет"
    try:
        sys.path.insert(0, str(ROOT))
        import rerank_eval as rr
        from embeddings_build import log_usage
        key = rr.load_env()
        docs = [c.get("text") or c.get("title") or "" for c in cands]
        if not any(docs):
            return cands, "у кандидатов нет текста — реранкер пропущен"
        stats = {}
        sc = rr.rerank(" ".join(str(text).split())[:1500], docs, key, model, stats=stats)
        log_usage("rerank", stats.get("tokens", 0), model=f"qwen3-reranker-{model.lower()}")
    except Exception as e:
        return cands, f"реранкер недоступен ({type(e).__name__}), беру как есть"
    for c, s in zip(cands, sc):
        c["rerank"] = round(float(s), 5)
    kept = [c for c in sorted(cands, key=lambda c: -c["rerank"]) if c["rerank"] >= min_score]
    if not kept:
        # Все кандидаты слабые — это тоже ответ. Отдаём лучшего одного и говорим правду:
        # лучше один честно слабый сосед, чем пять, выданных за находки.
        best = max(cands, key=lambda c: c["rerank"])
        return [best], f"все соседи слабые (лучший {best['rerank']:.3f}) — опора ненадёжна"
    return kept[:keep], f"реранкер оставил {min(len(kept), keep)} из {len(cands)}"


def drill_hint(aid, source="auto", top=3):
    """«Рядом с вашей работой в науке густо, а у нас пусто». Вопрос 3 ведущей.

    Карта строится `drill.py` (600 областей по вспомогательному индексу arXiv) и
    лежит в data/drill-*.  Здесь мы спрашиваем её про одну точку: к каким областям
    статья ближе всего и что в этих областях с плотностью.

    ЧЕСТНАЯ ГРАНИЦА. Это НЕ «здесь никто не работал» — вспомогательный индекс сейчас
    один месяц arXiv (29 тысяч работ), и пустая область может быть пустой по выборке.
    Формулировать автору надо как есть: «мы этого не разбирали, а работы там идут» —
    это правда о нас, а не о науке. Обещать «тут никого нет» мы не вправе.
    """
    import numpy as np
    cp, rp = DATA / "drill-centers.npy", DATA / "drill-regions.json"
    if not (cp.exists() and rp.exists()):
        return []
    C = np.load(cp)
    R = json.loads(rp.read_text(encoding="utf-8"))
    key = _base(aid)
    if source == "auto":
        source = next((s for s in ("abstract", "fulltext") if key in _load(s)[2]), None)
        if source is None:
            return []
    M, ids, pos = _load(source)
    i = pos.get(key)
    if i is None:
        i = next((j for j, a in enumerate(ids) if _base(a) == key), None)
    if i is None:
        return []
    sim = C @ M[i]
    out = []
    for j in np.argsort(-sim)[:40]:
        if R["restricted"][j] or R["n_arxiv"][j] < R["min_arxiv"]:
            continue
        if R["n_ours"][j] > 0:
            continue
        out.append({"область": R["names"][j], "работ_у_науки": R["n_arxiv"][j],
                    "у_нас": 0, "близость": round(float(sim[j]), 4),
                    "разделы": R["cats"].get(str(j), [])})
        if len(out) >= top:
            break
    return out


def compare_sources(n=200, k=10, seed=42, min_sim=0.0):
    """Аннотация или полный текст — что даёт лучших соседей. Замер, а не мнение.

    Ground truth без разметчика: считаем соседей ХОРОШИМИ, если реранкер (кросс-
    энкодер, механизм другой) подтверждает их связь с исходной статьёй. Это не
    идеальная истина, но независимая от обоих сравниваемых источников — а значит
    сравнение честное. Считается на выборке, потому что реранкер стоит денег.
    """
    import random
    import numpy as np
    sys.path.insert(0, str(ROOT))
    import rerank_eval as rr
    key = rr.load_env()
    texts = {}
    with (DATA / "embeddings-ours.jsonl").open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                texts[_base(r["id"])] = " ".join(str(r.get("text", "")).split())[:900]
    _, ids_a, _ = _load("abstract")
    _, ids_f, _ = _load("fulltext")
    common = sorted({_base(a) for a in ids_a} & {_base(a) for a in ids_f} & set(texts))
    random.Random(seed).shuffle(common)
    sample = common[:n]
    res = {}
    for src in ("abstract", "fulltext"):
        good = tot = 0
        for aid in sample:
            nb = [x for x in neighbors(aid, k=k, source=src, min_sim=min_sim)
                  if _base(x["id"]) in texts]
            if not nb:
                continue
            sc = rr.rerank(texts[aid], [texts[_base(x["id"])] for x in nb], key, "8B")
            good += sum(1 for s in sc if s >= 0.05)
            tot += len(sc)
        res[src] = (good, tot, good / max(tot, 1))
        print(f"  {src}: подтверждённых соседей {good} из {tot} ({good/max(tot,1)*100:.1f}%)")
    return res


if __name__ == "__main__":
    import argparse
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", help="показать соседей и подсказку по бурению для статьи")
    ap.add_argument("--source", default="auto", choices=("auto", "abstract", "fulltext"))
    ap.add_argument("--compare", type=int, default=0, help="сравнить источники на N статьях")
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--min-sim", type=float, default=0.45)
    a = ap.parse_args()
    if a.compare:
        compare_sources(a.compare, k=a.k, min_sim=a.min_sim)
    elif a.id:
        for x in neighbors(a.id, source=a.source):
            print(f"  {x['sim']:.3f}  {x['id']}")
        print("\nрядом пусто у нас:")
        for h in drill_hint(a.id, source=a.source):
            print(f"  {h['близость']:.3f}  {h['область']} — "
                  f"у науки {h['работ_у_науки']}, у нас 0  [{', '.join(h['разделы'][:4])}]")
