#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Раздел /concepts/: страницы понятий волны 5 и облако с группами.

Владелец 26 августа: «да, делай применение и вторую сборку». Реестр applied через
tools/wave5_apply.py (data/concepts-live.json); здесь из него растут страницы.

ЧТО СТРОИТСЯ на каждый язык:
    /lang/{lang}/concepts/{id}.html   страница понятия: карточка, статьи по разметке
                                      v2, соседи по весу, учёные, формулы двумя ярусами
    /lang/{lang}/concepts/index.html  облако: 50 групп, внутри — понятия по опоре

ЯЗЫК. Название — перевод из старых справочников, где есть (526 понятий); у новых
названий и у всех карточек текст пока английский с пометкой lang="en" — владелец:
«пока на английском, переводы потом». Разметка от языка не зависит.

СТАРЫЕ РАЗДЕЛЫ /tags/ и /laws/ НЕ ТРОГАЮТСЯ этой сборкой: они работают как работали,
переезд с редиректами — решение к публикации, не к локальному смотру.

ВЕС. Урок STATIC_CARDS_CAP выучен до начала: вшиваем максимум 40 карточек статей,
счётчик показывает полное число.

    python concepts_pages.py            все языки
    python concepts_pages.py --lang ru  один язык
"""
import sys as _s
from pathlib import Path as _P
_s.path.insert(0, str(_P(__file__).resolve().parent))
from tools import runlock as _lock
import argparse
import html as H
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE = ROOT / "data" / "concepts-live.json"
# ЯЗЫКИ ПО НАЛИЧИЮ ПЕРЕВОДА (владелец 27.08: «по понятиям будет русский и
# английский… но у части есть, у части нет — что есть, не удалять»).
# ru и en — всегда: русский переведён у всех 3231, английский это язык
# карточек. es/ar/fr — страница собирается ТОЛЬКО тем понятиям, у которых на
# этом языке реально есть перевод (имя или текст старого справочника: таких
# 529); остальным на этих языках отдаётся редирект на английскую версию,
# чтобы ссылка была живой, а не 404.
from common import ALL_LANGS  # noqa: E402
LANGS = ALL_LANGS   # список языков один на проект: config.json через common.ALL_LANGS
ALWAYS_LANGS = ("ru", "en")
CARDS_CAP = 40

sys.path.insert(0, str(ROOT))
import generate as G   # entity_article_card, load_index — свои карточки, не вторая копия

KIND_LBL = {
    "ru": {"concept": "понятие", "object": "объект", "method": "метод", "instrument": "прибор",
           "substance": "вещество", "math": "математика", "phenomenon": "явление",
           "law": "закон", "equation": "уравнение", "effect": "эффект", "principle": "принцип",
           "theorem": "теорема", "process": "процесс", "property": "свойство", "theory": "теория",
           "quantity": "величина", "constant": "константа", "unit": "единица",
           "unit_system": "система единиц", "statistics": "статистика"},
    "es": {"concept": "concepto", "object": "objeto", "method": "método", "instrument": "instrumento",
           "substance": "sustancia", "math": "matemáticas", "phenomenon": "fenómeno",
           "law": "ley", "equation": "ecuación", "effect": "efecto", "principle": "principio",
           "theorem": "teorema", "process": "proceso", "property": "propiedad", "theory": "teoría",
           "quantity": "magnitud", "constant": "constante", "unit": "unidad",
           "unit_system": "sistema de unidades", "statistics": "estadística"},
    "fr": {"concept": "concept", "object": "objet", "method": "méthode", "instrument": "instrument",
           "substance": "substance", "math": "mathématiques", "phenomenon": "phénomène",
           "law": "loi", "equation": "équation", "effect": "effet", "principle": "principe",
           "theorem": "théorème", "process": "processus", "property": "propriété", "theory": "théorie",
           "quantity": "grandeur", "constant": "constante", "unit": "unité",
           "unit_system": "système d'unités", "statistics": "statistique"},
    "ar": {"concept": "مفهوم", "object": "جسم", "method": "طريقة", "instrument": "جهاز",
           "substance": "مادة", "math": "رياضيات", "phenomenon": "ظاهرة",
           "law": "قانون", "equation": "معادلة", "effect": "تأثير", "principle": "مبدأ",
           "theorem": "مبرهنة", "process": "عملية", "property": "خاصية", "theory": "نظرية",
           "quantity": "كمية", "constant": "ثابت", "unit": "وحدة",
           "unit_system": "نظام وحدات", "statistics": "إحصاء"},
}
SEC = {
    "ru": {"desc": "Описание", "history": "История", "how": "Как это работает",
           "practical": "Где применяется", "fact": "Любопытный факт"},
    "en": {"desc": "Description", "history": "History", "how": "How it works",
           "practical": "In practice", "fact": "Fun fact"},
    "es": {"desc": "Descripción", "history": "Historia", "how": "Cómo funciona",
           "practical": "En la práctica", "fact": "Dato curioso"},
    "ar": {"desc": "الوصف", "history": "التاريخ", "how": "كيف يعمل",
           "practical": "في التطبيق", "fact": "حقيقة طريفة"},
    "fr": {"desc": "Description", "history": "Histoire", "how": "Comment ça marche",
           "practical": "En pratique", "fact": "Anecdote"},
}
T = {
    "ru": {"title": "Понятия", "sub": "Реестр понятий: {n} записей в {g} группах. Карточки новых понятий пока на английском — переводы в работе.",
           "articles": "Статьи по теме", "related": "Рядом стоят", "sci": "Кто здесь работал",
           "formulas": "Формулы", "uses": "применений", "none": "Статей пока нет",
           "en_note": "перевод готовится", "of": "из"},
    "en": {"title": "Concepts", "sub": "Concept registry: {n} entries in {g} groups.",
           "articles": "Related articles", "related": "Nearby", "sci": "Who worked here",
           "formulas": "Formulas", "uses": "uses", "none": "No articles yet",
           "en_note": "", "of": "of"},
    "es": {"title": "Conceptos", "sub": "Registro de conceptos: {n} entradas en {g} grupos. Las fichas nuevas están en inglés — traducción en curso.",
           "articles": "Artículos relacionados", "related": "Cercanos", "sci": "Quién trabajó aquí",
           "formulas": "Fórmulas", "uses": "usos", "none": "Aún no hay artículos",
           "en_note": "traducción en curso", "of": "de"},
    "ar": {"title": "المفاهيم", "sub": "سجل المفاهيم: {n} مدخلاً في {g} مجموعة. البطاقات الجديدة بالإنجليزية مؤقتاً.",
           "articles": "مقالات ذات صلة", "related": "قريب منه", "sci": "من عمل هنا",
           "formulas": "صيغ", "uses": "تطبيقات", "none": "لا مقالات بعد",
           "en_note": "الترجمة قيد الإعداد", "of": "من"},
    "fr": {"title": "Concepts", "sub": "Registre des concepts : {n} entrées en {g} groupes. Les fiches récentes sont en anglais — traduction en cours.",
           "articles": "Articles liés", "related": "À proximité", "sci": "Qui a travaillé ici",
           "formulas": "Formules", "uses": "usages", "none": "Pas encore d'articles",
           "en_note": "traduction en cours", "of": "sur"},
}


_CHROME = {}


def site_chrome(lang):
    """Шапка сайта и футер — ВЫРЕЗАЮТСЯ ИЗ ЖИВОГО ШАБЛОНА templates/law.html,
    а не рисуются здесь заново.

    Владелец 27.08: «я вообще против этого меню, у нас было всё сразу… много
    функционала упущено — дизайн может быть другим, но функционал тот же».
    Своё меню из четырёх ссылок теряло поиск, избранное, учебник, языки,
    кнопку «ещё» и футер. Копия разъехалась бы с сайтом на первой же правке
    шапки — поэтому берём разметку оттуда, где она живёт."""
    if lang in _CHROME:
        return _CHROME[lang]
    tpl = (ROOT / "templates" / "law.html").read_text(encoding="utf-8")
    i = tpl.index('<div class="top-bar">')
    j = tpl.index('<div class="langs" id="langs-bar"></div>') + len(
        '<div class="langs" id="langs-bar"></div>')
    bar = tpl[i:j]
    UI = {"ru": ("Избранное", "Поиск статей…", "@ автор · # понятие · ! учёный"),
          "en": ("Favorites", "Search articles…", "@ author · # concept · ! scientist"),
          "es": ("Favoritos", "Buscar artículos…", "@ autor · # concepto · ! científico"),
          "ar": ("المفضلة", "ابحث عن مقالات…", "@ مؤلف · # مفهوم · ! عالم"),
          "fr": ("Favoris", "Rechercher…", "@ auteur · # concept · ! scientifique")}
    fav, ph, hint = UI.get(lang, UI["en"])
    bar = (bar.replace("$lang", lang)
              .replace("$fav_title", H.escape(fav))
              .replace("$search_placeholder", H.escape(ph))
              .replace("$search_hint", H.escape(hint))
              .replace("$law_version_toggle", ""))
    # «concepts» в шапке ведёт в наш раздел, а не в старые /laws/
    bar = bar.replace(f'/lang/{lang}/laws/', f'/lang/{lang}/concepts/')
    foot = "<footer><p>bridge42worlds</p></footer>"
    # b42-card — всплывающая карточка понятия: клик по подсвеченному слову
    # показывает определение прямо в тексте, с кнопками «подробно» и «закрыть».
    scripts = (f'<script src="{av("/js/b42-card.js")}" defer></script>'
               f'<script src="{av("/js/likes.js")}"></script>'
               f'<script src="{av("/js/icons.js")}"></script>'
               f'<script src="{av("/js/search.js")}"></script>'
               f'<script src="{av("/js/site-search.js")}"></script>'
               f'<script src="{av("/js/search-ui.js")}"></script>'
               f'<script src="{av("/js/sitenav.js")}" defer></script>')
    _CHROME[lang] = (bar, foot, scripts)
    return _CHROME[lang]


def av(path):
    """Метка версии файла для адреса скрипта/стиля. Без неё браузер держит
    старую копию: 27.08 страница графа грузила вчерашний b42-graph.js, и
    тач-управление «не работало», хотя код был на месте. Остальной сайт давно
    ходит с asset_ver — здесь его не было."""
    f = ROOT / path.lstrip("/")
    try:
        return f"{path}?v={int(f.stat().st_mtime):x}"
    except OSError:
        return path


SITE = "https://bridge42worlds.academy"


def _desc(text, limit=175):
    """Описание для выдачи: до конца предложения, а не по середине слова.

    Google обрежет своё на ~160 знаках, но обрежет грубо. Лучше закончить мысль."""
    t = " ".join(str(text or "").split())
    if len(t) <= limit:
        return t
    cut = t[:limit]
    for sep in (". ", "! ", "? "):
        i = cut.rfind(sep)
        if i > limit * 0.5:
            return cut[:i + 1]
    i = cut.rfind(" ")
    return (cut[:i] if i > 0 else cut) + "…"


def _seo(canon, alts, desc):
    """canonical + hreflang + описание.

    Страницы понятий строились без единого из этих тегов: charset, viewport, title —
    и всё. Отчёт Google за 31 августа объяснил, чем это кончилось: в выборке из тысячи
    проиндексированных адресов страниц понятий — НОЛЬ, при том что их 3 616 на язык и
    это самый долгоживущий наш текст. Пять языковых версий по одному адресу-близнецу,
    без canonical, без взаимных ссылок и без описания читаются поисковиком как пять
    копий неизвестно чего. Статья такое имеет с самого начала — здесь просто забыли.
    """
    if not canon:
        return ""
    rows = []
    if desc:
        d = H.escape(_desc(desc), quote=True)
        rows.append(f'<meta name="description" content="{d}">')
        rows.append(f'<meta property="og:description" content="{d}">')
    rows.append(f'<link rel="canonical" href="{SITE}{canon}">')
    here = "/lang/" + lang_of(canon) + "/"

    def other(l):
        return SITE + canon.replace(here, "/lang/" + l + "/", 1)

    for l in (alts or []):
        rows.append(f'<link rel="alternate" hreflang="{l}" href="{other(l)}">')
    if alts:
        # x-default ведёт на русскую версию: русский у нас исходный, остальные —
        # переводы с него, и читателю без подходящего языка честнее показать её.
        # Если русской нет (понятие пока только по-английски), ведём на первую
        # существующую: отправлять в переадресацию — тратить обход впустую.
        rows.append('<link rel="alternate" hreflang="x-default" '
                    f'href="{other("ru" if "ru" in alts else alts[0])}">')
    return "".join(r + chr(10) for r in rows)


def lang_of(path):
    """Язык из адреса вида /lang/ar/concepts/x.html."""
    parts = str(path).split("/")
    return parts[2] if len(parts) > 2 and parts[1] == "lang" else "ru"


def head(lang, title, body_class="entity-page", page_langs=None,
         canon="", alts=None, desc=""):
    d = "rtl" if lang == "ar" else "ltr"
    return f"""<!DOCTYPE html>
