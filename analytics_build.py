"""Аналитика «преломлённая через статьи» — офлайн-препросчёт, БЕЗ DeepSeek (юзер 2026-07-24).
Статьи как связующая среда: со-встречаемость тегов/учёных в статьях → близость → кластеры → 2D-карта.

Считает и кладёт в data/ маленькие JSON, которые читают клиентские страницы:
  - data/analytics/articles-map.json   — карта статей: {id,x,y,cluster,title,date} + мета кластеров
  - data/analytics/tags-cooc.json       — со-встречаемость тегов: кластеры + топ-связи на тег
  - data/analytics/scientists-cooc.json — со-встречаемость учёных
Фаза 2 (позже) — семантические эмбеддинги абстрактов (sentence-transformers), тот же формат.

Запуск: python analytics_build.py   (нужны numpy/scipy/pandas/scikit-learn)
"""
import json
import sys
from pathlib import Path
from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE

# cp1252-консоль Windows роняет печать ✅/❌ при ручном запуске
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Языки — из config.json, не списком: хардкод ["ru","en","es","ar"] — причина того, что
# пятый язык (fr) прошёл мимо половины инструментов (аудит 2026-07-30). Здесь он дожил
# до 2026-07-31: трактовки кластеров генерились без fr, и французская страница /analytics
# показывала имена групп через фолбэк.
_CONFIG = json.loads(Path("config.json").read_text(encoding="utf-8"))
DEFAULT_LANG = _CONFIG.get("default_lang", "ru")
LANGS = tuple(_CONFIG.get("languages", ["ru"]))
LANG_NAME = {"ru": "Russian", "en": "English", "es": "Spanish", "ar": "Arabic",
             "fr": "French", "zh": "Chinese"}
OUT = Path("data/analytics")
OUT.mkdir(parents=True, exist_ok=True)


# ── LLM-трактовка кластеров (юзер 2026-07-24: «трактовка — это изюминка; мы сами должны трактовать,
#    но у нас есть ИИ»). Кластеры считает математика (бесплатно), а человеческое ИМЯ+ОПИСАНИЕ каждой
#    группе даёт ИИ — по одному вызову на язык (дёшево). Включается флагом --interpret / interpret=True,
#    чтобы обычный пересчёт карты DeepSeek не трогал. Вызывается в пайплайне после «залили новый день».
def interpret_clusters(cluster_top, samples, kind, langs=LANGS):
    """cluster_top: {cid: [характерные теги]}, samples: {cid: [примеры-заголовки]}.
    Возвращает {cid: {lang: {"title","desc"}}} — человеческие названия групп на каждом языке."""
    from common import chat, clean_json  # ленивый импорт: чистый пересчёт карты не требует API-ключа
    ids = sorted(cluster_top, key=lambda c: int(c))
    lines = []
    for c in ids:
        ex = (samples or {}).get(int(c)) or (samples or {}).get(str(c)) or []
        row = f'#{c}: tags = [{", ".join(cluster_top[c])}]'
        if ex:
            row += "; sample titles: " + " | ".join(x for x in ex[:4] if x)
        lines.append(row)
    body = "\n".join(lines)
    what = ("thematic groups of related science articles" if kind == "articles"
            else "groups of researchers sharing a research profile (by their papers' arXiv areas)")
    out = {str(c): {} for c in ids}
    for lang in langs:
        prompt = (
            f"You are curating a popular-science site. Below are numbered clusters — {what}. "
            f"Each line lists a cluster's characteristic tags (technical ids) and, when available, sample titles. "
            f"For EVERY cluster id, give:\n"
            f'  "title": a short, vivid human name (2–4 words, NO underscores, NO jargon ids),\n'
            f'  "desc": ONE plain-language sentence telling a curious non-expert what unites this group and why it matters.\n'
            f"Write BOTH fields in {LANG_NAME.get(lang, lang)}. Do not transliterate the tag ids — interpret their meaning. "
            f'Return STRICT JSON: {{"<id>": {{"title": "...", "desc": "..."}}, ...}} covering every id below.\n\n{body}')
        # reasoning-модель изредка возвращает пустой/битый ответ (весь бюджет ушёл в рассуждение) —
        # ретраим, иначе целый язык выпадает из трактовки.
        data = None
        for attempt in range(3):
            try:
                resp = chat("cluster_interpret", prompt)
                raw = resp.choices[0].message.content or ""
                if raw.strip():
                    # Через clean_json, а не голым json.loads: латех внутри строки («\frac»,
                    # «\nu», «\upsilon») роняет разбор целиком, и трактовка кластера пропадала
                    # молча — три попытки подряд на одном и том же тексте. Владелец 2026-08-06:
                    # «везде это проверь, и при генерации, не только в переводе».
                    data = json.loads(clean_json(raw))
                    break
            except Exception as e:
                if attempt == 2:
                    print(f"  ⚠️ трактовка ({kind}/{lang}) не удалась после 3 попыток: {e}")
        if data is None:
            print(f"  ⚠️ трактовка ({kind}/{lang}) пуста — пропуск языка")
            continue
        for c in ids:
            v = data.get(str(c)) or data.get(int(c)) or {}
            if isinstance(v, dict) and v.get("title"):
                out[str(c)][lang] = {"title": str(v.get("title", "")).strip(),
                                     "desc": str(v.get("desc", "")).strip()}
        print(f"  трактовка {kind}/{lang}: {sum(1 for c in ids if out[str(c)].get(lang))}/{len(ids)} кластеров")
    return out


