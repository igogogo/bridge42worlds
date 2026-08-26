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
    # Дописано 2026-08-24 по итогу французского прогона: переводчик честно назвал три
    # подстрочника, которых не знал, и оставил их кириллицей в латинских формулах.
    # «Роша» — предел Роша (имя собственное, латиницей Roche), «рек» — реликтовое
    # излучение (в формулах мира это CMB), «экв» — эквивалентный.
    "Роша": "Roche", "рек": "CMB", "экв": "eq",
    # Единицы, у которых кириллическая буква ВЫГЛЯДИТ как латинская: ампер «А», вольт «В»,
    # ньютон «Н». На странице разницы не видно, а при копировании в поиск или в формулу
    # получается мусор — и не замечает этого никто и никогда. Поймано на французском курсе.
    "А": "A", "В": "V", "Кл": "C", "Ом": r"\Omega", "Тл": "T", "Ф": "F",
    # Стерадиан «ср» СОЗНАТЕЛЬНО не добавлен: этот ключ уже занят «средним» (ср → avg),
    # и переопределение молча испортило бы все средние величины курса ради одной единицы,
    # которая у нас нигде не встречается.
    "Вб": "Wb", "См": "S", "Гн": "H", "кд": "cd", "рад": "rad",
    # Единицы измерения. По всему сайту в формулах они латиницей на всех языках (в арабских
    # константах стоит «W / (m · K)»), поэтому здесь та же запись, а не арабские сокращения.
    "м": "m", "мм": "mm", "см": "cm", "км": "km", "нм": "nm", "мкм": r"\mu m",
    "с": "s", "мс": "ms", "ч": "h", "сут": "d", "кг": "kg", "г": "g",
    "Дж": "J", "кДж": "kJ", "МДж": "MJ", "эВ": "eV", "кэВ": "keV", "МэВ": "MeV",
    "Па": "Pa", "кПа": "kPa", "МПа": "MPa", "К": "K", "Вт": "W", "кВт": "kW",
    "Гц": "Hz", "кГц": "kHz", "МГц": "MHz", "Н": "N", "моль": "mol", "л": "L",
    "точн": "exact", "ш": "rough", "изм": "meas", "теор": "theor", "оп": "exp",
    # Фамилии внутри формул. Переводчику запрещено трогать формулы, поэтому подпись
    # «(Венцель)» под уравнением так и остаётся кириллицей на арабской странице —
    # ровно та же ловушка, что с подстрочниками, только заметнее глазу.
    "Венцель": "Wenzel", "Кассье": "Cassie", "Лаплас": "Laplace", "Юнг": "Young",
    "Стокс": "Stokes", "Пуазёйль": "Poiseuille", "Рейнольдс": "Reynolds",
    "Ван-дер-Ваальс": "van der Waals", "Майер": "Mayer", "Кориолис": "Coriolis",
    "Штейнер": "Steiner", "Фуко": "Foucault", "Эйлер": "Euler", "Максвелл": "Maxwell",
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


RUN = re.compile(r"[А-Яа-яЁё]+")


def fix_bare(s, where):
    """Голые обозначения: «А», «Ом·м», «Н/Кл = В/м», «Eк».

    fix() умеет только то, что стоит в \text{} или в подстрочнике после «_». А поля unit
    и часть sym записаны просто строкой: «А» — это ампер, и кириллическая «А» неотличима
    от латинской «A» на глаз. Здесь заменяем каждый кириллический кусок отдельно.

    Если кусок примыкает к латинской букве («Eк» — энергия кинетическая), ставим перед
    ним подчёркивание: «E_kin». Иначе вышло бы «Ekin» — слово, а не обозначение.
    """
    def r(m):
        w = m.group(0)
        if w not in MAP:
            unknown.setdefault(w, set()).add(where)
            return w
        pre = s[m.start() - 1] if m.start() else ""
        sep = "_" if pre.isalpha() and pre.isascii() else ""
        return sep + MAP[w]
    return RUN.sub(r, s)


INLINE = re.compile(r"\$[^$]{1,400}\$")


def fix_inline(s, where):
    """Формулы внутри прозы. Абзац может быть переведён целиком и честно, а внутри $...$
    сидеть $p_{\text{нас}}$ — та же кириллица в обозначении, только в тексте, а не в поле
    latex. Правим ТОЛЬКО то, что стоит между долларами: остальная проза не наше дело."""
    return INLINE.sub(lambda m: fix(m.group(0), where), s)


def walk(node, where):
    """Правит поля-обозначения (sym, latex) и формулы внутри прозы. Кириллица в самой прозе —
    это дыра перевода, её лечит другой инструмент, и подменять её латиницей было бы враньём."""
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if isinstance(v, str) and CYR.search(v) and k not in ("sym", "latex", "unit") and "$" in v:
                out[k] = fix_inline(v, where)
                continue
            # unit добавлен 24.08: единицы измерения — тоже обозначения, а не проза.
            # Французский прогон оставил «А» (ампер), «Н/Кл = В/м» — кириллические буквы,
            # визуально неотличимые от латинских. На странице это выглядит правильно, а
            # копирование в поиск или в формулу даёт мусор, и никто никогда не заметит.
            if k in ("sym", "latex", "unit") and isinstance(v, str) and CYR.search(v):
                nv = fix(v, where)
                # Второй заход по голым обозначениям: то, что не в фигурных скобках
                # и не в подстрочнике, первый проход не видит вовсе.
                if CYR.search(nv):
                    nv = fix_bare(nv, where)
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