<html lang="{lang}" dir="{d}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{H.escape(title)} — bridge42worlds</title>
{_seo(canon, alts, desc)}<meta property="og:title" content="{H.escape(title, quote=True)}">
<meta property="og:type" content="article">
<meta name="twitter:card" content="summary">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:opsz@14..32&family=Source+Serif+4:opsz@8..60&family=Noto+Naskh+Arabic:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
        onload="renderMathInElement(document.body, {{output: 'html', delimiters: [
          {{left: '$$', right: '$$', display: true}},
          {{left: '\\\\(', right: '\\\\)', display: false}}]}})"></script>
<link rel="stylesheet" href="{av("/css/style.css")}">
<link rel="icon" href="/favicon.ico" sizes="any">
</head>
<body class="{body_class}" data-langs="{','.join(page_langs or LANGS)}">
{site_chrome(lang)[0]}
"""


def name_of(c, cid, lang):
    return c["names"].get(lang) or c["names"].get("en") or cid.replace("_", " ")


def load_rich(lang):
    """Старые справочники языка: полные описания 527 переживших понятий."""
    rich = {}
    for fname in ("tags.json", "laws.json"):
        p = ROOT / "lang" / lang / "data" / fname
        if not p.exists():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for cid, v in d.items():
            if isinstance(v, dict):
                rich.setdefault(cid, v)
    return rich


import re as _re


def _stem(w):
    """Основа слова тем же духом, что sameWord в js/site-search.js: не меньше
    четырёх букв, окончание отбрасывается. Второй морфологии в проекте не заводим."""
    w = w.lower()
    return w[: max(4, len(w) - 2)] if len(w) > 5 else w


def autolink(html_text, cid, lang, live):
    """Первые вхождения названий соседних понятий в тексте → ссылки.

    html_text уже экранирован (H.escape) — работаем по тексту, вставляем разметку.
    Кандидаты: соседи по весу + одногруппники, отсортированы длиной названия вниз,
    чтобы «квантовая запутанность» съедалась раньше «запутанности»."""
    c = live["concepts"].get(cid) or {}
    cands = []
    seen = {cid}
    for r in c.get("related", []):
        if r["id"] not in seen:
            seen.add(r["id"])
            cands.append(r["id"])
    for gid, members in live.get("groups", {}).items():
        if cid in members:
            for m in members:
                if m not in seen:
                    seen.add(m)
                    cands.append(m)
    pairs = []
    for other in cands:
        oc = live["concepts"].get(other)
        if not oc:
            continue
        # Текст секции бывает английским (новые понятия до перевода), а сосед —
        # старым с русским названием. Ищем ОБА названия: языка страницы и английское;
        # на ссылку это не влияет, она всегда ведёт на страницу текущего языка.
        variants = {oc["names"].get(lang), oc["names"].get("en"),
                    other.replace("_", " ")}
        for nm in variants:
            if nm and len(nm) >= 4:
                pairs.append((nm, other))
    pairs.sort(key=lambda t: -len(t[0]))

    used = set()
    for nm, other in pairs:
        if other in used:
            continue
        words = [w for w in _re.split(r"\s+", nm) if w]
        # шаблон: основы всех слов названия подряд, каждая с любым окончанием
        pat = r"\b" + r"\s+".join(_re.escape(_stem(w)) + r"[\w-]*" for w in words) + r""
        m = _re.search(pat, html_text, _re.IGNORECASE)
        if not m:
            continue
        # не внутрь уже поставленной ссылки
        before = html_text[: m.start()]
        if before.count("<a ") > before.count("</a>"):
            continue
        used.add(other)
        html_text = (html_text[: m.start()]
                     + f'<a href="/lang/{lang}/concepts/{other}.html">{m.group(0)}</a>'
                     + html_text[m.end():])
    return html_text


VAL_LBL = {"ru": "Значение", "en": "Value", "es": "Valor",
           "ar": "القيمة", "fr": "Valeur"}
AREA_LBL = {"ru": "Области", "en": "Areas", "es": "Áreas",
            "ar": "المجالات", "fr": "Domaines"}
KNOW_LBL = {"ru": "Связи по существу", "en": "Stated relations",
            "es": "Relaciones explícitas", "ar": "علاقات مصرّح بها",
            "fr": "Relations énoncées"}
# Отношение называем словом, а не значком: «входит в» читается сразу, part_of — нет.
REL_T = {
    "ru": {"part_of": "входит в", "case_of": "частный случай",
           "follows": "следует из", "measures": "измеряет",
           "describes": "описывает", "opposite": "противоположно",
           "same_area": "одна область"},
    "en": {"part_of": "part of", "case_of": "case of", "follows": "follows from",
           "measures": "measures", "describes": "describes",
           "opposite": "opposite to", "same_area": "same area"},
    "es": {"part_of": "forma parte de", "case_of": "caso de",
           "follows": "se deriva de", "measures": "mide", "describes": "describe",
           "opposite": "opuesto a", "same_area": "misma área"},
    "ar": {"part_of": "جزء من", "case_of": "حالة من", "follows": "ينبع من",
           "measures": "يقيس", "describes": "يصف", "opposite": "عكس",
           "same_area": "المجال نفسه"},
    "fr": {"part_of": "fait partie de", "case_of": "cas de",
           "follows": "découle de", "measures": "mesure", "describes": "décrit",
           "opposite": "opposé à", "same_area": "même domaine"},
}

_KNOW = None


def _knowledge_links():
    """Связи, найденные знанием (tools/link_weaving.py) — читаем один раз за сборку."""
    global _KNOW
    if _KNOW is None:
        p = ROOT / "data" / "concept-links-knowledge.json"
        try:
            _KNOW = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        except Exception:
            _KNOW = {}
    return _KNOW

_GNAMES = None
_GINDEX = None


def _group_index(live):
    """Номер области в реестре → её место в графе.

    Это две разные нумерации, и путать их — значит уводить человека в чужую
    область. В реестре у группы свой номер (supers), а граф и облако D1 нумеруют
    области ПО РАЗМЕРУ, позиционно: самая большая — нулевая. Соответствие строится
    ровно тем же сортом, что в tools/concepts_graph_export.py.
    """
    global _GINDEX
    if _GINDEX is None:
        gids = sorted(live["groups"], key=lambda g: -len(live["groups"][g]))
        _GINDEX = {str(g): i for i, g in enumerate(gids)}
    return _GINDEX


def _group_names():
    """Человеческие названия областей — один источник на облако, страницу и граф.

    Имена даёт tools/group_names.py по реальному составу области; читаем их лениво
    и один раз за сборку: файл небольшой, но страниц восемь тысяч.
    """
    global _GNAMES
    if _GNAMES is None:
        p = ROOT / "data" / "group-names.json"
        try:
            _GNAMES = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        except Exception:
            _GNAMES = {}
    return _GNAMES
# Единицы по-русски: показывать «coulomb» русскому читателю на странице заряда —
# та же полумера, что английская карточка. Список короткий намеренно: сюда
# попадают только единицы, которые реально стоят при наших константах.
UNIT_RU = {
    "coulomb": "Кл", "joule_second": "Дж·с", "joule_per_kelvin": "Дж/К",
    "per_mole": "1/моль", "kilogram": "кг", "metre": "м", "second": "с",
    "metre_per_second": "м/с", "farad_per_metre": "Ф/м",
    "henry_per_metre": "Гн/м", "joule_per_mole_kelvin": "Дж/(моль·К)",
    "coulomb_per_mole": "Кл/моль", "per_metre": "1/м",
    "joule_per_tesla": "Дж/Тл", "weber": "Вб", "siemens": "См", "ohm": "Ом",
    "metre_kelvin": "м·К", "hertz": "Гц", "kelvin": "К", "pascal_second": "Па·с",
    "newton_metre_squared_per_kilogram_squared": "Н·м²/кг²",
    "newton_metre_squared_per_coulomb_squared": "Н·м²/Кл²",
    "watt_per_square_metre_kelvin_to_the_fourth": "Вт/(м²·К⁴)",
    "per_second": "1/с", "electronvolt": "эВ",
    # базовые СИ — те, что стоят при переменных наших формул
    "joule": "Дж", "newton": "Н", "pascal": "Па", "watt": "Вт", "volt": "В",
    "ampere": "А", "tesla": "Тл", "mole": "моль", "candela": "кд",
    "square_metre": "м²", "cubic_metre": "м³", "radian": "рад",
    "steradian": "ср", "joule_per_cubic_metre": "Дж/м³",
    "watt_per_square_metre": "Вт/м²", "volt_per_metre": "В/м",
    "reciprocal_metre": "1/м", "per_second_squared": "1/с²",
    "radian_per_metre": "рад/м", "siemens_per_metre": "См/м",
    "square_metre_per_kilogram": "м²/кг",
    "watt_per_metre_per_kelvin": "Вт/(м·К)",
    "joule_per_cubic_metre_per_kelvin": "Дж/(м³·К)",
    "kilogram_per_cubic_metre": "кг/м³",
    "metre_per_second_squared": "м/с²", "newton_per_metre": "Н/м",
    "joule_per_kilogram": "Дж/кг", "joule_per_mole": "Дж/моль",
}


# Основы единиц. Дальше их собирает разбор имени — словарём все 153 единицы,
# что стоят при наших формулах, не покрыть, а новые приезжают с каждой добычей.
UNIT_BASE = {
    "metre": "м", "meter": "м", "second": "с", "kilogram": "кг", "gram": "г",
    "kelvin": "К", "joule": "Дж", "watt": "Вт", "coulomb": "Кл",
    "newton": "Н", "pascal": "Па", "mole": "моль", "ampere": "А",
    "volt": "В", "tesla": "Тл", "hertz": "Гц", "radian": "рад",
    "steradian": "ср", "siemens": "См", "ohm": "Ом", "farad": "Ф",
    "henry": "Гн", "weber": "Вб", "candela": "кд", "bit": "бит",
    "byte": "байт", "parsec": "пк", "megaparsec": "Мпк", "kiloparsec": "кпк",
    "kilometre": "км", "centimetre": "см", "millimetre": "мм",
    "micrometre": "мкм", "nanometre": "нм", "picometre": "пм",
    "angstrom": "Å", "electronvolt": "эВ", "kiloelectronvolt": "кэВ",
    "megaelectronvolt": "МэВ", "gigaelectronvolt": "ГэВ", "gev": "ГэВ",
    "mev": "МэВ", "kev": "кэВ", "ev": "эВ", "tev": "ТэВ",
    "year": "год", "day": "сут", "hour": "ч", "minute": "мин",
    "millisecond": "мс", "microsecond": "мкс", "nanosecond": "нс",
    "femtosecond": "фс", "picosecond": "пс", "gigahertz": "ГГц",
    "megahertz": "МГц", "kilohertz": "кГц", "terahertz": "ТГц",
    "atmosphere": "атм", "bar": "бар", "litre": "л", "gauss": "Гс",
    "lightyear": "св. год", "astronomical": "а. е.", "solar": "M☉",
    "dalton": "Да", "barn": "барн", "sievert": "Зв", "becquerel": "Бк",
    "lumen": "лм", "lux": "лк", "degree": "°",
}
_POW = {"squared": "²", "square": "²", "cubed": "³", "cubic": "³",
        "quartic": "⁴", "fourth": "⁴", "quadratic": "²"}
# Единицы, у которых нет разбора: атомные, обиходные, обратные.
UNIT_ODD = {"hartree": "Ha", "bohr": "a₀", "inverse_gev": "1/ГэВ",
            "reciprocal_gev": "1/ГэВ", "cycle_per_metre": "цикл/м",
            "cycle_per_second": "Гц", "metre_to_the_minus_2": "м⁻²",
            "metre_to_the_minus_3_over_2": "м⁻³ᐟ²",
            "per_metre_to_the_three_halves": "м⁻³ᐟ²",
            "arcsecond": "″", "arcminute": "′", "percent": "%"}


def unit_ru(uid):
    """«joule_per_mole_kelvin» → «Дж/(моль·К)». Разбор, а не словарь.

    Имя единицы у нас всегда собрано из английских слов: основа, степень
    («squared», «cubic») и «per» как черта дроби. Значит его можно разобрать —
    и тогда новая единица из ночной добычи получает русскую запись сама, без
    правки кода. Чего разобрать не смог — отдаём как есть, лучше английское
    слово, чем выдумка.
    """
    uid = (uid or "").strip().lower()
    if uid in UNIT_ODD:
        return UNIT_ODD[uid]
    # «...kelvin_to_the_fourth» — степень словами. Сводим её к обычному суффиксу
    # степени, чтобы она досталась ПОСЛЕДНЕЙ единице, а не всей дроби: у закона
    # Стефана — Больцмана размерность Вт/(м²·К⁴), а не (Вт/м²·К)⁴.
    for tail, plain in (("_to_the_fourth", "_quartic"), ("_to_the_third", "_cubed"),
                        ("_to_the_second", "_squared")):
        if uid.endswith(tail):
            uid = uid[: -len(tail)] + plain
    parts = [p for p in uid.split("_") if p]
    if not parts:
        return ""
    num, den, cur = [], [], []
    slot = num
    i = 0
    while i < len(parts):
        w = parts[i].lower()
        if w in ("per", "reciprocal"):
            if w == "reciprocal" or not cur:
                if slot is num and not num:
                    num.append("1")
            slot = den
            i += 1
            continue
        if w in ("to", "the", "over", "of", "unit", "units"):
            return ""                       # «metre_to_the_minus_3_over_2» — не наш случай
        pw = ""
        if w in _POW:                       # «cubic metre» — степень идёт впереди
            pw = _POW[w]
            i += 1
            if i >= len(parts):
                return ""
            w = parts[i].lower()
        base = UNIT_BASE.get(w) or UNIT_BASE.get(w.rstrip("s"))
        if not base:
            return ""
        if i + 1 < len(parts) and parts[i + 1].lower() in _POW:
            pw = _POW[parts[i + 1].lower()]
            i += 1
        slot.append(base + pw)
        cur = slot
        i += 1
    if not num:
        return ""
    top = "·".join(num)
    if not den:
        return top
    bot = "·".join(den)
    return f"{top}/{bot}" if len(den) == 1 else f"{top}/({bot})"


RU_PLURAL = {
    "статья": ("статья", "статьи", "статей"),
    "формула": ("формула", "формулы", "формул"),
    "учёный": ("учёный", "учёных", "учёных"),
    "понятие": ("понятие", "понятия", "понятий"),
    "метод": ("метод", "метода", "методов"),
    "константа": ("константа", "константы", "констант"),
}


def count_ru(n, word):
    """«1 статья», «2 статьи», «5 статей» — склонение по числу.

    До этого счётчики печатались как «0 статьи по теме»: подпись бралась
    готовой строкой и не знала о числе рядом. Русский так не работает, а
    счётчик стоит на каждой странице понятия.
    """
    forms = RU_PLURAL.get(word)
    if not forms:
        return f"{n} {word}"
    n100, n10 = abs(n) % 100, abs(n) % 10
    if 11 <= n100 <= 14 or n10 == 0 or n10 >= 5:
        f = forms[2]
    elif n10 == 1:
        f = forms[0]
    else:
        f = forms[1]
    return f"{n} {f}"


_ANATOMY = None


def anatomy():
    """Разбор формул — читаем один раз: он нужен и странице формулы, и понятия."""
    global _ANATOMY
    if _ANATOMY is None:
        p = ROOT / "data" / "formula-anatomy.json"
        try:
            _ANATOMY = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            _ANATOMY = {}
    return _ANATOMY


SYM_T = {
    "ru": {"var": "переменная", "const": "константа", "op": "оператор",
           "head": "Что в формуле"},
    "en": {"var": "variable", "const": "constant", "op": "operator",
           "head": "What is in the formula"},
    "es": {"var": "variable", "const": "constante", "op": "operador",
           "head": "Qué hay en la fórmula"},
    "ar": {"var": "متغير", "const": "ثابت", "op": "مؤثر",
           "head": "ما في الصيغة"},
    "fr": {"var": "variable", "const": "constante", "op": "opérateur",
           "head": "Ce qu'il y a dans la formule"},
}


def symbol_rows(rec, lang, live, link=None):
    """Разбор формулы: КАЖДЫЙ символ с расшифровкой, единицей и значением.

    Владелец 28.08: «там, где формулы пишешь, мы же говорили — обязательно
    расшифровка всех переменных, операторов и констант в формуле и значения
    констант там же, а то просто формула и всё».

    Одна функция на два места: страницу формулы и страницу понятия. Раньше
    разбор был только на первой, а на второй под формулой стояла служебная
    пометка вроде «стоит константой · e» — она говорила, чем понятие входит в
    формулу, и не говорила ничего о самой формуле.

    link — как делать ссылку на понятие (у страниц формул своя функция с
    классами); без неё ссылка строится обычным путём.
    """
    if not rec:
        return ""
    T_ = SYM_T.get(lang, SYM_T["en"])
    concepts = live["concepts"] if "concepts" in live else live

    def name_link(cid, fallback=""):
        if not cid:
            return H.escape(fallback)
        v = concepts.get(cid)
        if not v:
            return H.escape(fallback or cid.replace("_", " "))
        nm = name_of(v, cid, lang)
        if link:
            return link(cid, lang, {"concepts": concepts})
        return (f'<a href="/lang/{lang}/concepts/{H.escape(cid)}.html">'
                f'{H.escape(nm)}</a>')

    rows = []
    ru = rec.get("ru") or {}

    def m_of(key, i, fallback):
        tr = ru.get(key) or []
        return tr[i] if lang == "ru" and i < len(tr) and tr[i] else fallback

    for i, v in enumerate(rec.get("variables") or []):
        unit = unit_label(v.get("unit"), lang)
        rows.append((v.get("s", ""), T_["var"],
                     H.escape(m_of("variables", i, v.get("m", ""))),
                     name_link(v.get("id")), "", unit))
    for i, cst in enumerate(rec.get("constants") or []):
        unit = unit_label(cst.get("unit"), lang)
        val = cst.get("value") or ""
        # значение берём из реестра, если оно там точнее (СИ), иначе из формулы
        cv = (concepts.get(cst.get("id") or "") or {}).get("value")
        rows.append((cst.get("s", ""), T_["const"],
                     H.escape(m_of("constants", i, cst.get("m", ""))),
                     name_link(cst.get("id")), H.escape(cv or val), unit))
    for i, o in enumerate(rec.get("operators") or []):
        rows.append((o.get("s", ""), T_["op"],
                     H.escape(m_of("operators", i, o.get("m", ""))),
                     name_link(o.get("id")), "", ""))
    if not rows:
        return ""
    tr = []
    for sym, kind, mean, target, val, unit in rows:
        right = mean
        if target:
            right += (" — " if right else "") + target
        if val:
            right += f' <span class="fx-val">= {val}</span>'
        if unit:
            right += f' <span class="fx-unit">{H.escape(unit)}</span>'
        tr.append(f'<tr><td class="fx-s">{H.escape(sym)}</td>'
                  f'<td class="fx-k">{kind}</td><td>{right}</td></tr>')
    return (f'<div class="fx-sym"><div class="fx-sym-h">{T_["head"]}</div>'
            f'<table>{"".join(tr)}</table></div>')


def unit_label(uid, lang):
    """Подпись единицы на языке страницы — одна точка входа для всех страниц."""
    uid = (uid or "").strip()
    if not uid or uid == "dimensionless":
        return ""
    if lang == "ru":
        return UNIT_RU.get(uid) or unit_ru(uid) or uid.replace("_", " ")
    return uid.replace("_", " ")


def _sci_latex(val):
    """«1.602176634e-19» → «1{,}602176634 \\times 10^{-19}» для KaTeX."""
    s = (val or "").strip()
    m = _re.match(r"^(-?\d+(?:\.\d+)?)[eE]([-+]?\d+)$", s)
    if not m:
        return H.escape(s)
    mant, exp = m.group(1), int(m.group(2))
    return f"{mant} \\times 10^{{{exp}}}"


def const_value_block(c, lang):
    """Число константы — крупной строкой под определением.

    Единица идёт РЯДОМ с формулой, обычным HTML, а не внутри KaTeX: в «Дж/(моль·К)»
    стоит средняя точка, и KaTeX внутри \\text{} подставляет ей \\cdotp, которого
    в её наборе нет — вся строка тогда краснеет ошибкой разбора. Заодно единица
    остаётся текстом: её можно выделить, найти поиском и позже увести ссылкой на
    понятие единицы.
    """
    unit = c.get("unit") or ""
    if not unit or unit == "dimensionless":
        unit_html = ""
    else:
        unit_html = (f'<span class="const-unit" style="font-family:var(--mono);'
                     f'font-size:15px;color:var(--soft);margin-left:8px">'
                     f'{H.escape(unit_label(unit, lang))}</span>')
    sym = c.get("symbol") or ""
    sym_tex = {"alpha": r"\alpha", "sigma": r"\sigma", "epsilon_0": r"\varepsilon_0",
               "mu_0": r"\mu_0", "mu_B": r"\mu_B", "Phi_0": r"\Phi_0",
               "R_infinity": r"R_\infty"}.get(sym, sym.replace("_", "_{") + ("}" if "_" in sym else ""))
    lhs = f"{sym_tex} = " if sym else ""
    # Без цветной полосы слева: владелец 28.08 — «никаких рамок слева на плашке,
    # это прям совсем везде не используй». Плашку держат поверхность и волосяная
    # рамка, как у остальных карточек дома.
    return (f'<div class="const-value" style="margin:var(--s-3) 0;padding:var(--s-3) var(--s-4);'
            f'background:var(--surface);border:1px solid var(--hair);'
            f'border-radius:var(--radius-sm)">'
            f'<div style="font-family:var(--mono);font-size:11px;color:var(--muted);'
            f'letter-spacing:.04em;text-transform:uppercase">{VAL_LBL.get(lang, "Value")}</div>'
            f'<div style="margin:4px 0 0;display:flex;align-items:baseline;flex-wrap:wrap">'
            f'<span class="formula" style="font-size:19px">'
            f'\\({lhs}{_sci_latex(c["value"])}\\)</span>{unit_html}</div></div>')


def concept_page(cid, c, lang, live, by_id, rich=None, page_langs=None):
    t = T[lang]
    name = name_of(c, cid, lang)
    kind = KIND_LBL.get(lang, {}).get(c["kind"], c["kind"])
    foreign = lang != "en" and not c["names"].get(lang)
    note = f' <span class="tag-ver" style="font-size:11px">{t["en_note"]}</span>' if foreign and t["en_note"] else ""

    # Описание берём из популярного объяснения понятия — это первое, что читатель
    # увидит в выдаче, и оно уже написано на его языке.
    _r = (rich or {}).get(cid) or {}
    out = [head(lang, name, page_langs=page_langs or list(ALWAYS_LANGS),
                canon=f"/lang/{lang}/concepts/{cid}.html",
                alts=list(page_langs or ALWAYS_LANGS),
                desc=_r.get("description_popular") or c.get("si_definition") or "")]
    out.append('<div class="tag-header">')
    # Класс понятия — бейджем ПЕРЕД названием: владелец 26.08 «у понятий был класс,
    # метод, принцип и так далее — они остались?» Остались у всех 1222; бейдж делает
    # это видимым, а не строкой мелкого шрифта.
    out.append(f'<div class="tag-title-row">'
               f'<span class="entity-kind" style="font-family:var(--mono);font-size:11.5px;'
               f'color:var(--cyan);border:1px solid currentColor;border-radius:999px;'
               f'padding:2px 10px;align-self:center">{H.escape(kind)}</span>'
               f'<h1>{H.escape(name)}</h1></div>')
    # Пометка «перевод готовится» — СТРОКОЙ ПОД заголовком, а не внутри него:
    # в одну строку с названием она читалась его частью («постоянная Ридберга
    # перевод готовится»), и заголовок страницы выходил бессмысленным.
    if note:
        out.append(f'<div style="font-family:var(--mono);font-size:11.5px;'
                   f'color:var(--muted);margin:-2px 0 6px">{note.strip()}</div>')
    # КАРТОЧКА понятия — выделенным определением, а не строчкой между служебных:
    # это главный текст страницы, пока перевод не приехал — по-английски с пометкой.
    # Эпиграф — на языке страницы, когда перевод карточки уже есть (full_i18n)
    _card_tr = ((c.get("full_i18n") or {}).get(lang) or {}).get("card")
    _card_lang = lang if _card_tr else "en"
    out.append(f'<blockquote class="concept-card" lang="{_card_lang}" style="font-family:var(--serif);'
               f'font-size:18px;line-height:1.55;margin:var(--s-3) 0;padding:var(--s-3) var(--s-4);'
               f'background:var(--bg);'
               f'border-radius:var(--radius-sm)">{H.escape(_card_tr or c["card_en"])}</blockquote>')
    # ЗНАЧЕНИЕ КОНСТАНТЫ — крупно, сразу под определением. Константа и есть своё
    # число: страница элементарного заряда без «1,602·10⁻¹⁹ Кл» не отвечает на
    # единственный вопрос, с которым на неё приходят. Данные — из разбора формул
    # и ядра СИ (tools/constants_from_formulas.py).
    if c.get("value"):
        out.append(const_value_block(c, lang))
    # Счётчики: нулевой не печатаем вовсе (у константы статей может не быть — она
    # приходит из формулы), русские склоняем по числу.
    def _cnt(n, ru_word, label):
        return count_ru(n, ru_word) if lang == "ru" else f"{n} {label.lower()}"
    stats = []
    if c["articles"]:
        stats.append(_cnt(len(c["articles"]), "статья", t["articles"]))
    if c["formulas"]:
        stats.append(_cnt(len(c["formulas"]), "формула", t["formulas"]))
    if c["scientists"]:
        stats.append(_cnt(len(c["scientists"]), "учёный", t["sci"]))
    if stats:
        out.append(f'<div class="tag-stats">{" · ".join(stats)}</div>')
    # Области, в которых понятие живёт. Раньше страница молчала о том, где предмет
    # стоит на карте знания, и в граф человек попадал без представления, куда попал.
    # Ссылка ведёт сразу в кадр этой области — не в общий обзор из пятидесяти кругов.
    # Принадлежность бывает двойной и это не ошибка: турбулентность — и гидродинамика,
    # и стохастические процессы.
    _gn = _group_names()
    _gi = _group_index(live)
    areas = []
    for gid in (c.get("supers") or [])[:3]:
        g = _gn.get(str(gid)) or {}
        nm = g.get(f"name_{lang}") or g.get("name_en")
        idx = _gi.get(str(gid))
        if nm and idx is not None:
            areas.append(f'<a href="/lang/{lang}/concepts/graph.html?group={idx}">'
                         f'{H.escape(nm)}</a>')
    if areas:
        out.append(f'<div class="related-tags" style="margin-top:6px">'
                   f'<b style="font-family:var(--mono);font-size:11px;color:var(--muted)">'
                   f'{AREA_LBL.get(lang, AREA_LBL["en"])}:</b> {" ".join(areas)}</div>')
    out.append('</div>')

    body = []
    # Полное описание — из старого справочника, на языке страницы. Это то самое
    # «полноценное описание», которое было у понятий всегда; card_en сверху — опора
    # вектора и определение-эпиграф, а читателю здесь — нормальный текст.
    # старая запись из справочника ИЛИ новая развёрнутая (fullcards, поле full) —
    # имена полей одинаковые, рендер один
    # приоритет источника: старый справочник языка → перевод full_i18n[lang]
    # (cards_translate_ru) → английская full-запись
    r = ((rich or {}).get(cid) or (c.get("full_i18n") or {}).get(lang)
         or c.get("full") or {})
    s = SEC.get(lang, SEC["en"])
    panes = []
    for field, label in (("description_popular", s["desc"]), ("history", s["history"]),
                         ("how_it_works", s["how"]),
                         ("practical_application", s["practical"]),
                         ("fun_fact_popular", s["fact"])):
        txt = (r.get(field) or "").strip()
        if txt:
            # literal-слэши той же болезни + настоящие переносы абзацев из полных
            # записей (2-3 абзаца) — иначе они склеиваются в одну простыню
            txt = txt.replace(chr(92) + "n", " ")
            linked = autolink(H.escape(txt), cid, lang, live)
            linked = linked.replace(chr(10) + chr(10), "</p><p>").replace(chr(10), "<br>")
            panes.append((label, f'<p>{linked}</p>'))
    # ВКЛАДОК НЕТ — разделы идут подряд, как на странице статьи (владелец 28.08:
    # «у нас же не было вкладок, просто листаем и читаем всё по этим разделам —
    # описание, история и так далее; для статьи мы это уже обсудили»).
    #
    # Вкладки прятали основное: замер на «чёрной дыре» — видно 336 знаков, скрыто
    # 1503, то есть четыре пятых текста за кликом. Понятие читают, чтобы
    # разобраться, а не чтобы искать нужную панель; к тому же на узкой колонке
    # ряд кнопок разваливался на две строки и «всё сразу» висело отдельно.
    for lbl, html in panes:
        body.append(f'<div class="section"><h2 style="font-size:16px;margin:14px 0 6px">'
                    f'{H.escape(lbl)}</h2>{html}</div>')
    # Системы единиц (владелец 27.08): у единицы — в каких системах живёт и как
    # определяется в СИ; у величины — её единицы по системам. Данные кладёт
    # tools/unit_systems_seed.py --link-units прямо в live.
    SYS_NAME = {"si": "SI", "gaussian": "CGS", "planck": "Planck",
                "natural": "natural", "atomic": "atomic"}
    SYS_LBL = {"ru": "Системы", "en": "Systems", "es": "Sistemas",
               "ar": "الأنظمة", "fr": "Systèmes"}
    UNITS_LBL = {"ru": "Единицы по системам", "en": "Units by system",
                 "es": "Unidades por sistema", "ar": "الوحدات حسب النظام",
                 "fr": "Unités par système"}
    # Ссылка только на то, что реально есть в реестре: у планковской температуры
    # имя в данных единиц есть, а карточки нет — и ссылка уходила в 404. Правило
    # владельца 28.08: «всё, что есть, то есть; чего нет — добавляем, как появится».
    # Нет карточки — остаётся просто текст, как у учёных вне реестра.
    def clink(cid, label=None):
        label = label if label is not None else cid.replace("_", " ")
        if cid not in live["concepts"]:
            return H.escape(label)
        return (f'<a href="/lang/{lang}/concepts/{H.escape(cid)}.html">'
                f'{H.escape(label)}</a>')

    if c.get("systems"):
        chips = "".join(
            f'<a href="/lang/{lang}/concepts/{s}_units.html">{SYS_NAME.get(s, s)}</a>'
            for s in c["systems"] if f"{s}_units" in live["concepts"])
        sd = (f' <span style="color:var(--soft);font-size:13px" lang="en">'
              f'{H.escape(c.get("si_definition") or "")}</span>'
              if c.get("si_definition") else "")
        body.append(f'<div class="related-tags"><b style="font-family:var(--mono);'
                    f'font-size:11px;color:var(--muted)">'
                    f'{SYS_LBL.get(lang, "Systems")}:</b> {chips}{sd}</div>')
    if c.get("units_by_system"):
        cells = " · ".join(f'{SYS_NAME.get(s, s)}: {clink(u)}'
                           for s, u in c["units_by_system"].items() if u)
        if cells:
            body.append(f'<div class="related-tags"><b style="font-family:var(--mono);'
                        f'font-size:11px;color:var(--muted)">'
                        f'{UNITS_LBL.get(lang, "Units")}:</b> {cells}</div>')
    # СВЯЗИ ПО СУЩЕСТВУ — третий источник (владелец 28.08: «как ты установишь связь
    # между законом и константой… это работа твоя как интеллекта, а не только что
    # есть в статьях»). Статьи дают соседство, вектор — похожесть, а здесь названо
    # само отношение: закон ВХОДИТ В область, прибор ИЗМЕРЯЕТ величину. До сих пор
    # эти связи жили только в рёбрах графа — на странице их не было видно вовсе,
    # хотя именно они объясняют, а не просто ставят рядом.
    # «Одна область» отсюда убрана намеренно: это не объяснение, а то же соседство,
    # которое ниже даёт ряд «рядом стоят» и выше — строка областей. Из трёх связей
    # турбулентности все три были «одна область» — ряд повторял соседей другими
    # словами. В графе такое ребро полезно, на странице — шум.
    know = [k for k in (_knowledge_links().get(cid) or [])
            if k.get("rel") != "same_area"]
    if know:
        kt = REL_T.get(lang, REL_T["en"])
        rows = []
        seen_rows = set()
        for lk in know[:12]:
            to = lk.get("to")
            # Слитое понятие как цель связи заменяем тем, в кого оно слилось:
            # связь остаётся верной, а вести читателя через переадресацию незачем.
            _m = (live["concepts"].get(to) or {}).get("merged_into")
            if _m:
                to = _m
            if to not in live["concepts"]:
                continue          # понятие могли переименовать или слить
            nm = name_of(live["concepts"][to], to, lang)
            # В реестре встречаются два разных понятия с одним именем («эхо
            # гравитационных волн»), и на странице это читается как заикание.
            # Повтор пары «отношение + имя» не показываем; сами дубли в реестре
            # разбирает чистка, а витрине заикаться нельзя уже сейчас.
            if (lk.get("rel"), nm) in seen_rows:
                continue
            seen_rows.add((lk.get("rel"), nm))
            # Отношение и понятие разделяет стрелка, а не пробел: «описывает
            # гравитация» — не по-русски, а падежи под семь отношений и пять
            # языков подгонять незачем. Стрелка читается как подпись связи и
            # заодно показывает направление, которое здесь существенно.
            # В арабском строка идёт справа налево, и «вперёд» там — влево:
            # стрелка вправо указывала бы назад, к тому, от чего связь идёт.
            _arr = "&larr;" if lang == "ar" else "&rarr;"
            rows.append(f'<span style="white-space:nowrap">'
                        f'<span style="font-family:var(--mono);font-size:11px;'
                        f'color:var(--muted)">{H.escape(kt.get(lk.get("rel"), ""))} '
                        f'{_arr}</span> '
                        f'<a href="/lang/{lang}/concepts/{H.escape(to)}.html">'
                        f'{H.escape(nm)}</a></span>')
        if rows:
            body.append(f'<div class="related-tags" style="margin-top:10px">'
                        f'<b style="font-family:var(--mono);font-size:11px;'
                        f'color:var(--muted)">{KNOW_LBL.get(lang, KNOW_LBL["en"])}:</b> '
                        + " · ".join(rows) + '</div>')
    # МИНИ-ГРАФ понятия (27.08): само понятие + соседи первого уровня + его
    # формулы. Тот же движок и вид, что у большого графа (js/b42-mini.js).
    _mini = [cid] + [r["id"] for r in (c.get("related") or [])[:10]]
    _mini += [lk["to"] for lk in know[:6] if lk.get("to") in live["concepts"]]
    _mini += [f'f:{f["id"]}' for f in (c.get("formulas") or [])[:3]]
    if len(_mini) >= 3:
        GT = GRAPH_T.get(lang, GRAPH_T["en"])
        body.append(
            f'<div class="b42mini" data-ids="{H.escape(",".join(_mini))}" '
            f'data-focus="{H.escape(cid)}"></div>'
            # ссылка ведёт в граф С ФОКУСОМ на этом понятии: человек смотрел его
            # окружение — оно и должно открыться, а не карта из пятидесяти кругов
            f'<div class="b42mini-note">'
            f'<a href="/lang/{lang}/concepts/graph.html?focus={H.escape(cid)}">'
            f'{GT["title"]} &rarr;</a></div>')
    if c["related"]:
        # Соседа без карточки не показываем вовсе: в отличие от единицы измерения,
        # где имя системы несёт смысл и без ссылки, «рядом стоит» имя, которое
        # некуда открыть, — обещание без содержания.
        chips = "".join(
            f'<a href="/lang/{lang}/concepts/{H.escape(r["id"])}.html">'
            f'{H.escape(name_of(live["concepts"][r["id"]], r["id"], lang))}</a>'
            for r in c["related"] if r["id"] in live["concepts"]
            and not live["concepts"][r["id"]].get("merged_into"))
        # Связь по смыслу и связь по статьям — разные вещи, и подпись это
        # говорит. «Рядом стоят» значит «встречаются в одних статьях»; у понятия
        # без статей соседи найдены по близости определений, и выдавать одно за
        # другое нельзя.
        _lbl = t["related"]
        if all(r.get("src") == "vec" for r in c["related"]):
            _lbl = {"ru": "Близки по смыслу", "en": "Close in meaning",
                    "es": "Cercanos por sentido", "ar": "قريبة في المعنى",
                    "fr": "Proches par le sens"}.get(lang, "Close in meaning")
        body.append(f'<div class="related-tags"><b style="font-family:var(--mono);'
                    f'font-size:11px;color:var(--muted)">{_lbl}:</b> {chips}</div>')
    if c["scientists"]:
        chips = "".join(
            f'<a href="/lang/{lang}/scientists/{H.escape(s["name"].replace(" ", "_"))}.html">'
            f'{H.escape(s["name"])} <em style="opacity:.6">{s["n"]}</em></a>'
            for s in c["scientists"])
        body.append(f'<div class="related-tags related-scientists"><b style="font-family:'
                    f'var(--mono);font-size:11px;color:var(--muted)">{t["sci"]}:</b> {chips}</div>')
    if c["formulas"]:
        rows = []
        for f in c["formulas"]:
            apps = "".join(f'<div style="font-family:var(--mono);font-size:12px;color:var(--soft);'
                           f'margin-top:4px">{H.escape(a["latex"])}'
                           + (f' · <a href="/lang/{lang}/index.html?q={H.escape(a["art"])}">{H.escape(a["art"])}</a>' if a["art"] else "")
                           + '</div>'
                           for a in f["apps"][:4])
            # РАЗБОР ФОРМУЛЫ, а не служебная пометка. Раньше здесь стояло «стоит
            # константой · e» — сообщение о том, чем понятие входит в формулу, и
            # ничего о самой формуле. Владелец 28.08: «там, где формулы пишешь,
            # обязательно расшифровка всех переменных, операторов и констант и
            # значения констант там же, а то просто формула и всё».
            an = anatomy().get(f["id"]) or {}
            sym = symbol_rows(an, lang, live)
            # Подпись формулы — на языке страницы, если перевод есть. Реестр несёт
            # английскую строку, а перевод лежит в анатомии (cards_translate_ru
            # --formulas, все 642 сделаны) — и страница всё равно показывала
            # английский: смотрели не туда.
            cap = ((an.get(lang) or {}).get("card")
                   or (an.get(lang) or {}).get("description")
                   or f["card"])
            cap_lang = lang if cap is not f["card"] else "en"
            rows.append(f'<div class="formula" style="margin-bottom:14px">'
                        f'<div style="font-family:var(--mono)">$${H.escape(f["latex"])}$$</div>'
                        f'<div style="font-size:13.5px;color:var(--soft)" '
                        f'lang="{cap_lang}">{H.escape(cap)}</div>'
                        f'{sym}{apps}</div>')
        body.append(f'<h2 style="font-size:16px;margin:14px 0 8px">{t["formulas"]}</h2>' + "".join(rows))
    # ДЕЙСТВИЯ И ОТКЛИК — те же функции, что у статьи и старых справочников
    # (владелец 27.08: «много функционала упущено — функционал тот же»).
    # Реакции, избранное, «поделиться», форма комментария; обрабатывает likes.js.
    _like = f"concept_{cid}_{lang}"
    body.append(G.build_actions_html(_like, cid, lang, "tag", inline_comment=True))
    body.append(G.build_feedback_html(_like, lang, "tag", inline_toggle=True))
    if body:
        out.append('<div class="entity-body">' + "".join(body) + '</div>')

    # СТАТЬИ ИЗ ТРЁХ ИСТОЧНИКОВ, а не только из разметки понятиями. Она строгая
    # (порог сходства плюс отрыв), и у «квантовой запутанности» ею отмечено 14
    # работ, тогда как старым тегом — 246. При сведении тегов и законов в понятия
    # (28.08) страница понятия становится единственной, и обеднять её нельзя:
    # статья, помеченная тегом «квантовая запутанность», про неё и есть.
    ids = list(c["articles"])
    seen_a = set(ids)
    for a in by_id.values():
        aid = a.get("id")
        if not aid or aid in seen_a:
            continue
        if cid in (a.get("tags") or []) or cid in (a.get("laws") or []):
            seen_a.add(aid)
            ids.append(aid)
    arts = [by_id[a] for a in ids if a in by_id]
    arts.sort(key=lambda a: a.get("date") or "", reverse=True)
    out.append(f'<h2 class="section-title">{t["articles"]}'
               f'<span style="font-family:var(--mono);font-size:13px;color:var(--soft)"> · '
               f'{len(arts)}</span></h2>')
    if arts:
        # контейнер живой ленты: статика внутри — то, что видно сразу и без
        # облака; воркер подменит её свежим списком (js/entity-live.js)
        out.append(f'<div id="search-results" class="entity-list" '
                   f'data-context-concept="{H.escape(cid)}">')
        out.append("".join(G.entity_article_card(a, lang) for a in arts[:CARDS_CAP]))
        out.append('</div>')
    else:
        out.append(f'<p style="color:var(--soft)">{t["none"]}</p>')
    out.append(site_chrome(lang)[1])          # футер сайта
    out.append(site_chrome(lang)[2])          # лайки, иконки, поиск, «ещё»
    out.append(f'<script src="{av("/js/b42-live.js")}"></script>'
               f'<script src="{av("/js/entity-live.js")}" defer></script>')
    # f-строка, а не обычная: без префикса подстановка не срабатывала, и в HTML
    # уезжало буквальное «{av("/js/b42-mini.js")}». Браузер честно запрашивал файл
    # с таким именем, получал 404 — и мини-граф на странице понятия не рисовался
    # вообще, оставляя пустое место. Поймано 28.08 по списку загруженных скриптов.
    out.append(f'<script src="{av("/js/b42-graph-core.js")}"></script>'
               f'<script src="{av("/js/b42-mini.js")}" defer></script>')
    # Скрипта вкладок больше нет. Он превращал разделы в панель и прятал под
    # неё четыре пятых текста; владелец 28.08: «вкладки — это лишние действия
    # и мусор в интерфейсе». Разделы идут подряд, как на странице статьи, и
    # никакого JS для чтения не требуется.
    out.append("</body></html>")
    return "".join(out)


def cloud_page(lang, live, by_id):
    t = T[lang]
    c = live["concepts"]
    out = [head(lang, t["title"], canon=f"/lang/{lang}/concepts/index.html",
                alts=list(LANGS), desc=t.get("sub", "").format(n=len(c),
                                                               g=len(live["groups"])))]
    out.append(f'<h1>{t["title"]}</h1>')
    gt = GRAPH_T.get(lang, GRAPH_T["en"])
    out.append(f'<div class="subtitle">{t["sub"].format(n=len(c), g=len(live["groups"]))}'
               f' &nbsp;<a href="/lang/{lang}/concepts/graph.html" '
               f'style="font-family:var(--mono);font-size:12.5px">{gt["title"]} →</a></div>')
    # РАЗДЕЛЫ — вход в облако не только через группы: статистика и математика
    # собраны по смыслу, константы по классу. Владелец 27.08: «сделать как новый
    # раздел кроме математики».
    st = SEC_T.get(lang, SEC_T["en"])
    secs = [(sec, st.get(sec, sec),
             sum(1 for v in c.values()
                 if v.get("section") == sec or v.get("kind") == sec))
            for sec in ("statistics", "math", "constant")]
    out.append('<div class="related-tags" style="margin:2px 0 18px">' + "".join(
        f'<a href="/lang/{lang}/concepts/{sec}.html">{H.escape(lbl)} '
        f'<em style="opacity:.55;font-size:10.5px">{n}</em></a>'
        for sec, lbl, n in secs if n) + '</div>')
    groups = sorted(live["groups"].items(), key=lambda kv: -len(kv[1]))
    # Контейнер результатов поиска НЕ ставим: search.js, найдя пустой
    # #search-results, наполняет его лентой статей — на облаке понятий
    # это чужой список (замер 27.08: 12 карточек ниоткуда). Поиск здесь
    # работает через site-search (переход на главную с запросом).
    # Названия областей — человеческие, те же, что в графе (data/group-names.json).
    # Заголовком стояла склейка трёх участников: «течение жидкости · гидродинамика ·
    # поверхностное натяжение». Это не название, а первые строки списка — по нему не
    # понять ни чем область занимается, ни чем отличается от соседней (владелец 28.08:
    # «статистика просто даёт что-то, а ты можешь дать понятное название»). Склейка
    # остаётся запасной — на случай, если область ещё не назвали.
    gnames = _group_names()

    for gid, members in groups:
        members = sorted(members, key=lambda m: -len(c.get(m, {}).get("articles", [])))
        _g = gnames.get(str(gid)) or {}
        title = (_g.get(f"name_{lang}") or _g.get("name_en")
                 or " · ".join(name_of(c[m], m, lang) for m in members[:3]
                                   if m in c and not c[m].get("merged_into")))
        note = _g.get(f"note_{lang}") or _g.get("note_en") or ""
        # Понятие без статей — тоже член группы. Фильтр по числу статей прятал с
        # облака всё, что пришло не из текстов: константы и статистику целиком.
        # Показываем их без счётчика — счётчик ноль ничего не сообщает, а место
        # в группе сообщает.
        chips = "".join(
            f'<a href="/lang/{lang}/concepts/{H.escape(m)}.html">'
            f'{H.escape(name_of(c[m], m, lang))}'
            + (f' <em style="opacity:.55;font-size:10.5px">{len(c[m]["articles"])}</em>'
               if c[m]["articles"] else "")
            + '</a>'
            # Слитое понятие в облаке не показываем: его имя и место занял тот,
            # в кого оно слилось, а вторая плашка с тем же названием — то самое
            # заикание, ради которого слияние и делалось.
            for m in members if m in c and not c[m].get("merged_into"))
        # Пояснение «о чём эта область» — под названием, серым: название говорит, что
        # это, пояснение — чем занимается. Вместе они заменяют то, что раньше читатель
        # должен был угадывать по трём первым участникам.
        note_html = (f'<div style="font-size:13px;color:var(--soft);margin:4px 0 2px">'
                     f'{H.escape(note)}</div>' if note else "")
        out.append(f'<details style="margin-bottom:10px"><summary style="cursor:pointer;'
                   f'font-family:var(--serif);font-size:16px">{H.escape(title)} '
                   f'<span style="font-family:var(--mono);font-size:12px;color:var(--soft)">'
                   f'· {len(members)}</span></summary>{note_html}'
                   f'<div class="related-tags" style="margin-top:8px">{chips}</div></details>')
    out.append(site_chrome(lang)[1])
    out.append(site_chrome(lang)[2])
    out.append("</body></html>")
    return "".join(out)


SEC_T = {
    "ru": {"statistics": "Статистика",
           "sub": "Чем физика обрабатывает данные: {n} методов и приёмов — от подгонки "
                  "и проверки гипотез до байесовской выборки и машинного обучения. "
                  "В статьях их обычно не называют по имени, а делают; поэтому раздел "
                  "собран как справочник, а не выужен из текстов.",
           "back": "Все понятия", "of_kind": "класс"},
    "en": {"statistics": "Statistics",
           "sub": "How physics handles data: {n} methods and practices — fitting, "
                  "hypothesis testing, Bayesian sampling, machine learning. Papers rarely "
                  "name them, they just use them, so this section is built as a reference "
                  "rather than mined from texts.",
           "back": "All concepts", "of_kind": "class"},
}
SEC_T["ru"]["math"] = "Математика"
SEC_T["en"]["math"] = "Mathematics"
SEC_T["ru"]["constant"] = "Константы"
SEC_T["en"]["constant"] = "Constants"
# Подписи разделов, которые собираются по классу, а не по метке
SEC_SUB = {
    "math": {"ru": "Математический аппарат физики: {n} понятий — операторы, "
                   "преобразования, уравнения и теоремы, которыми записаны законы.",
             "en": "The mathematics physics is written in: {n} concepts — operators, "
                   "transforms, equations and theorems behind the laws."},
    "constant": {"ru": "Константы: {n} величин с числом и единицей. Значения — из "
                       "разбора наших формул и определений СИ; константа может не "
                       "встречаться в статьях дословно, но о ней говорит формула.",
                 "en": "Constants: {n} values with number and unit, taken from our "
                       "formula anatomy and the SI definitions."},
}
# Порядок частей раздела — от того, чем меряют, к тому, чем решают.
SEC_ORDER = ["Анализ", "Алгебра и операторы", "Пространства и геометрия",
             "Случайность", "Основания и вычисления",
             "Определяющие СИ", "Электромагнетизм", "Частицы и атом",
             "Тепло и излучение", "Гравитация и планковские", "Из наших формул",
             "Оценивание и подгонка", "Неопределённости", "Проверка гипотез",
             "Распределения", "Байесовский анализ", "Ресемплинг и проверка",
             "Сигналы и временные ряды", "Многомерный анализ и обучение",
             "Моделирование и выборка"]
SEC_PART_EN = {
    "Анализ": "Analysis",
    "Алгебра и операторы": "Algebra and operators",
    "Пространства и геометрия": "Spaces and geometry",
    "Случайность": "Randomness",
    "Основания и вычисления": "Foundations and computation",
    "Определяющие СИ": "Defining the SI",
    "Электромагнетизм": "Electromagnetism",
    "Частицы и атом": "Particles and the atom",
    "Тепло и излучение": "Heat and radiation",
    "Гравитация и планковские": "Gravity and Planck scale",
    "Из наших формул": "From our formulas",
    "Оценивание и подгонка": "Estimation and fitting",
    "Неопределённости": "Uncertainties",
    "Проверка гипотез": "Hypothesis testing",
    "Распределения": "Distributions",
    "Байесовский анализ": "Bayesian analysis",
    "Ресемплинг и проверка": "Resampling and validation",
    "Сигналы и временные ряды": "Signals and time series",
    "Многомерный анализ и обучение": "Multivariate analysis and learning",
    "Моделирование и выборка": "Simulation and sampling",
}


# Части раздела математики. Здесь они живут в коде, а не в concept-sections.json,
# потому что раздел математики собирается по КЛАССУ понятия, а метка раздела у
# части из них уже занята статистикой: гауссово распределение — и математика, и
# статистика, и переписывать одну принадлежность другой нельзя.
MATH_PARTS = {
    "Анализ": ("derivative", "partial_derivative", "second_derivative",
               "time_derivative", "logarithmic_derivative", "integral", "limit",
               "uniform_convergence", "exponential_function", "logarithm",
               "natural_logarithm", "logarithm_base_10", "square_root",
               "absolute_value", "sine", "cosine", "fourier_series", "summation",
               "difference", "proportionality", "exponential_growth", "power_law"),
    "Алгебра и операторы": ("group", "group_theory", "ring", "category", "lie_group",
                            "elliptic_curve", "modular_form", "zeta_function",
                            "tensor", "matrix_element", "dot_product",
                            "product_operator", "commutator", "eigenvalue",
                            "trace_operator", "integral_operator"),
    "Пространства и геометрия": ("banach_space", "hilbert_space", "manifold",
                                 "symplectic_geometry", "topology", "homotopy",
                                 "differential_form", "knots", "fractal",
                                 "decoherence_free_subspace"),
    "Случайность": ("random_variable", "random_matrix", "markov_chain",
                    "ensemble_average", "gaussian_distribution", "covariance_matrix",
                    "maximum_likelihood"),
    "Основания и вычисления": ("axiom_of_choice", "turing_machine",
                               "functional_analysis", "hubbard_model"),
}
MATH_PART_OF = {c: p for p, ids in MATH_PARTS.items() for c in ids}


def section_page(section, lang, live):
    """Страница раздела: понятия, собранные по смыслу, а не по классу.

    Владелец 27.08: «добавил бы ещё раздел статистику… сделать как новый раздел
    кроме математики». Раздел шире класса: сюда входит и стандартное отклонение
    (величина), и метод наименьших квадратов (статистика) — принадлежность
    разделу живёт отдельным полем, класс у понятия остаётся свой.
    """
    t = SEC_T.get(lang, SEC_T["en"])
    c = live["concepts"]
    members = {cid: v for cid, v in c.items()
               if v.get("section") == section or v.get("kind") == section}
    parts = {}
    for cid, v in members.items():
        part = (MATH_PART_OF.get(cid, "") if section == "math"
                else v.get("section_part") or "")
        parts.setdefault(part, []).append(cid)
    title = t.get(section, section)
    sub = (SEC_SUB.get(section, {}).get(lang)
           or SEC_SUB.get(section, {}).get("en") or t["sub"])
    out = [head(lang, title, canon=f"/lang/{lang}/concepts/{section}.html",
                alts=list(ALWAYS_LANGS), desc=sub.format(n=len(members)))]
    out.append(f'<h1>{H.escape(title)}</h1>')
    out.append(f'<div class="subtitle">{sub.format(n=len(members))} '
               f'&nbsp;<a href="/lang/{lang}/concepts/" '
               f'style="font-family:var(--mono);font-size:12.5px">{t["back"]} →</a></div>')
    order = [p for p in SEC_ORDER if p in parts] + \
            [p for p in sorted(parts) if p and p not in SEC_ORDER] + \
            ([""] if "" in parts else [])
    for part in order:
        ids = sorted(parts[part], key=lambda m: (-len(c[m].get("articles") or []),
                                                 name_of(c[m], m, lang)))
        label = (part if lang == "ru" else SEC_PART_EN.get(part, part)) or \
                ({"ru": "Прочее", "en": "Other"}.get(lang, "Other"))
        rows = []
        for m in ids:
            v = c[m]
            card = ((v.get("full_i18n") or {}).get(lang) or {}).get("card") or v.get("card_en", "")
            n = len(v.get("articles") or [])
            rows.append(
                f'<div style="padding:10px 0;border-bottom:1px solid var(--hair)">'
                f'<a href="/lang/{lang}/concepts/{H.escape(m)}.html" '
                f'style="font-family:var(--serif);font-size:16px">'
                f'{H.escape(name_of(v, m, lang))}</a>'
                # В списке констант число важнее описания: за ним и приходят.
                # Показываем сразу за именем, единицу — рядом.
                + (f' <span style="font-family:var(--mono);font-size:13px;'
                   f'color:var(--cyan)">{H.escape(v["value"])}</span>'
                   + (f' <span style="font-family:var(--mono);font-size:11.5px;'
                      f'color:var(--soft)">{H.escape(unit_label(v.get("unit"), lang))}</span>'
                      if unit_label(v.get("unit"), lang) else "")
                   if v.get("value") else "")
                + (f' <span style="font-family:var(--mono);font-size:11px;color:var(--soft)">'
                   f'{n}</span>' if n else "")
                + f'<div style="font-size:13.5px;color:var(--soft);margin-top:2px" '
                  f'lang="{lang if ((v.get("full_i18n") or {}).get(lang) or {}).get("card") else "en"}">'
                  f'{H.escape(card[:180])}</div></div>')
        out.append(f'<h2 style="font-size:17px;margin:26px 0 6px">{H.escape(label)} '
                   f'<span style="font-family:var(--mono);font-size:12px;color:var(--soft)">'
                   f'· {len(ids)}</span></h2>' + "".join(rows))
    out.append(site_chrome(lang)[1])
    out.append(site_chrome(lang)[2])
    out.append("</body></html>")
    return "".join(out)


GRAPH_T = {
    "ru": {"title": "Граф понятий", "sub": "Кадры вместо всего облака: группы → группа → соседи понятия. Мощность ребра — сколько статей связывают два понятия.",
           "search": "найти понятие…", "w": "мощность ребра", "home": "Обзор",
           "legend": [("квадрат", "закон · принцип · теорема"), ("ромб", "метод · процесс"),
                      ("треугольник", "явление · эффект"), ("шестиугольник", "прибор"),
                      ("кольцо", "объект · вещество"), ("крест", "математика"),
                      ("пятиугольник", "величина · единица · система"), ("круг", "понятие")]},
    "en": {"title": "Concept graph", "sub": "Frames instead of the whole cloud: groups → one group → a concept's neighbors. Edge power = how many articles link two concepts.",
           "search": "find a concept…", "w": "edge power", "home": "Overview",
           "legend": [("square", "law · principle · theorem"), ("diamond", "method · process"),
                      ("triangle", "phenomenon · effect"), ("hexagon", "instrument"),
                      ("ring", "object · substance"), ("cross", "mathematics"),
                      ("pentagon", "quantity · unit · system"), ("circle", "concept")]},
}


def graph_page(lang):
    """Полноэкранное приложение-граф (владелец 27.08, третий заход: «во весь
    экран, прозрачность, панелька без наездов, тултипы, визуальность,
    лёгкость»). Канвас подо всем экраном, панели плавают поверх на
    полупрозрачном стекле (backdrop-blur)."""
    t = GRAPH_T.get(lang, GRAPH_T["en"])
    L = {"ru": {"mode": "Режим", "layout": "Представление", "force": "силы",
                "ring": "кольцо", "sphere": "сфера", "galaxy": "галактика",
                "layers": "слои", "spin": "вращение",
                "kinds": "Классы", "groups": "Группы", "info": "Выбрано",
                "stats": "Кадр", "path": "Путь"},
         "en": {"mode": "Mode", "layout": "Layout", "force": "force",
                "ring": "ring", "sphere": "sphere", "galaxy": "galaxy",
                "layers": "layers", "spin": "spin",
                "kinds": "Kinds", "groups": "Groups", "info": "Selection",
                "stats": "Frame", "path": "Trail"}}
    l = L.get(lang, L["en"])
    return head(lang, t["title"], body_class="graph-page") + f"""
