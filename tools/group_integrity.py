# -*- coding: utf-8 -*-
"""Перекрёстная внутригрупповая проверка: целостность знания ИЗНУТРИ групп.

Владелец 27.08: «сироты — ты, может, трёшь то, что нужно группам: внутри всё
должно быть целостно, займись; перекрёстная внутригрупповая проверка — и объём
вырастет процентов на 20, и математика появится, и методы».

Опора от статей — одна сторона правды. Вторая: каждая область (группа) обязана
нести свой скелет — законы, математику, статистику, методы. Если в «Оптике» нет
ни одного закона, это дыра, видимая только изнутри группы. И сирота по статьям
может быть несущим узлом области — его держит структура, а не разметка.

ТРИ КОМАНДЫ:

  --audit   по каждой из 50 групп: состав классов, дыры скелета (нет law/math/
            statistics), внутренняя связность, СТРУКТУРНЫЕ сироты (без статей,
            но с ≥2 векторными соседями в своей группе — их не трогать).
            → data/group-integrity.json, секция в аудите.

  --grow    дорост изнутри (ПЛАТНО, ~50 запросов DeepSeek): модель видит область
            (имя + опорные члены + её скелет) и называет НЕДОСТАЮЩИЕ ключевые
            законы/математику/статистику/методы. Кандидаты — в общую копилку
            с пометкой src=group. Ноль — валидный ответ.

  --support вектор-добор опоры: кандидатам без 5 статей ищем статьи ПОЛЕМ
            (наши 6678, cos ≥ 0.58 к карточке) — разметка их не выделила,
            а смысловая близость есть. Опора честная: дальше кандидат идёт
            через ОБЫЧНОЕ сито рождений (вектор + Scholar + ≥5 статей).

Перекрёстность: группа предлагает → вектор поля подтверждает → Scholar
проверяет реальность → рождение. Три стороны сверяют друг друга.
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT.parent / "b42-ml"
sys.path.insert(0, str(ROOT))
from tools import concept_harvest as CH  # noqa: E402

OUT = ROOT / "data" / "group-integrity.json"
GROW_STATE = ROOT / "data" / "group-grow-state.json"
SKELETON = ("law", "math", "statistics", "method", "constant")
FIELD_T = 0.58        # консервативная близость статьи к карточке для добора опоры


def load_live():
    doc = json.loads((ROOT / "data/concepts-live.json").read_text(encoding="utf-8"))
    return doc["concepts"], {int(k): v for k, v in doc["groups"].items()}


def load_cards():
    import numpy as np
    ids = (ML / "data/concept-cards.ids").read_text(encoding="utf-8").split()
    V = np.fromfile(ML / "data/concept-cards.f16", dtype=np.float16) \
        .reshape(len(ids), -1).astype(np.float32)
    V /= np.linalg.norm(V, axis=1, keepdims=True) + 1e-9
    return np, ids, V


def group_label(members, C, lang="en"):
    top = sorted(members, key=lambda m: -len(C.get(m, {}).get("articles", [])))[:3]
    return " · ".join((C[m].get("names") or {}).get(lang) or m for m in top if m in C)


def audit():
    np, ids, V = load_cards()
    C, groups = load_live()
    idx = {c: i for i, c in enumerate(ids)}
    report = {}
    struct_orphans_all = []
    for gid, members in groups.items():
        members = [m for m in members if m in C]
        kinds = Counter(C[m].get("kind", "?") for m in members)
        holes = [k for k in SKELETON if not kinds.get(k)]
        # внутренняя связность: у скольких членов есть сосед-одногруппник
        mset = set(members)
        connected = 0
        for m in members:
            if any(r["id"] in mset for r in (C[m].get("related") or [])):
                connected += 1
        # структурные сироты: без статей, но с ≥2 векторными соседями в группе
        struct = []
        rows = [idx[m] for m in members if m in idx]
        if rows:
            Vg = V[rows]
            for m in members:
                if C[m].get("articles") or m not in idx:
                    continue
                sims = Vg @ V[idx[m]]
                near = int((sims >= 0.60).sum()) - 1     # минус он сам
                if near >= 2:
                    struct.append(m)
        struct_orphans_all += struct
        report[str(gid)] = {
            "label": group_label(members, C),
            "n": len(members),
            "kinds": dict(kinds),
            "skeleton_holes": holes,
            "connected_share": round(connected / max(1, len(members)), 2),
            "structural_orphans": struct,
        }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    holes_n = sum(1 for g in report.values() if g["skeleton_holes"])
    print(f"✅ аудит групп → {OUT.name}")
    print(f"   групп с дырами скелета: {holes_n}/50")
    worst = sorted(report.values(), key=lambda g: -len(g["skeleton_holes"]))[:6]
    for g in worst:
        print(f"   {g['label'][:44]:46s} дыры: {', '.join(g['skeleton_holes']) or '—'}")
    print(f"   структурных сирот (держат группы, не трогать): {len(set(struct_orphans_all))}")
    return 0


GROW_SYS = """You are completing the skeleton of ONE physics area for a knowledge base.

