"""Переводит подписи внутри схем (js/figures.js) на en/es/ar.

Схемы идут к каждому шагу вывода формулы — 56 штук. Подписи на них рисуются прямо в SVG
и были только по-русски: англичанин, испанец и араб читали их кириллицей. Комментарий
в шапке файла это отрицал («SVG не требует перевода»), поэтому и не замечали.

Все подписи проходят через одну функцию `txt()`, поэтому перевод подставляется в ней —
править 148 мест не нужно. Здесь только собираем словарь и пишем `js/figures-i18n.js`.

    python tools/figures_i18n.py --check     сколько и какие
    python tools/figures_i18n.py --dry       перевести и показать
    python tools/figures_i18n.py             записать словарь
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import chat, clean_json, parse_json_salvage  # noqa: E402

SRC = Path("js/figures.js")
OUT = Path("js/figures-i18n.js")
LANGS = {"en": "English", "es": "Spanish", "ar": "Arabic"}
CYR = re.compile(r"[А-Яа-яЁё]")
LIT = re.compile(r"'([^']*)'|\"([^\"]*)\"")


def collect():
    """Русские строковые литералы из кода (без комментариев), в порядке появления."""
    out = []
    for line in SRC.read_text(encoding="utf-8").split("\n"):
        if re.match(r"\s*(//|\*|/\*)", line):
            continue
        line = re.sub(r"//.*$", "", line)
        for m in LIT.finditer(line):
            s = m.group(1) if m.group(1) is not None else m.group(2)
            if s and CYR.search(s) and s not in out:
                out.append(s)
    return out


PROMPT = """Translate these labels from a physics diagram into {lang}.

They are drawn inside schematic figures next to a formula derivation: short captions on
arrows, axes and objects. Keep them SHORT — they must fit on a small drawing.

Rules:
- Keep HTML entities (&#916; and similar), Latin symbols, digits and formulas EXACTLY as they are.
- Translate only the words. "Па = Н / м²" becomes "Pa = N / m²": units go to international symbols.
- Decimal comma becomes a decimal point for English and Spanish ("0,5 атм" -> "0.5 atm").
- Standard physics wording of {lang}-language textbooks, no explanations added.

Return STRICT JSON: an object mapping every input string to its translation, nothing else.

INPUT:
{payload}"""


def translate(strings, lang, retries=2):
    table, chunk, size = {}, [], 0

    def flush():
        nonlocal chunk, size
        if not chunk:
            return
        for _ in range(retries):
            try:
                r = chat("translate",
                         PROMPT.format(lang=LANGS[lang], payload=json.dumps(chunk, ensure_ascii=False)),
                         model="deepseek-v4-flash", max_tokens=16000)
                raw = r.choices[0].message.content or ""
                data = parse_json_salvage(raw) or json.loads(clean_json(raw))
                if isinstance(data, dict):
                    table.update({k: v for k, v in data.items() if isinstance(v, str) and v.strip()})
                    break
            except Exception as e:
                print(f"    ⚠️ {lang}: {e}")
        chunk, size = [], 0

    for s in strings:
        chunk.append(s)
        size += len(s)
        if size > 2200:
            flush()
    flush()
    return table


HEADER = """/* figures-i18n.js — подписи схем на четырёх языках.

   Схемы рисуются в js/figures.js, подписи на них были только по-русски: на английской,
   испанской и арабской версиях читатель видел кириллицу прямо на картинке. Ключ словаря —
   русская подпись как она написана в коде, поэтому промахнуться по смыслу нельзя.

   Подставляется в одной функции txt() — см. figures.js. Файл подключать ПЕРЕД figures.js.
   Собран tools/figures_i18n.py; после правки подписей в схемах прогнать его заново. */
window.B42FigText = """


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    strings = collect()
    print(f"подписей: {len(strings)}")
    if args.check:
        for s in strings[:40]:
            print("   " + s)
        return 0

    table = {}
    for lang in LANGS:
        got = translate(strings, lang)
        print(f"  {lang}: переведено {len(got)} из {len(strings)}")
        if args.dry:
            for k, v in list(got.items())[:6]:
                print(f"      «{k}» → «{v}»")
        for s in strings:
            if s in got:
                table.setdefault(s, {})[lang] = got[s]

    missing = [s for s in strings if len(table.get(s, {})) < len(LANGS)]
    if missing:
        print(f"  ⚠️ без полного перевода: {len(missing)}")
        for s in missing[:8]:
            print("      " + s)

    if not args.dry:
        OUT.write_text(HEADER + json.dumps(table, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
        print(f"записано: {OUT} ({len(table)} подписей)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
