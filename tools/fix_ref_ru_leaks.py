#!/usr/bin/env python3
"""Чистка трёх старых утечек русского в справочниках НЕрусских языков.

Найдено 2026-07-30 при добавлении французского (свежий язык высветил дыры,
жившие во всех языках): en 52, es 66, ar 85, fr 70 строк с кириллицей.

1. Русские подписи ВНУТРИ latex (\\text{эВ}, f_{набл}, «up-тип») — правило
   «latex не трогаем» защищало формулу и консервировало русский. Чиним словарём
   научных обозначений — детерминированно, формулы не трогаются ничем, кроме
   точных замен подписей.
2. lifespan «1947–н.в.» / «настоящее время» — по языку.
3. type: «уравнение» и другие русские значения служебных полей — по языку.

Запуск: python tools/fix_ref_ru_leaks.py [--dry]
"""
import io
import json
import re
import sys
from pathlib import Path

DRY = "--dry" in sys.argv
# Русский справочник — ИСТОЧНИК утечки в формулах: latex не переводится, он копируется
# во все языки как есть. Пока русские подписи стоят в ru, любая перегенерация переводов
# возвращает их обратно в en/es/ar/fr. С --with-ru чиним и русский, но только latex:
# lifespan и type там по-русски законно.
WITH_RU = "--with-ru" in sys.argv
ROOT = Path(__file__).resolve().parent.parent
LANGS = [d.name for d in (ROOT / "lang").iterdir()
         if d.is_dir() and (d.name != "ru" or WITH_RU) and (d / "data").exists()]

# — научные обозначения: безопасны во всех языках (международная нотация) —
LATEX_MAP = {
    "эВ": "eV", "кэВ": "keV", "МэВ": "MeV", "ГэВ": "GeV", "ТэВ": "TeV",
    "Гс": "G", "Тл": "T", "Дж": "J", "кДж": "kJ", "эрг": "erg",
    "МГц": "MHz", "ГГц": "GHz", "кГц": "kHz", "Гц": "Hz",
    "км/с": "km/s", "м/с": "m/s", "св.лет": "ly", "пк": "pc", "Мпк": "Mpc",
    "набл": "obs", "ист": "src", "нач": "i", "кон": "f",
    "ядра": "nucl", "яд": "nucl", "макс": "max", "мин": "min",
    "среднее": "avg", "ср": "avg", "эфф": "eff", "крит": "crit",
    "при ": "at ", "или": "or", "и ": "and ",
    "up-тип": "up-type", "down-тип": "down-type",
    # — добор 2026-07-30 (промпт-инженер): остаток первого прохода, разобран поштучно —
    # Индексы величин. Замены идут от длинных ключей к коротким (см. fix_latex),
    # поэтому «св.лет» отрабатывает раньше, чем «св».
    "св": "b", "пор": "th", "инерт": "inert", "гравит": "grav",
    "лин": "lin", "кв": "quad", "выт": "buoy",
    "Земли": "Earth", "Луны": "Moon", "Солнца": "Sun",
    # Куски фраз внутри \text{} — встречаются в математических формулировках.
    "такое, что": "such that", "такое что": "such that",
    "для бесконечно многих": "for infinitely many",
    "для всех": "for all", "существует": "there exists",
    "почти наверное": "almost surely",
    "сходится равномерно на": "converges uniformly on",
}
PRESENT = {"en": "present", "es": "presente", "fr": "aujourd'hui",
           "ar": "حتى الآن", "zh": "至今"}
TYPE_MAP = {
    "уравнение": {"en": "equation", "es": "ecuación", "fr": "équation", "ar": "معادلة"},
    "принцип":   {"en": "principle", "es": "principio", "fr": "principe", "ar": "مبدأ"},
    "закон":     {"en": "law", "es": "ley", "fr": "loi", "ar": "قانون"},
    "постоянная": {"en": "constant", "es": "constante", "fr": "constante", "ar": "ثابت"},
    "эффект":    {"en": "effect", "es": "efecto", "fr": "effet", "ar": "تأثير"},
}
CYR = re.compile(r"[а-яА-ЯёЁ]")


def fix_latex(s):
    """Замены по границам слова. Голый str.replace здесь опасен: ключ «и » превращал
    «почти наверное» в «почтand наверное» (поймано на доборе 30 июля). Ключи со знаками
    (св.лет, км/с, up-тип, «при ») остаются буквальными — границы им не нужны."""
    if not CYR.search(s):
        return s, 0
    n = 0
    for ru, lat in sorted(LATEX_MAP.items(), key=lambda kv: -len(kv[0])):
        if ru not in s:
            continue
        if ru.strip().isalpha():
            new = re.sub(rf"(?<![А-Яа-яЁё]){re.escape(ru)}(?![А-Яа-яЁё])", lat, s)
        else:
            new = s.replace(ru, lat)
        if new != s:
            s = new
            n += 1
    return s, n


def process(lang):
    fixed = left = 0
    for fname in ("tags", "laws", "scientists"):
        p = ROOT / "lang" / lang / "data" / f"{fname}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        changed = False

        def walk(node):
            nonlocal changed, fixed, left
            if isinstance(node, dict):
                for k, v in list(node.items()):
                    if isinstance(v, str):
                        new = v
                        if k in ("latex", "meaning") or "\\" in v:
                            new, n = fix_latex(v)
                            fixed += n
                        if lang == "ru":
                            # в русском справочнике чиним ТОЛЬКО формулы: подпись «н.в.»
                            # и тип «уравнение» там на своём месте
                            if new != v:
                                node[k] = new
                                changed = True
                            continue
                        if k == "lifespan" and CYR.search(new):
                            new = re.sub(r"(настоящее время|наст\.? ?время|н\.? ?в\.?)",
                                         PRESENT.get(lang, "present"), new)
                            fixed += 1
                        if k == "type" and new in TYPE_MAP:
                            new = TYPE_MAP[new].get(lang, TYPE_MAP[new]["en"])
                            fixed += 1
                        if new != v:
                            node[k] = new
                            changed = True
                        if CYR.search(node[k] if isinstance(node[k], str) else ""):
                            left += 1
                    else:
                        walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(d)
        if changed and not DRY:
            p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    return fixed, left


for lang in sorted(LANGS):
    fixed, left = process(lang)
    print(f"{lang}: заменено {fixed}, осталось строк с кириллицей {left}"
          + (" [dry]" if DRY else ""))