You are given the area (its top concepts) and what it ALREADY HAS by kind.
Name the MISSING key entries a physicist would expect this area to contain:
- law: named laws/theorems/equations of THIS area
- math: named mathematical structures/methods this area lives on
- statistics: statistical methods typically used in this area's papers
- method: core experimental/computational methods of the area
- constant: physical constants central to the area

Rules:
- ONLY well-established, widely recognised entries. Nothing invented, nothing
  paper-specific, nothing already in the HAVE lists (including synonyms of them).
- name: canonical English snake_case identifier.
- line: ONE dictionary-style sentence (max 25 words).
- 0 to 12 items TOTAL. Zero is a valid answer for a well-covered area.
Answer with a JSON array only:
[{"name": "...", "kind": "law|math|statistics|method|constant", "line": "..."}]"""


def grow():
    try:
        from tools.freeze import guard
        guard("дорост изнутри групп (DeepSeek)")
    except ImportError:
        pass
    key = CH.env("DEEPSEEK_API_KEY")
    C, groups = load_live()
    done = set()
    if GROW_STATE.exists():
        done = set(json.loads(GROW_STATE.read_text(encoding="utf-8"))["done"])
    rows = CH.load_harvest()
    n_new = 0
    for gid, members in sorted(groups.items()):
        if str(gid) in done:
            continue
        members = [m for m in members if m in C]
        top = sorted(members, key=lambda m: -len(C[m].get("articles", [])))[:15]
        have = defaultdict(list)
        for m in members:
            k = C[m].get("kind")
            if k in SKELETON:
                have[k].append(m)
        payload = (f"AREA: {group_label(members, C)}\n"
                   f"TOP CONCEPTS: {', '.join(top)}\n"
                   + "\n".join(f"HAVE {k}: {', '.join(sorted(have[k])[:25]) or '(none)'}"
                               for k in SKELETON))
        body = json.dumps({
            "model": "deepseek-chat",
            "messages": [{"role": "system", "content": GROW_SYS},
                         {"role": "user", "content": payload}],
            "temperature": 0.2, "max_tokens": 900,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.deepseek.com/chat/completions", data=body,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read().decode("utf-8"))
            raw = d["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  группа {gid}: сбой {e} — дальше")
            time.sleep(5)
            continue
        cands = CH.parse_answer(raw)
        cands = [c for c in cands if c.get("kind") in SKELETON]
        added = 0
        for c in cands:
            name = c["name"]
            if name in C or name in rows:
                continue
            rows[name] = {"name": name, "kind": c["kind"],
                          "group": group_label(members, C)[:80],
                          "scope": "general", "line": c["line"],
                          "articles": [], "matched": None, "src": "group"}
            added += 1
            n_new += 1
        done.add(str(gid))
        GROW_STATE.write_text(json.dumps({"done": sorted(done)}), encoding="utf-8")
        print(f"  группа {gid:>2} ({group_label(members, C)[:38]}): +{added}")
    CH.save_harvest(rows)
    print(f"✅ дорост изнутри: +{n_new} кандидатов от групп")
    return 0


def support():
    """Вектор-добор опоры: статьи поля, близкие к карточке кандидата."""
    import numpy as np
    sys.path.insert(0, str(ML))
    import concepts_grow as g
    art = g.load_corpus("ru")
    rowof, M = g.field_rows()
    have = [a for a in art if a in rowof]
    X = np.empty((len(have), M.shape[1]), dtype=np.float32)
    for i, a in enumerate(have):
        X[i] = M[rowof[a]]
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9

    rows = CH.load_harvest()
    # кандидаты без достаточной опоры, несовпавшие, с векторами из --match
    todo = [r for r in rows.values()
            if not r.get("matched") and not r.get("born")
            and len(r.get("articles") or []) < CH.ARTICLES_MIN and r.get("vec")]
    print(f"кандидатов на полевой добор опоры: {len(todo)}")
    boosted = 0
    for r in todo:
        v = np.asarray(r["vec"], dtype=np.float32)
        v /= np.linalg.norm(v) + 1e-9
        sims = X @ v
        hits = np.argsort(-sims)[:30]
        arts = [have[i] for i in hits if sims[i] >= FIELD_T]
        if not arts:
            continue
        merged = sorted(set(r.get("articles") or []) | set(arts))
        if len(merged) > len(r.get("articles") or []):
            r["articles"] = merged
            boosted += 1
    CH.save_harvest(rows)
    ready = [r for r in rows.values()
             if not r.get("matched") and not r.get("born")
             and len(r.get("articles") or []) >= CH.ARTICLES_MIN]
    print(f"✅ опора добрана у {boosted}; готовых к рождению теперь {len(ready)}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Внутригрупповая целостность")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--grow", action="store_true")
    ap.add_argument("--support", action="store_true")
    a = ap.parse_args()
    if a.audit:
        return audit()
    if a.grow:
        return grow()
    if a.support:
        return support()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
