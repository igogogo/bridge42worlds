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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--top", type=int, default=4)
    ap.add_argument("--min", type=float, default=0.10)
    args = ap.parse_args()

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
