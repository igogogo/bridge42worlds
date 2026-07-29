"""Убирает русский, оставшийся в переводах курса (en/es/ar).

Откуда взялся. Переводчик курса по инструкции не трогал формулы — и вместе с математикой
оставлял нетронутыми русские слова внутри `\\text{…}`: читатель-англичанин видел
`E_{\\text{иониз}}`. Заодно непереведёнными остались названия законов и куски текста.
Причина закрыта в промпте `course_translate.py`; этот скрипт убирает уже накопленное.

Почему точечно, а не повторным переводом всего курса: правки хирургические и проверяемые —
собираем СПИСОК РАЗНЫХ русских строк, переводим его одним запросом на язык и подставляем
обратно. Дёшево, и видно ровно то, что изменилось.

    python tools/fix_leak.py --check          что найдено, без запросов к модели
    python tools/fix_leak.py --langs en       только английский
    python tools/fix_leak.py --dry            перевести и показать, но не записывать
    python tools/fix_leak.py                  сделать
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import chat, clean_json, parse_json_salvage  # noqa: E402

ROOT = Path("data/theory/courses")
LANGS = ["en", "es", "ar"]
LANG_NAME = {"en": "English", "es": "Spanish", "ar": "Arabic"}
CYR = re.compile(r"[А-Яа-яЁё]")
TEXT_CMD = re.compile(r"\\(?:text|mathrm)\{([^{}]*)\}")


def is_formula_field(path):
    return re.search(r"(^|\.)(latex|eq|plate)($|\[)", path) is not None


# Единицы, набранные кириллицей ПРОСТЫМ текстом (вне \text{…}): в переводах они должны стоять
# международными обозначениями. Заменяем механически — тут нечего решать модели, и результат
# проверяем глазами. Работает и внутри составных: «кг·м/с²» → «kg·m/s²», «Дж/(мол·К)» → «J/(mol·K)».
UNITS = {
    "м": "m", "с": "s", "кг": "kg", "г": "g", "т": "t", "мг": "mg",
    "км": "km", "см": "cm", "мм": "mm", "мкм": "µm", "нм": "nm", "пм": "pm",
    "Дж": "J", "кДж": "kJ", "МДж": "MJ", "эВ": "eV", "кэВ": "keV", "МэВ": "MeV", "ГэВ": "GeV",
    "Н": "N", "кН": "kN", "Па": "Pa", "кПа": "kPa", "МПа": "MPa", "атм": "atm", "бар": "bar",
    "Вт": "W", "кВт": "kW", "МВт": "MW", "В": "V", "кВ": "kV", "мВ": "mV", "мВт": "mW",
    "А": "A", "мА": "mA", "Ом": "Ω", "кОм": "kΩ", "Кл": "C", "Ф": "F", "Тл": "T", "Вб": "Wb",
    "К": "K", "Гц": "Hz", "кГц": "kHz", "МГц": "MHz", "ГГц": "GHz",
    "моль": "mol", "мол": "mol", "рад": "rad", "ср": "sr",
    "л": "L", "мл": "mL", "ч": "h", "мин": "min", "мс": "ms", "мкс": "µs", "нс": "ns",
    "лет": "yr", "год": "yr", "года": "yr",
}
CYR_RUN = re.compile(r"[А-Яа-яЁё]+")


def fix_units(s):
    """Меняет кириллические обозначения единиц на международные. Слова не трогает."""
    return CYR_RUN.sub(lambda m: UNITS.get(m.group(0), m.group(0)), s)


def rest_after_math(s):
    """Что останется от строки, если убрать всю математику: `$…$` и содержимое \\text{…}."""
    return TEXT_CMD.sub("", re.sub(r"\$[^$]*\$", "", s))


def collect(node, path, out):
    """Складывает найденные русские куски по видам.

    Подписи внутри \\text{…} собираем из ЛЮБЫХ полей: формула встречается и в `law`, и в тексте.
    Целиком строку берём только если она без математики — иначе модель, переводя, поломает LaTeX.
    Смешанные («формула + русские слова вокруг») откладываем в 'mixed' на ручной разбор."""
    if isinstance(node, str):
        if not CYR.search(node):
            return
        for inner in TEXT_CMD.findall(node):
            if CYR.search(inner):
                out.setdefault("label", set()).add(inner)
        rest = rest_after_math(node)
        if not CYR.search(rest):
            return                                  # весь русский сидел в подписях — уже собран
        if "$" in node or "\\" in node:
            out.setdefault("mixed", set()).add(node)
        elif path.endswith(".law"):
            out.setdefault("law", set()).add(node)
        else:
            out.setdefault("prose", set()).add(node)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            collect(v, f"{path}[{i}]", out)
    elif isinstance(node, dict):
        for k, v in node.items():
            collect(v, f"{path}.{k}", out)


def apply(node, path, table):
    """Подставляет перевод. Внутри формул меняем только содержимое \\text{…}."""
    if isinstance(node, str):
        if not CYR.search(node):
            return node, 0
        # строку целиком заменяем только если она попала в словарь как есть (текст без формул)
        whole = table.get(node)
        if whole and whole != node:
            return whole, 1
        n = 0

        def sub(m):
            nonlocal n
            inner = m.group(1)
            repl = table.get(inner)
            if repl and repl != inner:
                n += 1
                return m.group(0).replace("{" + inner + "}", "{" + repl + "}")
            return m.group(0)
        return TEXT_CMD.sub(sub, node), n
    if isinstance(node, list):
        total = 0
        for i, v in enumerate(node):
            node[i], k = apply(v, f"{path}[{i}]", table)
            total += k
        return node, total
    if isinstance(node, dict):
        total = 0
        for k, v in node.items():
            node[k], c = apply(v, f"{path}.{k}", table)
            total += c
        return node, total
    return node, 0


PROMPT = """You are fixing a localisation bug in a physics course. The strings below are Russian
fragments that were left untranslated in the {lang} version. Translate every one of them into {lang}.

