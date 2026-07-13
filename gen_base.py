#!/usr/bin/env python3
"""Базовый слой: общие константы (языки/версии/месяцы/категории) и низкоуровневые хелперы
(safe/attr_safe/author_slug/load_template/version_*/загрузка справочников). Импортируется
рендером/индексами/пайплайном. Config/языки — из common.
"""

import os
import sys
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from string import Template

from common import CONFIG as config, LANGUAGES, DEFAULT_LANG, LANG_DIR, DEEPSEEK_API_KEY, load_prompt  # noqa: F401

SITE_NAME = config.get("site_name", "bridge42worlds")
SITE_URL = config.get("site_url", "https://bridge42worlds.org")
GOATCOUNTER = config.get("goatcounter", "bridge42worlds")
MAX_ARTICLES = config.get("max_articles", 10)
SELECTION_PERCENT = config.get("selection_percent", 10)
ARTICLE_WORKERS = config.get("article_workers", 3)  # параллельных статей в фазе LLM

RTL_LANGS = {"ar", "he", "fa", "ur"}

# Локализованные названия месяцев / сокращения дней недели (пн-первый) для календаря архива.
MONTH_NAMES = {
    "ru": ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль",
           "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"],
    "en": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
    "zh": ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"],
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"],
    "ar": ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو",
           "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
}
WEEKDAY_ABBR = {
    "ru": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "zh": ["一", "二", "三", "四", "五", "六", "日"],
    "fr": ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"],
    "ar": ["إثن", "ثلا", "أرب", "خمي", "جمع", "سبت", "أحد"],
}

# ── Уровни сложности статьи (от простого к сложному) ──
# popular — самая простая, версия ПО УМОЛЧАНИЮ (index.html);
# simple — средняя (simple.html); advanced — полная (advanced.html).
VERSIONS = ["popular", "simple", "advanced"]
# Порядок вкладок в переключателе — от сложного к простому (визуально, не влияет на генерацию,
# которая по-прежнему идёт в порядке VERSIONS). Мини всегда добавляется последним отдельно.
VERSION_DISPLAY_ORDER = ["advanced", "popular", "simple"]
VERSION_FILES = {"popular": "index.html", "simple": "simple.html", "advanced": "advanced.html", "mini": "mini.html"}
VERSION_INDEX = {"popular": "articles-index.json", "simple": "articles-index-simple.json",
                 "advanced": "articles-index-advanced.json"}
# Откат контента, если версии нет (старые статьи без popular): popular→simple→advanced.
VERSION_FALLBACK = {"popular": ["popular", "simple", "advanced"],
                    "simple": ["simple", "advanced"], "advanced": ["advanced"],
                    "mini": ["mini"]}
VERSION_LABELS = {
    "popular":  {"ru": "Популярно", "en": "Popular", "es": "Popular", "zh": "科普", "fr": "Populaire", "ar": "مبسّط"},
    "simple":   {"ru": "Просто", "en": "Simple", "es": "Simple", "zh": "简明", "fr": "Simple", "ar": "بسيط"},
    "advanced": {"ru": "Подробно", "en": "Advanced", "es": "Avanzado", "zh": "深入", "fr": "Avancé", "ar": "متقدم"},
}
# "mini" — компактная версия: страница mini.html с threads-текстом вместо полной статьи.
# В VERSIONS не входит, генерируется отдельно в regenerate_all_html.
MINI_VERSION_LABEL = {"ru": "Мини", "en": "Mini", "es": "Mini", "zh": "迷你", "fr": "Mini", "ar": "مصغّر"}

# Подсказки (title=) на вкладках уровня сложности — первый визит должен объяснять,
# что это регулятор глубины изложения, а не разделы сайта.
VERSION_HINTS = {
    "popular":  {"ru": "Богаче простого — если наука уже увлекает", "en": "Richer than Simple — if science already excites you",
                 "es": "Más rico que Simple — si la ciencia ya te apasiona", "zh": "比“简明”更丰富——适合对科学感兴趣的读者",
                 "fr": "Plus riche que Simple — si la science vous passionne déjà", "ar": "أغنى من «مبسّط» - إذا كان العلم يثيرك"},
    "simple":   {"ru": "Максимально просто — для первого знакомства", "en": "As simple as it gets — for a first look",
                 "es": "Lo más simple — para una primera mirada", "zh": "最简单——适合初次了解",
                 "fr": "Le plus simple — pour découvrir", "ar": "الأبسط - لأول نظرة"},
    "advanced": {"ru": "С формулами и историей открытия", "en": "With formulas and the full discovery story",
                 "es": "Con fórmulas e historia completa", "zh": "含公式与完整发现历程",
                 "fr": "Avec formules et histoire complète", "ar": "بالمعادلات والقصة الكاملة"},
}
MINI_VERSION_HINT = {"ru": "Суть за 10 секунд", "en": "The gist in 10 seconds", "es": "La idea esencial en 10 segundos",
                      "zh": "10秒获取核心结论", "fr": "L'essentiel en 10 secondes", "ar": "الخلاصة في 10 ثوانٍ"}
