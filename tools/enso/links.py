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
import concurrent.futures as cf
import hashlib
import json
import os
import re
import sqlite3
import sys
import threading
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
FLOOR_ALL = 0.56        # работа вне темы (весь архив) — только при заметно большем сходстве
KEEP = 3                # сколько ссылок остаётся у одного якоря после проверки
WORKERS = 4                              # потоков разметки: запросы независимы (06.09)
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
def _delatex(t):
    """Заголовки arXiv несут TeX-акценты: El Ni\\~no показывался на панели буквально
    (28 заголовков в links.json 06.09, проверка Fable). Снимаем самые частые."""
    t = str(t or "")
    for a, b in (("\\~n", "ñ"), ("\\~N", "Ñ"), ("\\'e", "é"), ("\\'a", "á"), ("\\'o", "ó"),
                 ("\\'i", "í"), ("\\'u", "ú"), ('\\"o', "ö"), ('\\"u', "ü"), ('\\"a', "ä"),
                 ("\\c{c}", "ç"), ("{", ""), ("}", ""), (" -- ", " – "), ("$", "")):
        t = t.replace(a, b)
    return " ".join(t.split())

def _deny_load():
    """Снятые вручную ссылки: {якорь: [id работ]}. Кэш приговоров модели иначе вернул бы их
    при следующей разметке. Файл пишет проверяющий (Fable), см. FABLE-ПРОВЕРКА-ПАНЕЛИ.md."""
    p = DATA / "links-deny.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:                                        # noqa: BLE001
        return {}


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
        # id тревоги переживает смену числа в заголовке, slug — нет (06.09).
        out.append({"id": "alert:" + (a.get("id") or _aslug(a["title"])), "label": a["title"], "kind": "alert:" + (a.get("kind") or "climate"),
                    "text": a["title"] + ". " + (a.get("detail") or "")})
    for r in (ref.get("regions") or []):
        seasons = " ".join((v or {}).get("note") or "" for v in (r.get("seasons") or {}).values())
        out.append({"id": "region:" + r["id"], "label": r["name"], "kind": "region",
                    "text": " ".join([r["name"], r.get("countries") or "", seasons,
                                      (r.get("vulnerability") or {}).get("note") or ""])})
    for k, g in gl.items():
        out.append({"id": "term:" + k, "label": g["name"], "kind": "term",
                    "text": " ".join([g["name"], g.get("def") or "", g.get("why") or ""])})

    # ЯКОРЯ ПЛАШЕК KPI. Просьба сессии панели 08.09: у плашки нет своего якоря, и облако
    # понятий приходится брать от термина подписи — попадание случайное. Ключ журнала это
    # и есть имя показателя (n34_daily, food_index, ohc_2000), панель уже ключует им
    # подписи (kmeta), так что дорога та же и правок в панели не нужно.
    try:
        J = json.loads((DATA / "journal.json").read_text(encoding="utf-8"))
        for k, m in (J.get("metrics") or {}).items():
            if k.startswith("risk:"):
                continue                                  # риск уже есть своим якорем
            title = (m.get("title") or k).strip()
            src = (m.get("src") or "").strip()
            if not title:
                continue
            out.append({"id": "kpi:" + k, "label": title, "kind": "kpi",
                        "text": " ".join([title, src, m.get("unit") or ""]).strip()})
    except Exception:                                     # noqa: BLE001
        pass

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
    # НОВЫЕ ИСТОЧНИКИ 07.09 (владелец: «чтобы новые источники вписались так же, как у нас было»)
    out.append({"id": "block:radiance", "kind": "block", "label": "Convection and the Walker circulation seen in raw radiances",
                "text": ("Deep convection over the central and eastern equatorial Pacific read from satellite infrared "
                         "brightness temperature (cold cloud tops below 235 K) and the east-west contrast of outgoing "
                         "longwave radiation as a measure of the Walker circulation; microwave sounders show the tropical "
                         "troposphere warming through cloud during El Niño. How the Walker cell weakens or reverses in a "
                         "strong event, and what satellite radiances and OLR say about the shift of convection.")})
    out.append({"id": "block:spectral", "kind": "block", "label": "Early-warning signals and short-period oscillations before a transition",
                "text": ("Early-warning signals of critical transitions in climate series: critical slowing down, rising "
                         "variance and autocorrelation, spectral reddening, and the appearance of discrete short-period "
                         "oscillations (days) as a system nears the edge of stability; period doubling and subharmonics "
                         "of the diurnal forcing in tropical convection; detection of such signals in daily sea surface "
                         "temperature and air temperature.")})
    out.append({"id": "block:rain", "kind": "block", "label": "El Niño and regional rainfall",
                "text": ("Teleconnections of El Niño to rainfall by region: drought over Indonesia and the Maritime "
                         "Continent, East Africa short rains, the Peru coast floods, the Indian monsoon, and rain over "
                         "the Gulf and Europe; reanalysis and satellite precipitation products (ERA5, GPCP, CHIRPS) and "
                         "their biases in the tropics.")})
    out.append({"id": "block:landbox", "kind": "block", "label": "Regional temperature response to El Niño",
                "text": ("How near-surface air temperature over land regions responds to a strong El Niño: the Peru coast, "
                         "Indonesia, East Africa, the Arabian Gulf, India and Europe; lags of months between the ocean and "
                         "the land, and the year after the peak being warmer than the peak year.")})
    out.append({"id": "block:type", "kind": "block", "label": "Eastern-type El Niño",
                "text": ("Eastern Pacific (canonical) El Niño against central Pacific (Modoki): what makes the warm "
                         "pool sit off South America, how the two flavours differ in their impacts, and why the "
                         "eastern type is the harsher one.")})
    return out