<div class="b42g-stage"><canvas id="b42g"></canvas></div>
<div class="b42g-top glass">
  <b style="font-family:var(--serif);font-size:16px">{t["title"]}</b>
  <button id="b42g-home" class="b42g-mini">{t["home"]}</button>
  <button id="b42g-all" class="b42g-mini">{"всё облако" if lang == "ru" else "whole cloud"}</button>
  <span id="b42g-crumbs"></span>
  <input id="b42g-q" list="b42g-names" placeholder="{t["search"]}">
  <datalist id="b42g-names"></datalist>
  <button id="b42g-demo" class="b42g-mini" title="{"экскурсия: сам ведёт, подсвечивает, крутит" if lang == "ru" else "tour: drives, highlights, spins by itself"}">▶ {"демо" if lang == "ru" else "demo"}</button>
</div>
<aside class="b42g-side glass">
  <div class="b42g-sec"><div class="b42g-h">{l["mode"]}</div>
    <button id="b42g-2d" class="b42g-mini active">2D</button>
    <button id="b42g-3d" class="b42g-mini">3D</button>
    <button id="b42g-spin" class="b42g-mini" style="display:none">⟳ {l["spin"]}</button>
  </div>
  <div class="b42g-sec"><div class="b42g-h">{l["layout"]}</div>
    <button data-layout="force" class="b42g-mini active">{l["force"]}</button>
    <button data-layout="ring" class="b42g-mini">{l["ring"]}</button>
    <button data-layout="sphere" class="b42g-mini">{l["sphere"]}</button>
    <button data-layout="galaxy" class="b42g-mini">{l["galaxy"]}</button>
    <button data-layout="layers" class="b42g-mini">{l["layers"]}</button>
  </div>
  <div class="b42g-sec"><div class="b42g-h">{t["w"]} <span id="b42g-wv">≥2</span></div>
    <input id="b42g-w" type="range" min="2" max="20" value="2" style="width:100%">
  </div>
  <div class="b42g-sec"><div class="b42g-h">{l["stats"]}
    <span id="b42g-live" class="b42g-dim" title="источник кадров">файл</span></div>
    <div id="b42g-stats" class="b42g-info"></div>
  </div>
  <div class="b42g-sec"><div class="b42g-h">{l["info"]}</div>
    <div id="b42g-info" class="b42g-info"></div>
  </div>
  <div class="b42g-sec"><div class="b42g-h">{l["kinds"]}</div>
    <div id="b42g-kinds" class="b42g-kgrid"></div>
  </div>
  <details class="b42g-sec"><summary class="b42g-h">{"Разделы arXiv" if lang == "ru" else "arXiv sections"}</summary>
    <div id="b42g-cats" class="b42g-groups"></div>
  </details>
  <details class="b42g-sec"><summary class="b42g-h">{l["groups"]}</summary>
    <div id="b42g-groups" class="b42g-groups"></div>
  </details>
  <details class="b42g-sec" style="margin-bottom:4px"><summary class="b42g-h">{l["path"]}</summary>
    <div id="b42g-path" class="b42g-info"></div>
  </details>
