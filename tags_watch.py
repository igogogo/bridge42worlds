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


def report_dead(active_tags):
    """Разбор «мёртвого» словаря. Дашборд считает по справочнику (tags.json, 363 карточки),
    а в статьи идёт только активный список (233) — образовательные теги в статьи не идут
    ПО УСТРОЙСТВУ и мёртвыми не являются. Разделяем эти три вещи, иначе цифра «180 мёртвых»
    зовёт чистить то, что работает как задумано."""
    active = {t["en"] for t in active_tags}
    domain_of = {t["en"]: t.get("domain", "") for t in active_tags}
    edu_path = Path(f"lang/{DEFAULT_LANG}/data/tags-list-educational.json")
    express_path = Path(f"lang/{DEFAULT_LANG}/data/tags-list-express.json")
    book_path = Path(f"lang/{DEFAULT_LANG}/data/tags.json")
    jload = lambda p: json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    edu = {t["en"] for t in jload(edu_path)}
    express = {t["en"] for t in jload(express_path)}
    book = jload(book_path)
    book_ids = set(book) if isinstance(book, dict) else {t.get("id") for t in book}

    used = Counter()
    express_articles = total = 0
    for p in Path(f"lang/{DEFAULT_LANG}/archive").glob("*/*/data.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        total += 1
        express_articles += 1 if data.get("express") else 0
        for level in ("simple", "popular", "advanced"):
            tier = (data.get(level) or {}).get(DEFAULT_LANG) or {}
            if tier.get("main_tag"):
                used[tier["main_tag"]] += 1
            for tag in tier.get("extra_tags") or []:
                used[tag] += 1

    dead_book = book_ids - used.keys()
    dead_active = sorted(active - used.keys())
    orphan = sorted(dead_book - active - edu)
    print(f"\nмёртвый словарь (статей {total}, из них экспресс {express_articles}):")
    print(f"   справочник tags.json:            {len(book_ids)}, не встречается {len(dead_book)}")
    print(f"   из них образовательные:          {len(dead_book & edu)}  — в статьи не идут по устройству")
    print(f"   из них активные, но не выбраны:  {len(dead_active)}  ← настоящие кандидаты на разбор")
    print(f"   осиротевшие (карточка есть, в списках нет): {len(orphan)}"
          + (f" — {', '.join(orphan)}" if orphan else ""))
    hidden = [t for t in dead_active if t not in express]
    print(f"   из мёртвых активных не входят в экспресс-словарь: {len(hidden)} — "
          f"их не видели {express_articles / max(1, total):.0%} статей архива")
    by_domain = Counter(domain_of.get(t, "") for t in dead_active)
    print("   по доменам: " + ", ".join(f"{d}×{n}" for d, n in by_domain.most_common(6)))
    for tag in dead_active:
        print(f"      {domain_of.get(tag, ''):<24} {tag}")


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

    # 3б) мёртвая часть словаря — по требованию (замер дашборда 2026-07-31: «180 из 363»)
    if "--dead" in sys.argv:
        report_dead(tags)

    # 4) по требованию — сразу дорастить
    if "--grow" in sys.argv:
        n = int(sys.argv[sys.argv.index("--grow") + 1])
        focus = " ".join(dom.replace("_", " ") for _, dom, _, _ in hungry[:4]) or "computer science mathematics statistics"
        print(f"\nдоращиваю словарь: +{n} тегов с фокусом «{focus}»")
        subprocess.run([sys.executable, "run.py", "tags", "--gaps", str(n), "--focus", focus])


if __name__ == "__main__":
    main()
