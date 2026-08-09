"""Проверка самих промптов — те правила, которые 31 июля стоили нам аннотации на витрине.

Разбор владельца дал пять уроков; три из них проверяются машинно, и здесь они и живут:

1. ЯЗЫК В КОНЦЕ. Требование «пиши по-русски» в начале файла модель теряет — так аннотация
   молча вышла английской. Правило должно стоять рядом с форматом ответа.
2. {style_core} НА ОТДЕЛЬНОЙ СТРОКЕ. В article-generate-express он стоял в середине фразы,
   и инструкция разваливалась пополам, а между половинами вклинивался весь блок стиля.
3. НЕТ РЕФЕРАТИВНОГО БРИФА. «Краткое содержание», «сохрани суть и результаты» без указания
   голоса превращают модель в реферативный журнал — ровно то, что читатель увидел на карточке.

Четвёртый и пятый урок (где показывается результат; правка стиля может ухудшить текст)
машинно не проверить — они в чеклисте вывода, читать глазами.

    python prompts_watch.py            # сводка
    python prompts_watch.py --list     # + строки-нарушители

Ничего не меняет, только читает data/prompts/. Запускать можно всем.
"""
import argparse
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROMPTS = Path("data/prompts")
TAIL_LINES = 12          # «в конце» — последние строки перед форматом ответа

LANG_RULE = re.compile(r"СТРОГО\s+(НА\s+РУССКОМ|на русском)|"
                       r"пиши\s+.{0,30}по-русски|TARGET LANGUAGE", re.I)
REFERAT = re.compile(r"краткое содержание|кратко переска|реферат", re.I)
# Промпты, которым язык не нужен: они либо сами про язык (перевод), либо не порождают
# видимого читателем текста (отбор, ранжирование, промпт картинки на английском).
NO_LANG_NEEDED = {"article-translate", "caption-translate", "reference-translate",
                  "reference-translate-about", "scientist-translate",
                  "image-generate", "image-generate-ref",
                  "article-select", "article-rank", "arab-authors-select",
                  # system.txt — не промпт, а системная роль: она идёт отдельным
                  # сообщением и целиком, терять там нечего.
                  "system",
                  # ask-answer отвечает читателю НА ЯЗЫКЕ ВОПРОСА — требовать русский тут
                  # значило бы отвечать по-русски французу. Правило языка у него своё.
                  "ask-answer",
                  # article-kind отдаёт не текст, а один из четырёх английских ярлыков
                  # (experimental/theoretical/methods/review) — требование русского его сломает.
                  "article-kind"}


def check(path):
    text = path.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    name = path.stem
    problems = []

    if name not in NO_LANG_NEEDED:
        # «В конце» — это ПОСЛЕ входных данных статьи/справочника. Иначе между правилом
        # и ответом лежит длинный входной текст, и модель дочитывает до него, а не до правила.
        last_input = max((i for i, ln in enumerate(lines)
                          if re.search(r"\$\w+|\{(summary|article_text|advanced_json|popular_json|"
                                       r"simple_json|abstract_json|articles_json|scipop_json)\}", ln)),
                         default=-1)
        rule_lines = [i for i, ln in enumerate(lines) if LANG_RULE.search(ln)]
        if not rule_lines:
            problems.append(("язык", "требования языка нет вовсе"))
        elif max(rule_lines) < last_input:
            problems.append(("язык", f"требование языка в строке {max(rule_lines) + 1}, "
                                     f"а входные данные ниже (строка {last_input + 1}) — "
                                     f"модель дочитывает до них, а не до правила"))
        elif max(rule_lines) < len(lines) - TAIL_LINES * 2:
            problems.append(("язык", f"требование языка в строке {max(rule_lines) + 1} "
                                     f"из {len(lines)} — далеко от формата ответа"))

    for i, line in enumerate(lines):
        if "{style_core}" in line and line.strip() != "{style_core}":
            problems.append(("style_core", f"строка {i + 1}: плейсхолдер внутри текста — «{line.strip()[:60]}»"))

    for i, line in enumerate(lines):
        # «…а не как краткое содержание» — это запрет, а не бриф. Ловим только утверждения.
        if REFERAT.search(line) and not re.search(r"не как|а не|НЕЛЬЗЯ|✗", line):
            problems.append(("реферат", f"строка {i + 1}: «{line.strip()[:70]}»"))

    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="показать строки-нарушители")
    args = ap.parse_args()

    if not PROMPTS.exists():
        print(f"нет {PROMPTS} — запускать из корня проекта")
        return

    files = sorted(p for p in PROMPTS.glob("*.txt") if not p.name.startswith("_"))
    dirty = {}
    for path in files:
        problems = check(path)
        if problems:
            dirty[path.stem] = problems

    kinds = {}
    for problems in dirty.values():
        for kind, _ in problems:
            kinds[kind] = kinds.get(kind, 0) + 1
    print(f"промптов проверено: {len(files)}, с замечаниями: {len(dirty)}")
    for kind, count in sorted(kinds.items(), key=lambda kv: -kv[1]):
        print(f"   {count:>3}  {kind}")
    if args.list:
        for name, problems in sorted(dirty.items()):
            print(f"\n{name}")
            for kind, detail in problems:
                print(f"   {kind}: {detail}")
    elif dirty:
        print("\n" + ", ".join(sorted(dirty)) + "\n--list — подробности")


if __name__ == "__main__":
    main()