# ---------------------------------------------------------------- работы
TOPIC_IDS = set()


def works(limit_ids=None, all_archive=False):
    """Разобранные климатические работы: номер, дата, английское название, аннотация arXiv.

    all_archive=True — весь архив (владелец 05.09: «попробовать ещё поискать, может что-то
    есть»): работы вне темы допускаются к якорю только при заметно большем сходстве
    (FLOOR_ALL), чтобы широкий пул не нанёс шума."""
    ids = []
    for name in ("works-tier1.txt", "works-tier2.txt"):
        p = DATA / name
        if p.exists():
            ids += [l.strip() for l in p.read_text(encoding="utf-8").splitlines()
                    if l.strip() and not l.startswith("#")]
    have = {}
    for p in ROOT.glob("lang/ru/archive/*/*/data.json"):
        have[p.parent.name.split("v")[0]] = p
    TOPIC_IDS.update(i.split("v")[0] for i in ids)
    if all_archive:
        extra = sorted(b for b in have if b not in TOPIC_IDS)
        ids = ids + extra
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
        title = _delatex(title or d.get("original_title") or "")
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
        def ok(j):
            base = (wks[j]["id"] or "").split("v")[0]
            return sim[i][j] >= (FLOOR if base in TOPIC_IDS else FLOOR_ALL)
        picks = [{"w": wks[j], "score": round(float(sim[i][j]), 3)} for j in order if ok(j)]
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


# ---------------------------------------------------------------- приговоры на диске
VERDICTS = DATA / "links-verdicts.jsonl"


def _verdict_key(a, picks):
    """Якорь плюс набор кандидатов: сменился текст или список работ — спросим заново."""
    parts = [a["id"], a.get("text") or ""] + [c["w"]["id"] for c in picks]
    h = hashlib.md5(chr(1).join(parts).encode("utf-8")).hexdigest()
    return a["id"] + ":" + h[:12]


def _verdicts_load():
    out = {}
    if not VERDICTS.exists():
        return out
    for line in VERDICTS.read_text(encoding="utf-8").splitlines():
        try:
            o = json.loads(line)
            out[o["k"]] = o["v"]
        except Exception:                                    # noqa: BLE001, PERF203
            continue                                         # битую строку просто пропускаем
    return out


def _verdict_save(k, v):
    with VERDICTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"k": k, "v": v}, ensure_ascii=False) + chr(10))


def _keep_from(got, picks):
    """Ответ модели → строки ссылок. Общая для свежего ответа и для взятого из кэша."""
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
    return keep


