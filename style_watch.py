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


# «Что статья ДАЛА» — требование владельца 2026-08-04: три вопроса, на которые текст обязан
# отвечать. Четвёртый шаблон ловит честное признание, что пользы пока нет, — оно ценно само
# по себе: замер до правки промптов показал 0%, то есть мы не признавались НИКОГДА.
BEFORE_AFTER = re.compile(r"\b(до сих пор|раньше|прежде|до этой работы|оставалось загадкой|"
                          r"не удавалось|никто не|теперь|впервые)\b", re.I)
METHOD_PLAIN = re.compile(r"\b(сравнил\w+|измерил\w+|проследил\w+|дождал\w+|смоделировал\w+|"
                          r"перебрал\w+|обучил\w+|наблюдал\w+|проверил\w+ на)\b", re.I)
USE_TODAY = re.compile(r"\b(пригодит\w+|применен\w+|на практике|в технике|инженер\w+|"
                       r"медицин\w+|уже сегодня|позволит)\b", re.I)
HONEST_NO_USE = re.compile(r"\b(чистое знание|применений пока|практического применения пока|"
                           r"до применений далеко)\b", re.I)


def report_meaning():
    """Отвечают ли статьи на три вопроса читателя. Замер 2026-08-04, ДО правки промптов:
    все три закрыты у 2% статей, приём словами у 10%, честное «пользы нет» — 0%."""
    rows = []
    for path in Path(f"lang/{DEFAULT_LANG}/archive").glob("*/*/data.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        text = strip_markup(((data.get("popular") or {}).get(DEFAULT_LANG) or {}).get("text", ""))
        if len(text) < 800:
            continue
        rows.append((bool(BEFORE_AFTER.search(text)), bool(METHOD_PLAIN.search(text)),
                     bool(USE_TODAY.search(text)), bool(HONEST_NO_USE.search(text))))
    if not rows:
        print("нечего мерить: нет статей с популярным уровнем длиннее 800 знаков")
        return
    n = len(rows)
    print(f"что статья дала (популярный уровень, статей {n}):")
    print(f"   было ДО → стало ПОСЛЕ:      {sum(r[0] for r in rows) * 100 // n}%")
    print(f"   приём словами:              {sum(r[1] for r in rows) * 100 // n}%")
    print(f"   где пригодится:             {sum(r[2] for r in rows) * 100 // n}%")
    print(f"   честное «пользы пока нет»:  {sum(r[3] for r in rows) * 100 // n}%")
    print(f"   все три вопроса закрыты:    {sum(1 for r in rows if r[0] and r[1] and r[2]) * 100 // n}%")


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
    ap.add_argument("--meaning", action="store_true",
                    help="отвечают ли статьи на три вопроса читателя (что дала работа)")
    args = ap.parse_args()

    if args.meaning:
        report_meaning()
        return

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
