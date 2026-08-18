# -*- coding: utf-8 -*-
"""Кириллические подстрочники в переводах — на международную запись.

Зачем. Переводчику велено не трогать формулы, и он их не трогает: в английской версии остаётся
$\\rho_{\\text{в}}$ и $p_{\\text{нас}}$. Читатель видит кириллицу внутри формулы, а детектор
пробелов видит кириллицу в блоке и ставит блок в очередь на перевод — снова и снова, каждый прогон,
за деньги, без всякой надежды сойтись: перевести это переводчик не может по инструкции.

Что делает: в НЕрусских ветках заменяет известные русские подстрочники на общепринятые
международные ($\\rho_{\\text{w}}$, $p_{\\text{sat}}$). Русскую ветку не трогает — там читателю
привычнее свои буквы. Неизвестные подстрочники не выдумывает, а печатает списком: их надо
разобрать руками и дописать в словарь.

    python tools/symbols_latin.py            разбор
    python tools/symbols_latin.py --apply    заменить
"""
import glob
import io
import json
import re
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LANGS = ("en", "es", "ar", "fr")

# Русский подстрочник → международный. Выбор простой: если у величины есть общепринятое
# латинское обозначение — берём его (ртуть Hg, насыщение sat), иначе первую букву слова
# на английском (вода w, лаборатория lab).
MAP = {
    "в": "w", "вода": "w", "рт": "Hg", "кам": "rock", "возд": "air", "ж": "f", "т": "s",
    "нас": "sat", "кол": "vib", "вр": "rot", "пост": "tr", "ср": "avg", "скв": "rms",
    "макс": "max", "мин": "min", "кр": "cr", "к": "kin", "п": "pot", "мол": "mol",
    "вых": "out", "вх": "in", "нул": "0", "лаб": "lab", "соб": "0", "б": "beat",
    "вид": "vis", "иониз": "ion", "заж": "ign", "прил": "tid", "зв": "s", "общ": "tot",
    "эфф": "eff", "нач": "i", "кон": "f", "пов": "surf", "об": "vol", "уд": "sp",
    # Единицы измерения. По всему сайту в формулах они латиницей на всех языках (в арабских
    # константах стоит «W / (m · K)»), поэтому здесь та же запись, а не арабские сокращения.
    "м": "m", "мм": "mm", "см": "cm", "км": "km", "нм": "nm", "мкм": r"\mu m",
    "с": "s", "мс": "ms", "ч": "h", "сут": "d", "кг": "kg", "г": "g",
    "Дж": "J", "кДж": "kJ", "МДж": "MJ", "эВ": "eV", "кэВ": "keV", "МэВ": "MeV",
    "Па": "Pa", "кПа": "kPa", "МПа": "MPa", "К": "K", "Вт": "W", "кВт": "kW",
    "Гц": "Hz", "кГц": "kHz", "МГц": "MHz", "Н": "N", "моль": "mol", "л": "L",
}

TEXT = re.compile(r"\\text\{([А-Яа-яЁё]+)\}")
SUBS = re.compile(r"_\{?([А-Яа-яЁё]+)\}?")
CYR = re.compile(r"[А-Яа-яЁё]")

unknown = {}
changed_examples = []


def fix(s, where):
    """Заменяет известные подстрочники; неизвестные копит для отчёта."""
    def t(m):
        w = m.group(1)
        if w in MAP:
            return "\\text{%s}" % MAP[w]
        unknown.setdefault(w, set()).add(where)
        return m.group(0)

    def u(m):
        w = m.group(1)
        if w in MAP:
            return "_{%s}" % MAP[w]
        unknown.setdefault(w, set()).add(where)
        return m.group(0)

    out = TEXT.sub(t, s)
    out = SUBS.sub(u, out)
    return out


def walk(node, where):
    """Правит только поля-обозначения: sym и latex. В прозе кириллица — это дыра перевода,
    её лечит другой инструмент, и подменять её латиницей было бы враньём."""
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k in ("sym", "latex") and isinstance(v, str) and CYR.search(v):
                nv = fix(v, where)
                if nv != v and len(changed_examples) < 12:
                    changed_examples.append((where, v[:60], nv[:60]))
                out[k] = nv
            else:
                out[k] = walk(v, where)
        return out
    if isinstance(node, list):
        return [walk(v, where) for v in node]
    return node


def branches(d):
    if isinstance(d.get("ru"), dict):
        return {"": d}
    return {k: v for k, v in d.items() if isinstance(v, dict) and isinstance(v.get("ru"), dict)}


def main():
    apply = "--apply" in sys.argv
    files, seen = [], set()
    for pat in ("data/theory/courses/*/*.json", "data/theory/*.json"):
        for f in glob.glob(pat):
            if f not in seen:
                seen.add(f)
                files.append(f)

    touched = 0
    for f in sorted(files):
        raw = io.open(f, encoding="utf-8", newline="").read()
        nl = "\r\n" if "\r\n" in raw else "\n"
        try:
            d = json.loads(raw)
        except Exception:
            continue
        before = json.dumps(d, ensure_ascii=False, sort_keys=True)
        for owner, br in branches(d).items():
            for lang in LANGS:
                if isinstance(br.get(lang), dict):
                    br[lang] = walk(br[lang], "%s %s" % (f.replace("\\", "/").split("courses/")[-1], lang))
        after = json.dumps(d, ensure_ascii=False, sort_keys=True)
        if before != after:
            touched += 1
            if apply:
                io.open(f, "w", encoding="utf-8", newline=nl).write(
                    json.dumps(d, ensure_ascii=False, indent=1) + "\n")

    for where, a, b in changed_examples:
        print("  %-44s %s → %s" % (where, a, b))
    print("файлов с кириллицей в обозначениях перевода: %d%s" % (touched, " (заменено)" if apply else ""))
    if unknown:
        print("НЕИЗВЕСТНЫЕ подстрочники — дописать в словарь и прогнать снова:")
        for w, where in sorted(unknown.items()):
            print("   %-12s %s" % (w, list(where)[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
