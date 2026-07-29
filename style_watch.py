"""Контроль стиля сгенерированных статей — проверяет то, что записано в data/prompts/_style-core.txt.

Заведён 2026-07-29 после разбора: правило «клише-открывашки» модель исполняла буквально —
первая фраза чистая, а аналогию в середине текста вводила через «Представьте, что…».
Глазами это ловится только выборочно, а промпт-правило без проверки живёт до первого прогона.
Поэтому каждое правило стиля, которое можно проверить текстом, проверяется здесь.

Проверяет только статьи НОВОЙ схемы (у них заполнена metaphor) — на старых текстах
правила ещё не действовали, и они бы забили отчёт шумом.

Запуск:
    python style_watch.py              # сводка по нарушениям
    python style_watch.py --list       # + id статей и фрагменты
    python style_watch.py --all        # включая статьи старой схемы

Ничего не меняет, только читает. Запускать можно всем.
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

DEFAULT_LANG = "ru"
LEVELS = ("simple", "popular")

# Обращение к читателю в повелительном наклонении. Ловим именно обращение: «Вальрас вообразил
# аукциониста» — законное описание поступка учёного, а не клише, и попадать в отчёт не должно.
ADDRESS = re.compile(
    r"\b(представьте|вообразите|подумайте только|заметьте|обратите внимание|"
    r"а знаете ли вы|согласитесь)\b", re.I)
FILLERS = re.compile(
    r"\b(поистине|невероятн\w*|уникальн\w*|революционн\w*|прорывн\w*|"
    r"сложно переоценить|не что иное, как)\b", re.I)
PROMO = re.compile(r"\b(читайте в статье|узнайте больше)\b", re.I)
MARKUP = re.compile(r"\[/?(?:tag|scientist|law|callout)[^\]]*\]")

MINI_MIN, MINI_MAX = 600, 900


def strip_markup(text):
    return MARKUP.sub("", text or "")


def mini_of(data):
    """mini живёт по-разному в зависимости от поколения статьи: в новой схеме — поле simple.mini,
    в старой — popular.threads (наследие лимита Threads). Берём то, что есть."""
    simple = (data.get("simple") or {}).get(DEFAULT_LANG) or {}
    popular = (data.get("popular") or {}).get(DEFAULT_LANG) or {}
    return simple.get("mini") or popular.get("threads") or data.get("mini") or ""


def check_article(data):
    """→ список (уровень, тип нарушения, фрагмент)."""
    problems = []
    texts = {lvl: strip_markup(((data.get(lvl) or {}).get(DEFAULT_LANG) or {}).get("text", ""))
             for lvl in LEVELS}
    texts["mini"] = strip_markup(mini_of(data))

    for level, text in texts.items():
        for kind, pattern in (("обращение", ADDRESS), ("усилитель", FILLERS), ("зазывание", PROMO)):
            for m in pattern.finditer(text):
                start = max(0, m.start() - 40)
                problems.append((level, kind, text[start:m.end() + 40].replace("\n", " ")))

    mini = texts["mini"]
    if mini and not MINI_MIN <= len(mini) <= MINI_MAX:
        problems.append(("mini", "длина", f"{len(mini)} знаков (норма {MINI_MIN}–{MINI_MAX})"))
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="показать id статей и фрагменты")
    ap.add_argument("--all", action="store_true", help="включая статьи старой схемы")
    args = ap.parse_args()

    paths = sorted(Path(f"lang/{DEFAULT_LANG}/archive").glob("*/*/data.json"))
    checked = 0
    dirty = 0
    kinds = Counter()
    details = []

    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        advanced = (data.get("advanced") or {}).get(DEFAULT_LANG) or {}
        if not args.all and not advanced.get("metaphor"):
            continue  # старая схема — правила стиля к ней не применялись
        checked += 1
        problems = check_article(data)
        if problems:
            dirty += 1
            for level, kind, fragment in problems:
                kinds[f"{level}: {kind}"] += 1
                details.append((path.parent.name, level, kind, fragment))

    scope = "весь архив" if args.all else "статьи новой схемы"
    print(f"проверено: {checked} ({scope}) из {len(paths)}")
    if not checked:
        print("нечего проверять — статей новой схемы ещё нет, попробуйте --all")
        return
    print(f"с нарушениями: {dirty} ({dirty * 100 // checked}%)\n")
    for name, count in kinds.most_common():
        print(f"  {count:>4}  {name}")
    if args.list:
        print()
        for aid, level, kind, fragment in details:
            print(f"  {aid}  {level}/{kind}: …{fragment}…")
    elif details:
        print("\n--list — с фрагментами")


if __name__ == "__main__":
    main()