# ---------------------------------------------------------------- проверка моделью
def verify(anc_by_id, cands, quiet=False):
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        print("⚠️ нет DEEPSEEK_API_KEY — оставляю только вектор, с пометкой")
        return {k: [{"id": c["w"]["id"], "date": c["w"]["date"], "folder": c["w"]["folder"],
                     "title": c["w"]["title"], "score": c["score"], "why": "", "kind": "unverified"}
                    for c in v[:KEEP]] for k, v in cands.items()}
    from openai import OpenAI
    # Ожидание жёсткое и повторов ровно два: без этого обрыв связи вешал прогон навсегда
    # (06.09: двадцать минут на 60-м якоре из 108).
    client = OpenAI(api_key=key, base_url="https://api.deepseek.com", timeout=90, max_retries=2)
    out, spent = {}, {"in": 0, "out": 0}
    done = _verdicts_load()
    reused = 0
    items = list(cands.items())
    lock = threading.Lock()

    def one(n_aid_picks):
        """Один якорь: взять готовое или спросить модель. Возвращает строку журнала."""
        nonlocal reused
        n, (aid, picks) = n_aid_picks
        a = anc_by_id[aid]
        ck = _verdict_key(a, picks)
        got = done.get(ck)
        if got is not None:
            keep = _keep_from(got, picks)
            with lock:
                reused += 1
                if keep:
                    out[aid] = keep
            return f"  {n}/{len(items)} {aid}: из кэша, оставлено {len(keep)}"
        payload = {"statement": a["text"], "where_it_appears": a["kind"],
                   "papers": [{"id": c["w"]["id"], "title": c["w"]["title"], "abstract": c["w"]["text"][:1400]}
                              for c in picks]}
        try:
            r = client.chat.completions.create(
                model=MODEL, temperature=0.1, response_format={"type": "json_object"},
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])
            got = json.loads(r.choices[0].message.content)
        except Exception as e:                               # noqa: BLE001
            return f"  ⚠️ {aid}: модель не ответила ({str(e)[:90]}) — якорь без ссылок"
        keep = _keep_from(got, picks)
        with lock:
            _verdict_save(ck, got)                           # сразу на диск: обрыв не сжигает оплаченное
            if r.usage:
                spent["in"] += r.usage.prompt_tokens
                spent["out"] += r.usage.completion_tokens
            if keep:
                out[aid] = keep
        return f"  {n}/{len(items)} {aid}: из {len(picks)} оставлено {len(keep)}"

    # Четыре потока: запросы независимы, а по одному якорю за раз прогон занимал три часа.
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for line in pool.map(one, enumerate(items, 1)):
            if not quiet:
                print(line)
    print(f"проверка моделью: {spent['in']:,} + {spent['out']:,} токенов"
          + (f"; из кэша {reused} якорей" if reused else ""))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="только вектор, без модели и без записи")
    ap.add_argument("--limit", type=int, help="взять только первые N якорей (проба)")
    ap.add_argument("--all", action="store_true", help="пул — весь архив, не только работы темы")
    a = ap.parse_args()

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    anc = anchors()
    if a.limit:
        anc = anc[:a.limit]
    wks = works(all_archive=('--all' in sys.argv))
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

    import ops as OPSLOG
    run = OPSLOG.Run("links", note="all archive" if a.all else "theme works")
    anc_by_id = {x["id"]: x for x in anc}
    links = verify(anc_by_id, cands)
    deny = _deny_load()
    if deny:
        dropped = 0
        for aid, ids in deny.items():
            before = len(links.get(aid) or [])
            links[aid] = [l for l in (links.get(aid) or []) if l["id"] not in set(ids)]
            dropped += before - len(links[aid])
            if not links[aid]:
                links.pop(aid, None)
        print(f"снято по links-deny.json: {dropped}")
    payload = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "model": MODEL,
               "floor": FLOOR, "floor_weak": FLOOR_WEAK, "top": TOP, "keep": KEEP,
               "n_works": len(wks), "n_anchors": len(anc), "anchors": links,
               "note": "vector finds what is about the same thing; the model decides whether it belongs next to the "
                       "statement. A link means 'this is what the research says about this', not 'this is the source "
                       "of that number'."}
    OUT.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    run.finish("ok", anchors=len(links), of=len(anc), works=len(wks), links=sum(len(v) for v in links.values()))
    print(f"\n✅ {OUT.name}: ссылки у {len(links)} якорей из {len(anc)}; работ в пуле {len(wks)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