# Стиль отрисовки: popular/simple/mini — сплошной text; advanced — секции.
SIMPLE_LIKE = {"popular", "simple", "mini"}

# arXiv-категории → человекочитаемые названия (основной набор для astro-ph и смежных).
ARXIV_CATEGORIES = {
    "astro-ph.CO": "Cosmology", "astro-ph.EP": "Exoplanets", "astro-ph.GA": "Galaxies",
    "astro-ph.HE": "High Energy", "astro-ph.IM": "Instrumentation", "astro-ph.SR": "Stellar",
    "gr-qc": "General Relativity", "hep-ex": "HEP Experiment", "hep-lat": "HEP Lattice",
    "hep-ph": "HEP Phenomenology", "hep-th": "HEP Theory", "math-ph": "Math Physics",
    "nucl-ex": "Nuclear Experiment", "nucl-th": "Nuclear Theory", "physics.atom-ph": "Atomic Physics",
    "physics.flu-dyn": "Fluid Dynamics", "physics.geo-ph": "Geophysics", "physics.optics": "Optics",
    "physics.plasm-ph": "Plasma Physics", "physics.space-ph": "Space Physics", "quant-ph": "Quantum Physics",
    "cond-mat": "Condensed Matter", "cond-mat.mes-hall": "Mesoscale", "cond-mat.mtrl-sci": "Materials",
    "cond-mat.stat-mech": "Statistical Mech", "cond-mat.str-el": "Strongly Correlated",
    "cond-mat.supr-con": "Superconductivity", "cond-mat.dis-nn": "Disordered Systems",
    "cond-mat.other": "Other Condensed Matter", "cond-mat.quant-gas": "Quantum Gases",
    "cond-mat.soft": "Soft Condensed Matter", "nlin.CD": "Chaotic Dynamics",
    "math.AP": "Analysis PDEs", "math.MP": "Math Physics", "math.DS": "Dynamical Systems",
    "cs.LG": "Machine Learning", "cs.AI": "Artificial Intelligence", "cs.CV": "Computer Vision",
    "cs.NE": "Neural Computing", "cs.CC": "Computational Complexity", "cs.CR": "Cryptography",
    "cs.NI": "Networking", "stat.ML": "Statistical ML", "eess.SP": "Signal Processing",
    "eess.IV": "Image Processing", "physics.app-ph": "Applied Physics", "physics.bio-ph": "Biological Physics",
    "physics.med-ph": "Medical Physics", "q-bio.NC": "Neurons and Cognition",
}

