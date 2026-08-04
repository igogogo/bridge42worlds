"""Формулы в тексте: чиним разметку без перегенерации статей.

Владелец 2026-08-02: «формулы по тексту, степени и так далее хромают — Ω\\_{GW}h\\^2 ~
10\\^{-12}. Это можно потом пройтись, необязательно перегенерировать».

Он прав: платить модели за пересказ ради разметки незачем — текст правильный, сломано
только оформление. Три разных беды, и лечатся они по-разному:

1. ЭКРАНИРОВАНИЕ ИЗ MARKDOWN: модель пишет `Ω\\_{GW}h\\^2`, защищая подчёркивание от
   markdown. У нас markdown не используется вовсе, а KaTeX от такой записи отказывается —
   читатель видит косые черты посреди формулы. Убираем экранирование.
2. ГОЛАЯ МАТЕМАТИКА БЕЗ РАЗДЕЛИТЕЛЕЙ: `10^{-38}`, `g_A^n`, `X_{Max}` — формула написана,
   но KaTeX её не видит, потому что нечем опознать. Оборачиваем в $…$.
3. РАЗДЕЛИТЕЛИ \\( \\) и \\[ \\] — эти KaTeX понимает, их не трогаем.

    python tools/fix_inline_math.py --dry            посмотреть, что изменится
    python tools/fix_inline_math.py                  починить весь архив
    python tools/fix_inline_math.py --ids 2607.1 …   точечно

Правим ВСЕ языки: формула одна на всех, и сломана она везде одинаково.
"""
import argparse
import json
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

ROOT = Path(__file__).resolve().parent.parent
TIERS = ("simple", "popular", "advanced")
FIELDS = ("text", "description", "fun_fact", "threads", "oneliner", "context",
          "methods", "results", "implications", "future_development", "mini")

# Маркеры сущностей и уже размеченные формулы трогать нельзя: внутри [tag:...] лежит
# идентификатор ссылки, а внутри $…$ и \(…\) — готовая формула.
PROTECT = re.compile(
    r"(\[(?:tag|scientist|law):[^\]]+\]|\[/(?:tag|scientist|law)\]"
    r"|\$[^$\n]{1,200}\$"
    r"|\\\([^)]{1,300}?\\\)"
    r"|\\\[[^\]]{1,400}?\\\])"
)

ESCAPED = re.compile(r"\\([_^{}])")

# Кусок математики без разделителей: символ (латиница/греческая) или число с индексом
# либо степенью, возможно цепочкой. Кириллицу НЕ трогаем — это обычный текст.
BARE = re.compile(
    r"(?<![\w$\\])"
    r"("
    r"(?:[A-Za-zΑ-ω]|\d+(?:[.,]\d+)?)"
    r"(?:[_^]\{[^{}\n]{1,24}\}|[_^][A-Za-z0-9+\-]{1,4})+"
    r"(?:\s*[×·]\s*10[_^]\{?-?\d+\}?)?"
    r")"
)


def fix_text(s):
    """Возвращает (новый текст, сколько правок). Защищённые куски не трогаются."""
    if not isinstance(s, str) or not s:
        return s, 0
    parts = PROTECT.split(s)
    changed = 0
    out = []
    for i, chunk in enumerate(parts):
        # нечётные индексы — это сами защищённые совпадения
        if i % 2 == 1 or not chunk:
            out.append(chunk)
            continue
        new = chunk
        if ESCAPED.search(new):
            new = ESCAPED.sub(r"\1", new)
            changed += 1
        def wrap(m):
            # Многозначную степень/индекс берём в фигурные скобки: `10^42` KaTeX прочтёт
            # как 10⁴·2 — в показатель уходит ТОЛЬКО первый символ. Молчаливая ошибка:
            # формула отрисуется красиво и будет означать другое число.
            body = re.sub(r"([_^])([A-Za-z0-9+\-]{2,4})(?![\w}])", r"\1{\2}", m.group(1))
            return "$" + body + "$"
        new2 = BARE.sub(wrap, new)
        if new2 != new:
            changed += 1
            new = new2
        out.append(new)
    return "".join(out), changed


def walk(node):
    """Правит строки в полях статьи, возвращает число правок."""
    n = 0
    if isinstance(node, dict):
        for k, v in list(node.items()):
            if isinstance(v, str) and k in FIELDS:
                new, c = fix_text(v)
                if c:
                    node[k] = new
                    n += c
            else:
                n += walk(v)
    elif isinstance(node, list):
        for v in node:
            n += walk(v)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--ids", nargs="*")
    args = ap.parse_args()

    paths = sorted((ROOT / "lang/ru/archive").glob("*/*/data.json"))
    if args.ids:
        want = set(args.ids)
        paths = [p for p in paths if p.parent.name in want]

    touched = fixes = 0
    shown = 0
    for p in paths:
        d = json.loads(p.read_text(encoding="utf-8"))
        before = json.dumps(d, ensure_ascii=False)
        n = 0
        for tier in TIERS:
            n += walk(d.get(tier, {}))
        if not n:
            continue
        touched += 1
        fixes += n
        after = json.dumps(d, ensure_ascii=False)
        if args.dry and shown < 5:
            shown += 1
            i = next((k for k in range(min(len(before), len(after))) if before[k] != after[k]), 0)
            print(f"\n{p.parent.name}:")
            print(f"  было:  …{before[max(0, i - 60):i + 60]}…")
            print(f"  стало: …{after[max(0, i - 60):i + 60]}…")
        if not args.dry:
            p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

    word = "нашлось" if args.dry else "починено"
    print(f"\n{word}: статей {touched}, правок {fixes} (просмотрено {len(paths)})")
    if args.dry:
        print("это черновой прогон — ничего не записано; убери --dry, чтобы применить")
    else:
        print("дальше: run.py html --only index (страницы соберутся заново, API не тратится)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
