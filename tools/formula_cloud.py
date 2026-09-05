"""Облако формул: страница /formulas/ на всех языках.

Владелец 2026-08-04: «собирай слой и делай облако формул. Туда отлично ляжет математика:
формулы, теоремы, обозначения — связь наук, их единство».

Что показываем и в каком порядке — решение осмысленное, а не «все подряд по алфавиту»:

1. **МОСТЫ** — формулы, встречающиеся в РАЗНЫХ статьях, наверху и крупно. Их всего 15 из
   1218, и это самое ценное, что есть в слое: закон Хаббла связывает десять работ, которые
   между собой ничем больше не связаны. Ради этого облако и делается.
2. **ПО ОБОЗНАЧЕНИЯМ** — группировка по буквам, которые в формуле участвуют. Это и есть
   «единство науки» в чистом виде: работы про чёрные дыры и про элементарные частицы
   делят символ c, и видно, что физика одна.
3. **ОСТАЛЬНЫЕ** — по алфавиту канонической записи, чтобы страница была полной.

Формула рендерится KaTeX, как в статье. Под ней — человеческое объяснение и ссылки на
статьи, где она встречается: формула без объяснения на научпоп-сайте бесполезна.

    python tools/formula_cloud.py            собрать страницы на все языки
    python tools/formula_cloud.py --lang ru  только русскую
"""
import argparse
import html
import json
import sys
from collections import defaultdict
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "formulas.json"
# Импорт common работает из любой папки, а не только из корня репозитория.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
from common import ALL_LANGS  # noqa: E402
LANGS = ALL_LANGS   # список языков один на проект: config.json через common.ALL_LANGS

L10N = {
    "ru": {"title": "Формулы", "lead": "Формулы из наших статей. Одна формула часто связывает работы, "
                                       "которые больше ничем не пересекаются — в этом и видно единство науки.",
           "bridges": "Формулы-мосты", "bridges_note": "встречаются в нескольких статьях",
           "symbols": "По обозначениям", "all": "Все формулы", "in": "в статьях", "art": "статей"},
    "en": {"title": "Formulas", "lead": "Formulas from our articles. One formula often links papers that "
                                        "share nothing else — this is where the unity of science shows.",
           "bridges": "Bridging formulas", "bridges_note": "appear in several articles",
           "symbols": "By notation", "all": "All formulas", "in": "in articles", "art": "articles"},
    "es": {"title": "Fórmulas", "lead": "Fórmulas de nuestros artículos. Una misma fórmula suele unir "
                                        "trabajos que no comparten nada más: ahí se ve la unidad de la ciencia.",
           "bridges": "Fórmulas puente", "bridges_note": "aparecen en varios artículos",
           "symbols": "Por notación", "all": "Todas las fórmulas", "in": "en artículos", "art": "artículos"},
    "ar": {"title": "الصيغ", "lead": "صيغ من مقالاتنا. الصيغة الواحدة تربط غالبًا أبحاثًا لا يجمعها شيء آخر — "
                                     "وهنا تظهر وحدة العلم.",
           "bridges": "صيغ جسر", "bridges_note": "ترد في عدة مقالات",
           "symbols": "حسب الرموز", "all": "كل الصيغ", "in": "في مقالات", "art": "مقالات"},
    "fr": {"title": "Formules", "lead": "Formules tirées de nos articles. Une même formule relie souvent des "
                                        "travaux qui n'ont rien d'autre en commun : c'est là que se voit l'unité des sciences.",
           "bridges": "Formules-ponts", "bridges_note": "apparaissent dans plusieurs articles",
           "symbols": "Par notation", "all": "Toutes les formules", "in": "dans les articles", "art": "articles"},
}


def esc(s):
    return html.escape(str(s or ""), quote=True)


_TITLES = {}     # id → заголовок статьи на языке текущей сборки (см. build)


def _titles_for(lang):
    """Заголовки статей на языке страницы из lang/<lang>/articles-index.json. В formulas.json
    заголовки и пояснения только русские — на английской странице они утекали как есть
    (аудит 05.09). Нет перевода — показываем номер arXiv, а не русский текст."""
    if lang == "ru":
        return {}
    p = ROOT / "lang" / lang / "articles-index.json"
    try:
        return {a["id"]: a.get("title") or "" for a in json.loads(p.read_text(encoding="utf-8"))}
    except Exception:                                            # noqa: BLE001
        return {}


