"""Связи между статьями по смыслу — считаем ЛОКАЛЬНО, из текстов статей.

Владелец 2026-08-02: «можно ссылок понаставить по тексту по векторной базе — это будет
эффектно».

Почему не через Vectorize, хотя векторы там: наш собственный сторож от ботов держит
недельную квоту на семантический поиск, и массовый прогон в 2100 запросов упирается в неё
на второй статье (проверено). Ломать сторож ради своего же удобства неправильно — он
защищает от переплаты за чужие запросы. Поэтому считаем сами: тексты статей лежат у нас,
sklearn уже стоит (на нём построена карта /analytics), и близость по TF-IDF на своём
корпусе даёт связи не хуже — а главное, воспроизводимо и бесплатно.

Что получается лучше нынешних «похожих»: сейчас они подбираются по СОВПАДЕНИЮ ТЕГОВ. Тег
грубая мерка — две работы про «энтропию» бывают о совершенно разном, а работа про приливные
силы и работа про деформацию звёзд общего тега могут не иметь вовсе. Здесь сравнивается
сам текст.

    python tools/vector_links_local.py --dry     показать примеры, ничего не писать
    python tools/vector_links_local.py           посчитать весь архив

Результат — data/related-vec.json: {id: [{id, score}, …]}. Формат тот же, что у облачной
версии, чтобы страница читала его одинаково.
"""
import argparse
import json
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "related-vec.json"
MARK = re.compile(r"\[(?:tag|scientist|law):[^\]]+\]|\[/(?:tag|scientist|law)\]")


