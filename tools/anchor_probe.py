# -*- coding: utf-8 -*-
"""ПРОБА: якорение понятий в тексте статьи вектором, а не словарём.

Владелец 26.08: «словарь — плохой механизм, мы так ничего не найдём: понятия есть,
написание другое. Надо тоже вектором. Пробуй, ищи как делать, покажи результат».

КАК УСТРОЕНА ПРОБА (три шага, все вектором bge-m3 — тем же, что и всё остальное):

  1. Текст статьи режется на предложения, каждое получает вектор.
  2. Для каждого ПРИВЯЗАННОГО к статье понятия (разметка v2 уже есть) ищется
     ближайшее по смыслу предложение: вектор английской карточки понятия против
     векторов русских предложений — bge-m3 кросс-язычный, перевод не нужен.
  3. Внутри лучшего предложения ищется ФРАЗА-ЯКОРЬ: окна из 1-5 соседних слов
     векторизуются, ближайшее к карточке окно и есть место ссылки. Так
     «запутанные фотоны» станут ссылкой на quantum_entanglement, хотя словарного
     совпадения между ними нет.

ПОРОГИ ЗДЕСЬ НЕ НАЗНАЧАЮТСЯ — проба их ПОКАЗЫВАЕТ: печатается сходство каждого
якоря, и по живым примерам видно, где проводить границу.

    python tools/anchor_probe.py ID [ID...] --html   показать разметку страницей
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT.parent / "b42-ml"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ML))

from tools.concept_harvest import embed  # noqa: E402  тот же движок

MIN_SENT = 40          # предложения короче — служебные обрывки
WIN = (1, 2, 3, 4, 5)  # окна фразы-якоря, в словах


def sentences(text):
    text = re.sub(r"\[(tag|law|scientist):[^\]]+\]|\[/(tag|law|scientist)\]", "", text)
    text = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+(?=[А-ЯA-ZЁ])", text)
    return [p.strip() for p in parts if len(p.strip()) >= MIN_SENT]


def article(aid):
    hits = (list((ROOT / "lang/ru/archive").glob(f"*/{aid}/data.json"))
            or list((ROOT / "lang/ru/archive").glob(f"*/{aid.split('v')[0]}*/data.json")))
    if not hits:
        return None
    d = json.loads(hits[0].read_text(encoding="utf-8"))
    v = d.get("popular", {}).get("ru") or {}
    return {"title": v.get("title", aid), "text": v.get("text", ""),
            "concepts": [c for c in (v.get("concepts_v2") or []) if c]}


def probe(aid, live, cids, CV, np):
    art = article(aid)
    if not art or not art["text"]:
        print(f"{aid}: нет текста")
        return None
    sents = sentences(art["text"])
    if not sents:
        return None
    row = {c: i for i, c in enumerate(cids)}
    concepts = [c for c in art["concepts"] if c in row]
    print(f"\n═══ {art['title'][:70]}")
    print(f"    предложений {len(sents)} · понятий v2 {len(concepts)}")

    SV = np.asarray(embed(sents), dtype=np.float32)
    SV /= np.linalg.norm(SV, axis=1, keepdims=True) + 1e-9

    anchors = []
    for c in concepts:
        cv = CV[row[c]]
        sims = SV @ cv
        j = int(sims.argmax())
        s_sim = float(sims[j])
        # фраза-якорь: окна слов лучшего предложения
        words = sents[j].split()
        spans = []
        for w in WIN:
            for s in range(0, max(1, len(words) - w + 1)):
                spans.append(" ".join(words[s:s + w]))
        seen = set()
        spans = [s for s in spans if not (s.lower() in seen or seen.add(s.lower()))]
        PV = np.asarray(embed(spans), dtype=np.float32)
        PV /= np.linalg.norm(PV, axis=1, keepdims=True) + 1e-9
        psims = PV @ cv
        k = int(psims.argmax())
        name_ru = (live["concepts"].get(c, {}).get("names") or {}).get("ru", "")
        anchors.append({"concept": c, "name_ru": name_ru, "sent": j,
                        "sent_sim": round(s_sim, 3),
                        "phrase": spans[k], "phrase_sim": round(float(psims[k]), 3)})
        print(f"    {s_sim:.3f}/{float(psims[k]):.3f}  {c:<34} → «{spans[k]}»")
    return {"title": art["title"], "sents": sents, "anchors": anchors}


def html_out(results, path):
    """Наглядная страница: текст с подсвеченными якорями + таблица сходств."""
    import html as H
    parts = ["""<!doctype html><meta charset="utf-8"><title>Проба якорения</title>
<link rel="stylesheet" href="/css/tokens.css"><style>
body{font-family:var(--sans);background:var(--bg);color:var(--text);max-width:760px;
margin:0 auto;padding:24px 16px;line-height:1.7}
h1{font-family:var(--serif)}h2{font-family:var(--serif);font-size:19px;margin-top:36px}
mark{background:rgba(46,138,160,.16);border-bottom:2px solid var(--cyan);padding:0 2px;
border-radius:3px;cursor:help}
table{border-collapse:collapse;font-size:13px;margin:10px 0;width:100%}
td,th{border-bottom:1px solid var(--hair);padding:4px 8px;text-align:left;font-family:var(--mono)}
.lo{color:var(--ochre)}</style>
<h1>Проба: понятия заякорены в тексте вектором</h1>
<p>Подсветка — фраза-якорь, найденная по смыслу (словарного совпадения не требуется).
Числа: сходство предложения / сходство фразы с карточкой понятия.</p>"""]
    for r in results:
        parts.append(f"<h2>{H.escape(r['title'])}</h2><table><tr><th>понятие</th>"
                     f"<th>фраза-якорь</th><th>предл.</th><th>фраза</th></tr>")
        for a in r["anchors"]:
            cls = ' class="lo"' if a["phrase_sim"] < 0.55 else ""
            nm = a["name_ru"] or a["concept"].replace("_", " ")
            parts.append(f"<tr{cls}><td>{H.escape(nm)}</td><td>«{H.escape(a['phrase'])}»</td>"
                         f"<td>{a['sent_sim']}</td><td>{a['phrase_sim']}</td></tr>")
        parts.append("</table>")
        # текст с подсветкой
        anchors_by_sent = {}
        for a in r["anchors"]:
            anchors_by_sent.setdefault(a["sent"], []).append(a)
        out = []
        for i, s in enumerate(r["sents"]):
            es = H.escape(s)
            for a in anchors_by_sent.get(i, []):
                ep = H.escape(a["phrase"])
                nm = a["name_ru"] or a["concept"]
                es = es.replace(ep, f'<mark title="{H.escape(nm)} · {a["phrase_sim"]}">{ep}</mark>', 1)
            out.append(es)
        parts.append("<p>" + " ".join(out) + "</p>")
    Path(path).write_text("".join(parts), encoding="utf-8")
    print(f"\n→ {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--html", action="store_true")
    a = ap.parse_args()
    import numpy as np
    import concepts_super as cs
    cids, CV = cs.load_cards()
    live = json.loads((ROOT / "data/concepts-live.json").read_text(encoding="utf-8"))
    results = []
    for aid in a.ids:
        r = probe(aid, live, cids, CV, np)
        if r:
            results.append(r)
    if a.html and results:
        html_out(results, ROOT / "anchor-probe.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
