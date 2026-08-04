"""Слой формул: собрать, привести к канону, связать со статьями и величинами.

Владелец 2026-08-04: «создать облако формул, связать граф формул — это красиво. Приводить
к канону — работаем как с тегами: строим иерархии, графы, облака. Отдельно константы,
системы единиц. Туда отлично ляжет математика: формулы, теоремы, обозначения — связь наук,
их единство. Развивай в этом направлении».

Почему формула — лучший узел графа, чем тег. Тег можно поставить наугад, закон притянуть
по касательной, а формула либо есть в работе, либо её нет. И одна формула связывает работы,
которые словами не пересекаются: уравнение диффузии стоит и в переносе тепла, и в
распространении эпидемии, и в ценообразовании опционов. Такую связь текстовый вектор не
найдёт никогда — тексты разные, математика одна. Это и есть единство науки, показанное
не лозунгом, а структурой.

Замер до начала работы (2026-08-04): 1247 формул в 692 статьях из 2124 (32%), из них
1225 разных записей. Грубое приведение к канону свернуло их всего до 1217 — то есть
**формулы почти всегда записаны по-разному**, и текстовая нормализация бессильна.
Настоящие повторы при этом есть: закон Хаббла встречается 10 раз, светимость чёрного
тела 5, радиус Шварцшильда 4. Значит канон нужен смысловой, а не буквенный — та же
развилка, что с тегами.

    python tools/formula_layer.py --build        собрать data/formulas.json
    python tools/formula_layer.py --stats        что получилось, без записи
    python tools/formula_layer.py --dupes        показать кандидатов на склейку

Здесь делается ЧЕСТНАЯ часть: сбор, разбор структуры, буквенный канон и связи со статьями.
Смысловая склейка (одна формула в разных записях) — за вектором, задача ML.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "formulas.json"
TIERS = ("advanced", "popular", "simple")

# Синонимы записи: разные способы написать одно и то же. Это НЕ смысловая склейка, а
# приведение орфографии латеха — то, что можно сделать честно и без модели.
SYN = [
    (r"\\left|\\right", ""),                     # \left( ... \right) → ( ... )
    (r"\\,|\\;|\\!|\\ ", ""),                    # тонкие пробелы
    (r"\\dfrac|\\tfrac", r"\\frac"),             # варианты дроби
    (r"\\cdot|\\times", "*"),                    # умножение
    (r"\\mathrm|\\text|\\mathbf|\\bm", ""),      # начертание смысла не меняет
    (r"\s+", ""),
]
GREEK = {r"\\alpha": "α", r"\\beta": "β", r"\\gamma": "γ", r"\\delta": "δ", r"\\Delta": "Δ",
         r"\\epsilon": "ε", r"\\lambda": "λ", r"\\mu": "μ", r"\\nu": "ν", r"\\pi": "π",
         r"\\rho": "ρ", r"\\sigma": "σ", r"\\tau": "τ", r"\\phi": "φ", r"\\omega": "ω",
         r"\\Omega": "Ω", r"\\hbar": "ħ", r"\\theta": "θ", r"\\chi": "χ", r"\\psi": "ψ"}


def canon(tex):
    """Буквенный канон: то, что можно свести честно, не догадываясь о смысле."""
    s = tex or ""
    for pat, rep in GREEK.items():
        s = re.sub(pat, rep, s)
    for pat, rep in SYN:
        s = re.sub(pat, rep, s)
    return s.strip().rstrip(".").lower()


def symbols(tex):
    """Обозначения, встречающиеся в формуле: по ним строятся связи формула↔формула.
    Две формулы, делящие символ (E, c, G, ħ), почти наверняка про одно поле явлений."""
    s = re.sub(r"\\[a-zA-Z]+", " ", tex or "")
    return sorted(set(re.findall(r"[A-Za-zΑ-Ωα-ωħ]", s)))


def collect():
    items = []
    for p in sorted((ROOT / "lang/ru/archive").glob("*/*/data.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for tier in TIERS:
            v = (d.get(tier, {}) or {}).get("ru")
            if not isinstance(v, dict) or not v.get("formulas"):
                continue
            for f in v["formulas"]:
                if not isinstance(f, dict) or not f.get("latex"):
                    continue
                items.append({
                    "latex": f["latex"].strip(),
                    "meaning": (f.get("meaning") or f.get("description") or "").strip(),
                    "article": p.parent.name,
                    "date": d.get("date", ""),
                    "title": v.get("title", ""),
                    "tags": ([v.get("main_tag")] if v.get("main_tag") else []) + (v.get("extra_tags") or []),
                })
            break
    return items


def build(items):
    """Группируем по каноническому виду. Узел графа — не отдельная запись, а формула
    как сущность: у неё много вхождений в разные статьи, и именно это делает её мостом."""
    by = defaultdict(lambda: {"latex": "", "meanings": [], "articles": [], "tags": set(),
                              "symbols": []})
    for it in items:
        k = canon(it["latex"])
        g = by[k]
        # Показываем самую полную запись: она обычно и самая понятная.
        if len(it["latex"]) > len(g["latex"]):
            g["latex"] = it["latex"]
            g["symbols"] = symbols(it["latex"])
        if it["meaning"] and it["meaning"] not in g["meanings"]:
            g["meanings"].append(it["meaning"])
        g["articles"].append({"id": it["article"], "date": it["date"], "title": it["title"]})
        g["tags"].update(t for t in it["tags"] if t)
    out = {}
    for k, g in by.items():
        out[k] = {"latex": g["latex"], "meaning": g["meanings"][0] if g["meanings"] else "",
                  "meanings": g["meanings"][:3], "symbols": g["symbols"],
                  "tags": sorted(g["tags"])[:8], "articles": g["articles"],
                  "n": len(g["articles"])}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--dupes", action="store_true")
    args = ap.parse_args()

    items = collect()
    formulas = build(items)
    multi = {k: v for k, v in formulas.items() if v["n"] > 1}
    print(f"вхождений {len(items)} · формул после канона {len(formulas)} · "
          f"встречаются больше раза {len(multi)}")

    if args.dupes or args.stats:
        print("\nформулы-мосты (встречаются в разных статьях):")
        for k, v in sorted(multi.items(), key=lambda x: -x[1]["n"])[:12]:
            print(f"  {v['n']}× {v['latex'][:52]}")
            print(f"      {v['meaning'][:70]}")

    # связи по общим обозначениям — заготовка графа
    bysym = defaultdict(list)
    for k, v in formulas.items():
        for s in v["symbols"]:
            bysym[s].append(k)
    pairs = sum(len(v) * (len(v) - 1) // 2 for v in bysym.values() if len(v) < 60)
    print(f"\nобозначений в ходу: {len(bysym)} · возможных связей по общим символам: {pairs}")

    if args.build:
        OUT.write_text(json.dumps(formulas, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nзаписано: {OUT} ({OUT.stat().st_size // 1024} КБ)")
    else:
        print("\nчерновой прогон — ничего не записано; --build запишет слой")
    return 0


if __name__ == "__main__":
    sys.exit(main())
