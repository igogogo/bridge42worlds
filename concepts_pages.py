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
LANGS = ("ru", "en", "es", "ar", "fr")
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
    scripts = (f'<script src="{av("/js/likes.js")}"></script>'
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


def head(lang, title, body_class="entity-page", page_langs=None):
    d = "rtl" if lang == "ar" else "ltr"
    return f"""<!DOCTYPE html>
<html lang="{lang}" dir="{d}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{H.escape(title)} — bridge42worlds</title>
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


def concept_page(cid, c, lang, live, by_id, rich=None, page_langs=None):
    t = T[lang]
    name = name_of(c, cid, lang)
    kind = KIND_LBL.get(lang, {}).get(c["kind"], c["kind"])
    foreign = lang != "en" and not c["names"].get(lang)
    note = f' <span class="tag-ver" style="font-size:11px">{t["en_note"]}</span>' if foreign and t["en_note"] else ""

    out = [head(lang, name, page_langs=page_langs or list(ALWAYS_LANGS))]
    out.append('<div class="tag-header">')
    # Класс понятия — бейджем ПЕРЕД названием: владелец 26.08 «у понятий был класс,
    # метод, принцип и так далее — они остались?» Остались у всех 1222; бейдж делает
    # это видимым, а не строкой мелкого шрифта.
    out.append(f'<div class="tag-title-row">'
               f'<span class="entity-kind" style="font-family:var(--mono);font-size:11.5px;'
               f'color:var(--cyan);border:1px solid currentColor;border-radius:999px;'
               f'padding:2px 10px;align-self:center">{H.escape(kind)}</span>'
               f'<h1>{H.escape(name)}{note}</h1></div>')
    # КАРТОЧКА понятия — выделенным определением, а не строчкой между служебных:
    # это главный текст страницы, пока перевод не приехал — по-английски с пометкой.
    # Эпиграф — на языке страницы, когда перевод карточки уже есть (full_i18n)
    _card_tr = ((c.get("full_i18n") or {}).get(lang) or {}).get("card")
    _card_lang = lang if _card_tr else "en"
    out.append(f'<blockquote class="concept-card" lang="{_card_lang}" style="font-family:var(--serif);'
               f'font-size:18px;line-height:1.55;margin:var(--s-3) 0;padding:var(--s-3) var(--s-4);'
               f'background:var(--bg);'
               f'border-radius:var(--radius-sm)">{H.escape(_card_tr or c["card_en"])}</blockquote>')
    stats = [f'{len(c["articles"])} {t["articles"].lower()}']
    if c["formulas"]:
        stats.append(f'{len(c["formulas"])} {t["formulas"].lower()}')
    if c["scientists"]:
        stats.append(f'{len(c["scientists"])} {t["sci"].lower()}')
    out.append(f'<div class="tag-stats">{" · ".join(stats)}</div>')
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
    # ВКЛАДКИ вместо простыни секций (владелец 27.08: «полная карточка тоже с
    # вкладками»). Без JS видны все секции с заголовками; скрипт внизу страницы
    # превращает их в панель вкладок — деградация бесплатная.
    if len(panes) > 1:
        all_lbl = {"ru": "всё сразу", "en": "all at once", "es": "todo",
                   "ar": "الكل", "fr": "tout"}.get(lang, "all at once")
        tabs = "".join(f'<button class="ent-tab{" active" if i == 0 else ""}" '
                       f'data-pane="p{i}">{H.escape(lbl)}</button>'
                       for i, (lbl, _) in enumerate(panes))
        tabs += f'<button class="ent-tab ent-all-btn" id="ent-all">{all_lbl}</button>'
        content = "".join(f'<div class="ent-pane" data-pane="p{i}">'
                          f'<h2 class="ent-pane-t" style="font-size:16px;margin:14px 0 6px">'
                          f'{H.escape(lbl)}</h2>{html}</div>'
                          for i, (lbl, html) in enumerate(panes))
        body.append(f'<div class="ent-tabs" role="tablist">{tabs}</div>{content}')
    elif panes:
        body.append(f'<div class="section"><h2 style="font-size:16px;margin:14px 0 6px">'
                    f'{panes[0][0]}</h2>{panes[0][1]}</div>')
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
    if c.get("systems"):
        chips = "".join(
            f'<a href="/lang/{lang}/concepts/{s}_units.html">{SYS_NAME.get(s, s)}</a>'
            for s in c["systems"])
        sd = (f' <span style="color:var(--soft);font-size:13px" lang="en">'
              f'{H.escape(c.get("si_definition") or "")}</span>'
              if c.get("si_definition") else "")
        body.append(f'<div class="related-tags"><b style="font-family:var(--mono);'
                    f'font-size:11px;color:var(--muted)">'
                    f'{SYS_LBL.get(lang, "Systems")}:</b> {chips}{sd}</div>')
    if c.get("units_by_system"):
        cells = " · ".join(
            f'{SYS_NAME.get(s, s)}: <a href="/lang/{lang}/concepts/{H.escape(u)}.html">'
            f'{H.escape(u.replace("_", " "))}</a>'
            for s, u in c["units_by_system"].items() if u)
        if cells:
            body.append(f'<div class="related-tags"><b style="font-family:var(--mono);'
                        f'font-size:11px;color:var(--muted)">'
                        f'{UNITS_LBL.get(lang, "Units")}:</b> {cells}</div>')
    # МИНИ-ГРАФ понятия (27.08): само понятие + соседи первого уровня + его
    # формулы. Тот же движок и вид, что у большого графа (js/b42-mini.js).
    _mini = [cid] + [r["id"] for r in (c.get("related") or [])[:10]]
    _mini += [f'f:{f["id"]}' for f in (c.get("formulas") or [])[:3]]
    if len(_mini) >= 3:
        GT = GRAPH_T.get(lang, GRAPH_T["en"])
        body.append(
            f'<div class="b42mini" data-ids="{H.escape(",".join(_mini))}" '
            f'data-focus="{H.escape(cid)}"></div>'
            f'<div class="b42mini-note"><a href="/lang/{lang}/concepts/graph.html">'
            f'{GT["title"]} &rarr;</a></div>')
    if c["related"]:
        chips = "".join(
            f'<a href="/lang/{lang}/concepts/{H.escape(r["id"])}.html">'
            f'{H.escape(name_of(live["concepts"].get(r["id"], {"names": {}}), r["id"], lang))}</a>'
            for r in c["related"])
        body.append(f'<div class="related-tags"><b style="font-family:var(--mono);'
                    f'font-size:11px;color:var(--muted)">{t["related"]}:</b> {chips}</div>')
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
            rows.append(f'<div class="formula" style="margin-bottom:12px">'
                        f'<div style="font-family:var(--mono)">$${H.escape(f["latex"])}$$</div>'
                        f'<div style="font-size:13.5px;color:var(--soft)" lang="en">{H.escape(f["card"])}</div>'
                        f'{apps}</div>')
        body.append(f'<h2 style="font-size:16px;margin:14px 0 8px">{t["formulas"]}</h2>' + "".join(rows))
    # ДЕЙСТВИЯ И ОТКЛИК — те же функции, что у статьи и старых справочников
    # (владелец 27.08: «много функционала упущено — функционал тот же»).
    # Реакции, избранное, «поделиться», форма комментария; обрабатывает likes.js.
    _like = f"concept_{cid}_{lang}"
    body.append(G.build_actions_html(_like, cid, lang, "tag", inline_comment=True))
    body.append(G.build_feedback_html(_like, lang, "tag", inline_toggle=True))
    if body:
        out.append('<div class="entity-body">' + "".join(body) + '</div>')

    arts = [by_id[a] for a in c["articles"] if a in by_id]
    arts.sort(key=lambda a: a.get("date") or "", reverse=True)
    out.append(f'<h2 class="section-title">{t["articles"]}'
               f'<span style="font-family:var(--mono);font-size:13px;color:var(--soft)"> · '
               f'{len(arts)}</span></h2>')
    if arts:
        out.append("".join(G.entity_article_card(a, lang) for a in arts[:CARDS_CAP]))
    else:
        out.append(f'<p style="color:var(--soft)">{t["none"]}</p>')
    out.append(site_chrome(lang)[1])          # футер сайта
    out.append(site_chrome(lang)[2])          # лайки, иконки, поиск, «ещё»
    out.append('<script src="{av("/js/b42-graph-core.js")}"></script>'
               '<script src="{av("/js/b42-mini.js")}" defer></script>')
    # Вкладки полной записи. Скрываем НЕ через display:none, а атрибутом
    # hidden="until-found": браузер ищет текст и внутри скрытой панели, а найдя —
    # шлёт beforematch, и мы раскрываем именно её (владелец 27.08: «вкладки —
    # круто, но поиск же это не найдёт»). Плюс кнопка «всё сразу» — для тех, кто
    # читает подряд, и для браузеров без поддержки until-found. Без JS панель
    # вкладок скрыта и все секции видны простынёй, как раньше.
    out.append("""<script>(function(){
var bar=document.querySelector('.ent-tabs');if(!bar)return;
var panes=[].slice.call(document.querySelectorAll('.ent-pane'));
if(!panes.length)return;
document.body.classList.add('ent-tabs-on');
function hide(p){try{p.hidden='until-found';}catch(e){p.hidden=true;}}
function activate(id){
  bar.querySelectorAll('.ent-tab').forEach(function(x){
    if(x.id!=='ent-all')x.classList.toggle('active',x.dataset.pane===id);});
  panes.forEach(function(p){if(p.dataset.pane===id)p.hidden=false;else hide(p);});
}
panes.forEach(function(p){
  p.addEventListener('beforematch',function(){
    document.body.classList.remove('ent-all');
    activate(p.dataset.pane);});
});
bar.addEventListener('click',function(e){
  var b=e.target.closest('.ent-tab');if(!b||b.id==='ent-all')return;
  document.body.classList.remove('ent-all');
  document.getElementById('ent-all').classList.remove('active');
  activate(b.dataset.pane);
});
var all=document.getElementById('ent-all');
if(all)all.addEventListener('click',function(){
  var on=document.body.classList.toggle('ent-all');
  all.classList.toggle('active',on);
  if(on)panes.forEach(function(p){p.hidden=false;});
  else{var a=bar.querySelector('.ent-tab.active');activate(a?a.dataset.pane:panes[0].dataset.pane);}
});
activate(panes[0].dataset.pane);
})();</script>""")
    out.append("</body></html>")
    return "".join(out)


def cloud_page(lang, live, by_id):
    t = T[lang]
    c = live["concepts"]
    out = [head(lang, t["title"])]
    out.append(f'<h1>{t["title"]}</h1>')
    gt = GRAPH_T.get(lang, GRAPH_T["en"])
    out.append(f'<div class="subtitle">{t["sub"].format(n=len(c), g=len(live["groups"]))}'
               f' &nbsp;<a href="/lang/{lang}/concepts/graph.html" '
               f'style="font-family:var(--mono);font-size:12.5px">{gt["title"]} →</a></div>')
    groups = sorted(live["groups"].items(), key=lambda kv: -len(kv[1]))
    # Контейнер результатов поиска НЕ ставим: search.js, найдя пустой
    # #search-results, наполняет его лентой статей — на облаке понятий
    # это чужой список (замер 27.08: 12 карточек ниоткуда). Поиск здесь
    # работает через site-search (переход на главную с запросом).
    for gid, members in groups:
        members = sorted(members, key=lambda m: -len(c.get(m, {}).get("articles", [])))
        top3 = " · ".join(name_of(c[m], m, lang) for m in members[:3] if m in c)
        chips = "".join(
            f'<a href="/lang/{lang}/concepts/{H.escape(m)}.html">'
            f'{H.escape(name_of(c[m], m, lang))} <em style="opacity:.55;font-size:10.5px">'
            f'{len(c[m]["articles"])}</em></a>'
            for m in members if m in c and c[m]["articles"])
        out.append(f'<details style="margin-bottom:10px"><summary style="cursor:pointer;'
                   f'font-family:var(--serif);font-size:16px">{H.escape(top3)} '
                   f'<span style="font-family:var(--mono);font-size:12px;color:var(--soft)">'
                   f'· {len(members)}</span></summary>'
                   f'<div class="related-tags" style="margin-top:8px">{chips}</div></details>')
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


def write_redirects(live):
    """es/ar/fr: каждая страница понятия ведёт на английскую."""
    n = 0
    for lang in REDIRECT_LANGS:
        d = ROOT / "lang" / lang / "concepts"
        d.mkdir(parents=True, exist_ok=True)
        for cid in live["concepts"]:
            (d / f"{cid}.html").write_text(
                redirect_html(f"/lang/en/concepts/{cid}.html"), encoding="utf-8")
            n += 1
        (d / "index.html").write_text(
            redirect_html("/lang/en/concepts/"), encoding="utf-8")
        (d / "graph.html").write_text(
            redirect_html("/lang/en/concepts/graph.html"), encoding="utf-8")
    print(f"  редиректов es/ar/fr: {n}")


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
        print(f"  {lang}: {made} страниц + {skipped} редиректов + облако + граф")
    print(f"✅ раздел /concepts/: {total} страниц")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", help="один язык")
    a = ap.parse_args()
    build([a.lang] if a.lang else LANGS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
