# -*- coding: utf-8 -*-
"""Сопоставление наших авторов с Semantic Scholar — офлайн, по уже собранному.

Владелец 27.08: «по полной имплементируем везде… престиж для учёных» и «не забудь
про авторов». Ключ нашего реестра — отображаемое имя из статьи; у S2 — authorId.
Мостик — сами статьи: у каждой нашей статьи S2 вернул список её авторов с id.
Для автора X идём по его статьям, в каждой ищем S2-автора с той же фамилией
(и совпадающей первой буквой имени, если она есть), собираем голоса и берём
самый частый id: один человек под разными написаниями сходится к одному id,
случайный однофамилец в одной статье — нет.

Результат: data/s2/author-map.json {наше имя: {"id", "hIndex", "citations",
"papers", "affiliations"}} — данные подшиты сразу, рендеру не нужно ходить
по трём файлам.

    python tools/s2_author_map.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
S2 = ROOT / "data" / "s2"


def norm(name):
    """(фамилия, первая буква имени) — терпит 'J. H. Adams,', 'Adams J.', диакритику."""
    s = re.sub(r"[.,]", " ", name or "").strip().lower()
    parts = [p for p in s.split() if p]
    if not parts:
        return "", ""
    # фамилия — самое длинное слово с конца (инициалы длиной 1 отбрасываем)
    last = next((p for p in reversed(parts) if len(p) > 1), parts[-1])
    first = next((p[0] for p in parts if p != last), "")
    return last, first


def main():
    papers = json.loads((S2 / "papers.json").read_text(encoding="utf-8"))
    s2_authors = json.loads((S2 / "authors.json").read_text(encoding="utf-8")) \
        if (S2 / "authors.json").exists() else {}
    graph = json.loads((ROOT / "data/authors-graph.json").read_text(encoding="utf-8"))

    out, matched = {}, 0
    for name, d in graph.items():
        last, first = norm(name)
        if not last:
            continue
        votes = Counter()
        for aid in d.get("articles", []):
            rec = papers.get(aid)
            if not rec:
                continue
            cands = []
            for sa in rec.get("authors") or []:
                sl, sf = norm(sa.get("name"))
                if sl == last and (not first or not sf or sf == first):
                    cands.append(sa.get("authorId"))
            # голос только при однозначности внутри статьи: два однофамильца — молчим
            if len(set(filter(None, cands))) == 1:
                votes[cands[0]] += 1
        if not votes:
            continue
        best, n = votes.most_common(1)[0]
        if n < 1:
            continue
        a = s2_authors.get(best) or {}
        out[name] = {
            "id": best,
            "hIndex": a.get("hIndex"),
            "citations": a.get("citationCount"),
            "papers": a.get("paperCount"),
            "affiliations": (a.get("affiliations") or [])[:2],
        }
        matched += 1
    (S2 / "author-map.json").write_text(json.dumps(out, ensure_ascii=False),
                                        encoding="utf-8")
    print(f"✅ сопоставлено {matched}/{len(graph)} авторов → data/s2/author-map.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
