#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Контекстные ссылки на разобранные работы: к утверждению, а не списком внизу.

Владелец 03.09: «куда будут вставлены ссылки на статьи? контекстно? тут поможет вектор?»
Да — и вот почему именно вектор, а не слова: якорь на панели говорит «модели занижают
прогноз», а работа называется «systematic cold bias in seasonal SST hindcasts». Общих слов
нет ни одного, смысл один. Кандидатов мало (сотни отобранных климатических работ, не три
миллиона), поэтому ступень со словами не нужна: считаем сходство напрямую по всем.

ДВА ШАГА, И ВТОРОЙ ОБЯЗАТЕЛЕН.
  1. Вектор находит «про то же»: bge-m3, косинус, верхние TOP штук выше пола FLOOR.
  2. Модель решает, «подпирает ли это утверждение»: пары «утверждение + аннотация» уходят
     в DeepSeek, и остаются только те, где работа действительно объясняет или подтверждает,
     с одной фразой «что она сюда добавляет». Связь, которую никто не проверил, на панель
     не идёт — то же правило, что у машины знаний с опорами.

ЯКОРЯ (что именно обвешиваем ссылками):
  risk:*    карточки рисков          alert:*   тревоги (климат, цены, модели)
  region:*  строки регионов          term:*    статьи глоссария
  block:*   утверждения блоков (как ломаются модели, цены, оценка пика)

    python tools/enso/links.py --dry           только вектор, показать кандидатов
    python tools/enso/links.py                 вектор + проверка моделью, записать links.json
    python tools/enso/links.py --limit 5       на пробу, пять якорей
"""
import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "enso"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

FIELD_DB = ROOT / "data" / "arxiv-field.sqlite"
CACHE = DATA / "links-cache.jsonl"
OUT = DATA / "links.json"
TOP = 8                 # сколько кандидатов вектор отдаёт модели на проверку
FLOOR = 0.50            # пол по косинусу: ниже — уже соседняя тема (bge-m3 лежит узко)
FLOOR_WEAK = 0.42       # второй заход для якорей, которым не нашлось ничего: помечаем weak
KEEP = 3                # сколько ссылок остаётся у одного якоря после проверки
MODEL = os.environ.get("ELNINO_LLM_MODEL", "deepseek-v4-pro")

SYSTEM = """You decide whether a scientific paper belongs next to a specific statement on a
climate dashboard. You are given the statement and a few candidate papers (title and abstract).

Rules:
1. Keep a paper only if it explains, supports or measures what the statement is about. A paper
   on the same broad topic that does not touch the statement is NOT kept.
2. Never claim the paper proves a number on the dashboard. The link means "this is what the
   research says about this", not "this is the source of that number".
3. For every kept paper write one line, at most 140 characters, saying what it adds here:
   the mechanism, the measurement, or the caveat. Plain English, no jargon without a gloss,
   no dashes joining clauses — use words.
4. Prefer papers that add something the dashboard cannot say by itself. Two good links beat
   five weak ones. Keeping nothing is a valid answer.
