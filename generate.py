#!/usr/bin/env python3
"""
Bridge For Two Worlds — генератор научно-популярных статей из arXiv.
arXiv astro-ph → DeepSeek → HTML + data.json + API-ответы
"""

import os, sys, json, time, re, random, calendar, requests, traceback, xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from string import Template
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

# Windows-консоль по умолчанию cp1252 — кириллица/эмодзи в print() падают. Форсим UTF-8.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

load_dotenv()
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

CONFIG_PATH = Path("config.json")
if not CONFIG_PATH.exists():
    print("❌ config.json not found")
    sys.exit(1)

config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
LANGUAGES = config.get("languages", ["ru", "en"])
DEFAULT_LANG = config.get("default_lang", "ru")
LANG_DIR = config.get("lang_dir", "lang")
SITE_NAME = config.get("site_name", "bridge42worlds")
SITE_URL = config.get("site_url", "https://bridge42worlds.org")
GOATCOUNTER = config.get("goatcounter", "bridge42worlds")
MAX_ARTICLES = config.get("max_articles", 10)
SELECTION_PERCENT = config.get("selection_percent", 10)
ARTICLE_WORKERS = config.get("article_workers", 3)  # параллельных статей в фазе LLM

LANG_NAMES = {
    "ru": "Russian", "en": "English", "cn": "Chinese", "zh": "Chinese",
    "fr": "French", "de": "German", "es": "Spanish", "it": "Italian",
    "pt": "Portuguese", "ja": "Japanese", "ko": "Korean", "ar": "Arabic",
    "hi": "Hindi", "tr": "Turkish", "pl": "Polish", "nl": "Dutch",
}

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
VERSION_FILES = {"popular": "index.html", "simple": "simple.html", "advanced": "advanced.html"}
VERSION_INDEX = {"popular": "articles-index.json", "simple": "articles-index-simple.json",
                 "advanced": "articles-index-advanced.json"}
# Откат контента, если версии нет (старые статьи без popular): popular→simple→advanced.
VERSION_FALLBACK = {"popular": ["popular", "simple", "advanced"],
                    "simple": ["simple", "advanced"], "advanced": ["advanced"]}
VERSION_LABELS = {
    "popular":  {"ru": "Популярно", "en": "Popular", "zh": "科普", "fr": "Populaire", "ar": "مبسّط"},
    "simple":   {"ru": "Просто", "en": "Simple", "zh": "简明", "fr": "Simple", "ar": "بسيط"},
    "advanced": {"ru": "Подробно", "en": "Advanced", "zh": "深入", "fr": "Avancé", "ar": "متقدم"},
}
# Стиль отрисовки: popular/simple — сплошной text; advanced — секции.
SIMPLE_LIKE = {"popular", "simple"}

# arXiv-категории → человекочитаемые названия (основной набор для astro-ph и смежных).
ARXIV_CATEGORIES = {
    "astro-ph.CO": "Cosmology",
    "astro-ph.EP": "Exoplanets",
    "astro-ph.GA": "Galaxies",
    "astro-ph.HE": "High Energy",
    "astro-ph.IM": "Instrumentation",
    "astro-ph.SR": "Stellar",
    "gr-qc": "General Relativity",
    "hep-ex": "HEP Experiment",
    "hep-lat": "HEP Lattice",
    "hep-ph": "HEP Phenomenology",
    "hep-th": "HEP Theory",
    "math-ph": "Math Physics",
    "nucl-ex": "Nuclear Experiment",
    "nucl-th": "Nuclear Theory",
    "physics.atom-ph": "Atomic Physics",
    "physics.flu-dyn": "Fluid Dynamics",
    "physics.geo-ph": "Geophysics",
    "physics.optics": "Optics",
    "physics.plasm-ph": "Plasma Physics",
    "physics.space-ph": "Space Physics",
    "quant-ph": "Quantum Physics",
    "cond-mat": "Condensed Matter",
    "cond-mat.mes-hall": "Mesoscale",
    "cond-mat.mtrl-sci": "Materials",
    "cond-mat.stat-mech": "Statistical Mech",
    "cond-mat.str-el": "Strongly Correlated",
    "cond-mat.supr-con": "Superconductivity",
    "nlin.CD": "Chaotic Dynamics",
    "math.AP": "Analysis PDEs",
    "math.MP": "Math Physics",
    "cs.LG": "Machine Learning",
    "cs.AI": "Artificial Intelligence",
    "cs.CV": "Computer Vision",
    "cs.NE": "Neural Computing",
    "stat.ML": "Statistical ML",
    "eess.SP": "Signal Processing",
    "eess.IV": "Image Processing",
}


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


def version_toggle_spans(lang, current="popular"):
    """Переключатель для главной/лент (JS-управляемые span data-version)."""
    spans = "".join(
        f'<span class="{"active" if v == current else ""}" data-version="{v}">{safe(version_label(v, lang))}</span>'
        for v in VERSIONS)
    return f'<div class="version-toggle" id="version-toggle">{spans}</div>'


def version_toggle_links(lang, current, date_str, aid):
    """Переключатель на странице статьи — ссылки на 3 файла версии."""
    parts = []
    for v in VERSIONS:
        active = ' class="active"' if v == current else ''
        href = f"/{LANG_DIR}/{lang}/archive/{date_str}/{aid}/{VERSION_FILES[v]}"
        parts.append(f'<a href="{href}"{active}>{safe(version_label(v, lang))}</a>')
    return f'<div class="version-toggle">{"".join(parts)}</div>'


def page_dir(lang):
    return "rtl" if lang in RTL_LANGS else "ltr"


# Культурная адаптация перевода по языкам. Для арабского — уважение к исламским нормам
# (важно для партнёрства в Кувейте). Механизм общий: добавляй сюда любую страну.
CULTURE_NOTES = {
    "ar": ("ВАЖНО — КУЛЬТУРНАЯ АДАПТАЦИЯ ДЛЯ АРАБСКОЙ И МУСУЛЬМАНСКОЙ АУДИТОРИИ: переводи с "
           "уважением к исламским ценностям и обычаям арабских стран Персидского залива. Избегай "
           "аналогий и примеров, связанных с алкоголем, свининой, азартными играми, романтическими "
           "или интимными отношениями, и любых образов, которые могут быть восприняты как неуважение "
           "к религии. Сохраняй достоинство и уважительный, уместный для региона тон."),
}

