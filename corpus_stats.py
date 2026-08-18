"""Статистика покрытия для дашборда (юзер 2026-07-25): сколько ВСЕГО статей в архиве (Kaggle-дамп)
за 2025-2026 vs сколько мы обработали, разбивка по разделам и ЛИЦЕНЗИЯМ (сколько можем взять),
плюс признаки из дампа (опубликовано в журнале, число версий, размер коллабораций).

Пишет data/corpus-stats.json; дашборд (js/dashboard.js) читает его и рисует блок «Покрытие архива».

ДВА ВХОДА, и это главное в этом файле:

    python corpus_stats.py           наши числа — сколько статей мы обработали (0,2 с)
    python corpus_stats.py --dump    полный скан дампа 5,4 ГБ + наши числа (20 с, замер 2026-07-31)

Почему разведено (2026-07-31). Файл собирал обе половины разом, и дешёвая была прикована к
дорогой: чтобы обновить «обработали», приходилось перечитывать 5,4 ГБ. Никто этого не делал,
и блок «Покрытие» показывал позавчерашние 1922 статьи, пока KPI на той же странице — свежие
2085.

Дело не только в секундах (их, как оказалось, всего двадцать), а в том, что половины живут
в разном ритме и от разного зависят. Наши числа меняются после каждой сборки и считаются по
файлу, который лежит в дереве. Числа arXiv не меняются вообще, пока не выйдет новый дамп
Kaggle, и требуют файла на 5,4 ГБ, которого нет ни в репозитории, ни на чужой машине —
привязать к нему каждую сборку значит сделать её зависимой от чужого диска.

Дефолт — БЕЗ скана: команда без флагов обновляет только наши числа. Полный скан просите явно.
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Консоль Windows по умолчанию cp1252 — печать ✅/❌ роняет скрипт при ручном запуске
# (из run.py спасает PYTHONIOENCODING, но скрипт обязан жить и сам по себе).
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Где искать дамп: Downloads → кэш kagglehub. Тот же список, что в arxiv_bulk_chunk.py,
# и это не роскошь: чанкер после успешного разбора УДАЛЯЕТ исходник, чтобы не держать
# 5 ГБ на диске, и следующим шагом этот скрипт искал дамп ровно там, где его только что
# не стало. В кэше kagglehub при этом лежала живая копия.
_DUMP_CANDIDATES = [
    Path.home() / "Downloads" / "arxiv-metadata-oai-snapshot.json",
    Path.home() / ".cache/kagglehub/datasets/Cornell-University/arxiv/versions/294/arxiv-metadata-oai-snapshot.json",
]
DUMP = next((c for c in _DUMP_CANDIDATES if c.exists()), _DUMP_CANDIDATES[0])
OUT = Path("data/corpus-stats.json")
YEARS = ("25", "26")  # arXiv id YYMM.xxxxx → 2025-2026
# Единственный источник истины по лицензиям — gen_arxiv.license_class (free/analysis/no).
# Своя копия списка здесь уже разъезжалась с конвейером (2026-08-18: NC-семейство открыли
# в отборе, а статистика продолжала считать его закрытым — числа врали бы молча).
from gen_arxiv import license_class  # noqa: E402


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
    return license_class(lic) != "no"


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
    """Наши числа — из готового индекса статей. Это и есть дешёвая половина: чтение одного
    файла, который к моменту вызова уже пересобран генератором."""
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


def build_full():
    """Полная сборка: скан дампа + наши числа. ~20 секунд на 5,4 ГБ — дешёвый пре-фильтр по
    строке отбрасывает чужие годы до разбора json."""
    print("скан Kaggle-дампа за 2025-2026 (лицензии + признаки)…", flush=True)
    if not DUMP.exists():
        print(f"❌ дампа нет: {DUMP}\n   Это единственное, ради чего нужен --dump. Скачайте дамп "
              f"или обновляйте только наши числа: python corpus_stats.py")
        return 1
    # Дата дампа — в файл. Без неё нельзя отличить свежий скан от скана по старой копии
    # из кэша, и витрина молча уезжает назад: сегодняшний прогон по июльской копии дал
    # 462 720 работ там, где вчера было 482 576, и на дашборде это выглядело бы как будто
    # arXiv усох на двадцать тысяч статей.
    dump_mtime = datetime.fromtimestamp(DUMP.stat().st_mtime).strftime("%Y-%m-%d")
    prev = {}
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
    if prev.get("dump_date") and prev["dump_date"] > dump_mtime and not os.environ.get("B42_FORCE_STATS"):
        print(f"⏭️ дамп на диске ({dump_mtime}) старее того, по которому уже посчитано "
              f"({prev['dump_date']}) — числа не трогаю, чтобы витрина не поехала назад.\n"
              f"   Нужно всё равно — B42_FORCE_STATS=1.")
        return 0
    by_month, by_section, licenses, n = scan_dump()
    gm, gtot = generated_counts()
    months = sorted(set(by_month) | set(gm))
    out = {
        "range": "2025-2026",
        "dump_date": dump_mtime,
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
    return 0


def refresh_ours():
    """Быстрый вход: переписывает в готовом corpus-stats.json ТОЛЬКО наши числа — общий счётчик
    и три поля у каждого месяца. Всё, что пришло из дампа (dump/allowed/published/средние,
    разделы, лицензии), остаётся нетронутым: оно про arXiv и меняется только с новым дампом.

    Работает поверх существующего файла и не умеет создавать его с нуля — там, где нужны числа
    arXiv, догадки хуже отсутствия. Нет файла — говорим об этом ненулевым кодом, чтобы хвост
    run.py напечатал предупреждение, а не проглотил молча."""
    if not OUT.exists():
        print(f"❌ {OUT} нет — сначала разовый полный скан: python corpus_stats.py --dump")
        return 1
    data = json.loads(OUT.read_text(encoding="utf-8"))
    gm, gtot = generated_counts()
    was = data.get("generated_total", {}).get("gen", 0)
    data["generated_total"] = gtot

    by_ym = {m["ym"]: m for m in data.get("months", [])}
    for ym, g in gm.items():
        m = by_ym.get(ym)
        if m is None:
            # Месяц, которого в дампе ещё нет: мы уже пишем про свежие статьи, а снимок arXiv
            # сделан раньше. Нули в полях дампа честны — «сколько всего вышло» мы пока не знаем.
            m = {"ym": ym, "dump": 0, "allowed": 0, "published": 0, "avg_authors": 0, "avg_versions": 0}
            by_ym[ym] = m
        m["generated"], m["express"], m["full"] = g["gen"], g["express"], g["full"]
    for ym, m in by_ym.items():
        if ym not in gm:
            m["generated"] = m["express"] = m["full"] = 0
    data["months"] = [by_ym[ym] for ym in sorted(by_ym)]

    OUT.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"✅ corpus-stats.json: наши числа обновлены — обработали {gtot['gen']} "
          f"({gtot['express']} express / {gtot['full']} full), было {was}. "
          f"Числа arXiv не трогали: они из дампа, обновляются через --dump")
    return 0


def main():
    p = argparse.ArgumentParser(description="статистика покрытия для дашборда")
    p.add_argument("--dump", action="store_true",
                   help="полный скан Kaggle-дампа (5,4 ГБ, ~20 с) вдобавок к нашим числам")
    p.add_argument("--ours", action="store_true",
                   help="только наши числа (поведение по умолчанию, флаг для явности)")
    args = p.parse_args()
    return build_full() if args.dump else refresh_ours()


if __name__ == "__main__":
    # Код возврата обязан доезжать до вызывающего: без sys.exit скрипт заканчивался нулём
    # даже после «❌ дампа нет», и обновление дампа рапортовало «🎉 всё обновлено» поверх
    # несделанного шага. Молчащий сбой хуже громкого.
    sys.exit(main())
