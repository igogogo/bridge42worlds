"""Сбор цитирований из сохранённых PDF: связи «многие ко многим» бесплатно.

Владелец 2026-08-06: «пройтись по PDF, вытащить списки, дополнить базу связью многие
ко многим — это как-то почти бесплатно». Так и есть: ни одного обращения к модели,
только чтение файлов, которые уже лежат на диске.

Что было: split_references отрезал библиографию от тела (правильно — она ест до 20%
токенов при генерации), а extract_ref_arxiv_ids вытаскивал оттуда идентификаторы —
но только у полных статей и только в момент генерации. Итог: цитирования есть у 744
статей из 2179, при том что PDF лежит у ВСЕХ 2179, включая экспрессы.

Почему эти связи ценнее векторных: наша векторная близость вероятностная («похоже
по смыслу»), цитирование — фактическое и направленное. A цитирует B — значит B раньше
и фундаментальнее. Это скелет, на котором держится настоящая наука, а не наша догадка
о ней.

    python tools/citations_harvest.py --dry     посчитать, ничего не писать
    python tools/citations_harvest.py           пройти все PDF и дополнить data.json

Пишет cited_arxiv (список id) и cited_dois в data.json, плюс сводку связей в
data/citations.json: внутренние рёбра графа, сопряжение (общие источники) и внешние
работы, которые цитируют многие наши статьи, — кандидаты в очередь пополнения.
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# arXiv-идентификатор в любом виде, какой встречается в библиографиях:
# arXiv:2401.12345, arxiv.org/abs/2401.12345, [2401.12345], старый формат hep-th/9901001
ARXIV_RE = re.compile(
    r"(?:ar[Xx]iv[:\s]*|arxiv\.org/(?:abs|pdf)/)((?:\d{4}\.\d{4,5})|(?:[a-z-]+(?:\.[A-Z]{2})?/\d{7}))",
    re.I)
BARE_RE = re.compile(r"[\[(](\d{4}\.\d{4,5})[\])]")
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")


def refs_text(folder):
    """Библиография: из готового references.txt, иначе режем PDF заново."""
    rf = folder / "references.txt"
    if rf.exists():
        t = rf.read_text(encoding="utf-8", errors="replace")
        if len(t) > 200:
            return t, "файл"
    pdf = folder / "original.pdf"
    if not pdf.exists():
        return "", "нет"
    try:
        from gen_arxiv import parse_pdf, split_references
        text, _ = parse_pdf(pdf)
        if not text:
            return "", "пусто"
        body, refs = split_references(text)
        if refs and len(refs) > 200:
            rf.write_text(refs, encoding="utf-8", errors="replace")   # пригодится в следующий раз
            return refs, "pdf"
        # Заголовка «References» может не быть — берём хвост: библиография всегда в конце.
        return text[-14000:], "хвост"
    except Exception:
        return "", "сбой"


def ids_from(text):
    out = []
    for m in ARXIV_RE.finditer(text):
        out.append(m.group(1))
    for m in BARE_RE.finditer(text):
        out.append(m.group(1))
    # Порядок сохраняем, дубли убираем: порядок в библиографии несёт смысл.
    return list(dict.fromkeys(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    paths = sorted((ROOT / "lang/ru/archive").glob("*/*/data.json"))
    ours = {p.parent.name: p for p in paths}
    ours_base = {k.split("v")[0]: k for k in ours}

    cites = {}
    stat = Counter()
    added = 0
    for p in paths:
        d = json.loads(p.read_text(encoding="utf-8"))
        aid = p.parent.name
        было = d.get("cited_arxiv") or []
        text, src = refs_text(p.parent)
        stat[src] += 1
        found = ids_from(text) if text else []
        dois = list(dict.fromkeys(DOI_RE.findall(text)))[:60] if text else []
        merged = list(dict.fromkeys(list(было) + found))
        cites[aid] = merged
        if not args.dry and (len(merged) > len(было) or dois):
            d["cited_arxiv"] = merged
            if dois:
                d["cited_dois"] = dois
            p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            if len(merged) > len(было):
                added += 1

    with_c = sum(1 for v in cites.values() if v)
    total_refs = sum(len(v) for v in cites.values())
    print(f"статей {len(cites)} · с цитированиями {with_c} ({with_c * 100 // len(cites)}%) · "
          f"ссылок {total_refs}")
    print("источник библиографии:", dict(stat))
    if not args.dry:
        print(f"дополнено статей: {added}")

    # ── связи ──
    internal = []          # A → B, обе наши: фактическое ребро графа
    for a, refs in cites.items():
        for r in refs:
            b = ours_base.get(r.split("v")[0])
            if b and b != a:
                internal.append((a, b))
    # сопряжение: сколько общих источников у пары наших статей (об одном, даже если
    # тексты не похожи — классическая мерка, и данные для неё у нас в руках)
    by_ref = defaultdict(list)
    for a, refs in cites.items():
        for r in refs:
            by_ref[r.split("v")[0]].append(a)
    pair = Counter()
    for r, arts in by_ref.items():
        if 1 < len(arts) <= 40:          # ссылку из сотни статей общей темой не считаем
            arts = sorted(set(arts))
            for i in range(len(arts)):
                for j in range(i + 1, len(arts)):
                    pair[(arts[i], arts[j])] += 1
    coupled = {k: v for k, v in pair.items() if v >= 2}
    # внешние работы, на которые ссылаются многие наши статьи — кандидаты в пополнение
    outside = Counter({r: len(a) for r, a in by_ref.items() if r not in ours_base})
    print(f"\nвнутренних рёбер (наши → наши): {len(internal)}")
    print(f"пар статей с ≥2 общими источниками: {len(coupled)}")
    print(f"внешних работ, цитируемых нами: {len(outside)}; из них ≥3 раза: "
          f"{sum(1 for _, n in outside.items() if n >= 3)}")
    print("самые цитируемые нами внешние работы:")
    for r, n in outside.most_common(8):
        print(f"   {n}×  arXiv:{r}")

    if not args.dry:
        (ROOT / "data" / "citations.json").write_text(json.dumps({
            "internal": [{"from": a, "to": b} for a, b in internal],
            "coupled": [{"a": k[0], "b": k[1], "shared": v}
                        for k, v in sorted(coupled.items(), key=lambda x: -x[1])[:3000]],
            "wanted": [{"id": r, "cited_by": n} for r, n in outside.most_common(500)],
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        print("\nсводка: data/citations.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
