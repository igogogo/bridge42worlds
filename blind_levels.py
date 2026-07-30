"""Слепая приёмка уровней: различим ли уровень по одному абзацу, без подсказок.

Зачем именно слепо. Читая статью целиком и зная, что это «simple», уровень всегда «выглядит
правильным» — глаз достраивает. Проверка имеет смысл, только если сначала прочитал абзац
и назвал уровень, а потом узнал ответ. Поэтому здесь два шага и ключ на диске.

    python blind_levels.py ask   --n 8            # печатает перемешанные фрагменты, ключ прячет
    python blind_levels.py score --answers a.txt  # сверяет ответы с ключом

Файл ответов — строки вида «A1 simple» (регистр и порядок не важны).
Перемешивание детерминировано (--seed), чтобы приёмку можно было повторить.

Ничего не меняет, только читает lang/. Запускать можно всем.
"""
import argparse
import json
import random
import re
from pathlib import Path

LANG = "ru"
LEVELS = ("simple", "popular", "advanced")
KEY_PATH = Path(".blind-levels-key.json")   # не в git: ответ не должен попасться на глаза
MARKUP = re.compile(r"\[/?(?:tag|scientist|law|callout)[^\]]*\]")


def levels_of(data):
    """Один средний абзац каждого уровня. Средний, а не первый: первый абзац часто
    начинается одинаково во всех версиях, и различие пришлось бы угадывать по зачину."""
    out = {}
    for level in LEVELS:
        scipop = (data.get(level) or {}).get(LANG) or {}
        text = scipop.get("text") or " ".join(
            scipop.get(k, "") for k in ("context", "methods", "results", "implications"))
        paragraphs = [MARKUP.sub("", p).strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        paragraphs = [p for p in paragraphs if len(p) > 200]
        if paragraphs:
            out[level] = paragraphs[len(paragraphs) // 2]
    return out if len(out) == len(LEVELS) else {}


def collect(root, since, until, limit, rng):
    found = []
    for path in sorted(Path(root).glob("*/*/data.json")):
        date = path.parent.parent.name
        if not since <= date <= until:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("express"):
            continue          # у экспресса уровни намеренно одинаковые, проверять нечего
        picked = levels_of(data)
        if picked:
            found.append((path.parent.name, date, picked))
    rng.shuffle(found)
    return found[:limit]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("ask", "score"))
    ap.add_argument("--root", default=f"lang/{LANG}/archive")
    ap.add_argument("--new", default="2026-07-24:2026-07-29", help="диапазон дат нового конвейера")
    ap.add_argument("--old", default="2026-07-17:2026-07-23", help="диапазон дат старого")
    ap.add_argument("--n", type=int, default=6, help="статей из каждого конвейера")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--answers", help="файл ответов для score")
    args = ap.parse_args()

    if args.mode == "score":
        if not KEY_PATH.exists():
            print("ключа нет — сначала ask")
            return
        key = json.loads(KEY_PATH.read_text(encoding="utf-8"))
        answers = {}
        for line in Path(args.answers).read_text(encoding="utf-8").split("\n"):
            parts = line.split()
            if len(parts) >= 2:
                answers[parts[0].strip().upper()] = parts[1].strip().lower()
        right = wrong = 0
        misses = []
        for code, meta in sorted(key.items()):
            given = answers.get(code)
            if given == meta["level"]:
                right += 1
            else:
                wrong += 1
                misses.append(f"  {code}  {meta['pipeline']:>6}  верно: {meta['level']:<9} "
                              f"назвал: {given or '—':<9} {meta['id']}")
        total = right + wrong
        print(f"попал: {right} из {total} ({right * 100 // max(1, total)}%)")
        by_pipe = {}
        for code, meta in key.items():
            ok = answers.get(code) == meta["level"]
            hit, cnt = by_pipe.get(meta["pipeline"], (0, 0))
            by_pipe[meta["pipeline"]] = (hit + (1 if ok else 0), cnt + 1)
        for pipe, (hit, cnt) in sorted(by_pipe.items()):
            print(f"  {pipe}: {hit} из {cnt}")
        if misses:
            print("\nмимо:")
            print("\n".join(misses))
        return

    rng = random.Random(args.seed)
    items = []
    for pipeline, span in (("новый", args.new), ("старый", args.old)):
        since, until = span.split(":")
        for aid, date, picked in collect(args.root, since, until, args.n, rng):
            for level, fragment in picked.items():
                items.append({"id": aid, "date": date, "pipeline": pipeline,
                              "level": level, "fragment": fragment})
    if not items:
        print("нечего проверять: в этих датах нет неэкспресс-статей со всеми тремя уровнями")
        return
    rng.shuffle(items)

    key = {}
    for i, item in enumerate(items, 1):
        code = f"A{i}"
        key[code] = {k: item[k] for k in ("id", "date", "pipeline", "level")}
        print(f"\n=== {code} ===\n{item['fragment']}")
    KEY_PATH.write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n\nфрагментов: {len(items)}. Ключ спрятан в {KEY_PATH} — не открывай до ответов.")


if __name__ == "__main__":
    main()