TARGET_DATE = os.environ.get("DATE", (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d"))
HTML_ONLY = "--html-only" in sys.argv


def safe(s):
    if not s:
        return ""
    return str(s).replace("$", "$$")


def attr_safe(s):
    return safe(s).replace('"', "&quot;")


def author_slug(name):
    # "/" реально встречается в именах коллабораций (напр. «The CHIME/FRB Collaboration») —
    # без замены Path(...) / f"{slug}.html" читает его как вложенный путь и падает
    # FileNotFoundError (родительской директории не существует).
    return name.replace(" ", "_").replace(".", "").replace("/", "-").replace("\\", "-")


def page_dir(lang):
    return "rtl" if lang in RTL_LANGS else "ltr"


def load_template(name):
    p = Path(f"templates/{name}.html")
    return Template(p.read_text(encoding="utf-8")) if p.exists() else Template("")


def version_label(version, lang):
    return VERSION_LABELS[version].get(lang, VERSION_LABELS[version]["en"])


def version_scipop(data, version, lang):
    """scipop нужной версии/языка из data.json с откатами по версии и языку."""
    for v in VERSION_FALLBACK.get(version, [version]):
        vdata = data.get(v, {})
        s = vdata.get(lang) or vdata.get(DEFAULT_LANG)
        if s:
            return s
    return {}


# Бегунок сложности — от простого к сложному, лево→право (мини даже проще «Просто»).
SLIDER_ORDER = ["mini", "simple", "popular", "advanced"]
SLIDER_TITLE = {"ru": "Уровень", "en": "Level", "es": "Nivel", "zh": "难度", "fr": "Niveau", "ar": "المستوى"}


def _slider_label(v, lang):
    return MINI_VERSION_LABEL.get(lang, MINI_VERSION_LABEL["en"]) if v == "mini" else version_label(v, lang)


def _slider_hint(v, lang):
    return (MINI_VERSION_HINT.get(lang, MINI_VERSION_HINT["en"]) if v == "mini"
            else VERSION_HINTS[v].get(lang, VERSION_HINTS[v]["en"]))


def _slider_html(lang, current, dot_html_fn):
    """Общая разметка бегунка — ВСЕГДА развёрнут целиком (не попап), сидит прямо в шапке.
    dot_html_fn(v, idx) строит одну точку — единственное, чем отличаются spans- (JS) и
    links- (навигация) режимы. id ОДИН и тот же в обоих режимах — на странице бегунок всегда
    ровно один, JS ищет по нему независимо от того, точки внутри <button> или <a>."""
    n = len(SLIDER_ORDER)
    cur_idx = SLIDER_ORDER.index(current) if current in SLIDER_ORDER else SLIDER_ORDER.index("popular")
    fill_pct = round(cur_idx / (n - 1) * 100, 2) if n > 1 else 0
    dots = "".join(dot_html_fn(v, i) for i, v in enumerate(SLIDER_ORDER))
    title = SLIDER_TITLE.get(lang, SLIDER_TITLE["en"])
    return (
        f'<div class="version-slider" id="version-toggle" data-count="{n}" role="group" aria-label="{attr_safe(title)}">'
        f'<span class="vs-current">{safe(_slider_label(current, lang))}</span>'
        f'<div class="vs-track">'
        f'<div class="vs-fill" style="width:{fill_pct}%"></div>'
        f'<div class="vs-thumb" style="left:{fill_pct}%"></div>'
        f'{dots}'
        f'</div>'
        f'</div>'
    )


def version_toggle_spans(lang, current="popular", include_mini=False):
    """Бегунок сложности для главной/лент — JS-управляемый (без include_mini мини-деление
    просто не активно по клику, но не убирается — 4 фиксированные позиции проще одного шаблона)."""
    def dot(v, idx):
        active = " active" if v == current else ""
        hint = attr_safe(_slider_hint(v, lang))
        label = attr_safe(_slider_label(v, lang))
        return (f'<button type="button" class="vs-dot{active}" data-version="{v}" data-idx="{idx}" '
                f'data-label="{label}" title="{label} — {hint}"></button>')
    return _slider_html(lang, current, dot)


def version_toggle_links(lang, current, date_str, aid):
    """Бегунок сложности на странице статьи — точки это ссылки на 4 файла версии (навигация,
    работает без JS; JS только красиво анимирует и открывает/закрывает панель)."""
    def dot(v, idx):
        active = " active" if v == current else ""
        href = f"/{LANG_DIR}/{lang}/archive/{date_str}/{aid}/{VERSION_FILES[v]}"
        hint = attr_safe(_slider_hint(v, lang))
        label = attr_safe(_slider_label(v, lang))
        return (f'<a class="vs-dot{active}" data-version="{v}" data-idx="{idx}" href="{href}" '
                f'data-label="{label}" title="{label} — {hint}"></a>')
    return _slider_html(lang, current, dot)


# ── Загрузка справочников ──
def load_tags_list():
    p = Path("data/tags-graph.json")
    return "\n".join(sorted(json.loads(p.read_text()).get("graph", {}).keys())) if p.exists() else ""


def load_tags_loc(lang):
    p = Path(f"lang/{lang}/data/tags.json")
    if not p.exists():
        p = Path(f"lang/{DEFAULT_LANG}/data/tags.json")
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def gen_tags_side(tags, lang):
    loc = load_tags_loc(lang)
    return "\n".join(
        f'<a href="/{LANG_DIR}/{lang}/tags/{t}.html" class="side-tag" data-tag="{attr_safe(t)}">{loc.get(t, {}).get("name", t)}</a>'
        for t in tags if t
    )


def load_scientists_list():
    p = Path(f"lang/{DEFAULT_LANG}/data/scientists.json")
    return "\n".join(json.loads(p.read_text()).keys()) if p.exists() else ""