5. Answer strictly as JSON: {"keep": [{"id": "...", "why": "...", "kind": "explains|supports|background"}]}
   with ids exactly as given, ordered best first."""


# ---------------------------------------------------------------- якоря
def _aslug(title):
    """Тот же slug считает панель (js/enso.js, aslug): менять только вместе."""
    return re.sub(r"[^a-z0-9]+", "_", str(title).lower()).strip("_")[:48]


def anchors():
    D = json.loads((DATA / "latest.json").read_text(encoding="utf-8"))
    gl = (json.loads((DATA / "glossary.json").read_text(encoding="utf-8")) or {}).get("en") or {}
    ref = json.loads((DATA / "regions-ref.json").read_text(encoding="utf-8"))
    out = []

    # ЯКОРЬ — ИМЯ РИСКА, НЕ НОМЕР. Список рисков сортируется по уровню и меняется от прогона к
    # прогону; ссылка по номеру после появления нового риска уезжала на чужую карточку.
    # Имя (rid) живёт, пока живёт правило. Тревоги без имени — по slug заголовка.
    for i, r in enumerate(D.get("risks") or []):
        out.append({"id": "risk:" + (r.get("id") or str(i)), "label": r["title"], "kind": "risk",
                    "text": " ".join([r["title"], r.get("plain") or "", r.get("evidence") or "",
                                      "What to watch: " + (r.get("watch") or "")])})
    for i, a in enumerate(D.get("alerts") or []):
        out.append({"id": "alert:" + _aslug(a["title"]), "label": a["title"], "kind": "alert:" + (a.get("kind") or "climate"),
                    "text": a["title"] + ". " + (a.get("detail") or "")})
    for r in (ref.get("regions") or []):
        seasons = " ".join((v or {}).get("note") or "" for v in (r.get("seasons") or {}).values())
        out.append({"id": "region:" + r["id"], "label": r["name"], "kind": "region",
                    "text": " ".join([r["name"], r.get("countries") or "", seasons,
                                      (r.get("vulnerability") or {}).get("note") or ""])})
    for k, g in gl.items():
        out.append({"id": "term:" + k, "label": g["name"], "kind": "term",
                    "text": " ".join([g["name"], g.get("def") or "", g.get("why") or ""])})

    # утверждения самой панели, которые просят подкрепления сильнее всего
    iri = D.get("iri") if isinstance(D.get("iri"), dict) else {}
    bd = iri.get("breakdown") or {}
    rows = bd.get("by_issue") or []
    if rows:
        out.append({"id": "block:models", "kind": "block", "label": "How the forecast models break",
                    "text": ("Seasonal forecast models systematically underestimate a strong El Niño: the share of "
                             f"models below the observed ONI grew from {rows[0]['share']} % in the {rows[0]['issue']} "
                             f"issue to {rows[-1]['share']} % in the {rows[-1]['issue']} issue, and the same models "
                             "lag issue after issue. Why do dynamical and statistical seasonal models have a cold "
                             "bias in strong events, and what is the skill limit of ENSO prediction.")})
    pe = (D.get("nino34") or {}).get("peak_estimate") or {}
    if pe:
        out.append({"id": "block:peak", "kind": "block", "label": "When the growth stops",
                    "text": ("The current El Niño is already above every analogue on the same calendar days, so the "
                             "usual way of estimating the peak from past events breaks down. What sets the peak of an "
                             "El Niño event, why it happens in November to January, and what stops the growth.")})
    food = D.get("food") if isinstance(D.get("food"), dict) else {}
    if food and not food.get("error"):
        out.append({"id": "block:food", "kind": "block", "label": "El Niño and food prices",
                    "text": ("How El Niño moves world food prices and crop yields: teleconnections to harvests, the "
                             "lag between the ocean and the market, and which crops and regions carry the shock.")})
    out.append({"id": "block:type", "kind": "block", "label": "Eastern-type El Niño",
                "text": ("Eastern Pacific (canonical) El Niño against central Pacific (Modoki): what makes the warm "
                         "pool sit off South America, how the two flavours differ in their impacts, and why the "
                         "eastern type is the harsher one.")})
    return out


# ---------------------------------------------------------------- работы
def works(limit_ids=None):
    """Разобранные климатические работы: номер, дата, английское название, аннотация arXiv."""
    ids = []
    for name in ("works-tier1.txt", "works-tier2.txt"):
        p = DATA / name
        if p.exists():
            ids += [l.strip() for l in p.read_text(encoding="utf-8").splitlines()
                    if l.strip() and not l.startswith("#")]
    have = {}
    for p in ROOT.glob("lang/ru/archive/*/*/data.json"):
        have[p.parent.name.split("v")[0]] = p
    # Аннотация — из дампа arXiv тем же способом, что у tools/field.py: индекс FTS у нас
    # contentless (content=''), из него текст не достать, а дамп лежит по месяцам.
    sys.path.insert(0, str(ROOT / "tools"))
    import field as FLD
    pairs, meta = [], {}
    for aid in ids:
        base = aid.split("v")[0]
        p = have.get(base)
        if not p:
            continue
        meta[base] = p
        pairs.append((aid, FLD._mon_of(aid)))
    abstracts = FLD._abstracts(pairs) if pairs else {}
    rows = []
    for aid, _mon in pairs:
        base = aid.split("v")[0]
        p = meta[base]
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            continue
        title, abstract = "", ""
        got = abstracts.get(aid) or abstracts.get(base)
        if got:
            title, abstract = got[0], got[1]
        title = title or d.get("original_title") or ""
        # НАШ заголовок и НАША строка, а не только авторские. Владелец 04.09: цель — чтобы
        # на дашборде контекстно появлялись разобранные НАМИ работы; значит и показывать надо
        # то, что мы про них написали, а не пересказ титульного листа.
        pop_en = ((d.get("popular") or {}).get("en") or {})
        rows.append({"id": d.get("id") or base, "folder": p.parent.name, "date": p.parent.parent.name,
                     "title": " ".join(title.split()),
                     "our_title": (pop_en.get("title") or "").strip(),
                     "oneliner": (pop_en.get("oneliner") or "").strip(),
                     "text": (" ".join(title.split()) + ". " + abstract)[:2400],
                     "primary": d.get("primary_category") or ""})
        if limit_ids and len(rows) >= limit_ids:
            break
    return rows


# ---------------------------------------------------------------- вектор
def vectors(texts, label):
    from embeddings_build import embed_cached, load_env
    import numpy as np
    key = load_env(ROOT).get("DEEPINFRA_API_KEY", "")
    if not key:
        sys.exit("нет DEEPINFRA_API_KEY в .env — эмбеддинги не посчитать")
    cut = [" ".join(t.split())[:2400] for t in texts]
    m = np.asarray(embed_cached(cut, key, CACHE, label, agent="enso-links"), dtype=np.float32)
    m /= np.linalg.norm(m, axis=1, keepdims=True) + 1e-9
    return m


def candidates(A, W, anc, wks):
    import numpy as np
    sim = A @ W.T
    out = {}
    for i, a in enumerate(anc):
        order = np.argsort(-sim[i])[:TOP]
        picks = [{"w": wks[j], "score": round(float(sim[i][j]), 3)} for j in order if sim[i][j] >= FLOOR]
        # ВТОРОЙ ЗАХОД С НИЗКИМ ПОРОГОМ. Из 87 якорей ссылки нашлись у сорока: пул в сто
        # работ мал, и половине якорей нечего предложить выше 0.50. Вместо пустоты берём
        # лучших кандидатов выше FLOOR_WEAK и помечаем weak — решает по-прежнему модель,
        # она отбрасывает натяжки так же строго. На панели такая ссылка подписана честно:
        # «более далёкое совпадение».
        if not picks:
            picks = [{"w": wks[j], "score": round(float(sim[i][j]), 3), "weak": True}
                     for j in order[:KEEP] if sim[i][j] >= FLOOR_WEAK]
        if picks:
            out[a["id"]] = picks
    return out


# ---------------------------------------------------------------- проверка моделью
def verify(anc_by_id, cands, quiet=False):
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        print("⚠️ нет DEEPSEEK_API_KEY — оставляю только вектор, с пометкой")
        return {k: [{"id": c["w"]["id"], "date": c["w"]["date"], "folder": c["w"]["folder"],
                     "title": c["w"]["title"], "score": c["score"], "why": "", "kind": "unverified"}
                    for c in v[:KEEP]] for k, v in cands.items()}
    from openai import OpenAI
    client = OpenAI(api_key=key, base_url="https://api.deepseek.com", timeout=120)
    out, spent = {}, {"in": 0, "out": 0}
    for n, (aid, picks) in enumerate(cands.items(), 1):
        a = anc_by_id[aid]
        payload = {"statement": a["text"], "where_it_appears": a["kind"],
                   "papers": [{"id": c["w"]["id"], "title": c["w"]["title"], "abstract": c["w"]["text"][:1400]}
                              for c in picks]}
        try:
            r = client.chat.completions.create(
                model=MODEL, temperature=0.1, response_format={"type": "json_object"},
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])
            got = json.loads(r.choices[0].message.content)
            if r.usage:
                spent["in"] += r.usage.prompt_tokens; spent["out"] += r.usage.completion_tokens
        except Exception as e:                               # noqa: BLE001
            print(f"  ⚠️ {aid}: модель не ответила ({str(e)[:90]}) — якорь без ссылок")
            continue
        by_id = {c["w"]["id"]: c for c in picks}
        keep = []
        for k in (got.get("keep") or [])[:KEEP]:
            c = by_id.get(k.get("id"))
            if not c:
                continue
            keep.append({"id": c["w"]["id"], "date": c["w"]["date"], "folder": c["w"]["folder"],
                         "title": c["w"]["title"],
                         "our_title": c["w"].get("our_title") or "",
                         "oneliner": c["w"].get("oneliner") or "",
                         "score": c["score"], "weak": bool(c.get("weak")),
                         "why": (k.get("why") or "").strip()[:180], "kind": k.get("kind") or "background"})
        if keep:
            out[aid] = keep
        if not quiet:
            print(f"  {n}/{len(cands)} {aid}: из {len(picks)} оставлено {len(keep)}")
    print(f"проверка моделью: {spent['in']:,} + {spent['out']:,} токенов")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="только вектор, без модели и без записи")
    ap.add_argument("--limit", type=int, help="взять только первые N якорей (проба)")
    a = ap.parse_args()

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    anc = anchors()
    if a.limit:
        anc = anc[:a.limit]
    wks = works()
    print(f"якорей {len(anc)}, разобранных климатических работ {len(wks)}")
    if not wks:
        sys.exit("нет ни одной разобранной работы из списков — сначала works_run.py")

    A = vectors([x["text"] for x in anc], "якоря")
    W = vectors([w["text"] for w in wks], "работы")
    cands = candidates(A, W, anc, wks)
    print(f"вектор дал кандидатов для {len(cands)} якорей из {len(anc)}")
    if a.dry:
        for k, v in list(cands.items())[:12]:
            print(f"\n{k} — {next(x['label'] for x in anc if x['id'] == k)}")
            for c in v[:4]:
                print(f"   {c['score']:.3f}  {c['w']['id']}  {c['w']['title'][:80]}")
        return 0

    anc_by_id = {x["id"]: x for x in anc}
    links = verify(anc_by_id, cands)
    payload = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "model": MODEL,
               "floor": FLOOR, "floor_weak": FLOOR_WEAK, "top": TOP, "keep": KEEP,
               "n_works": len(wks), "n_anchors": len(anc), "anchors": links,
               "note": "vector finds what is about the same thing; the model decides whether it belongs next to the "
                       "statement. A link means 'this is what the research says about this', not 'this is the source "
                       "of that number'."}
    OUT.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ {OUT.name}: ссылки у {len(links)} якорей из {len(anc)}; работ в пуле {len(wks)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