def corpus():
    """Тексты статей: заголовок + описание + тело. Русский тир — он самый полный."""
    ids, texts, meta = [], [], {}
    for p in sorted((ROOT / "lang/ru/archive").glob("*/*/data.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        v = (d.get("popular", {}) or {}).get("ru") or (d.get("simple", {}) or {}).get("ru") or {}
        if not isinstance(v, dict) or not v.get("title"):
            continue
        t = " ".join(str(v.get(k, "")) for k in ("title", "description", "text", "oneliner"))
        t = MARK.sub(" ", t)
        if len(t) < 200:
            continue
        aid = p.parent.name
        ids.append(aid)
        texts.append(t)
        meta[aid] = {"title": v["title"], "date": d.get("date", ""),
                     "tags": v.get("extra_tags", []), "express": bool(d.get("express"))}
    return ids, texts, meta


def by_vector(ids, top=4, floor=0.42, dry=False):
    """Соседи по смысловому вектору — один запрос к Vectorize на работу.

    Зачем отдельный путь. Массовый прогон считает слова: это бесплатно, воспроизводимо и
    для 94% архива работает. Но у длинных работ вес размазан, и их настоящие соседи не
    добирают до порога: у 2609.90001 (8299 знаков против медианных 2251) лучшая близость
    по словам 0.085 при пороге 0.10, а тот же список по вектору идёт на 0.45–0.52.
    Обрезка текстов до общей длины не помогает — проверено, дело в мерке.

    Запросов ровно столько, сколько названо работ, поэтому недельная квота сторожа
    (ради которой массовый прогон и считается словами) здесь не тратится.
    """
    import os
    import requests
    sys.path.insert(0, str(ROOT))
    from embeddings_build import load_env
    envv = load_env(ROOT) or {}
    tok = envv.get("CLOUDFLARE_API_TOKEN") or os.environ.get("CLOUDFLARE_API_TOKEN")
    acc = envv.get("CLOUDFLARE_ACCOUNT_ID") or os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    if not (tok and acc):
        sys.exit("нет CLOUDFLARE_API_TOKEN / CLOUDFLARE_ACCOUNT_ID")
    base = f"https://api.cloudflare.com/client/v4/accounts/{acc}/vectorize/v2/indexes/b42-articles"
    H = {"Authorization": f"Bearer {tok}"}

    data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    try:
        mark = json.loads((ROOT / "data" / "articles-retag-v2.json").read_text(encoding="utf-8"))["articles"]
    except Exception:                                    # noqa: BLE001
        mark = {}
    titles = {}
    try:
        for a in json.loads((ROOT / "lang/ru/articles-index.json").read_text(encoding="utf-8")):
            titles[a["id"]] = a.get("title", "")
            titles.setdefault(a["id"].split("v")[0], a.get("title", ""))
    except Exception:                                    # noqa: BLE001
        pass

    changed = 0
    for aid in ids:
        got = requests.post(f"{base}/get_by_ids", headers=H, json={"ids": [aid]}, timeout=60).json()
        rows = got.get("result") or []
        if not rows:
            print(f"  {aid}: вектора нет в индексе — сперва embeddings_export.py + vector_build.py")
            continue
        q = requests.post(f"{base}/query", headers=H, timeout=60,
                          json={"vector": rows[0]["values"], "topK": top * 3,
                                "returnMetadata": "none", "namespace": "ours"}).json()
        # ОБЩЕЕ ПОНЯТИЕ ОБЯЗАТЕЛЬНО. Вектор ставит рядом всё, что «про похожее вообще»:
        # у 2609.90001 в первую четвёрку попали варп-двигатель и суперсимметрия — темы
        # соседние по звучанию, но не по сути. У них с работой нет ни одного общего
        # понятия, а у водопада, вязкого мёда и вихрей в жидком гелии есть. Условие
        # дешёвое (разметка уже посчитана) и отсекает ровно этот случай.
        mine = set(mark.get(aid) or mark.get(aid.split("v")[0]) or [])
        near, loose = [], []
        for m in (q.get("result") or {}).get("matches", []):
            if m["id"] == aid or m["id"].split("v")[0] == aid.split("v")[0]:
                continue
            if float(m["score"]) < floor:
                break
            item = {"id": m["id"], "score": round(float(m["score"]), 3)}
            his = set(mark.get(m["id"]) or mark.get(m["id"].split("v")[0]) or [])
            (near if (mine & his) else loose).append(item)
            if len(near) >= top:
                break
        # Если разметки ещё нет или общих понятий не нашлось совсем — берём по близости,
        # иначе работа осталась бы вовсе без соседей, а это хуже неточного соседа.
        if len(near) < 2:
            near = (near + [x for x in loose if x not in near])[:top]
        near = near[:top]
        print(f"  {aid}: соседей {len(near)}")
        for x in near:
            print(f"      {x['score']:.3f}  {x['id']:14} {titles.get(x['id'], '')[:56]}")
        if not dry:
            data[aid] = near
            changed += 1
    if dry:
        print("показ, файл не тронут")
        return 0
    OUT.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"→ {OUT.relative_to(ROOT)}: обновлено работ {changed}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--top", type=int, default=4)
    ap.add_argument("--min", type=float, default=0.10)
    ap.add_argument("--vec", metavar="ID[,ID…]",
                    help="соседей ЭТИХ работ взять смысловым вектором и влить в файл "
                         "(для длинных работ, которым не хватает совпадения слов)")
    ap.add_argument("--vec-min", type=float, default=0.42, dest="vec_min",
                    help="порог близости для --vec (у вектора своя шкала, не как у слов)")
    args = ap.parse_args()

    if args.vec:
        return by_vector([x.strip() for x in args.vec.split(",") if x.strip()],
                         top=args.top, floor=args.vec_min, dry=args.dry)

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import linear_kernel
    import numpy as np

    ids, texts, meta = corpus()
    print(f"статей в корпусе: {len(ids)}")

    # min_df=3 — слово должно встретиться хотя бы в трёх статьях, иначе это опечатка или
    # имя собственное, которое роднит статьи случайно. max_df=0.4 — выбрасываем слова,
    # которые есть почти везде («учёные», «исследование»): они не различают статьи, а
    # только съедают вес.
    vec = TfidfVectorizer(min_df=3, max_df=0.4, sublinear_tf=True,
                          token_pattern=r"(?u)\b\w[\w-]{2,}\b")
    X = vec.fit_transform(texts)
    print(f"словарь: {len(vec.vocabulary_)} слов")

    out = {}
    shown = 0
    # По кускам: матрица 2100×2100 целиком не нужна, а по 200 строк считается мгновенно
    # и не съедает память, когда статей станет тридцать тысяч.
    CHUNK = 200
    for start in range(0, X.shape[0], CHUNK):
        sim = linear_kernel(X[start:start + CHUNK], X)
        for i, row in enumerate(sim):
            gi = start + i
            row[gi] = 0                      # сама с собой не сравнивается
            best = np.argsort(row)[::-1][:args.top * 2]
            near = []
            for j in best:
                s = float(row[j])
                if s < args.min:
                    break
                near.append({"id": ids[j], "score": round(s, 3)})
                if len(near) >= args.top:
                    break
            out[ids[gi]] = near
            if args.dry and near and shown < 6:
                shown += 1
                print(f"\n{meta[ids[gi]]['title'][:60]}")
                for n in near:
                    print(f"   {n['score']:.2f}  {meta[n['id']]['title'][:60]}")
        print(f"  … {min(start + CHUNK, X.shape[0])}/{X.shape[0]}")

    total = sum(len(v) for v in out.values())
    withl = sum(1 for v in out.values() if v)
    print(f"\nсвязей {total}, статей со связями {withl} из {len(out)} "
          f"({withl * 100 // max(1, len(out))}%), в среднем {total / max(1, len(out)):.1f}")
    if args.dry:
        print("черновой прогон — ничего не записано")
    else:
        OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        print(f"файл: {OUT} ({OUT.stat().st_size // 1024} КБ)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
