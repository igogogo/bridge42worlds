#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Облако формул: страница каждой основной формы с полной анатомией.

Владелец 26.08: «отнестись серьёзно к облаку формул… с формулами поработай,
не забудь единицы измерений». Здесь формула перестаёт быть картинкой с латехом:

    /lang/{lang}/formula/{base_id}.html   страница формы:
        канон LaTeX (KaTeX) · карточка · ОПИСАНИЕ · ОБЛАСТЬ ПРИМЕНИМОСТИ
        разбор символов: переменная → величина (ссылка, с единицей СИ),
                         константа → константа (ссылка, значение и единица),
                         оператор → математика (ссылка)
        применения: частные записи из статей со ссылками на статьи
        понятия формы (ссылки в /concepts/)
    /lang/{lang}/formula/index.html       облако форм по применяемости

Источники: b42-ml/data/formulas-linked.json (формы, применения, понятия) и
data/formula-anatomy.json (анатомия — собирает ночной прогон; страница честно
живёт и без неё: раздел «разбор символов» просто не печатается, пока анатомии нет).

СТАРЫЙ раздел /formulas/ (сводка-справочник) НЕ трогается — механизмы дополняем.

    python formulas_pages.py [--lang ru]
"""
import argparse
import html as H
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ML = ROOT.parent / "b42-ml"
sys.path.insert(0, str(ROOT))
from concepts_pages import head, name_of, KIND_LBL, site_chrome  # noqa: E402
import generate as G   # noqa: E402 — действия и отклик теми же функциями

# формулы — те же два языка, что и понятия; остальным редирект (см. concepts_pages)
LANGS = ("ru", "en")
REDIRECT_LANGS = ("es", "ar", "fr")

T = {
    "ru": {"title": "Формулы", "sub": "Основные формы: {n}. У каждой — разбор символов "
                    "с единицами, описание и границы применимости.",
           "desc": "Что утверждает", "appl": "Где работает и где ломается",
           "sym": "Разбор символов", "uses": "Применения в статьях",
           "concepts": "Понятия", "var": "переменная", "const": "константа",
           "op": "оператор", "unit_lbl": "единица", "val": "значение", "art": "статья"},
    "en": {"title": "Formulas", "sub": "Canonical forms: {n}. Each with symbol anatomy, "
                    "units, meaning and limits of applicability.",
           "desc": "What it states", "appl": "Where it works and where it breaks",
           "sym": "Symbols", "uses": "Uses in articles",
           "concepts": "Concepts", "var": "variable", "const": "constant",
           "op": "operator", "unit_lbl": "unit", "val": "value", "art": "article"},
    "es": {"title": "Fórmulas", "sub": "Formas canónicas: {n}.",
           "desc": "Qué afirma", "appl": "Dónde funciona y dónde falla",
           "sym": "Símbolos", "uses": "Usos en artículos",
           "concepts": "Conceptos", "var": "variable", "const": "constante",
           "op": "operador", "unit_lbl": "unidad", "val": "valor", "art": "artículo"},
    "ar": {"title": "الصيغ", "sub": "الصيغ الأساسية: {n}.",
           "desc": "ماذا تقول", "appl": "أين تعمل وأين تنهار",
           "sym": "الرموز", "uses": "تطبيقات في المقالات",
           "concepts": "مفاهيم", "var": "متغير", "const": "ثابت",
           "op": "مؤثر", "unit_lbl": "وحدة", "val": "قيمة", "art": "مقالة"},
    "fr": {"title": "Formules", "sub": "Formes canoniques : {n}.",
           "desc": "Ce qu'elle affirme", "appl": "Où elle marche et où elle casse",
           "sym": "Symboles", "uses": "Usages dans les articles",
           "concepts": "Concepts", "var": "variable", "const": "constante",
           "op": "opérateur", "unit_lbl": "unité", "val": "valeur", "art": "article"},
}


def load_all():
    bases = json.loads((ML / "data/formulas-linked.json").read_text(encoding="utf-8"))["bases"]
    p = ROOT / "data" / "formula-anatomy.json"
    anatomy = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    live = json.loads((ROOT / "data/concepts-live.json").read_text(encoding="utf-8"))
    return bases, anatomy, live


def concept_link(cid, lang, live, cls="side-tag"):
    c = live["concepts"].get(cid)
    label = name_of(c, cid, lang) if c else cid.replace("_", " ")
    if not c:
        return H.escape(label)
    return (f'<a href="/lang/{lang}/concepts/{H.escape(cid)}.html" class="{cls}">'
            f'{H.escape(label)}</a>')


def _ru_m(an, lang, kind_key, i, fallback):
    """m-поле символа на языке страницы: перевод из блока ru (cards_translate_ru)
    по индексу, иначе английский оригинал."""
    if lang != "ru":
        return fallback
    tr = (an.get("ru") or {}).get(kind_key) or []
    return tr[i] if i < len(tr) and tr[i] else fallback


def sym_rows(an, lang, live, t):
    """Таблица разбора: символ · что это · куда ведёт. Единицы — обязательны
    (владелец: «не забудь единицы измерений»)."""
    rows = []
    for i, v in enumerate(an.get("variables") or []):
        unit = v.get("unit") or ""
        unit_html = ""
        if unit and unit != "dimensionless":
            unit_html = (" · " + t["unit_lbl"] + ": "
                         + concept_link(unit, lang, live, "side-law")
                         if live["concepts"].get(unit) else f" · {t['unit_lbl']}: {H.escape(unit.replace('_', ' '))}")
        target = (concept_link(v["id"], lang, live) if v.get("id") and live["concepts"].get(v["id"])
                  else H.escape((v.get("id") or "").replace("_", " ")))
        m = _ru_m(an, lang, "variables", i, v.get("m", ""))
        rows.append(f'<tr><td class="fx-s">{H.escape(v["s"])}</td>'
                    f'<td>{t["var"]}</td><td>{H.escape(m)}'
                    f'{(" — " + target) if target else ""}{unit_html}</td></tr>')
    for i, c in enumerate(an.get("constants") or []):
        val = f' = {H.escape(c["value"])}' if c.get("value") else ""
        unit = c.get("unit") or ""
        unit_html = f' {H.escape(unit.replace("_", " "))}' if unit and unit != "dimensionless" else ""
        m = _ru_m(an, lang, "constants", i, c.get("m", ""))
        desc = f' — {H.escape(m)}' if m else ""
        rows.append(f'<tr><td class="fx-s">{H.escape(c["s"])}</td>'
                    f'<td>{t["const"]}</td>'
                    f'<td>{concept_link(c.get("id") or "", lang, live)}{val}{unit_html}'
                    f'{desc}</td></tr>')
    for i, o in enumerate(an.get("operators") or []):
        m = _ru_m(an, lang, "operators", i, o.get("m", ""))
        desc = f' — {H.escape(m)}' if m else ""
        rows.append(f'<tr><td class="fx-s">{H.escape(o["s"])}</td>'
                    f'<td>{t["op"]}</td>'
                    f'<td>{concept_link(o.get("id") or "", lang, live)}{desc}</td></tr>')
    return rows


def formula_page(b, an, lang, live):
    t = T[lang]
    name = b.get("name") or b["base_id"]
    out = [head(lang, name)]
    out.append('<div class="tag-header">')
    out.append(f'<div class="tag-title-row"><h1>{H.escape(name)}</h1></div>')
    out.append(f'<div class="formula" style="font-size:20px;margin:12px 0">'
               f'$${H.escape(b.get("latex", ""))}$$</div>')
    _card_ru = (an.get("ru") or {}).get("card") if lang == "ru" else None
    out.append(f'<p class="desc" lang="{"ru" if _card_ru else "en"}">'
               f'{H.escape(_card_ru or b.get("card", ""))}</p>')
    out.append('</div>')

    body = []
    # текст на языке страницы: русский из блока ru (cards_translate_ru), иначе en
    _ru = an.get("ru") or {}
    def _txt(field):
        if lang == "ru" and _ru.get(field):
            return _ru[field], "ru"
        return an.get(field, ""), "en"
    if an.get("description"):
        txt, tl = _txt("description")
        body.append(f'<div class="section"><h2 style="font-size:16px;margin:14px 0 6px">'
                    f'{t["desc"]}</h2><p lang="{tl}">'
                    f'{H.escape(txt)}</p></div>')
    if an.get("history"):
        hist_lbl = {"ru": "История", "en": "History", "es": "Historia",
                    "ar": "التاريخ", "fr": "Histoire"}[lang]
        txt, tl = _txt("history")
        body.append(f'<div class="section"><h2 style="font-size:16px;margin:14px 0 6px">'
                    f'{hist_lbl}</h2><p lang="{tl}">'
                    f'{H.escape(txt)}</p></div>')
    if an.get("applicability"):
        txt, tl = _txt("applicability")
        body.append(f'<div class="section"><h2 style="font-size:16px;margin:14px 0 6px">'
                    f'{t["appl"]}</h2><p lang="{tl}">'
                    f'{H.escape(txt)}</p></div>')
    rows = sym_rows(an, lang, live, t)
    if rows:
        body.append(f'<h2 style="font-size:16px;margin:14px 0 6px">{t["sym"]}</h2>'
                    f'<table style="border-collapse:collapse;font-size:14px">'
                    + "".join(rows) + '</table>'
                    + '<style>.fx-s{font-family:var(--mono);padding:3px 12px 3px 0}'
                      'td{padding:3px 12px 3px 0;border-bottom:1px solid var(--hair)}</style>')
    # В других системах единиц (владелец 27.08: «формулы могут быть представлены
    # в разных системах — надо доводить до ума»). Данные — formula_anatomy --systems;
    # пустой список = проверено, форма всюду одна, блока нет.
    if an.get("unit_systems"):
        US_LBL = {"ru": "В других системах единиц", "en": "In other unit systems",
                  "es": "En otros sistemas de unidades",
                  "ar": "في أنظمة وحدات أخرى", "fr": "Dans d'autres systèmes d'unités"}
        US_NAME = {"si": "SI", "gaussian": "Gaussian CGS", "planck": "Planck",
                   "natural": "natural units", "atomic": "atomic units"}
        srows = []
        for i, u in enumerate(an["unit_systems"]):
            sysid = {"si": "si_units", "gaussian": "gaussian_units",
                     "planck": "planck_units", "natural": "natural_units",
                     "atomic": "atomic_units"}.get(u["system"], "")
            sn = US_NAME.get(u["system"], u["system"])
            slink = (f'<a href="/lang/{lang}/concepts/{sysid}.html">{sn}</a>'
                     if sysid else H.escape(sn))
            nt = _ru_m(an, lang, "system_notes", i, u.get("note", ""))
            ntl = "ru" if (lang == "ru" and nt != u.get("note", "")) else "en"
            note = (f' <span style="color:var(--soft)" lang="{ntl}">— '
                    f'{H.escape(nt)}</span>' if nt else "")
            srows.append(f'<div style="margin:8px 0"><b style="font-family:var(--mono);'
                         f'font-size:11.5px">{slink}</b>'
                         f'<div class="formula" style="margin:4px 0">'
                         f'$${H.escape(u["latex"])}$$</div>{note}</div>')
        body.append(f'<h2 style="font-size:16px;margin:14px 0 6px">'
                    f'{US_LBL.get(lang, US_LBL["en"])}</h2>' + "".join(srows))
    # МИНИ-ГРАФ формулы: сама форма + понятия, которые она связывает
    _mini = ["f:" + b["base_id"]] + [c["concept"] for c in (b.get("concepts") or [])[:8]]
    if len(_mini) >= 3:
        body.append(f'<div class="b42mini" data-ids="{H.escape(",".join(_mini))}" '
                    f'data-focus="f:{H.escape(b["base_id"])}"></div>')
    if b.get("concepts"):
        chips = " ".join(concept_link(c["concept"], lang, live) for c in b["concepts"][:4])
        body.append(f'<div class="related-tags" style="margin-top:12px">'
                    f'<b style="font-family:var(--mono);font-size:11px;color:var(--muted)">'
                    f'{t["concepts"]}:</b> {chips}</div>')
    apps = b.get("applications") or []
    if apps:
        rows = []
        for a in apps[:10]:
            art = a.get("article") or a.get("art") or ""
            link = (f' · <a href="/lang/{lang}/index.html?q={H.escape(art)}">{H.escape(art)}</a>'
                    if art else "")
            rec = (a.get("record") or "")[:140]
            rows.append(f'<div style="font-size:13px;'
                        f'color:var(--soft);margin:4px 0">'
                        f'<span style="display:inline-block;max-width:100%;overflow-x:auto">'
                        + chr(92) + f'({H.escape(rec)}' + chr(92) + f')</span>{link}</div>')
        body.append(f'<h2 style="font-size:16px;margin:14px 0 6px">{t["uses"]}</h2>'
                    + "".join(rows))
    # действия/отклик/футер — как у понятия и статьи (единый функционал сайта)
    _like = f"formula_{b['base_id']}_{lang}"
    body.append(G.build_actions_html(_like, b["base_id"], lang, "tag", inline_comment=True))
    body.append(G.build_feedback_html(_like, lang, "tag", inline_toggle=True))
    out.append('<div class="entity-body">' + "".join(body) + '</div>')
    out.append(site_chrome(lang)[1])
    out.append(site_chrome(lang)[2])
    out.append('<script src="/js/b42-graph-core.js"></script>'
               '<script src="/js/b42-mini.js" defer></script>')
    out.append("</body></html>")
    return "".join(out)


def cloud(bases, lang, live):
    t = T[lang]
    out = [head(lang, t["title"])]
    out.append(f'<h1>{t["title"]}</h1>'
               f'<div class="subtitle">{t["sub"].format(n=len(bases))}</div>')
    # Разделы (владелец 27.08: «список по разделам как-то»): форма наследует раздел
    # от своего первого понятия — его группа верхнего уровня. Подпись раздела — три
    # крупнейших члена группы, как в смотровой. Формы без привязки — в «прочее».
    groups = live.get("groups") or {}
    def section_of(b):
        for c in (b.get("concepts") or []):
            sup = (live["concepts"].get(c["concept"], {}) or {}).get("supers") or []
            if sup:
                return str(sup[0])
        return None
    def label_of(gid):
        members = groups.get(gid) or []
        big = sorted(members,
                     key=lambda m: -len(live["concepts"].get(m, {}).get("articles", [])))[:3]
        return " · ".join(name_of(live["concepts"][m], m, lang)
                          for m in big if m in live["concepts"]) or gid
    by_sec = {}
    for b in bases:
        by_sec.setdefault(section_of(b), []).append(b)
    ordered = sorted(((g, bs) for g, bs in by_sec.items() if g is not None),
                     key=lambda kv: -len(kv[1]))
    if None in by_sec:
        ordered.append((None, by_sec[None]))
    other = {"ru": "Прочее", "en": "Other", "es": "Otros", "ar": "أخرى", "fr": "Autres"}[lang]
    for gid, bs in ordered:
        out.append(f'<h2 style="font-family:var(--serif);font-size:18px;'
                   f'margin:26px 0 10px">{H.escape(label_of(gid) if gid else other)} '
                   f'<span style="font-family:var(--mono);font-size:12px;'
                   f'color:var(--soft)">· {len(bs)}</span></h2>')
        _emit_rows(out, bs, lang)
    out.append(site_chrome(lang)[1])
    out.append(site_chrome(lang)[2])
    out.append("</body></html>")
    return "".join(out)


def _emit_rows(out, bases, lang):
    for b in sorted(bases, key=lambda x: -len(x.get("applications") or [])):
        uses = len(b.get("applications") or [])
        out.append(f'<div style="margin-bottom:10px">'
                   f'<a href="/lang/{lang}/formula/{H.escape(b["base_id"])}.html" '
                   f'style="font-family:var(--serif);font-size:16px">'
                   f'{H.escape(b.get("name") or b["base_id"])}</a> '
                   f'<span style="font-family:var(--mono);font-size:12px;color:var(--soft)">'
                   f'· {uses}</span><br>'
                   # Латех в облаке РЕНДЕРИТСЯ (владелец 27.08: «в списке формат не
                   # латех»). Не режем: обрезанный латех ломает KaTeX; узкий рендер
                   # прокручивается своим контейнером по канону сайта.
                   f'<span style="display:inline-block;max-width:100%;overflow-x:auto">'
                   rf'\({H.escape(b.get("latex") or "")}\)</span></div>')


def build(langs):
    bases, anatomy, live = load_all()
    for lang in langs:
        d = ROOT / "lang" / lang / "formula"
        d.mkdir(parents=True, exist_ok=True)
        for b in bases:
            an = anatomy.get(b["base_id"]) or {}
            (d / f'{b["base_id"]}.html').write_text(
                formula_page(b, an, lang, live), encoding="utf-8")
        (d / "index.html").write_text(cloud(bases, lang, live), encoding="utf-8")
        print(f"  {lang}: {len(bases)} формул + облако")
    print(f"✅ раздел /formula/: {len(bases) * len(langs)} страниц · "
          f"анатомий готово {len(anatomy)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang")
    a = ap.parse_args()
    build([a.lang] if a.lang else LANGS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