TARGET_DATE = os.environ.get("DATE", (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d"))

HTML_ONLY = "--html-only" in sys.argv

# Ключ нужен только для операций с API. Офлайн-команды оркестратора
# (html/reindex/check/delete) должны работать и без него.
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com") if DEEPSEEK_API_KEY else None

if not DEEPSEEK_API_KEY:
    print("⚠️  DEEPSEEK_API_KEY не задан — доступны только офлайн-операции (html/reindex/check/delete)")

print(f"🚀 {SITE_NAME} generator")
print(f"   Languages: {LANGUAGES}")


def load_template(name):
    p = Path(f"templates/{name}.html")
    return Template(p.read_text(encoding="utf-8")) if p.exists() else Template("")


def load_prompt(name):
    p = Path(f"data/prompts/{name}.txt")
    return p.read_text(encoding="utf-8") if p.exists() else ""


def safe(s):
    if not s: return ""
    return str(s).replace("$", "$$")


def attr_safe(s):
    return safe(s).replace('"', "&quot;")


def author_slug(name):
    return name.replace(" ", "_").replace(".", "")


# ── Tags ──
def load_tags_list():
    p = Path("data/tags-graph.json")
    return "\n".join(sorted(json.loads(p.read_text()).get("graph", {}).keys())) if p.exists() else ""


def load_tags_loc(lang):
    p = Path(f"lang/{lang}/data/tags.json")
    if not p.exists(): p = Path(f"lang/{DEFAULT_LANG}/data/tags.json")
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


# ── arXiv ──
def fetch_arxiv(date_str):
    f = f"{date_str.replace('-', '')}0000"
    t = f"{date_str.replace('-', '')}2359"
    url = "http://es.arxiv.org/api/query"
    params = {
        "search_query": f"cat:astro-ph.* AND submittedDate:[{f} TO {t}]",
        "start": 0, "max_results": 200,
        "sortBy": "submittedDate", "sortOrder": "descending"
    }
    r = requests.get(url, params=params, timeout=30)
    Path(f"temp/{date_str}").mkdir(parents=True, exist_ok=True)
    Path(f"temp/{date_str}/arxiv-api.xml").write_text(r.text, encoding="utf-8")

    if not r.text or r.status_code != 200:
        print(f"  ❌ arXiv API error: status {r.status_code}")
        return []
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        return []

    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    articles = []
    for e in root.findall("atom:entry", ns):
        try:
            aid = e.find("atom:id", ns).text.split("/abs/")[-1]
            cats = list(dict.fromkeys(
                c.get("term") for c in e.findall("atom:category", ns) if c.get("term")))
            primary = e.find("arxiv:primary_category", ns)
            primary_cat = primary.get("term", "") if primary is not None else (cats[0] if cats else "")
            articles.append({
                "id": aid,
                "title": e.find("atom:title", ns).text.strip().replace("\n", " "),
                "summary": e.find("atom:summary", ns).text.strip().replace("\n", " "),
                "authors": [a.find("atom:name", ns).text for a in e.findall("atom:author", ns)],
                "published": e.find("atom:published", ns).text,
                "categories": cats,
                "primary_category": primary_cat,
            })
        except:
            pass
    print(f"  ✅ Found: {len(articles)} articles")
    return articles


# ── License ──
def get_license(arxiv_id):
    try:
        r = requests.get("http://es.arxiv.org/oai2", params={
            "verb": "GetRecord", "identifier": f"oai:arXiv.org:{arxiv_id}", "metadataPrefix": "arXiv"
        }, timeout=10)
        return r.text
    except:
        return None


def is_allowed_license(xml_text):
    if not xml_text: return False, None
    try:
        root = ET.fromstring(xml_text)
        lic = root.find(".//{http://arxiv.org/OAI/arXiv/}license")
        if lic is None: return False, None
        lic_url = lic.text
        allowed = ["by/4.0", "by-sa/4.0", "zero/1.0", "nonexclusive-distrib/1.0"]
        return any(a in lic_url for a in allowed), lic_url
    except:
        return False, None


# ── PDF ──
def download_pdf(aid):
    p = Path(f"temp/{aid}.pdf");
    p.parent.mkdir(exist_ok=True)
    if not p.exists(): p.write_bytes(requests.get(f"https://arxiv.org/pdf/{aid}.pdf", timeout=60).content)
    return p


def parse_pdf(path):
    # Берём ВЕСЬ текст статьи (без ограничения по числу страниц) — модели скармливаем полностью.
    try:
        r = PdfReader(str(path))
        t = ""
        imgs = []
        for pg in r.pages:
            pt = pg.extract_text()
            if pt: t += pt + "\n"
            try:
                for img in pg.images: imgs.append(img.data)
            except:
                pass
        return t, imgs
    except:
        return "", []


# Заголовок списка литературы: строка вида "References"/"REFERENCES"/"Bibliography"
# (возможно с номером раздела), стоящая отдельной строкой.
REF_HEADING = re.compile(
    r'\n[ \t]*(?:\d+[.\)]?[ \t]*)?(?:References?|REFERENCES|Bibliography|BIBLIOGRAPHY|References and Notes)[ \t]*\n')
ARXIV_ID_RE = re.compile(r'ar[Xx]iv:\s*(\d{4}\.\d{4,5})')


def split_references(text):
    """Отделяет список литературы (References/Bibliography) от тела статьи.
    Возвращает (body, references). Заголовок ищем в ПОСЛЕДНЕЙ части документа и режем по
    ПОСЛЕДНЕМУ совпадению — чтобы упоминание 'references' в тексте не обрезало тело раньше времени.
    Список литературы ест до ~20% токенов и для генерации статьи бесполезен."""
    cut = None
    for m in REF_HEADING.finditer(text):
        if m.start() > len(text) * 0.4:  # только во второй половине — там реальный список в конце статьи
            cut = m
    if cut:
        return text[:cut.start()].rstrip(), text[cut.end():].strip()
    return text, ""


def extract_ref_arxiv_ids(references):
    """arXiv id цитируемых работ из списка литературы — на будущее для привязки к релевантным статьям."""
    return list(dict.fromkeys(m.group(1) for m in ARXIV_ID_RE.finditer(references or "")))


def clean_article_text(text):
    """Тело статьи БЕЗ списка литературы и голых URL — то, что уходит в промт."""
    body, _ = split_references(text)
    return re.sub(r'https?://\S+', '', body)


def extract_captions(text, limit=12):
    """Достаёт подписи к рисункам из текста PDF ('Figure N: ...' / 'Fig. N. ...').
    Возвращает список подписей по возрастанию номера рисунка — для сопоставления с картинками по порядку."""
    caps = {}
    for m in re.finditer(r'(?:Figure|Fig)\.?\s*(\d{1,3})\s*[\.:]\s*([^\n]{10,300})', text):
        n = int(m.group(1))
        cap = re.sub(r'\s+', ' ', m.group(2)).strip()
        if n not in caps and len(cap) > 12:
            caps[n] = cap
    return [caps[n] for n in sorted(caps)][:limit]


def save_images(images, aid, folder, min_size=40000):
    # Имена строго последовательные 0..N-1: og:image и gen_mosaic() рассчитывают
    # на непрерывную нумерацию, пропуски из-за фильтра мелких картинок недопустимы.
    saved = []
    for d in images:
        if len(d) < min_size: continue
        p = folder / f"{len(saved)}.jpg"
        p.write_bytes(d)
        saved.append(str(p))
    if saved: print(f"    🖼️ Saved: {len(saved)} images")
    return saved


def gen_mosaic(images, aid, date_str, captions=None):
    # Горизонтальная лента: блок 5:1 (ширина:высота), видно 5 картинок,
    # остальные — скроллом; стрелка появляется при >5. Подписи (если есть) — figcaption + alt/title.
    if not images: return ""
    captions = captions or []
    base = f"/{LANG_DIR}/{DEFAULT_LANG}/archive/{date_str}/{aid}"
    parts = []
    for i in range(len(images)):
        cap = captions[i] if i < len(captions) and captions[i] else ""
        alt = attr_safe(cap)
        capfig = f'<figcaption>{safe(cap)}</figcaption>' if cap else ''
        title = f' title="{alt}"' if cap else ''
        parts.append(
            f'<figure class="mosaic-item"><a href="{base}/{i}.jpg" target="_blank">'
            f'<img src="{base}/{i}.jpg" alt="{alt}"{title} loading="lazy"></a>{capfig}</figure>'
        )
    items = "".join(parts)
    arrows = ""
    if len(images) > 5:
        arrows = (
            '<button type="button" class="mosaic-arrow mosaic-prev" aria-label="Prev" '
            "onclick=\"this.parentElement.querySelector('.mosaic-track').scrollBy({left:-this.parentElement.querySelector('.mosaic-track').clientWidth*0.6,behavior:'smooth'})\">‹</button>"
            '<button type="button" class="mosaic-arrow mosaic-next" aria-label="More images" '
            "onclick=\"this.parentElement.querySelector('.mosaic-track').scrollBy({left:this.parentElement.querySelector('.mosaic-track').clientWidth*0.6,behavior:'smooth'})\">›</button>")
    return f'<div class="mosaic-track">{items}</div>{arrows}'


# ── DeepSeek ──
def clean_json(t):
    t = t.strip()
    for m in ["```json", "```"]:
        if t.startswith(m): t = t[len(m):]
    if t.endswith("```"): t = t[:-3]
    t = t.strip().rstrip(",")
    t += "}" * (t.count("{") - t.count("}"))
    t += "]" * (t.count("[") - t.count("]"))
    return t


SYSTEM_PROMPT = Path("data/prompts/system.txt").read_text(encoding="utf-8")


def chat(user_prompt, temperature=0.7, max_tokens=4000, retries=3):
    """Вызов DeepSeek с ретраями — сетевой сбой не должен терять статью."""
    if client is None:
        raise RuntimeError("DEEPSEEK_API_KEY не задан — операция с API невозможна")
    for attempt in range(1, retries + 1):
        try:
            return client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=[{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": user_prompt}],
                temperature=temperature, max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )
        except Exception as e:
            if attempt == retries:
                raise
            wait = 5 * attempt
            print(f"    ⚠️ DeepSeek error: {e} — retry {attempt}/{retries} через {wait}с")
            time.sleep(wait)


def select_best(articles, date_str):
    total = len(articles)
    count = max(1, total * SELECTION_PERCENT // 100)
    count = min(count, MAX_ARTICLES)
    if total <= count: return articles

    j = json.dumps([{"id": a["id"], "title": a["title"], "summary": a["summary"][:500]} for a in articles],
                   ensure_ascii=False)
    prompt = load_prompt("select-articles").format(count=count, articles_json=j)
    print(f"  🤖 Selecting {count} best from {total}...")
    r = chat(prompt, temperature=0.7, max_tokens=2000)
    Path(f"temp/{date_str}").mkdir(parents=True, exist_ok=True)
    Path(f"temp/{date_str}/selection.json").write_text(r.choices[0].message.content, encoding="utf-8")
    try:
        data = json.loads(clean_json(r.choices[0].message.content))
        ids = [x["id"] for x in data.get("articles", data if isinstance(data, list) else [])]
        if not ids and isinstance(data, dict):
            ids = [x["id"] for x in data.get("selection", data.get("articles", []))]
        return [a for a in articles if a["id"] in ids][:count]
    except:
        return articles[:count]


def _script_ratio(text, lo, hi):
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 1.0  # нечего оценивать — не блокируем
    return sum(1 for c in letters if lo <= c <= hi) / len(letters)


def _default_lang_ok(scipop):
    """RU-генерация иногда сваливается в английский на кросс-доменных статьях (cs.LG и т.п.).
    Проверяем, что заголовок/описание реально на русском. Только для кириллического default_lang."""
    if DEFAULT_LANG != "ru":
        return True
    sample = " ".join(str(scipop.get(k, "")) for k in ("title", "oneliner", "description"))
    return _script_ratio(sample, "Ѐ", "ӿ") >= 0.5


def generate_advanced(article, text, tags_input, scientists_keys):
    tags_list = ", ".join(t["en"] for t in tags_input)
    scientists_list = ", ".join(scientists_keys)
    prompt = load_prompt("generate-article-advanced").format(
        tags_list=tags_list, scientists_list=scientists_list, article_text=text
    )
    print(f"  🤖 Advanced (RU)...")
    reinforce = "\n\nВНИМАНИЕ: все текстовые поля пиши СТРОГО на русском языке. Не отвечай на английском."
    result = None
    for attempt in range(2):
        r = chat(prompt if attempt == 0 else prompt + reinforce, temperature=0.7, max_tokens=8000)
        try:
            parsed = json.loads(clean_json(r.choices[0].message.content))
        except:
            Path(f"temp/debug_adv_{article['id']}.txt").write_text(r.choices[0].message.content, encoding="utf-8")
            # Сбой парсинга на ретрае: сохраняем ранее распарсенный результат (пусть и английский) —
            # это лучше, чем терять статью целиком; неправильный язык поймает скан-и-реген.
            if result is not None:
                break
            return None
        result = parsed
        if _default_lang_ok(result):
            return result
        print(f"    ⚠️ RU-версия вышла не на русском — повтор с усилением языка")
    return result  # последняя удачно распарсенная попытка


IMG_VARIATIONS = {
    "lighting": ["soft volumetric light", "dramatic rim light", "golden hour glow", "cold moonlight",
                 "bioluminescent glow", "harsh directional light", "diffuse studio light", "backlit haze"],
    "camera": ["wide establishing shot", "extreme close-up macro", "low angle looking up",
               "top-down view", "tilted dutch angle", "shallow depth of field", "long lens compression"],
    "palette": ["deep indigo and cyan", "warm amber and crimson", "monochrome teal", "violet and gold",
                "emerald and black", "muted pastel", "high-contrast black and white with one accent color"],
    "style": ["cinematic photorealism", "elegant scientific 3D render", "abstract minimalism",
              "painterly digital art", "crisp editorial illustration", "atmospheric concept art"],
    "mood": ["serene and vast", "tense and dramatic", "mysterious", "hopeful and luminous",
             "cold and precise", "awe-inspiring", "intimate and quiet"],
}


def generate_image_prompt(scipop):
    """DeepSeek придумывает промпт для FLUX по статье, со случайными вариациями (чтобы не однотипно)."""
    picks = {k: random.choice(v) for k, v in IMG_VARIATIONS.items()}
    tmpl = load_prompt("generate-ai-image")
    prompt = tmpl.format(
        title=scipop.get("title", ""), oneliner=scipop.get("oneliner", ""),
        description=scipop.get("description", ""),
        tags=", ".join([scipop.get("main_tag", "")] + scipop.get("extra_tags", [])[:5]),
        **picks)
    r = chat(prompt, temperature=1.0, max_tokens=400)
    try:
        return json.loads(clean_json(r.choices[0].message.content)).get("prompt", "")
    except Exception:
        return ""


def generate_image(image_prompt, out_path):
    """Рисует картинку через DeepInfra FLUX-2-pro. Key-guarded: без ключа — пропуск."""
    key = os.environ.get("DEEPINFRA_API_KEY", "")
    if not key or not image_prompt:
        return False
    try:
        import base64
        cli = OpenAI(base_url="https://api.deepinfra.com/v1/openai", api_key=key)
        resp = cli.images.generate(model="black-forest-labs/FLUX-2-pro",
                                    prompt=image_prompt, n=1, size="1024x1024")
        Path(out_path).write_bytes(base64.b64decode(resp.data[0].b64_json))
        return True
    except Exception as e:
        print(f"    ⚠️ FLUX error: {e}")
        return False


def generate_simple(scipop_advanced):
    prompt = load_prompt("generate-article-simple").format(
        advanced_json=json.dumps(scipop_advanced, ensure_ascii=False)
    )
    print(f"  🤖 Simple (RU)...")
    reinforce = "\n\nВНИМАНИЕ: пиши СТРОГО на русском языке."
    data = None
    for attempt in range(2):
        r = chat(prompt if attempt == 0 else prompt + reinforce, temperature=0.8, max_tokens=6000)
        try:
            data = json.loads(clean_json(r.choices[0].message.content))
        except:
            return scipop_advanced
        if _default_lang_ok(data):
            break
    data["main_tag"] = scipop_advanced.get("main_tag", "")
    data["extra_tags"] = scipop_advanced.get("extra_tags", [])
    data["scientists"] = scipop_advanced.get("scientists", [])
    return data


def generate_popular(scipop_simple):
    """Ещё более простая версия, чем simple (на её основе). Та же структура полей."""
    prompt = load_prompt("generate-article-popular").format(
        simple_json=json.dumps(scipop_simple, ensure_ascii=False)
    )
    print(f"  🤖 Popular (RU)...")
    reinforce = "\n\nВНИМАНИЕ: пиши СТРОГО на русском языке."
    data = None
    for attempt in range(2):
        r = chat(prompt if attempt == 0 else prompt + reinforce, temperature=0.8, max_tokens=5000)
        try:
            data = json.loads(clean_json(r.choices[0].message.content))
        except:
            return scipop_simple
        if _default_lang_ok(data):
            break
    data["main_tag"] = scipop_simple.get("main_tag", "")
    data["extra_tags"] = scipop_simple.get("extra_tags", [])
    data["scientists"] = scipop_simple.get("scientists", [])
    return data


def translate_scipop(scipop, target_lang):
    target_language = LANG_NAMES.get(target_lang, target_lang)
    prompt = load_prompt("translate-article").format(
        article_json=json.dumps(scipop, ensure_ascii=False), target_language=target_language,
        culture_note=CULTURE_NOTES.get(target_lang, ""))
    print(f"  🌐 Translating to {target_language}...")
    r = chat(prompt, temperature=0.4, max_tokens=8000)
    try:
        return json.loads(clean_json(r.choices[0].message.content))
    except:
        return scipop


def validate_tags(scipop, valid_tags_set):
    all_tags = [scipop.get("main_tag", "")] + scipop.get("extra_tags", [])
    fixed = []
    for t in all_tags:
        if not t: continue
        if t in valid_tags_set:
            fixed.append(t)
        else:
            t_lower = t.lower().replace(" ", "_").replace("-", "_")
            for vt in valid_tags_set:
                if vt in t_lower or t_lower in vt: fixed.append(vt); break
    seen = set();
    fixed_unique = []
    for t in fixed:
        if t not in seen: seen.add(t); fixed_unique.append(t)
    if fixed_unique:
        scipop["main_tag"] = fixed_unique[0]
        scipop["extra_tags"] = fixed_unique[1:11] if len(fixed_unique) > 1 else []
    return scipop


# ── HTML ──
_VALID_TAGS = None
_VALID_SCI = None


def valid_tag_ids():
    global _VALID_TAGS
    if _VALID_TAGS is None:
        p = Path("data/tags-graph.json")
        _VALID_TAGS = set(json.loads(p.read_text(encoding="utf-8")).get("graph", {}).keys()) if p.exists() else set()
    return _VALID_TAGS


def valid_scientist_ids():
    global _VALID_SCI
    if _VALID_SCI is None:
        p = Path(f"lang/{DEFAULT_LANG}/data/scientists.json")
        _VALID_SCI = set(json.loads(p.read_text(encoding="utf-8")).keys()) if p.exists() else set()
    return _VALID_SCI


def reading_minutes(scipop):
    """Оценка времени чтения (мин), ~180 слов/мин."""
    parts = [scipop.get("text", "")]
    for k in ("context", "methods", "results", "implications", "future_development",
              "impact_on", "next_steps", "key_problems_connection", "metaphor", "future"):
        parts.append(scipop.get(k, ""))
    words = len(re.sub(r"\[/?(tag|scientist)[^\]]*\]", " ", " ".join(parts)).split())
    return max(1, round(words / 180))


def build_jsonld(scipop, article, date_str, lang, canonical_url):
    data = {
        "@context": "https://schema.org", "@type": "ScholarlyArticle",
        "headline": scipop.get("title", article.get("title", ""))[:110],
        "description": scipop.get("oneliner", "")[:250],
        "inLanguage": lang, "datePublished": date_str,
        "url": canonical_url,
        "image": f"{SITE_URL}/{LANG_DIR}/{DEFAULT_LANG}/archive/{date_str}/{article['id']}/0.jpg",
        "author": [{"@type": "Person", "name": a} for a in article.get("authors", [])[:10]],
        "publisher": {"@type": "Organization", "name": SITE_NAME},
        "isBasedOn": f"https://arxiv.org/abs/{article['id']}",
    }
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + '</script>'


def parse_markers(text, lang):
    # Ссылку делаем ТОЛЬКО если тег/учёный реально существует. Модель иногда метит
    # понятия вне нашего списка — для них оставляем обычный текст, без битой ссылки.
    def tag_link(m):
        tid, label = m.group(1).strip(), m.group(2)
        if tid not in valid_tag_ids():
            alt = re.sub(r"[\s-]+", "_", tid.lower())
            tid = alt if alt in valid_tag_ids() else None
        if not tid:
            return label
        return f'<a href="/{LANG_DIR}/{lang}/tags/{tid}.html" class="text-tag" data-tag="{tid}">{label}</a>'

    def scientist_link(m):
        name, label = m.group(1).strip(), m.group(2)
        if name not in valid_scientist_ids():
            return label
        return (f'<a href="/{LANG_DIR}/{lang}/scientists/{attr_safe(author_slug(name))}.html" '
                f'class="text-scientist" data-scientist="{attr_safe(name)}">{label}</a>')

    text = re.sub(r'\[tag:([^\]]+)\](.*?)\[/tag\]', tag_link, text)
    text = re.sub(r'\[scientist:([^\]]+)\](.*?)\[/scientist\]', scientist_link, text)
    return text


def render_formulas(formulas):
    return "".join(
        f'<div class="formula"><div class="formula-render">{f["latex"]}</div><div class="formula-meaning">{f.get("meaning", "")}</div></div>'
        for f in formulas
    )


def gen_article_html(scipop, article, date_str, images, lang, version, captions=None):
    tpl = load_template("article")
    if not tpl.template: return "<html><body>Template not found</body></html>"

    loc = {
        "en": {"search": "Search articles, #tags, @authors", "hint": "# tag · @ author · ! scientist",
               "share": "Share", "next": "Next article",
               "license": "Original", "scientists": "Scientists:", "key_numbers": "Key numbers",
               "context": "Context", "methods": "Methods", "results": "Results",
               "implications": "Implications", "future_development": "Future development",
               "impact_on": "Impact", "next_steps": "Next steps",
               "key_problems_connection": "Key open problems",
               "author_verify_label": "I am the author — verify & edit",
               "author_verify_body": "Are you one of the authors of this paper? Email us from your institutional "
                                      "or work email address mentioning this article's arXiv ID and we'll verify "
                                      "you and give you edit access to this page."},
        "ru": {"search": "Поиск статей, #теги, @авторы", "hint": "# тег · @ автор · ! учёный",
               "share": "Поделиться", "next": "Следующая статья",
               "license": "Оригинал", "scientists": "Учёные:", "key_numbers": "Ключевые числа",
               "context": "Контекст", "methods": "Методы", "results": "Результаты",
               "implications": "Значение", "future_development": "Развитие",
               "impact_on": "Влияние", "next_steps": "Следующие шаги",
               "key_problems_connection": "Ключевые проблемы",
               "author_verify_label": "Я автор — подтвердить и редактировать",
               "author_verify_body": "Вы один из авторов этой статьи? Напишите нам с рабочей или университетской "
                                      "почты, указав arXiv ID этой статьи, и мы подтвердим вас и дадим доступ к "
                                      "редактированию этой страницы."},
        "zh": {"search": "搜索文章、#标签、@作者", "hint": "# 标签 · @ 作者 · ! 科学家",
               "share": "分享", "next": "下一篇文章",
               "license": "原文", "scientists": "科学家：", "key_numbers": "关键数据",
               "context": "背景", "methods": "方法", "results": "结果",
               "implications": "意义", "future_development": "未来发展",
               "impact_on": "影响", "next_steps": "下一步",
               "key_problems_connection": "关键未解决问题",
               "author_verify_label": "我是作者 — 验证并编辑",
               "author_verify_body": "您是这篇论文的作者之一吗？请使用您的机构或工作邮箱给我们发邮件，注明这篇文章的 arXiv "
                                      "编号，我们将验证您的身份并授予您编辑此页面的权限。"},
        "fr": {"search": "Rechercher des articles, #tags, @auteurs", "hint": "# tag · @ auteur · ! scientifique",
               "share": "Partager", "next": "Article suivant",
               "license": "Original", "scientists": "Scientifiques :", "key_numbers": "Chiffres clés",
               "context": "Contexte", "methods": "Méthodes", "results": "Résultats",
               "implications": "Implications", "future_development": "Développements futurs",
               "impact_on": "Impact", "next_steps": "Prochaines étapes",
               "key_problems_connection": "Problèmes ouverts clés",
               "author_verify_label": "Je suis l'auteur — vérifier et modifier",
               "author_verify_body": "Êtes-vous l'un des auteurs de cet article ? Envoyez-nous un e-mail depuis "
                                      "votre adresse professionnelle ou institutionnelle en mentionnant l'ID arXiv "
                                      "de cet article, et nous vous vérifierons pour vous donner accès à la "
                                      "modification de cette page."},
        "ar": {"search": "ابحث عن مقالات، #وسوم، @مؤلفين", "hint": "# وسم · @ مؤلف · ! عالم",
               "share": "مشاركة", "next": "المقال التالي",
               "license": "الأصل", "scientists": "العلماء:", "key_numbers": "أرقام رئيسية",
               "context": "السياق", "methods": "المنهجية", "results": "النتائج",
               "implications": "الأهمية", "future_development": "التطور المستقبلي",
               "impact_on": "التأثير", "next_steps": "الخطوات التالية",
               "key_problems_connection": "المسائل المفتوحة الرئيسية",
               "author_verify_label": "أنا المؤلف — تحقّق وحرّر",
               "author_verify_body": "هل أنت أحد مؤلفي هذا البحث؟ راسلنا من بريدك المؤسسي أو المهني مع ذكر رقم "
                                      "arXiv لهذا المقال، وسنتحقق منك ونمنحك صلاحية تحرير هذه الصفحة."}
    }.get(lang, {"search": "Search...", "hint": "# tag · @ author · ! scientist",
                 "share": "Share", "next": "Next article", "license": "Original",
                 "scientists": "Scientists:", "key_numbers": "Key numbers",
                 "context": "Context", "methods": "Methods", "results": "Results",
                 "implications": "Implications", "future_development": "Future development",
                 "author_verify_label": "I am the author — verify & edit",
                 "author_verify_body": "Are you one of the authors of this paper? Email us from your institutional "
                                        "or work email address mentioning this article's arXiv ID and we'll verify "
                                        "you and give you edit access to this page.",
                 "impact_on": "Impact", "next_steps": "Next steps",
                 "key_problems_connection": "Key open problems"})
    loc["min"] = {"ru": "мин", "en": "min", "zh": "分钟", "fr": "min", "ar": "دقيقة"}.get(lang, "min")
    loc["related_articles"] = {"ru": "Похожие статьи", "en": "Related articles", "zh": "相关文章",
                               "fr": "Articles similaires", "ar": "مقالات ذات صلة"}.get(lang, "Related articles")

    tags = [t for t in [scipop.get("main_tag", "")] + scipop.get("extra_tags", []) if t]
    authors = article.get("authors", [])
    authors_html = ", ".join(
        f'<a href="/{LANG_DIR}/{DEFAULT_LANG}/authors/{attr_safe(author_slug(a))}.html" class="text-author-link" data-author="{attr_safe(a)}">{safe(a)}</a>'
        for a in authors
    )
    scientists = scipop.get("scientists", [])

    if version in SIMPLE_LIKE:
        if scipop.get("text"):
            paragraphs = [p.strip() for p in re.split(r'\n\s*\n', scipop["text"]) if p.strip()]
            text_html = "".join(f"<p>{parse_markers(p, lang)}</p>" for p in paragraphs)
        else:
            parts = [scipop.get(k, "") for k in ("context", "metaphor", "future")]
            text_html = "".join(f"<p>{parse_markers(p, lang)}</p>" for p in parts if p)
        nav_html = key_numbers_html = ""
        formulas_html = render_formulas(scipop.get("formulas", []))
        fun_html = f'<div class="fun-fact">🎯 {scipop.get("fun_fact", "")}</div>' if scipop.get("fun_fact") else ""
    else:
        sections = [
            ("context", loc["context"]), ("methods", loc["methods"]), ("results", loc["results"]),
            ("implications", loc["implications"]), ("future_development", loc["future_development"]),
            ("impact_on", loc["impact_on"]), ("next_steps", loc["next_steps"]),
            ("key_problems_connection", loc["key_problems_connection"])
        ]
        nav_html = '<nav class="article-nav" id="section-nav"><ul>'
        text_html = ""
        for sid, slabel in sections:
            content = scipop.get(sid, "")
            if content:
                content = parse_markers(content, lang)
                nav_html += f'<li><a href="#{sid}">{slabel}</a></li>'
                text_html += f'<section id="{sid}"><h2>{slabel}</h2><p>{content}</p></section>'
        nav_html += '</ul></nav>'

        formulas_html = render_formulas(scipop.get("formulas", []))
        kn = scipop.get("key_numbers", {})
        key_numbers_html = ""
        if kn:
            key_numbers_html = f'<div class="key-numbers"><h3>{safe(loc["key_numbers"])}</h3><ul>' + \
                               "".join(f"<li><strong>{k}:</strong> {v}</li>" for k, v in kn.items()) + '</ul></div>'
        fun_html = f'<div class="fun-fact">🎯 {scipop.get("fun_fact", "")}</div>' if scipop.get("fun_fact") else ""

    scientists_html = ""
    if scientists:
        scientists_html = f'<div class="scientists-section"><strong>{safe(loc["scientists"])}</strong> ' + \
                          ', '.join(
                              f'<a href="/{LANG_DIR}/{lang}/scientists/{attr_safe(author_slug(s))}.html" class="text-scientist" data-scientist="{attr_safe(s)}">{s}</a>' for s
                              in scientists) + '</div>'

    mosaic_html = gen_mosaic(images, article["id"], date_str, captions)
    ai_jpg = Path(LANG_DIR) / DEFAULT_LANG / "archive" / date_str / article["id"] / "ai.jpg"
    if ai_jpg.exists():
        ai_cover_html = (f'<div class="ai-cover"><img src="/{LANG_DIR}/{DEFAULT_LANG}/archive/{date_str}/'
                         f'{article["id"]}/ai.jpg" alt=""></div>')
    else:
        ai_cover_html = '<div class="ai-cover ai-cover-ph"></div>'
    tags_side_html = gen_tags_side(tags, lang)

    page_file = VERSION_FILES[version]
    version_toggle_html = version_toggle_links(lang, version, date_str, article["id"])
    # canonical — собственный URL страницы; языковые альтернативы описывает hreflang
    canonical_url = f"{SITE_URL}/{LANG_DIR}/{lang}/archive/{date_str}/{article['id']}/{page_file}"

    cats = article.get("categories", [])
    categories_html = ""
    if cats:
        badges = " ".join(
            f'<span class="cat-badge" data-cat="{c}">{ARXIV_CATEGORIES.get(c, c)}</span>' for c in cats[:5])
        categories_html = f'· {badges}'

    lic = article.get("license_url", "")
    lic_name = "CC BY 4.0" if "by/4.0" in lic else (
        "CC BY-SA 4.0" if "by-sa" in lic else ("CC0" if "zero" in lic else "CC BY"))

    hreflang_links = "\n    ".join(
        f'<link rel="alternate" hreflang="{l}" href="{SITE_URL}/{LANG_DIR}/{l}/archive/{date_str}/{article["id"]}/{page_file}">'
        for l in LANGUAGES
    ) + f'\n    <link rel="alternate" hreflang="x-default" href="{SITE_URL}/{LANG_DIR}/{DEFAULT_LANG}/archive/{date_str}/{article["id"]}/{page_file}">'

    rmin = reading_minutes(scipop)
    reading_html = f'<span class="reading-time">⏱ {rmin} {safe(loc.get("min", "min"))}</span>'
    jsonld_html = build_jsonld(scipop, article, date_str, lang, canonical_url)

    return tpl.substitute(
        lang=lang, site_name=SITE_NAME, site_url=SITE_URL, goatcounter=GOATCOUNTER,
        authors_lang=DEFAULT_LANG,
        clickbait=safe(scipop.get("title", article["title"])),
        clickbait_escaped=safe(scipop.get("title", "").replace("'", "\\'")),
        original_title=safe(article["title"]),
        oneliner=safe(scipop.get("oneliner", "")),
        oneliner_short=safe(scipop.get("oneliner", "")[:160]),
        oneliner_og=safe(scipop.get("oneliner", "")[:200]),
        description=safe(scipop.get("description", scipop.get("oneliner", ""))[:300]),
        id=article["id"], date=date_str,
        version_toggle_html=version_toggle_html,
        authors_full=authors_html,
        search_placeholder=safe(loc.get("search", "")),
        search_hint=safe(loc.get("hint", "# tag · @ author · ! scientist")),
        author_verify_label=safe(loc.get("author_verify_label", "I am the author — verify & edit")),
        author_verify_body=safe(loc.get("author_verify_body", "")),
        share_label=safe(loc.get("share", "Share")),
        next_label=safe(loc.get("next", "Next article")),
        license_label=safe(loc.get("license", "Original")),
        license_url=lic, license_name=lic_name,
        canonical_url=canonical_url, hreflang_links=hreflang_links,
        tags_side_html=tags_side_html, mosaic_html=mosaic_html, ai_cover_html=ai_cover_html,
        nav_html=nav_html, text_html=text_html,
        formulas_html=formulas_html, key_numbers_html=key_numbers_html,
        scientists_html=scientists_html,
        fun_fact_html=fun_html,
        reading_html=reading_html, jsonld_html=jsonld_html,
        related_label=safe(loc.get("related_articles", "Related articles")),
        categories_html=categories_html,
    )


# ── Data.json ──
def save_data_json(versions_ru, article, date_str, folder, translations=None, captions=None):
    """versions_ru: {version: scipop_ru}; translations: {version: {lang: scipop}}.
    Пишет по ключу на каждую версию (popular/simple/advanced), плюс мета и подписи к картинкам."""
    translations = translations or {}
    scipop_adv = versions_ru.get("advanced", {})
    payload = {
        "id": article["id"], "original_title": article["title"],
        "authors": article.get("authors", []), "date": date_str,
        "license": article.get("license_url", ""), "license_name": article.get("license_name", "CC BY"),
        "tags": [scipop_adv.get("main_tag", "")] + scipop_adv.get("extra_tags", []),
        "main_tag": scipop_adv.get("main_tag", ""),
        "scientists": scipop_adv.get("scientists", []),
        "categories": article.get("categories", []),
        "primary_category": article.get("primary_category", ""),
        "cited_arxiv": article.get("cited_arxiv", []),
    }
    if captions:
        payload["captions"] = captions
    for v in VERSIONS:
        vdata = {DEFAULT_LANG: versions_ru.get(v, {})}
        vdata.update(translations.get(v, {}))
        payload[v] = vdata
    (folder / "data.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Indexes ──
def update_index(scipop, article, date_str, lang, version):
    base = Path(LANG_DIR) / lang
    base.mkdir(parents=True, exist_ok=True)
    filename = VERSION_INDEX[version]
    ip = base / filename
    idx = json.loads(ip.read_text(encoding="utf-8")) if ip.exists() else []
    idx = [x for x in idx if x.get("id") != article["id"]]
    url = f"/{LANG_DIR}/{lang}/archive/{date_str}/{article['id']}/{VERSION_FILES[version]}"
    idx.append({
        "id": article["id"], "version": version,
        "title": scipop.get("title", article["title"]),
        "oneliner": scipop.get("oneliner", "")[:300],
        "description": scipop.get("description", "")[:300],
        "authors": article.get("authors", [])[:5], "date": date_str,
        "tags": [scipop.get("main_tag", "")] + scipop.get("extra_tags", []),
        "scientists": scipop.get("scientists", []), "url": url,
        "reading": reading_minutes(scipop),
        "categories": article.get("categories", []),
        "primary_category": article.get("primary_category", ""),
    })
    ip.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")


def update_authors_graph(article):
    ap = Path("data/authors-graph.json")
    graph = json.loads(ap.read_text(encoding="utf-8")) if ap.exists() else {}
    for a in article.get("authors", []):
        if a not in graph: graph[a] = {"articles": [], "coauthors": [], "article_count": 0}
        if article["id"] not in graph[a]["articles"]:
            graph[a]["articles"].append(article["id"])
            graph[a]["article_count"] = len(graph[a]["articles"])
        for ca in article.get("authors", []):
            if ca != a and ca not in graph[a]["coauthors"]: graph[a]["coauthors"].append(ca)
    ap.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")


def update_tag_counts(scipop):
    gp = Path("data/tags-graph.json")
    if not gp.exists(): return
    graph = json.loads(gp.read_text(encoding="utf-8"))
    for t in [scipop.get("main_tag", "")] + scipop.get("extra_tags", []):
        if t and t in graph.get("graph", {}):
            graph["graph"][t]["article_count"] = graph["graph"][t].get("article_count", 0) + 1
            if "scientists" not in graph["graph"][t]: graph["graph"][t]["scientists"] = []
            for s in scipop.get("scientists", []):
                if s not in graph["graph"][t]["scientists"]: graph["graph"][t]["scientists"].append(s)
    gp.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Pages ──
def ensure_lang_structure(lang):
    base = Path(LANG_DIR) / lang
    for d in ["archive", "tags", "scientists"]: (base / d).mkdir(parents=True, exist_ok=True)
    if not (base / "index.html").exists(): generate_index_page(lang)
    if not (base / "about.html").exists(): generate_about_page(lang)
    if not (base / "articles-index.json").exists(): (base / "articles-index.json").write_text("[]", encoding="utf-8")


def generate_index_page(lang):
    tpl = load_template("index")
    if not tpl.template: return
    loc = {
        "en": {"search": "Search articles, #tags, @authors", "hint": "# tag · @ author · ! scientist",
               "loading": "Loading...", "footer": "science made simple"},
        "ru": {"search": "Поиск статей, #теги, @авторы", "hint": "# тег · @ автор · ! учёный", "loading": "Загрузка...",
               "footer": "наука простыми словами"},
        "zh": {"search": "搜索文章、#标签、@作者", "hint": "# 标签 · @ 作者 · ! 科学家", "loading": "加载中...",
               "footer": "让科学变简单"},
        "fr": {"search": "Rechercher des articles, #tags, @auteurs", "hint": "# tag · @ auteur · ! scientifique",
               "loading": "Chargement...", "footer": "la science simplifiée"},
        "ar": {"search": "ابحث عن مقالات، #وسوم، @مؤلفين", "hint": "# وسم · @ مؤلف · ! عالم",
               "loading": "جارٍ التحميل...", "footer": "العلم ببساطة"}
    }.get(lang, {"search": "Search...", "hint": "", "loading": "Loading...", "footer": ""})
    (Path(LANG_DIR) / lang / "index.html").write_text(tpl.substitute(
        lang=lang, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG,
        search_placeholder=safe(loc["search"]), search_hint=safe(loc["hint"]),
        loading_text=safe(loc["loading"]), footer_text=safe(loc["footer"]),
        version_toggle_html=version_toggle_spans(lang, "popular")
    ), encoding="utf-8")


def generate_about_page(lang):
    tpl = load_template("about")
    if not tpl.template: return
    loc = {
        "en": {"title": "About", "body": "We translate scientific papers from arXiv into clear articles.",
               "footer": "science made simple"},
        "ru": {"title": "О проекте", "body": "Мы переводим научные статьи с arXiv на понятный язык.",
               "footer": "наука простыми словами"},
        "zh": {"title": "关于我们", "body": "我们将 arXiv 上的科学论文翻译成通俗易懂的文章。",
               "footer": "让科学变简单"},
        "fr": {"title": "À propos", "body": "Nous traduisons des articles scientifiques d'arXiv en textes clairs.",
               "footer": "la science simplifiée"},
        "ar": {"title": "عن المشروع", "body": "نترجم الأبحاث العلمية من arXiv إلى مقالات واضحة ومبسّطة.",
               "footer": "العلم ببساطة"}
    }.get(lang, {"title": "About", "body": "", "footer": ""})
    (Path(LANG_DIR) / lang / "about.html").write_text(tpl.substitute(
        lang=lang, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG,
        title=safe(loc["title"]), body=safe(loc["body"]), footer_text=safe(loc["footer"])
    ), encoding="utf-8")


def generate_tags_cloud(lang):
    tpl = load_template("tags-cloud")
    if not tpl.template: return
    tags_loc = load_tags_loc(lang)
    idx_path = Path(LANG_DIR) / lang / "articles-index.json"
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else []
    tag_counts = {}
    for a in index:
        for t in a.get("tags", []): tag_counts[t] = tag_counts.get(t, 0) + 1
    max_count = max(tag_counts.values()) if tag_counts else 1
    # Граф — источник всех тегов, включая образовательные (0 статей): они всё равно
    # должны быть в облаке отдельным типом карточек (обучающая карта).
    gp = Path("data/tags-graph.json")
    graph = json.loads(gp.read_text(encoding="utf-8")).get("graph", {}) if gp.exists() else {}
    edu_ids = [tid for tid, n in graph.items() if n.get("educational")]
    cloud_html = ""
    for tag_id, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
        if graph.get(tag_id, {}).get("educational"):
            continue  # образовательные выводим отдельным блоком ниже
        size = "size-l" if count >= max_count * 0.7 else ("size-m" if count >= max_count * 0.3 else "size-s")
        name = tags_loc.get(tag_id, {}).get("name", tag_id)
        cloud_html += f'<a href="/{LANG_DIR}/{lang}/tags/{tag_id}.html" class="tag-item {size}" data-tag="{tag_id}"><span class="check"></span>{name}</a>\n'
    for tag_id in sorted(edu_ids, key=lambda t: tags_loc.get(t, {}).get("name", t)):
        name = tags_loc.get(tag_id, {}).get("name", tag_id)
        cloud_html += f'<a href="/{LANG_DIR}/{lang}/tags/{tag_id}.html" class="tag-item size-s educational" data-tag="{tag_id}"><span class="check"></span>{name}</a>\n'
    loc = {
        "en": {"title": "Tags", "subtitle": "Select tags to filter articles.", "footer": "science made simple"},
        "ru": {"title": "Теги", "subtitle": "Выберите теги для фильтрации статей.", "footer": "наука простыми словами"},
        "zh": {"title": "标签", "subtitle": "选择标签以筛选文章。", "footer": "让科学变简单"},
        "fr": {"title": "Tags", "subtitle": "Sélectionnez des tags pour filtrer les articles.", "footer": "la science simplifiée"},
        "ar": {"title": "الوسوم", "subtitle": "اختر الوسوم لتصفية المقالات.", "footer": "العلم ببساطة"}
    }.get(lang, {"title": "Tags", "subtitle": "", "footer": ""})
    (Path(LANG_DIR) / lang / "tags" / "index.html").write_text(tpl.substitute(
        lang=lang, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG,
        tags_title=safe(loc["title"]), tags_subtitle=safe(loc["subtitle"]),
        footer_text=safe(loc["footer"]), selected_tags_html="", tags_cloud_html=cloud_html
    ), encoding="utf-8")


def generate_tag_page(tag_id, lang):
    tpl = load_template("tag")
    if not tpl.template: return
    tags_loc = load_tags_loc(lang)
    tag_data = tags_loc.get(tag_id, {})
    graph = json.loads(Path("data/tags-graph.json").read_text(encoding="utf-8"))
    tag_graph = graph.get("graph", {}).get(tag_id, {})
    idx_path = Path(LANG_DIR) / lang / "articles-index.json"
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else []

    articles_html = ""
    for a in index:
        if tag_id in a.get("tags", []) and a.get("version") == "popular":
            articles_html += f"""<div class="article-card"><div class="card-content">
                <h3><a href="{a['url']}">{a['title']}</a></h3>
                <div class="oneliner">{a.get('description', a.get('oneliner', ''))}</div>
                <div class="meta">arXiv:{a['id']} · {a['date']}</div></div></div>"""

    related_html = "".join(
        f'<a href="/{LANG_DIR}/{lang}/tags/{rt}.html" data-tag="{attr_safe(rt)}">{tags_loc.get(rt, {}).get("name", rt)}</a>'
        for rt in tag_graph.get("related", [])[:8]
    )
    formulas_html = render_formulas(tag_data.get("formulas", []))
    scientists_links = " ".join(
        f'<a href="/{LANG_DIR}/{lang}/scientists/{attr_safe(author_slug(s))}.html" class="text-scientist" data-scientist="{attr_safe(s)}">{s}</a>'
        for s in tag_data.get("scientists", [])
    )
    loc = {
        "en": {"related": "Related tags", "history": "History", "how": "How it works", "problems": "Open problems & fun facts",
               "search": "Search...", "hint": "# tag · @ author · ! scientist", "footer": "science made simple",
               "scientists": "Scientists:", "no_articles": "No articles yet"},
        "ar": {"related": "وسوم ذات صلة", "history": "التاريخ", "how": "كيف يعمل",
               "problems": "مسائل مفتوحة وحقائق طريفة", "search": "بحث...",
               "hint": "# وسم · @ مؤلف · ! عالم", "footer": "العلم ببساطة",
               "scientists": "العلماء:", "no_articles": "لا مقالات بعد"},
        "ru": {"related": "Связанные теги", "history": "История", "how": "Как работает",
               "problems": "Открытые проблемы и интересные факты", "search": "Поиск...",
               "hint": "# тег · @ автор · ! учёный", "footer": "наука простыми словами",
               "scientists": "Учёные:", "no_articles": "Пока нет статей"},
        "zh": {"related": "相关标签", "history": "历史", "how": "工作原理", "problems": "未解决的问题与趣味知识",
               "search": "搜索...", "hint": "# 标签 · @ 作者 · ! 科学家", "footer": "让科学变简单",
               "scientists": "科学家：", "no_articles": "暂无文章"},
        "fr": {"related": "Tags associés", "history": "Histoire", "how": "Fonctionnement",
               "problems": "Problèmes ouverts et anecdotes", "search": "Rechercher...",
               "hint": "# tag · @ auteur · ! scientifique", "footer": "la science simplifiée",
               "scientists": "Scientifiques :", "no_articles": "Pas encore d'articles"}
    }.get(lang, {"related": "Related", "history": "History", "how": "How it works", "problems": "Open problems & fun facts",
                 "search": "Search...", "hint": "# tag · @ author · ! scientist", "footer": "",
                 "scientists": "Scientists:", "no_articles": "No articles yet"})

    problems_and_fact_html = ""
    if tag_data.get("key_problems") or tag_data.get("fun_fact"):
        problems_and_fact_html = f'<div class="section"><h2>{safe(loc["problems"])}</h2>'
        if tag_data.get("key_problems"):
            problems_and_fact_html += f'<p>{safe("; ".join(tag_data["key_problems"]))}</p>'
        if tag_data.get("fun_fact"):
            problems_and_fact_html += f'<p class="fact">💡 {safe(tag_data["fun_fact"])}</p>'
        problems_and_fact_html += '</div>'

    fun_fact_html = ""
    if tag_data.get("fun_fact"):
        fun_fact_html = f'<div class="fun-fact">💡 {safe(tag_data["fun_fact"])}</div>'
    fun_fact_popular_html = ""
    ff_pop = tag_data.get("fun_fact_popular") or tag_data.get("fun_fact", "")
    if ff_pop:
        fun_fact_popular_html = f'<div class="fun-fact">💡 {safe(ff_pop)}</div>'

    scientists_section_html = ""
    if scientists_links:
        scientists_section_html = f'<div class="scientists-section"><strong>{safe(loc["scientists"])}</strong> {scientists_links}</div>'

    tag_version_toggle = version_toggle_spans(lang, "popular")
    tag_version_toggle = tag_version_toggle.replace('id="version-toggle"', 'id="tag-version-toggle"')

    desc_pop = tag_data.get("description_popular") or tag_data.get("description_simple") or tag_data.get("description", "")
    desc_simple = tag_data.get("description_simple") or tag_data.get("description", "")
    hist_simple = tag_data.get("history_simple") or tag_data.get("history", "")
    how_simple = tag_data.get("how_it_works_simple") or tag_data.get("how_it_works", "")

    (Path(LANG_DIR) / lang / "tags" / f"{tag_id}.html").write_text(tpl.substitute(
        lang=lang, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG,
        tag_id=attr_safe(tag_id),
        tag_name=safe(tag_data.get("name", tag_id)), article_count=tag_graph.get("article_count", 0),
        tag_version_toggle=tag_version_toggle,
        tag_description_popular=safe(desc_pop),
        fun_fact_popular_html=fun_fact_popular_html,
        tag_description_simple=safe(desc_simple),
        tag_history_simple=safe(hist_simple),
        tag_how_it_works_simple=safe(how_simple),
        fun_fact_html=fun_fact_html,
        tag_description=safe(tag_data.get("description", "")),
        tag_history=safe(tag_data.get("history", "")),
        tag_how_it_works=safe(tag_data.get("how_it_works", "")),
        problems_and_fact_html=problems_and_fact_html,
        formulas_html=formulas_html, scientists_section_html=scientists_section_html,
        laws_section_html=laws_for_tag(tag_id, lang),
        history_label=safe(loc["history"]), how_label=safe(loc["how"]),
        related_label=safe(loc["related"]),
        related_tags_html=related_html, search_placeholder=safe(loc["search"]),
        search_hint=safe(loc["hint"]),
        articles_list_html=articles_html or f'<p>{safe(loc["no_articles"])}</p>', footer_text=safe(loc["footer"])
    ), encoding="utf-8")


def update_all_tags(lang):
    generate_tags_cloud(lang)
    graph = json.loads(Path("data/tags-graph.json").read_text(encoding="utf-8"))
    for tag_id in graph.get("graph", {}): generate_tag_page(tag_id, lang)
    print(f"  🏷️ Tags updated for {lang}")


# ── Законы (закон/принцип/теорема/эффект) — слой поверх тегов, дом формул ──
def load_laws_loc(lang):
    p = Path(f"lang/{lang}/data/laws.json")
    if not p.exists(): p = Path(f"lang/{DEFAULT_LANG}/data/laws.json")
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


LAWS_LABELS = {
    "ru": {"title": "Законы и принципы", "subtitle": "Фундаментальные законы науки. Формула — лишь отображение; суть в тексте.",
           "history": "История открытия", "how": "Как работает", "problems": "Нюансы", "laws": "Законы:", "footer": "наука простыми словами",
           "search": "Найти закон...", "tags": "Связанные понятия", "related_laws": "Связанные законы", "articles": "Статьи по теме", "scientists": "Открыли:"},
    "en": {"title": "Laws & Principles", "subtitle": "Fundamental laws of science. The formula is just a representation; the idea is in the text.",
           "history": "Discovery", "how": "How it works", "problems": "Caveats", "laws": "Laws:", "footer": "science made simple",
           "search": "Find a law...", "tags": "Related concepts", "related_laws": "Related laws", "articles": "Related articles", "scientists": "Discovered by:"},
    "zh": {"title": "定律与原理", "subtitle": "科学的基本定律。公式只是表现形式，本质在文字中。",
           "history": "发现历史", "how": "工作原理", "problems": "注意事项", "laws": "定律：", "footer": "让科学变简单",
           "search": "查找定律...", "tags": "相关概念", "related_laws": "相关定律", "articles": "相关文章", "scientists": "发现者："},
    "fr": {"title": "Lois et principes", "subtitle": "Lois fondamentales de la science. La formule n'est qu'une représentation.",
           "history": "Découverte", "how": "Fonctionnement", "problems": "Nuances", "laws": "Lois :", "footer": "la science simplifiée",
           "search": "Trouver une loi...", "tags": "Concepts liés", "related_laws": "Lois liées", "articles": "Articles liés", "scientists": "Découverte par :"},
    "ar": {"title": "القوانين والمبادئ", "subtitle": "القوانين الأساسية للعلم. الصيغة مجرد تمثيل؛ الفكرة في النص.",
           "history": "تاريخ الاكتشاف", "how": "كيف يعمل", "problems": "ملاحظات", "laws": "القوانين:", "footer": "العلم ببساطة",
           "search": "ابحث عن قانون...", "tags": "مفاهيم ذات صلة", "related_laws": "قوانين ذات صلة", "articles": "مقالات ذات صلة", "scientists": "اكتشفه:"},
}

LAW_TYPE_COLORS = {"закон": "#C0392B", "принцип": "#8E44AD", "теорема": "#2471A3",
                   "эффект": "#B9770E", "уравнение": "#148F77", "теория": "#5D6D7E"}


def laws_for_tag(tag_id, lang):
    """Ссылки на СТРАНИЦЫ законов, относящихся к тегу (секция «Законы» на странице тега)."""
    laws = load_laws_loc(lang)
    loc = LAWS_LABELS.get(lang, LAWS_LABELS["en"])
    related = [(lid, L) for lid, L in laws.items() if tag_id in (L.get("tags") or [])]
    if not related:
        return ""
    chips = " ".join(
        f'<a href="/{LANG_DIR}/{lang}/laws/{attr_safe(lid)}.html" class="law-chip">{safe(L.get("name", lid))}</a>'
        for lid, L in related[:14])
    return f'<div class="tag-laws"><strong>{safe(loc["laws"])}</strong> {chips}</div>'


def generate_laws_cloud(lang):
    """Облако ИМЁН законов (как теги): каждое имя — ссылка на страницу закона. + граф."""
    tpl = load_template("laws-cloud")
    if not tpl.template: return
    laws = load_laws_loc(lang)
    loc = LAWS_LABELS.get(lang, LAWS_LABELS["en"])
    order = sorted(laws.keys(), key=lambda lid: (-len(laws[lid].get("tags", [])), laws[lid].get("name", "")))
    cloud = ""
    for lid in order:
        L = laws[lid]
        color = LAW_TYPE_COLORS.get(L.get("type", ""), "#888")
        cloud += (
            f'<a href="/{LANG_DIR}/{lang}/laws/{attr_safe(lid)}.html" class="tag-item size-m law-item" '
            f'data-law="{attr_safe(lid)}" title="{attr_safe(L.get("type", ""))}">'
            f'<span class="law-type-dot" style="background:{color}"></span>{safe(L.get("name", lid))}</a>\n'
        )
    (Path(LANG_DIR) / lang / "laws").mkdir(parents=True, exist_ok=True)
    (Path(LANG_DIR) / lang / "laws" / "index.html").write_text(tpl.substitute(
        lang=lang, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG,
        laws_title=safe(loc["title"]), laws_subtitle=safe(loc["subtitle"]),
        search_placeholder=safe(loc["search"]),
        laws_cloud_html=cloud or f'<p>{safe(loc["subtitle"])}</p>',
        footer_text=safe(loc["footer"])
    ), encoding="utf-8")


def generate_law_page(law_id, lang):
    """Отдельная страница закона (как страница тега): описание ×3, формулы, история, связи, статьи по теме."""
    tpl = load_template("law")
    if not tpl.template: return
    laws = load_laws_loc(lang)
    L = laws.get(law_id, {})
    if not L: return
    tags_loc = load_tags_loc(lang)
    loc = LAWS_LABELS.get(lang, LAWS_LABELS["en"])
    law_tags = L.get("tags") or []

    toggle = version_toggle_spans(lang, "popular").replace('id="version-toggle"', 'id="law-version-toggle"')
    formulas_html = render_formulas(L.get("formulas", []))
    related_tags_html = " ".join(
        f'<a href="/{LANG_DIR}/{lang}/tags/{t}.html" data-tag="{attr_safe(t)}">{safe(tags_loc.get(t, {}).get("name", t))}</a>'
        for t in law_tags if t)
    sci_links = " ".join(
        f'<a href="/{LANG_DIR}/{lang}/scientists/{attr_safe(author_slug(s))}.html" class="text-scientist" data-scientist="{attr_safe(s)}">{safe(s)}</a>'
        for s in (L.get("scientists") or []))
    scientists_section_html = f'<div class="scientists-section"><strong>{safe(loc["scientists"])}</strong> {sci_links}</div>' if sci_links else ""
    related_laws = [rl for rl in (L.get("related_laws") or []) if rl in laws]
    related_laws_html = " ".join(
        f'<a href="/{LANG_DIR}/{lang}/laws/{attr_safe(rl)}.html" class="law-chip">{safe(laws[rl].get("name", rl))}</a>'
        for rl in related_laws)
    related_laws_block = f'<div class="related-tags"><strong>{safe(loc["related_laws"])}:</strong> {related_laws_html}</div>' if related_laws_html else ""

    def sec(label, text):
        return f'<div class="section"><h2>{safe(label)}</h2><p>{safe(text)}</p></div>' if text else ""
    fun_fact_popular_html = f'<div class="fun-fact">💡 {safe(L.get("fun_fact_popular") or L.get("fun_fact", ""))}</div>' if (L.get("fun_fact_popular") or L.get("fun_fact")) else ""
    fun_fact_html = f'<div class="fun-fact">💡 {safe(L.get("fun_fact", ""))}</div>' if L.get("fun_fact") else ""
    problems = L.get("key_problems") or []
    problems_html = f'<div class="section"><h2>{safe(loc["problems"])}</h2><p>{safe("; ".join(problems))}</p></div>' if problems else ""

    # Статьи по теме — по объединению тегов закона (как лента тега, но для нескольких тегов)
    idx_path = Path(LANG_DIR) / lang / "articles-index.json"
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else []
    seen = set()
    articles_html = ""
    for a in index:
        if a.get("version") != "popular": continue
        if not (set(a.get("tags", [])) & set(law_tags)): continue
        if a["id"] in seen: continue
        seen.add(a["id"])
        articles_html += (
            f'<div class="article-card"><div class="card-content">'
            f'<h3><a href="{a["url"]}">{safe(a["title"])}</a></h3>'
            f'<div class="oneliner">{safe(a.get("description", a.get("oneliner", "")))}</div>'
            f'<div class="meta">arXiv:{a["id"]} · {a["date"]}</div></div></div>'
        )

    (Path(LANG_DIR) / lang / "laws" / f"{law_id}.html").write_text(tpl.substitute(
        lang=lang, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG,
        law_name=safe(L.get("name", law_id)), law_type=safe(L.get("type", "")),
        law_version_toggle=toggle,
        desc_popular=safe(L.get("description_popular") or L.get("description_simple") or L.get("description", "")),
        fun_fact_popular_html=fun_fact_popular_html,
        desc_simple=safe(L.get("description_simple") or L.get("description", "")),
        how_simple_html=sec(loc["how"], L.get("how_it_works_simple", "")),
        fun_fact_html=fun_fact_html,
        desc_advanced=safe(L.get("description", "")),
        history_html=sec(loc["history"], L.get("history", "")),
        how_html=sec(loc["how"], L.get("how_it_works", "")),
        problems_html=problems_html,
        formulas_html=formulas_html,
        scientists_section_html=scientists_section_html,
        tags_label=safe(loc["tags"]), related_tags_html=related_tags_html,
        related_laws_block=related_laws_block,
        articles_label=safe(loc["articles"]),
        primary_tag=attr_safe(law_tags[0] if law_tags else ""),
        articles_list_html=articles_html or f'<p style="color:var(--soft)">—</p>',
        footer_text=safe(loc["footer"])
    ), encoding="utf-8")


def update_all_laws(lang):
    laws = load_laws_loc(lang)
    if not laws:
        return
    generate_laws_cloud(lang)
    for law_id in laws:
        generate_law_page(law_id, lang)
    print(f"  ⚖️ Laws updated for {lang} ({len(laws)} pages)")


def generate_scientists_cloud(lang):
    tpl = load_template("scientists-cloud")
    if not tpl.template: return
    sp = Path(f"lang/{lang}/data/scientists.json")
    if not sp.exists(): sp = Path(f"lang/{DEFAULT_LANG}/data/scientists.json")
    scientists = json.loads(sp.read_text(encoding="utf-8"))
    cloud_html = "".join(
        f'<a href="/{LANG_DIR}/{lang}/scientists/{attr_safe(author_slug(sid))}.html" class="scientist-item" data-scientist="{attr_safe(sid)}"><span class="check"></span>{data.get("name", sid)}</a>'
        for sid, data in scientists.items()
    )
    loc = {
        "en": {"title": "Scientists", "subtitle": "Great minds behind the discoveries.",
               "search": "Find scientists...", "footer": "science made simple"},
        "ru": {"title": "Учёные", "subtitle": "Великие умы стоящие за открытиями.", "search": "Найти учёных...",
               "footer": "наука простыми словами"},
        "zh": {"title": "科学家", "subtitle": "发现背后的伟大头脑。", "search": "查找科学家...",
               "footer": "让科学变简单"},
        "fr": {"title": "Scientifiques", "subtitle": "Les grands esprits derrière les découvertes.",
               "search": "Rechercher des scientifiques...", "footer": "la science simplifiée"},
        "ar": {"title": "العلماء", "subtitle": "العقول العظيمة وراء الاكتشافات.",
               "search": "ابحث عن علماء...", "footer": "العلم ببساطة"}
    }.get(lang, {"title": "Scientists", "subtitle": "", "search": "Find...", "footer": ""})
    (Path(LANG_DIR) / lang / "scientists" / "index.html").write_text(tpl.substitute(
        lang=lang, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG,
        scientists_title=safe(loc["title"]), scientists_subtitle=safe(loc["subtitle"]),
        search_placeholder=safe(loc["search"]), scientists_cloud_html=cloud_html,
        footer_text=safe(loc["footer"])
    ), encoding="utf-8")


def generate_scientist_page(sid, lang):
    tpl = load_template("scientist")
    if not tpl.template: return
    sp = Path(f"lang/{lang}/data/scientists.json")
    if not sp.exists(): sp = Path(f"lang/{DEFAULT_LANG}/data/scientists.json")
    scientists = json.loads(sp.read_text(encoding="utf-8"))
    data = scientists.get(sid, {})
    if not data: return
    tags_loc = load_tags_loc(lang)
    related_html = "".join(
        f'<a href="/{LANG_DIR}/{lang}/tags/{t}.html" data-tag="{attr_safe(t)}">{tags_loc.get(t, {}).get("name", t)}</a>'
        for t in data.get("related_tags", [])[:8]
    )
    idx_path = Path(LANG_DIR) / lang / "articles-index.json"
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else []
    articles_html = ""
    for a in index:
        if sid in a.get("scientists", []) and a.get("version") == "popular":
            articles_html += f"""<div class="article-card"><div class="card-content">
                <h3><a href="{a['url']}">{a['title']}</a></h3>
                <div class="oneliner">{a.get('description', a.get('oneliner', ''))}</div>
                <div class="meta">arXiv:{a['id']} · {a['date']}</div></div></div>"""
    loc = {
        "en": {"related": "Related tags", "discoveries": "Key discoveries", "bio": "Biography", "quote": "Quote",
               "search": "Search...", "hint": "! scientist · # tag · @ author", "footer": "science made simple",
               "no_articles": "No articles yet"},
        "ar": {"related": "وسوم ذات صلة", "discoveries": "اكتشافات رئيسية", "bio": "سيرة", "quote": "اقتباس",
               "search": "بحث...", "hint": "! عالم · # وسم · @ مؤلف", "footer": "العلم ببساطة",
               "no_articles": "لا مقالات بعد"},
        "ru": {"related": "Связанные теги", "discoveries": "Ключевые открытия", "bio": "Биография", "quote": "Цитата",
               "search": "Поиск...", "hint": "! учёный · # тег · @ автор", "footer": "наука простыми словами",
               "no_articles": "Пока нет статей"},
        "zh": {"related": "相关标签", "discoveries": "重要发现", "bio": "生平", "quote": "名言",
               "search": "搜索...", "hint": "! 科学家 · # 标签 · @ 作者", "footer": "让科学变简单",
               "no_articles": "暂无文章"},
        "fr": {"related": "Tags associés", "discoveries": "Découvertes clés", "bio": "Biographie", "quote": "Citation",
               "search": "Rechercher...", "hint": "! scientifique · # tag · @ auteur", "footer": "la science simplifiée",
               "no_articles": "Pas encore d'articles"}
    }.get(lang, {"related": "Related", "discoveries": "Discoveries", "bio": "Biography", "quote": "Quote",
                 "search": "Search...", "hint": "! scientist · # tag · @ author", "footer": "",
                 "no_articles": "No articles yet"})
    (Path(LANG_DIR) / lang / "scientists" / f"{author_slug(sid)}.html").write_text(tpl.substitute(
        lang=lang, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG,
        scientist_id=attr_safe(sid),
        scientist_name=safe(data.get("name", sid)), lifespan=data.get("lifespan", ""),
        fields=", ".join(data.get("fields", [])),
        scientist_description=safe(data.get("description", "")),
        scientist_biography=safe(data.get("biography", "")),
        scientist_discoveries="".join(f"<li>{d}</li>" for d in data.get("key_discoveries", [])),
        scientist_quote=safe(data.get("quote", "")), scientist_fun_fact=safe(data.get("fun_fact", "")),
        discoveries_label=safe(loc["discoveries"]), bio_label=safe(loc["bio"]),
        quote_label=safe(loc["quote"]), related_tags_label=safe(loc["related"]),
        related_tags_html=related_html, search_placeholder=safe(loc["search"]),
        search_hint=safe(loc["hint"]),
        articles_list_html=articles_html or f'<p>{safe(loc["no_articles"])}</p>', footer_text=safe(loc["footer"])
    ), encoding="utf-8")


def update_all_scientists(lang):
    (Path(LANG_DIR) / lang / "scientists").mkdir(parents=True, exist_ok=True)
    generate_scientists_cloud(lang)
    sp = Path(f"lang/{lang}/data/scientists.json")
    if not sp.exists(): sp = Path(f"lang/{DEFAULT_LANG}/data/scientists.json")
    for sid in json.loads(sp.read_text(encoding="utf-8")): generate_scientist_page(sid, lang)
    print(f"  👨‍🔬 Scientists updated for {lang}")


def update_all_authors():
    (Path(LANG_DIR) / DEFAULT_LANG / "authors").mkdir(parents=True, exist_ok=True)
    tpl_cloud, tpl_page = load_template("authors-cloud"), load_template("author")
    if not tpl_cloud.template or not tpl_page.template: return
    loc = {
        "en": {"title": "Authors", "subtitle": "Researchers publishing on arXiv.", "find": "Find authors...",
               "search": "Search articles...", "hint": "@ author · # tag · ! scientist",
               "coauthors": "Co-authors", "no_articles": "No articles yet", "footer": "science made simple",
               "articles": "articles", "coauthors_word": "co-authors"},
        "ru": {"title": "Авторы", "subtitle": "Исследователи, публикующиеся в arXiv.", "find": "Найти авторов...",
               "search": "Поиск статей...", "hint": "@ автор · # тег · ! учёный",
               "coauthors": "Соавторы", "no_articles": "Пока нет статей", "footer": "наука простыми словами",
               "articles": "статей", "coauthors_word": "соавторов"},
        "zh": {"title": "作者", "subtitle": "在 arXiv 上发表论文的研究人员。", "find": "查找作者...",
               "search": "搜索文章...", "hint": "@ 作者 · # 标签 · ! 科学家",
               "coauthors": "合著者", "no_articles": "暂无文章", "footer": "让科学变简单",
               "articles": "篇文章", "coauthors_word": "位合著者"},
        "fr": {"title": "Auteurs", "subtitle": "Chercheurs publiant sur arXiv.", "find": "Rechercher des auteurs...",
               "search": "Rechercher des articles...", "hint": "@ auteur · # tag · ! scientifique",
               "coauthors": "Co-auteurs", "no_articles": "Pas encore d'articles", "footer": "la science simplifiée",
               "articles": "articles", "coauthors_word": "co-auteurs"}
    }.get(DEFAULT_LANG, {"title": "Authors", "subtitle": "Researchers publishing on arXiv.", "find": "Find authors...",
                          "search": "Search articles...", "hint": "@ author · # tag · ! scientist",
                          "coauthors": "Co-authors", "no_articles": "No articles yet", "footer": "science made simple",
                          "articles": "articles", "coauthors_word": "co-authors"})
    ap = Path("data/authors-graph.json")
    graph = json.loads(ap.read_text(encoding="utf-8")) if ap.exists() else {}

    # id -> дата (из индекса языка по умолчанию) для «последней статьи» и «свежести»
    id_date = {}
    di = Path(LANG_DIR) / DEFAULT_LANG / "articles-index.json"
    if di.exists():
        for a in json.loads(di.read_text(encoding="utf-8")):
            id_date[a["id"]] = a["date"]
    newest = max(id_date.values()) if id_date else ""

    def last_date_of(d):
        ds = [id_date.get(i, "") for i in d.get("articles", [])]
        ds = [x for x in ds if x]
        return max(ds) if ds else ""

    def is_recent(ld):
        if not ld or not newest: return False
        try:
            return (datetime.strptime(newest, "%Y-%m-%d") - datetime.strptime(ld, "%Y-%m-%d")).days <= 30
        except ValueError:
            return False

    last_label = {"ru": "последняя", "en": "latest", "zh": "最新", "fr": "dernière",
                  "ar": "الأحدث"}.get(DEFAULT_LANG, "latest")
    authors = sorted([{"name": n, "count": d.get("article_count", 0), "last": last_date_of(d)}
                      for n, d in graph.items()], key=lambda x: -x["count"])
    cloud_html = ""
    for a in authors:
        size = "size-s" if a["count"] <= 2 else ("size-m" if a["count"] <= 5 else "size-l")
        rec = " recent" if is_recent(a["last"]) else ""
        slug = author_slug(a["name"])
        cloud_html += (f'<a href="/{LANG_DIR}/{DEFAULT_LANG}/authors/{slug}.html" '
                       f'class="author-item {size}{rec}" data-author="{attr_safe(a["name"])}">'
                       f'<span class="check"></span>{a["name"]}<span class="au-count">{a["count"]}</span></a>\n')
    (Path(LANG_DIR) / DEFAULT_LANG / "authors" / "index.html").write_text(tpl_cloud.substitute(
        lang=DEFAULT_LANG, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG,
        authors_title=safe(loc["title"]), authors_subtitle=safe(loc["subtitle"]),
        search_placeholder=safe(loc["find"]), selected_html="", authors_cloud_html=cloud_html,
        footer_text=safe(loc["footer"])
    ), encoding="utf-8")
    for author_name, data in graph.items():
        slug = author_slug(author_name)
        articles_html = ""
        for lc in LANGUAGES:
            ip = Path(LANG_DIR) / lc / "articles-index.json"
            if not ip.exists(): continue
            for a in json.loads(ip.read_text(encoding="utf-8")):
                if a["id"] in data.get("articles", []):
                    articles_html += f"""<div class="article-card"><div class="card-content">
                        <h3><a href="{a['url']}">{a['title']}</a></h3>
                        <div class="oneliner">{a.get('description', a.get('oneliner', ''))}</div>
                        <div class="meta">arXiv:{a['id']} · {a['date']}</div></div></div>"""
        coauthors_html = "".join(
            f'<a href="/{LANG_DIR}/{DEFAULT_LANG}/authors/{author_slug(ca)}.html" data-author="{attr_safe(ca)}">{ca}</a>'
            for ca in data.get("coauthors", [])[:15]
        )
        (Path(LANG_DIR) / DEFAULT_LANG / "authors" / f"{slug}.html").write_text(tpl_page.substitute(
            lang=DEFAULT_LANG, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG,
            author_slug=attr_safe(slug),
            author_name=author_name, author_name_attr=attr_safe(author_name),
            article_count=len(data.get("articles", [])),
            articles_label=safe(loc["articles"]), coauthors_word=safe(loc["coauthors_word"]),
            last_seen=f'{last_label}: {last_date_of(data)}' if last_date_of(data) else '',
            coauthor_count=len(data.get("coauthors", [])), coauthors_label=safe(loc["coauthors"]),
            coauthors_html=coauthors_html, search_placeholder=safe(loc["search"]),
            search_hint=safe(loc["hint"]),
            articles_list_html=articles_html or f'<p>{safe(loc["no_articles"])}</p>',
            footer_text=safe(loc["footer"])
        ), encoding="utf-8")
    print(f"  👥 Authors updated ({len(graph)} authors)")


# ── Main ──
def _archive_calendar(counts, lang):
    """Календарь-навигация над архивом: по месяцу-сетке (год→месяц→день), новые сверху.
    Дни со статьями подсвечены и ведут якорем на секцию дня; горизонт — годы, поэтому
    рисуем только те месяцы, где что-то есть."""
    if not counts: return ""
    months = MONTH_NAMES.get(lang, MONTH_NAMES["en"])
    wds = WEEKDAY_ABBR.get(lang, WEEKDAY_ABBR["en"])
    present = sorted({d[:7] for d in counts}, reverse=True)  # 'YYYY-MM'
    cal = calendar.Calendar(firstweekday=0)  # понедельник первый
    blocks = ""
    for ym in present:
        y, m = int(ym[:4]), int(ym[5:7])
        head = "".join(f'<span class="cal-wd">{w}</span>' for w in wds)
        cells = ""
        for week in cal.monthdayscalendar(y, m):
            for dnum in week:
                if dnum == 0:
                    cells += '<span class="cal-cell cal-blank"></span>'
                    continue
                ds = f"{y:04d}-{m:02d}-{dnum:02d}"
                n = counts.get(ds, 0)
                if n:
                    cells += (f'<a class="cal-cell cal-has" href="#{ds}" title="{n}">'
                              f'{dnum}<i class="cal-dot">{n}</i></a>')
                else:
                    cells += f'<span class="cal-cell cal-off">{dnum}</span>'
        blocks += (f'<div class="cal-month"><div class="cal-mtitle">{months[m - 1]} {y}</div>'
                   f'<div class="cal-grid">{head}{cells}</div></div>')
    return f'<div class="archive-calendar">{blocks}</div>'


def generate_archive_page(lang):
    """Страница /archive: календарь-навигация + статьи, сгруппированные по дням
    (crawlable ссылки для SEO)."""
    idx = Path(LANG_DIR) / lang / "articles-index.json"
    if not idx.exists(): return
    items = json.loads(idx.read_text(encoding="utf-8"))
    by_day = {}
    for a in sorted(items, key=lambda x: x["date"], reverse=True):
        by_day.setdefault(a["date"], []).append(a)
    loc = {"ru": {"title": "Архив", "footer": "наука простыми словами", "art": "статей"},
           "en": {"title": "Archive", "footer": "science made simple", "art": "articles"},
           "zh": {"title": "存档", "footer": "让科学变简单", "art": "篇"},
           "fr": {"title": "Archives", "footer": "la science simplifiée", "art": "articles"},
           "ar": {"title": "الأرشيف", "footer": "العلم ببساطة", "art": "مقالات"}}.get(lang,
           {"title": "Archive", "footer": "science made simple", "art": "articles"})
    calendar_html = _archive_calendar({d: len(a) for d, a in by_day.items()}, lang)
    days_html = ""
    for day, arts in by_day.items():
        links = "".join(f'<a href="{a["url"]}" class="related-item">{a["title"]}</a>' for a in arts)
        days_html += (f'<div class="feed-day" id="{day}">{day} · {len(arts)} {loc["art"]}</div>{links}')
    html = f'''<!DOCTYPE html><html lang="{lang}"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{loc["title"]} — bridge42worlds</title>
<link rel="stylesheet" href="/css/style.css?v=15">
<script data-goatcounter="https://{GOATCOUNTER}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script></head><body>
<div class="top-bar"><a href="/{LANG_DIR}/{lang}/index.html" class="logo">bridge42worlds</a>
<div class="header-right"><div class="nav-links">
<a href="/{LANG_DIR}/{lang}/index.html">main</a><a href="/{LANG_DIR}/{lang}/tags/">tags</a>
<a href="/{LANG_DIR}/{DEFAULT_LANG}/authors/">authors</a><a href="/{LANG_DIR}/{lang}/scientists/">scientists</a>
<a href="/{LANG_DIR}/{lang}/archive/" class="active">archive</a><a href="/{LANG_DIR}/{lang}/about.html">about</a>
</div></div></div>
<div class="langs" id="langs-bar"></div>
<h1>🗓️ {loc["title"]}</h1>
{calendar_html}
{days_html}
<footer><p>bridge42worlds — {loc["footer"]}</p></footer>
<script src="/js/search.js?v=15"></script></body></html>'''
    (Path(LANG_DIR) / lang / "archive" / "index.html").write_text(html, encoding="utf-8")


def generate_status_page():
    """status.html — дашборд состояния системы (статьи по языкам/дням, покрытие переводами, счётчики)."""
    total = 0
    langs_have = {l: 0 for l in LANGUAGES}
    by_day = {}
    incomplete = 0
    for data, folder in iter_articles():
        total += 1
        by_day[data.get("date", "?")] = by_day.get(data.get("date", "?"), 0) + 1
        for l in LANGUAGES:
            if data.get("advanced", {}).get(l):
                langs_have[l] += 1
    archive = Path(LANG_DIR) / DEFAULT_LANG / "archive"
    if archive.exists():
        for day in archive.iterdir():
            if not day.is_dir(): continue
            for f in day.iterdir():
                if f.is_dir() and not (f / "data.json").exists() and (
                        (f / "api").exists() or any(f.glob("*.jpg"))):
                    incomplete += 1
    tags_n = len(json.loads(Path("data/tags-graph.json").read_text(encoding="utf-8")).get("graph", {})) \
        if Path("data/tags-graph.json").exists() else 0
    sci_n = len(valid_scientist_ids())
    authors_n = len(json.loads(Path("data/authors-graph.json").read_text(encoding="utf-8"))) \
        if Path("data/authors-graph.json").exists() else 0

    def bar(v, mx, color):
        w = int(100 * v / mx) if mx else 0
        return f'<div style="background:#eee;border-radius:4px;overflow:hidden;height:14px"><div style="width:{w}%;height:100%;background:{color}"></div></div>'

    cov_rows = ""
    for l in LANGUAGES:
        pct = round(100 * langs_have[l] / total) if total else 0
        cov_rows += (f'<tr><td style="padding:4px 10px">{l}</td>'
                     f'<td style="padding:4px 10px;width:220px">{bar(langs_have[l], total, "#4a7c9b")}</td>'
                     f'<td style="padding:4px 10px;color:#888">{langs_have[l]}/{total} · {pct}%</td></tr>')
    max_day = max(by_day.values()) if by_day else 1
    day_rows = ""
    for d in sorted(by_day, reverse=True)[:30]:
        day_rows += (f'<tr><td style="padding:3px 10px;color:#888">{d}</td>'
                     f'<td style="padding:3px 10px;width:220px">{bar(by_day[d], max_day, "#2e7d32")}</td>'
                     f'<td style="padding:3px 10px">{by_day[d]}</td></tr>')
    warn = f'<p style="color:#b31b1b">⚠️ Недопечённых папок: {incomplete}</p>' if incomplete else '<p style="color:#2e7d32">✓ Недопечённых нет</p>'
    html = f'''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Status — bridge42worlds</title>
<style>body{{font-family:system-ui,Arial,sans-serif;max-width:760px;margin:0 auto;padding:30px 18px;color:#2c2c2c}}
h1{{font-size:22px}}h2{{font-size:15px;margin:24px 0 8px;color:#555}}
.cards{{display:flex;gap:12px;flex-wrap:wrap;margin:14px 0}}
.card{{flex:1;min-width:120px;background:#f6f6f6;border-radius:10px;padding:12px 14px}}
.card b{{font-size:24px;display:block}}.card span{{color:#888;font-size:13px}}
table{{border-collapse:collapse;font-size:13px;width:100%}}</style></head><body>
<h1>📊 Состояние системы</h1>
<div class="cards">
<div class="card"><b>{total}</b><span>статей</span></div>
<div class="card"><b>{authors_n}</b><span>авторов</span></div>
<div class="card"><b>{sci_n}</b><span>учёных</span></div>
<div class="card"><b>{tags_n}</b><span>тегов</span></div>
<div class="card"><b>{len(LANGUAGES)}</b><span>языков</span></div>
</div>
<h2>Покрытие переводами</h2><table>{cov_rows}</table>
<h2>Статьи по дням (последние 30)</h2><table>{day_rows}</table>
<h2>Целостность</h2>{warn}
</body></html>'''
    Path("status.html").write_text(html, encoding="utf-8")
    print(f"  📊 status.html ({total} статей, {authors_n} авторов)")


def generate_sitemaps():
    """sitemap-{lang}.xml (статьи+теги+учёные+about+index) + индекс sitemap.xml в корне."""
    def urlset(urls):
        body = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
        return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>'

    tags_graph = json.loads(Path("data/tags-graph.json").read_text(encoding="utf-8")).get("graph", {}) \
        if Path("data/tags-graph.json").exists() else {}
    made = []
    for lang in LANGUAGES:
        urls = [f"{SITE_URL}/{LANG_DIR}/{lang}/index.html",
                f"{SITE_URL}/{LANG_DIR}/{lang}/about.html",
                f"{SITE_URL}/{LANG_DIR}/{lang}/archive/index.html",
                f"{SITE_URL}/{LANG_DIR}/{lang}/tags/index.html",
                f"{SITE_URL}/{LANG_DIR}/{lang}/scientists/index.html"]
        idx = Path(LANG_DIR) / lang / "articles-index.json"
        ids_seen = set()
        if idx.exists():
            for a in json.loads(idx.read_text(encoding="utf-8")):
                if a["id"] in ids_seen: continue
                ids_seen.add(a["id"])
                for vf in VERSION_FILES.values():
                    urls.append(f"{SITE_URL}/{LANG_DIR}/{lang}/archive/{a['date']}/{a['id']}/{vf}")
        for tid in tags_graph:
            urls.append(f"{SITE_URL}/{LANG_DIR}/{lang}/tags/{tid}.html")
        fn = f"sitemap-{lang}.xml"
        Path(fn).write_text(urlset(urls), encoding="utf-8")
        made.append(fn)
    index = ('<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
             + "".join(f"<sitemap><loc>{SITE_URL}/{f}</loc></sitemap>" for f in made) + "</sitemapindex>")
    Path("sitemap.xml").write_text(index, encoding="utf-8")
    print(f"  🗺️ Sitemaps: {', '.join(made)} + sitemap.xml")


def regenerate_all_html():
    """Пересобирает HTML всех статей из data.json (без API). Идёт по источнику правды,
    а не по индексам — устойчиво к их повреждению."""
    print("🔄 Regenerate HTML only (no API)")
    for lang in LANGUAGES: ensure_lang_structure(lang)
    count = 0
    for data, folder in iter_articles():
        date_str = data.get("date", folder.parent.name)
        # только контентные картинки 0.jpg..N-1.jpg (ai.jpg — обложка, не в мозаике)
        images = sorted([p for p in folder.glob("*.jpg") if p.stem.isdigit()],
                        key=lambda p: int(p.stem))
        captions = data.get("captions") or []
        article_obj = {
            "id": data["id"],
            "title": data.get("original_title", ""),
            "authors": data.get("authors", []),
            "license_url": data.get("license", ""),
            "license_name": data.get("license_name", "CC BY"),
            "categories": data.get("categories", []),
            "primary_category": data.get("primary_category", ""),
        }
        for version in VERSIONS:
            for lang in LANGUAGES:
                scipop = version_scipop(data, version, lang)
                if not scipop: continue
                html = gen_article_html(scipop, article_obj, date_str,
                                        [str(p) for p in images], lang, version, captions)
                out = Path(LANG_DIR) / lang / "archive" / date_str / data["id"] / VERSION_FILES[version]
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(html, encoding="utf-8")
                count += 1
    for lang in LANGUAGES:
        update_all_tags(lang)
        update_all_scientists(lang)
        update_all_laws(lang)
        generate_archive_page(lang)
    update_all_authors()
    generate_sitemaps()
    generate_status_page()
    print(f"  ✅ Regenerated {count} HTML pages + tags/scientists/authors/laws")


def load_generation_inputs():
    tags_input = json.loads(Path(f"lang/{DEFAULT_LANG}/data/tags-list.json").read_text(encoding="utf-8"))
    return {
        "tags_input": tags_input,
        "valid_tags": set(t["en"] for t in tags_input),
        "scientists_keys": list(
            json.loads(Path(f"lang/{DEFAULT_LANG}/data/scientists.json").read_text(encoding="utf-8")).keys()),
    }


def build_article(a, date_str, inputs, force=False):
    """Фаза A: arXiv + PDF + все вызовы DeepSeek. Пишет только в папку статьи (гонок нет).
    Возвращает подготовленный dict либо None (пропущено/ошибка)."""
    article_folder = Path(LANG_DIR) / DEFAULT_LANG / "archive" / date_str / a["id"]
    if not force and (article_folder / "data.json").exists():
        print(f"  ⏭️ {a['id']} — уже есть, пропускаю (--force чтобы пересоздать)")
        return None
    try:
        oai_xml = get_license(a["id"])
        allowed, lic_url = is_allowed_license(oai_xml)
        if not allowed:
            print(f"  ⏭️ {a['id']} — license: {lic_url or 'none'}")
            return None
        atom_xml = requests.get(f"http://es.arxiv.org/api/query?id_list={a['id']}", timeout=30).text
        a["license_url"], a["license_name"] = lic_url, ("CC BY 4.0" if "by/4.0" in lic_url else "CC BY")
        pdf = download_pdf(a["id"])
        text, imgs = parse_pdf(pdf)
        captions = extract_captions(text)  # подписи ищем в полном тексте (в списке литературы их нет)
        body, refs = split_references(text)
        a["cited_arxiv"] = extract_ref_arxiv_ids(refs)  # на будущее: связь с релевантными работами
        text = re.sub(r'https?://\S+', '', body)  # тело без литературы и URL → экономия ~20% токенов в промте
        article_folder.mkdir(parents=True, exist_ok=True)
        if refs:
            (article_folder / "references.txt").write_text(refs, encoding="utf-8")
        (article_folder / "arxiv-atom.xml").write_text(atom_xml, encoding="utf-8")
        (article_folder / "arxiv-oai.xml").write_text(oai_xml or "", encoding="utf-8")
        (article_folder / "original.pdf").write_bytes(pdf.read_bytes())
        images = save_images(imgs, a["id"], article_folder)
        captions = captions[:len(images)]  # выравниваем по числу сохранённых картинок
        if not text: text = a["summary"]
        scipop_adv = generate_advanced(a, text, inputs["tags_input"], inputs["scientists_keys"])
        if not scipop_adv: return None
        (article_folder / "api").mkdir(exist_ok=True)
        (article_folder / "api" / "advanced-ru.json").write_text(
            json.dumps(scipop_adv, ensure_ascii=False, indent=2), encoding="utf-8")
        scipop_adv = validate_tags(scipop_adv, inputs["valid_tags"])
        scipop_simple = generate_simple(scipop_adv)
        (article_folder / "api" / "simple-ru.json").write_text(
            json.dumps(scipop_simple, ensure_ascii=False, indent=2), encoding="utf-8")
        scipop_pop = generate_popular(scipop_simple)
        (article_folder / "api" / "popular-ru.json").write_text(
            json.dumps(scipop_pop, ensure_ascii=False, indent=2), encoding="utf-8")

        # Промпт для AI-обложки (один на статью, вне языка) + сама картинка (если есть ключ)
        img_prompt = generate_image_prompt(scipop_adv)
        if img_prompt:
            (article_folder / "api" / "image-prompt.txt").write_text(img_prompt, encoding="utf-8")
            scipop_adv["image_prompt"] = img_prompt
            generate_image(img_prompt, article_folder / "ai.jpg")

        versions_ru = {"popular": scipop_pop, "simple": scipop_simple, "advanced": scipop_adv}
        # Переводы: каждую версию на каждый целевой язык — параллельно.
        translations = {v: {} for v in VERSIONS}
        targets = [l for l in LANGUAGES if l != DEFAULT_LANG]
        if targets:
            with ThreadPoolExecutor(max_workers=min(8, len(targets) * len(VERSIONS))) as tex:
                futures = {}
                for l in targets:
                    for v in VERSIONS:
                        futures[tex.submit(translate_scipop, versions_ru[v], l)] = (v, l)
                for fut, (v, l) in futures.items():
                    try:
                        res = fut.result()
                    except Exception as e:
                        print(f"    ⚠️ {a['id']} перевод {v}/{l} не удался ({e}) — оставляю оригинал")
                        res = versions_ru[v]
                    translations[v][l] = res

        save_data_json(versions_ru, a, date_str, article_folder, translations, captions)
        return {"article": a, "versions": versions_ru, "translations": translations,
                "images": images, "captions": captions}
    except Exception as e:
        print(f"  ❌ {a['id']}: {e}")
        traceback.print_exc()
        return None


def write_article_pages(item, date_str):
    """Фаза B (последовательно): HTML по языкам×версиям + индексы/графы (read-modify-write)."""
    a, images = item["article"], item["images"]
    versions_ru, translations = item["versions"], item["translations"]
    captions = item.get("captions") or []
    for lang in LANGUAGES:
        lang_folder = Path(LANG_DIR) / lang / "archive" / date_str / a["id"]
        lang_folder.mkdir(parents=True, exist_ok=True)
        for v in VERSIONS:
            scipop = versions_ru[v] if lang == DEFAULT_LANG else translations.get(v, {}).get(lang, versions_ru[v])
            (lang_folder / VERSION_FILES[v]).write_text(
                gen_article_html(scipop, a, date_str, images, lang, v, captions), encoding="utf-8")
            update_index(scipop, a, date_str, lang, v)
    update_authors_graph(a)
    update_tag_counts(versions_ru["advanced"])
    print(f"  ✅ {a['id']} done")


def process_day(date_str, force=False, refresh_aggregates=True):
    print(f"\n{'=' * 60}\n📅 {date_str}\n{'=' * 60}")
    for lang in LANGUAGES: ensure_lang_structure(lang)

    articles = fetch_arxiv(date_str)
    if not articles: return 0
    best = select_best(articles, date_str)
    inputs = load_generation_inputs()

    print(f"  🚀 Обработка {len(best)} статей в {ARTICLE_WORKERS} потока...")
    with ThreadPoolExecutor(max_workers=ARTICLE_WORKERS) as ex:
        prepared = [r for r in ex.map(lambda a: build_article(a, date_str, inputs, force), best) if r]

    for item in prepared:
        write_article_pages(item, date_str)

    if refresh_aggregates and prepared:
        for lang in LANGUAGES:
            update_all_tags(lang)
            update_all_scientists(lang)
            generate_archive_page(lang)
        update_all_authors()
        generate_sitemaps()
        generate_status_page()
    print(f"\n✅ {date_str}: {len(prepared)} articles generated")
    return len(prepared)


# ── Обслуживание: reindex / графы / удаление / целостность ──
def _index_entry(scipop, data, date_str, lang, version):
    url = f"/{LANG_DIR}/{lang}/archive/{date_str}/{data['id']}/{VERSION_FILES[version]}"
    return {
        "id": data["id"], "version": version,
        "title": scipop.get("title", data.get("original_title", "")),
        "oneliner": scipop.get("oneliner", "")[:300],
        "description": scipop.get("description", "")[:300],
        "authors": data.get("authors", [])[:5], "date": date_str,
        "tags": [scipop.get("main_tag", "")] + scipop.get("extra_tags", []),
        "scientists": scipop.get("scientists", []), "url": url,
        "reading": reading_minutes(scipop),
        "categories": data.get("categories", []),
        "primary_category": data.get("primary_category", ""),
    }


def iter_articles():
    """Идёт по всем data.json в архиве языка по умолчанию (источник правды)."""
    archive = Path(LANG_DIR) / DEFAULT_LANG / "archive"
    if not archive.exists(): return
    for data_path in sorted(archive.glob("*/*/data.json")):
        try:
            yield json.loads(data_path.read_text(encoding="utf-8")), data_path.parent
        except json.JSONDecodeError:
            print(f"  ⚠️ битый data.json: {data_path}")


def rebuild_indexes():
    """Полная пересборка articles-index*.json из data.json (чинит дрейф/висящие записи).
    popular с откатом на simple — чтобы лента по умолчанию не пустовала для старых статей."""
    buckets = {lang: {v: [] for v in VERSIONS} for lang in LANGUAGES}
    for data, _ in iter_articles():
        date_str = data.get("date", "")
        for version in VERSIONS:
            for lang in LANGUAGES:
                scipop = version_scipop(data, version, lang)
                if scipop:
                    buckets[lang][version].append(_index_entry(scipop, data, date_str, lang, version))
    for lang in LANGUAGES:
        base = Path(LANG_DIR) / lang
        base.mkdir(parents=True, exist_ok=True)
        for version in VERSIONS:
            (base / VERSION_INDEX[version]).write_text(
                json.dumps(buckets[lang][version], ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(b["popular"]) for b in buckets.values())
    print(f"  ✅ Индексы пересобраны ({total} записей popular по всем языкам)")


def rebuild_author_graph():
    """authors-graph.json полностью выводится из статей — пересобираем начисто."""
    graph = {}
    for data, _ in iter_articles():
        authors = data.get("authors", [])
        for a in authors:
            g = graph.setdefault(a, {"articles": [], "coauthors": [], "article_count": 0})
            if data["id"] not in g["articles"]:
                g["articles"].append(data["id"])
            for ca in authors:
                if ca != a and ca not in g["coauthors"]:
                    g["coauthors"].append(ca)
    for a, g in graph.items():
        g["article_count"] = len(g["articles"])
    Path("data/authors-graph.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ Граф авторов пересобран ({len(graph)} авторов)")


def recompute_tag_counts():
    """Пересчитывает article_count в tags-graph.json из статей (article_count дрейфует)."""
    gp = Path("data/tags-graph.json")
    if not gp.exists(): return
    graph = json.loads(gp.read_text(encoding="utf-8"))
    for t in graph.get("graph", {}).values():
        t["article_count"] = 0
    for data, _ in iter_articles():
        for t in [data.get("main_tag", "")] + data.get("tags", []):
            node = graph.get("graph", {}).get(t)
            if node:
                node["article_count"] = node.get("article_count", 0) + 1
    gp.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    print("  ✅ Счётчики тегов пересчитаны")


def find_article_dates(aid):
    """Все даты, под которыми лежит статья с данным id (обычно одна)."""
    dates = set()
    for lang in LANGUAGES:
        for folder in (Path(LANG_DIR) / lang / "archive").glob(f"*/{aid}"):
            dates.add(folder.parent.name)
    return sorted(dates)


def delete_article(aid, rebuild=True):
    """Удаляет статью (папки во всех языках: контент, картинки, PDF) и чистит индексы/графы."""
    import shutil
    removed = 0
    for lang in LANGUAGES:
        for folder in (Path(LANG_DIR) / lang / "archive").glob(f"*/{aid}"):
            shutil.rmtree(folder)
            removed += 1
            print(f"  🗑️ удалено {folder}")
    if removed and rebuild:
        rebuild_indexes()
        rebuild_author_graph()
        recompute_tag_counts()
        for lang in LANGUAGES:
            update_all_tags(lang)
            update_all_scientists(lang)
        update_all_authors()
    if not removed:
        print(f"  ⚠️ статья {aid} не найдена")
    return removed


def fetch_one_arxiv(aid):
    """Метаданные одной статьи по arXiv id."""
    r = requests.get(f"http://es.arxiv.org/api/query?id_list={aid}", timeout=30)
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        return None
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    e = root.find("atom:entry", ns)
    if e is None: return None
    cats = list(dict.fromkeys(
        c.get("term") for c in e.findall("atom:category", ns) if c.get("term")))
    primary = e.find("arxiv:primary_category", ns)
    primary_cat = primary.get("term", "") if primary is not None else (cats[0] if cats else "")
    return {
        "id": aid,
        "title": (e.find("atom:title", ns).text or "").strip().replace("\n", " "),
        "summary": (e.find("atom:summary", ns).text or "").strip().replace("\n", " "),
        "authors": [x.find("atom:name", ns).text for x in e.findall("atom:author", ns)],
        "published": (e.find("atom:published", ns).text or ""),
        "categories": cats,
        "primary_category": primary_cat,
    }


def regenerate_article(aid, force=True):
    """Пересоздаёт одну статью с нуля (удаляет старое, генерит заново, чинит агрегаты)."""
    dates = find_article_dates(aid)
    date_str = dates[0] if dates else None
    delete_article(aid, rebuild=False)
    a = fetch_one_arxiv(aid)
    if not a:
        print(f"  ❌ не удалось получить метаданные {aid} с arXiv")
        return False
    if not date_str:
        date_str = (a.get("published", "")[:10]) or TARGET_DATE
    for lang in LANGUAGES: ensure_lang_structure(lang)
    item = build_article(a, date_str, load_generation_inputs(), force=True)
    if not item:
        print(f"  ❌ {aid}: генерация не удалась")
        return False
    write_article_pages(item, date_str)
    rebuild_indexes()
    rebuild_author_graph()
    recompute_tag_counts()
    for lang in LANGUAGES:
        update_all_tags(lang)
        update_all_scientists(lang)
    update_all_authors()
    print(f"  ✅ {aid} пересоздана ({date_str})")
    return True


def _refresh_all_aggregates():
    for lang in LANGUAGES:
        update_all_tags(lang)
        update_all_scientists(lang)
    update_all_authors()


def generate_ids(id_list, force=False):
    """Генерирует конкретные статьи по списку arXiv id. Дата берётся из метаданных
    статьи (published), поэтому статьи корректно ложатся в свои дни."""
    for lang in LANGUAGES: ensure_lang_structure(lang)
    inputs = load_generation_inputs()

    def prep(aid):
        a = fetch_one_arxiv(aid)
        if not a:
            print(f"  ❌ {aid}: нет метаданных на arXiv")
            return None
        date_str = (a.get("published", "")[:10]) or TARGET_DATE
        item = build_article(a, date_str, inputs, force=force)
        if item: item["date_str"] = date_str
        return item

    print(f"  🚀 Генерация {len(id_list)} статей по id в {ARTICLE_WORKERS} потока...")
    with ThreadPoolExecutor(max_workers=ARTICLE_WORKERS) as ex:
        prepared = [r for r in ex.map(prep, id_list) if r]
    for item in prepared:
        write_article_pages(item, item["date_str"])
    if prepared:
        _refresh_all_aggregates()
    print(f"\n✅ Сгенерировано по id: {len(prepared)} из {len(id_list)}")
    return len(prepared)


def search_arxiv_author(name, from_date=None, to_date=None, max_results=200):
    """Ищет статьи автора на arXiv (по строке имени). Возвращает список
    {id, title, published}. Имя-строка → возможны однофамильцы, поэтому режим
    предполагает превью-подтверждение перед генерацией."""
    q = f'au:"{name}"'
    if from_date and to_date:
        f = from_date.replace("-", "") + "0000"
        t = to_date.replace("-", "") + "2359"
        q += f" AND submittedDate:[{f} TO {t}]"
    r = requests.get("http://es.arxiv.org/api/query", params={
        "search_query": q, "start": 0, "max_results": max_results,
        "sortBy": "submittedDate", "sortOrder": "descending"}, timeout=30)
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        return []
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    out = []
    for e in root.findall("atom:entry", ns):
        idnode = e.find("atom:id", ns)
        if idnode is None: continue
        out.append({
            "id": idnode.text.split("/abs/")[-1],
            "title": (e.find("atom:title", ns).text or "").strip().replace("\n", " "),
            "published": (e.find("atom:published", ns).text or "")[:10],
        })
    return out


def backfill_images(force=False):
    """Бэкфилл AI-обложек: генерит промпт (если нет) и картинку (если есть ключ DeepInfra)."""
    has_key = bool(os.environ.get("DEEPINFRA_API_KEY", ""))
    print(f"  🖼️ Бэкфилл обложек (картинки: {'да' if has_key else 'НЕТ ключа — только промпты'})")
    n_prompt, n_img = 0, 0
    for data, folder in iter_articles():
        adv = data.get("advanced", {}).get(DEFAULT_LANG, {})
        prompt = data.get("image_prompt") or adv.get("image_prompt", "")
        pfile = folder / "api" / "image-prompt.txt"
        if not prompt and pfile.exists():
            prompt = pfile.read_text(encoding="utf-8").strip()
        if not prompt or force:
            prompt = generate_image_prompt(adv) or prompt
            if prompt:
                (folder / "api").mkdir(exist_ok=True)
                pfile.write_text(prompt, encoding="utf-8")
                data["image_prompt"] = prompt
                (folder / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                n_prompt += 1
        img = folder / "ai.jpg"
        if has_key and prompt and (force or not img.exists()):
            if generate_image(prompt, img):
                n_img += 1
        print(f"    · {data['id']} (промпт={'ok' if prompt else '—'})")
    print(f"  ✅ Промптов: {n_prompt}, картинок: {n_img}")


def backfill_language(new_lang):
    """Переводит все существующие статьи на новый язык и дописывает перевод в data.json.
    Возобновляемо: статьи, где перевод уже есть, пропускаются."""
    if new_lang == DEFAULT_LANG:
        print(f"  ⏭️ {new_lang} — это язык по умолчанию, перевод не нужен")
        return 0
    count = 0
    for data, folder in iter_articles():
        changed = False
        for version in VERSIONS:
            vdata = data.get(version, {})
            if vdata.get(new_lang):
                continue
            src = vdata.get(DEFAULT_LANG)
            if not src:
                continue
            vdata[new_lang] = translate_scipop(src, new_lang)
            data[version] = vdata
            changed = True
        if changed:
            (folder / "data.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            count += 1
            print(f"  🌐 {data['id']} → {new_lang} ({count})")
    print(f"  ✅ Переведено статей на {new_lang}: {count}")
    return count


def integrity_check(fix=False):
    """Проверяет: data.json парсится, HTML есть по всем языкам, переводы на месте, индексы согласованы."""
    problems = []
    seen_ids = set()
    for data, folder in iter_articles():
        aid = data.get("id", folder.name)
        date_str = data.get("date", folder.parent.name)
        seen_ids.add(aid)
        for version in VERSIONS:
            fname = VERSION_FILES[version]
            vdata = data.get(version, {})
            for lang in LANGUAGES:
                page = Path(LANG_DIR) / lang / "archive" / date_str / aid / fname
                if not page.exists() or page.stat().st_size == 0:
                    problems.append(("missing_html", aid, f"{lang}/{fname}"))
                # перевод спрашиваем только если для версии есть исходник (иначе это ожидаемый откат)
                if vdata.get(DEFAULT_LANG) and lang != DEFAULT_LANG and lang not in vdata:
                    problems.append(("missing_translation", aid, f"{version}/{lang}"))

    # Недопечённые папки: контент есть (картинки/api/pdf), но data.json нет —
    # значит фаза A прошла, а фаза B (или сам data.json) не записалась.
    archive = Path(LANG_DIR) / DEFAULT_LANG / "archive"
    if archive.exists():
        for day in archive.iterdir():
            if not day.is_dir(): continue
            for folder in day.iterdir():
                if not folder.is_dir() or (folder / "data.json").exists():
                    continue
                has_content = (folder / "api").exists() or any(folder.glob("*.jpg")) or any(folder.glob("*.pdf"))
                if has_content:
                    problems.append(("incomplete", folder.name, f"{day.name}/{folder.name} (нет data.json)"))

    # Согласованность индексов: запись в индексе без data.json
    for lang in LANGUAGES:
        for f in VERSION_INDEX.values():
            ip = Path(LANG_DIR) / lang / f
            if not ip.exists(): continue
            for e in json.loads(ip.read_text(encoding="utf-8")):
                if e.get("id") not in seen_ids:
                    problems.append(("orphan_index", e.get("id"), f"{lang}/{f}"))

    by_type = {}
    for kind, aid, detail in problems:
        by_type.setdefault(kind, []).append((aid, detail))
    if not problems:
        print(f"  ✅ Целостность: проблем не найдено ({len(seen_ids)} статей)")
    else:
        print(f"  ⚠️ Найдено проблем: {len(problems)} (статей проверено: {len(seen_ids)})")
        for kind, items in by_type.items():
            print(f"    • {kind}: {len(items)}")
            for aid, detail in items[:10]:
                print(f"        {aid} — {detail}")
            if len(items) > 10:
                print(f"        … и ещё {len(items) - 10}")

    if fix and problems:
        broken_html = {aid for kind, aid, _ in problems if kind in ("missing_html", "orphan_index")}
        if broken_html or any(k == "orphan_index" for k, _, _ in problems):
            print("  🔧 fix: пересборка HTML и индексов...")
            regenerate_all_html()
            rebuild_indexes()
        missing_tr = [aid for kind, aid, _ in problems if kind == "missing_translation"]
        if missing_tr:
            print(f"  ⚠️ {len(set(missing_tr))} статей без перевода — нужен API: "
                  f"перегенерируйте их (run.py regen <id>) или запустите daily --force")
        incomplete = sorted({aid for kind, aid, _ in problems if kind == "incomplete"})
        if incomplete:
            print(f"  ⚠️ {len(incomplete)} недопечённых статей (нет data.json) — нужен API: "
                  f"run.py regen <id>. Список: {', '.join(incomplete[:20])}")
    return problems


def regenerate_all_html_and_reindex():
    regenerate_all_html()
    rebuild_indexes()


if __name__ == "__main__":
    if not Path("templates/article.html").exists():
        print("❌ templates/article.html not found");
        sys.exit(1)
    if HTML_ONLY:
        for lang in LANGUAGES: ensure_lang_structure(lang)
        regenerate_all_html()
    else:
        process_day(TARGET_DATE)
    print("\n🎉 Done!")