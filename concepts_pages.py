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
           "theorem": "теорема", "process": "процесс", "property": "свойство", "theory": "теория"},
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


def concept_page(cid, c, lang, live, by_id):
    t = T[lang]
    name = name_of(c, cid, lang)
    kind = KIND_LBL.get(lang, {}).get(c["kind"], c["kind"])
    foreign = lang != "en" and not c["names"].get(lang)
    note = f' <span class="tag-ver" style="font-size:11px">{t["en_note"]}</span>' if foreign and t["en_note"] else ""

    out = [head(lang, name)]
    out.append('<div class="tag-header">')
    out.append(f'<div class="tag-title-row"><h1>{H.escape(name)}{note}</h1></div>')
    out.append(f'<div class="tag-stats">{H.escape(kind)} · {len(c["articles"])} '
               f'{t["articles"].lower()}</div>')
    # карточка — по-английски до перевода, честно размечено lang
    out.append(f'<p class="desc" lang="en">{H.escape(c["card_en"])}</p>')
    out.append('</div>')

    body = []
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
    out.append('<script src="/js/icons.js"></script><script src="/js/search.js" defer></script>')
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
        d = ROOT / "lang" / lang / "concepts"
        d.mkdir(parents=True, exist_ok=True)
        for cid, cv in live["concepts"].items():
            (d / f"{cid}.html").write_text(concept_page(cid, cv, lang, live, by_id),
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