</aside>
<style>
/* весь экран: канвас — сцена, всё остальное плавает поверх */
html, body {{ height:100%; overflow:hidden; }}
.top-bar {{ position:relative; z-index:5; }}
.b42g-stage {{ position:fixed; inset:0; z-index:0; background:var(--bg); }}
.b42g-stage canvas {{ display:block; width:100%; height:100%; }}
.glass {{ background:color-mix(in srgb, var(--surface) 72%, transparent);
  backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px);
  border:1px solid var(--hairline); border-radius:var(--radius-sm); }}
.b42g-top {{ position:fixed; top:var(--b42g-top,78px); left:14px; right:296px; z-index:4;
  display:flex; flex-wrap:wrap; gap:10px; align-items:center;
  font-family:var(--mono); font-size:12px; padding:8px 14px; }}
.b42g-side {{ position:fixed; top:var(--b42g-top,78px); right:14px; bottom:14px; width:264px;
  z-index:4; font-family:var(--mono); font-size:12px;
  overflow-y:auto; padding:12px 14px; }}
.b42g-sec {{ margin-bottom:10px; }}
.b42g-h {{ font-size:10px; text-transform:uppercase; letter-spacing:.09em;
  color:var(--soft); margin-bottom:4px; }}
details.b42g-sec > summary.b42g-h {{ cursor:pointer; list-style:none; }}
details.b42g-sec > summary.b42g-h::before {{ content:"▸ "; }}
details[open].b42g-sec > summary.b42g-h::before {{ content:"▾ "; }}
.b42g-kgrid {{ display:grid; grid-template-columns:1fr 1fr; gap:0 6px; }}
.b42g-kgrid .b42g-check {{ font-size:10.5px; }}
.b42g-top input[list] {{ padding:4px 10px; border:1px solid var(--hairline);
  border-radius:999px; background:var(--bg); color:var(--text);
  font:inherit; min-width:150px; flex:1; max-width:230px; }}
