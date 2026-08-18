"""Системный сбалансированный отбор статей из свежего arXiv-снапшота (решение владельца 2026-07-27:
«выборка пропорциональная, чтобы не было много из квантовой — всех поровну из разделов,
наполняем системно; количество не показатель»).

Принцип:
- смотрим ВСЕ наши разделы (наш справочник arxiv-categories, 156 категорий);
- считаем, сколько статей у нас УЖЕ есть в каждом разделе;
- берём поровну на раздел, отдавая приоритет тем, где у нас меньше всего (выравниваем перекос);
- фильтруем по открытой лицензии и по тому, чего ещё нет в архиве.

Запуск:
    python balanced_select.py --per-section 2 --months 2026-07,2026-08
    python balanced_select.py --check          # только показать текущий перекос
"""
import json
import re
from datetime import datetime
import sys
from collections import Counter, defaultdict
from pathlib import Path

DUMP = Path(r"C:/Users/nadez/Downloads/arxiv-metadata-oai-snapshot.json")
# Компактный индекс (arxiv_index_build.py) — 107 МБ вместо 5 ГБ. Если он есть, снапшот не нужен.
INDEX = Path("data/arxiv-index.jsonl")
OUT_DIR = Path("data/bulk-select")
# Свободные лицензии — полный конвейер. NC-семейство (решение владельца 2026-08-18 после
# пропуска 2606.12457: «расширяем забор, не берём картинки, ставим признак») — тоже берём,
# но конвейер помечает их license_class=analysis: только собственный текст, авторские
# рисунки и подписи не используются (см. gen_arxiv.license_class и _build_article).
ALLOWED = ("by/4.0", "by-sa/4.0", "zero/1.0", "nonexclusive-distrib/1.0",
           "by-nc-nd/4.0", "by-nc-sa/4.0", "by-nc/4.0")
DEFAULT_LANG = "ru"


def our_sections():
    """Наши разделы (id → название) из локализованного справочника."""
    p = Path("data/arxiv-categories-ru.json")
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def existing_counts():
    """Сколько статей у нас уже есть в каждом разделе + множество готовых id."""
    idx = Path(f"lang/{DEFAULT_LANG}/articles-index.json")
    have, per = set(), Counter()
    if idx.exists():
        for a in json.loads(idx.read_text(encoding="utf-8")):
            if a["id"] in have:
                continue
            have.add(a["id"])
            cats = a.get("categories") or []
            if cats:
                per[cats[0]] += 1
    # плюс то, что лежит на диске, но ещё не в индексе
    for p in Path(f"lang/{DEFAULT_LANG}/archive").glob("*/*/data.json"):
        have.add(p.parent.name)
    return per, have


def is_allowed(lic):
    return bool(lic) and any(a in lic for a in ALLOWED)


def _iso_date(v):
    """arXiv отдаёт «Wed, 1 Jul 2026 12:00:00 GMT» — приводим к 2026-07-01, иначе имя папки статьи
    получается обрубком вроде «Wed, 01 Ju» (поймано аудитом 2026-07-27)."""
    v = (v or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", v):
        return v[:10]
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S GMT"):
        try:
            return datetime.strptime(v, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})", v)
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %b %Y").strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


def _chunk_meta(months):
    """Заголовки/абстракты/авторы — из наших месячных чанков (в индексе их нет: он про лицензии).
    Так снапшот не нужен вовсе: лицензия из индекса, содержимое отсюда."""
    meta = {}
    for m in months:
        f = Path("data/arxiv-bulk") / f"{m}.jsonl"
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("id"):
                meta[d["id"]] = d
    return meta


def scan(months, have, sections, per_section, need_sections):
    """Один проход по дампу: собираем кандидатов по нужным разделам."""
    want = set(need_sections)
    pool = defaultdict(list)
    seen = 0
    source = INDEX if INDEX.exists() else DUMP
    from_index = source is INDEX
    meta = _chunk_meta(months) if from_index else {}
    with source.open(encoding="utf-8") as f:
        for line in f:
            head = line[:24]
            if not any(f'"{m[2:4]}{m[5:7]}.' in head for m in months):
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            aid = d.get("id", "")
            if aid in have:
                continue
            cats = (d.get("c") if from_index else d.get("categories") or "").split()
            if not cats:
                continue
            primary = cats[0]
            if primary not in want:
                continue
            if not is_allowed(d.get("l") if from_index else d.get("license")):
                continue
            if len(pool[primary]) >= per_section * 4:      # запас на ранжирование
                continue
            pool[primary].append({
                "id": aid,
                "title": (d.get("title") or "").strip().replace("\n", " "),
                "summary": (d.get("abstract") or "").strip().replace("\n", " "),
                "authors": [" ".join(x[::-1]).strip() for x in (d.get("authors_parsed") or [])],
                "categories": cats,
                "primary_category": primary,
                "published": _iso_date(d.get("d") if from_index else (d.get("versions") or [{}])[0].get("created", "")),
                "license": (d.get("l") if from_index else d.get("license", "")),
                "reviewed": (d.get("p") if from_index else (1 if (d.get("doi") or d.get("journal-ref")) else 0)),
            })
            seen += 1
    return pool, seen


def main():
    argv = sys.argv
    per_section = int(argv[argv.index("--per-section") + 1]) if "--per-section" in argv else 2
    months = (argv[argv.index("--months") + 1].split(",") if "--months" in argv
              else ["2026-07", "2026-08"])

    sections = our_sections()
    per, have = existing_counts()
    print(f"наших разделов: {len(sections)} | статей в архиве: {len(have)}")

    covered = [s for s in sections if per.get(s, 0) > 0]
    empty = [s for s in sections if per.get(s, 0) == 0]
    top = per.most_common(5)
    print(f"перекос: покрыто {len(covered)} разделов, пусто {len(empty)}")
    print(f"  больше всего: {[(s, n) for s, n in top]}")
    if "--check" in argv:
        print(f"  пустые (первые 15): {empty[:15]}")
        return

    # приоритет — разделам, где у нас меньше всего (выравниваем)
    need = sorted(sections, key=lambda s: per.get(s, 0))
    print(f"\nсканирую дамп за {months} по {len(need)} разделам, цель — {per_section} на раздел…", flush=True)
    pool, seen = scan(months, have, sections, per_section, need)

    # внутри раздела — предпочитаем работы, которые уже прошли рецензию (есть journal-ref/doi)
    picked = []
    for s in need:
        cand = pool.get(s) or []
        cand.sort(key=lambda a: (0 if a.get("reviewed") else 1, -len(a["summary"])))
        picked.extend(cand[:per_section])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = months[-1].replace("-", "") + f"-balanced{per_section}"
    out = OUT_DIR / f"{stamp}.json"
    # формат как у article_bulk_select.py — bulk_generate читает ключ "ready"
    payload = {
        "run_id": stamp,
        "created": months[-1],
        "mode": "balanced",
        "per_section": per_section,
        "months": months,
        "pool_size": seen,
        "ready": picked,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    got = Counter(a["primary_category"] for a in picked)
    print(f"\nотобрано: {len(picked)} статей из {len(got)} разделов (кандидатов просмотрено {seen})")
    print(f"  максимум на раздел: {max(got.values()) if got else 0} — перекоса нет")
    print(f"  файл: {out}")
    print(f"\nзапуск генерации:\n  python run.py bulk-generate --file {out} --batch-size 5")


if __name__ == "__main__":
    main()
