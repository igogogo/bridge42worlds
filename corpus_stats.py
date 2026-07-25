"""Статистика покрытия для дашборда (юзер 2026-07-25): сколько ВСЕГО статей в архиве (Kaggle-дамп)
за 2025-2026 vs сколько мы обработали, разбивка по разделам и ЛИЦЕНЗИЯМ (сколько можем взять),
плюс признаки из дампа (опубликовано в журнале, число версий, размер коллабораций).

Разовый скан дампа (~5.4ГБ) → data/corpus-stats.json. Дашборд (js/dashboard.js) читает и рисует.
Запуск: python corpus_stats.py   (несколько минут; фильтр по префиксу id 25xx/26xx — быстро пропускаем чужое)
"""
import json
from pathlib import Path
from collections import defaultdict

DUMP = Path(r"C:/Users/nadez/Downloads/arxiv-metadata-oai-snapshot.json")
OUT = Path("data/corpus-stats.json")
YEARS = ("25", "26")  # arXiv id YYMM.xxxxx → 2025-2026
ALLOWED = ("by/4.0", "by-sa/4.0", "zero/1.0", "nonexclusive-distrib/1.0")


def lic_key(lic):
    if not lic:
        return "нет/неизвестно"
    l = lic.lower()
    if "by-nc-sa" in l: return "CC BY-NC-SA"
    if "by-nc-nd" in l: return "CC BY-NC-ND"
    if "by-nc" in l: return "CC BY-NC"
    if "by-sa" in l: return "CC BY-SA"
    if "by-nd" in l: return "CC BY-ND"
    if "/by/" in l or l.endswith("/by/4.0/") or "licenses/by/" in l: return "CC BY"
    if "zero" in l or "publicdomain" in l: return "CC0 / public domain"
    if "nonexclusive-distrib" in l: return "arXiv non-exclusive"
    return "другая"


def is_allowed(lic):
    return bool(lic) and any(a in lic for a in ALLOWED)


def section_group(cats_field):
    # в Kaggle-дампе categories — СТРОКА через пробел ("astro-ph.CO hep-th"); берём ПЕРВУЮ ПОЛНУЮ
    # категорию (не верхний уровень) — дашборд резолвит её в локализованное имя через наш справочник
    # arxiv-categories-{lang}.json (юзер 2026-07-25: «используй наши названия разделов, все языки»).
    if not cats_field:
        return "?"
    parts = str(cats_field).split()
    return parts[0] if parts else "?"


def scan_dump():
    by_month = defaultdict(lambda: {"total": 0, "allowed": 0, "published": 0, "auth": 0, "vers": 0})
    by_section = defaultdict(lambda: {"total": 0, "allowed": 0})
    licenses = defaultdict(int)
    n = 0
    with DUMP.open(encoding="utf-8") as f:
        for line in f:
            # дешёвый пре-фильтр: id — первое поле, год в первых ~20 символах
            head = line[:22]
            if '"25' not in head and '"26' not in head:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            aid = d.get("id", "")
            yy, mm = aid[:2], aid[2:4]
            if yy not in YEARS or not mm.isdigit() or not (1 <= int(mm) <= 12):
                continue
            ym = f"20{yy}-{mm}"
            lic = d.get("license")
            allowed = is_allowed(lic)
            m = by_month[ym]
            m["total"] += 1
            if allowed: m["allowed"] += 1
            if d.get("journal-ref") or d.get("doi"): m["published"] += 1
            m["auth"] += len(d.get("authors_parsed") or [])
            m["vers"] += len(d.get("versions") or [])
            sec = by_section[section_group(d.get("categories"))]
            sec["total"] += 1
            if allowed: sec["allowed"] += 1
            licenses[lic_key(lic)] += 1
            n += 1
            if n % 20000 == 0:
                print(f"  … {n} статей 2025-2026 учтено", flush=True)
    return by_month, by_section, licenses, n


def generated_counts():
    idx = json.loads(Path("lang/ru/articles-index.json").read_text(encoding="utf-8"))
    seen, gm = set(), defaultdict(lambda: {"gen": 0, "express": 0, "full": 0})
    total = {"gen": 0, "express": 0, "full": 0}
    for a in idx:
        if a["id"] in seen:
            continue
        seen.add(a["id"])
        date = str(a.get("date", ""))
        if not (date.startswith("2025") or date.startswith("2026")):
            continue
        ym = date[:7]
        exp = bool(a.get("express"))
        gm[ym]["gen"] += 1; total["gen"] += 1
        k = "express" if exp else "full"
        gm[ym][k] += 1; total[k] += 1
    return gm, total


def main():
    print("скан Kaggle-дампа за 2025-2026 (лицензии + признаки)…", flush=True)
    by_month, by_section, licenses, n = scan_dump()
    gm, gtot = generated_counts()
    months = sorted(set(by_month) | set(gm))
    out = {
        "range": "2025-2026",
        "dump_total": n,
        "generated_total": gtot,
        "months": [{
            "ym": ym,
            "dump": by_month[ym]["total"],
            "allowed": by_month[ym]["allowed"],
            "generated": gm[ym]["gen"], "express": gm[ym]["express"], "full": gm[ym]["full"],
            "published": by_month[ym]["published"],
            "avg_authors": round(by_month[ym]["auth"] / by_month[ym]["total"], 1) if by_month[ym]["total"] else 0,
            "avg_versions": round(by_month[ym]["vers"] / by_month[ym]["total"], 2) if by_month[ym]["total"] else 0,
        } for ym in months],
        "sections": sorted(([s, v["total"], v["allowed"]] for s, v in by_section.items()), key=lambda x: -x[1]),
        "licenses": sorted(licenses.items(), key=lambda x: -x[1]),
        "allowed_total": sum(m["allowed"] for m in by_month.values()),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"✅ corpus-stats.json: дамп 2025-2026 = {n}, можем взять (откр. лиц.) = {out['allowed_total']}, "
          f"обработали = {gtot['gen']} ({gtot['express']} express / {gtot['full']} full)")


if __name__ == "__main__":
    main()