.b42g-mini {{ font:inherit; font-size:11px; padding:3px 10px; cursor:pointer;
  color:var(--muted); background:var(--bg); border:1px solid var(--hairline);
  border-radius:999px; margin:0 3px 4px 0; white-space:nowrap; }}
.b42g-mini:hover {{ color:var(--link); border-color:var(--link); }}
.b42g-mini.active {{ color:#fff; background:var(--link); border-color:var(--link); }}
.b42g-crumb {{ font:inherit; border:none; background:none; color:var(--link);
  cursor:pointer; padding:2px 1px; max-width:180px; overflow:hidden;
  text-overflow:ellipsis; white-space:nowrap; }}
.b42g-sep {{ color:var(--soft); margin:0 2px; }}
.b42g-info {{ font-size:11.5px; line-height:1.5; }}
.b42g-sel {{ font-size:12.5px; overflow-wrap:anywhere; }}
.b42g-dim {{ color:var(--soft); }}
.b42g-check {{ display:flex; align-items:center; gap:6px; padding:1px 0;
  cursor:pointer; color:var(--muted); min-width:0; }}
.b42g-check:hover {{ color:var(--text); }}
.b42g-check span {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.b42g-sw {{ flex:none; }}
.b42g-ell {{ display:block; min-width:0; }}
.b42g-groups {{ max-height:200px; overflow-y:auto; }}
.b42g-jump {{ display:flex; justify-content:space-between; gap:8px; width:100%;
  font:inherit; border:none; background:none; color:var(--link); cursor:pointer;
  padding:1px 0; text-align:start; }}
.b42g-jump span {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.b42g-jump em {{ color:var(--soft); font-style:normal; flex:none; }}
.b42g-jump:hover {{ color:var(--cyan); }}
.b42g-bar {{ position:relative; height:13px; margin:2px 0; background:
  color-mix(in srgb, var(--hairline) 45%, transparent); border-radius:3px;
  overflow:hidden; }}
.b42g-bar i {{ position:absolute; inset:0 auto 0 0; opacity:.5; }}
.b42g-bar span {{ position:absolute; right:5px; top:0; font-size:9.5px;
  color:var(--muted); line-height:13px; }}
@media (max-width: 900px) {{
  html, body {{ overflow:auto; }}
  .b42g-stage {{ position:relative; height:70vh; }}
  .b42g-top {{ position:static; margin:8px; }}
  .b42g-side {{ position:static; width:auto; margin:8px; max-height:none; }}
  /* палец, а не курсор: кнопки и галочки крупнее, холст не отдаёт жест странице */
  .b42g-mini {{ font-size:12px; padding:7px 13px; }}
  .b42g-check {{ padding:5px 0; font-size:12px; }}
  .b42g-check input {{ width:18px; height:18px; }}
  .b42g-stage canvas {{ touch-action:none; }}
  .b42g-groups {{ max-height:none; }}
}}
</style>
{site_chrome(lang)[2]}
<script src="{av("/js/b42-graph-core.js")}"></script>
<script src="{av("/js/b42-graph.js")}" defer></script>
</body></html>"""


def has_translation(cid, c, lang, rich):
    """Есть ли на этом языке хоть что-то своё: имя или текст справочника."""
    if lang in ALWAYS_LANGS:
        return True
    if (c.get("names") or {}).get(lang):
        return True
    r = (rich or {}).get(cid) or {}
    return bool(r.get("description_popular") or r.get("history"))


def redirect_html(to):
    """Лёгкая страница-перенаправление (359 байт) — тем же приёмом, каким
    старые /tags/ уводят в /laws/."""
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
            f'<meta http-equiv="refresh" content="0;url={to}">'
            f'<link rel="canonical" href="{to}">'
            f'<title>→ {to}</title></head><body>'
            f'<a href="{to}">→</a></body></html>')


_RICH_CACHE = {}


def langs_of(cid, live, cur):
    """Языки, на которых страница этого понятия реально существует —
    переключатель показывает только их, чтобы не вести в редирект."""
    c = live["concepts"][cid]
    out = list(ALWAYS_LANGS)
    for lang in LANGS:
        if lang in out:
            continue
        if lang not in _RICH_CACHE:
            _RICH_CACHE[lang] = load_rich(lang)
        if has_translation(cid, c, lang, _RICH_CACHE[lang]):
            out.append(lang)
    return out


"""Отдельной функции редиректов больше нет.

Она лежала здесь мёртвой: обращалась к REDIRECT_LANGS, которой в этом файле не
существует, — то есть упала бы NameError при первом же вызове, если бы её кто-то
звал. Редиректы давно пишет сама build(): страница понятия без перевода на этот
язык уводит на английскую, и то же теперь делают разделы.
"""


def build(langs):
    live = json.loads(LIVE.read_text(encoding="utf-8"))
    total = 0
    for lang in langs:
        idx = G.load_index(lang)
        by_id = {}
        for a in idx:
            if a.get("version") != "popular":
                continue
            by_id[a["id"]] = a
            by_id[a["id"].split("v")[0]] = a
        rich = load_rich(lang)
        d = ROOT / "lang" / lang / "concepts"
        d.mkdir(parents=True, exist_ok=True)
        made = skipped = 0
        for cid, cv in live["concepts"].items():
            # Слитое понятие (tools/concept_twins.py) страницы не имеет — ведёт к
            # тому, во что слилось. Удалить его нельзя: на идентификатор ссылается
            # разметка тысяч статей и внешние ссылки, и без переадресации всё это
            # стало бы четырьмястами четырьмя.
            if cv.get("merged_into"):
                (d / f"{cid}.html").write_text(
                    redirect_html(f"/lang/{lang}/concepts/{cv['merged_into']}.html"),
                    encoding="utf-8")
                skipped += 1
                continue
            if has_translation(cid, cv, lang, rich):
                (d / f"{cid}.html").write_text(
                    concept_page(cid, cv, lang, live, by_id, rich, langs_of(cid, live, lang)),
                    encoding="utf-8")
                made += 1
                total += 1
            else:
                (d / f"{cid}.html").write_text(
                    redirect_html(f"/lang/en/concepts/{cid}.html"), encoding="utf-8")
                skipped += 1
        (d / "index.html").write_text(cloud_page(lang, live, by_id), encoding="utf-8")
        (d / "graph.html").write_text(graph_page(lang), encoding="utf-8")
        # Разделы — на русском и английском; остальным редирект на английский,
        # как и у самих понятий: показывать раздел с русскими подписями частей
        # французу хуже, чем честно увести на язык, который у нас полон.
        for sec in ("statistics", "math", "constant"):
            (d / f"{sec}.html").write_text(
                section_page(sec, lang, live) if lang in ALWAYS_LANGS
                else redirect_html(f"/lang/en/concepts/{sec}.html"),
                encoding="utf-8")
        print(f"  {lang}: {made} страниц + {skipped} редиректов + облако + граф + разделы")
    print(f"✅ раздел /concepts/: {total} страниц")


def main():
    _lock.acquire("tree", "страницы понятий")
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", help="один язык")
    a = ap.parse_args()
    build([a.lang] if a.lang else LANGS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