def card(key, f, lang, loc, big=False):
    """Карточка формулы. Латех отдаём как есть в .formula-render — его рендерит KaTeX
    на странице, тем же вызовом, что в статьях (см. templates/article.html)."""
    arts = f.get("articles") or []

    def title_of(a):
        if lang == "ru":
            return a["title"]
        return _TITLES.get(a["id"]) or ("arXiv:" + a["id"])

    links = "".join(
        f'<a class="fx-art" href="/lang/{lang}/archive/{esc(a["date"])}/{esc(a["id"])}/">{esc(title_of(a)[:60])}</a>'
        for a in arts[:6])
    n = f.get("n", len(arts))
    badge = f'<span class="fx-n">{n} {esc(loc["art"])}</span>' if n > 1 else ""
    # пояснение к формуле пока есть только по-русски — на других языках его не показываем
    mean = f'<div class="fx-mean">{esc(f.get("meaning", ""))}</div>' if lang == "ru" else ""
    return (f'<article class="fx-card{" fx-big" if big else ""}">'
            f'<div class="formula-render">{esc(f.get("latex", ""))}</div>'
            f'{badge}'
            f'{mean}'
            f'<div class="fx-arts">{links}</div></article>')


def build(lang, formulas):
    loc = L10N.get(lang, L10N["en"])
    global _TITLES
    _TITLES = _titles_for(lang)
    items = sorted(formulas.items(), key=lambda x: (-x[1].get("n", 0), x[0]))
    bridges = [(k, v) for k, v in items if v.get("n", 0) > 1]
    rest = [(k, v) for k, v in items if v.get("n", 0) <= 1]

    # группировка по обозначениям: символ → формулы. Показываем только символы, у которых
    # набирается хотя бы три формулы, иначе группа не группа, а строка.
    bysym = defaultdict(list)
    for k, v in items:
        for s in v.get("symbols", []):
            bysym[s].append((k, v))
    sym_html = ""
    for s, lst in sorted(bysym.items(), key=lambda x: -len(x[1])):
        if len(lst) < 3:
            continue
        sym_html += (f'<details class="fx-sym"><summary><b>{esc(s)}</b> '
                     f'<span class="fx-n">{len(lst)}</span></summary>'
                     + "".join(card(k, v, lang, loc) for k, v in lst[:24]) + "</details>")

    # лид уже стоит подзаголовком страницы (tags_subtitle) — второй раз не повторяем
    body = (f'<p class="fx-lead" hidden>{esc(loc["lead"])}</p>'
            f'<h2>{esc(loc["bridges"])} <small>— {esc(loc["bridges_note"])}</small></h2>'
            f'<div class="fx-grid fx-grid-big">' + "".join(card(k, v, lang, loc, big=True) for k, v in bridges) + "</div>"
            f'<h2>{esc(loc["symbols"])}</h2><div class="fx-syms">{sym_html}</div>'
            f'<h2>{esc(loc["all"])} <span class="fx-n">{len(items)}</span></h2>'
            f'<div class="fx-grid">' + "".join(card(k, v, lang, loc) for k, v in rest[:400]) + "</div>")
    return body, loc, len(items), len(bridges)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang")
    args = ap.parse_args()
    if not DATA.exists():
        print("нет data/formulas.json — сначала tools/formula_layer.py --build")
        return 1
    formulas = json.loads(DATA.read_text(encoding="utf-8"))

    sys.path.insert(0, str(ROOT))
    import generate

    import string
    for lang in ([args.lang] if args.lang else LANGS):
        body, loc, n, nb = build(lang, formulas)
        # Оболочка — от облака тегов: шапка, меню, языки и подвал те же, что на остальном
        # сайте. Контентную зону шаблона вырезаем и ставим свою: первый заход подставлял
        # НЕ ТЕ плейсхолдеры (safe_substitute молча оставил чужие), и страница вышла пустым
        # облаком тегов с заголовком «Tags». Поймано проверкой живьём, не отчётом.
        raw = (ROOT / "templates" / "tags-cloud.html").read_text(encoding="utf-8")
        i = raw.find('<div class="tag-cloud"')
        j = raw.find('<script', i)
        shell = raw[:i] + "${FORMULA_BODY}\n" + raw[j:]
        page = string.Template(shell).safe_substitute(
            lang=lang, dir=generate.dir_for(lang), asset_ver=generate.asset_ver(),
            goatcounter=getattr(generate, "GOATCOUNTER", ""),
            fav_title="", version_toggle_html="", mini_graph_filters_html="",
            selected_tags_html="", tags_cloud_html="", treemap_data="[]",
            tags_title=loc["title"], tags_subtitle=loc["lead"],
            FORMULA_BODY=body)
        # KaTeX — те же подключения, что в статье: без них .formula-render остаётся латехом
        katex = ('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">'
                 '<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js" '
                 "onload=\"document.querySelectorAll('.formula-render').forEach(function(el){"
                 'try{katex.render(el.textContent,el,{throwOnError:false})}catch(e){}})"></script>')
        # Заголовок вкладки в шаблоне зашит строкой «Tags», не плейсхолдером — меняем сами.
        page = page.replace("<title>Tags — bridge42worlds</title>",
                            f"<title>{loc['title']} — bridge42worlds</title>")
        page = page.replace("</head>", katex + "</head>")
        out = ROOT / "lang" / lang / "formulas" / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")
        print(f"  ✅ {lang}: {n} формул, из них мостов {nb} → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
