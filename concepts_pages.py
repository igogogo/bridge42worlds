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
LANGS = ("ru", "en", "es", "ar", "fr")
CARDS_CAP = 40

sys.path.insert(0, str(ROOT))
import generate as G   # entity_article_card, load_index — свои карточки, не вторая копия

KIND_LBL = {
    "ru": {"concept": "понятие", "object": "объект", "method": "метод", "instrument": "прибор",
           "substance": "вещество", "math": "математика", "phenomenon": "явление",
           "law": "закон", "equation": "уравнение", "effect": "эффект", "principle": "принцип",
           "theorem": "теорема", "process": "процесс", "property": "свойство", "theory": "теория",
           "quantity": "величина", "constant": "константа", "unit": "единица",
           "unit_system": "система единиц"},
    "es": {"concept": "concepto", "object": "objeto", "method": "método", "instrument": "instrumento",
           "substance": "sustancia", "math": "matemáticas", "phenomenon": "fenómeno",
           "law": "ley", "equation": "ecuación", "effect": "efecto", "principle": "principio",
           "theorem": "teorema", "process": "proceso", "property": "propiedad", "theory": "teoría",
           "quantity": "magnitud", "constant": "constante", "unit": "unidad",
           "unit_system": "sistema de unidades"},
    "fr": {"concept": "concept", "object": "objet", "method": "méthode", "instrument": "instrument",
           "substance": "substance", "math": "mathématiques", "phenomenon": "phénomène",
           "law": "loi", "equation": "équation", "effect": "effet", "principle": "principe",
           "theorem": "théorème", "process": "processus", "property": "propriété", "theory": "théorie",
           "quantity": "grandeur", "constant": "constante", "unit": "unité",
           "unit_system": "système d'unités"},
    "ar": {"concept": "مفهوم", "object": "جسم", "method": "طريقة", "instrument": "جهاز",
           "substance": "مادة", "math": "رياضيات", "phenomenon": "ظاهرة",
           "law": "قانون", "equation": "معادلة", "effect": "تأثير", "principle": "مبدأ",
           "theorem": "مبرهنة", "process": "عملية", "property": "خاصية", "theory": "نظرية",
           "quantity": "كمية", "constant": "ثابت", "unit": "وحدة",
           "unit_system": "نظام وحدات"},
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


def head(lang, title):
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
<link rel="stylesheet" href="/css/style.css">
<link rel="icon" href="/favicon.ico" sizes="any">
</head>
<body>
<div class="top-bar">
  <a href="/lang/{lang}/index.html" class="logo">bridge42worlds</a>
  <div class="header-right"><div class="nav-links">
    <a href="/lang/{lang}/index.html">main</a>
    <a href="/lang/{lang}/concepts/">concepts</a>
    <a href="/lang/{lang}/scientists/">scientists</a>
    <a href="/lang/{lang}/sections/">sections</a>
  </div></div>
</div>
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


def concept_page(cid, c, lang, live, by_id, rich=None):
    t = T[lang]
    name = name_of(c, cid, lang)
    kind = KIND_LBL.get(lang, {}).get(c["kind"], c["kind"])
    foreign = lang != "en" and not c["names"].get(lang)
    note = f' <span class="tag-ver" style="font-size:11px">{t["en_note"]}</span>' if foreign and t["en_note"] else ""

    out = [head(lang, name)]
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
            panes.append((label, f'<p style="max-width:var(--w-read)">{linked}</p>'))
    # ВКЛАДКИ вместо простыни секций (владелец 27.08: «полная карточка тоже с
    # вкладками»). Без JS видны все секции с заголовками; скрипт внизу страницы
    # превращает их в панель вкладок — деградация бесплатная.
    if len(panes) > 1:
        tabs = "".join(f'<button class="ent-tab{" active" if i == 0 else ""}" '
                       f'data-pane="p{i}">{H.escape(lbl)}</button>'
                       for i, (lbl, _) in enumerate(panes))
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
    out.append('<script src="/js/icons.js"></script><script src="/js/search.js" defer></script>'
               '<script src="/js/likes.js" defer></script>')
    # Вкладки полной записи: включаются только при JS, иначе секции остаются простынёй
    out.append("""<script>(function(){
var bar=document.querySelector('.ent-tabs');if(!bar)return;
document.body.classList.add('ent-tabs-on');
bar.addEventListener('click',function(e){
  var b=e.target.closest('.ent-tab');if(!b)return;
  bar.querySelectorAll('.ent-tab').forEach(function(x){x.classList.toggle('active',x===b)});
  document.querySelectorAll('.ent-pane').forEach(function(p){
    p.classList.toggle('active',p.dataset.pane===b.dataset.pane)});
});
var first=document.querySelector('.ent-pane');if(first)first.classList.add('active');
})();</script>""")
    out.append("</body></html>")
    return "".join(out)


def cloud_page(lang, live, by_id):
    t = T[lang]
    c = live["concepts"]
    out = [head(lang, t["title"])]
    out.append(f'<h1>{t["title"]}</h1>')
    out.append(f'<div class="subtitle">{t["sub"].format(n=len(c), g=len(live["groups"]))}</div>')
    groups = sorted(live["groups"].items(), key=lambda kv: -len(kv[1]))
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
    out.append("</body></html>")
    return "".join(out)


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
        for cid, cv in live["concepts"].items():
            (d / f"{cid}.html").write_text(concept_page(cid, cv, lang, live, by_id, rich),
                                           encoding="utf-8")
            total += 1
        (d / "index.html").write_text(cloud_page(lang, live, by_id), encoding="utf-8")
        print(f"  {lang}: {len(live['concepts'])} страниц + облако")
    print(f"✅ раздел /concepts/: {total} страниц")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", help="один язык")
    a = ap.parse_args()
    build([a.lang] if a.lang else LANGS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
