# -*- coding: utf-8 -*-
"""Досвязывание ядра: связи, которых нет ни в статьях, ни в векторе.

Владелец 28.08: «рёбра графа строятся только по общим статьям — а я думал, статьи
лишь один источник. Как ты установишь связь между законом и константой или между
понятиями? Тут надо потом пройтись тебе уже самому и добрать связи, досвязать
лично — это работа твоя как интеллекта, а не только что есть в статьях. Понятно,
что это разово, но пусть будем разово этим раз в неделю заниматься: это важная
штука — ставить внутреннюю связанность ядра».

ТРИ ИСТОЧНИКА СВЯЗИ, и они разные по природе:

  статьи   — два понятия названы в одних и тех же работах. Честно, но слепо к
             тому, чего в корпусе мало: у «чёрной дыры» и «слияния чёрных дыр»
             ноль общих статей, хотя связь очевидна.
  вектор   — их определения близки. Ловит синонимию и соседство по теме, но не
             отличает «часть целого» от «просто похоже».
  ЗНАНИЕ   — этот файл. Закон Стефана — Больцмана и постоянная Стефана —
             Больцмана связаны не потому, что встретились в одной статье, а
             потому, что одна входит в другой. Такую связь не выведешь из
             статистики: её надо знать.

Как считаем. Кандидатов не выдумываем — берём тех, кто уже рядом: соседи по
вектору, соседи по группе, понятия одной формулы. Пары, где ребро уже есть,
отбрасываем. Оставшееся показываем модели вместе с определениями и спрашиваем не
«похожи ли», а КАК одно относится к другому: входит в состав, частный случай,
измеряется этим, следует из этого. Ответ «связи нет» — полноправный и частый.

Тип связи важнее веса: он делает граф читаемым — видно, что константа входит в
закон, а не просто «стоит рядом».

    python tools/link_weaving.py --kinds law,constant --limit 40   проба, показать
    python tools/link_weaving.py --kinds law,constant --limit 40 --apply
    python tools/link_weaving.py --all --apply                     недельный проход
"""
import argparse
import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.concept_harvest import env  # noqa: E402

LIVE = ROOT / "data" / "concepts-live.json"
GRAPH = ROOT / "data" / "concepts-graph.json"
OUT = ROOT / "data" / "concept-links-knowledge.json"
STATE = ROOT / "data" / "link-weaving-state.json"

PER_CALL = 5          # понятий в запросе: у каждого до 8 кандидатов — уже много текста
WORKERS = 5
CAND = 8

# Типы связи. Список закрыт намеренно: свободная формулировка превращает граф в
# свалку синонимов («связано», «относится», «имеет отношение»).
REL = {
    "part_of":   {"ru": "входит в", "en": "part of"},
    "case_of":   {"ru": "частный случай", "en": "special case of"},
    "follows":   {"ru": "следует из", "en": "follows from"},
    "measures":  {"ru": "измеряет", "en": "measures"},
    "describes": {"ru": "описывает", "en": "describes"},
    "opposite":  {"ru": "противоположно", "en": "opposite to"},
    "same_area": {"ru": "одна область", "en": "same area"},
}

SYS = """You link physics concepts in a knowledge graph.

For each numbered concept you get its definition and a list of candidate
neighbours with their definitions. For every candidate decide how the concept
relates to it — or that it does not.

Allowed relations (use the key exactly):
  part_of    — one is a component of the other (a constant inside a law)
  case_of    — one is a special case of the other
  follows    — one is derived from or implied by the other
  measures   — one is the instrument or method that measures the other
  describes  — one is the theory/law that describes the other phenomenon
  opposite   — they are opposing or complementary notions
  same_area  — same narrow subject, no stronger relation
  none       — no real relation; being about physics is NOT a relation

DIRECTION MATTERS. The relation reads "CONCEPT <rel> CANDIDATE":
  right: "Stefan-Boltzmann constant" part_of "Stefan-Boltzmann law"
  WRONG: "Hubble law" part_of "velocity" — velocity enters the law, not the
         reverse. If the direction is the other way round, answer none.
Never use part_of towards a basic quantity (speed, distance, mass, time,
energy): a law is not "part of" the quantity it relates.

Be strict. "none" is the correct answer most of the time. Do not link two
concepts merely because they appear in similar contexts or share a word.
Prefer no link over a vague one: same_area is for a NARROW shared subject, not
for "both are physics" or "both are quantum".
Strength: 3 = textbook-level, unavoidable link; 2 = clear; 1 = defensible.

Return JSON array, one object per concept, same order:
[{"n": 1, "links": [{"to": "<candidate id>", "rel": "part_of", "w": 3}]}]
Only real links; omit the rest. Nothing else."""


def load():
    live = json.loads(LIVE.read_text(encoding="utf-8"))["concepts"]
    have = set()
    if GRAPH.exists():
        g = json.loads(GRAPH.read_text(encoding="utf-8"))
        ids = [n["id"] for n in g["nodes"]]
        # Ребро подросло: с 28.08 четвёртым элементом идёт источник связи (статьи,
        # вектор, знание), и жёсткая тройка здесь роняла весь шаг. Берём первые три
        # позиции и не загадываем, сколько их будет завтра — этому шагу нужны только
        # концы ребра, чтобы не спрашивать модель про уже известную связь.
        for e in g["edges"]:
            a, b = e[0], e[1]
            if a < len(ids) and b < len(ids):
                have.add((min(ids[a], ids[b]), max(ids[a], ids[b])))
    return live, have