def load_articles():
    idx = json.loads(Path(f"lang/{DEFAULT_LANG}/articles-index.json").read_text(encoding="utf-8"))
    seen, arts = set(), []
    for a in idx:
        if a["id"] in seen:
            continue
        seen.add(a["id"])
        arts.append(a)
    return arts


# arXiv-разделы, явно тяготеющие к теории или эксперименту — для оси «теоретик↔экспериментатор».
THEORY_HINT = ("-th", "gr-qc", "math-ph", "hep-lat", "nlin", "cond-mat.stat-mech", "cond-mat.str-el")
EXPERIMENT_HINT = ("-ex", "physics.ins-det", "astro-ph.im", "eess", "physics.med-ph", "physics.app-ph")


def _lean(cat):
    c = cat.lower()
    if any(h in c for h in THEORY_HINT):
        return "T"
    if any(h in c for h in EXPERIMENT_HINT):
        return "E"
    return None


def _tsne3(X, n):
    perp = max(5, min(40, n // 30))
    Xd = X.toarray() if hasattr(X, "toarray") else X
    # TF-IDF L2-нормирован → евклид монотонен косинусу. На больших множествах (все авторы, 16k+)
    # cosine-t-SNE форсит exact O(n²) и виснет — берём быстрый barnes_hut/euclidean.
    if n > 5000:
        xyz = TSNE(n_components=3, method="barnes_hut", init="pca", perplexity=perp,
                   random_state=0).fit_transform(Xd)
    else:
        xyz = TSNE(n_components=3, metric="cosine", init="random", perplexity=perp,
                   random_state=0).fit_transform(Xd)
    return (xyz - xyz.min(0)) / (np.ptp(xyz, 0) + 1e-9)  # 0..1 по каждой оси


def build_article_map(arts, interpret=False):
    # Документ = мультимножество тегов статьи (space-joined), TF-IDF взвешивает по редкости.
    docs = [" ".join((a.get("tags") or [])) for a in arts]
    keep = [i for i, d in enumerate(docs) if d.strip()]
    arts = [arts[i] for i in keep]
    docs = [docs[i] for i in keep]
    if len(arts) < 10:
        print("мало статей с тегами — пропуск карты"); return
    vec = TfidfVectorizer(token_pattern=r"[^ ]+", min_df=2)
    X = vec.fit_transform(docs)
    n_clusters = max(6, min(24, len(arts) // 60))
    labels = KMeans(n_clusters=n_clusters, n_init=6, random_state=0).fit(X).labels_
    xyz = _tsne3(X, len(arts))  # 3D — можно покрутить (юзер 2026-07-24)
    terms = np.array(vec.get_feature_names_out())
    Xd = X.toarray()
    cluster_top = {}
    for c in range(n_clusters):
        m = labels == c
        if m.any():
            cluster_top[int(c)] = list(terms[np.asarray(Xd[m].mean(0)).ravel().argsort()[::-1][:4]])
    points = [{"id": a["id"], "t": (a.get("title") or "")[:80], "d": a.get("date", ""),
               "x": round(float(xyz[i][0]), 4), "y": round(float(xyz[i][1]), 4), "z": round(float(xyz[i][2]), 4),
               "c": int(labels[i]), "url": a.get("url", "")} for i, a in enumerate(arts)]
    out = {"points": points, "clusters": cluster_top, "n": len(points)}
    if interpret:
        samples = {}
        for i, a in enumerate(arts):
            samples.setdefault(int(labels[i]), [])
            if len(samples[int(labels[i])]) < 4:
                samples[int(labels[i])].append((a.get("title") or "")[:80])
        out["titles"] = interpret_clusters(cluster_top, samples, "articles")
    (OUT / "articles-map.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"articles-map: {len(points)} статей, {n_clusters} кластеров (3D){' + трактовка' if interpret else ''}")


def build_author_map(arts, min_articles=1, interpret=False):  # ВСЕ авторы (юзер 2026-07-24: важно не
    # число точек-авторов, а как ведёт себя ВСЁ множество — облака-кластеры; хоть 1 статья, хоть 3.
    # Профиль автора = смесь arXiv-разделов его статей (юзер: не число статей, а КТО он — теоретик/
    # экспериментатор, тематические облака). id→разделы берём из индекса; автор→статьи из графа авторов.
    ap = Path("data/authors-graph.json")
    if not ap.exists():
        print("нет authors-graph.json — пропуск карты авторов"); return
    graph = json.loads(ap.read_text(encoding="utf-8"))
    id2cats = {a["id"]: (a.get("categories") or []) for a in arts}
    id2primary = {a["id"]: (a.get("categories") or ["?"])[0] for a in arts}

    names, docs, leans = [], [], []
    for name, g in graph.items():
        ids = g.get("articles") or []
        if len(ids) < min_articles:
            continue
        cats = []
        t = e = 0
        for aid in ids:
            for c in id2cats.get(aid, []):
                cats.append(c.replace(".", "_"))
            L = _lean(id2primary.get(aid, ""))
            if L == "T":
                t += 1
            elif L == "E":
                e += 1
        if not cats:
            continue
        names.append(name)
        docs.append(" ".join(cats))
        leans.append(round(t / (t + e), 3) if (t + e) else 0.5)  # 1=теоретик, 0=экспериментатор
    n = len(names)
    if n < 20:
        print(f"мало авторов с профилем ({n}) — пропуск"); return
    vec = TfidfVectorizer(token_pattern=r"[^ ]+", min_df=3)
    X = vec.fit_transform(docs)
    n_clusters = max(8, min(24, n // 400))  # всё множество авторов → чуть больше кластеров-облаков
    labels = KMeans(n_clusters=n_clusters, n_init=6, random_state=0).fit(X).labels_
    xyz = _tsne3(X, n)
    terms = np.array(vec.get_feature_names_out())
    Xd = X.toarray()
    cluster_top = {}
    for c in range(n_clusters):
        m = labels == c
        if m.any():
            cluster_top[int(c)] = list(terms[np.asarray(Xd[m].mean(0)).ravel().argsort()[::-1][:4]])
    points = [{"id": names[i], "x": round(float(xyz[i][0]), 4), "y": round(float(xyz[i][1]), 4),
               "z": round(float(xyz[i][2]), 4), "c": int(labels[i]), "th": leans[i]} for i in range(n)]
    out = {"points": points, "clusters": cluster_top, "n": n}
    if interpret:
        # для авторов метки = коды разделов; примеров-заголовков нет — трактуем по разделам.
        out["titles"] = interpret_clusters(cluster_top, {}, "authors")
    (OUT / "authors-map.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"authors-map: {n} авторов (≥{min_articles} статей), {n_clusters} кластеров, ось теория↔эксп (3D){' + трактовка' if interpret else ''}")


def cooccurrence(arts, field, out_name, min_count=3, top_neighbors=8):
    # Со-встречаемость сущностей (тегов/учёных) в одних статьях.
    freq = Counter()
    pairs = Counter()
    for a in arts:
        items = sorted(set(x for x in (a.get(field) or []) if x))
        for x in items:
            freq[x] += 1
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                pairs[(items[i], items[j])] += 1
    keep = {x for x, c in freq.items() if c >= min_count}
    ent = sorted(keep, key=lambda x: -freq[x])
    idx = {x: i for i, x in enumerate(ent)}
    n = len(ent)
    if n < 8:
        print(f"{out_name}: мало сущностей ({n}) — пропуск"); return
    # матрица близости (Jaccard по со-встречаемости) для кластеризации
    M = np.zeros((n, n), dtype=np.float32)
    for (x, y), c in pairs.items():
        if x in idx and y in idx:
            j = c / (freq[x] + freq[y] - c + 1e-9)
            M[idx[x]][idx[y]] = M[idx[y]][idx[x]] = j
    n_clusters = max(5, min(20, n // 20))
    km = KMeans(n_clusters=n_clusters, n_init=6, random_state=0).fit(M)
    labels = km.labels_
    # топ-соседи каждой сущности
    neigh = {}
    for x in ent:
        i = idx[x]
        order = M[i].argsort()[::-1]
        neigh[x] = [(ent[j], round(float(M[i][j]), 3)) for j in order if M[i][j] > 0][:top_neighbors]
    data = {"entities": [{"id": x, "n": freq[x], "c": int(labels[idx[x]]), "nb": neigh[x]} for x in ent]}
    (OUT / out_name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"{out_name}: {n} сущностей, {n_clusters} кластеров")


def main():
    interpret = "--interpret" in sys.argv  # + LLM-имена кластерам (тратит DeepSeek); без флага — бесплатно
    arts = load_articles()
    print(f"загружено уникальных статей: {len(arts)}" + (" | ТРАКТОВКА ИИ: вкл" if interpret else ""))
    build_article_map(arts, interpret=interpret)
    build_author_map(arts, interpret=interpret)
    cooccurrence(arts, "tags", "tags-cooc.json", min_count=3)
    cooccurrence(arts, "scientists", "scientists-cooc.json", min_count=2)
    print("АНАЛИТИКА ПОСЧИТАНА → data/analytics/")


if __name__ == "__main__":
    main()
