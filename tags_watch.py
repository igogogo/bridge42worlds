"""Системный контроль тегов (решение владельца 2026-07-27: «следи за новыми тегами системно»).

Показывает, где словарь отстаёт от контента:
- какие статьи остались БЕЗ тегов или с одним тегом (значит, словарь их не покрыл);
- какие домены науки в архиве есть, а тегов под них нет (после балансированного наполнения
  появились cs/math/stat — а словарь пока физико-биологический);
- что модель просила добавить сама (data/gap-suggestions.jsonl — копится при генерации).

Запуск:
    python tags_watch.py                 # отчёт
    python tags_watch.py --grow 20       # отчёт + догенерация тегов под самые голодные домены
"""
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_LANG = "ru"
# домен тега → какие arXiv-группы он покрывает (для поиска «голодных» областей)
DOMAIN_BY_GROUP = {
    "cs": "computer_science", "math": "mathematics", "stat": "statistics",
    "q-bio": "biology", "q-fin": "economics_finance", "econ": "economics_finance",
    "eess": "engineering", "physics": "physics", "astro-ph": "astrophysics",
    "cond-mat": "chemistry_materials", "quant-ph": "quantum", "hep-th": "particles_nuclear",
    "hep-ph": "particles_nuclear", "hep-ex": "particles_nuclear", "nucl-th": "particles_nuclear",
    "nucl-ex": "particles_nuclear", "gr-qc": "relativity_gravity", "nlin": "mathematics",
}


def load_tags():
    p = Path(f"lang/{DEFAULT_LANG}/data/tags-list.json")
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def main():
    tags = load_tags()
    by_domain = Counter(t.get("domain", "?") for t in tags)
    print(f"словарь: {len(tags)} тегов в {len(by_domain)} доменах")

    # 1) статьи без тегов / с одним тегом — прямой признак, что словарь не покрыл тему
    thin, groups_thin = [], Counter()
    per_group = Counter()
    for p in Path(f"lang/{DEFAULT_LANG}/archive").glob("*/*/data.json"):
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        cats = j.get("categories") or []
        grp = (cats[0].split(".")[0] if cats else "?")
        per_group[grp] += 1
        n = len([t for t in (j.get("tags") or []) if t])
        if n <= 1:
            thin.append((p.parent.name, grp, n))
            groups_thin[grp] += 1

    print(f"\nстатей с 0-1 тегом: {len(thin)}")
    for g, n in groups_thin.most_common(8):
        share = n / max(per_group[g], 1)
        print(f"   {g:<12} {n:>4} из {per_group[g]:<5} ({share:.0%}) → домен «{DOMAIN_BY_GROUP.get(g, '?')}»")

    # 2) домены, где контент есть, а тегов нет
    hungry = []
    for grp, cnt in per_group.most_common():
        dom = DOMAIN_BY_GROUP.get(grp)
        if not dom:
            continue
        have = by_domain.get(dom, 0)
        if cnt >= 3 and have < max(5, cnt // 20):
            hungry.append((grp, dom, cnt, have))
    print("\nголодные домены (контент есть, тегов мало):")
    for grp, dom, cnt, have in hungry[:10]:
        print(f"   {grp:<12} статей {cnt:>4} · тегов в домене «{dom}»: {have}")

    # 3) что просила сама модель
    gp = Path("data/gap-suggestions.jsonl")
    asked = Counter()
    if gp.exists():
        for line in gp.read_text(encoding="utf-8").splitlines()[-4000:]:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            for t in (rec.get("suggested") or {}).get("missing_tags") or []:
                asked[str(t).strip().lower()] += 1
    if asked:
        print(f"\nмодель чаще всего просила добавить (топ-12 из {len(asked)}):")
        print("   " + ", ".join(f"{t}×{n}" for t, n in asked.most_common(12)))

    # 4) по требованию — сразу дорастить
    if "--grow" in sys.argv:
        n = int(sys.argv[sys.argv.index("--grow") + 1])
        focus = " ".join(dom.replace("_", " ") for _, dom, _, _ in hungry[:4]) or "computer science mathematics statistics"
        print(f"\nдоращиваю словарь: +{n} тегов с фокусом «{focus}»")
        subprocess.run([sys.executable, "run.py", "tags", "--gaps", str(n), "--focus", focus])


if __name__ == "__main__":
    main()