Context of each kind:
- "label": a short label that sits INSIDE a formula, usually a subscript (e.g. "иониз" is the
  subscript of ionisation energy). Keep it SHORT, the way a physicist writes a subscript in
  {lang}. Units must become the international symbols: м→m, с→s, кг→kg, Дж→J, Н→N, Вт→W, В→V,
  А→A, Кл→C, К→K, Гц→Hz, эВ→eV, МэВ→MeV, моль→mol.
- "law": the name of a physical law or effect — use the standard name in {lang}
  ("Закон Ома" → "Ohm's law").
- "prose": ordinary sentences or captions.

Rules:
- Standard physics terminology of {lang}-language textbooks.
- Do NOT add explanations, keep the register and the length close to the original.
- Keep any LaTeX, digits and Latin symbols exactly as they are.

Return STRICT JSON: an object mapping every input string to its translation, nothing else.

INPUT ({kind}):
{payload}"""


def translate(strings, lang, kind, retries=2):
    """Список строк → словарь {оригинал: перевод}. Режем на части, чтобы ответ не обрывался."""
    table, chunk, size = {}, [], 0
    def flush():
        nonlocal chunk, size
        if not chunk:
            return
        for _ in range(retries):
            try:
                r = chat("translate",
                         PROMPT.format(lang=LANG_NAME[lang], kind=kind,
                                       payload=json.dumps(chunk, ensure_ascii=False)),
                         model="deepseek-v4-flash", max_tokens=16000)
                raw = r.choices[0].message.content or ""
                data = parse_json_salvage(raw) or json.loads(clean_json(raw))
                if isinstance(data, dict):
                    table.update({k: v for k, v in data.items() if isinstance(v, str) and v.strip()})
                    break
            except Exception as e:
                print(f"    ⚠️ {kind}/{lang}: {e}")
        chunk, size = [], 0

    for s in strings:
        chunk.append(s)
        size += len(s)
        if size > 3000:
            flush()
    flush()
    return table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", default=",".join(LANGS))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--units", action="store_true",
                    help="только механическая замена единиц, без обращения к модели")
    args = ap.parse_args()
    langs = [l for l in args.langs.split(",") if l in LANGS]

    if args.units:
        total = 0
        for f in sorted(ROOT.rglob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            n = 0

            def walk_units(node):
                nonlocal n
                if isinstance(node, str):
                    fixed = fix_units(node)
                    if fixed != node:
                        n += 1
                    return fixed
                if isinstance(node, list):
                    return [walk_units(v) for v in node]
                if isinstance(node, dict):
                    return {k: walk_units(v) for k, v in node.items()}
                return node

            for lang in langs:
                if lang in data:
                    data[lang] = walk_units(data[lang])
            if n:
                total += n
                print(f"    {f.relative_to(ROOT)}: {n}")
                if not args.dry:
                    f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(("НАШЛОСЬ" if args.dry else "ЗАМЕНЕНО") + f": {total}")
        return 0

    files = sorted(f for f in ROOT.rglob("*.json"))
    found = {l: {} for l in langs}
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        for lang in langs:
            if lang not in data:
                continue
            out = {}
            collect(data[lang], "", out)
            for kind, vals in out.items():
                found[lang].setdefault(kind, set()).update(vals)

    for lang in langs:
        kinds = found[lang]
        print(f"{lang}: " + ", ".join(f"{k} {len(v)}" for k, v in sorted(kinds.items())) or f"{lang}: чисто")
    if args.check:
        for lang in langs:
            for kind, vals in sorted(found[lang].items()):
                print(f"  --- {lang}/{kind} ---")
                for v in sorted(vals)[:12]:
                    print("      " + v[:90])
        return 0

    tables = {}
    for lang in langs:
        tables[lang] = {}
        for kind, vals in sorted(found[lang].items()):
            if kind == "mixed":
                print(f"  {lang}/mixed: {len(vals)} — не трогаю, там формула вперемешку с текстом")
                continue
            print(f"  перевожу {lang}/{kind}: {len(vals)}")
            got = translate(sorted(vals), lang, kind)
            if args.dry:
                for k, v in list(got.items())[:12]:
                    print(f"      «{k[:50]}» → «{v[:50]}»")
            tables[lang].update(got)

    total = 0
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        before = json.dumps(data, ensure_ascii=False)
        n = 0
        for lang in langs:
            if lang in data:
                data[lang], k = apply(data[lang], "", tables[lang])
                n += k
        if n and not args.dry:
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if n:
            total += n
            print(f"    {f.relative_to(ROOT)}: {n}")
        _ = before
    print(("НАШЛОСЬ" if args.dry else "ЗАМЕНЕНО") + f": {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
