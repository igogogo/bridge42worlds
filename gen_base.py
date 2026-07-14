#!/usr/bin/env python3
"""Базовый слой: общие константы (языки/версии/месяцы/категории) и низкоуровневые хелперы
(safe/attr_safe/author_slug/load_template/version_*/загрузка справочников). Импортируется
рендером/индексами/пайплайном. Config/языки — из common.
"""

import os
import sys
import json
import re
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
    "physics.ins-det": "Instrumentation and Detectors", "physics.ao-ph": "Atmospheric and Oceanic Physics",
    "physics.hist-ph": "History and Philosophy of Physics", "physics.chem-ph": "Chemical Physics",
    "physics.pop-ph": "Popular Physics", "physics.comp-ph": "Computational Physics",
    "physics.class-ph": "Classical Physics", "physics.soc-ph": "Physics and Society",
    "physics.atm-clus": "Atomic and Molecular Clusters", "stat.AP": "Applied Statistics",
    "cs.MS": "Mathematical Software", "cs.IT": "Information Theory", "math.IT": "Information Theory",
    "cs.CL": "Computation and Language", "cs.RO": "Robotics",
}

# Развёрнутые описания (официальный текст arXiv с /archive/<name> и /category_taxonomy,
# для 2 категорий без официального текста — quant-ph и physics.pop-ph — написано по общеизвестному
# охвату категории) — тултипы к бейджам категорий. Не переводим на языки сайта: это устоявшийся
# англоязычный научный жаргон, аудитория тегов/категорий такого уровня всё равно читает по-английски.
ARXIV_CATEGORY_DESCRIPTIONS = {
    "astro-ph.CO": "Phenomenology of early universe, cosmic microwave background, cosmological parameters, primordial element abundances, extragalactic distance scale, large-scale structure of the universe.",
    "astro-ph.EP": "Interplanetary medium, planetary physics, planetary astrobiology, extrasolar planets, comets, asteroids, meteorites. Structure and formation of the solar system.",
    "astro-ph.GA": "Phenomena pertaining to galaxies or the Milky Way. Star clusters, HII regions and planetary nebulae, the interstellar medium, atomic and molecular clouds, dust.",
    "astro-ph.HE": "Cosmic ray production, acceleration, propagation, detection. Gamma ray astronomy and bursts, X-rays, charged particles, supernovae and other explosive phenomena, stellar remnants and accretion systems.",
    "astro-ph.IM": "Detector and telescope design, experiment proposals. Laboratory astrophysics. Methods for data analysis, statistical methods. Software, database design.",
    "astro-ph.SR": "White dwarfs, brown dwarfs, cataclysmic variables. Star formation and protostellar systems, stellar astrobiology, binary and multiple systems of stars, stellar evolution and structure, coronas.",
    "gr-qc": "Gravitational physics: detection and interpretation of gravitational waves, tests of gravitational theories, computational general relativity, relativistic astrophysics, solutions to Einstein's equations, alternative theories of gravity, classical and quantum cosmology, quantum gravity.",
    "hep-ex": "Results from high-energy/particle physics experiments and prospects for future results: tests of the standard model, measurements of standard model parameters, searches for physics beyond the standard model, astroparticle physics experimental results.",
    "hep-lat": "Lattice field theory: phenomenology, algorithms and hardware for lattice field theory.",
    "hep-ph": "Theoretical particle physics and its interrelation with experiment: prediction of particle physics observables, effective field theories, calculation techniques, analysis of theory through experimental results.",
    "hep-th": "Formal aspects of quantum field theory. String theory, supersymmetry and supergravity.",
    "math-ph": "Application of mathematics to problems in physics, development of mathematical methods for such applications, rigorous formulations of physical theories.",
    "nucl-ex": "Results from experimental nuclear physics: fundamental interactions, low- and medium-energy measurements, relativistic heavy-ion collisions.",
    "nucl-th": "Theory of nuclear structure, from models of hadron structure to neutron stars. Nuclear equations of state, theory of nuclear reactions including heavy-ion reactions at low and high energies.",
    "physics.atom-ph": "Atomic and molecular structure, spectra, collisions, and data. Atoms and molecules in external fields. Molecular dynamics and coherent and optical control. Cold atoms and molecules.",
    "physics.flu-dyn": "Turbulence, incompressible and compressible flows, aero- and hydrodynamics, biological fluid dynamics, complex fluids, mathematical methods for fluid flow analysis.",
    "physics.geo-ph": "Atmospheric physics, biogeosciences, geophysical techniques, hydrospheric geophysics, magnetospheric physics, planetology, solid earth geophysics.",
    "physics.optics": "Adaptive optics, fiber optics, holography, lasers, optical devices, quantum optics, spectroscopy and other optical subfields.",
    "physics.plasm-ph": "Fundamental plasma physics, magnetically confined plasmas, high energy density plasmas, astrophysical plasmas, low temperature plasma applications.",
    "physics.space-ph": "Space plasma physics, heliophysics, space weather, planetary magnetospheres, auroras, interplanetary space, cosmic rays, radio astronomy.",
    "quant-ph": "Foundations of quantum mechanics, quantum information and computation, quantum optics, entanglement, and related experiments.",
    "cond-mat": "General condensed matter physics not covered by the more specific cond-mat subcategories.",
    "cond-mat.mes-hall": "Semiconducting nanostructures: quantum dots, wires, and wells. Single electronics, spintronics, 2d electron gases, quantum Hall effect, nanotubes, graphene, plasmonic nanostructures.",
    "cond-mat.mtrl-sci": "Techniques, synthesis, characterization, structure. Structural phase transitions, mechanical properties, phonons. Defects, adsorbates, interfaces.",
    "cond-mat.stat-mech": "Phase transitions, thermodynamics, field theory, non-equilibrium phenomena, renormalization group and scaling, integrable models, turbulence.",
    "cond-mat.str-el": "Quantum magnetism, non-Fermi liquids, spin liquids, quantum criticality, charge density waves, metal-insulator transitions.",
    "cond-mat.supr-con": "Superconductivity: theory, models, experiment. Superflow in helium.",
    "cond-mat.dis-nn": "Glasses and spin glasses; properties of random, aperiodic and quasiperiodic systems; transport in disordered media; localization; phenomena mediated by defects and disorder; neural networks.",
    "cond-mat.other": "Work in condensed matter that does not fit into the other cond-mat classifications.",
    "cond-mat.quant-gas": "Ultracold atomic and molecular gases, Bose-Einstein condensation, Feshbach resonances, spinor condensates, optical lattices, quantum simulation with cold atoms and molecules.",
    "cond-mat.soft": "Membranes, polymers, liquid crystals, glasses, colloids, granular matter.",
    "nlin.CD": "Dynamical systems, chaos, quantum chaos, topological dynamics, cycle expansions, turbulence, propagation.",
    "math.AP": "Existence and uniqueness, boundary conditions, linear and non-linear operators, stability, soliton theory, integrable PDEs, conservation laws, qualitative dynamics.",
    "math.MP": "Application of mathematics to physics problems, mathematical methods for such applications, rigorous formulations of physical theories (same scope as math-ph).",
    "math.DS": "Dynamics of differential equations and flows, mechanics, classical few-body problems, iterations, complex dynamics, delayed differential equations.",
    "cs.LG": "Machine learning research: supervised, unsupervised, reinforcement learning, bandit problems, and related topics.",
    "cs.AI": "Artificial intelligence, excluding vision, robotics, machine learning, multiagent systems and NLP: expert systems, theorem proving, knowledge representation, planning, uncertainty in AI.",
    "cs.CV": "Image processing, computer vision, pattern recognition, and scene understanding.",
    "cs.NE": "Neural networks, connectionism, genetic algorithms, artificial life, adaptive behavior.",
    "cs.CC": "Models of computation, complexity classes, structural complexity, complexity tradeoffs, upper and lower bounds.",
    "cs.CR": "Cryptography and security: authentication, public key cryptosystems, proof-carrying code and related topics.",
    "cs.NI": "Computer communication networks: network architecture and design, network protocols.",
    "stat.ML": "Machine learning with a statistical or theoretical grounding: supervised, unsupervised, semi-supervised learning, graphical models, reinforcement learning, bandits, high dimensional inference.",
    "eess.SP": "Theory, algorithms, performance analysis and applications of signal and data analysis: physical modeling, processing, detection, parameter estimation, learning, mining, retrieval, information extraction.",
    "eess.IV": "Theory, algorithms, and architectures for formation, capture, processing, communication, analysis and display of images, video, and multidimensional signals.",
    "physics.app-ph": "Applications of physics to new technology: electronic devices, optics, photonics, microwaves, spintronics, advanced materials, metamaterials, nanotechnology, energy sciences.",
    "physics.bio-ph": "Molecular, cellular and neurological biophysics, membrane biophysics, quantum phenomena in biological systems, and related methodologies.",
    "physics.med-ph": "Radiation therapy, radiation dosimetry, biomedical imaging, reconstruction and processing, biomedical system modeling, new imaging or therapy modalities.",
    "q-bio.NC": "Synapse, cortex, neuronal dynamics, neural network, sensorimotor control, behavior, attention.",
    "physics.ins-det": "Instrumentation and detectors for research in natural science, including optical, molecular, atomic, nuclear and particle physics instrumentation and associated electronics.",
    "physics.ao-ph": "Atmospheric and oceanic physics and physical chemistry, biogeophysics, and climate science.",
    "physics.hist-ph": "History and philosophy of all branches of physics, astrophysics, and cosmology, including appreciations of physicists.",
    "physics.chem-ph": "Experimental, computational, and theoretical physics of atoms, molecules, and clusters: classical and quantum descriptions, spectroscopy, electronic structure, chemical thermodynamics.",
    "physics.pop-ph": "Accessible discussions of physics topics for a general, non-specialist audience.",
    "physics.comp-ph": "All aspects of computational science applied to physics.",
    "physics.class-ph": "Newtonian and relativistic dynamics, electromagnetic forces, vibrating systems, classical waves including acoustics, classical thermodynamics.",
    "physics.soc-ph": "Structure, dynamics and collective behavior of societies and groups. Quantitative analysis of social networks and other complex networks. Physics and engineering of infrastructure.",
    "physics.atm-clus": "Atomic and molecular clusters and nanoparticles: geometric, electronic, optical, chemical, and magnetic properties, spectroscopy, computational methods.",
    "stat.AP": "Statistical applications in biology, education, epidemiology, engineering, environmental sciences, medicine, physical sciences, quality control, social sciences.",
    "cs.MS": "Mathematical software.",
    "cs.IT": "Theoretical and experimental aspects of information theory and coding.",
    "math.IT": "Alias for cs.IT — theoretical and experimental aspects of information theory and coding.",
    "cs.CL": "Natural language processing: computational linguistics and related work on human language.",
    "cs.RO": "Robotics.",
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
    # FileNotFoundError (родительской директории не существует). Остальные символы,
    # запрещённые в именах файлов на Windows (: < > " | ? *) — тоже на "-": однажды словили
    # мусорного "автора" с именем ровно ":" (артефакт парсинга списка авторов) — падало
    # с OSError [Errno 22] на записи файла.
    slug = name.replace(" ", "_").replace(".", "").replace("/", "-").replace("\\", "-")
    return re.sub(r'[:<>"|?*]', "-", slug)


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