def candidates(cid, live, have, groups):
    """Кого спросить про это понятие: соседи по вектору, по группе, по формуле."""
    v = live[cid]
    seen, out = {cid}, []

    def add(other):
        if other in seen or other not in live:
            return
        if (min(cid, other), max(cid, other)) in have:
            return                      # связь уже есть — спрашивать нечего
        seen.add(other)
        out.append(other)

    for r in (v.get("related") or [])[:10]:
        add(r["id"])
    for f in (v.get("formulas") or [])[:4]:
        for other, fl in groups["by_formula"].get(f["id"], []):
            if other != cid:
                add(other)
    for gid in (v.get("supers") or [])[:1]:
        for other in groups["by_group"].get(str(gid), [])[:14]:
            add(other)
    return out[:CAND]


def ask(batch, key):
    lines = []
    for i, (cid, card, cands) in enumerate(batch, 1):
        lines.append(f'{i}. concept "{cid}": {card[:200]}')
        for oid, ocard in cands:
            lines.append(f'   - "{oid}": {ocard[:150]}')
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": SYS},
                     {"role": "user", "content": "\n".join(lines)}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        raw = json.loads(r.read().decode("utf-8"))["choices"][0]["message"]["content"]
    got = json.loads(raw)
    if isinstance(got, dict):
        for v in got.values():
            if isinstance(v, list):
                got = v
                break
    out = {}
    for it in (got if isinstance(got, list) else []):
        try:
            n = int(it["n"])
            if not (1 <= n <= len(batch)):
                continue
            cid = batch[n - 1][0]
            ok = []
            for lk in (it.get("links") or []):
                rel = str(lk.get("rel", "")).strip()
                to = str(lk.get("to", "")).strip()
                if rel not in REL or not to:
                    continue
                w = lk.get("w")
                w = int(w) if isinstance(w, (int, float)) and 1 <= w <= 3 else 2
                ok.append({"to": to, "rel": rel, "w": w})
            if ok:
                out[cid] = ok
        except (KeyError, ValueError, TypeError):
            continue
    return out


def main():
    ap = argparse.ArgumentParser(description="Досвязывание ядра графа знаний")
    ap.add_argument("--kinds", default="law,constant,equation,principle,theorem",
                    help="классы понятий, с которых начинаем")
    ap.add_argument("--all", action="store_true", help="все классы подряд")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    live, have = load()
    by_group, by_formula = {}, {}
    for cid, v in live.items():
        for gid in (v.get("supers") or [])[:1]:
            by_group.setdefault(str(gid), []).append(cid)
        for f in (v.get("formulas") or [])[:6]:
            by_formula.setdefault(f["id"], []).append((cid, f["id"]))
    groups = {"by_group": by_group, "by_formula": by_formula}

    done = {}
    if OUT.exists():
        try:
            done = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            done = {}
    state = {"done": []}
    if STATE.exists():
        try:
            state = json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    seen = set(state.get("done") or [])

    kinds = None if a.all else {k.strip() for k in a.kinds.split(",") if k.strip()}
    # Ядро вперёд: у закона и константы связь по знанию нужнее всего — их редко
    # называют вместе в статьях, а связаны они неразрывно.
    pool = [cid for cid, v in live.items()
            if (kinds is None or v.get("kind") in kinds) and cid not in seen]
    pool.sort(key=lambda c: -len(live[c].get("articles") or []))
    pool = pool[:a.limit]
    if not pool:
        print("новых понятий для обхода нет")
        return 0

    batch_in = []
    for cid in pool:
        cands = candidates(cid, live, have, groups)
        if not cands:
            continue
        batch_in.append((cid, live[cid].get("card_en") or "",
                         [(o, live[o].get("card_en") or "") for o in cands]))
    print(f"понятий к обходу: {len(batch_in)} · запросов: "
          f"{(len(batch_in) + PER_CALL - 1) // PER_CALL}")
    if not batch_in:
        return 0

    key = env("DEEPSEEK_API_KEY")
    bs = [batch_in[i:i + PER_CALL] for i in range(0, len(batch_in), PER_CALL)]
    got_all = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for got in ex.map(lambda b: ask(b, key), bs):
            got_all.update(got or {})

    n_links = sum(len(v) for v in got_all.values())
    print(f"найдено связей: {n_links} у {len(got_all)} понятий\n")
    for cid, links in list(got_all.items())[:14]:
        nm = (live[cid].get("names") or {}).get("ru") or cid
        for lk in links:
            onm = (live.get(lk["to"], {}).get("names") or {}).get("ru") or lk["to"]
            print(f"  {nm} — {REL[lk['rel']]['ru']} → {onm}  (сила {lk['w']})")
    if not a.apply:
        print("\nпроба. записать: --apply")
        return 0

    for cid, links in got_all.items():
        cur = {(l["to"], l["rel"]): l for l in done.get(cid, [])}
        for l in links:
            cur[(l["to"], l["rel"])] = l
        done[cid] = list(cur.values())
    OUT.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
    seen |= set(pool)
    STATE.write_text(json.dumps({"done": sorted(seen)}, ensure_ascii=False),
                     encoding="utf-8")
    print(f"\n→ {OUT.name}: связей у {len(done)} понятий · обойдено всего {len(seen)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
