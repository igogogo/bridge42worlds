# -*- coding: utf-8 -*-
"""Выжимка волны 5 для просмотра: одна страница вместо шести файлов.

ЗАЧЕМ. ML закончила перестройку слоя понятий и положила предложение шестью файлами
в СОСЕДНЕМ дереве (b42-ml, ветка ml-wave5-concepts). Владелец 26 августа: «прежде чем
переводить понятия, я хотел бы посмотреть карточки, все их английские, надо как-то
разместить у нас». Читать шесть json руками — не смотреть, а разбирать.

Здесь они сводятся в один файл под страницу concepts-review.html.

ЧТО ВАЖНО ЗНАТЬ ПРО ИСХОДНИКИ — иначе картина выйдет неверной:

  · concepts-v3.json  содержит СТАРЫЕ списки учёных. У `entropy` там снова Эйнштейн,
    Аспе, Китаев — то самое, что волна и вычищала. Новые, обрезанные до 1304 привязок,
    лежат ОТДЕЛЬНО в concept-scientists.json. Применять v3 к боевому реестру, не заменив
    в нём учёных, значит вернуть разъезд, который только что убрали.

  · related внутри v3 — простой список без весов. Взвешенные 5 440 связей живут
    в concepts-super.json. Для просмотра берём взвешенные: без веса связь не читается.

  · super_names в concepts-super.json ПУСТ, хотя в отчёте имена процитированы
    («Quantum Information Science» и прочие). Значит шаг именования отработал,
    а в файл не попал. Пока подписываем группы по самым крупным членам и помечаем
    это как временную подпись, чтобы никто не принял её за решение ML.

ЗАПУСК:  python tools/wave5_review.py [--ml ПУТЬ]
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ML = ROOT.parent / "b42-ml"
OUT = ROOT / "data" / "wave5-review.json"

TOP_RELATED = 8      # столько соседей показываем в карточке
TOP_SCI = 6
TOP_FORMULAS = 4


def load(ml, name):
    p = ml / "data" / name
    if not p.exists():
        print(f"⚠️ нет {p}")
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def title_of(cid):
    """Человеческое имя из идентификатора. Названий у понятий в v3 нет — только id."""
    return cid.replace("_", " ")


def build(ml):
    v3 = load(ml, "concepts-v3.json")
    sup = load(ml, "concepts-super.json")
    sci = load(ml, "concept-scientists.json")
    fml = load(ml, "formulas-linked.json")
    retag = load(ml, "articles-retag.json")
    if not (v3 and sup):
        print("нечего собирать"); return 1

    concepts = v3["concepts"]
    groups = {int(k): v for k, v in sup["groups"].items()}
    membership = {k: v for k, v in sup["membership"].items()}
    links = sup["links"]
    sci_map = (sci or {}).get("concepts", {})
    bases = (fml or {}).get("bases", [])

    # ── взвешенные соседи: связь двусторонняя, а список — по каждому концу ──
    nb = defaultdict(list)
    for e in links:
        nb[e["a"]].append((e["b"], e["w"], e["n"]))
        nb[e["b"]].append((e["a"], e["w"], e["n"]))
    for k in nb:
        nb[k].sort(key=lambda t: -t[1])

    # ── формулы к понятию: берём ПЕРВУЮ (самую близкую) привязку каждой формы ──
    by_concept_formula = defaultdict(list)
    for b in bases:
        for i, c in enumerate(b.get("concepts") or []):
            by_concept_formula[c["concept"]].append({
                "id": b["base_id"], "name": b.get("name") or b["base_id"],
                "latex": b.get("latex", ""), "card": b.get("card", ""),
                "sim": c.get("sim", 0), "rank": i,
                "uses": len(b.get("applications") or []),
            })
    for k in by_concept_formula:
        by_concept_formula[k].sort(key=lambda f: (f["rank"], -f["sim"]))

    # ── сколько статей получило понятие по НОВОЙ разметке ──────────────────
    new_count = defaultdict(int)
    if retag:
        for arts in retag["articles"].values():
            for c in arts:
                cid = c["concept"] if isinstance(c, dict) else c
                new_count[cid] += 1

    out_concepts = {}
    for cid, v in concepts.items():
        old_sci = v.get("scientists") or []
        new_sci = sci_map.get(cid) or []
        out_concepts[cid] = {
            "t": title_of(cid),
            "card": v.get("card_en", ""),
            "kind": v.get("kind") or "",
            "domain": v.get("domain") or "",
            "origin": v.get("origin") or "",
            "n_old": v.get("article_count", 0),
            "n_new": new_count.get(cid, 0),
            "supers": membership.get(cid, []),
            "rel": [{"id": a, "w": round(w, 3), "n": n} for a, w, n in nb.get(cid, [])[:TOP_RELATED]],
            # СТАРЫХ учёных отдаём только числом: показывать их списком значило бы
            # предлагать читателю сравнивать со свалкой, которую мы и убираем.
            "sci_old": len(old_sci),
            "sci": [{"name": s["name"], "w": round(s.get("weight", 0), 2),
                     "n": s.get("articles", 0)} for s in new_sci[:TOP_SCI]],
            "formulas": by_concept_formula.get(cid, [])[:TOP_FORMULAS],
        }

    # ── группы: подпись временная, по самым крупным членам ─────────────────
    out_groups = {}
    for gid, members in groups.items():
        big = sorted(members, key=lambda c: -out_concepts.get(c, {}).get("n_new", 0))[:3]
        out_groups[str(gid)] = {
            "n": len(members),
            "members": members,
            # Подпись НАША, не от ML: её super_names пуст. Помечено в UI.
            "label": " · ".join(title_of(b) for b in big),
        }

    payload = {
        "built": (sup.get("built") or "")[:10],
        "source": "b42-ml / ml-wave5-concepts",
        "concepts": out_concepts,
        "groups": out_groups,
        "names_from_ml": bool(sup.get("super_names")),
        "stats": {
            "concepts": len(out_concepts),
            "was": 536,
            "groups": len(out_groups),
            "links": len(links),
            "density": (retag or {}).get("density"),
            "density_before": (retag or {}).get("density_before"),
            "articles": len((retag or {}).get("articles") or {}),
            "empty_articles": sum(1 for a in ((retag or {}).get("articles") or {}).values() if not a),
            "sci_pairs_before": (sci or {}).get("pairs_before"),
            "sci_pairs_after": (sci or {}).get("pairs_after"),
            "formula_bases": len(bases),
            "formula_uses": sum(len(b.get("applications") or []) for b in bases),
        },
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    kb = OUT.stat().st_size / 1024
    s = payload["stats"]
    print(f"✅ {OUT.relative_to(ROOT)} — {kb:.0f} КБ")
    print(f"   понятий {s['concepts']} (было {s['was']}) · групп {s['groups']} · связей {s['links']}")
    print(f"   разметка {s['density_before']} → {s['density']} на статью, "
          f"статей {s['articles']}, без понятий {s['empty_articles']}")
    print(f"   учёные {s['sci_pairs_before']} → {s['sci_pairs_after']} · "
          f"формул {s['formula_bases']}, применений {s['formula_uses']}")
    if not payload["names_from_ml"]:
        print("   ⚠️ имена суперпонятий в файле ML пусты — подписи временные, по крупным членам")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Выжимка волны 5 под страницу просмотра")
    ap.add_argument("--ml", default=str(DEFAULT_ML), help="путь к дереву b42-ml")
    a = ap.parse_args()
    return build(Path(a.ml))


if __name__ == "__main__":
    sys.exit(main())
