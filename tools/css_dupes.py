"""Дубли правил в CSS: один селектор объявлен дважды в одном контексте.

Зачем. Так был найден дефект строки-паспорта карточки: `.card-eyebrow` объявлен дважды
с разницей в 1700 строк, и нижнее объявление возвращало `align-items: baseline` — строка
разъезжалась начиная с даты. Правило, продублированное в двух местах, обязательно
разойдётся (ПРАВИЛА-РАБОТЫ.md), а в файле на три с половиной тысячи строк второе
объявление глазами не находится.

    python tools/css_dupes.py                 # css/style.css
    python tools/css_dupes.py путь.css
    python tools/css_dupes.py --check         # код 1, если есть опасные дубли

Что считаем опасным. Не всякий повтор: одинаковый селектор внутри @media — норма
(мобильная ступень, тёмная тема). Опасен тот, где второе объявление ПЕРЕОПРЕДЕЛЯЕТ
свойство, заданное в первом: только там читатель видит не то, что написано выше, и
только там правка «по месту» уходит в пустоту. Такие идут первыми, по разбросу строк —
чем дальше объявления друг от друга, тем вернее, что автор второго не знал о первом.

Мерка честная: разбираем текст, а не догадываемся по отступам. Комментарии вырезаются
до разбора, иначе фигурные скобки внутри них ломают счётчик вложенности.
"""
import io
import re
import sys
from collections import defaultdict

DEFAULT = "css/style.css"


def parse(text):
    """→ [(контекст, селектор, строка, {свойство: значение})]"""
    clean = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)

    line_at, ln = [], 1
    for ch in clean:
        line_at.append(ln)
        if ch == "\n":
            ln += 1
    line_at.append(ln)

    rules, ctx = [], []
    i = head_start = 0
    while i < len(clean):
        ch = clean[i]
        if ch == "{":
            head = clean[head_start:i].strip()
            if head.startswith("@"):
                ctx.append(" ".join(head.split()))
                head_start = i + 1
                i += 1
                continue
            j, depth = i + 1, 1
            while j < len(clean) and depth:
                if clean[j] == "{":
                    depth += 1
                elif clean[j] == "}":
                    depth -= 1
                j += 1
            props = {}
            for part in clean[i + 1:j - 1].split(";"):
                if ":" in part:
                    k, v = part.split(":", 1)
                    k = k.strip().lower()
                    if k and not k.startswith("--"):
                        props[k] = " ".join(v.split())
            for sel in head.split(","):
                sel = " ".join(sel.split())
                if sel:
                    rules.append((" | ".join(ctx), sel, line_at[head_start], props))
            i = head_start = j
            continue
        if ch == "}":
            if ctx:
                ctx.pop()
            head_start = i + 1
        i += 1
    return rules


def collect(rules):
    by_key = defaultdict(list)
    for c, s, line, props in rules:
        by_key[(c, s)].append((line, props))

    risky, benign = [], []
    for (c, s), items in by_key.items():
        if len(items) < 2:
            continue
        clashes = []
        for a in range(len(items)):
            for b in range(a + 1, len(items)):
                shared = set(items[a][1]) & set(items[b][1])
                diff = [p for p in shared if items[a][1][p] != items[b][1][p]]
                if diff:
                    clashes.append((items[a], items[b], diff))
        (risky if clashes else benign).append((c, s, items, clashes))
    return risky, benign


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check = "--check" in sys.argv
    path = args[0] if args else DEFAULT

    rules = parse(io.open(path, encoding="utf-8").read())
    risky, benign = collect(rules)
    risky.sort(key=lambda x: -max(abs(b[0] - a[0]) for a, b, _ in x[3]))

    print(f"файл: {path}")
    print(f"правил: {len(rules)}, уникальных селекторов: {len(rules) - len(risky) - len(benign)}\n")

    print("=== ОПАСНЫЕ: тот же селектор, то же свойство, разные значения ===")
    for c, s, items, clashes in risky:
        span = max(abs(b[0] - a[0]) for a, b, _ in clashes)
        where = f"в «{c}»" if c else "верхний уровень"
        print(f"\n  {s}   [{where}]  строки {[l for l, _ in items]}   разброс {span}")
        for a, b, diff in clashes[:2]:
            for p in diff[:4]:
                print(f"      {p}: {a[0]}→{a[1][p]}   ПЕРЕБИТО {b[0]}→{b[1][p]}")

    print(f"\n  опасных: {len(risky)}")
    print(f"  повторов без спора свойств: {len(benign)}")

    if check and risky:
        print("\nСвести объявление в одно место: правка «по месту» иначе уходит в пустоту.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
