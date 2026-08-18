#!/usr/bin/env python3
"""
Bridge For Two Worlds — генератор научно-популярных статей из arXiv.
arXiv astro-ph → DeepSeek → HTML + data.json + API-ответы
"""

import os, sys, json, time, re, random, calendar, requests, traceback, hashlib, shutil, html, xml.etree.ElementTree as ET
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
        _stream.reconfigure(encoding="utf-8", line_buffering=True)
    except (AttributeError, ValueError):
        pass

load_dotenv()

# Слои вынесены в модули; generate.py — фасад (рендер/индексы/пайплайн + реэкспорт).
from common import CONFIG as config, DEEPSEEK_API_KEY, LANGUAGES, DEFAULT_LANG, LANG_DIR, as_list, deepseek_peak_status, write_json_atomic  # noqa: F401
import common               # common.job() — метка «к какой статье относится вызов»
from gen_base import *    # noqa: F401,F403 — константы и базовые хелперы
from gen_arxiv import *   # noqa: F401,F403 — arXiv/PDF-слой
from gen_arxiv import _get_with_retry  # leading underscore не попадает в import *
import gen_arxiv          # список отказов читаем через модуль, а не через копию имени

if not DEEPSEEK_API_KEY:
    print("⚠️  DEEPSEEK_API_KEY не задан — доступны только офлайн-операции (html/reindex/check/delete)")

print(f"🚀 {SITE_NAME} generator")
print(f"   Languages: {LANGUAGES}")

_ASSET_VER = None

# Иконка «граф знаний» — инлайновый SVG-глиф (3 узла + рёбра, currentColor → любая тема)
# вместо эмодзи-паутины 🕸. Один источник для всех мест (label графа на статье + заголовки).
GRAPH_ICO = ('<svg class="ico-graph" viewBox="0 0 25 25" aria-hidden="true">'
             '<g fill="none" stroke="currentColor" stroke-width="1.7">'
             '<line x1="4.5" y1="7" x2="20.5" y2="5"/><line x1="5.5" y1="9" x2="12" y2="20"/>'
             '<line x1="20" y1="7" x2="13.5" y2="20"/></g>'
             '<g fill="currentColor"><circle cx="4.5" cy="7" r="2.9"/>'
             '<circle cx="20.5" cy="5" r="2.9"/><circle cx="12.5" cy="21" r="2.9"/></g></svg>')

# Иконка «настройки» — три ползунка, а не шестерёнка: шестерёнка в интерфейсе обычно
# означает настройки ПРИЛОЖЕНИЯ, а тут настраивается вид одного блока. Нужна потому,
# что кнопка «настройки мини-графа» рисовалась глифом ГРАФА: значок обещал показать
# граф, а кнопка раскрывала панель фильтров.
SLIDERS_ICO = ('<svg class="ico-sliders" viewBox="0 0 25 25" aria-hidden="true" fill="none" '
               'stroke="currentColor" stroke-width="1.7" stroke-linecap="round">'
               '<line x1="4" y1="7" x2="21" y2="7"/><line x1="4" y1="12.5" x2="21" y2="12.5"/>'
               '<line x1="4" y1="18" x2="21" y2="18"/>'
               '<circle cx="9" cy="7" r="2.2" fill="var(--card-bg, #fff)"/>'
               '<circle cx="16" cy="12.5" r="2.2" fill="var(--card-bg, #fff)"/>'
               '<circle cx="7" cy="18" r="2.2" fill="var(--card-bg, #fff)"/></svg>')


def asset_ver():
    """Хэш от содержимого всех css/js. С 2026-08-04 в СТРАНИЦЫ БОЛЬШЕ НЕ ВШИВАЕТСЯ
    (шаблоны зовут /js/x.js без ?v=): каждая правка интерфейса меняла байты всех 42 471
    страницы, Google видел «весь сайт обновился» и тратил бюджет обхода на переобход
    старья вместо свежих статей — а свежая статья это автор, который ищет сам себя
    (владелец). Свежесть кэша теперь держат заголовки Worker: css/js 5 минут + 304.
    Дисциплина взамен версии: JS обязан работать со СТАРОЙ разметкой — новые функции
    проверяют «есть ли элемент», а не предполагают его; окно рассинхрона ≤5 минут.
    Хэш остаётся для служебных нужд (сторож изменений, учебные страницы)."""
    global _ASSET_VER
    if _ASSET_VER is None:
        h = hashlib.sha256()
        for p in sorted(Path("css").glob("*.css")) + sorted(Path("js").glob("*.js")):
            h.update(p.read_bytes())
        _ASSET_VER = h.hexdigest()[:10]
    return _ASSET_VER


# ── Images ──
def ensure_article_webp(folder):
    """Webp для картинок ОДНОЙ статьи — внутри конвейера. Третье пришествие webp-граблей
    (2026-07-30, ночь): шаг жил в обёртках run.py, а исполнитель очереди заказов зовёт
    генератор напрямую — первая заказанная статья (2310.15936) вышла с 10 jpg и 0 webp,
    партнёры увидели страницу без единой картинки. Теперь конверсия там, где картинки
    рождаются, и НИ ОДИН путь вызова её не обойдёт. CLI-шаг _ensure_webp остаётся как
    страховка-догонялка для старых статей."""
    try:
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        for jpg in Path(folder).glob("*.jpg"):
            wp = jpg.with_suffix(".webp")
            if wp.exists():
                continue
            im = Image.open(jpg)
            im.save(wp, "WEBP", quality=82, method=4)
    except Exception as e:
        print(f"    ⚠️ webp для {folder}: {e} — страница может остаться без картинок")


def save_images(images, aid, folder, min_size=40000):
    # Имена строго последовательные 0..N-1: og:image и gen_mosaic() рассчитывают
    # на непрерывную нумерацию, пропуски из-за фильтра мелких картинок недопустимы.
    saved = []
    for d in images:
        if len(d) < min_size: continue
        p = folder / f"{len(saved)}.jpg"
        p.write_bytes(d)
        saved.append(str(p))
    return saved


def pick_cover_image(images):
    """Обложка статьи — самая крупная (по пиксельной площади) картинка из уже извлечённых из PDF
    (save_images уже отсеял мелочь <40KB байтами). AI-генерация (FLUX) для статей больше не
    используется — дорого и визуально однотипно для космических тем (шар по центру что чёрная
    дыра, что звезда, что планета); настоящие иллюстрации из самой статьи разнообразнее и бесплатны.
    FLUX остался только для тегов/законов (backfill_tag_law_images) — у них своих картинок нет.
    None, если картинок не нашлось (страница уйдёт в плейсхолдер, как раньше у тегов без обложки)."""
    if not images:
        return None
    try:
        from PIL import Image
    except Exception:
        return images[0]
    best, best_area = None, 0
    for p in images:
        try:
            w, h = Image.open(p).size
            area = w * h
            if area > best_area:
                best, best_area = p, area
        except Exception:
            continue
    return best or images[0]


def make_thumbnails(folder, max_pdf=None, width=220):
    """Отдельные лёгкие миниатюры для карточки ленты (чтобы не грузить полноразмерные):
    t_ai.jpg (обложка) + t_0.jpg..t_{max_pdf-1}.jpg (первые PDF-картинки). Возвращает число PDF-миниатюр.
    max_pdf по умолчанию из config.card_pdf_thumbs (в карточке 2 миниатюры/ряд, до 3 рядов = 6). Требует Pillow. Идемпотентно."""
    if max_pdf is None:
        max_pdf = config.get("card_pdf_thumbs", 6)
    try:
        from PIL import Image
    except Exception:
        return 0

    def thumb(src, dst):
        try:
            im = Image.open(src).convert("RGB")
            w, h = im.size
            im = im.resize((width, max(1, round(h * width / w))), Image.LANCZOS)
            im.save(dst, "JPEG", quality=72, optimize=True)
            return True
        except Exception:
            return False

    folder = Path(folder)
    if (folder / "ai.jpg").exists():
        thumb(folder / "ai.jpg", folder / "t_ai.jpg")
    n = 0
    for i in range(max_pdf):
        src = folder / f"{i}.jpg"
        if src.exists() and thumb(src, folder / f"t_{i}.jpg"):
            n += 1
    return n


def captions_for_lang(captions_field, lang):
    """captions в data.json — {"en": [...], "ru": [...], "es": [...]} (переведённые). Старые
    статьи (до этой фичи) хранят плоский английский список — тогда отдаём его как есть для
    любого языка (деградация без перевода, не крэш) до перегенерации/бэкфилла."""
    if isinstance(captions_field, dict):
        return captions_field.get(lang) or captions_field.get("en") or []
    return captions_field or []


def gen_mosaic(images, aid, date_str, captions=None, cover_url=None):
    # Галерея: одно ГЛАВНОЕ изображение (клик → полноэкранный лайтбокс) + лента превью снизу.
    # Клик по превью меняет главное «в окне», ‹ › листают (js/gallery.js). Подписи — figcaption
    # + alt. Одиночная картинка — без ленты/стрелок, только главное. (Юзер-фидбек 2026-07-19.)
    # cover_url (ai.jpg) — AI-обложка ПЕРВЫМ кадром (2026-07-20). Если обложка-fallback это копия
    # одной из PDF-фигур (совпадает по размеру+md5), не показываем её в галерее дважды.
    captions = captions or []
    base = f"/{LANG_DIR}/{DEFAULT_LANG}/archive/{date_str}/{aid}"
    folder = Path(LANG_DIR) / DEFAULT_LANG / "archive" / date_str / aid

    def cap_of(i):
        return captions[i] if i < len(captions) and captions[i] else ""

    dup_idx = None
    if cover_url:
        ai_p = folder / "ai.jpg"
        if ai_p.exists():
            ai_sz, ai_hash = ai_p.stat().st_size, None
            for i in range(len(images)):
                fp = folder / f"{i}.jpg"
                if fp.exists() and fp.stat().st_size == ai_sz:
                    if ai_hash is None:
                        ai_hash = hashlib.md5(ai_p.read_bytes()).hexdigest()
                    if hashlib.md5(fp.read_bytes()).hexdigest() == ai_hash:
                        dup_idx = i
                        break

    items = []  # (full_url, thumb_url, caption)
    if cover_url:
        cover_thumb = f"{base}/t_ai.webp" if (folder / "t_ai.jpg").exists() else cover_url
        items.append((cover_url, cover_thumb, ""))
    for i in range(len(images)):
        if i == dup_idx:
            continue
        u = f"{base}/{i}.webp"
        items.append((u, u, cap_of(i)))

    if not items:
        return ""
    n = len(items)
    thumbs = "".join(
        f'<button type="button" class="gallery-thumb{" is-active" if k == 0 else ""}" '
        f'data-i="{k}" data-src="{full}" data-cap="{attr_safe(cap)}" '
        f'aria-label="{attr_safe(cap) or f"Image {k + 1}"}">'
        f'<img src="{thumb}" alt="" loading="lazy"></button>'
        for k, (full, thumb, cap) in enumerate(items)
    )
    full0, _t0, cap0 = items[0]
    cap_style = "" if cap0 else ' style="display:none"'
    nav = (
        '<button type="button" class="gallery-nav gallery-prev" aria-label="Prev">‹</button>'
        '<button type="button" class="gallery-nav gallery-next" aria-label="Next">›</button>'
    ) if n > 1 else ""
    thumbs_html = f'<div class="gallery-thumbs">{thumbs}</div>' if n > 1 else ""
    return (
        f'<div class="gallery" data-count="{n}">'
        f'<div class="gallery-stage">{nav}'
        f'<a class="gallery-main" href="{full0}" aria-label="Open image">'
        f'<img class="gallery-main-img" src="{full0}" alt="{attr_safe(cap0)}"></a>'
        f'<figcaption class="gallery-caption"{cap_style}>{safe(cap0)}</figcaption>'
        f'</div>{thumbs_html}</div>'
    )


from gen_llm import *  # LLM-слой вынесен в gen_llm.py
import tag_domains     # доменные облака тегов (какой словарь видит статья в промпте)
import gen_context     # окружение работы для промпта разбора (соседи, плотность, группа карты)


def _check_neighbourhood(scipop, ctx_meta):
    """Опоры поля neighbourhood проверяются кодом, а не доверием к модели.

    Правило то же, что в tools/recommend.py: утверждение без опоры на реальную работу из
    показанного списка — выброшено целиком. Разведка 11 августа показала, зачем: модель
    охотно ссылается на работы, которых в списке не было, и такую ссылку читатель-учёный
    проверяет первой. Здесь дешевле промолчать, чем ошибиться.
    """
    nb = scipop.get("neighbourhood")
    if not isinstance(nb, dict):
        scipop.pop("neighbourhood", None)
        return scipop
    known = {str(x.get("id")) for x in (ctx_meta.get("neighbours") or [])}
    known |= {str(x.get("id")) for x in (ctx_meta.get("world") or [])}
    based = [b for b in as_list(nb.get("based_on")) if str(b) in known]
    if not based or not (nb.get("same") or nb.get("different")):
        if nb:
            print("    🌐 окружение: neighbourhood без опоры на показанные работы — выброшено")
        scipop.pop("neighbourhood", None)
        return scipop
    # Идентификаторы в самом тексте не показываем: ссылку подставляет сайт (правило recommend.py).
    for k in ("same", "different"):
        if isinstance(nb.get(k), str):
            nb[k] = re.sub(r"\[?\b\d{4}\.\d{4,5}(v\d+)?\b\]?", "", nb[k]).replace("  ", " ").strip()
    nb["based_on"] = based
    scipop["neighbourhood"] = nb
    return scipop
# Флаг экономии (ТЗ 2026-07-27, §6.5): advanced — самый крупный и самый редко читаемый уровень.
# По умолчанию true, чтобы ничего не сломать на существующем архиве.
TRANSLATE_ADVANCED = CONFIG.get("translate_advanced", True)

REFINE = os.environ.get("REFINE") == "1" or CONFIG.get("refine", False)

# Версия промпта «Аннотации» (data/prompts/abstract-adapt.txt). Поднимается ВРУЧНУЮ при
# смысловой правке промпта: по ней build_article решает, реюзить старую аннотацию при
# пересоздании статьи или считать заново. v2 — переписан 2026-07-31 (сухой пересказ →
# наш голос; аннотация уходит на карточку в ленте и делает первое впечатление).
ABSTRACT_PROMPT_V = 2

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


_VALID_LAWS = None
def valid_law_ids():
    global _VALID_LAWS
    if _VALID_LAWS is None:
        p = Path(f"lang/{DEFAULT_LANG}/data/laws.json")
        _VALID_LAWS = set(json.loads(p.read_text(encoding="utf-8")).keys()) if p.exists() else set()
    return _VALID_LAWS


def scientist_link_or_text(s, lang, label=None):
    """Ссылка на страницу учёного — только если он реально есть в курируемом реестре
    (valid_scientist_ids(), ключи одинаковы для всех языков). Законы/теги/статьи нередко
    упоминают в истории открытия учёных, которые в 129-реестр не попали (не влезли по конфигу,
    либо второстепенная фигура) — тогда просто текст, а не мёртвая ссылка на /scientists/....html."""
    label = label if label is not None else s
    if s not in valid_scientist_ids():
        return safe(label)
    return (f'<a href="/{LANG_DIR}/{lang}/scientists/{attr_safe(author_slug(s))}.html" '
            f'class="text-scientist" data-scientist="{attr_safe(s)}">{safe(label)}</a>')


def reading_minutes(scipop):
    """Оценка времени чтения (мин), ~180 слов/мин."""
    parts = [scipop.get("text", "")]
    for k in ("context", "methods", "results", "implications", "future_development",
              "impact_on", "next_steps", "key_problems_connection", "metaphor", "future"):
        parts.append(scipop.get(k, ""))
    words = len(re.sub(r"\[/?(tag|scientist)[^\]]*\]", " ", " ".join(parts)).split())
    return max(1, round(words / 180))


def article_og_image_html(date_str, article_id):
    """Блок og:image для статьи — с ПРОВЕРКОЙ, что картинка есть, и с настоящими размерами.

    До 2026-07-31 адрес обложки и размеры 1440x960 стояли в шаблоне литералом. Обе половины
    врали (обход живого сайта): у 222 статей файла нет вовсе — карточка ссылки уходила
    с адресом, отдающим 404; а из тех, что есть, заявленным 1440x960 соответствовали 27% —
    остальные 1024x1024, 1920x1080 и длинный хвост, и парсер, который верит мете, рисовал
    карточку не той пропорции.

    Обложки лежат централизованно под языком-источником — на всех языках один файл.
    Нет картинки (или она вырожденная) — отдаём карточку без картинки: пустая лучше битой.
    """
    folder = Path(LANG_DIR) / DEFAULT_LANG / "archive" / date_str / article_id
    webp = folder / "ai.webp"
    try:
        if not webp.exists() or webp.stat().st_size < 2000:
            return '<meta name="twitter:card" content="summary">'
    except OSError:
        return '<meta name="twitter:card" content="summary">'
    url = f"{SITE_URL}/{LANG_DIR}/{DEFAULT_LANG}/archive/{date_str}/{article_id}/ai.webp"
    size = ""
    try:
        import warnings

        from PIL import Image
        with warnings.catch_warnings():
            # Image.open читает только заголовок, распаковки не происходит — а Pillow всё
            # равно предупреждает про «бомбу» на каждой обложке крупнее 89 мегапикселей,
            # и таких у нас достаточно, чтобы залить весь лог сборки и спрятать в нём
            # настоящую ошибку. Глушим ровно здесь и ровно это.
            warnings.simplefilter("ignore", Image.DecompressionBombWarning)
            with Image.open(webp) as im:
                w, h = im.size
        # Ниже 200x200 карточку не принимает часть площадок — лучше без картинки.
        if w < 200 or h < 200:
            return '<meta name="twitter:card" content="summary">'
        nl = "\n    "
        size = (f'{nl}<meta property="og:image:width" content="{w}">'
                f'{nl}<meta property="og:image:height" content="{h}">')
    except Exception:
        pass   # размеры необязательны: без них площадка просто померит сама
    return (f'<meta property="og:image" content="{url}">{size}'
            f'\n    <meta name="twitter:card" content="summary_large_image">')


def og_title_for(scipop, article, lang):
    """Заголовок для карточки ссылки. У непереведённых статей тело честно говорит
    «на этот язык ещё не переведено», а og:title оставался РУССКИМ — 216 страниц
    (en 81, es 61, ar 72) уходили в мессенджер кириллицей. Для неславянских языков
    кириллица в заголовке = заведомо непереведённая заглушка: берём оригинальное
    название статьи с arXiv, оно хотя бы на латинице и по теме."""
    title = (scipop.get("title") or "").strip()
    if lang != "ru" and re.search(r"[А-Яа-яЁё]", title):
        return (article.get("title") or title).strip()
    return title or article.get("title", "")


def build_jsonld(scipop, article, date_str, lang, canonical_url, abstract_full=""):
    data = {
        "@context": "https://schema.org", "@type": "ScholarlyArticle",
        "headline": scipop.get("title", article.get("title", ""))[:110],
        "description": scipop.get("oneliner", "")[:250],
        "inLanguage": lang, "datePublished": date_str,
        "url": canonical_url,
        "image": f"{SITE_URL}/{LANG_DIR}/{DEFAULT_LANG}/archive/{date_str}/{article['id']}/ai.webp",
        "author": [{"@type": "Person", "name": a} for a in article.get("authors", [])[:10]],
        "publisher": {"@type": "Organization", "name": SITE_NAME},
        "isBasedOn": f"https://arxiv.org/abs/{article['id']}",
    }
    if abstract_full:  # авторитетное саммари из оригинального абстракта — для поиска/LLM-краулеров
        data["abstract"] = abstract_full[:2000]
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + '</script>'


CALLOUT_RE = re.compile(r'\[callout\](.+?)\[/callout\]', re.S | re.I)


def _render_paragraph(p, lang):
    """Абзац текста статьи: врезки [callout]…[/callout] выделяются в блок .callout.
    Модель иногда ставит врезку не отдельным абзацем, а вперемешку с обычным текстом —
    поэтому режем по всем вхождениям, а не требуем точного совпадения всего абзаца."""
    chunks = CALLOUT_RE.split(p)
    if len(chunks) == 1:
        return f"<p>{parse_markers(p, lang)}</p>"
    html_parts = []
    for i, chunk in enumerate(chunks):
        chunk = chunk.strip()
        if not chunk:
            continue
        if i % 2 == 1:
            html_parts.append(f'<div class="callout">{parse_markers(chunk, lang)}</div>')
        else:
            html_parts.append(f"<p>{parse_markers(chunk, lang)}</p>")
    return "".join(html_parts)


_SCI_LOC_CACHE = {}


def load_scientists_loc(lang):
    """Локализованный справочник учёных (по образцу load_tags_loc), с откатом на язык по умолчанию."""
    if lang not in _SCI_LOC_CACHE:
        p = Path(f"lang/{lang}/data/scientists.json")
        if not p.exists():
            p = Path(f"lang/{DEFAULT_LANG}/data/scientists.json")
        try:
            _SCI_LOC_CACHE[lang] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        except json.JSONDecodeError:
            _SCI_LOC_CACHE[lang] = {}
    return _SCI_LOC_CACHE[lang]


def _looks_russian_word(v):
    """Для КОРОТКИХ подписей ссылок: одной кириллической буквы достаточно, порог по доле
    (как в _looks_russian) тут не работает — подпись бывает в одно слово."""
    return isinstance(v, str) and bool(_CYRILLIC.search(v))


def parse_markers(text, lang):
    # Ссылку делаем ТОЛЬКО если тег/учёный реально существует. Модель иногда метит
    # понятия вне нашего списка — для них оставляем обычный текст, без битой ссылки.

    # Подпись ссылки живёт прямо в маркере ([[tag:id|подпись]]) и приходит из перевода. Модель
    # переводит прозу, но подпись местами оставляет русской — в английском тексте всплывало
    # «пульсары», в арабском «чёрные дыры» (юзер 2026-07-23). Русскую подпись заменяем
    # локализованным названием из справочника: детерминированно и без повторного перевода.
    def fix_label(label, localized):
        return localized if (lang != DEFAULT_LANG and _looks_russian_word(label) and localized) else label

    def tag_link(m):
        tid, label = m.group(1).strip(), m.group(2)
        if tid not in valid_tag_ids():
            alt = re.sub(r"[\s-]+", "_", tid.lower())
            tid = alt if alt in valid_tag_ids() else None
        if not tid:
            return label
        label = fix_label(label, load_tags_loc(lang).get(tid, {}).get("name"))
        return f'<a href="/{LANG_DIR}/{lang}/tags/{tid}.html" class="text-tag" data-tag="{tid}">{label}</a>'

    def scientist_link(m):
        name, label = m.group(1).strip(), m.group(2)
        if name not in valid_scientist_ids():
            return label
        label = fix_label(label, load_scientists_loc(lang).get(name, {}).get("name"))
        return (f'<a href="/{LANG_DIR}/{lang}/scientists/{attr_safe(author_slug(name))}.html" '
                f'class="text-scientist" data-scientist="{attr_safe(name)}">{label}</a>')

    def law_link(m):
        # Модель иногда метит закон вне нашего реестра — тогда оставляем обычный текст, без битой ссылки.
        lid, label = m.group(1).strip(), m.group(2)
        if lid not in valid_law_ids():
            alt = re.sub(r"[\s-]+", "_", lid.lower())
            lid = alt if alt in valid_law_ids() else None
        if not lid:
            return label
        label = fix_label(label, load_laws_loc(lang).get(lid, {}).get("name"))
        return f'<a href="/{LANG_DIR}/{lang}/laws/{lid}.html" class="text-law" data-law="{lid}">{label}</a>'

    text = re.sub(r'\[tag:([^\]]+)\](.*?)\[/tag\]', tag_link, text)
    text = re.sub(r'\[scientist:([^\]]+)\](.*?)\[/scientist\]', scientist_link, text)
    text = re.sub(r'\[law:([^\]]+)\](.*?)\[/law\]', law_link, text)
    return text


def render_formulas(formulas):
    """formula-render получает СЫРОЙ LaTeX как textContent, который потом читает katex.render()
    на клиенте (см. article.html/tag.html/law.html — эти элементы исключены из авто-скана
    $-делимитеров, ignoredClasses:['formula-render']). Без HTML-экранирования LaTeX с <, >
    или & (сравнения, \\land/\\lor через &, матрицы/aligned-окружения) парсится браузером как
    разметка ДО того, как el.textContent доберётся до KaTeX — формула рендерится сломанно или
    обрезанной (Блок 7, юзер-фидбек 2026-07-21). html.escape() + textContent на чтении
    корректно восстанавливает исходные символы для KaTeX."""
    return "".join(
        f'<div class="formula"><div class="formula-render">{html.escape(f["latex"])}</div>'
        f'<div class="formula-meaning">{html.escape(f.get("meaning", ""))}</div></div>'
        for f in formulas if f.get("latex")
    )


def trivia_html(fun_fact, scifi="", lang=DEFAULT_LANG):
    """Единый блок «интересный факт + в фантастике» под текстом статьи (одна карточка, не два разрозненных блока).

    Текст идёт через parse_markers: модель размечает [tag:…]/[scientist:…] и в fun_fact,
    и раньше маркеры печатались читателю сырыми — 1419 файлов (QA 2026-07-29)."""
    rows = []
    if fun_fact:
        rows.append(f'<p class="fact">{parse_markers(fun_fact, lang)}</p>')
    if scifi:
        rows.append(f'<p class="fact fact-scifi">{parse_markers(scifi, lang)}</p>')
    return f'<div class="fun-fact">{"".join(rows)}</div>' if rows else ""


def abstract_for(abstract, lang, version):
    """Текст «Аннотации» нужного языка+версии с откатами. Обратно совместимо со старым
    плоским форматом (abstract{lang} = строка → одна на все версии). mini берёт popular."""
    a = (abstract or {}).get(lang)
    # Откат на русскую аннотацию допустим ТОЛЬКО для русской страницы: иначе под арабской
    # обвязкой висел русский абзац (юзер 2026-07-23 — нашёл русский текст на ar). Нет своей
    # аннотации — не показываем никакой.
    if not a and lang == DEFAULT_LANG:
        a = (abstract or {}).get(DEFAULT_LANG)
    a = a or {}
    if isinstance(a, str):
        return "" if lang != DEFAULT_LANG and _looks_russian(a) else a
    if isinstance(a, dict):
        if version == "mini":
            return ""  # у «мини» аннотация не нужна
        t = a.get(version) or a.get("popular") or next((t for t in a.values() if t), "")
        return "" if lang != DEFAULT_LANG and _looks_russian(t) else t
    return ""


def _looks_russian(v):
    return isinstance(v, str) and len(v) > 20 and len(_CYRILLIC.findall(v)) / len(v) > 0.30


# Виджет обратной связи (реакции 👍👎⭐ + чипы + коммент) — общий для статей/тегов/законов/учёных.
# entity_type пишется в БД (likes.entity_type/feedback.entity_type) — see docs/engagement-expand-migration.sql.
FEEDBACK_CHIPS_LOC = [
    ("reads_well", {"ru": "Хорошо читается", "en": "Reads well", "zh": "读起来顺畅", "fr": "Se lit bien", "ar": "سهل القراءة"}),
    ("too_long", {"ru": "Многовато текста", "en": "Too long", "zh": "篇幅偏长", "fr": "Trop long", "ar": "طويل جدًا"}),
    ("unclear", {"ru": "Непонятно", "en": "Unclear", "zh": "不易懂", "fr": "Peu clair", "ar": "غير واضح"}),
    ("great", {"ru": "Отлично", "en": "Great", "zh": "很棒", "fr": "Excellent", "ar": "ممتاز"}),
    ("dry", {"ru": "Суховато", "en": "A bit dry", "zh": "略枯燥", "fr": "Un peu sec", "ar": "جاف قليلاً"}),
]
FEEDBACK_UI_LOC = {
    "ru": ("Как читается? (поможет улучшить тексты)", "+ написать комментарий",
           "ваш комментарий разберём пакетно — при необходимости поправим статью", "отправить"),
    "en": ("How does it read? (helps us improve)", "+ add a comment",
           "comments are reviewed in batches — we may update the article", "send"),
    "es": ("¿Qué tal se lee? (nos ayuda a mejorar)", "+ añadir un comentario",
           "los comentarios se revisan por lotes — podemos actualizar el artículo", "enviar"),
    "zh": ("读起来怎么样？(帮助我们改进)", "+ 添加评论",
           "评论将批量处理 — 如有需要我们会修改文章", "发送"),
    "fr": ("Lecture agréable ? (nous aide à améliorer)", "+ ajouter un commentaire",
           "les commentaires sont traités par lots — nous pourrons mettre à jour l'article", "envoyer"),
    "ar": ("كيف كانت القراءة؟ (يساعدنا على التحسين)", "+ أضف تعليقًا",
           "تتم مراجعة التعليقات دفعة واحدة — قد نُحدّث المقال عند الحاجة", "إرسال"),
}


def feedback_comment_label(lang):
    """Подпись кнопки «+ комментарий» — нужна и снаружи (когда кнопка живёт в строке лайков статьи)."""
    # своя SVG-иконка вместо голого «+» (юзер 2026-07-25: «+ add comment — сделать нашу иконку»)
    return '<svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 12a7.5 7.5 0 0 1-7.5 7.5c-1.2 0-2.35-.28-3.36-.78L4.5 20l1.3-4.1A7.5 7.5 0 1 1 20 12Z"/></svg> ' + FEEDBACK_UI_LOC.get(lang, ("", "add a comment", "", ""))[1].lstrip("+ ")


def build_feedback_html(like_id, lang, entity_type="article", next_button_html="", inline_toggle=False):
    fb_title, fb_comment_lbl, fb_placeholder, fb_send = FEEDBACK_UI_LOC.get(
        lang, ("How does it read?", "+ add a comment",
               "comments are reviewed in batches — we may update the article", "send"))
    fb_chips = "".join(f'<span class="fb-chip" data-opt="{k}">{safe(loc.get(lang, loc["en"]))}</span>' for k, loc in FEEDBACK_CHIPS_LOC)
    # Разгружено (юзер-фидбек 2026-07-21: «How does it read? — лишний текст; выбор ответов убрать
    # внутрь открывающегося add comment, а то перегруз»). В покое видна только кнопка «+ комментарий»
    # (и, на статье, кнопка «след. статья»); по клику раскрывается .fb-expand с чипами + полем + отправкой.
    # inline_toggle=True: кнопку «+ комментарий» рисует не тут, а строка лайков статьи (юзер
    # 2026-07-23: «+ add a comment справа от лайков, а не под next article»); здесь только раскрытие.
    title_row = f'<div class="fb-title-row">{next_button_html}</div>' if next_button_html else ''
    toggle = '' if inline_toggle else f'<button type="button" class="fb-comment-toggle">{safe(fb_comment_lbl)}</button>'
    return (f'<div class="feedback" id="feedback" data-article-id="{like_id}" data-entity-type="{entity_type}">'
            f'{title_row}'
            f'{toggle}'
            f'<div class="fb-expand" hidden>'
            f'<div class="fb-chips">{fb_chips}</div>'
            f'<textarea class="fb-comment" rows="2" placeholder="{attr_safe(fb_placeholder)}"></textarea>'
            f'<div class="fb-row"><button class="fb-send">{safe(fb_send)}</button></div>'
            f'</div>'
            f'<span class="fb-status"></span>'
            f'</div>')


ACTIONS_LOC = {
    "ru": "избранное", "en": "favorite", "es": "favorito", "zh": "收藏", "fr": "favori", "ar": "مفضلة",
}
SHARE_LABEL = {"ru": "Поделиться", "en": "Share", "es": "Compartir", "ar": "مشاركة",
               "fr": "Partager", "zh": "分享"}
def share_label_for(lang):
    return SHARE_LABEL.get(lang, SHARE_LABEL["en"])
NAV_FAV_LOC = {
    "ru": "Избранное", "en": "Favorites", "zh": "收藏夹", "fr": "Favoris", "es": "Favoritos", "ar": "المفضلة",
}
REACTIONS_LOC = {
    "ru": {"like": "Нравится", "dislike": "Не нравится", "superlike": "Супер!"},
    "en": {"like": "Like", "dislike": "Dislike", "superlike": "Awesome!"},
    "es": {"like": "Me gusta", "dislike": "No me gusta", "superlike": "¡Genial!"},
    "ar": {"like": "أعجبني", "dislike": "لم يعجبني", "superlike": "رائع!"},
}


def nav_fav_title(lang):
    """Тайтл ★-ссылки на /favorites.html в шапке — локализован (юзер-фидбек: title="Избранное"
    торчал по-русски на en/es/ar)."""
    return NAV_FAV_LOC.get(lang, NAV_FAV_LOC["en"])


def reaction_titles(lang):
    return REACTIONS_LOC.get(lang, REACTIONS_LOC["en"])


def text_section_html(label, text):
    """<div class="section"><h2>label</h2><p>text</p></div> — ТОЛЬКО если text непусто, иначе "".
    Раньше на странице тега эта разметка была литералом в шаблоне (всегда рендерилась, даже
    без текста) — пустая секция с H2-подписью и пустым <p> давала визуальный "стык" пустых
    строк с соседними блоками, у которых есть border-top/bottom (юзер-фидбек 2026-07-21,
    Блок 4). Страница закона уже строила секции так же (свой sec()); теперь общая функция."""
    return f'<div class="section"><h2>{safe(label)}</h2><p>{safe(text)}</p></div>' if text else ""


def related_row(label, links, kind=""):
    """Ряд плашек связей. Заголовки-слова («Связанные:», «Открыли:») убраны — владелец
    2026-07-30: «слово связанные лишнее, и так понятно»; группы различаются CSS-классом
    (row-tags / row-laws / row-sci — оттенок и шрифт), label остаётся в aria для читалок."""
    if not links:
        return ""
    cls = f" related-{kind}" if kind else ""
    return (f'<div class="related-tags{cls}" aria-label="{safe(label)}">'
            f'{" · ".join(links)}</div>')


def side_chip_group(label, chip_html_list):
    """Колонка-плашек для правого сайдбара (.side-sci/.side-tag/.side-law уже стилизованы в
    css/style.css под .article-side) — та же визуальная логика, что и на странице статьи,
    применённая теперь и к странице тега/закона/учёного (юзер-фидбек 2026-07-15: "тот же
    принцип... везде один подход"). chip_html_list — уже готовые <a class="side-...">...</a>."""
    if not chip_html_list:
        return ""
    return f'<div class="side-tags-label">{safe(label)}</div>' + "".join(chip_html_list)


GRAPH_KIND_PRIORITY = ["tag", "law", "sci"]
GRAPH_CROSS_EDGES = {frozenset(("tag", "law")): "tag-law", frozenset(("tag", "sci")): "tag-sci",
                     frozenset(("law", "sci")): "law-sci"}


def mini_graph_filters_html(lang, center_kind="tag"):
    """Чекбоксы типов узлов + типов связей для мини-графа — та же логика фильтра, что и на
    большом графе-эксплорере. center_kind=None (страницы-облака тегов/законов/учёных без
    привязки к одному узлу) — единый дефолт "все 3 типа + все кросс-рёбра, без сам-на-себя"
    (юзер-фидбек 2026-07-15: "цинфицировать везде один подход").
    center_kind="tag"/"law"/"sci" (страница одной сущности) — умный дефолт: центр + следующий
    по приоритету тег→закон→учёный тип, и только связь МЕЖДУ ними. Третий тип и любые
    "сам-на-себя" рёбра пользователь включает вручную — авто-переключение кросс-рёбер при
    смене типов делает js/mini-graph.js.
    center_kind=None дефолт — только законы+учёные (юзер-фидбек 2026-07-17: "граф оказывается
    перегружен" — тегов у статьи/в справочнике обычно больше всего, они и захламляли вид;
    тег-узлы никуда не делись, просто чекбокс "теги" по умолчанию снят).
    center_kind="article" (мультицентровой граф НА КАРТОЧКЕ СТАТЬИ конкретно, не облачные
    страницы) — тег снова включён по умолчанию (юзер-фидбек 2026-07-19: "по умолчанию включенный
    тег и его связи с учёными и законами") — теги статьи это её собственные центры, прятать их
    там не нужно (в отличие от облачных страниц, где тегов МНОГИЕ СОТНИ и они реально захламляют)."""
    loc = GRAPH_LABELS.get(lang, GRAPH_LABELS["en"])
    if center_kind == "article":
        default_kinds = {"tag", "law", "sci"}
        default_cross_edges = {"tag-law", "tag-sci", "law-sci"}
    elif center_kind is None:
        default_kinds = {"law", "sci"}
        default_cross_edges = {"law-sci"}
    else:
        next_kind = GRAPH_KIND_PRIORITY[(GRAPH_KIND_PRIORITY.index(center_kind) + 1) % 3]
        default_kinds = {center_kind, next_kind}
        default_cross_edges = {GRAPH_CROSS_EDGES[frozenset((center_kind, next_kind))]}

    def kind_box(value, color, label):
        checked = " checked" if value in default_kinds else ""
        return f'<label><input type="checkbox" class="mg-kind" value="{value}"{checked}> <span style="color:{color}">●</span> {safe(label)}</label>'

    # Цвета-легенды точек ● синхронны с KIND_COLORS в js/mini-graph.js / js/knowledge-graph.js:
    # один цвет на ТИП узла (тег/закон/учёный/раздел), чтобы тип читался с одного взгляда.
    kind_boxes = (
        kind_box("tag", "#6C5CE7", loc["tags"])
        + kind_box("law", "#D64545", loc["laws"])
        + kind_box("sci", "#2FA84F", loc["scientists"])
    )

    def edge_box(value, label, checked):
        return f'<label class="mg-edge-label"><input type="checkbox" class="mg-edge" value="{value}"{" checked" if checked else ""}> {safe(label)}</label>'

    edge_boxes = (
        edge_box("tag-law", loc["edge_tag_law"], "tag-law" in default_cross_edges)
        + edge_box("tag-sci", loc["edge_tag_sci"], "tag-sci" in default_cross_edges)
        + edge_box("law-sci", loc["edge_law_sci"], "law-sci" in default_cross_edges)
        + edge_box("tag-tag", loc["edge_tag_tag"], False)
        + edge_box("law-law", loc["edge_law_law"], False)
        + edge_box("sci-sci", loc["edge_sci_sci"], False)
    )
    # Раздел arXiv — 4-й тип узла, ТОЛЬКО на облачных страницах (center_kind=None), выключен по
    # умолчанию (юзер 2026-07-18: "опционально включаемый... это будет круто"). Своей страницы у
    # раздела нет (описания уже есть в data/arxiv-category-descriptions.json для .cat-chip в
    # поиске) — только узел в графе + связь с тегами статей этого раздела.
    if center_kind is None:
        kind_boxes += kind_box("cat", "#C9A227", loc.get("categories", "categories"))
        edge_boxes += edge_box("tag-cat", loc.get("edge_tag_cat", "tag↔category"), False)
    # Контрол глубины (−1+) — в правом крае строки галок типов.
    depth = ('<span class="mini-depth-ctrl"><button type="button" id="mini-depth-minus">−</button>'
             '<span id="mini-depth-val">1</span><button type="button" id="mini-depth-plus">+</button></span>')
    # Настройки представления графа свёрнуты в подменю (юзер 2026-07-24: «убрать в подменю, а то
    # места много занимает»). По умолчанию скрыто; раскрывается кнопкой-шестерёнкой. Это же снимает
    # проблему «связи не влезают в строку» — их просто не видно, пока не открыл. Единый вид на ВСЕХ
    # карточках (статья/тег/закон/учёный) — функция общая.
    cfg_lbl = MINI_CONFIG_LABEL.get(lang, MINI_CONFIG_LABEL["en"])
    return (f'<button type="button" class="mg-config-toggle">{SLIDERS_ICO} {safe(cfg_lbl)}</button>'
            f'<div class="mini-graph-filters" hidden>'
            f'<div class="mg-kinds">{kind_boxes}{depth}</div>'
            f'<div class="mg-edges">{edge_boxes}</div>'
            f'</div>')


# Описания сайта для карточки предпросмотра — то, что видит человек, которому кинули
# ссылку в мессенджер, ДО того как открыл. У главной и гида их не было вовсе: партнёр
# получал голую ссылку без заголовка, описания и картинки (замер живого сайта 2026-07-30).
SITE_OG = {
    "ru": ("bridge42worlds — наука понятным языком",
           "Свежие препринты arXiv, переписанные так, чтобы их понял любой. "
           "Четыре глубины на выбор, живая карта науки: темы, законы и учёные за каждым открытием."),
    "en": ("bridge42worlds — science made simple",
           "The latest arXiv preprints rewritten so anyone can read them. "
           "Four depths to choose from, and a living map of science: topics, laws and the people behind them."),
    "es": ("bridge42worlds — la ciencia simplificada",
           "Los últimos preprints de arXiv reescritos para que cualquiera pueda leerlos. "
           "Cuatro niveles a elegir y un mapa vivo de la ciencia: temas, leyes y científicos."),
    "fr": ("bridge42worlds — la science simplifiée",
           "Les dernières prépublications arXiv réécrites pour être lues par tous. "
           "Quatre niveaux au choix et une carte vivante de la science : sujets, lois et scientifiques."),
    "ar": ("bridge42worlds — العلم ببساطة",
           "أحدث أبحاث arXiv مُعاد كتابتها ليقرأها الجميع. أربعة مستويات للاختيار، "
           "وخريطة حيّة للعلم: الموضوعات والقوانين والعلماء وراء كل اكتشاف."),
}


def latest_cover_url(lang):
    """Картинка предпросмотра для главной и гида — обложка САМОЙ СВЕЖЕЙ статьи.
    Отдельной брендовой картинки 1200x630 у нас нет, а обложки рисует FLUX и они хороши;
    заодно карточка ссылки показывает, что на сайте сегодня. Отдаём jpg, а не webp:
    часть мессенджеров webp в предпросмотре не разбирает."""
    try:
        idx = json.loads((Path(LANG_DIR) / lang / "articles-latest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    for a in idx if isinstance(idx, list) else []:
        aid, date = a.get("id"), a.get("date")
        if not (aid and date):
            continue
        folder = Path(LANG_DIR) / DEFAULT_LANG / "archive" / date / aid
        if (folder / "ai.jpg").exists():
            return f"{SITE_URL}/{LANG_DIR}/{DEFAULT_LANG}/archive/{date}/{aid}/ai.jpg"
    return ""


def site_og_meta(lang, url):
    title, desc = SITE_OG.get(lang, SITE_OG["en"])
    return build_og_meta(title, desc, url, latest_cover_url(lang))


def _og_cut(text, limit=200):
    """Обрезка описания для карточки ссылки — по концу предложения, потом по слову."""
    t = " ".join((text or "").split())
    if len(t) <= limit:
        return t
    head = t[:limit]
    for stop in (". ", "! ", "? ", "; "):
        i = head.rfind(stop)
        if i > limit * 0.5:
            return head[:i + 1]
    i = head.rfind(" ")
    return (head[:i] if i > limit * 0.5 else head).rstrip(" ,;:") + "…"


def build_og_meta(title, description, url, image_url=""):
    """og:/twitter: + meta description — общий блок для тег/закон/учёный страниц
    (у статьи свой набор в шаблоне — там ещё JSON-LD и hreflang)."""
    # Описание режем по границе предложения: у тегов сюда приходило 700+ знаков, у законов
    # 420 — площадки всё равно обрежут на ~160-200, но обрежут ПОСРЕДИНЕ слова, и карточка
    # выглядит оборванной. Лучше закончить мысль самим.
    description = _og_cut(description)
    title, description = attr_safe(title), attr_safe(description)
    img_html = (f'<meta property="og:image" content="{image_url}">\n    '
                f'<meta name="twitter:card" content="summary_large_image">') if image_url else \
               '<meta name="twitter:card" content="summary">'
    return (f'<meta name="description" content="{description}">\n    '
            f'<meta property="og:title" content="{title}">\n    '
            f'<meta property="og:description" content="{description}">\n    '
            f'<meta property="og:url" content="{attr_safe(url)}">\n    '
            # canonical у страниц тега/закона/учёного не было вовсе — поисковик считал
            # пять языковых версий пятью разными страницами об одном и том же.
            f'<link rel="canonical" href="{attr_safe(url)}">\n    '
            f'<meta property="og:type" content="website">\n    '
            f'{img_html}')


ICON_THUMB_UP = ('<svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                 'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
                 '<path d="M7 21V10l4.2-6.6c.9 0 1.8.8 1.8 1.8V9h4.7c1.1 0 1.9 1 1.6 2.1l-1.6 6.3c-.2.8-.9 1.3-1.7 1.3H7Z"/>'
                 '<path d="M7 10H4v11h3"/></svg>')
ICON_THUMB_DN = ('<svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                 'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
                 '<path d="M7 3v11l4.2 6.6c.9 0 1.8-.8 1.8-1.8V15h4.7c1.1 0 1.9-1 1.6-2.1L17.7 6.6c-.2-.8-.9-1.3-1.7-1.3H7Z"/>'
                 '<path d="M7 14H4V3h3"/></svg>')
ICON_STAR = ('<svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
             'stroke-width="1.6" stroke-linejoin="round" aria-hidden="true">'
             '<path d="M12 3.6l2.45 5 5.5.7-4 3.85 1 5.45L12 21.35 7.05 18.5l1-5.45-4-3.85 5.5-.7Z"/></svg>')

def full_first(items):
    """Экспресс — в конец списка при прочих равных (правило владельца 2026-07-31).

    Устойчиво: внутри каждой группы сохраняется порядок, который список задал сам
    (свежесть, вес совпадения). Применяется ко всем спискам статей на страницах
    сущностей — тега, закона, учёного, раздела: правило одно на весь сайт, и в JS
    (js/search.js: fullFirst) оно такое же."""
    full = [a for a in items if not a.get("express")]
    return full + [a for a in items if a.get("express")]


def entity_article_card(a, lang):
    """Карточка статьи в списках справочников (тег/закон/учёный/раздел/автор) — единый вид с
    лентой: миниатюра-обложка + название + короткий текст (юзер 2026-07-24: «список с картинками
    как в тегах, единообразно»). Раньше тут была голая .card-content без картинки."""
    base = f"/{LANG_DIR}/{DEFAULT_LANG}/archive/{a['date']}/{a['id']}/"
    has_img = a.get("image") is not False
    thumb = (f'<a class="card-img-wrap" href="{a["url"]}"><img src="{base}t_ai.webp" '
             f'data-fb="{base}ai.webp" loading="lazy" '
             f"onerror=\"if(this.dataset.fb){{this.src=this.dataset.fb;this.removeAttribute('data-fb');}}"
             f"else{{this.closest('.card-img-wrap').style.display='none';}}\" alt=\"\"></a>") if has_img else ''
    desc = safe(a.get("description", a.get("oneliner", "")))
    title = safe(a["title"])
    # Три уровня прямо на карточке — чтобы попадать сразу в нужную глубину, не открывая
    # статью и не переключаясь внутри. Заменили общий бегунок в шапке (юзер 2026-07-28).
    levels = level_switch_links(lang, "popular", a["date"], a["id"])
    return (f'<article class="article-card">'
            f'<div class="card-eyebrow"><span class="card-date">{a["date"]}</span></div>'
            f'{thumb}'
            f'<div class="card-body">{levels}'
            f'<h3><a href="{a["url"]}" title="{attr_safe(a["title"])}">{title}</a></h3>'
            f'<div class="oneliner">{desc}</div></div></article>')


def build_actions_html(like_id, fav_id, lang, entity_type="article", inline_comment=False):
    """Реакции 👍👎⭐ + избранное — общий блок для статей/тегов/законов/учёных (без «поделиться»,
    оно у статей особое из-за clickbait-заголовка и своей ссылки).
    inline_comment=True — добавляет кнопку «+ комментарий» вплотную к лайкам (единый вид со
    статьёй, юзер 2026-07-24); раскрытие ловит соседний .feedback (см. likes.js)."""
    fav_label = ACTIONS_LOC.get(lang, ACTIONS_LOC["en"])
    rt = reaction_titles(lang)
    comment = (f'<button type="button" class="fb-comment-toggle actions-comment">'
               f'{safe(feedback_comment_label(lang))}</button>') if inline_comment else ''
    return (f'<div class="actions actions-compact" data-article-id="{like_id}" data-entity-type="{entity_type}">'
            f'<div class="reactions">'
            f'<button class="react-btn" data-react="like" title="{attr_safe(rt["like"])}">{ICON_THUMB_UP}<span class="rc">…</span></button>'
            f'<button class="react-btn" data-react="dislike" title="{attr_safe(rt["dislike"])}">{ICON_THUMB_DN}<span class="rc">…</span></button>'
            f'</div>'
            f'<button class="fav-btn" data-fav="{attr_safe(fav_id)}" title="{attr_safe(fav_label)}">'
            f'<span class="fav-ic">{ICON_STAR}</span></button>'
            f'{comment}'
            f'</div>')


# ── Авторские работы: три отличия от статьи с arXiv ──────────────────────────
# Не отдельный шаблон и не отдельный генератор — три функции, дающие три куска html.
# Всё остальное на странице собирается тем же кодом, что у двух тысяч других статей,
# и любая правка дизайна приходит сюда сама.

AW_LABELS = {
    "work":   {"ru": "работа автора", "en": "author's work", "es": "trabajo del autor",
               "ar": "عمل المؤلف", "fr": "travail de l'auteur"},
    "checked": {"ru": "мы разобрали", "en": "we reviewed it", "es": "lo analizamos",
                "ar": "راجعناه", "fr": "examiné par nous"},
    "exp":    {"ru": "эксперимент", "en": "experimental", "es": "experimental",
               "ar": "تجريبي", "fr": "expérimental"},
    "th":     {"ru": "теория", "en": "theoretical", "es": "teórico",
               "ar": "نظري", "fr": "théorique"},
    "live":   {"ru": "работа автора: HTML", "en": "author's paper: HTML",
               "es": "trabajo del autor: HTML", "ar": "بحث المؤلف: HTML",
               "fr": "travail de l'auteur : HTML"},
    "pdf":    {"ru": "PDF", "en": "PDF", "es": "PDF", "ar": "PDF", "fr": "PDF"},
    "zip":    {"ru": "все материалы", "en": "all materials", "es": "todos los materiales",
               "ar": "كل المواد", "fr": "tous les matériaux"},
    "rev_h":  {"ru": "Что мы об этом думаем", "en": "What we make of it",
               "es": "Lo que pensamos", "ar": "رأينا في هذا", "fr": "Ce que nous en pensons"},
    "rev_note": {"ru": "Работа не проходила рецензирование. Это наш разбор — мнение, а не приговор.",
                 "en": "This work has not been peer-reviewed. What follows is our reading of it.",
                 "es": "Este trabajo no ha sido revisado por pares. Lo que sigue es nuestra lectura.",
                 "ar": "لم يخضع هذا البحث لمراجعة الأقران. ما يلي هو قراءتنا له.",
                 "fr": "Ce travail n'a pas été évalué par les pairs. Voici notre lecture."},
    "strength": {"ru": "Сильная сторона", "en": "What works", "es": "Lo que funciona",
                 "ar": "نقطة القوة", "fr": "Le point fort"},
    "advice": {"ru": "Что усилит работу", "en": "What would make it stronger",
               "es": "Qué lo haría más fuerte", "ar": "ما الذي يقوّي العمل",
               "fr": "Ce qui le renforcerait"},
    "questions": {"ru": "Вопросы автору", "en": "Questions for the author",
                  "es": "Preguntas al autor", "ar": "أسئلة إلى المؤلف",
                  "fr": "Questions à l'auteur"},
    "word":   {"ru": "Слово автора", "en": "The author's word", "es": "La palabra del autor",
               "ar": "كلمة المؤلف", "fr": "La parole de l'auteur"},
}


def _aw(key, lang):
    return AW_LABELS[key].get(lang, AW_LABELS[key]["en"])


# Наш знак — мост из логотипа. Ставится у заголовка авторской работы: читатель должен
# видеть, что источник другой, ещё до того, как дочитает строку-паспорт. Тултип говорит
# прямо: это не препринт с arXiv (владелец 2026-08-08).
AW_MARK_SVG = (
    '<svg class="aw-mark" viewBox="0 0 240 150" aria-hidden="true">'
    '<defs><linearGradient id="aw-g" x1="0" x2="1">'
    '<stop offset="0" stop-color="var(--ochre)"/><stop offset="1" stop-color="var(--cyan)"/>'
    '</linearGradient></defs>'
    '<line x1="44" y1="112" x2="196" y2="112" stroke="currentColor" stroke-opacity=".38" '
    'stroke-width="8" stroke-linecap="round"/>'
    '<path d="M44 112 C 84 24, 156 24, 196 112" fill="none" stroke="url(#aw-g)" '
    'stroke-width="14" stroke-linecap="round"/>'
    '<circle cx="44" cy="112" r="13" fill="var(--ochre)"/>'
    '<circle cx="196" cy="112" r="13" fill="var(--cyan)"/></svg>')

AW_TOOLTIP = {
    "ru": "Работа автора, а не препринт с arXiv: прислана нам напрямую и разобрана нами. "
          "Рецензирование она не проходила — доверять ей или нет, решаете вы.",
    "en": "An author's own work, not an arXiv preprint: sent to us directly and reviewed by us. "
          "It has not been peer-reviewed — whether to trust it is up to you.",
    "es": "Trabajo propio del autor, no un preprint de arXiv: enviado directamente y analizado "
          "por nosotros. No ha sido revisado por pares; confiar en él es decisión suya.",
    "ar": "عمل خاص بالمؤلف، وليس مسودة من arXiv: أُرسل إلينا مباشرة وقمنا بمراجعته. "
          "لم يخضع لمراجعة الأقران — والثقة به قرارك أنت.",
    "fr": "Travail propre de l'auteur, non un preprint arXiv : envoyé directement et examiné "
          "par nous. Il n'a pas été évalué par les pairs — à vous de juger.",
}

AW_FILES_H = {"ru": "Забрать работу целиком", "en": "Take the whole work",
              "es": "Llevarse el trabajo completo", "ar": "خذ العمل كاملاً",
              "fr": "Emporter le travail complet"}
AW_FILES_NOTE = {
    "ru": "У статьи с arXiv по ссылке лежит текст. Здесь — текст и все данные, на которых "
          "он построен: работу можно проверить, а не только прочитать.",
    "en": "An arXiv paper gives you the text. Here you get the text and all the data behind "
          "it: this work can be checked, not just read.",
    "es": "Un artículo de arXiv da el texto. Aquí están el texto y todos los datos que lo "
          "sustentan: este trabajo se puede comprobar, no solo leer.",
    "ar": "بحث arXiv يمنحك النص فقط. هنا النص وكل البيانات التي بُني عليها: "
          "يمكن التحقق من هذا العمل، لا قراءته فحسب.",
    "fr": "Un article arXiv donne le texte. Ici, le texte et toutes les données qui le "
          "sous-tendent : ce travail peut être vérifié, pas seulement lu.",
}


def author_work_files_html(article, lang):
    """Блок «забрать работу целиком» под кнопками уровней: HTML, PDF, архив.

    У статьи с arXiv он пуст — там скачивать нечего, и ссылка на первоисточник стоит
    в строке-паспорте. Кнопки без файла не рисуем: ведущая в 404 хуже отсутствующей.
    """
    if not article.get("author_work"):
        return ""
    src = article.get("sources") or {}
    live, pdf = aw_localized(src, lang)
    btns = []
    if live:
        btns.append(f'<a class="aw-file aw-file-main" href="{attr_safe(live)}">'
                    f'{ICON_DOC}{safe(_aw("live", lang))}</a>')
    if pdf:
        btns.append(f'<a class="aw-file" href="{attr_safe(pdf)}">'
                    f'{ICON_DOC}{safe(_aw("pdf", lang))}</a>')
    if src.get("zip"):
        mb = src.get("zip_mb")
        tail = f'<span class="aw-file-size">{mb} MB</span>' if mb else ""
        btns.append(f'<a class="aw-file" href="{attr_safe(src["zip"])}">'
                    f'{ICON_BOX}{safe(_aw("zip", lang))}{tail}</a>')
    if not btns:
        return ""
    return (f'<section class="aw-files"><h3>{safe(AW_FILES_H.get(lang, AW_FILES_H["en"]))}</h3>'
            f'<p class="aw-note">{safe(AW_FILES_NOTE.get(lang, AW_FILES_NOTE["en"]))}</p>'
            f'<div class="aw-file-row">{"".join(btns)}</div></section>')


ICON_DOC = ('<svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/>'
            '<path d="M14 3v5h5"/><path d="M9 13h6"/><path d="M9 17h4"/></svg>')
ICON_BOX = ('<svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            '<path d="M3 7.5h18v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
            '<path d="M3 7.5l1.6-3.2A1.5 1.5 0 0 1 6 3.5h12a1.5 1.5 0 0 1 1.4.8L21 7.5"/>'
            '<path d="M10 12h4"/></svg>')


def aw_localized(src, lang):
    """Живая версия и PDF на языке страницы, если они есть.

    Работа автора переводится на все наши языки, как и всё остальное (владелец 2026-08-08:
    «оригинальный html переведи тоже на все языки… у нас стандарт на все распространяется»).
    Арабский читатель, нажав «работа автора», должен попасть в арабский текст, а не в
    русский. Нет перевода — ведём на язык автора: это честнее, чем битая ссылка.
    """
    live, pdf = src.get("live", ""), src.get("pdf", "")
    if live:
        cand = live.replace("/lang/ru/", f"/lang/{lang}/")
        if (Path(cand.lstrip("/")).exists()):
            live = cand
    if pdf:
        cand = pdf.replace("/lang/ru/", f"/lang/{lang}/")
        if (Path(cand.lstrip("/")).exists()):
            pdf = cand
    return live, pdf


def author_work_sources(article, lang):
    """Три ссылки на первоисточник вместо одной на arXiv.

    Отличие по существу, а не оформление: у статьи с arXiv по ссылке лежит текст, здесь —
    текст И данные, на которых он построен. Такую работу можно проверить, а не только
    прочитать. Чего нет — того и в строке нет: ссылка в 404 хуже отсутствующей.
    """
    src = article.get("sources") or {}
    # НАШ код первым и явно (владелец 2026-08-08: «код статьи не arXiv явно, а наш b42w»).
    # Раньше в этом месте стояло «arXiv:b42p-2026-001» — ссылка на препринт, которого на
    # arXiv нет и не будет: работа пришла к нам напрямую. Читатель, привыкший видеть здесь
    # источник, получал ложный.
    out = [f'<span class="aw-code" title="{attr_safe(AW_TOOLTIP.get(lang, AW_TOOLTIP["en"]))}">'
           f'b42w:{safe(article.get("code") or article["id"])}</span>']
    live, pdf = aw_localized(src, lang)
    if live:
        out.append(f'<a href="{attr_safe(live)}">{safe(_aw("live", lang))}</a>')
    if pdf:
        out.append(f'<a href="{attr_safe(pdf)}">{safe(_aw("pdf", lang))}</a>')
    if src.get("zip"):
        mb = src.get("zip_mb")
        tail = f' ({mb} MB)' if mb else ""
        out.append(f'<a href="{attr_safe(src["zip"])}">{safe(_aw("zip", lang))}{tail}</a>')
    return " · ".join(out)


def author_work_badges_html(article, lang):
    """Плашки у заголовка: чья работа и что мы её разбирали.

    Стоят там же, где «экспресс» у обычной статьи, и выглядят так же — это пометка об
    источнике, а не предупреждение. Ни красного, ни восклицательных знаков.
    """
    kind = (article.get("kind") or "").lower()
    kind_key = "exp" if "эксперимент" in kind or "experim" in kind else (
        "th" if "теор" in kind or "theor" in kind else "")
    tip = attr_safe(AW_TOOLTIP.get(lang, AW_TOOLTIP["en"]))
    parts = [f'<span class="express-badge aw-badge" title="{tip}">'
             f'{AW_MARK_SVG}{safe(_aw("work", lang))}</span>']
    if kind_key:
        parts.append(f'<span class="express-badge aw-kind">{safe(_aw(kind_key, lang))}</span>')
    return " ".join(parts)


def author_work_review_html(article, lang):
    """Наш разбор работы и слово автора — то, чего у статьи с arXiv нет и быть не может.

    Три карточки: что работает, что усилит, о чём спросили. Пустые не показываем: заголовок
    над пустотой читается как поломка страницы.
    """
    rev_all = article.get("review") or {}
    rev = rev_all.get(lang) or rev_all.get("ru") or {}
    if isinstance(rev, dict) and "strength" not in rev and rev_all.get("strength"):
        rev = rev_all
    strength = (rev.get("strength") or "").strip()
    advice = [x for x in (rev.get("advice") or []) if str(x).strip()]
    questions = [x for x in (rev.get("questions") or []) if str(x).strip()]
    comment = (article.get("author_comment") or "").strip()
    if not (strength or advice or questions or comment):
        return ""

    cards = []
    if strength:
        cards.append(f'<div class="aw-card aw-card-plus"><p class="aw-card-l">'
                     f'{safe(_aw("strength", lang))}</p><p>{safe(strength)}</p></div>')
    if advice:
        li = "".join(f"<li>{safe(x)}</li>" for x in advice)
        cards.append(f'<div class="aw-card aw-card-adv"><p class="aw-card-l">'
                     f'{safe(_aw("advice", lang))}</p><ul>{li}</ul></div>')
    if questions:
        li = "".join(f"<li>{safe(x)}</li>" for x in questions)
        cards.append(f'<div class="aw-card"><p class="aw-card-l">'
                     f'{safe(_aw("questions", lang))}</p><ul>{li}</ul></div>')
    word = ""
    if comment:
        paras = "".join(f"<p>{safe(x.strip())}</p>" for x in comment.split(chr(10) + chr(10)) if x.strip())
        word = (f'<div class="aw-word"><p class="aw-card-l">{safe(_aw("word", lang))}</p>'
                f'{paras}</div>')
    return (f'<section class="aw-review"><h2>{safe(_aw("rev_h", lang))}</h2>'
            f'<p class="aw-note">{safe(_aw("rev_note", lang))}</p>'
            f'<div class="aw-cards">{"".join(cards)}</div>{word}</section>')


_KM = {
    "ru": {"h": "Взгляд машины знаний", "nav": "Машина знаний",
           "note": "Этот раздел адресован автору работы и его коллегам. Соседние работы "
                   "нашёл смысловой поиск по нашему архиву — не по совпадению слов, а по "
                   "смыслу. Мы не рецензируем: мы показываем поле вокруг.",
           "seen": "Что сделано в работе", "strength": "В чём сила",
           "dirs": "Куда можно двигаться", "ideas": "Что можно попробовать",
           "sig": "Почему это может быть важно", "src": "опора:",
           "links": "Работы рядом в нашем архиве", "near": "близость",
           "dense": "Вокруг этой работы в архиве плотно: {nn} рядом, ближайший {top}. Тему уже ходят — и есть с чем сверяться.",
           "sparse": "Вокруг этой работы в архиве пусто: ближайший разбор всего на {top}, при обычных 0.64. Похоже, рядом почти не бурили.",
           "mid": "Ближайшая работа архива — {top} по смысловой близости, рядом {nn}. Обычный для нашего корпуса уровень."},
    "en": {"h": "The knowledge machine's view", "nav": "Knowledge machine",
           "note": "This section is addressed to the author of the paper and their "
                   "colleagues. Neighbouring works were found by meaning-based search "
                   "across our archive, not by word overlap. We do not review: we show "
                   "the field around the work.",
           "seen": "What the work does", "strength": "Where its strength is",
           "dirs": "Where it could go next", "ideas": "Worth trying",
           "sig": "Why this may matter", "src": "based on:",
           "links": "Nearby works in our archive", "near": "similarity",
           "dense": "The archive is crowded around this work: {nn} nearby, closest at {top}. This ground is well walked — and there is plenty to compare against.",
           "sparse": "The archive is sparse around this work: the closest review is only {top}, against a usual 0.64. It looks like few have drilled nearby.",
           "mid": "The closest work in the archive sits at {top} by meaning, with {nn} nearby — the usual level for our corpus."},
    "es": {"h": "La mirada de la máquina del conocimiento", "nav": "Máquina del conocimiento",
           "note": "Esta sección está dirigida al autor del trabajo y a sus colegas. Los "
                   "trabajos vecinos los encontró la búsqueda por significado en nuestro "
                   "archivo, no por coincidencia de palabras. No evaluamos: mostramos el "
                   "campo alrededor.",
           "seen": "Qué hace el trabajo", "strength": "Dónde está su fuerza",
           "dirs": "Hacia dónde puede avanzar", "ideas": "Vale la pena probar",
           "sig": "Por qué puede importar", "src": "se apoya en:",
           "links": "Trabajos cercanos en nuestro archivo", "near": "cercanía",
           "dense": "El archivo está poblado alrededor de este trabajo: {nn} cercanos, el más próximo a {top}. Es terreno transitado, y hay con qué contrastar.",
           "sparse": "El archivo está vacío alrededor de este trabajo: el análisis más cercano queda en {top}, frente a un 0.64 habitual. Parece que aquí al lado casi nadie ha perforado.",
           "mid": "El trabajo más cercano del archivo está a {top} por significado, con {nn} alrededor: el nivel habitual de nuestro corpus."},
    "fr": {"h": "Le regard de la machine du savoir", "nav": "Machine du savoir",
           "note": "Cette section s'adresse à l'auteur du travail et à ses collègues. Les "
                   "travaux voisins ont été trouvés par une recherche sémantique dans notre "
                   "archive, et non par correspondance de mots. Nous n'évaluons pas : nous "
                   "montrons le champ autour.",
           "seen": "Ce que fait ce travail", "strength": "Où est sa force",
           "dirs": "Vers où avancer", "ideas": "À essayer",
           "sig": "Pourquoi cela peut compter", "src": "appui :",
           "links": "Travaux voisins dans notre archive", "near": "proximité",
           "dense": "L'archive est dense autour de ce travail : {nn} voisines, la plus proche à {top}. Le terrain est fréquenté, et il y a de quoi se comparer.",
           "sparse": "L'archive est vide autour de ce travail : l'analyse la plus proche n'est qu'à {top}, contre 0,64 d'ordinaire. Il semble qu'on ait peu foré à côté.",
           "mid": "Le travail le plus proche de l'archive se situe à {top} par le sens, avec {nn} autour — le niveau habituel de notre corpus."},
    "ar": {"h": "نظرة آلة المعرفة", "nav": "آلة المعرفة",
           "note": "هذا القسم موجَّه إلى مؤلف العمل وزملائه. الأعمال المجاورة عثر عليها بحثٌ "
                   "دلالي في أرشيفنا، لا بتطابق الكلمات. نحن لا نقيّم العمل: نعرض الحقل من "
                   "حوله.",
           "seen": "ماذا يفعل هذا العمل", "strength": "أين تكمن قوته",
           "dirs": "إلى أين يمكن المضي", "ideas": "يستحق التجربة",
           "sig": "لماذا قد يكون هذا مهمًا", "src": "استنادًا إلى:",
           "links": "أعمال قريبة في أرشيفنا", "near": "التقارب",
           "dense": "الأرشيف مزدحم حول هذا العمل: {nn} قريبة، أقربها عند {top}. أرض مطروقة، وفيها ما يُقاس عليه.",
           "sparse": "الأرشيف خالٍ حول هذا العمل: أقرب تحليل عند {top} فقط، مقابل 0.64 المعتادة. يبدو أن الحفر بجواره كان نادرًا.",
           "mid": "أقرب عمل في الأرشيف يقع عند {top} من حيث المعنى، وحوله {nn} — وهو المستوى المعتاد في مجموعتنا."},
    "zh": {"h": "知识机器的视角", "nav": "知识机器",
           "note": "本节写给论文作者及其同行。相邻工作由我们档案库的语义检索找出，而非词面匹配。"
                   "我们不做评审，只呈现它周围的领域。",
           "seen": "这项工作做了什么", "strength": "它的长处",
           "dirs": "可以往哪里走", "ideas": "值得一试",
           "sig": "为什么这可能重要", "src": "依据：",
           "links": "档案库中相邻的工作", "near": "相似度",
           "dense": "这项工作周围很密集：附近有 {nn}，最近的为 {top}。这片地方常有人走，也有得对照。",
           "sparse": "这项工作周围很空：最近的解读只有 {top}，而通常是 0.64。看来旁边少有人钻探。",
           "mid": "档案库中最近的工作按语义为 {top}，周围有 {nn}——是我们语料的常见水平。"},
}


_ORIG_ABS = {
    "ru": ("Оригинальная аннотация", "как её написали авторы, на английском"),
    "en": ("Original abstract", "as written by the authors"),
    "es": ("Resumen original", "tal como lo escribieron los autores, en inglés"),
    "fr": ("Résumé original", "tel que rédigé par les auteurs, en anglais"),
    "ar": ("الملخص الأصلي", "كما كتبه المؤلفون، بالإنجليزية"),
    "zh": ("原文摘要", "作者原文，英文"),
}


# Плашка у NC/ND-работ и её пояснение (в подсказке). Объясняем читателю, почему разбор
# такой работы легален: копирайт защищает выражение, а не факты и идеи; наш текст — наша
# собственная работа, авторский материал (рисунки, подписи) не воспроизводится, дословная
# аннотация показывается неизменной со ссылкой на источник.
_ANALYSIS_BADGE = {
    "ru": "собственный разбор", "en": "independent analysis", "es": "análisis propio",
    "fr": "analyse indépendante", "ar": "تحليل مستقل",
}
_ANALYSIS_NOTE = {
    "ru": "Лицензия этой работы не разрешает переработку авторских материалов, поэтому здесь "
          "только наш собственный текст: рисунки и подписи авторов не используются, оригинальная "
          "аннотация приведена без изменений со ссылкой на источник. Пересказ идей своими "
          "словами — самостоятельное произведение: авторское право защищает форму, а не сами "
          "идеи и факты.",
    "en": "The licence of this paper does not permit adaptation of the authors' materials, so this "
          "page contains only our own text: the authors' figures and captions are not used, and "
          "the original abstract appears unchanged with a link to the source. Explaining ideas in "
          "our own words is an independent work: copyright protects expression, not ideas or facts.",
    "es": "La licencia de este trabajo no permite adaptar los materiales de los autores, así que "
          "esta página contiene solo nuestro propio texto: no se usan sus figuras ni leyendas, y el "
          "resumen original aparece sin cambios con enlace a la fuente. Explicar ideas con palabras "
          "propias es una obra independiente: el copyright protege la expresión, no las ideas.",
    "fr": "La licence de ce travail n'autorise pas l'adaptation des contenus des auteurs : cette "
          "page ne contient donc que notre propre texte, sans leurs figures ni légendes, et le "
          "résumé original est reproduit tel quel avec un lien vers la source. Expliquer des idées "
          "avec ses propres mots est une œuvre indépendante : le droit d'auteur protège "
          "l'expression, pas les idées.",
    "ar": "رخصة هذا العمل لا تسمح بتحوير مواد المؤلفين، لذا لا تحتوي هذه الصفحة إلا على نصنا "
          "الخاص: لا نستخدم رسومهم أو تعليقاتهم، والملخص الأصلي معروض دون تغيير مع رابط "
          "المصدر. شرح الأفكار بكلماتنا عمل مستقل: حقوق النشر تحمي الصياغة لا الأفكار والحقائق.",
}


# Снятие с публикации для NC/ND-работ: текст в модалке «Я автор». Подтверждение — письмо
# с институтского адреса; снятие делает человек после проверки, не автомат.
_TAKEDOWN = {
    "ru": {"body": "Вы автор этой работы и не хотите, чтобы наш разбор был опубликован? "
                   "Напишите нам с рабочего или университетского адреса — после подтверждения "
                   "мы снимем страницу с публикации.",
           "btn": "Я автор — снять с публикации"},
    "en": {"body": "Are you an author of this paper and would prefer our analysis not to be "
                   "published? Email us from your institutional address; once confirmed, we "
                   "will take the page down.",
           "btn": "I am the author — request removal"},
    "es": {"body": "¿Es usted autor de este trabajo y prefiere que nuestro análisis no esté "
                   "publicado? Escríbanos desde su correo institucional; tras confirmarlo, "
                   "retiraremos la página.",
           "btn": "Soy el autor: solicitar retirada"},
    "fr": {"body": "Vous êtes l'un des auteurs et préférez que notre analyse ne soit pas "
                   "publiée ? Écrivez-nous depuis votre adresse institutionnelle ; après "
                   "confirmation, nous retirerons la page.",
           "btn": "Je suis l'auteur : demander le retrait"},
    "ar": {"body": "هل أنت من مؤلفي هذا العمل وتفضل عدم نشر تحليلنا؟ راسلنا من بريدك "
                   "الجامعي، وبعد التأكد سنزيل الصفحة.",
           "btn": "أنا المؤلف — طلب إزالة الصفحة"},
}


def original_abstract_html(article, lang):
    """Аннотация работы словами её авторов — в конце продвинутой версии, мелким текстом.

    Владелец 11 августа: «это бесплатно, быстро и даст возможность привлекать поиск по
    оригиналу, который могут делать авторы». Суть в этом: заголовок у нас образный, текст —
    пересказ, и по запросу собственными словами работы наша страница не находится вообще.
    Здесь появляются те самые слова — и заодно читатель может сверить пересказ с источником.

    Показываем и у экспрессов: аннотация — ровно то, из чего экспресс и сделан, скрывать
    её там особенно нечего.
    """
    text = (article.get("abstract_orig") or "").strip()
    if not text:
        return ""
    head, note = _ORIG_ABS.get(lang, _ORIG_ABS["en"])
    aid = article.get("id", "")
    src = ""
    if re.match(r"^\d{4}\.\d{4,5}", aid):
        src = (f'<a class="orig-abs-src" href="https://arxiv.org/abs/{attr_safe(aid)}" '
               f'target="_blank" rel="noopener">arXiv:{safe(aid)}</a>')
    title = safe(article.get("original_title", ""))
    # lang="en" и dir="ltr" на самом тексте: он английский на любой версии страницы, и без
    # этого арабская страница разворачивает латиницу по своим правилам.
    return (f'<section id="orig-abstract" class="orig-abs">'
            f'<h2>{safe(head)}</h2>'
            f'<p class="orig-abs-note">{safe(note)} {src}</p>'
            + (f'<p class="orig-abs-title" lang="en" dir="ltr">{title}</p>' if title else "")
            + f'<p class="orig-abs-text" lang="en" dir="ltr">{safe(text)}</p></section>')


_KM_BADGE_TIP = {
    "ru": "Разобрано машиной знаний: в конце продвинутой версии есть раздел для автора работы "
          "— куда двигаться дальше и что лежит рядом в нашем архиве.",
    "en": "Read by the knowledge machine: the advanced version ends with a section for the "
          "paper's author — where the work could go next and what lies nearby in our archive.",
    "es": "Analizado por la máquina del conocimiento: la versión avanzada termina con una "
          "sección para el autor del trabajo — hacia dónde avanzar y qué hay cerca en nuestro archivo.",
    "fr": "Lu par la machine du savoir : la version avancée se termine par une section destinée "
          "à l'auteur — vers où avancer et ce qui se trouve à côté dans notre archive.",
    "ar": "قرأته آلة المعرفة: تنتهي النسخة المتقدمة بقسم موجَّه إلى مؤلف العمل — إلى أين يمكن "
          "المضي وما الذي يقع قريبًا في أرشيفنا.",
    "zh": "已由知识机器解读：进阶版末尾有写给论文作者的一节——可以往哪里走，档案库里附近有什么。",
}


def km_badge_html(article, lang, date_str, version):
    """Значок «разобрано машиной знаний» у заголовка статьи.

    Владелец 11 августа: «пометить работы, где это выполнено, рядом с названием плюсиком;
    плюсик виден во ВСЕХ версиях и списках, тултип с объяснением, при нажатии — переход
    на рекомендации». Отсюда две особенности: значок рисуется на любом уровне чтения, а
    ведёт всегда в продвинутую версию — раздел живёт только там.
    """
    if not (article.get("recommend") or {}).get(lang) and \
       not (article.get("recommend") or {}).get(DEFAULT_LANG):
        return ""
    tip = _KM_BADGE_TIP.get(lang, _KM_BADGE_TIP["en"])
    href = ("#km-advice" if version == "advanced"
            else f'/{LANG_DIR}/{lang}/archive/{date_str}/{article["id"]}/advanced.html#km-advice')
    return (f'<a class="km-badge" href="{attr_safe(href)}" title="{attr_safe(tip)}" '
            f'aria-label="{attr_safe(tip)}">✛</a>')


def _km_count(n, lang):
    """«4 разбора», а не «4 разборов». Число живёт внутри фразы, и склонение к нему
    прилагается: русский требует трёх форм, арабский — двойственного числа, английский
    и французский различают единственное. Строка «4 разборов рядом» выдаёт машину
    ровно в том разделе, который должен читаться как письмо коллеги."""
    if lang == "ru":
        n10, n100 = n % 10, n % 100
        if n10 == 1 and n100 != 11:
            w = "разбор"
        elif n10 in (2, 3, 4) and n100 not in (12, 13, 14):
            w = "разбора"
        else:
            w = "разборов"
        return f"{n} {w}"
    if lang == "ar":
        if n == 1:
            return "تحليل واحد"
        if n == 2:
            return "تحليلان"
        return f"{n} تحليلات" if n <= 10 else f"{n} تحليلًا"
    if lang == "zh":
        return f"{n} 篇解读"
    one, many = {"en": ("review", "reviews"), "es": ("análisis", "análisis"),
                 "fr": ("analyse", "analyses")}.get(lang, ("review", "reviews"))
    return f"{n} {one if n == 1 else many}"


def knowledge_advice_html(article, lang):
    """Раздел «Взгляд машины знаний» — рекомендации АВТОРУ разобранной работы.

    Владелец 10 августа: «к каждой статье при полном разборе давай на основе ML
    рекомендации… отдельное описание, что автор видел, что и как сделано, потом
    структурированно наши мысли, ссылки, заключения — всё только позитивное: куда
    двигаться дальше, в чём сила, какие идеи можно апробировать, как найти где бурить
    новую скважину».

    Содержание готовит `tools/recommend.py`: соседей ищет вектор, формулирует модель, но
    каждое направление обязано опираться на конкретную статью архива — и она названа
    ссылкой. Раздела нет, пока опоры нет: пустой блок «рекомендаций» хуже отсутствия.

    Вёрстка берётся у разбора авторских работ (`.aw-review`/`.aw-card`) — те же карточки,
    тот же ритм. Своя вёрстка рядом с общей 8 августа уже кончилась переделкой.
    """
    rec_all = article.get("recommend") or {}
    rec = rec_all.get(lang) or (rec_all.get("ru") if lang == DEFAULT_LANG else None)
    if not rec or not rec.get("directions"):
        return ""
    t = _KM.get(lang, _KM["en"])
    by_id = {n["id"]: n for n in (rec.get("neighbours") or []) if n.get("id")}

    def link(aid):
        n = by_id.get(aid)
        if not n:
            return ""
        title = (n.get("titles") or {}).get(lang) or (n.get("titles") or {}).get("ru") or aid
        # Читатель уже на продвинутом уровне — уводить его на популярный значит терять
        # глубину на ровном месте (владелец 11 августа). Ведём в продвинутую версию, но
        # только если она у соседа настоящая: у экспресса там баннер «полная готовится».
        # У записей до 11 августа поля full нет — считаем, что полной версии не обещали.
        page = "advanced.html" if n.get("full") else "index.html"
        href = f'/{LANG_DIR}/{lang}/archive/{n["date"]}/{aid}/{page}'
        return f'<a href="{attr_safe(href)}">{safe(title)}</a>'

    def meta(n):
        """Код работы и дата публикации — «паспорт» соседа той же строкой, что и в ленте."""
        aid = n.get("id") or ""
        code = (f'<a class="km-arxiv" href="https://arxiv.org/abs/{attr_safe(aid)}" '
                f'target="_blank" rel="noopener">arXiv:{safe(aid)}</a>'
                if re.match(r"^\d{4}\.\d{4,5}", aid) else f'<span class="km-arxiv">{safe(aid)}</span>')
        # Честная пометка: у экспресса разобрана только авторская аннотация. Читатель по
        # ссылке должен знать заранее, насколько глубоко мы туда заглядывали.
        mark = ("" if n.get("full") else
                f'<span class="km-express">'
                f'{safe({"ru": "экспресс", "en": "express", "es": "exprés", "fr": "express", "ar": "سريع", "zh": "速览"}.get(lang, "express"))}</span>')
        return (f'<span class="km-meta">{code}'
                f'<span class="km-date">{safe(n.get("date", ""))}</span>{mark}</span>')

    cards = []
    if rec.get("seen"):
        cards.append(f'<div class="aw-card"><p class="aw-card-l">{safe(t["seen"])}</p>'
                     f'<p>{safe(rec["seen"])}</p></div>')
    if rec.get("strength"):
        cards.append(f'<div class="aw-card aw-card-plus"><p class="aw-card-l">'
                     f'{safe(t["strength"])}</p><p>{safe(rec["strength"])}</p></div>')
    items = []
    for x in rec["directions"]:
        srcs = [s for s in (link(a) for a in (x.get("based_on") or [])) if s]
        tail = (f'<span class="km-src">{safe(t["src"])} {" · ".join(srcs)}</span>'
                if srcs else "")
        items.append(f'<li>{safe(x["text"])}{tail}</li>')
    cards.append(f'<div class="aw-card aw-card-adv"><p class="aw-card-l">{safe(t["dirs"])}</p>'
                 f'<ul>{"".join(items)}</ul></div>')
    if rec.get("ideas"):
        li = "".join(f"<li>{safe(i)}</li>" for i in rec["ideas"])
        cards.append(f'<div class="aw-card"><p class="aw-card-l">{safe(t["ideas"])}</p>'
                     f'<ul>{li}</ul></div>')

    sig = ""
    if rec.get("significance"):
        sig = (f'<div class="km-sig"><p class="aw-card-l">{safe(t["sig"])}</p>'
               f'<p>{safe(rec["significance"])}</p></div>')
    links = ""
    if by_id:
        rows = "".join(
            f'<li><span class="km-link-main">{link(n["id"])}{meta(n)}</span>'
            f'<span class="km-score">{safe(t["near"])} {n.get("score", 0):.2f}</span></li>'
            for n in (rec.get("neighbours") or []) if n.get("id"))
        # Плотность окружения — честный сигнал «здесь уже топтались» / «здесь пусто».
        # Считается кодом при сборке рекомендаций, а не моделью: это измерение, а не мнение.
        fr = rec.get("frontier") or {}
        fr_html = ""
        if fr.get("nearest"):
            # Полосу выбрал recommend.py по откалиброванным порогам — страница её не
            # переизобретает. У старых записей поля band нет: там молчим, а не гадаем.
            phrase = t.get(fr.get("band") or "", "")
            if phrase:
                said = phrase.format(nn=_km_count(fr.get("dense", 0), lang),
                                     top=f'{fr["nearest"]:.2f}')
                fr_html = f'<p class="km-frontier">{safe(said)}</p>'
        links = (f'<div class="km-links"><p class="aw-card-l">{safe(t["links"])}</p>'
                 f'<ul>{rows}</ul>{fr_html}</div>')
    # Заголовок ведёт на страницу гида, где методика описана целиком. Владелец 11 августа:
    # «методику, которую мы используем, — ссылка на страницу; описание машины знаний
    # впоследствии превратится в полноценного чат-бота». Пока это раздел гида; когда
    # появится бот, менять придётся один адрес, а не разметку всех статей.
    about = f'/{LANG_DIR}/{lang}/about.html#km'
    return (f'<section class="aw-review km-advice" id="km-advice">'
            f'<h2><a class="km-about" href="{attr_safe(about)}">{safe(t["h"])}</a></h2>'
            f'<p class="aw-note">{safe(t["note"])}</p>'
            f'<div class="aw-cards">{"".join(cards)}</div>{sig}{links}</section>')


def gen_article_html(scipop, article, date_str, images, lang, version, captions=None, abstract=None,
                     has_mini=True):
    tpl = load_template("article")
    if not tpl.template: return "<html><body>Template not found</body></html>"
    # Аннотация СНЯТА С ПОКАЗА (решение владельца 2026-07-31): её промпт писал паспорт
    # статьи вместо человеческого текста, и это видел читатель. Данные не удаляем и не
    # перестаём считать — возвращаем показ строкой в config, когда промпт-инженер
    # переделает промпт и QA примет качество (см. задачи/промпты.md, разбор 07-31).
    abstract_text = abstract_for(abstract, lang, version) if config.get("show_abstract", False) else ""
    abstract_html = ""
    if abstract_text:  # аннотация из авторского абстракта — постоянно на виду, не по клику
        abstract_html = (f'<div class="abstract-lead"><div class="abstract-label">'
                         f'{safe(ABSTRACT_LABEL.get(lang, ABSTRACT_LABEL["en"]))}</div>'
                         f'<p>{safe(abstract_text)}</p></div>')

    loc = {
        "en": {"search": "Search articles, #tags, @authors", "hint": "# tag · @ author · ! scientist",
               "share": "Share", "next": "Next article",
               "license": "Original", "scientists": "Scientists:", "key_numbers": "Key numbers",
               "context": "Context", "methods": "Methods", "results": "Results",
               "implications": "Implications", "future_development": "Future development",
               "impact_on": "Impact", "next_steps": "Next steps",
               "key_problems_connection": "Key open problems",
               "author_verify_label": "I am the author",
               "author_verify_body": "Are you one of the authors of this paper? Email us from your institutional "
                                      "or work email address mentioning this article's arXiv ID and we'll verify "
                                      "you and give you edit access to this page."},
        "es": {"search": "Buscar artículos, #etiquetas, @autores", "hint": "# etiqueta · @ autor · ! científico",
               "share": "Compartir", "next": "Siguiente artículo",
               "license": "Original", "scientists": "Científicos:", "key_numbers": "Cifras clave",
               "context": "Contexto", "methods": "Métodos", "results": "Resultados",
               "implications": "Implicaciones", "future_development": "Desarrollo futuro",
               "impact_on": "Impacto", "next_steps": "Próximos pasos",
               "key_problems_connection": "Problemas abiertos clave",
               "author_verify_label": "Soy el autor",
               "author_verify_body": "¿Es usted uno de los autores de este trabajo? Escríbanos desde su correo "
                                      "institucional o profesional indicando el arXiv ID de este artículo: "
                                      "le verificaremos y le daremos acceso de edición a esta página."},
        "ru": {"search": "Поиск статей, #теги, @авторы", "hint": "# тег · @ автор · ! учёный",
               "share": "Поделиться", "next": "Следующая статья",
               "license": "Оригинал", "scientists": "Учёные:", "key_numbers": "Ключевые числа",
               "context": "Контекст", "methods": "Методы", "results": "Результаты",
               "implications": "Значение", "future_development": "Развитие",
               "impact_on": "Влияние", "next_steps": "Следующие шаги",
               "key_problems_connection": "Ключевые проблемы",
               "author_verify_label": "Я автор",
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
               "author_verify_label": "我是作者",
               "author_verify_body": "您是这篇论文的作者之一吗？请使用您的机构或工作邮箱给我们发邮件，注明这篇文章的 arXiv "
                                      "编号，我们将验证您的身份并授予您编辑此页面的权限。"},
        "fr": {"search": "Rechercher des articles, #tags, @auteurs", "hint": "# tag · @ auteur · ! scientifique",
               "share": "Partager", "next": "Article suivant",
               "license": "Original", "scientists": "Scientifiques :", "key_numbers": "Chiffres clés",
               "context": "Contexte", "methods": "Méthodes", "results": "Résultats",
               "implications": "Implications", "future_development": "Développements futurs",
               "impact_on": "Impact", "next_steps": "Prochaines étapes",
               "key_problems_connection": "Problèmes ouverts clés",
               "author_verify_label": "Je suis l'auteur",
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
               "author_verify_label": "أنا المؤلف",
               "author_verify_body": "هل أنت أحد مؤلفي هذا البحث؟ راسلنا من بريدك المؤسسي أو المهني مع ذكر رقم "
                                      "arXiv لهذا المقال، وسنتحقق منك ونمنحك صلاحية تحرير هذه الصفحة."}
    }.get(lang, {"search": "Search...", "hint": "# tag · @ author · ! scientist",
                 "share": "Share", "next": "Next article", "license": "Original",
                 "scientists": "Scientists:", "key_numbers": "Key numbers",
                 "context": "Context", "methods": "Methods", "results": "Results",
                 "implications": "Implications", "future_development": "Future development",
                 "author_verify_label": "I am the author",
                 "author_verify_body": "Are you one of the authors of this paper? Email us from your institutional "
                                        "or work email address mentioning this article's arXiv ID and we'll verify "
                                        "you and give you edit access to this page.",
                 "impact_on": "Impact", "next_steps": "Next steps",
                 "key_problems_connection": "Key open problems"})
    loc["min"] = {"ru": "мин", "en": "min", "es": "min", "zh": "分钟", "fr": "min", "ar": "دقيقة"}.get(lang, "min")
    loc["related_articles"] = {"ru": "Похожие статьи", "en": "Related articles", "es": "Artículos relacionados",
                               "zh": "相关文章", "fr": "Articles similaires", "ar": "مقالات ذات صلة"}.get(lang, "Related articles")
    loc["feedback_nav"] = {"ru": "Отклик", "en": "Feedback", "es": "Comentarios", "zh": "反馈",
                            "fr": "Retour", "ar": "التعليقات"}.get(lang, "Feedback")
    # №41 «Цитатные связи». Заголовок говорит ровно то, что есть: не «связанные работы»,
    # а «из того, что цитирует эта статья, мы разбирали вот это». Связь провёл автор
    # статьи, а не наш вектор, и подпись не должна присваивать нам чужую заслугу.
    loc["cited_ours"] = {"ru": "Из цитируемого мы разбирали",
                         "en": "From its references, we covered",
                         "es": "De sus referencias, analizamos",
                         "zh": "在其参考文献中，我们解读过",
                         "fr": "Parmi ses références, nous avons analysé",
                         "ar": "من مراجعها، تناولنا"}.get(lang, "From its references, we covered")
    loc["cited_ours_hint"] = {"ru": "ссылку поставил автор статьи, разбор — наш",
                              "en": "the link is the author’s, the write-up is ours",
                              "es": "el enlace es del autor, el análisis es nuestro",
                              "zh": "引用来自作者，解读来自我们",
                              "fr": "le lien vient de l’auteur, l’analyse est la nôtre",
                              "ar": "الإحالة من المؤلف، والتحليل منا"}.get(
        lang, "the link is the author’s, the write-up is ours")

    # "Следующая статья" — на ту же строку, что заголовок отклика (юзер-фидбек 2026-07-15:
    # "следующая статья поставить надо с отзывами, как раз на строку в которой было
    # написано как читается"), поэтому строится ЗДЕСЬ и передаётся внутрь build_feedback_html,
    # а не отдельным блоком в шаблоне.
    like_id = f"{article['id']}_{lang}_{version}"
    next_arrow = "←" if lang in RTL_LANGS else "→"
    # Нижняя кнопка «следующая статья» убрана совсем (юзер 2026-07-23) — верхняя переехала в
    # закреплённую строку с языками. Фидбэк больше не несёт next_button.
    feedback_html = build_feedback_html(like_id, lang, "article", inline_toggle=True)
    # Кнопка «+ комментарий» едет в строку лайков (.actions-compact), справа от реакций/шэра.
    comment_toggle_html = f'<button type="button" class="fb-comment-toggle actions-comment">{safe(feedback_comment_label(lang))}</button>'

    # ТЕГИ БЕРЁМ ИЗ ВЕКТОРА, если он посчитан (владелец 2026-08-09: «переходим целиком
    # на вектор, теги в промпте больше не гоняем»).
    #
    # Причина не в экономии, а в качестве. Из 368 тегов 159 не стояли ни у одной статьи:
    # модель, выбирая из списка в промпте, берёт знакомое и частое, а редкое и точное не
    # берёт никогда. Статья про мозг получала «энтропия, ГАЛАКТИКА, спектроскопия».
    # Вектор сравнивает смыслы — в ходу все 368, и связи стали честными.
    #
    # Откат: убрать tags_vec из data.json или вернуть строку ниже. Старые поля целы.
    tags = _display_tags(scipop)
    authors = article.get("authors", [])
    authors_html = ", ".join(
        (f'<a href="/{LANG_DIR}/en/authors/{attr_safe(author_slug(a))}.html" class="text-author-link" data-author="{attr_safe(a)}">{safe(a)}</a>'
         if any(c.isalpha() for c in a) else safe(a))  # мусорное "имя" (парсинг-артефакт без букв) — без ссылки, страницы для него нет
        for a in authors
    )
    # Законы — ПРЯМО ИЗ ВЕКТОРА, а не через общий тег.
    #
    # Прежнее правило цепляло закон к статье, если совпал хотя бы один тег: у закона
    # излучения Планка стоит «спектроскопия», и он приклеивался ко всему, где спектроскопия
    # хоть упомянута. Вектор сравнивает описание закона с текстом статьи напрямую.
    # Порог отсечения намеренно высокий: физического закона для статьи про языковые модели
    # не существует, и пустая колонка честнее принципа Паули в статье про трансформеры.
    # Треть статей остаётся без законов — это правда, а не пробел.
    laws_loc = load_laws_loc(lang)
    # tagset нужен и ниже, для подбора учёных по related_tags, — поэтому считаем его
    # здесь, а не внутри ветки отката. Убрав его вместе со старым блоком законов,
    # я уронил сборку всех статей: UnboundLocalError на первой же.
    tagset = set(tags)
    side_laws = []
    for lid in (scipop.get("laws_vec") or [])[:6]:
        ld = laws_loc.get(lid)
        if ld:
            side_laws.append((lid, ld.get("name", lid)))
    if not side_laws and not scipop.get("laws_vec"):
        # Вектор для статьи ещё не считался — старый путь через теги, чтобы страница
        # не осталась без связей до следующего прогона разметки.
        for lid, ld in laws_loc.items():
            if tagset & set(ld.get("tags", [])):
                side_laws.append((lid, ld.get("name", lid)))
            if len(side_laws) >= 6:
                break
    # Учёные статьи — через её теги (related_tags учёного) И через уже найденные законы
    # (их scientists/influenced_by) — тот же стандартный подход, что у законов выше.
    # Результат идёт ПЕРВЫМ в колонке (сверху тегов) — см. side_sci_html ниже.
    sci_ids_path = Path(f"lang/{DEFAULT_LANG}/data/scientists.json")
    all_sci = json.loads(sci_ids_path.read_text(encoding="utf-8")) if sci_ids_path.exists() else {}
    side_sci_ids = []
    for lid, _name in side_laws:
        ld = laws_loc.get(lid, {})
        for s in (ld.get("scientists") or []) + (ld.get("influenced_by") or []):
            if s in all_sci and s not in side_sci_ids:
                side_sci_ids.append(s)
    for sid, sdata in all_sci.items():
        if len(side_sci_ids) >= 6:
            break
        if sid in side_sci_ids:
            continue
        if tagset & set(sdata.get("related_tags", [])):
            side_sci_ids.append(sid)
    side_sci_ids = side_sci_ids[:6]

    # Мини-граф статьи — те же теги/законы/учёные, что уже в сайдбаре, но как несколько
    # центров сразу (мульти-BFS в js/mini-graph.js), тот же фирменный компонент, что и на
    # страницах тег/закон/учёный (юзер-фидбек 2026-07-15: "в статью добавить граф... готовый
    # фильтр класс будет везде фирменный подход"). Меньше 2 узлов — граф бессмысленен, не рисуем.
    # Считаем ДО nav_extra_items — пункт левого меню на граф добавляем, только если граф реально
    # будет на странице (юзер-фидбек 2026-07-15: "ссылка на отзыв тоже слева после графа").
    # Законы/учёные — приоритет над тегами при обрезке до 8: тегов у статьи обычно больше
    # (юзер-фидбек 2026-07-17: "учёные вообще не отображаются") — при tags-first порядке 8+ тегов
    # съедали весь лимит ДО того, как в список попадал хоть один закон/учёный.
    article_graph_ids = (
        [f"l:{lid}" for lid, _ in side_laws] + [f"s:{s}" for s in side_sci_ids] + [f"t:{t}" for t in tags]
    )[:8]
    article_graph_html = ""
    if len(article_graph_ids) >= 2:
        # Метка «Связи в графе знаний» убрана (юзер 2026-07-23: «и так понятно»), контрол глубины
        # теперь внутри фильтров справа. id-якорь для левого меню переехал на блок фильтров.
        article_graph_html = (
            f'<div id="article-graph" class="mini-graph-config">{mini_graph_filters_html(lang, "article")}</div>'
            f'<div class="mini-graph mini-graph--article" data-node="{attr_safe(",".join(article_graph_ids))}"><canvas id="minigraph"></canvas></div>'
        )

    # Пункты левого меню-навигатора, актуальные на ЛЮБОМ режиме (не только advanced) —
    # разделы статьи (context/methods/...) добавляются ниже отдельно, только когда они есть.
    # Порядок = порядок блоков на странице (граф стоит перед действиями/откликом в основном
    # потоке — см. article.html): граф (если есть) → отклик → похожие статьи.
    nav_extra_items = []
    # Первый пункт левого меню — короткое слово «наверх» со ссылкой к началу статьи
    # (юзер-фидбек 2026-07-22: не вставлять сам заголовок, просто слово + ссылка наверх).
    _top_lbl = {"ru": "↑ наверх", "en": "↑ top", "es": "↑ arriba", "ar": "↑ للأعلى",
                "fr": "↑ haut", "zh": "↑ 顶部"}.get(lang, "↑ top")
    nav_top_item = f'<li class="article-nav-home"><a href="#article-top">{safe(_top_lbl)}</a></li>'
    if article_graph_html:
        graph_nav_lbl = GRAPH_NAV_LABEL.get(lang, GRAPH_NAV_LABEL["en"])
        nav_extra_items.append(f'<li><a href="#article-graph">{safe(graph_nav_lbl)}</a></li>')
    nav_extra_items += [f'<li><a href="#feedback">{loc["feedback_nav"]}</a></li>',
                         f'<li><a href="#related">{loc["related_articles"]}</a></li>']

    if version in SIMPLE_LIKE or scipop.get("express_locked"):
        if scipop.get("text"):
            paragraphs = [p.strip() for p in re.split(r'\n\s*\n', scipop["text"]) if p.strip()]
            text_html = "".join(_render_paragraph(p, lang) for p in paragraphs)
        else:
            parts = [scipop.get(k, "") for k in ("context", "metaphor", "future")]
            text_html = "".join(f"<p>{parse_markers(p, lang)}</p>" for p in parts if p)
        key_numbers_html = ""
        nav_html = '<nav class="article-nav" id="section-nav"><ul>' + nav_top_item + '<li class="article-nav-sep"></li>' + "".join(nav_extra_items) + '</ul></nav>'
        formulas_html = render_formulas(scipop.get("formulas", []))
        fun_html = trivia_html(scipop.get("fun_fact", ""), scipop.get("scifi", ""), lang)
    else:
        sections = [
            ("context", loc["context"]), ("methods", loc["methods"]), ("results", loc["results"]),
            ("implications", loc["implications"]), ("future_development", loc["future_development"]),
            ("impact_on", loc["impact_on"]), ("next_steps", loc["next_steps"]),
            ("key_problems_connection", loc["key_problems_connection"])
        ]
        nav_html = '<nav class="article-nav" id="section-nav"><ul>' + nav_top_item + '<li class="article-nav-sep"></li>'
        text_html = ""
        for sid, slabel in sections:
            content = scipop.get(sid, "")
            if content:
                content = parse_markers(content, lang)
                nav_html += f'<li><a href="#{sid}">{slabel}</a></li>'
                text_html += f'<section id="{sid}"><h2>{slabel}</h2><p>{content}</p></section>'
        nav_html += '<li class="article-nav-sep"></li>' + "".join(nav_extra_items) + '</ul></nav>'

        formulas_html = render_formulas(scipop.get("formulas", []))
        kn = scipop.get("key_numbers", {})
        key_numbers_html = ""
        if kn:
            key_numbers_html = f'<div class="key-numbers"><h3>{safe(loc["key_numbers"])}</h3><ul>' + \
                               "".join(f"<li><strong>{k}:</strong> {sci_notation(v)}</li>" for k, v in kn.items()) + '</ul></div>'
        fun_html = trivia_html(scipop.get("fun_fact", ""), scipop.get("scifi", ""), lang)

    # Хвост продвинутой версии — общий для обеих веток выше. У экспресса продвинутый уровень
    # идёт по ветке SIMPLE_LIKE (там баннер «полная готовится»), но оригинальную аннотацию
    # владелец просил и там: экспресс из неё как раз и сделан.
    #
    # Порядок: сначала наш разбор, потом слово машины знаний автору, потом первоисточник
    # мелким шрифтом. Владелец 11 августа про аннотацию: «не обязательно в первом абзаце,
    # мелким текстом, во вторую очередь».
    if version == "advanced":
        tail_nav = ""
        km_html = knowledge_advice_html(article, lang)
        if km_html:
            tail_nav += f'<li><a href="#km-advice">{safe(_KM.get(lang, _KM["en"])["nav"])}</a></li>'
            text_html += km_html
        orig_html = original_abstract_html(article, lang)
        if orig_html:
            lbl = _ORIG_ABS.get(lang, _ORIG_ABS["en"])[0]
            tail_nav += f'<li><a href="#orig-abstract">{safe(lbl)}</a></li>'
            text_html += orig_html
        if tail_nav:
            # Пункты встают перед последним разделителем — то есть в группу разделов статьи,
            # а не к служебным ссылкам внизу меню. Меню к этому месту уже собрано строкой
            # в обеих ветках, поэтому вставляем по образцу, а не пересобираем.
            anchor = '<li class="article-nav-sep"></li>' + "".join(nav_extra_items)
            if anchor in nav_html:
                nav_html = nav_html.replace(anchor, tail_nav + anchor, 1)

    if scipop.get("express_locked"):
        # Показываем баннер сверху текста: "показана версия X, Y пока не готова" — текст уже
        # реальный (тот же, что и у X), не generic-заглушка (см. express_locked_scipop).
        avail = [v for v in ("popular", "simple", "mini") if v in (article.get("express_tiers") or [])]
        if avail:
            target = avail[0]
            shown_name = (MINI_VERSION_LABEL.get(lang, MINI_VERSION_LABEL["en"]) if target == "mini"
                          else version_label(target, lang))
            locked_name = (MINI_VERSION_LABEL.get(lang, MINI_VERSION_LABEL["en"]) if version == "mini"
                           else version_label(version, lang))
            banner_tpl = EXPRESS_LOCKED_BANNER.get(lang, EXPRESS_LOCKED_BANNER["en"])
            banner_html = f'<p class="express-locked-banner">{banner_tpl.format(shown=shown_name, locked=locked_name)}</p>'
            text_html = banner_html + text_html

    # AI-обложка (ai.jpg) идёт ПЕРВЫМ кадром галереи, а не отдельным блоком сверху (юзер-фидбек
    # 2026-07-20: "AI картинки первые, отдельную первую убрать"). Отдельного .ai-cover больше нет.
    ai_jpg = Path(LANG_DIR) / DEFAULT_LANG / "archive" / date_str / article["id"] / "ai.jpg"
    ai_url = f'/{LANG_DIR}/{DEFAULT_LANG}/archive/{date_str}/{article["id"]}/ai.webp' if ai_jpg.exists() else None
    mosaic_html = gen_mosaic(images, article["id"], date_str, captions, cover_url=ai_url)
    ai_cover_html = ""
    tags_side_html = gen_tags_side(tags, lang)
    # Заглушка непереведённой статьи умеет не только извиняться: очередь заказов уже принимает
    # kind=translate, поэтому читателю предлагаем перевести прямо сейчас. Блок пуст на переведённых
    # страницах — там предлагать нечего.
    translate_offer_html = ""
    if scipop.get("untranslated"):
        translate_offer_html = (
            f'<div class="translate-offer" data-arxiv-id="{attr_safe(article["id"])}" '
            f'data-to="{attr_safe(lang)}"></div>')

    if tags_side_html:
        tags_lbl = SIDE_TAGS_LABEL.get(lang, SIDE_TAGS_LABEL["en"])
        tags_side_html = f'<div class="side-tags-label">{safe(tags_lbl)}</div>' + tags_side_html
    side_sci_html = ""
    if side_sci_ids:
        sci_lbl = SIDE_SCI_LABEL.get(lang, SIDE_SCI_LABEL["en"])
        side_sci_html = (f'<div class="side-sci-label">{safe(sci_lbl)}</div>' + "".join(
            f'<a href="/{LANG_DIR}/{lang}/scientists/{attr_safe(author_slug(s))}.html" class="side-sci" '
            f'data-scientist="{attr_safe(s)}">{safe(all_sci[s].get("name", s))}</a>' for s in side_sci_ids))
    tags_side_html = side_sci_html + tags_side_html
    if side_laws:
        lbl = SIDE_LAWS_LABEL.get(lang, SIDE_LAWS_LABEL["en"])
        tags_side_html += (f'<div class="side-laws-label">{safe(lbl)}</div>' + "".join(
            f'<a href="/{LANG_DIR}/{lang}/laws/{attr_safe(lid)}.html" class="side-law" '
            f'data-law="{attr_safe(lid)}">{safe(name)}</a>' for lid, name in side_laws))

    page_file = VERSION_FILES[version]
    version_toggle_html = ""   # бегунок заменён иконочным переключателем (2026-07-28)
    # Фаза 4: иконочный переключатель над названием + компактный дубль внизу статьи,
    # плюс карточка «коротко» шапкой (решения владельца 2026-07-27).
    # «Мини» показываем, только если mini.html для этой статьи действительно пишется: у экспресс-
    # статьи без короткого текста его нет, а кнопка стояла всегда и вела в 404 (нашли 2026-07-29).
    level_switch_html = level_switch_links(lang, version, date_str, article["id"], with_mini=has_mini)
    level_switch_bottom_html = level_switch_links(lang, version, date_str, article["id"], compact=True)
    mini_head_html = mini_header_html((scipop.get("mini") or "").strip(), lang)
    # canonical — ОДИН на статью, на популярный уровень (index.html). Языковые
    # альтернативы описывает hreflang.
    #
    # Раньше каждый уровень указывал сам на себя, и поисковик получал четыре
    # самостоятельных документа с одним и тем же материалом. Итог виден в отчёте Google
    # за 8 августа: мы предъявили 46 662 адреса, проиндексировано 3 535 — семь процентов.
    # 39 500 страниц он даже не стал читать («обнаружена, не проиндексирована»), ещё 585
    # прочёл и отверг. Восемнадцать штук он сам склеил, решив за нас, какая версия главная.
    #
    # Теперь мини, просто и подробно ссылаются на популярный уровень: предъявляем 11 тысяч
    # страниц вместо 44, и вес четырёх версий сливается в одну вместо того, чтобы делиться
    # между ними. Читатель ничего не теряет — переключатель уровней работает как работал,
    # меняется только то, что мы говорим поисковику.
    canonical_url = f"{SITE_URL}/{LANG_DIR}/{lang}/archive/{date_str}/{article['id']}/index.html"
    # Собственный адрес страницы всё равно нужен: для og:url и структурированных данных
    # правильнее показывать именно ту страницу, которую человек открыл.
    page_url = f"{SITE_URL}/{LANG_DIR}/{lang}/archive/{date_str}/{article['id']}/{page_file}"

    cats = article.get("categories", [])
    categories_html = ""
    if cats:
        # Каждый раздел — ссылка на свою страницу /sections/<slug>.html (юзер-фидбек 2026-07-20:
        # "со статьи должна вести ссылка в раздел"; показываем ВСЕ разделы статьи, не только один).
        badges = " ".join(
            f'<a class="cat-badge" href="/{LANG_DIR}/{lang}/sections/{section_slug(c)}.html" '
            f'data-cat="{c}" title="{attr_safe(cat_desc(c, lang))}">'
            f'{safe(cat_name(c, lang))}</a>' for c in cats[:5])
        # Разделы — на своей строке (юзер 2026-07-23), поэтому без ведущей «·».
        categories_html = badges

    lic = article.get("license_url", "")
    lic_name = article.get("license_name") or license_label(lic)
    # Признак «собственный разбор» (владелец 18.08: «ставим определённый признак и
    # объясняем, почему это легально»). У NC/ND-работ рядом с лицензией — плашка с
    # пояснением в подсказке: наш текст оригинален, авторский материал не воспроизводится.
    license_note_html, author_takedown_html = "", ""
    if article.get("license_class") == "analysis":
        note = _ANALYSIS_NOTE.get(lang, _ANALYSIS_NOTE["en"])
        license_note_html = (f' · <span class="lic-analysis" title="{attr_safe(note)}">'
                             f'{safe(_ANALYSIS_BADGE.get(lang, _ANALYSIS_BADGE["en"]))}</span>')
        # Кнопка снятия (владелец 18.08: «я автор — снять с публикации, после подтверждения»).
        # Письмо с рабочего адреса и есть подтверждение личности: снимаем руками после
        # проверки, автомат ничего не удаляет. Живёт в модалке «Я автор» — u автора одна
        # дверь на все вопросы.
        td = _TAKEDOWN.get(lang, _TAKEDOWN["en"])
        author_takedown_html = (
            f'<hr><p>{safe(td["body"])}</p>'
            f'<p><a class="takedown-link" href="mailto:author@bridge42worlds.academy'
            f'?subject=Takedown%20request%20-%20{attr_safe(article.get("id", ""))}">'
            f'{safe(td["btn"])}</a></p>')

    # hreflang ведёт на index.html каждого языка, а не на текущий уровень: языковые
    # альтернативы обязаны указывать на канонические адреса, иначе поисковик отбрасывает
    # всю связку целиком. Раньше mini.html ссылался на mini.html соседних языков — то есть
    # на страницы, которые сами каноническими не являются.
    hreflang_links = "\n    ".join(
        f'<link rel="alternate" hreflang="{l}" href="{SITE_URL}/{LANG_DIR}/{l}/archive/{date_str}/{article["id"]}/index.html">'
        for l in LANGUAGES
    ) + f'\n    <link rel="alternate" hreflang="x-default" href="{SITE_URL}/{LANG_DIR}/{DEFAULT_LANG}/archive/{date_str}/{article["id"]}/index.html">'

    rmin = reading_minutes(scipop)
    reading_html = f'<span class="reading-time"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12.5" r="7.6"/><path d="M12 8.4V12.6L15 14.6"/></svg> {rmin} {safe(loc.get("min", "min"))}</span>'
    jsonld_html = build_jsonld(scipop, article, date_str, lang, canonical_url, abstract_for(abstract, lang, "advanced"))

    # ── АВТОРСКАЯ РАБОТА ──────────────────────────────────────────────────────
    # Работа, присланная автором, — такая же статья, тем же шаблоном и тем же кодом.
    # Отличий ровно три, и все три приходят ДАННЫМИ, а не отдельной вёрсткой (владелец
    # 2026-08-08: «такая же статья, максимум ещё ссылки, объяснения и так далее, но всё
    # то же самое, просто другой источник, и всё»).
    source_meta_html = (f'arXiv:<a href="https://arxiv.org/abs/{attr_safe(article["id"])}" '
                        f'target="_blank" rel="noopener">{safe(article["id"])}</a>')
    author_work_badges = ""
    review_block_html = ""
    if article.get("author_work"):
        source_meta_html = author_work_sources(article, lang)
        author_work_badges = author_work_badges_html(article, lang)
        review_block_html = author_work_review_html(article, lang)

    return tpl.substitute(
        source_meta_html=source_meta_html, author_work_badges=author_work_badges,
        review_block_html=review_block_html,
        author_work_files_html=author_work_files_html(article, lang),
        lang=lang, dir=dir_for(lang), site_name=SITE_NAME, site_url=SITE_URL, goatcounter=GOATCOUNTER,
        authors_lang="en", asset_ver=asset_ver(),
        clickbait=safe(scipop.get("title", article["title"])),
        og_title=safe(og_title_for(scipop, article, lang)),
        og_image_html=article_og_image_html(date_str, article["id"]),
        clickbait_escaped=safe(scipop.get("title", "").replace("'", "\\'")),
        km_badge=km_badge_html(article, lang, date_str, version),
        refine_badge=(f'<span class="refine-badge" title="{safe({"ru": "Отшлифовано редактором", "en": "Polished by an editor", "es": "Pulido por un editor", "ar": "تم صقله بواسطة محرر", "fr": "Peaufiné par un éditeur", "zh": "编辑润色"}.get(lang, "Polished by an editor"))}">✦</span>' if article.get("refined") else ""),
        express_badge=(f'<span class="express-badge" title="{safe({"ru": "Экспресс-версия: по аннотации автора, без разбора полного текста статьи", "en": "Express version: based on the author\'s abstract, not the full paper text", "es": "Versión exprés: basada en el resumen del autor, no en el texto completo", "ar": "نسخة سريعة: بناءً على ملخص المؤلف، دون تحليل النص الكامل", "fr": "Version express : basée sur le résumé de l\'auteur", "zh": "速览版：基于作者摘要"}.get(lang, "Express version: based on the abstract"))}">{safe({"ru": "экспресс", "en": "express", "es": "exprés", "ar": "سريع", "fr": "express", "zh": "速览"}.get(lang, "express"))}</span>' if article.get("express") else ""),
        original_title=safe(article["title"]),
        oneliner=safe(scipop.get("oneliner", "")),
        oneliner_short=safe(scipop.get("oneliner", "")[:160]),
        oneliner_og=safe(scipop.get("oneliner", "")[:200]),
        description=safe(card_cut(scipop.get("description", scipop.get("oneliner", "")))),
        id=article["id"], date=date_str,
        like_id=like_id,
        version_toggle_html=version_toggle_html,
        level_switch_html=level_switch_html,
        level_switch_bottom_html=level_switch_bottom_html,
        mini_head_html=mini_head_html,
        authors_full=authors_html,
        search_placeholder=safe(loc.get("search", "")),
        search_hint=safe(loc.get("hint", "# tag · @ author · ! scientist")),
        author_verify_label=safe(loc.get("author_verify_label", "I am the author — verify & edit")),
        author_verify_body=safe(loc.get("author_verify_body", "")),
        share_label=safe(loc.get("share", "Share")),
        comment_toggle_html=comment_toggle_html,
        next_label=safe(loc.get("next", "Next article")),
        next_arrow="←" if lang in RTL_LANGS else "→",
        express_locked_js="true" if scipop.get("express_locked") else "false",
        license_label=safe(loc.get("license", "Original")),
        license_url=lic, license_name=lic_name, license_note_html=license_note_html,
        author_takedown_html=author_takedown_html,
        canonical_url=canonical_url, page_url=page_url, hreflang_links=hreflang_links,
        tags_side_html=tags_side_html, article_graph_html=article_graph_html,
        mosaic_html=mosaic_html, ai_cover_html=ai_cover_html,
        abstract_html=abstract_html,
        translate_offer_html=translate_offer_html,
        feedback_html=feedback_html,
        nav_html=nav_html, text_html=text_html,
        formulas_html=formulas_html, key_numbers_html=key_numbers_html,
        fun_fact_html=fun_html,
        reading_html=reading_html, jsonld_html=jsonld_html,
        related_label=safe(loc.get("related_articles", "Related articles")),
        cited_ours_label=safe(loc["cited_ours"]), cited_ours_hint=safe(loc["cited_ours_hint"]),
        categories_html=categories_html,
        fav_title=safe(nav_fav_title(lang)),
        like_title=safe(reaction_titles(lang)["like"]),
        dislike_title=safe(reaction_titles(lang)["dislike"]),
        superlike_title=safe(reaction_titles(lang)["superlike"]),
        fav_label=safe(ACTIONS_LOC.get(lang, ACTIONS_LOC["en"])),
    )


# ── Data.json ──

_TAGS_REGISTRY = None


def _tags_registry():
    """Множество зарегистрированных понятий — из data/concepts.json, один раз на прогон.

    С 18.08 источник правды — единый реестр (решение владельца: одна классификация).
    Для валидации разметки это не косметика: витрина тегов знает 363 понятия, реестр —
    535, и закон, размеченный в тексте как [tag:hawking_radiation], по витрине выглядел
    бы незарегистрированным. Витрина остаётся запасным путём, пока слой совместимости
    не прогнан везде.
    """
    global _TAGS_REGISTRY
    if _TAGS_REGISTRY is None:
        try:
            reg = json.loads(Path("data/concepts.json").read_text(encoding="utf-8"))
            ids = set((reg.get("concepts") or {}).keys())
            if ids:
                _TAGS_REGISTRY = ids
                return _TAGS_REGISTRY
        except Exception:
            pass
        try:
            g = json.loads(Path("data/tags-graph.json").read_text(encoding="utf-8"))
            _TAGS_REGISTRY = set((g.get("graph") or {}).keys())
        except Exception:
            # Реестр не прочитался — валидация невозможна. Пропускаем ВСЁ и говорим об
            # этом: молча пропустить хуже, но молча выбросить все теги ещё хуже.
            print("    ⚠️ ни concepts.json, ни tags-graph.json не прочитались — валидация тегов пропущена")
            _TAGS_REGISTRY = None
            return set()
    return _TAGS_REGISTRY if _TAGS_REGISTRY is not None else set()


def save_data_json(versions_ru, article, date_str, folder, translations=None, captions=None, abstract=None, refined=False):
    """versions_ru: {version: scipop_ru}; translations: {version: {lang: scipop}};
    abstract: {lang: текст} — «Аннотация» из авторского arXiv-abstract (версионно-независимо).
    Пишет по ключу на каждую версию (popular/simple/advanced), плюс мета и подписи к картинкам."""
    translations = translations or {}
    scipop_adv = versions_ru.get("advanced", {})
    # ── Валидация тегов НА ЗАПИСИ, а не в чистильщике ────────────────────────────
    # Аудит 16 августа: 5 незарегистрированных тегов за месяц выросли в 505 на 189
    # статьях, 108 статей ссылались на несуществующие страницы тегов (живые 404).
    # Чистка вдогонку не работает на корпусе, растущем на тысячи в неделю: пока
    # чистишь старое, генератор пишет новое. Кран закрывается только здесь — в
    # единственной точке, где тег впервые попадает в data.json.
    #
    # Незнакомый тег НЕ выбрасывается молча: он уходит в tags_unverified — кандидаты
    # для пополнения словаря (доменные облака, задача №20). Молча выбросить значило бы
    # потерять сигнал «словарь отстал от корпуса», а это ровно тот сигнал, по которому
    # словарь и должен расти.
    _known_tags = _tags_registry()
    _raw_tags = [t for t in ([scipop_adv.get("main_tag", "")] + scipop_adv.get("extra_tags", [])) if t]
    if _known_tags:
        _ok_tags = [t for t in _raw_tags if t in _known_tags]
        _bad_tags = [t for t in _raw_tags if t not in _known_tags]
    else:
        _ok_tags, _bad_tags = _raw_tags, []
    if _bad_tags:
        print(f"    🏷️ теги вне реестра (в tags_unverified): {', '.join(_bad_tags[:5])}")
    payload = {
        "id": article["id"], "original_title": article["title"],
        "authors": article.get("authors", []), "date": date_str,
        "license": article.get("license_url", ""),
        "license_name": article.get("license_name") or license_label(article.get("license_url", "")),
        **({"license_class": article["license_class"]} if article.get("license_class") else {}),
        "tags": _ok_tags,
        **({"tags_unverified": _bad_tags} if _bad_tags else {}),
        "laws": scipop_adv.get("laws", []),
        "main_tag": scipop_adv.get("main_tag", ""),
        "scientists": scipop_adv.get("scientists", []),
        "categories": article.get("categories", []),
        "primary_category": article.get("primary_category", ""),
        "cited_arxiv": article.get("cited_arxiv", []),
        "threads": (versions_ru.get("popular", {}).get("threads", "") or "")[:480],
        "abstract": abstract or {},
        "abstract_v": ABSTRACT_PROMPT_V,   # каким промптом сделана — см. константу
        "thumbs": article.get("thumbs", 0),
        "refined": refined,
        "express": article.get("express", False),
        "express_tiers": article.get("express_tiers", []),
    }
    # Поле пишет covers_full.py задним числом; при пересоздании статьи build_article проносит его
    # через article — иначе regen молча терял и поле, и с ним защиту FLUX-обложки от затирания.
    if article.get("image_model"):
        payload["image_model"] = article["image_model"]
    if article.get("upgraded"):
        payload["upgraded"] = article["upgraded"]
    has_captions = any(captions.values()) if isinstance(captions, dict) else bool(captions)
    if has_captions:
        payload["captions"] = captions
    for v in VERSIONS:
        vdata = {DEFAULT_LANG: versions_ru.get(v, {})}
        vdata.update(translations.get(v, {}))
        payload[v] = vdata
    (folder / "data.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Indexes ──
_MARKER_RE = re.compile(r'\[(?:tag:[^\]]+|/tag|scientist:[^\]]+|/scientist|law:[^\]]+|/law|callout|/callout)\]')


def strip_markers(s):
    """Убирает разметку [tag:..]/[scientist:..]/[callout] для карточек/индекса, оставляя внутренний текст."""
    return _MARKER_RE.sub('', s or '')


# Индекс статей — ОДИН РАЗ НА ЯЗЫК, из памяти.
#
# Шесть мест собирали страницы (тег, закон, учёный, раздел, автор, облако) и каждое читало
# lang/<lang>/articles-index.json с диска заново. В одном прогоне индекс сначала переписывается,
# а потом читается — и если чтение попадает в момент записи, файл виден пустым: json падает
# с «Expecting value: line 1 column 1», сборка обрывается на середине, а часть страниц остаётся
# от прошлого поколения. Именно отсюда бралась «каша» из страниц разных поколений, которую
# владелец видел 2026-08-02, — и она же трижды за день роняла прогон.
#
# Чтение из памяти убирает гонку по устройству, а не по везению: файл читается один раз,
# до записи, и все страницы видят один и тот же снимок. Побочно это и в разы быстрее:
# индекс на 6,8 МБ разбирался заново для каждой из 42 тысяч страниц.
_INDEX_CACHE = {}


def load_index(lang):
    if lang not in _INDEX_CACHE:
        p = Path(LANG_DIR) / lang / "articles-index.json"
        try:
            _INDEX_CACHE[lang] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
        except json.JSONDecodeError:
            # Файл в этот момент пишется другим шагом — не роняем сборку из-за момента.
            print(f"    ⚠️ индекс {lang} читается в момент записи — беру пустой на этот проход")
            _INDEX_CACHE[lang] = []
    return _INDEX_CACHE[lang]


def drop_index_cache(lang=None):
    """Сбросить снимок после перезаписи индексов (rebuild_indexes)."""
    if lang:
        _INDEX_CACHE.pop(lang, None)
    else:
        _INDEX_CACHE.clear()


_POW_RE = re.compile(r"10\^\{?(-?\d+)\}?")
_EXP_RE = re.compile(r"(\d+(?:[.,]\d+)?)[eE]([+-]?\d+)")


def sci_notation(v):
    """Порядки величин — типографикой, а не «10^{11}» сырьём.

    Владелец 2026-08-05: «в физике используют порядки, надо показывать их формулой — это
    будет профессионально». Ключевые числа приходят от модели строками вида «~10^{11} ГэВ»
    или «3.5e-9 м» — на странице это выглядело как черновик. KaTeX сюда тащить незачем:
    степень делается обычным <sup>, работает без скриптов и в RSS."""
    s = str(v)
    s = _EXP_RE.sub(lambda m: f"{m.group(1)}·10<sup>{int(m.group(2))}</sup>", s)
    s = _POW_RE.sub(lambda m: f"10<sup>{m.group(1)}</sup>", s)
    return s


def _display_sci(scipop):
    """Учёные статьи: сначала выведенные машиной знаний (scientists_vec), иначе прежние.

    Владелец 2026-08-18: «учёные должны быть связаны с законами автоматом, это отдельный
    процесс». Список имён убран из промптов; привязку считает tag_by_vector по законам и
    понятиям статьи. Пока по статье нет расчёта — показываем то, что стояло раньше,
    чтобы связи не пропали на время перехода.
    """
    return [x for x in (scipop.get("scientists_vec") or []) if x] or scipop.get("scientists", [])


def _display_tags(scipop):
    """Теги статьи для показа и индекса: вектор, с откатом на прежние.

    Одна функция на все места, где теги нужны, — иначе страница и лента расходятся,
    и заметить это можно только глазами, случайно.
    """
    vec = [x for x in (scipop.get("tags_vec") or []) if x]
    # Мало тегов — значит вектор НЕ УВЕРЕН, и верить ему нельзя.
    #
    # Порог отбора один на всех, поэтому у статьи с уверенной привязкой набирается шесть
    # тегов, а у сомнительной — два-три: близость едва переваливает за порог. Живой случай
    # 10 августа: авторская работа про MEMS-акселерометры получила «большие языковые модели»
    # и «рекуррентные нейросети» — TF-IDF зацепился за общие слова «данные» и «модель»,
    # потому что своего текста у работы всего три тысячи знаков. Прежние теги из промпта
    # там были точные: обработка сигналов, спектральный анализ.
    #
    # Так что три тега и меньше — это не разметка, а шум. Берём прежние.
    if len(vec) >= 4:
        return vec
    return [x for x in [scipop.get("main_tag", "")] + (scipop.get("extra_tags") or []) if x]


def _card_text(scipop, limit=420):
    """Текст для карточки в ленте: начало простого изложения.

    Порядок отката не случаен. Простой текст — то, ради чего человек и приходит; если его
    нет (у экспресса без simple), берём популярный; только потом справочное description,
    и в самом конце однострочник. Пустой карточки не бывает.
    """
    body = ""
    for k in ("text", "description", "oneliner"):
        v = (scipop.get(k) or "").strip()
        if v:
            body = v
            break
    return card_cut(body, limit)


def card_cut(s, limit=300):
    """Обрез для карточки — по границе ПРЕДЛОЖЕНИЯ, а не по счётчику символов.

    Жёсткое [:300] обрывало текст посреди слова («…при определённых условиях становят»),
    и читатель видел кашу вместо законченной мысли — владелец поймал это на главной
    2026-08-02: «текст как бы оборван, а должен быть чёткий компактный законченный».
    Берём столько ЦЕЛЫХ предложений, сколько влезает в лимит; если первое же предложение
    длиннее лимита — режем по последнему слову с многоточием: лучше честное многоточие,
    чем обрубок слова."""
    s = (s or "").strip()
    if len(s) <= limit:
        return s
    cut = s[:limit]
    # последняя граница предложения в пределах лимита
    best = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "),
               cut.rfind(".\n"), len(cut) - 1 if cut.endswith(('.', '!', '?')) else -1)
    if best > limit // 3:          # нашли границу не слишком близко к началу
        return s[:best + 1].strip()
    sp = cut.rfind(" ")
    return (cut[:sp] if sp > 0 else cut).rstrip(",;:—- ") + "…"


def update_index(scipop, article, date_str, lang, version, abstract=""):
    base = Path(LANG_DIR) / lang
    base.mkdir(parents=True, exist_ok=True)
    filename = VERSION_INDEX[version]
    ip = base / filename
    idx = json.loads(ip.read_text(encoding="utf-8")) if ip.exists() else []
    idx = [x for x in idx if x.get("id") != article["id"]]
    url = f"/{LANG_DIR}/{lang}/archive/{date_str}/{article['id']}/{VERSION_FILES[version]}"
    idx.append({
        "id": article["id"], "version": version,
        # express_locked_scipop больше не подменяет title заглушкой (юзер-фидбек 2026-07-17) —
        # scipop["title"] всегда настоящий, локked-тиры отличаются только express_locked-баннером.
        "title": scipop.get("title", article["title"]),
        "oneliner": card_cut(strip_markers(scipop.get("oneliner", ""))),
        # В карточку идёт НАЧАЛО ПРОСТОГО ТЕКСТА, а не поле description.
        #
        # description пишется как справка и звучит соответственно: «у ядер-близнецов число
        # протонов и нейтронов меняется местами, физики использовали разницу радиусов, чтобы
        # прощупать тензорные силы». Термины, ни одного образа. А простой текст той же статьи
        # начинается так: «в атомном ядре протоны и нейтроны упакованы так плотно, что между
        # ними действуют силы, напоминающие туго натянутые пружины».
        #
        # Владелец 2026-08-09: «в карточку списка — простой понятный текст». Карточка — первое,
        # что человек видит в ленте, и по ней решает, читать ли дальше. Справкой не заманишь.
        "description": strip_markers(_card_text(scipop)),
        # abstract, threads и thumbs из индекса УБРАНЫ. Замер 13 августа: индекс ленты
        # весит 9.9 МБ и качается при каждом заходе на главную, а три индекса уровней
        # вместе — 30 МБ. Из них abstract это 1.14 МБ, threads 0.47 МБ, thumbs не читает
        # никто вовсе. Единственное, для чего abstract использовался, — поиск по словам
        # (search.js), и там он давал совпадения по тексту, которого на карточке нет:
        # человек искал слово, получал статью и не понимал, при чём она.
        # Полный текст для поиска живёт в векторном индексе (Vectorize) — он для этого и
        # заведён, и он в облаке, а не в браузере читателя.
        "thumbs": article.get("thumbs", 0),
        "authors": article.get("authors", [])[:50], "date": date_str,  # до 50 — лента показывает ≤20, >20 разворачивает
        # Теги В ИНДЕКС — тоже из вектора. Я поправил показ на странице статьи и забыл
        # про индекс, а по нему живут лента, поиск и облако тегов: после полной пересборки
        # страницы были размечены по смыслу, а облако осталось прежним — 306 тегов вместо
        # 368 и те же 46% на десяти самых частых. Один источник правды, а не два.
        "tags": _display_tags(scipop),
        # Законы в индексе не было вовсе — на карточке их показать было нечем, хотя в data.json
        # они лежат с самого введения слоя «Законы». Владелец 2026-08-02: показывать на карточке
        # теги, учёных и законы в едином графическом ключе.
        # Законы в индексе — из вектора, как и на странице. Иначе карточка в ленте
        # покажет один набор, а страница другой.
        "laws": (scipop.get("laws_vec") or scipop.get("laws") or []),
        "scientists": _display_sci(scipop), "url": url,
        "reading": reading_minutes(scipop),
        "categories": article.get("categories", []),
        "primary_category": article.get("primary_category", ""),
        "express": article.get("express", False),
        # Значок «разобрано машиной знаний» в карточке ленты. Карточки рисует js/search.js
        # по этому индексу, а не сервер, — без флага здесь значок в списках не появится
        # ни при какой правке шаблонов.
        "km": bool((article.get("recommend") or {}).get(lang)
                   or (article.get("recommend") or {}).get(DEFAULT_LANG)),
    })
    write_json_atomic(ip, idx)


MAX_COAUTHORS = 30  # авторская страница показывает только первые 15 (см. generate_author_page) —
# без кэпа мега-коллаборации (сотни/тысячи авторов на статью, обычное дело в hep-ex/astro-ph)
# раздували authors-graph.json до 80+ МБ, которые целиком грузились на главной при каждом визите.


def update_authors_graph(article):
    ap = Path("data/authors-graph.json")
    graph = json.loads(ap.read_text(encoding="utf-8")) if ap.exists() else {}
    # Мусорные "авторы" (голая пунктуация — артефакт парсинга списка авторов, напр. одинокий
    # ":") ломали author_slug()/запись файла страницы автора — отсекаем на входе в граф.
    authors = [a for a in article.get("authors", []) if any(c.isalpha() for c in a)]
    for a in authors:
        if a not in graph: graph[a] = {"articles": [], "coauthors": [], "article_count": 0}
        if article["id"] not in graph[a]["articles"]:
            graph[a]["articles"].append(article["id"])
            graph[a]["article_count"] = len(graph[a]["articles"])
        for ca in authors:
            if len(graph[a]["coauthors"]) >= MAX_COAUTHORS:
                break
            if ca != a and ca not in graph[a]["coauthors"]: graph[a]["coauthors"].append(ca)
    write_json_atomic(ap, graph)   # 22 МБ граф авторов — самый крупный публикуемый файл


def update_tag_counts(scipop):
    """Счётчик статей и учёные тега — накапливаются по ходу генерации.

    Пишем В ОБА места: витрину (её читают страницы) и единый реестр понятий (он
    источник правды с 18.08). Иначе реестр отстаёт от жизни, а витрина, собранная из
    него слоем совместимости, откатывает счётчики назад — замер 18.08 показал
    расхождение уже через минуту после сборки реестра, на четырёх тегах.
    """
    ids = [t for t in [scipop.get("main_tag", "")] + scipop.get("extra_tags", []) if t]
    if not ids:
        return
    gp = Path("data/tags-graph.json")
    if gp.exists():
        graph = json.loads(gp.read_text(encoding="utf-8"))
        for t in ids:
            if t in graph.get("graph", {}):
                graph["graph"][t]["article_count"] = graph["graph"][t].get("article_count", 0) + 1
                if "scientists" not in graph["graph"][t]: graph["graph"][t]["scientists"] = []
                for s in _display_sci(scipop):
                    if s not in graph["graph"][t]["scientists"]: graph["graph"][t]["scientists"].append(s)
        write_json_atomic(gp, graph)
    cp = Path("data/concepts.json")
    if cp.exists():
        reg = json.loads(cp.read_text(encoding="utf-8"))
        node = reg.get("concepts") or {}
        for t in ids:
            if t in node:
                node[t]["article_count"] = node[t].get("article_count", 0) + 1
                sci = node[t].setdefault("scientists", [])
                for s in _display_sci(scipop):
                    if s not in sci: sci.append(s)
        write_json_atomic(cp, reg)


# ── Pages ──
def ensure_lang_structure(lang):
    base = Path(LANG_DIR) / lang
    for d in ["archive", "tags", "scientists"]: (base / d).mkdir(parents=True, exist_ok=True)
    generate_index_page(lang)
    generate_about_page(lang)
    if not (base / "articles-index.json").exists(): (base / "articles-index.json").write_text("[]", encoding="utf-8")


def generate_index_page(lang):
    tpl = load_template("index")
    if not tpl.template: return
    loc = {
        "en": {"search": "Search articles, #tags, @authors", "hint": "# tag · @ author · ! scientist",
               "loading": "Loading...", "footer": "science made simple",
               "intro": "bridge42worlds turns fresh arXiv preprints into articles anyone can read — every day, "
                        "no physics degree required. Pick your level: <b>Simple</b> for a first look, "
                        "<b>Popular</b> if science already excites you, <b>Advanced</b> for formulas and the full "
                        "story, <b>Mini</b> for the gist in 10 seconds. Plus a living map of science — the tags, "
                        "laws, and scientists behind every discovery."},
        "ru": {"search": "Поиск статей, #теги, @авторы", "hint": "# тег · @ автор · ! учёный", "loading": "Загрузка...",
               "footer": "наука простыми словами",
               "intro": "bridge42worlds превращает свежие научные препринты с arXiv в понятные тексты — каждый "
                        "день, без диплома физика. Выбирайте свой уровень: <b>Просто</b> — для первого знакомства, "
                        "<b>Популярно</b> — если наука уже увлекает, <b>Подробно</b> — с формулами и историей "
                        "открытия, <b>Мини</b> — если нужна только суть за 10 секунд. Плюс карта науки: связанные "
                        "темы, законы и учёные, которые за ними стоят."},
        "es": {"search": "Buscar artículos, #etiquetas, @autores", "hint": "# etiqueta · @ autor · ! científico",
               "loading": "Cargando...", "footer": "la ciencia simplificada",
               "intro": "bridge42worlds convierte los últimos preprints de arXiv en artículos que cualquiera puede "
                        "leer — cada día, sin necesidad de un título en física. Elige tu nivel: <b>Simple</b> para "
                        "una primera mirada, <b>Popular</b> si la ciencia ya te apasiona, <b>Avanzado</b> para "
                        "fórmulas e historia completa, <b>Mini</b> para la idea esencial en 10 segundos. Además, "
                        "un mapa vivo de la ciencia: las etiquetas, leyes y científicos detrás de cada descubrimiento."},
        "zh": {"search": "搜索文章、#标签、@作者", "hint": "# 标签 · @ 作者 · ! 科学家", "loading": "加载中...",
               "footer": "让科学变简单",
               "intro": "bridge42worlds 每天将 arXiv 上的最新科研预印本转化为通俗易懂的文章，无需物理学位。选择你的"
                        "难度：<b>简明</b>适合初次了解，<b>科普</b>适合对科学感兴趣的读者，<b>深入</b>提供公式与发现"
                        "历程，<b>迷你</b>10秒获取核心结论。还有一张不断生长的科学地图——标签、定律与背后的科学家。"},
        "fr": {"search": "Rechercher des articles, #tags, @auteurs", "hint": "# tag · @ auteur · ! scientifique",
               "loading": "Chargement...", "footer": "la science simplifiée",
               "intro": "bridge42worlds transforme les derniers prépublications arXiv en articles accessibles à "
                        "tous — chaque jour, sans diplôme de physique. Choisissez votre niveau : <b>Simple</b> pour "
                        "découvrir, <b>Populaire</b> si la science vous passionne déjà, <b>Avancé</b> pour les "
                        "formules et l'histoire complète, <b>Mini</b> pour l'essentiel en 10 secondes. Plus une "
                        "carte vivante de la science : tags, lois et scientifiques derrière chaque découverte."},
        "ar": {"search": "ابحث عن مقالات، #وسوم، @مؤلفين", "hint": "# وسم · @ مؤلف · ! عالم",
               "loading": "جارٍ التحميل...", "footer": "العلم ببساطة",
               "intro": "يحوّل bridge42worlds أحدث الأبحاث العلمية من arXiv إلى مقالات يفهمها الجميع - كل يوم، دون "
                        "الحاجة لشهادة في الفيزياء. اختر مستواك: <b>مبسّط</b> لأول نظرة، <b>شائع</b> إذا كان العلم "
                        "يثير شغفك، <b>متقدّم</b> للمعادلات والقصة كاملة، <b>مختصر</b> للخلاصة في 10 ثوانٍ. بالإضافة "
                        "إلى خريطة حية للعلم: الوسوم والقوانين والعلماء وراء كل اكتشاف."}
    }.get(lang, {"search": "Search...", "hint": "", "loading": "Loading...", "footer": "", "intro": ""})
    calendar_title = {"ru": "Архив по датам", "en": "Browse by date", "zh": "按日期浏览",
                       "fr": "Parcourir par date", "ar": "تصفح حسب التاريخ"}.get(lang, "Browse by date")
    about_title = {"ru": "О проекте", "en": "About this site", "zh": "关于本站",
                   "fr": "À propos", "ar": "عن الموقع"}.get(lang, "About this site")
    html = tpl.substitute(
        lang=lang, dir=dir_for(lang), goatcounter=GOATCOUNTER, authors_lang="en", asset_ver=asset_ver(),
        fav_title=safe(nav_fav_title(lang)),
        search_placeholder=safe(loc["search"]), search_hint=safe(loc["hint"]),
        loading_text=safe(loc["loading"]), footer_text=safe(loc["footer"]),
        intro_html=loc["intro"], calendar_title=safe(calendar_title), about_title=safe(about_title),
        og_meta_html=site_og_meta(lang, f"{SITE_URL}/{LANG_DIR}/{lang}/index.html"),
        version_toggle_html=""
    )
    base = Path(LANG_DIR) / lang
    _write_text_retry(base / "index.html", html)
    # Вкладка «Избранное» — тот же шаблон/лента; search.js показывает favorites по URL (клиент, localStorage).
    _write_text_retry(base / "favorites.html", html)


def generate_about_page(lang):
    """Страница-гид «About» (дизайн 2026-07-21). Контент — переводимые строки в
    lang/{lang}/data/about.json (шаблон templates/about.html держит только структуру + $lang/$dir).
    Строки могут содержать доверенную инлайн-разметку (<a>/<b>/<strong>/<code>) — НЕ экранируем.
    Фолбэк по КЛЮЧАМ на язык-источник: недостающие в переводе ключи берутся из ru, поэтому даже
    частичный/отсутствующий about.json не роняет страницу (напр. до прогона add-lang)."""
    tpl = load_template("about")
    if not tpl.template: return

    def load_about(l):
        p = Path(LANG_DIR) / l / "data" / "about.json"
        try:
            return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        except Exception:
            return {}
    strings = {**load_about(DEFAULT_LANG), **load_about(lang)}
    if not strings:
        return  # нет даже исходного about.json — нечего рендерить
    (Path(LANG_DIR) / lang / "about.html").write_text(
        tpl.substitute(lang=lang, dir=dir_for(lang),
                       og_meta_html=site_og_meta(lang, f"{SITE_URL}/{LANG_DIR}/{lang}/about.html"),
                       **strings), encoding="utf-8")


# Цвет области науки для treemap-мозаики (дефолтный вид облака тегов). 10 областей + фоллбэк.
DOMAIN_COLORS = {
    "astrophysics": "#3E6DA6", "cosmology": "#6C5CE7", "relativity_gravity": "#B5651D",
    "quantum": "#2E9E8F", "particles_nuclear": "#C0392B", "chemistry_materials": "#2E9E4F",
    "thermo_stat": "#E67E22", "instruments_methods": "#5A7D8C", "mathematics": "#8E44AD",
    "electromagnetism_optics": "#159E86",
}


def generate_tags_cloud(lang):
    tpl = load_template("tags-cloud")
    if not tpl.template: return
    tags_loc = load_tags_loc(lang)
    index = load_index(lang)

    # Счётчики из статей
    tag_counts = {}
    for a in index:
        for t in a.get("tags", []):
            tag_counts[t] = tag_counts.get(t, 0) + 1

    # Все теги из графа
    gp = Path("data/tags-graph.json")
    graph = json.loads(gp.read_text(encoding="utf-8")).get("graph", {}) if gp.exists() else {}

    loc = {
        "en": {"title": "Tags", "subtitle": "Select tags to filter articles.", "footer": "science made simple"},
        "es": {"title": "Etiquetas", "subtitle": "Elige etiquetas para filtrar artículos.", "footer": "ciencia en palabras sencillas"},
        "ru": {"title": "Теги", "subtitle": "Выберите теги для фильтрации статей.", "footer": "наука простыми словами"},
        "zh": {"title": "标签", "subtitle": "选择标签以筛选文章。", "footer": "让科学变简单"},
        "fr": {"title": "Tags", "subtitle": "Sélectionnez des tags pour filtrer les articles.",
               "footer": "la science simplifiée"},
        "ar": {"title": "الوسوم", "subtitle": "اختر الوسوم لتصفية المقالات.", "footer": "العلم ببساطة"}
    }.get(lang, {"title": "Tags", "subtitle": "", "footer": ""})

    def tag_row(tag_id, extra_cls=""):
        name = tags_loc.get(tag_id, {}).get("name", tag_id)
        cnt = tag_counts.get(tag_id, 0)
        count_html = f'<span class="cat-chip-n">{cnt}</span>' if cnt else ""
        cls = f"tag-item {extra_cls}".strip()
        return (f'<a href="/{LANG_DIR}/{lang}/tags/{tag_id}.html" class="{cls}" data-tag="{tag_id}">'
                f'<span>{name}</span>{count_html}</a>\n')

    # Группировка по разделу науки (domain) — компактные колоночные списки; образовательные теги
    # внутри группы помечены курсивом (.educational), но НЕ выносятся в отдельную группу.
    by_domain = {}
    for tid, n in graph.items():
        by_domain.setdefault(n.get("domain") or "", []).append(tid)
    order = sorted(by_domain.keys(), key=lambda d: tag_domain_label(d, lang))
    cloud_html = ""
    for domain in order:
        cloud_html += f'<div class="cloud-group-label">{safe(tag_domain_label(domain, lang))}</div>\n'
        ids = sorted(by_domain[domain], key=lambda t: tags_loc.get(t, {}).get("name", t))
        cloud_html += "".join(
            tag_row(t, "educational" if graph.get(t, {}).get("educational") else "") for t in ids)

    # Данные для treemap-мозаики (дефолтный вид): область = плитка (размер = сумма статей области),
    # внутри — теги (размер = статьи тега). Клик по области → зум к её тегам (js/treemap.js).
    all_lbl = {"ru": "все области", "en": "all fields", "es": "todos los campos",
               "ar": "كل المجالات"}.get(lang, "all fields")
    tm_groups = []
    for domain in by_domain:
        children = sorted(
            ({"name": tags_loc.get(t, {}).get("name", t), "count": tag_counts.get(t, 0),
              "url": f"/{LANG_DIR}/{lang}/tags/{t}.html"} for t in by_domain[domain]),
            key=lambda c: -c["count"])
        tm_groups.append({"key": domain or "other", "label": tag_domain_label(domain, lang),
                          "count": sum(c["count"] for c in children) or len(children),
                          "color": DOMAIN_COLORS.get(domain, "#6b7280"), "children": children})
    tm_groups.sort(key=lambda g: -g["count"])
    treemap_data = json.dumps({"allLabel": all_lbl, "groups": tm_groups}, ensure_ascii=False)

    _write_text_retry(Path(LANG_DIR) / lang / "tags" / "index.html", tpl.substitute(
        lang=lang, dir=dir_for(lang), goatcounter=GOATCOUNTER, authors_lang="en", asset_ver=asset_ver(),
        fav_title=safe(nav_fav_title(lang)),
        version_toggle_html="",
        tags_title=safe(loc["title"]), tags_subtitle=safe(loc["subtitle"]),
        footer_text=safe(loc["footer"]), selected_tags_html="", tags_cloud_html=cloud_html,
        treemap_data=treemap_data,
        mini_graph_filters_html=mini_graph_filters_html(lang, None)
    ), encoding="utf-8")


def generate_tag_page(tag_id, lang):
    tpl = load_template("tag")
    if not tpl.template: return
    tags_loc = load_tags_loc(lang)
    tag_data = tags_loc.get(tag_id, {})
    graph = json.loads(Path("data/tags-graph.json").read_text(encoding="utf-8"))
    tag_graph = graph.get("graph", {}).get(tag_id, {})
    index = load_index(lang)

    articles_html = ""
    for a in full_first([x for x in index
                         if tag_id in x.get("tags", []) and x.get("version") == "popular"]):
        articles_html += entity_article_card(a, lang)

    related_html = " · ".join(
        f'<a href="/{LANG_DIR}/{lang}/tags/{rt}.html" data-tag="{attr_safe(rt)}">{tags_loc.get(rt, {}).get("name", rt)}</a>'
        for rt in tag_graph.get("related", [])[:8]
    )
    formulas_html = render_formulas(tag_data.get("formulas", []))
    loc = {
        "en": {"related": "Related tags", "history": "History", "how": "How it works", "problems": "Open problems & fun facts",
               "search": "Search...", "hint": "# tag · @ author · ! scientist", "footer": "science made simple",
               "scientists": "Scientists:", "no_articles": "No articles yet", "practical": "In practice", "articles": "Related articles"},
        "es": {"related": "Etiquetas relacionadas", "history": "Historia", "how": "Cómo funciona",
               "problems": "Problemas abiertos y curiosidades",
               "search": "Buscar...", "hint": "# etiqueta · @ autor · ! científico",
               "footer": "ciencia en palabras sencillas", "scientists": "Científicos:",
               "no_articles": "Aún no hay artículos", "practical": "En la práctica",
               "articles": "Artículos relacionados"},
        "ar": {"related": "وسوم ذات صلة", "history": "التاريخ", "how": "كيف يعمل",
               "problems": "مسائل مفتوحة وحقائق طريفة", "search": "بحث...",
               "hint": "# وسم · @ مؤلف · ! عالم", "footer": "العلم ببساطة",
               "scientists": "العلماء:", "no_articles": "لا مقالات بعد", "practical": "في الواقع", "articles": "مقالات ذات صلة"},
        "ru": {"related": "Связанные теги", "history": "История", "how": "Как работает",
               "problems": "Открытые проблемы и интересные факты", "search": "Поиск...",
               "hint": "# тег · @ автор · ! учёный", "footer": "наука простыми словами",
               "scientists": "Учёные:", "no_articles": "Пока нет статей", "practical": "На практике", "articles": "Статьи по теме"},
        "zh": {"related": "相关标签", "history": "历史", "how": "工作原理", "problems": "未解决的问题与趣味知识",
               "search": "搜索...", "hint": "# 标签 · @ 作者 · ! 科学家", "footer": "让科学变简单",
               "scientists": "科学家：", "no_articles": "暂无文章", "practical": "实际应用", "articles": "相关文章"},
        "fr": {"related": "Tags associés", "history": "Histoire", "how": "Fonctionnement",
               "problems": "Problèmes ouverts et anecdotes", "search": "Rechercher...",
               "hint": "# tag · @ auteur · ! scientifique", "footer": "la science simplifiée",
               "scientists": "Scientifiques :", "no_articles": "Pas encore d'articles", "practical": "En pratique", "articles": "Articles liés"}
    }.get(lang, {"related": "Related", "history": "History", "how": "How it works", "problems": "Open problems & fun facts",
                 "search": "Search...", "hint": "# tag · @ author · ! scientist", "footer": "",
                 "scientists": "Scientists:", "no_articles": "No articles yet", "practical": "In practice", "articles": "Related articles"})

    problems_and_fact_html = ""
    if tag_data.get("key_problems") or tag_data.get("fun_fact"):
        problems_and_fact_html = f'<div class="section"><h2>{safe(loc["problems"])}</h2>'
        if tag_data.get("key_problems"):
            problems_and_fact_html += f'<p>{safe("; ".join(tag_data["key_problems"]))}</p>'
        if tag_data.get("fun_fact"):
            problems_and_fact_html += f'<p class="fact fact-fun">{safe(tag_data["fun_fact"])}</p>'
        problems_and_fact_html += '</div>'

    fun_fact_html = ""
    if tag_data.get("fun_fact"):
        fun_fact_html = f'<div class="fun-fact">{safe(tag_data["fun_fact"])}</div>'
    fun_fact_popular_html = ""
    ff_pop = tag_data.get("fun_fact_popular") or tag_data.get("fun_fact", "")
    if ff_pop:
        fun_fact_popular_html = f'<div class="fun-fact">{safe(ff_pop)}</div>'

    scientists_link_list = [scientist_link_or_text(s, lang) for s in tag_data.get("scientists", [])]
    scientists_section_html = related_row(loc["scientists"].rstrip(":"), scientists_link_list, "sci")

    mini_html = f'<p class="mini-desc">{safe(tag_data["mini"])}</p>' if tag_data.get("mini") else ""
    if tag_data.get("practical_application"):
        mini_html += f'<div class="practical-app"><strong>{safe(loc["practical"])}:</strong> {safe(tag_data["practical_application"])}</div>'

    tag_img_url = entity_image_url("tags", tag_id)
    ai_cover_html = f'<div class="ai-cover"><img src="{tag_img_url}" alt=""></div>' if tag_img_url else ""

    # id НЕ переименовываем в tag-version-toggle: search.js слушает именно #version-toggle,
    # чтобы синхронно перерисовать список статей внизу при смене версии (был баг — текст тега
    # переключался, а список статей оставался на старой версии).
    tag_version_toggle = level_switch_spans(lang, "popular")

    desc_pop = tag_data.get("description_popular") or tag_data.get("description_simple") or tag_data.get("description", "")
    desc_simple = tag_data.get("description_simple") or tag_data.get("description", "")
    hist_simple = tag_data.get("history_simple") or tag_data.get("history", "")
    how_simple = tag_data.get("how_it_works_simple") or tag_data.get("how_it_works", "")
    raw = tag_data.get("raw") or {}
    raw_pop = raw.get("description_popular") or raw.get("description_simple") or raw.get("description", "")
    raw_simple = raw.get("description_simple") or raw.get("description", "")
    raw_adv = raw.get("description", "")
    tag_like_id = f"{tag_id}_{lang}_page"
    actions_html = build_actions_html(tag_like_id, tag_id, lang, "tag", inline_comment=True)
    feedback_html = build_feedback_html(tag_like_id, lang, "tag", inline_toggle=True)
    og_meta_html = build_og_meta(
        f'#{tag_data.get("name", tag_id)} — bridge42worlds', desc_pop,
        f"{SITE_URL}/{LANG_DIR}/{lang}/tags/{tag_id}.html", tag_img_url and f"{SITE_URL}{tag_img_url}")

    # Правый сайдбар (как на статье/законе): связанные теги + законы + учёные плашками-колонкой,
    # вместо разбросанных по телу related-блоков (юзер-фидбек 2026-07-17: "по тому же образу
    # справа, а не в подвале"). Тот же side_chip_group/.side-* стиль, что на law-странице.
    _laws_loc = load_laws_loc(lang)
    side_tag_chips = [
        f'<a href="/{LANG_DIR}/{lang}/tags/{attr_safe(rt)}.html" class="side-tag" data-tag="{attr_safe(rt)}">'
        f'{safe(tags_loc.get(rt, {}).get("name", rt))}</a>' for rt in tag_graph.get("related", [])[:8]]
    side_law_chips = [
        f'<a href="/{LANG_DIR}/{lang}/laws/{attr_safe(lid)}.html" class="side-law" data-law="{attr_safe(lid)}">'
        f'{safe(L.get("name", lid))}</a>'
        for lid, L in _laws_loc.items() if tag_id in (L.get("tags") or [])][:6]
    side_sci_chips = [
        f'<a href="/{LANG_DIR}/{lang}/scientists/{attr_safe(author_slug(s))}.html" class="side-sci" '
        f'data-scientist="{attr_safe(s)}">{safe(s)}</a>'
        for s in tag_data.get("scientists", []) if s in valid_scientist_ids()]
    entity_side_html = (
        side_chip_group(side_label("sci", lang), side_sci_chips)
        + side_chip_group(side_label("tags", lang), side_tag_chips)
        + side_chip_group(side_label("laws", lang), side_law_chips)
    )

    _write_text_retry(Path(LANG_DIR) / lang / "tags" / f"{tag_id}.html", tpl.substitute(
        lang=lang, dir=dir_for(lang), goatcounter=GOATCOUNTER, authors_lang="en", asset_ver=asset_ver(),
        fav_title=safe(nav_fav_title(lang)),
        og_meta_html=og_meta_html, entity_side_html=entity_side_html,
        tag_id=attr_safe(tag_id),
        tag_name=safe(tag_data.get("name", tag_id)), entity_kind_html=entity_kind_html("tag", lang), article_count=tag_graph.get("article_count", 0),
        tag_stats_html=(f'<div class="tag-stats"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><line x1="6.5" y1="19" x2="6.5" y2="13"/><line x1="12" y1="19" x2="12" y2="8.5"/><line x1="17.5" y1="19" x2="17.5" y2="11"/><line x1="4" y1="19.5" x2="20" y2="19.5"/></svg> <a class="stat-jump" href="#article-list">{tag_graph.get("article_count", 0)}</a></div>'
                         if tag_graph.get("article_count", 0) else ""),
        ai_cover_html=ai_cover_html,
        actions_html=actions_html, feedback_html=feedback_html, share_label=safe(share_label_for(lang)),
        tag_version_toggle=tag_version_toggle,
        tag_mini_html=mini_html,
        tag_desc_popular_raw=attr_safe(raw_pop),
        tag_desc_simple_raw=attr_safe(raw_simple),
        tag_desc_adv_raw=attr_safe(raw_adv),
        tag_description_popular=safe(desc_pop),
        fun_fact_popular_html=fun_fact_popular_html,
        tag_description_simple=safe(desc_simple),
        tag_history_simple=safe(hist_simple),
        tag_how_it_works_simple=safe(how_simple),
        history_simple_section_html=text_section_html(loc["history"], hist_simple),
        how_simple_section_html=text_section_html(loc["how"], how_simple),
        fun_fact_html=fun_fact_html,
        tag_description=safe(tag_data.get("description", "")),
        tag_history=safe(tag_data.get("history", "")),
        tag_how_it_works=safe(tag_data.get("how_it_works", "")),
        history_section_html=text_section_html(loc["history"], tag_data.get("history", "")),
        how_section_html=text_section_html(loc["how"], tag_data.get("how_it_works", "")),
        problems_and_fact_html=problems_and_fact_html,
        formulas_html=formulas_html, scientists_section_html=scientists_section_html,
        laws_section_html=laws_for_tag(tag_id, lang),
        history_label=safe(loc["history"]), how_label=safe(loc["how"]),
        related_label=safe(loc["related"]), articles_label=safe(loc["articles"]),
        related_tags_html=related_html, search_placeholder=safe(loc["search"]),
        search_hint=safe(loc["hint"]), graph_mini_label=safe(MINI_LABEL.get(lang, MINI_LABEL["en"])),
        mini_graph_filters_html=mini_graph_filters_html(lang, "tag"),
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
           "search": "Найти закон...", "tags": "Связанные понятия", "related_laws": "Связанные законы", "articles": "Статьи по теме", "scientists": "Открыли:", "practical": "На практике",
           "influenced": "Оказали влияние:", "article_search": "Поиск статей...", "article_hint": "# тег · @ автор · ! учёный"},
    "en": {"title": "Laws & Principles", "subtitle": "Fundamental laws of science. The formula is just a representation; the idea is in the text.",
           "history": "Discovery", "how": "How it works", "problems": "Caveats", "laws": "Laws:", "footer": "science made simple",
           "search": "Find a law...", "tags": "Related concepts", "related_laws": "Related laws", "articles": "Related articles", "scientists": "Discovered by:", "practical": "In practice",
           "influenced": "Key influence:", "article_search": "Search articles...", "article_hint": "# tag · @ author · ! scientist"},
    "zh": {"title": "定律与原理", "subtitle": "科学的基本定律。公式只是表现形式，本质在文字中。",
           "history": "发现历史", "how": "工作原理", "problems": "注意事项", "laws": "定律：", "footer": "让科学变简单",
           "search": "查找定律...", "tags": "相关概念", "related_laws": "相关定律", "articles": "相关文章", "scientists": "发现者：", "practical": "实际应用",
           "influenced": "重要影响：", "article_search": "搜索文章...", "article_hint": "# 标签 · @ 作者 · ! 科学家"},
    "fr": {"title": "Lois et principes", "subtitle": "Lois fondamentales de la science. La formule n'est qu'une représentation.",
           "history": "Découverte", "how": "Fonctionnement", "problems": "Nuances", "laws": "Lois :", "footer": "la science simplifiée",
           "search": "Trouver une loi...", "tags": "Concepts liés", "related_laws": "Lois associées", "articles": "Articles liés", "scientists": "Découverte par :", "practical": "En pratique",
           "influenced": "Influence clé :", "article_search": "Rechercher des articles...", "article_hint": "# tag · @ auteur · ! scientifique"},
    "ar": {"title": "القوانين والمبادئ", "subtitle": "القوانين الأساسية للعلم. الصيغة مجرد تمثيل؛ الفكرة في النص.",
           "history": "تاريخ الاكتشاف", "how": "كيف يعمل", "problems": "ملاحظات", "laws": "القوانين:", "footer": "العلم ببساطة",
           "search": "ابحث عن قانون...", "tags": "مفاهيم ذات صلة", "related_laws": "قوانين ذات صلة", "articles": "مقالات ذات صلة", "scientists": "اكتشفه:", "practical": "في الواقع",
           "influenced": "تأثير رئيسي:", "article_search": "ابحث عن مقالات...", "article_hint": "# وسم · @ مؤلف · ! عالم"},
}

LAW_TYPE_COLORS = {"закон": "#C0392B", "принцип": "#8E44AD", "теорема": "#2471A3",
                   "эффект": "#B9770E", "уравнение": "#148F77", "теория": "#5D6D7E",
                   "изобретение": "#2E7D32"}
# Тип закона хранится в data по-русски и служит заголовком группы на странице /laws/.
# Локализуем его под язык страницы (юзер-фидбек 2026-07-22: на es группы были по-русски).
LAW_TYPE_LABEL = {
    "закон":       {"en": "law", "es": "ley", "ar": "قانون", "fr": "loi", "zh": "定律"},
    "принцип":     {"en": "principle", "es": "principio", "ar": "مبدأ", "fr": "principe", "zh": "原理"},
    "теорема":     {"en": "theorem", "es": "teorema", "ar": "مبرهنة", "fr": "théorème", "zh": "定理"},
    "эффект":      {"en": "effect", "es": "efecto", "ar": "تأثير", "fr": "effet", "zh": "效应"},
    "уравнение":   {"en": "equation", "es": "ecuación", "ar": "معادلة", "fr": "équation", "zh": "方程"},
    "теория":      {"en": "theory", "es": "teoría", "ar": "نظرية", "fr": "théorie", "zh": "理论"},
    "изобретение": {"en": "invention", "es": "invención", "ar": "اختراع", "fr": "invention", "zh": "发明"},
}
def law_type_label(t, lang):
    if not t or lang == "ru":
        return t
    return LAW_TYPE_LABEL.get(t, {}).get(lang, t)

# Раздел науки тега (для группировки облака списком) — фиксированный английский slug (НЕ переводится
# через LLM, чтобы группировка/цвета не разъезжались по языкам); подписи — тут, локализуются вручную.
# Подпись ТИПА страницы-сущности над заголовком — чтобы читатель понимал, где он находится
# (юзер 2026-07-25: «на карточках тегов/законов/учёных надо писать, что это за тип»).
ENTITY_KIND_LABELS = {
    "tag":       {"ru": "Тег", "en": "Tag", "es": "Etiqueta", "ar": "وسم"},
    "law":       {"ru": "Закон", "en": "Law", "es": "Ley", "ar": "قانون"},
    "scientist": {"ru": "Учёный", "en": "Scientist", "es": "Científico", "ar": "عالِم"},
    "section":   {"ru": "Раздел", "en": "Section", "es": "Sección", "ar": "قسم"},
    "author":    {"ru": "Автор", "en": "Author", "es": "Autor", "ar": "مؤلف"},
}


def entity_kind_html(kind, lang):
    e = ENTITY_KIND_LABELS.get(kind)
    if not e:
        return ""
    return f'<div class="entity-kind">{safe(e.get(lang, e["en"]))}</div>'


TAG_DOMAIN_LABELS = {
    "cosmology":              {"ru": "Космология", "en": "Cosmology", "es": "Cosmología", "ar": "علم الكونيات"},
    "astrophysics":           {"ru": "Астрофизика", "en": "Astrophysics", "es": "Astrofísica", "ar": "الفيزياء الفلكية"},
    "particles_nuclear":      {"ru": "Физика частиц и ядерная физика", "en": "Particle & Nuclear Physics", "es": "Física de partículas y nuclear", "ar": "فيزياء الجسيمات والنووية"},
    "quantum":                {"ru": "Квантовая механика", "en": "Quantum Mechanics", "es": "Mecánica cuántica", "ar": "الميكانيكا الكمّية"},
    "relativity_gravity":     {"ru": "Относительность и гравитация", "en": "Relativity & Gravity", "es": "Relatividad y gravedad", "ar": "النسبية والجاذبية"},
    "thermo_stat":            {"ru": "Термодинамика и статфизика", "en": "Thermodynamics & Stat. Physics", "es": "Termodinámica y física estadística", "ar": "الديناميكا الحرارية والإحصائية"},
    "electromagnetism_optics": {"ru": "Электромагнетизм и оптика", "en": "Electromagnetism & Optics", "es": "Electromagnetismo y óptica", "ar": "الكهرومغناطيسية والبصريات"},
    "chemistry_materials":    {"ru": "Химия и материалы", "en": "Chemistry & Materials", "es": "Química y materiales", "ar": "الكيمياء والمواد"},
    "mathematics":            {"ru": "Математика", "en": "Mathematics", "es": "Matemáticas", "ar": "الرياضيات"},
    "instruments_methods":    {"ru": "Инструменты и методы", "en": "Instruments & Methods", "es": "Instrumentos y métodos", "ar": "الأدوات والطرق"},
    "biology":                {"ru": "Биология", "en": "Biology", "es": "Biología", "ar": "الأحياء"},
    "medicine":               {"ru": "Медицина", "en": "Medicine", "es": "Medicina", "ar": "الطب"},
    "neuroscience":           {"ru": "Нейронаука", "en": "Neuroscience", "es": "Neurociencia", "ar": "علم الأعصاب"},
    "genomics":               {"ru": "Геномика", "en": "Genomics", "es": "Genómica", "ar": "علم الجينوم"},
    "bioengineering":         {"ru": "Биоинженерия", "en": "Bioengineering", "es": "Bioingeniería", "ar": "الهندسة الحيوية"},
}
TAG_DOMAIN_FALLBACK = {"ru": "Другое", "en": "Other", "es": "Otros", "fr": "Autre", "ar": "أخرى"}

# Имена ГРУПП разделов верхнего уровня (юзер 2026-07-25: на /sections/ у cs/math/… не было имени —
# в справочнике только подкатегории). Фолбэк для gname. Умбреллы вроде cond-mat/hep-th/gr-qc/quant-ph
# резолвятся из arxiv-categories, а эти — нет.
SECTION_GROUP_NAMES = {
    "cs":       {"ru": "Информатика", "en": "Computer Science", "es": "Informática", "ar": "علوم الحاسوب"},
    "math":     {"ru": "Математика", "en": "Mathematics", "es": "Matemáticas", "ar": "الرياضيات"},
    "physics":  {"ru": "Физика", "en": "Physics", "es": "Física", "ar": "الفيزياء"},
    "astro-ph": {"ru": "Астрофизика", "en": "Astrophysics", "es": "Astrofísica", "ar": "الفيزياء الفلكية"},
    "q-bio":    {"ru": "Количественная биология", "en": "Quantitative Biology", "es": "Biología cuantitativa", "ar": "الأحياء الكمّية"},
    "eess":     {"ru": "Электротехника и системы", "en": "Electrical Eng. & Systems Science", "es": "Ingeniería eléctrica y sistemas", "ar": "الهندسة الكهربائية والأنظمة"},
    "stat":     {"ru": "Статистика", "en": "Statistics", "es": "Estadística", "ar": "الإحصاء"},
    "econ":     {"ru": "Экономика", "en": "Economics", "es": "Economía", "ar": "الاقتصاد"},
    "q-fin":    {"ru": "Количественные финансы", "en": "Quantitative Finance", "es": "Finanzas cuantitativas", "ar": "التمويل الكمّي"},
    "nlin":     {"ru": "Нелинейные науки", "en": "Nonlinear Sciences", "es": "Ciencias no lineales", "ar": "العلوم اللاخطية"},
}


def section_group_name(prefix, lang):
    e = SECTION_GROUP_NAMES.get(prefix)
    return e.get(lang, e["en"]) if e else ""


def tag_domain_label(domain, lang):
    entry = TAG_DOMAIN_LABELS.get(domain)
    if not entry:
        return TAG_DOMAIN_FALLBACK.get(lang, TAG_DOMAIN_FALLBACK["en"])
    return entry.get(lang, entry["en"])

MINI_CONFIG_LABEL = {"ru": "настроить представление", "en": "configure view", "es": "configurar vista",
                     "ar": "ضبط العرض", "fr": "configurer la vue", "zh": "显示设置"}
MINI_LABEL = {"ru": "Связи в графе знаний", "en": "Links in the knowledge graph",
              "es": "Conexiones en el grafo del conocimiento",
              "zh": "知识图谱中的关联", "fr": "Liens dans le graphe des savoirs", "ar": "الروابط في شبكة المعرفة"}
# Короткий ярлык для левого меню-навигатора статьи (пункт на граф — только когда граф есть,
# юзер-фидбек 2026-07-15: "ссылка на отзыв тоже слева после графа").
GRAPH_NAV_LABEL = {"ru": "Граф", "en": "Graph", "es": "Grafo", "zh": "关系图", "fr": "Graphe", "ar": "الشبكة"}

SIDE_LAWS_LABEL = {"ru": "Законы", "en": "Laws", "es": "Leyes", "zh": "定律", "fr": "Lois", "ar": "قوانين"}
SIDE_TAGS_LABEL = {"ru": "Теги", "en": "Tags", "es": "Etiquetas", "zh": "标签", "fr": "Tags", "ar": "الوسوم"}
SIDE_SCI_LABEL = {"ru": "Учёные", "en": "Scientists", "es": "Científicos", "zh": "科学家", "fr": "Scientifiques", "ar": "العلماء"}


def side_label(kind, lang):
    """Подпись колонки сайдбара — один источник на все страницы.

    Колонка сайдбара везде отвечает на один вопрос: «что ещё связано с этим». Раньше
    подпись брали кто откуда — страница тега из SIDE_LAWS_LABEL, страница закона из
    loc["tags"], страница учёного из loc["related"] — и они разъехались: колонка тегов
    называлась то «Теги», то «Связанные теги», по-французски законы были одновременно
    «Lois liées» и «Lois associées». Теперь слово зависит от сущности, а не от страницы,
    и следующая страница разойтись уже не сможет.

    Роли — отдельный случай и сюда не входят: «Открыли» на странице закона и «Оказали
    влияние» на странице учёного значат не «связанные учёные», а кто именно это сделал."""
    d = {"tags": SIDE_TAGS_LABEL, "laws": SIDE_LAWS_LABEL, "sci": SIDE_SCI_LABEL}[kind]
    return d.get(lang, d["en"])

ABSTRACT_LABEL = {"ru": "Аннотация", "en": "Abstract", "es": "Resumen", "zh": "摘要", "fr": "Résumé", "ar": "الملخّص"}

# ── Экспресс-режим: locked-тиры (не входят в express.tiers) теперь показывают РЕАЛЬНЫЙ
# контент уже готового тира (см. express_locked_scipop) + баннер сверху текста, а не заглушку
# с generic-заголовком (юзер-фидбек 2026-07-17: "смущает, что название подменяется... лучше
# оставить как у простой, но сверху написать это простой вариант"). Клик на locked-вкладку —
# сигнал интереса (logExpressInterest в likes.js), помогает приоритизировать, какие статьи
# апгрейдить (run.py regen <id>) первыми.

# Баннер над текстом locked-тира: "показана версия X — Y пока не готова". {shown}/{locked} —
# названия тиров подставляются на лету при рендере (article["express_tiers"] решает, какой тир
# реально показан), сам баннер один и тот же для всех статей.
EXPRESS_LOCKED_BANNER = {
    "ru": '📄 Показана версия «{shown}» — «{locked}» пока не готова. Добавьте ★ в избранное, если хотите её ускорить.',
    "en": '📄 Showing the "{shown}" version — "{locked}" is not ready yet. Add it to favorites to help prioritize it.',
    "es": '📄 Mostrando la versión "{shown}" — "{locked}" aún no está lista. Añádelo a favoritos para ayudar a priorizarla.',
    "zh": '📄 当前显示"{shown}"版本 — "{locked}"尚未准备好。收藏可以帮助优先制作。',
    "fr": '📄 Version "{shown}" affichee, "{locked}" n est pas encore prete. Ajoutez-le aux favoris pour aider a la prioriser.',
    "ar": '📄 معروضة نسخة «{shown}» — «{locked}» غير جاهزة بعد. أضفه إلى المفضّلة للمساعدة في تسريعها.',
}
EXPRESS_LOCKED_HINT_UNUSED_TOP = {
    "ru": 'DEAD_START',
    "fr": 'DEADCODE_UNUSED_IGNORE_’article est disponible en version « {tier} » — <a href="{url}">l’ouvrir</a>.',
    "ar": 'يتوفر المقال حاليًا بمستوى «{tier}» — <a href="{url}">فتحه</a>.',
}


def express_locked_scipop(base, lang):
    """base - realny kontent uzhe gotovogo tira (obychno express-rezultat, simple-formy).
    Ranshe podmenyala VES kontent na generic-zaglushku - yuzer-fidbek 2026-07-17: nazvanie
    ne dolzhno podmenyatsya, pokazyvaem realny kontent. Teper prosto pomechaet locked-flagom,
    realny kontent ostayotsya kak est - gen_article_html renderit ego cherez SIMPLE_LIKE-vetku
    (dazhe dlya nominalno advanced/popular) i dobavlyaet banner-uvedomlenie sverhu teksta."""
    return {**base, "express_locked": True}


def laws_for_tag(tag_id, lang):
    """Ссылки на СТРАНИЦЫ законов, относящихся к тегу (секция «Законы» на странице тега)."""
    laws = load_laws_loc(lang)
    loc = LAWS_LABELS.get(lang, LAWS_LABELS["en"])
    related = [(lid, L) for lid, L in laws.items() if tag_id in (L.get("tags") or [])]
    links = [
        f'<a href="/{LANG_DIR}/{lang}/laws/{attr_safe(lid)}.html" class="law-chip" data-law="{attr_safe(lid)}">{safe(L.get("name", lid))}</a>'
        for lid, L in related[:14]]
    return related_row(loc["laws"].rstrip(":"), links, "laws")


def generate_laws_cloud(lang):
    """Облако ИМЁН законов (как теги): каждое имя — ссылка на страницу закона. + граф."""
    tpl = load_template("laws-cloud")
    if not tpl.template: return
    laws = load_laws_loc(lang)
    loc = LAWS_LABELS.get(lang, LAWS_LABELS["en"])
    # Цвет типа берём по КАНОНИЧЕСКОМУ (ru) типу, т.к. type в laws.json локализован — на en/es/ar
    # ключи LAW_TYPE_COLORS (русские) иначе не совпадают и всё падало в серый (баг и у точек-типа).
    ru_laws = laws if lang == "ru" else load_laws_loc("ru")
    def law_color(lid):
        return LAW_TYPE_COLORS.get(ru_laws.get(lid, {}).get("type", ""), "#7f8c8d")

    # Счётчики статей по законам (через пересечение тегов)
    index = load_index(lang)
    law_counts = {}
    for a in index:
        arts = set(a.get("tags", []))
        for lid, L in laws.items():
            ltags = set(L.get("tags", []))
            if ltags & arts:
                law_counts[lid] = law_counts.get(lid, 0) + 1

    # Группируем по типу (уже локализованная строка — сама и есть заголовок группы), внутри — по алфавиту
    by_type = {}
    for lid, L in laws.items():
        by_type.setdefault(L.get("type", "") or "—", []).append(lid)

    def law_row(lid):
        L = laws[lid]
        color = law_color(lid)
        cnt = law_counts.get(lid, 0)
        count_html = f'<span class="cat-chip-n">{cnt}</span>' if cnt else ""
        return (
            f'<a href="/{LANG_DIR}/{lang}/laws/{attr_safe(lid)}.html" class="tag-item law-item" data-law="{attr_safe(lid)}">'
            f'<span><span class="law-type-dot" style="background:{color}"></span>{safe(L.get("name", lid))}</span>{count_html}</a>\n'
        )

    cloud = ""
    for t in sorted(by_type.keys()):
        cloud += f'<div class="cloud-group-label">{safe(law_type_label(t, lang))}</div>\n'
        cloud += "".join(law_row(lid) for lid in sorted(by_type[t], key=lambda x: laws[x].get("name", x)))

    # Данные для treemap-мозаики (дефолтный вид): тип закона = плитка, внутри — законы.
    all_lbl = {"ru": "все типы", "en": "all types", "es": "todos los tipos",
               "ar": "كل الأنواع"}.get(lang, "all types")
    tm_groups = []
    for t, lids in by_type.items():
        children = sorted(
            ({"name": laws[lid].get("name", lid), "count": law_counts.get(lid, 0),
              "url": f"/{LANG_DIR}/{lang}/laws/{attr_safe(lid)}.html"} for lid in lids),
            key=lambda c: -c["count"])
        color = law_color(lids[0])
        tm_groups.append({"key": t, "label": law_type_label(t, lang), "count": sum(c["count"] for c in children) or len(children),
                          "color": color, "children": children})
    tm_groups.sort(key=lambda g: -g["count"])
    treemap_data = json.dumps({"allLabel": all_lbl, "groups": tm_groups}, ensure_ascii=False)

    (Path(LANG_DIR) / lang / "laws").mkdir(parents=True, exist_ok=True)
    _write_text_retry(Path(LANG_DIR) / lang / "laws" / "index.html", tpl.substitute(
        lang=lang, dir=dir_for(lang), goatcounter=GOATCOUNTER, authors_lang="en", asset_ver=asset_ver(),
        fav_title=safe(nav_fav_title(lang)),
        version_toggle_html="",
        laws_title=safe(loc["title"]), laws_subtitle=safe(loc["subtitle"]),
        search_placeholder=safe(loc["search"]),
        laws_cloud_html=cloud or f'<p>{safe(loc["subtitle"])}</p>',
        treemap_data=treemap_data,
        footer_text=safe(loc["footer"]),
        mini_graph_filters_html=mini_graph_filters_html(lang, None)
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

    # id НЕ переименовываем (см. тот же комментарий у тегов) — иначе список статей внизу не
    # синхронизируется с переключением версии.
    toggle = level_switch_spans(lang, "popular")
    law_img_url = entity_image_url("laws", law_id)
    ai_cover_html = f'<div class="ai-cover"><img src="{law_img_url}" alt=""></div>' if law_img_url else ""
    formulas_html = render_formulas(L.get("formulas", []))
    def _law_tag_link(t):
        label = safe(tags_loc.get(t, {}).get("name", t))
        # t не в valid_tag_ids() — обычно перевод закона положил в "tags" локализованное имя
        # вместо канонического id (гэп в reference_translate.py), ссылка на такой id 404-ит.
        if t not in valid_tag_ids():
            return label
        return f'<a href="/{LANG_DIR}/{lang}/tags/{t}.html" data-tag="{attr_safe(t)}">{label}</a>'
    related_tags_html = " · ".join(_law_tag_link(t) for t in law_tags if t)
    sci_links = [scientist_link_or_text(s, lang) for s in (L.get("scientists") or [])]
    scientists_section_html = related_row(loc["scientists"].rstrip(":"), sci_links)
    influenced_links = [scientist_link_or_text(s, lang) for s in (L.get("influenced_by") or [])]
    influenced_section_html = related_row(loc["influenced"].rstrip(":"), influenced_links)
    related_laws = [rl for rl in (L.get("related_laws") or []) if rl in laws]
    related_laws_links = [
        f'<a href="/{LANG_DIR}/{lang}/laws/{attr_safe(rl)}.html" class="law-chip" data-law="{attr_safe(rl)}">{safe(laws[rl].get("name", rl))}</a>'
        for rl in related_laws]
    related_laws_block = related_row(loc["related_laws"], related_laws_links)

    # Правый сайдбар (эксперимент, тот же подход, что на странице статьи): учёные сверху,
    # затем теги, затем связанные законы — те же .side-sci/.side-tag/.side-law чипы.
    all_sci_ids = ((L.get("scientists") or []) + (L.get("influenced_by") or []))[:6]
    side_sci_chips = [
        f'<a href="/{LANG_DIR}/{lang}/scientists/{attr_safe(author_slug(s))}.html" class="side-sci" '
        f'data-scientist="{attr_safe(s)}">{safe(s)}</a>' for s in all_sci_ids if s in valid_scientist_ids()]
    side_tag_chips = [
        f'<a href="/{LANG_DIR}/{lang}/tags/{attr_safe(t)}.html" class="side-tag" data-tag="{attr_safe(t)}">'
        f'{safe(tags_loc.get(t, {}).get("name", t))}</a>' for t in law_tags[:8] if t in valid_tag_ids()]
    side_law_chips = [
        f'<a href="/{LANG_DIR}/{lang}/laws/{attr_safe(rl)}.html" class="side-law" data-law="{attr_safe(rl)}">'
        f'{safe(laws[rl].get("name", rl))}</a>' for rl in related_laws[:6]]
    entity_side_html = (
        # «Открыли» — роль (кто открыл именно этот закон), а не «связанные учёные»:
        # эту подпись сознательно оставляем из словаря страницы, см. side_label().
        side_chip_group(loc["scientists"].rstrip(":"), side_sci_chips)
        + side_chip_group(side_label("tags", lang), side_tag_chips)
        + side_chip_group(side_label("laws", lang), side_law_chips)
    )

    mini_html = f'<p class="mini-desc">{safe(L["mini"])}</p>' if L.get("mini") else ""
    if L.get("practical_application"):
        mini_html += f'<div class="practical-app"><strong>{safe(loc["practical"])}:</strong> {safe(L["practical_application"])}</div>'
    fun_fact_popular_html = f'<div class="fun-fact">{safe(L.get("fun_fact_popular") or L.get("fun_fact", ""))}</div>' if (L.get("fun_fact_popular") or L.get("fun_fact")) else ""
    fun_fact_html = f'<div class="fun-fact">{safe(L.get("fun_fact", ""))}</div>' if L.get("fun_fact") else ""
    problems = L.get("key_problems") or []
    problems_html = f'<div class="section"><h2>{safe(loc["problems"])}</h2><p>{safe("; ".join(problems))}</p></div>' if problems else ""

    # Статьи по теме — по объединению тегов закона (как лента тега, но для нескольких тегов)
    index = load_index(lang)
    seen = set()
    articles_html = ""
    law_article_count = 0
    for a in index:
        if a.get("version") != "popular": continue
        if not (set(a.get("tags", [])) & set(law_tags)): continue
        if a["id"] in seen: continue
        seen.add(a["id"])
        law_article_count += 1
        articles_html += (
            entity_article_card(a, lang)
        )

    lraw = L.get("raw") or {}
    raw_pop = lraw.get("description_popular") or lraw.get("description_simple") or lraw.get("description", "")
    raw_simple = lraw.get("description_simple") or lraw.get("description", "")
    raw_adv = lraw.get("description", "")
    law_like_id = f"{law_id}_{lang}_page"
    actions_html = build_actions_html(law_like_id, law_id, lang, "law", inline_comment=True)
    feedback_html = build_feedback_html(law_like_id, lang, "law", inline_toggle=True)
    desc_pop_for_og = L.get("description_popular") or L.get("description_simple") or L.get("description", "")
    og_meta_html = build_og_meta(
        f'{L.get("name", law_id)} — bridge42worlds', desc_pop_for_og,
        f"{SITE_URL}/{LANG_DIR}/{lang}/laws/{law_id}.html", law_img_url and f"{SITE_URL}{law_img_url}")

    _write_text_retry(Path(LANG_DIR) / lang / "laws" / f"{law_id}.html", tpl.substitute(
        lang=lang, dir=dir_for(lang), goatcounter=GOATCOUNTER, authors_lang="en", asset_ver=asset_ver(),
        fav_title=safe(nav_fav_title(lang)),
        og_meta_html=og_meta_html,
        law_name=safe(L.get("name", law_id)), entity_kind_html=entity_kind_html("law", lang), law_type=safe(L.get("type", "")),
        ai_cover_html=ai_cover_html,
        actions_html=actions_html, feedback_html=feedback_html, share_label=safe(share_label_for(lang)),
        entity_side_html=entity_side_html,
        law_version_toggle=toggle,
        law_mini_html=mini_html,
        desc_popular_raw=attr_safe(raw_pop),
        desc_simple_raw=attr_safe(raw_simple),
        desc_advanced_raw=attr_safe(raw_adv),
        desc_popular=safe(L.get("description_popular") or L.get("description_simple") or L.get("description", "")),
        fun_fact_popular_html=fun_fact_popular_html,
        desc_simple=safe(L.get("description_simple") or L.get("description", "")),
        how_simple_html=text_section_html(loc["how"], L.get("how_it_works_simple", "")),
        fun_fact_html=fun_fact_html,
        desc_advanced=safe(L.get("description", "")),
        history_html=text_section_html(loc["history"], L.get("history", "")),
        how_html=text_section_html(loc["how"], L.get("how_it_works", "")),
        problems_html=problems_html,
        formulas_html=formulas_html,
        scientists_section_html=scientists_section_html,
        influenced_section_html=influenced_section_html,
        tags_label=safe(loc["tags"]), related_tags_html=related_tags_html,
        related_laws_block=related_laws_block,
        graph_mini_label=safe(MINI_LABEL.get(lang, MINI_LABEL["en"])), law_id=attr_safe(law_id),
        mini_graph_filters_html=mini_graph_filters_html(lang, "law"),
        articles_label=safe(loc["articles"]), article_count=law_article_count,
        tag_stats_html=(f'<div class="tag-stats"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><line x1="6.5" y1="19" x2="6.5" y2="13"/><line x1="12" y1="19" x2="12" y2="8.5"/><line x1="17.5" y1="19" x2="17.5" y2="11"/><line x1="4" y1="19.5" x2="20" y2="19.5"/></svg> <a class="stat-jump" href="#article-list">{law_article_count} {safe(loc["articles"])}</a></div>'
                         if law_article_count else ""),
        search_placeholder=safe(loc["article_search"]), search_hint=safe(loc["article_hint"]),
        primary_tag=attr_safe(",".join(law_tags)),
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


LOADING_LABEL = {"ru": "Загрузка…", "en": "Loading…", "es": "Cargando…", "ar": "جارٍ التحميل…",
                 "fr": "Chargement…", "zh": "加载中…"}

GRAPH_LABELS = {
    "ru": {"title": "Граф знаний", "subtitle": "Теги, законы и учёные и все их связи. Переключай, что показывать.",
           "nodes": "Узлы:", "edges": "Связи:", "presets": "Пресеты:",
           "tags": "теги", "laws": "законы", "scientists": "учёные", "footer": "наука простыми словами",
           "search_tag": "Найти тег…", "search_law": "Найти закон…", "search_sci": "Найти учёного…",
           "depth": "Глубина:", "clear": "Сбросить",
           "warning": "⚠ Отображение оптимизировано под большой экран, формирование графа может занять некоторое время.",
           "edge_tag_law": "тег↔закон", "edge_tag_sci": "тег↔учёный", "edge_law_sci": "закон↔учёный",
           "edge_tag_tag": "тег↔тег", "edge_law_law": "закон↔закон", "edge_sci_sci": "учёный↔учёный", "edge_law_influence": "закон↔влияние", "categories": "разделы", "edge_tag_cat": "тег↔раздел", "preset_core": "каркас", "preset_all": "всё"},
    "en": {"title": "Knowledge graph", "subtitle": "Tags, laws and scientists and all their links. Toggle what to show.",
           "nodes": "Nodes:", "edges": "Edges:", "presets": "Presets:",
           "tags": "tags", "laws": "laws", "scientists": "scientists", "footer": "science made simple",
           "search_tag": "Find a tag…", "search_law": "Find a law…", "search_sci": "Find a scientist…",
           "depth": "Depth:", "clear": "Clear",
           "warning": "⚠ Optimized for large screens — building the graph may take a moment.",
           "edge_tag_law": "tag↔law", "edge_tag_sci": "tag↔scientist", "edge_law_sci": "law↔scientist",
           "edge_tag_tag": "tag↔tag", "edge_law_law": "law↔law", "edge_sci_sci": "scientist↔scientist", "edge_law_influence": "law↔influence", "categories": "categories", "edge_tag_cat": "tag↔category", "preset_core": "core", "preset_all": "all"},
    "es": {"title": "Red de conocimiento", "subtitle": "Etiquetas, leyes y científicos y todos sus vínculos. Elige qué mostrar.",
           "nodes": "Nodos:", "edges": "Vínculos:", "presets": "Preajustes:",
           "tags": "etiquetas", "laws": "leyes", "scientists": "científicos", "footer": "ciencia simple",
           "search_tag": "Buscar una etiqueta…", "search_law": "Buscar una ley…", "search_sci": "Buscar un científico…",
           "depth": "Profundidad:", "clear": "Restablecer",
           "warning": "⚠ Optimizado para pantallas grandes — construir el grafo puede tardar un momento.",
           "edge_tag_law": "etiqueta↔ley", "edge_tag_sci": "etiqueta↔científico", "edge_law_sci": "ley↔científico",
           "edge_tag_tag": "etiqueta↔etiqueta", "edge_law_law": "ley↔ley", "edge_sci_sci": "científico↔científico", "edge_law_influence": "ley↔influencia", "categories": "categorías", "edge_tag_cat": "etiqueta↔categoría", "preset_core": "núcleo", "preset_all": "todo"},
    "zh": {"title": "知识图谱", "subtitle": "标签、定律与科学家及其关联。切换显示内容。",
           "nodes": "节点：", "edges": "关联：", "presets": "预设：",
           "tags": "标签", "laws": "定律", "scientists": "科学家", "footer": "让科学变简单",
           "search_tag": "查找标签…", "search_law": "查找定律…", "search_sci": "查找科学家…",
           "depth": "深度：", "clear": "重置",
           "warning": "⚠ 界面针对大屏幕优化，图谱生成可能需要一些时间。",
           "edge_tag_law": "标签↔定律", "edge_tag_sci": "标签↔科学家", "edge_law_sci": "定律↔科学家",
           "edge_tag_tag": "标签↔标签", "edge_law_law": "定律↔定律", "edge_sci_sci": "科学家↔科学家", "edge_law_influence": "定律↔影响", "categories": "分类", "edge_tag_cat": "标签↔分类", "preset_core": "核心", "preset_all": "全部"},
    "fr": {"title": "Graphe des savoirs", "subtitle": "Tags, lois et scientifiques et leurs liens. Choisissez l'affichage.",
           "nodes": "Nœuds :", "edges": "Liens :", "presets": "Préréglages :",
           "tags": "tags", "laws": "lois", "scientists": "scientifiques", "footer": "la science simplifiée",
           "search_tag": "Trouver un tag…", "search_law": "Trouver une loi…", "search_sci": "Trouver un scientifique…",
           "depth": "Profondeur :", "clear": "Réinitialiser",
           "warning": "⚠ Optimisé pour grand écran — la construction du graphe peut prendre un moment.",
           "edge_tag_law": "tag↔loi", "edge_tag_sci": "tag↔scientifique", "edge_law_sci": "loi↔scientifique",
           "edge_tag_tag": "tag↔tag", "edge_law_law": "loi↔loi", "edge_sci_sci": "scientifique↔scientifique", "edge_law_influence": "loi↔influence", "categories": "catégories", "edge_tag_cat": "tag↔catégorie", "preset_core": "noyau", "preset_all": "tout"},
    "ar": {"title": "شبكة المعرفة", "subtitle": "الوسوم والقوانين والعلماء وكل روابطهم. بدّل ما تريد عرضه.",
           "nodes": "العقد:", "edges": "الروابط:", "presets": "إعدادات:",
           "tags": "وسوم", "laws": "قوانين", "scientists": "علماء", "footer": "العلم ببساطة",
           "search_tag": "ابحث عن وسم…", "search_law": "ابحث عن قانون…", "search_sci": "ابحث عن عالِم…",
           "depth": "العمق:", "clear": "إعادة تعيين",
           "warning": "⚠ الواجهة محسّنة للشاشات الكبيرة، وقد يستغرق إنشاء الرسم البياني بعض الوقت.",
           "edge_tag_law": "وسم↔قانون", "edge_tag_sci": "وسم↔عالِم", "edge_law_sci": "قانون↔عالِم",
           "edge_tag_tag": "وسم↔وسم", "edge_law_law": "قانون↔قانون", "edge_sci_sci": "عالِم↔عالِم", "edge_law_influence": "قانون↔تأثير", "categories": "الأقسام", "edge_tag_cat": "وسم↔قسم", "preset_core": "النواة", "preset_all": "الكل"},
}



# Виды понятий единого реестра для фильтров графа (решение владельца 18.08).
# Ключи совпадают с kind в data/concepts.json — ровно 13 видов, сгруппированных
# по четырём осям. Группы не выдуманы под интерфейс: «каркас» — то, что объясняет
# (закон, принцип, теорема), «методы» — то, чем добывают, «объекты» — то, что
# изучают, «понятия» — язык, на котором говорят. Волна назвала три группы и девять
# видов; concept, math, effect и invention она не упомянула, их разложил я:
# эффект наблюдают — значит к объектам и явлениям, изобретение это прибор в
# широком смысле — к методам, а concept и math языка не имеют вовсе и образуют
# четвёртую группу. Иначе 232 понятия из 535 остались бы без единой галочки.
GRAPH_KINDS = {
    "ru": {'kinds': 'Виды:', 'g_frame': 'каркас', 'g_method': 'методы', 'g_object': 'объекты', 'g_idea': 'понятия', 'law': 'закон', 'principle': 'принцип', 'theorem': 'теорема', 'method': 'метод', 'instrument': 'прибор', 'equation': 'уравнение', 'invention': 'изобретение', 'object': 'объект', 'substance': 'вещество', 'phenomenon': 'явление', 'effect': 'эффект', 'concept': 'понятие', 'math': 'математика'},
    "en": {'kinds': 'Kinds:', 'g_frame': 'framework', 'g_method': 'methods', 'g_object': 'objects', 'g_idea': 'concepts', 'law': 'law', 'principle': 'principle', 'theorem': 'theorem', 'method': 'method', 'instrument': 'instrument', 'equation': 'equation', 'invention': 'invention', 'object': 'object', 'substance': 'substance', 'phenomenon': 'phenomenon', 'effect': 'effect', 'concept': 'concept', 'math': 'mathematics'},
    "es": {'kinds': 'Tipos:', 'g_frame': 'marco', 'g_method': 'métodos', 'g_object': 'objetos', 'g_idea': 'conceptos', 'law': 'ley', 'principle': 'principio', 'theorem': 'teorema', 'method': 'método', 'instrument': 'instrumento', 'equation': 'ecuación', 'invention': 'invención', 'object': 'objeto', 'substance': 'sustancia', 'phenomenon': 'fenómeno', 'effect': 'efecto', 'concept': 'concepto', 'math': 'matemáticas'},
    "fr": {'kinds': 'Types :', 'g_frame': 'charpente', 'g_method': 'méthodes', 'g_object': 'objets', 'g_idea': 'concepts', 'law': 'loi', 'principle': 'principe', 'theorem': 'théorème', 'method': 'méthode', 'instrument': 'instrument', 'equation': 'équation', 'invention': 'invention', 'object': 'objet', 'substance': 'substance', 'phenomenon': 'phénomène', 'effect': 'effet', 'concept': 'concept', 'math': 'mathématiques'},
    "ar": {'kinds': 'الأنواع:', 'g_frame': 'الهيكل', 'g_method': 'الطرائق', 'g_object': 'الأجسام', 'g_idea': 'المفاهيم', 'law': 'قانون', 'principle': 'مبدأ', 'theorem': 'مبرهنة', 'method': 'طريقة', 'instrument': 'أداة', 'equation': 'معادلة', 'invention': 'اختراع', 'object': 'جسم', 'substance': 'مادة', 'phenomenon': 'ظاهرة', 'effect': 'أثر', 'concept': 'مفهوم', 'math': 'رياضيات'},
    "zh": {'kinds': '种类：', 'g_frame': '骨架', 'g_method': '方法', 'g_object': '对象', 'g_idea': '概念', 'law': '定律', 'principle': '原理', 'theorem': '定理', 'method': '方法', 'instrument': '仪器', 'equation': '方程', 'invention': '发明', 'object': '物体', 'substance': '物质', 'phenomenon': '现象', 'effect': '效应', 'concept': '概念', 'math': '数学'},
}


def _graph_kind_labels(lang):
    """Подписи видов и групп для шаблона графа. Отсутствующий язык падает на английский,
    а не на пустую строку: пустая галочка без подписи выглядит как поломка вёрстки."""
    k = GRAPH_KINDS.get(lang) or GRAPH_KINDS["en"]
    out = {"kinds_label": safe(k["kinds"])}
    for g in ("frame", "method", "object", "idea"):
        out[f"group_{g}"] = safe(k[f"g_{g}"])
    for kind in ("law", "principle", "theorem", "method", "instrument", "equation",
                 "invention", "object", "substance", "phenomenon", "effect",
                 "concept", "math"):
        out[f"kind_{kind}"] = safe(k[kind])
    return out


def generate_knowledge_graph_page(lang):
    """Страница единого графа знаний (теги⇄законы⇄учёные) с тумблерами типов узлов/рёбер."""
    tpl = load_template("graph-explorer")
    if not tpl.template:
        return
    loc = GRAPH_LABELS.get(lang, GRAPH_LABELS["en"])
    (Path(LANG_DIR) / lang / "graph").mkdir(parents=True, exist_ok=True)
    _write_text_retry(Path(LANG_DIR) / lang / "graph" / "index.html", tpl.substitute(
        lang=lang, dir=dir_for(lang), goatcounter=GOATCOUNTER, authors_lang="en", asset_ver=asset_ver(),
        fav_title=safe(nav_fav_title(lang)),
        version_toggle_html="",
        graph_title=safe(loc["title"]), graph_subtitle=safe(loc["subtitle"]),
        nodes_label=safe(loc["nodes"]), edges_label=safe(loc["edges"]), presets_label=safe(loc["presets"]),
        tags_label=safe(loc["tags"]), laws_label=safe(loc["laws"]), scientists_label=safe(loc["scientists"]),
        search_tag_placeholder=safe(loc["search_tag"]), search_law_placeholder=safe(loc["search_law"]),
        search_sci_placeholder=safe(loc["search_sci"]), depth_label=safe(loc["depth"]), clear_label=safe(loc["clear"]),
        footer_text=safe(loc["footer"]), graph_warning=safe(loc["warning"]),
        edge_tag_law=safe(loc["edge_tag_law"]), edge_tag_sci=safe(loc["edge_tag_sci"]), edge_law_sci=safe(loc["edge_law_sci"]),
        edge_tag_tag=safe(loc["edge_tag_tag"]), edge_law_law=safe(loc["edge_law_law"]), edge_sci_sci=safe(loc["edge_sci_sci"]),
        edge_law_influence=safe(loc["edge_law_influence"]), preset_core=safe(loc["preset_core"]), preset_all=safe(loc["preset_all"]),
        **_graph_kind_labels(lang),
        loading_text=safe(LOADING_LABEL.get(lang, LOADING_LABEL["en"]))
    ), encoding="utf-8")


def build_knowledge_graph_data():
    """Пересобрать data/knowledge-graph.json (офлайн). Обёртка над build_knowledge_graph.py."""
    try:
        import build_knowledge_graph
        build_knowledge_graph.main()
    except Exception as e:
        print(f"  ⚠️ knowledge-graph не собран: {e}")


def generate_scientists_cloud(lang):
    tpl = load_template("scientists-cloud")
    if not tpl.template: return
    sp = Path(f"lang/{lang}/data/scientists.json")
    if not sp.exists(): sp = Path(f"lang/{DEFAULT_LANG}/data/scientists.json")
    scientists = json.loads(sp.read_text(encoding="utf-8"))

    # Счётчики статей по учёным
    index = load_index(lang)
    sci_counts = {}
    for a in index:
        for sid in a.get("scientists", []):
            sci_counts[sid] = sci_counts.get(sid, 0) + 1

    # Компактный колоночный список, группировка по первой букве имени (как авторы A–Z).
    # Имена учёных — ТОЛЬКО оригинальное английское (id) во всех языках, не переводим.
    def sci_row(sid, data):
        cnt = sci_counts.get(sid, 0)
        count_html = f'<span class="cat-chip-n">{cnt}</span>' if cnt else ""
        return (f'<a href="/{LANG_DIR}/{lang}/scientists/{attr_safe(author_slug(sid))}.html" class="scientist-item" '
                f'data-scientist="{attr_safe(sid)}"><span>{safe(sid)}</span>{count_html}</a>\n')

    ordered = sorted(scientists.items(), key=lambda kv: kv[0])
    cloud_html = ""
    cur_letter = None
    for sid, data in ordered:
        letter = (sid[:1] or "?").upper()
        if letter != cur_letter:
            cloud_html += f'<div class="cloud-group-label">{safe(letter)}</div>\n'
            cur_letter = letter
        cloud_html += sci_row(sid, data)
    loc = {
        "en": {"title": "Scientists", "subtitle": "Great minds behind the discoveries.",
               "search": "Find scientists...", "footer": "science made simple"},
        "es": {"title": "Científicos", "subtitle": "Las grandes mentes detrás de los descubrimientos.",
               "search": "Buscar científicos...", "footer": "ciencia en palabras sencillas"},
        "ru": {"title": "Учёные", "subtitle": "Великие умы стоящие за открытиями.", "search": "Найти учёных...",
               "footer": "наука простыми словами"},
        "zh": {"title": "科学家", "subtitle": "发现背后的伟大头脑。", "search": "查找科学家...",
               "footer": "让科学变简单"},
        "fr": {"title": "Scientifiques", "subtitle": "Les grands esprits derrière les découvertes.",
               "search": "Rechercher des scientifiques...", "footer": "la science simplifiée"},
        "ar": {"title": "العلماء", "subtitle": "العقول العظيمة وراء الاكتشافات.",
               "search": "ابحث عن علماء...", "footer": "العلم ببساطة"}
    }.get(lang, {"title": "Scientists", "subtitle": "", "search": "Find...", "footer": ""})
    _write_text_retry(Path(LANG_DIR) / lang / "scientists" / "index.html", tpl.substitute(
        lang=lang, dir=dir_for(lang), goatcounter=GOATCOUNTER, authors_lang="en", asset_ver=asset_ver(),
        fav_title=safe(nav_fav_title(lang)),
        version_toggle_html="",
        scientists_title=safe(loc["title"]), scientists_subtitle=safe(loc["subtitle"]),
        search_placeholder=safe(loc["search"]), scientists_cloud_html=cloud_html,
        footer_text=safe(loc["footer"]),
        mini_graph_filters_html=mini_graph_filters_html(lang, None)
    ), encoding="utf-8")


_PRESENT_LABEL = {"ru": "настоящее время", "en": "present", "es": "presente",
                  "ar": "الحاضر", "fr": "présent", "zh": "至今"}
def localize_present(lifespan, lang):
    """Годы жизни хранятся одной строкой (не переводятся) — у живущих учёных там русское
    «настоящее время». Локализуем этот токен под язык страницы (юзер-фидбек 2026-07-22)."""
    if not lifespan or lang == "ru":
        return lifespan
    return lifespan.replace("настоящее время", _PRESENT_LABEL.get(lang, "present"))

def generate_scientist_page(sid, lang):
    tpl = load_template("scientist")
    if not tpl.template: return
    sp = Path(f"lang/{lang}/data/scientists.json")
    if not sp.exists(): sp = Path(f"lang/{DEFAULT_LANG}/data/scientists.json")
    scientists = json.loads(sp.read_text(encoding="utf-8"))
    data = scientists.get(sid, {})
    if not data: return
    tags_loc = load_tags_loc(lang)
    related_tags_links = [
        f'<a href="/{LANG_DIR}/{lang}/tags/{t}.html" data-tag="{attr_safe(t)}">{tags_loc.get(t, {}).get("name", t)}</a>'
        for t in data.get("related_tags", [])[:8]
    ]
    lp = Path(f"lang/{lang}/data/laws.json")
    if not lp.exists(): lp = Path(f"lang/{DEFAULT_LANG}/data/laws.json")
    laws_data = json.loads(lp.read_text(encoding="utf-8")) if lp.exists() else {}
    related_laws_links = [
        f'<a href="/{LANG_DIR}/{lang}/laws/{attr_safe(lid)}.html" class="law-chip" data-law="{attr_safe(lid)}">{safe(ld.get("name", lid))}</a>'
        for lid, ld in laws_data.items()
        if sid in ld.get("scientists", []) or sid in ld.get("influenced_by", [])
    ]
    index = load_index(lang)
    articles_html = ""
    for a in index:
        if sid in a.get("scientists", []) and a.get("version") == "popular":
            articles_html += entity_article_card(a, lang)
    loc = {
        "en": {"related": "Related tags", "related_laws": "Related laws", "related_scientists": "Related scientists", "discoveries": "Key discoveries", "bio": "Biography", "quote": "Quote",
               "search": "Search...", "hint": "! scientist · # tag · @ author", "footer": "science made simple",
               "no_articles": "No articles yet", "articles": "Related articles"},
        "es": {"related": "Etiquetas relacionadas", "related_laws": "Leyes relacionadas",
               "related_scientists": "Científicos relacionados", "discoveries": "Descubrimientos clave",
               "bio": "Biografía", "quote": "Cita",
               "search": "Buscar...", "hint": "! científico · # etiqueta · @ autor",
               "footer": "ciencia en palabras sencillas",
               "no_articles": "Aún no hay artículos", "articles": "Artículos relacionados"},
        "ar": {"related": "وسوم ذات صلة", "related_laws": "قوانين ذات صلة", "related_scientists": "علماء ذوو صلة", "discoveries": "اكتشافات رئيسية", "bio": "سيرة", "quote": "اقتباس",
               "search": "بحث...", "hint": "! عالم · # وسم · @ مؤلف", "footer": "العلم ببساطة",
               "no_articles": "لا مقالات بعد", "articles": "مقالات ذات صلة"},
        "ru": {"related": "Связанные теги", "related_laws": "Связанные законы", "related_scientists": "Связанные учёные", "discoveries": "Ключевые открытия", "bio": "Биография", "quote": "Цитата",
               "search": "Поиск...", "hint": "! учёный · # тег · @ автор", "footer": "наука простыми словами",
               "no_articles": "Пока нет статей", "articles": "Статьи с его участием"},
        "zh": {"related": "相关标签", "related_laws": "相关定律", "related_scientists": "相关科学家", "discoveries": "重要发现", "bio": "生平", "quote": "名言",
               "search": "搜索...", "hint": "! 科学家 · # 标签 · @ 作者", "footer": "让科学变简单",
               "no_articles": "暂无文章", "articles": "相关文章"},
        "fr": {"related": "Tags associés", "related_laws": "Lois associées", "related_scientists": "Scientifiques associés", "discoveries": "Découvertes clés", "bio": "Biographie", "quote": "Citation",
               "search": "Rechercher...", "hint": "! scientifique · # tag · @ auteur", "footer": "la science simplifiée",
               "no_articles": "Pas encore d'articles", "articles": "Articles liés"}
    }.get(lang, {"related": "Related", "related_laws": "Related laws", "related_scientists": "Related scientists", "discoveries": "Discoveries", "bio": "Biography", "quote": "Quote",
                 "search": "Search...", "hint": "! scientist · # tag · @ author", "footer": "",
                 "no_articles": "No articles yet", "articles": "Related articles"})

    my_tags = set(data.get("related_tags", []))
    related_scientists = [
        other_sid for other_sid, other in scientists.items()
        if other_sid != sid and my_tags & set(other.get("related_tags", []))
    ]
    related_scientists_links = [
        f'<a href="/{LANG_DIR}/{lang}/scientists/{attr_safe(author_slug(s))}.html" class="text-scientist" data-scientist="{attr_safe(s)}">{safe(s)}</a>'
        for s in related_scientists[:8]
    ]
    related_scientists_html = related_row(loc["related_scientists"], related_scientists_links)
    related_tags_block = related_row(loc["related"], related_tags_links)
    related_laws_block = related_row(loc.get("related_laws", "Related laws"), related_laws_links)

    # Правый сайдбар (как на статье/законе/теге): связанные теги + законы + учёные плашками-колонкой.
    side_tag_chips = [
        f'<a href="/{LANG_DIR}/{lang}/tags/{attr_safe(t)}.html" class="side-tag" data-tag="{attr_safe(t)}">'
        f'{safe(tags_loc.get(t, {}).get("name", t))}</a>' for t in data.get("related_tags", [])[:8]]
    side_law_chips = [
        f'<a href="/{LANG_DIR}/{lang}/laws/{attr_safe(lid)}.html" class="side-law" data-law="{attr_safe(lid)}">'
        f'{safe(ld.get("name", lid))}</a>'
        for lid, ld in laws_data.items() if sid in ld.get("scientists", []) or sid in ld.get("influenced_by", [])][:6]
    side_sci_chips = [
        f'<a href="/{LANG_DIR}/{lang}/scientists/{attr_safe(author_slug(s))}.html" class="side-sci" '
        f'data-scientist="{attr_safe(s)}">{safe(s)}</a>' for s in related_scientists[:8]]
    entity_side_html = (
        side_chip_group(side_label("tags", lang), side_tag_chips)
        + side_chip_group(side_label("laws", lang), side_law_chips)
        + side_chip_group(side_label("sci", lang), side_sci_chips)
    )

    _sci_quote = (data.get("quote") or "").strip()
    sci_like_id = f"{author_slug(sid)}_{lang}_page"
    actions_html = build_actions_html(sci_like_id, sid, lang, "scientist", inline_comment=True)
    feedback_html = build_feedback_html(sci_like_id, lang, "scientist", inline_toggle=True)
    og_meta_html = build_og_meta(
        f'{sid} — bridge42worlds', data.get("description", ""),
        f"{SITE_URL}/{LANG_DIR}/{lang}/scientists/{author_slug(sid)}.html")

    _write_text_retry(Path(LANG_DIR) / lang / "scientists" / f"{author_slug(sid)}.html", tpl.substitute(
        lang=lang, dir=dir_for(lang), goatcounter=GOATCOUNTER, authors_lang="en", asset_ver=asset_ver(),
        fav_title=safe(nav_fav_title(lang)),
        og_meta_html=og_meta_html, entity_side_html=entity_side_html,
        articles_label=safe(loc.get("articles", loc.get("related", "Articles"))),
        scientist_id=attr_safe(sid),
        version_toggle_html=level_switch_spans(lang, "popular"),
        actions_html=actions_html, feedback_html=feedback_html, share_label=safe(share_label_for(lang)),
        scientist_name=safe(sid), entity_kind_html=entity_kind_html("scientist", lang), lifespan=safe(localize_present(data.get("lifespan", ""), lang)),
        fields=", ".join(as_list(data.get("fields", []))),
        scientist_description=safe(data.get("description", "")),
        scientist_biography=safe(data.get("biography", "")),
        scientist_discoveries="".join(f"<li>{safe(d)}</li>" for d in as_list(data.get("key_discoveries", []))),
        # Пустая цитата печатала голое `Цитата: ""` — блок из одних кавычек. Строим ряд
        # целиком здесь, чтобы при отсутствии цитаты его не было вовсе.
        scientist_quote_html=(f'<div class="quote" aria-label="{attr_safe(loc["quote"])}">'
                              f'"{safe(_sci_quote)}"</div>' if _sci_quote else ""),
        scientist_fun_fact=safe(data.get("fun_fact", "")),
        discoveries_label=safe(loc["discoveries"]), bio_label=safe(loc["bio"]),
        quote_label=safe(loc["quote"]),
        related_tags_block=related_tags_block, related_laws_block=related_laws_block,
        related_scientists_html=related_scientists_html,
        search_placeholder=safe(loc["search"]),
        search_hint=safe(loc["hint"]), graph_mini_label=safe(MINI_LABEL.get(lang, MINI_LABEL["en"])),
        mini_graph_filters_html=mini_graph_filters_html(lang, "sci"),
        articles_list_html=articles_html or f'<p>{safe(loc["no_articles"])}</p>', footer_text=safe(loc["footer"])
    ), encoding="utf-8")


def update_all_scientists(lang):
    (Path(LANG_DIR) / lang / "scientists").mkdir(parents=True, exist_ok=True)
    generate_scientists_cloud(lang)
    sp = Path(f"lang/{lang}/data/scientists.json")
    if not sp.exists(): sp = Path(f"lang/{DEFAULT_LANG}/data/scientists.json")
    for sid in json.loads(sp.read_text(encoding="utf-8")): generate_scientist_page(sid, lang)
    print(f"  👨‍🔬 Scientists updated for {lang}")


# ── Разделы arXiv (отдельные страницы, как теги/законы/учёные) ──────────────────────────────
# Категории arXiv — стандартная англоязычная таксономия (ARXIV_CATEGORIES/DESCRIPTIONS в gen_base).
# Раньше из-за этого имена и описания разделов оставались английскими на ВСЕХ языках: русская
# страница раздела открывалась заголовком "Superconductivity" (юзер-фидбек 2026-07-23: "почему
# тут нет текста"). Переводы лежат отдельными файлами data/arxiv-categories-{lang}.json и
# data/arxiv-category-descriptions-{lang}.json; английский набор из gen_base остаётся базой и
# фоллбэком на любой недостающий ключ, так что новая категория никогда не выпадет в пустоту.
# id вида "astro-ph.HE" → слаг с "_" вместо ".".
_CAT_LOC_CACHE = {}


def cat_loc(lang):
    if lang not in _CAT_LOC_CACHE:
        def load(p):
            f = Path(p)
            try:
                return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
            except json.JSONDecodeError:
                print(f"  ⚠️ битый {p} — раздел останется по-английски")
                return {}
        _CAT_LOC_CACHE[lang] = (load(f"data/arxiv-categories-{lang}.json"),
                                load(f"data/arxiv-category-descriptions-{lang}.json"))
    return _CAT_LOC_CACHE[lang]


def cat_name(cat, lang):
    return cat_loc(lang)[0].get(cat) or ARXIV_CATEGORIES.get(cat, cat)


def cat_desc(cat, lang):
    return cat_loc(lang)[1].get(cat) or ARXIV_CATEGORY_DESCRIPTIONS.get(cat, "")


def section_slug(cat):
    return cat.replace(".", "_").replace("/", "_")


SECTION_LOC = {
    "en": {"search": "Search articles...", "hint": "# tag · @ author · ! scientist", "articles": "articles",
           "no_articles": "No articles yet", "title": "Sections",
           "subtitle": "arXiv subject categories — browse articles by field.", "footer": "science made simple",
           "name_col": "Section", "code_col": "arXiv code", "count_col": "Articles"},
    "ru": {"search": "Поиск статей...", "hint": "# тег · @ автор · ! учёный", "articles": "статей",
           "no_articles": "Пока нет статей", "title": "Разделы",
           "subtitle": "Разделы arXiv — статьи по областям науки.", "footer": "наука простыми словами",
           "name_col": "Раздел", "code_col": "Код arXiv", "count_col": "Статей"},
    "es": {"search": "Buscar artículos...", "hint": "# etiqueta · @ autor · ! científico", "articles": "artículos",
           "no_articles": "Aún no hay artículos", "title": "Secciones",
           "subtitle": "Categorías de arXiv — artículos por campo.", "footer": "la ciencia simplificada",
           "name_col": "Sección", "code_col": "Código arXiv", "count_col": "Artículos"},
    "ar": {"search": "ابحث عن مقالات...", "hint": "# وسم · @ مؤلف · ! عالم", "articles": "مقالات",
           "no_articles": "لا مقالات بعد", "title": "الأقسام",
           "subtitle": "تصنيفات arXiv — تصفح المقالات حسب المجال.", "footer": "العلم ببساطة",
           "name_col": "القسم", "code_col": "رمز arXiv", "count_col": "المقالات"},
}


def _section_loc(lang):
    return SECTION_LOC.get(lang, SECTION_LOC["en"])


def generate_section_page(cat, lang, index=None):
    tpl = load_template("section")
    if not tpl.template: return
    if index is None:
        ip = Path(LANG_DIR) / lang / "articles-index.json"
        index = json.loads(ip.read_text(encoding="utf-8")) if ip.exists() else []
    loc = _section_loc(lang)
    seen, articles_html, count = set(), "", 0
    for a in index:
        if a.get("version") != "popular": continue
        if cat not in (a.get("categories") or []): continue
        if a["id"] in seen: continue
        seen.add(a["id"]); count += 1
        articles_html += (
            entity_article_card(a, lang)
        )
    (Path(LANG_DIR) / lang / "sections").mkdir(parents=True, exist_ok=True)
    _write_text_retry(Path(LANG_DIR) / lang / "sections" / f"{section_slug(cat)}.html", tpl.substitute(
        lang=lang, dir=dir_for(lang), goatcounter=GOATCOUNTER, authors_lang="en", asset_ver=asset_ver(),
        fav_title=safe(nav_fav_title(lang)),
        version_toggle_html=level_switch_spans(lang, "popular"),
        section_name=safe(cat_name(cat, lang)), section_id=safe(cat),
        section_desc=safe(cat_desc(cat, lang)),
        article_count=count, articles_label=safe(loc["articles"]),
        tag_stats_html=(f'<div class="tag-stats"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><line x1="6.5" y1="19" x2="6.5" y2="13"/><line x1="12" y1="19" x2="12" y2="8.5"/><line x1="17.5" y1="19" x2="17.5" y2="11"/><line x1="4" y1="19.5" x2="20" y2="19.5"/></svg> <a class="stat-jump" href="#article-list">{count} {safe(loc["articles"])}</a></div>'
                         if count else ""),
        search_placeholder=safe(loc["search"]), search_hint=safe(loc["hint"]),
        articles_list_html=articles_html or f'<p>{safe(loc["no_articles"])}</p>',
        footer_text=safe(loc["footer"]),
    ), encoding="utf-8")


def generate_sections_cloud(lang):
    tpl = load_template("sections-cloud")
    if not tpl.template: return
    ip = Path(LANG_DIR) / lang / "articles-index.json"
    index = json.loads(ip.read_text(encoding="utf-8")) if ip.exists() else []
    counts = {}
    for a in index:
        if a.get("version") != "popular": continue
        for c in (a.get("categories") or []):
            counts[c] = counts.get(c, 0) + 1
    loc = _section_loc(lang)
    # Табличный вид (юзер-фидбек 2026-07-21): облако плашек не различало math.MP и math-ph
    # визуально (оба показывают имя "Math Physics") — колонка с сырым arXiv-кодом устраняет
    # дубль наглядно, коды у них разные, хотя канонические англ. имена совпадают намеренно.
    # Группировка по префиксу кода до точки (astro-ph.HE → группа «astro-ph»), внутри — по коду.
    # Заголовок группы = префикс + человекочитаемое имя (юзер-фидбек 2026-07-22).
    groups = {}
    for c in counts:
        groups.setdefault(c.split(".")[0], []).append(c)
    rows = ""
    for prefix in sorted(groups.keys()):
        members = sorted(groups[prefix])
        gtotal = sum(counts[c] for c in members)
        gname = cat_loc(lang)[0].get(prefix) or ARXIV_CATEGORIES.get(prefix, "") or section_group_name(prefix, lang)
        # Группы РАСКРЫВАЕМЫЕ (юзер 2026-07-24): клик по строке-группе разворачивает её разделы.
        # По умолчанию свёрнуто — видно только группы (компактно), члены hidden с классом sm-<prefix>.
        rows += (
            f'<tr class="section-group" data-group="{attr_safe(prefix)}">'
            f'<td colspan="2"><span class="sg-caret">▸</span> '
            f'<span class="section-group-code">{safe(prefix)}</span>'
            + (f' <span class="section-group-name">{safe(gname)}</span>' if gname and gname != prefix else "")
            + f'</td><td class="section-count">{gtotal}</td></tr>'
        )
        for c in members:
            rows += (
                f'<tr class="section-member sm-{attr_safe(prefix)}" hidden>'
                f'<td><a href="/{LANG_DIR}/{lang}/sections/{section_slug(c)}.html" '
                f'title="{attr_safe(cat_desc(c, lang))}">{safe(cat_name(c, lang))}</a></td>'
                f'<td class="section-code">{safe(c)}</td>'
                f'<td class="section-count">{counts[c]}</td></tr>'
            )
    (Path(LANG_DIR) / lang / "sections").mkdir(parents=True, exist_ok=True)
    _write_text_retry(Path(LANG_DIR) / lang / "sections" / "index.html", tpl.substitute(
        lang=lang, dir=dir_for(lang), goatcounter=GOATCOUNTER, authors_lang="en", asset_ver=asset_ver(),
        fav_title=safe(nav_fav_title(lang)),
        version_toggle_html="",
        sections_title=safe(loc["title"]), sections_subtitle=safe(loc["subtitle"]),
        name_col=safe(loc["name_col"]), code_col=safe(loc["code_col"]), count_col=safe(loc["count_col"]),
        sections_cloud_html=rows, footer_text=safe(loc["footer"]),
    ), encoding="utf-8")


def update_all_sections(lang):
    generate_sections_cloud(lang)
    ip = Path(LANG_DIR) / lang / "articles-index.json"
    index = json.loads(ip.read_text(encoding="utf-8")) if ip.exists() else []
    cats = set()
    for a in index:
        if a.get("version") != "popular": continue
        for c in (a.get("categories") or []):
            cats.add(c)
    for c in cats:
        generate_section_page(c, lang, index)
    print(f"  🗂️ Sections updated for {lang} ({len(cats)} pages)")


def update_all_authors():
    # Страницы авторов теперь генерятся НА КАЖДОМ ЯЗЫКЕ (юзер-фидбек 2026-07-20: клик по автору
    # с ar/es статьи не должен переключать на русский и не должен 404-ить). Хром/подписи/чипы —
    # локализованы, ссылки и список статей — в языке страницы. Тег-ID языко-независимы, имена —
    # из tags_loc[lang]. Граф авторов (authors-graph.json) собирается ОДИН раз, до цикла языков.
    tpl_cloud, tpl_page = load_template("authors-cloud"), load_template("author")
    if not tpl_cloud.template or not tpl_page.template:
        return
    LOC = {
        "en": {"title": "Authors", "subtitle": "Researchers publishing on arXiv.", "find": "Find authors...",
               "search": "Search articles...", "hint": "@ author · # tag · ! scientist",
               "coauthors": "Co-authors", "no_articles": "No articles yet", "footer": "science made simple",
               "articles": "articles", "coauthors_word": "co-authors", "tags": "Tags", "laws": "Laws",
               "default_hint": 'Showing authors starting with "{letter}" — search above covers everyone.'},
        "ru": {"title": "Авторы", "subtitle": "Исследователи, публикующиеся в arXiv.", "find": "Найти авторов...",
               "search": "Поиск статей...", "hint": "@ автор · # тег · ! учёный",
               "coauthors": "Соавторы", "no_articles": "Пока нет статей", "footer": "наука простыми словами",
               "articles": "статей", "coauthors_word": "соавторов", "tags": "Теги", "laws": "Законы",
               "default_hint": 'Показаны авторы на «{letter}» — поиск выше ищет среди всех.'},
        "es": {"title": "Autores", "subtitle": "Investigadores que publican en arXiv.", "find": "Buscar autores...",
               "search": "Buscar artículos...", "hint": "@ autor · # etiqueta · ! científico",
               "coauthors": "Coautores", "no_articles": "Aún no hay artículos", "footer": "la ciencia simplificada",
               "articles": "artículos", "coauthors_word": "coautores", "tags": "Etiquetas", "laws": "Leyes",
               "default_hint": 'Autores que empiezan por «{letter}» — la búsqueda de arriba cubre a todos.'},
        "ar": {"title": "المؤلفون", "subtitle": "باحثون ينشرون على arXiv.", "find": "ابحث عن مؤلفين...",
               "search": "ابحث عن مقالات...", "hint": "@ مؤلف · # وسم · ! عالم",
               "coauthors": "مؤلفون مشاركون", "no_articles": "لا مقالات بعد", "footer": "العلم ببساطة",
               "articles": "مقالات", "coauthors_word": "مؤلفين مشاركين", "tags": "الوسوم", "laws": "القوانين",
               "default_hint": 'عرض المؤلفين الذين تبدأ أسماؤهم بـ «{letter}» — البحث أعلاه يغطي الجميع.'},
        "zh": {"title": "作者", "subtitle": "在 arXiv 上发表论文的研究人员。", "find": "查找作者...",
               "search": "搜索文章...", "hint": "@ 作者 · # 标签 · ! 科学家",
               "coauthors": "合著者", "no_articles": "暂无文章", "footer": "让科学变简单",
               "articles": "篇文章", "coauthors_word": "位合著者", "tags": "标签", "laws": "定律",
               "default_hint": '显示以「{letter}」开头的作者 — 上方搜索涵盖所有作者。'},
        "fr": {"title": "Auteurs", "subtitle": "Chercheurs publiant sur arXiv.", "find": "Rechercher des auteurs...",
               "search": "Rechercher des articles...", "hint": "@ auteur · # tag · ! scientifique",
               "coauthors": "Co-auteurs", "no_articles": "Pas encore d'articles", "footer": "la science simplifiée",
               "articles": "articles", "coauthors_word": "co-auteurs", "tags": "Tags", "laws": "Lois",
               "default_hint": 'Auteurs commençant par « {letter} » — la recherche ci-dessus couvre tout le monde.'},
    }
    LAST = {"ru": "последняя", "en": "latest", "es": "último", "ar": "الأحدث", "zh": "最新", "fr": "dernière"}
    COUNT_LBL = {"ru": "авторов", "en": "authors", "es": "autores", "ar": "مؤلفين", "zh": "位作者", "fr": "auteurs"}

    ap = Path("data/authors-graph.json")
    graph = json.loads(ap.read_text(encoding="utf-8")) if ap.exists() else {}

    # id -> дата и id -> теги — из индекса ЯЗЫКА ПО УМОЛЧАНИЮ (тег-ID и даты языко-независимы).
    id_date, id_tags = {}, {}
    di = Path(LANG_DIR) / DEFAULT_LANG / "articles-index.json"
    if di.exists():
        for a in json.loads(di.read_text(encoding="utf-8")):
            id_date[a["id"]] = a["date"]
            id_tags[a["id"]] = [t for t in a.get("tags", []) if t]

    def last_date_of(d):
        ds = [id_date.get(i, "") for i in d.get("articles", [])]
        ds = [x for x in ds if x]
        return max(ds) if ds else ""

    authors = sorted([{"name": n, "count": d.get("article_count", 0), "last": last_date_of(d),
                       "tags": list(dict.fromkeys(t for aid in d.get("articles", [])
                                                  for t in id_tags.get(aid, [])))}
                      for n, d in graph.items()], key=lambda x: x["name"].lower())

    sections = {}
    for a in authors:
        letter = a["name"][0].upper() if a["name"] else "#"
        if letter < "A" or letter > "Z":
            letter = "#"
        sections.setdefault(letter, []).append(a)
    ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    letters_with_content = [l for l in ALPHABET if sections.get(l)]
    # Детерминированный дефолтный ярус (наименьшая непустая буква по числу авторов) — раньше был
    # random.choice, из-за чего страница authors/index.html менялась КАЖДЫЙ регенер (git-шум × языки).
    default_letter = min(letters_with_content, key=lambda l: len(sections[l])) if letters_with_content else None

    # Индекс статей по языкам — один раз (список статей автора рендерим в языке страницы).
    articles_by_lang = {}
    for lc in LANGUAGES:
        ip = Path(LANG_DIR) / lc / "articles-index.json"
        if ip.exists():
            articles_by_lang[lc] = {a["id"]: a for a in json.loads(ip.read_text(encoding="utf-8"))}

    for lang in ["en"]:  # авторы ТОЛЬКО на en (юзер 2026-07-25: en-версия одна, ссылки со всех языков ведут сюда)
        (Path(LANG_DIR) / lang / "authors").mkdir(parents=True, exist_ok=True)
        loc = LOC.get(lang, LOC["en"])
        tags_loc = load_tags_loc(lang)
        laws_loc = load_laws_loc(lang)
        last_label = LAST.get(lang, "latest")
        author_count_label = COUNT_LBL.get(lang, "authors")
        lbase = LANG_DIR + "/" + lang

        def gen_alphabet_nav(active_letter=None):
            parts = []
            for l in ALPHABET:
                count = len(sections.get(l, []))
                cls = " active" if active_letter == l else ""
                href = f"/{lbase}/authors/{l.lower()}.html"
                if count:
                    parts.append(f'<a href="{href}" class="alpha-link{cls}" data-letter="{l}">{l}</a>')
                else:
                    parts.append(f'<span class="alpha-link alpha-empty">{l}</span>')
            if sections.get("#"):
                cls = " active" if active_letter == "#" else ""
                parts.append(f'<a href="/{lbase}/authors/other.html" class="alpha-link{cls}" data-letter="#">#</a>')
            return "".join(parts)

        def gen_letter_section(letter):
            items = sections.get(letter, [])
            if not items:
                return ""
            def author_tags_html(a):
                return " · ".join(
                    '<span onclick="event.stopPropagation();window.location=`/{}/tags/{}.html`" class="text-tag" data-tag="{}">{}</span>'.format(
                        lbase, t, t, safe(tags_loc.get(t, {}).get("name", t)))
                    for t in a.get("tags", [])[:6])
            rows = "".join(
                '<a href="/{}/authors/{}.html" class="author-row" data-author="{}">'
                '<span class="author-name">{}</span><span class="author-tags">{}</span>'
                '<span class="author-count">{} {}</span></a>'.format(
                    lbase, author_slug(a["name"]), attr_safe(a["name"]),
                    safe(a["name"]), author_tags_html(a), a["count"], safe(loc["articles"]))
                for a in items)
            return f'<div class="letter-section" id="letter-{letter}"><h2 class="letter-heading">{letter}</h2><div class="author-list">{rows}</div></div>'

        # Облако авторов (index) — один дефолтный ярус (поиск на странице ищет по всем через граф).
        index_subtitle = loc["subtitle"] + (
            " " + loc["default_hint"].format(letter=default_letter) if default_letter else "")
        _write_text_retry(Path(LANG_DIR) / lang / "authors" / "index.html", tpl_cloud.substitute(
            lang=lang, dir=dir_for(lang), goatcounter=GOATCOUNTER, authors_lang="en", asset_ver=asset_ver(),
            fav_title=safe(nav_fav_title(lang)),
            version_toggle_html="",
            page_title=safe(loc["title"]), authors_title=safe(loc["title"]),
            authors_subtitle=safe(index_subtitle), alphabet_nav_html=gen_alphabet_nav(),
            search_placeholder=safe(loc["find"]),
            author_sections_html=gen_letter_section(default_letter) if default_letter else "",
            footer_text=safe(loc["footer"])
        ), encoding="utf-8")

        for letter in letters_with_content:
            _write_text_retry(Path(LANG_DIR) / lang / "authors" / f"{letter.lower()}.html", tpl_cloud.substitute(
                lang=lang, dir=dir_for(lang), goatcounter=GOATCOUNTER, authors_lang="en", asset_ver=asset_ver(),
                fav_title=safe(nav_fav_title(lang)),
                version_toggle_html="",
                page_title=safe(f"{loc['title']} — {letter}"), authors_title=loc["title"],
                authors_subtitle=safe(f"{letter} — {len(sections[letter])} {author_count_label}"),
                alphabet_nav_html=gen_alphabet_nav(active_letter=letter), search_placeholder=safe(loc["find"]),
                author_sections_html=gen_letter_section(letter), footer_text=safe(loc["footer"])
            ), encoding="utf-8")
        if sections.get("#"):
            _write_text_retry(Path(LANG_DIR) / lang / "authors" / "other.html", tpl_cloud.substitute(
                lang=lang, dir=dir_for(lang), goatcounter=GOATCOUNTER, authors_lang="en", asset_ver=asset_ver(),
                fav_title=safe(nav_fav_title(lang)),
                version_toggle_html="",
                page_title=safe(f"{loc['title']} — #"), authors_title=loc["title"],
                authors_subtitle=safe(f"# — {len(sections['#'])} {author_count_label}"),
                alphabet_nav_html=gen_alphabet_nav(active_letter="#"), search_placeholder=safe(loc["find"]),
                author_sections_html=gen_letter_section("#"), footer_text=safe(loc["footer"])
            ), encoding="utf-8")

        # Индивидуальные страницы авторов — тонкие: список статей ЭТОГО языка (search.js всё равно
        # перерисует в языке страницы по data-context-author), чипы соавторов/тегов/законов локализованы.
        by_id = articles_by_lang.get(lang, {})
        for author_name, data in graph.items():
            slug = author_slug(author_name)
            articles_html = "".join(
                entity_article_card(a, lang)
                for a in (by_id.get(aid) for aid in data.get("articles", [])) if a
            )
            coauthors_html = " · ".join(
                f'<a href="/{lbase}/authors/{author_slug(ca)}.html" data-author="{attr_safe(ca)}">{ca}</a>'
                for ca in data.get("coauthors", [])[:15]
            )
            author_tags = []
            for aid in data.get("articles", []):
                for t in id_tags.get(aid, []):
                    if t not in author_tags:
                        author_tags.append(t)
            author_tags_set = set(author_tags)
            author_tags_html = " · ".join(
                f'<a href="/{lbase}/tags/{attr_safe(t)}.html" data-tag="{attr_safe(t)}">{safe(tags_loc.get(t, {}).get("name", t))}</a>'
                for t in author_tags[:20]
            )
            author_law_ids = [lid for lid, L in laws_loc.items() if set(L.get("tags", [])) & author_tags_set]
            author_laws_html = " · ".join(
                f'<a href="/{lbase}/laws/{attr_safe(lid)}.html" class="law-chip" data-law="{attr_safe(lid)}">{safe(laws_loc[lid].get("name", lid))}</a>'
                for lid in author_law_ids[:20]
            )
            # Описание для выдачи: сколько работ и о чём. Без него поисковик собирает сниппет
            # из случайного куска страницы, а человек, нашедший себя по имени, должен сразу
            # понимать, что он нашёл.
            n_art = len(data.get("articles", []))
            topics = ", ".join(
                str(tags_loc.get(t, {}).get("name", t)) for t in author_tags[:3]
            )
            author_desc = (
                f"{author_name}: {n_art} " + ("paper" if n_art == 1 else "papers")
                + " retold in plain language"
                + (f" — {topics}" if topics else "")
                + ". Free to read at bridge42worlds."
            )
            _write_text_retry(Path(LANG_DIR) / lang / "authors" / f"{slug}.html", tpl_page.substitute(
                author_desc=attr_safe(author_desc),
                author_url=f"{SITE_URL}/{LANG_DIR}/en/authors/{slug}.html",
                lang=lang, dir=dir_for(lang), goatcounter=GOATCOUNTER, authors_lang="en", asset_ver=asset_ver(),
                fav_title=safe(nav_fav_title(lang)),
                version_toggle_html="",
                author_slug=attr_safe(slug),
                author_name=author_name, author_name_attr=attr_safe(author_name),
                author_tags_attr=attr_safe(",".join(author_tags)),
                graph_mini_label=safe(MINI_LABEL.get(lang, MINI_LABEL["en"])),
                article_count=len(data.get("articles", [])),
                articles_label=safe(loc["articles"]), coauthors_word=safe(loc["coauthors_word"]),
                last_seen=f'{last_label}: {last_date_of(data)}' if last_date_of(data) else '',
                coauthor_count=len(data.get("coauthors", [])), coauthors_label=safe(loc["coauthors"]),
                coauthors_html=coauthors_html, search_placeholder=safe(loc["search"]),
                search_hint=safe(loc["hint"]),
                # Раньше пустой ряд подменялся прочерком — при подписи «Теги:» это читалось,
                # без подписи ряд из одного «—» бессмыслен. Отдаём пусто: .related-tags:empty
                # скрывает такой ряд целиком.
                tags_label=safe(loc["tags"]), author_tags_html=author_tags_html,
                laws_label=safe(loc["laws"]), author_laws_html=author_laws_html,
                articles_list_html=articles_html or f'<p>{safe(loc["no_articles"])}</p>',
                footer_text=safe(loc["footer"])
            ), encoding="utf-8")
        print(f"  👥 Authors updated for {lang} ({len(graph)} authors)")


# ── Main ──


DASH_TITLE = {"ru": "Сводка", "en": "Dashboard", "es": "Panel", "ar": "لوحة", "fr": "Tableau de bord", "zh": "面板"}


def generate_archive_page(lang):
    """Страница /archive — теперь ДАШБОРД-витрина проекта (юзер 2026-07-24: старый архив был
    тупиком — голый список + старое меню + без русского; делаем аналитический дашборд). Клиентский:
    оболочка + унифицированная шапка; всю статистику считает и рисует js/dashboard.js из индексов,
    которые грузит js/search.js. Живёт на рефреше — числа пересчитываются из свежих данных."""
    title = DASH_TITLE.get(lang, DASH_TITLE["en"])
    fav_links = ('<link rel="icon" href="/favicon.ico" sizes="any">'
                 '<link rel="icon" type="image/png" href="/favicon.png">'
                 '<link rel="apple-touch-icon" href="/favicon.png">')
    html = f'''<!DOCTYPE html><html lang="{lang}" dir="{dir_for(lang)}"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{title} — bridge42worlds</title>
{fav_links}
<link rel="stylesheet" href="/css/style.css?v={asset_ver()}">
<script data-goatcounter="https://{GOATCOUNTER}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script></head><body>
<div class="top-bar"><a href="/{LANG_DIR}/{lang}/index.html" class="logo">bridge42worlds</a>
<div class="header-right"><div class="nav-links">
<a href="/{LANG_DIR}/{lang}/index.html">main</a><a href="/{LANG_DIR}/{lang}/tags/">tags</a>
<a href="/{LANG_DIR}/{lang}/laws/">laws</a><a href="/{LANG_DIR}/{lang}/scientists/">scientists</a>
<a href="/{LANG_DIR}/{lang}/sections/">sections</a><a href="/{LANG_DIR}/en/authors/">authors</a>
<a href="/{LANG_DIR}/{lang}/graph/">graph</a><a href="/learn.html">learn</a>
<a class="nav-ic" href="/{LANG_DIR}/{lang}/favorites.html" title="{safe(nav_fav_title(lang))}"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" aria-hidden="true"><path d="M12 3.6l2.45 5 5.5.7-4 3.85 1 5.45-4.95-2.65-4.95 2.65 1-5.45-4-3.85 5.5-.7Z"/></svg></a>
</div></div></div>
<div class="langs" id="langs-bar"></div>
<div id="dashboard"></div>
<footer><p>bridge42worlds </p></footer>
<script src="/js/icons.js?v={asset_ver()}"></script>
<script src="/js/search.js?v={asset_ver()}"></script>
<script src="/js/dashboard.js?v={asset_ver()}"></script></body></html>'''
    _write_text_retry(Path(LANG_DIR) / lang / "archive" / "index.html", html)


ANALYTICS_TITLE = {"ru": "Карта проекта", "en": "Project map", "es": "Mapa del proyecto",
                   "ar": "خريطة المشروع", "fr": "Carte du projet", "zh": "项目地图"}


def generate_analytics_page(lang):
    """Страница /analytics — 3D-карта облака статей/авторов, которую можно покрутить (юзер 2026-07-24:
    показать группировки/кластеры, вау-эффект). Клиентская: оболочка + унифицированная шапка; всё
    считает офлайн analytics_build.py (БЕЗ DeepSeek) в data/analytics/*.json, рисует js/analytics.js."""
    title = ANALYTICS_TITLE.get(lang, ANALYTICS_TITLE["en"])
    fav_links = ('<link rel="icon" href="/favicon.ico" sizes="any">'
                 '<link rel="icon" type="image/png" href="/favicon.png">'
                 '<link rel="apple-touch-icon" href="/favicon.png">')
    html = f'''<!DOCTYPE html><html lang="{lang}" dir="{dir_for(lang)}"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{title} — bridge42worlds</title>
{fav_links}
<link rel="stylesheet" href="/css/style.css?v={asset_ver()}">
<script data-goatcounter="https://{GOATCOUNTER}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script></head><body>
<div class="top-bar"><a href="/{LANG_DIR}/{lang}/index.html" class="logo">bridge42worlds</a>
<div class="header-right"><div class="nav-links">
<a href="/{LANG_DIR}/{lang}/index.html">main</a><a href="/{LANG_DIR}/{lang}/tags/">tags</a>
<a href="/{LANG_DIR}/{lang}/laws/">laws</a><a href="/{LANG_DIR}/{lang}/scientists/">scientists</a>
<a href="/{LANG_DIR}/{lang}/sections/">sections</a><a href="/{LANG_DIR}/en/authors/">authors</a>
<a href="/{LANG_DIR}/{lang}/graph/">graph</a><a href="/learn.html">learn</a>
<a class="nav-ic" href="/{LANG_DIR}/{lang}/favorites.html" title="{safe(nav_fav_title(lang))}"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" aria-hidden="true"><path d="M12 3.6l2.45 5 5.5.7-4 3.85 1 5.45-4.95-2.65-4.95 2.65 1-5.45-4-3.85 5.5-.7Z"/></svg></a>
</div></div></div>
<div class="langs" id="langs-bar"></div>
<div id="analytics"></div>
<footer><p>bridge42worlds </p></footer>
<script src="/js/icons.js?v={asset_ver()}"></script>
<script src="/js/search.js?v={asset_ver()}"></script>
<script src="/js/analytics.js?v={asset_ver()}"></script></body></html>'''
    (Path(LANG_DIR) / lang / "analytics").mkdir(parents=True, exist_ok=True)
    _write_text_retry(Path(LANG_DIR) / lang / "analytics" / "index.html", html)


def compute_connectivity_gaps():
    """Считает сущности (тег/закон/учёный), которым не хватает связи с КАЖДЫМ из двух других типов
    (юзер-фидбек 2026-07-18: "проверка все теги имеют по крайней мере один закон и одного учёного
    и так далее для каждой сущности"). Источники истины — те же три файла, что питают
    build_knowledge_graph.py: data/tags-graph.json, data/laws-graph.json, scientists.json.
    Тег↔учёный и учёный↔тег проверяются В ОБЕ СТОРОНЫ (tag.scientists ИЛИ scientist.related_tags) —
    как и в build_knowledge_graph.py — иначе часть связей ложно считается отсутствующей
    (см. находку 2026-07-18: граф-файлы двух направлений могут расходиться).
    Возвращает dict с 6 отсортированными списками id — переиспользуется дашбордом (status.html) и
    connectivity_repair.py (точечный автопочин через LLM).
    """
    tg = json.loads(Path("data/tags-graph.json").read_text(encoding="utf-8")).get("graph", {}) \
        if Path("data/tags-graph.json").exists() else {}
    lg = json.loads(Path("data/laws-graph.json").read_text(encoding="utf-8")).get("graph", {}) \
        if Path("data/laws-graph.json").exists() else {}
    sci_all = json.loads(Path(f"lang/{DEFAULT_LANG}/data/scientists.json").read_text(encoding="utf-8")) \
        if Path(f"lang/{DEFAULT_LANG}/data/scientists.json").exists() else {}

    tags_with_law = set()
    for n in lg.values():
        tags_with_law.update(n.get("tags", []))
    tags_sci_direct = {t for t, n in tg.items() if n.get("scientists")}
    tags_sci_reverse = set()
    for s in sci_all.values():
        tags_sci_reverse.update(s.get("related_tags", []))
    tags_no_law = sorted(t for t in tg if t not in tags_with_law)
    tags_no_sci = sorted(t for t in tg if t not in tags_sci_direct and t not in tags_sci_reverse)

    laws_no_tag = sorted(lid for lid, n in lg.items() if not n.get("tags"))
    laws_no_sci = sorted(lid for lid, n in lg.items() if not n.get("scientists") and not n.get("influenced_by"))

    sci_tags_direct = {s for s, v in sci_all.items() if v.get("related_tags")}
    sci_tags_reverse = set()
    for n in tg.values():
        sci_tags_reverse.update(n.get("scientists", []))
    sci_no_tag = sorted(s for s in sci_all if s not in sci_tags_direct and s not in sci_tags_reverse)
    sci_with_law = set()
    for n in lg.values():
        sci_with_law.update(n.get("scientists", []))
        sci_with_law.update(n.get("influenced_by", []))
    sci_no_law = sorted(s for s in sci_all if s not in sci_with_law)

    return {
        "tags_no_law": tags_no_law, "tags_no_sci": tags_no_sci,
        "laws_no_tag": laws_no_tag, "laws_no_sci": laws_no_sci,
        "sci_no_tag": sci_no_tag, "sci_no_law": sci_no_law,
        "n_tags": len(tg), "n_laws": len(lg), "n_sci": len(sci_all),
    }


def build_connectivity_report_html():
    g = compute_connectivity_gaps()

    def row(label, missing, total_n):
        if not missing:
            return f'<p style="color:#2e7d32">✓ {label}: все {total_n} связаны</p>'
        shown = ", ".join(missing[:15]) + (f' … +{len(missing) - 15} ещё' if len(missing) > 15 else '')
        return f'<p style="color:#b31b1b">⚠️ {label}: {len(missing)}/{total_n} без связи — {shown}</p>'

    return (
        row("Теги без закона", g["tags_no_law"], g["n_tags"])
        + row("Теги без учёного", g["tags_no_sci"], g["n_tags"])
        + row("Законы без тега", g["laws_no_tag"], g["n_laws"])
        + row("Законы без учёного", g["laws_no_sci"], g["n_laws"])
        + row("Учёные без тега", g["sci_no_tag"], g["n_sci"])
        + row("Учёные без закона", g["sci_no_law"], g["n_sci"])
    )


def generate_status_page():
    """status.html — дашборд состояния системы (статьи по языкам/дням/разделам, экспресс vs
    полные, источник обложек + оценка расхода на них, очередь bulk-generate, счётчики)."""
    total = 0
    langs_have = {l: 0 for l in LANGUAGES}
    by_day = {}
    by_cat = {}
    express_n = full_n = 0
    img_pdf_n = img_ai_n = img_pending_n = img_none_n = 0
    ai_model_counts = {}
    known_ids = set()
    incomplete = 0
    for data, folder in iter_articles():
        total += 1
        known_ids.add(data.get("id", ""))
        by_day[data.get("date", "?")] = by_day.get(data.get("date", "?"), 0) + 1
        cat = data.get("primary_category") or (data.get("categories") or ["?"])[0]
        by_cat[cat] = by_cat.get(cat, 0) + 1
        if data.get("express"):
            express_n += 1
        else:
            full_n += 1
        model = data.get("image_model")
        if model:
            img_ai_n += 1
            ai_model_counts[model] = ai_model_counts.get(model, 0) + 1
        elif (folder / "ai.jpg").exists():
            img_pdf_n += 1
        elif data.get("image_pending"):
            img_pending_n += 1
        else:
            img_none_n += 1
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
    laws_n = len(json.loads(Path(f"lang/{DEFAULT_LANG}/data/laws.json").read_text(encoding="utf-8"))) \
        if Path(f"lang/{DEFAULT_LANG}/data/laws.json").exists() else 0
    sci_n = len(valid_scientist_ids())
    authors_n = len(json.loads(Path("data/authors-graph.json").read_text(encoding="utf-8"))) \
        if Path("data/authors-graph.json").exists() else 0

    # Примерная цена картинок по модели (см. config.json agents.image*) — не точный биллинг,
    # просто прикидка по счётчику картинок × известная цена за штуку у DeepInfra.
    IMG_COST = {"black-forest-labs/FLUX-1-schnell": 0.002, "black-forest-labs/FLUX-2-pro": 0.015}
    img_cost_est = sum(IMG_COST.get(m, 0.01) * n for m, n in ai_model_counts.items())

    # Очередь bulk-generate — самый свежий data/bulk-select/*.json (кроме служебных arab-authors-*),
    # "готово" = сколько его id уже реально сгенерены (есть в корпусе).
    queue_html = ""
    bulk_files = sorted(Path("data/bulk-select").glob("*.json")) if Path("data/bulk-select").exists() else []
    bulk_files = [p for p in bulk_files if "arab-authors" not in p.name]
    if bulk_files:
        qdata = json.loads(bulk_files[-1].read_text(encoding="utf-8"))
        ready = qdata.get("ready", [])
        qdone = sum(1 for a in ready if a.get("id") in known_ids)
        qtotal = len(ready)
        qpct = round(100 * qdone / qtotal) if qtotal else 0
        queue_html = (f'<h2>Очередь bulk-generate ({bulk_files[-1].name})</h2>'
                      f'<div class="cards"><div class="card"><b>{qdone}/{qtotal}</b><span>готово · {qpct}%</span></div></div>'
                      f'<div style="background:#eee;border-radius:6px;overflow:hidden;height:18px;margin:6px 0 14px">'
                      f'<div style="width:{qpct}%;height:100%;background:#4a7c9b"></div></div>')

    def bar(v, mx, color):
        w = int(100 * v / mx) if mx else 0
        return f'<div style="background:#eee;border-radius:4px;overflow:hidden;height:14px"><div style="width:{w}%;height:100%;background:{color}"></div></div>'

    def donut(parts):
        """parts: [(label, value, color), ...] — CSS conic-gradient кольцо, без JS/библиотек."""
        tot = sum(v for _, v, _ in parts) or 1
        segs, acc = [], 0
        for _, v, c in parts:
            start, acc = acc, acc + v
            segs.append(f'{c} {start / tot * 360:.1f}deg {acc / tot * 360:.1f}deg')
        ring = f'<div style="width:84px;height:84px;border-radius:50%;background:conic-gradient({", ".join(segs)});flex-shrink:0"></div>'
        legend = "".join(
            f'<div style="display:flex;align-items:center;gap:6px;font-size:12px;margin:3px 0">'
            f'<span style="width:10px;height:10px;border-radius:3px;background:{c};display:inline-block"></span>'
            f'{label}: <b>{v}</b> ({round(100 * v / tot) if tot else 0}%)</div>'
            for label, v, c in parts)
        return f'<div style="display:flex;gap:16px;align-items:center;margin:10px 0">{ring}<div>{legend}</div></div>'

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
    top_cats = sorted(by_cat.items(), key=lambda kv: -kv[1])[:15]
    max_cat = top_cats[0][1] if top_cats else 1
    cat_rows = "".join(
        f'<tr><td style="padding:3px 10px;color:#888">{ARXIV_CATEGORIES.get(c, c)}</td>'
        f'<td style="padding:3px 10px;width:220px">{bar(n, max_cat, "#8e44ad")}</td>'
        f'<td style="padding:3px 10px">{n}</td></tr>' for c, n in top_cats)
    warn = f'<p style="color:#b31b1b">⚠️ Недопечённых папок: {incomplete}</p>' if incomplete else '<p style="color:#2e7d32">✓ Недопечённых нет</p>'
    tier_donut = donut([("экспресс", express_n, "#e67e22"), ("полные", full_n, "#2e7d32")])
    img_donut = donut([("из PDF", img_pdf_n, "#2e7d32"), ("AI", img_ai_n, "#4a7c9b"),
                        ("ждёт бюджета", img_pending_n, "#e67e22"), ("нет вообще", img_none_n, "#b31b1b")])
    connectivity_html = build_connectivity_report_html()
    html = f'''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Status — bridge42worlds</title>
<style>body{{font-family:system-ui,Arial,sans-serif;max-width:760px;margin:0 auto;padding:30px 18px;color:#2c2c2c}}
h1{{font-size:22px}}h2{{font-size:15px;margin:24px 0 8px;color:#555}}
.cards{{display:flex;gap:12px;flex-wrap:wrap;margin:14px 0}}
.card{{flex:1;min-width:120px;background:#f6f6f6;border-radius:10px;padding:12px 14px}}
.card b{{font-size:24px;display:block}}.card span{{color:#888;font-size:13px}}
table{{border-collapse:collapse;font-size:13px;width:100%}}</style></head><body>
<h1><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><line x1="6.5" y1="19" x2="6.5" y2="13"/><line x1="12" y1="19" x2="12" y2="8.5"/><line x1="17.5" y1="19" x2="17.5" y2="11"/><line x1="4" y1="19.5" x2="20" y2="19.5"/></svg> Состояние системы</h1>
<div class="cards">
<div class="card"><b>{total}</b><span>статей</span></div>
<div class="card"><b>{authors_n}</b><span>авторов</span></div>
<div class="card"><b>{sci_n}</b><span>учёных</span></div>
<div class="card"><b>{tags_n}</b><span>тегов</span></div>
<div class="card"><b>{laws_n}</b><span>законов</span></div>
<div class="card"><b>{len(LANGUAGES)}</b><span>языков</span></div>
</div>
{queue_html}
<h2>Экспресс vs полные</h2>{tier_donut}
<h2>Источник обложек (оценка расхода на AI: ${img_cost_est:.2f})</h2>{img_donut}
<h2>Покрытие переводами</h2><table>{cov_rows}</table>
<h2>По разделам arXiv (топ-15)</h2><table>{cat_rows}</table>
<h2>Статьи по дням (последние 30)</h2><table>{day_rows}</table>
<h2>Целостность</h2>{warn}
<h2>Связность сущностей (тег↔закон↔учёный)</h2>{connectivity_html}
</body></html>'''
    _write_text_retry(Path("status.html"), html)
    print(f"  📊 status.html ({total} статей, {authors_n} авторов)")


def generate_llms_txt():
    """llms.txt — путеводитель по сайту для языковых моделей.

    То же, чем robots.txt служит поисковику, только адресат другой: модель, которая пришла
    отвечать на вопрос человека, читает короткий markdown и понимает, что здесь лежит и как
    устроено, вместо того чтобы догадываться по случайной странице. Cloudflare держит
    /llms.txt и /llms-full.txt в списке путей, открытых даже заблокированным краулерам, —
    то есть считает файл частью нормального устройства сайта.

    Владелец 8 августа 2026 снял блокировку со всех ИИ-краулеров: мы отдаём материал по
    свободной лицензии, и читатель, пришедший по ссылке из ответа ИИ, — такой же читатель.
    """
    idx = Path(LANG_DIR) / DEFAULT_LANG / "articles-index.json"
    n_art = len(json.loads(idx.read_text(encoding="utf-8"))) if idx.exists() else 0
    n_auth = len(list((Path(LANG_DIR) / "en" / "authors").glob("*.html"))) if \
        (Path(LANG_DIR) / "en" / "authors").exists() else 0
    langs = ", ".join(LANGUAGES)

    body = f"""# bridge42worlds

> Peer-reviewed physics, biology and related research from arXiv, retold in plain language.
> {n_art} papers, each at four depths — from a one-paragraph gist to a full technical
> account — in {len(LANGUAGES)} languages ({langs}). Free to read, no registration, no ads.

Every article keeps a link to the arXiv original and its licence. The retelling is ours;
the science belongs to the authors named on each page. If you quote from here, cite the
original paper — and a link back to our page helps its authors find the retelling.

## How the site is laid out

- Article addresses look like `/{LANG_DIR}/<lang>/archive/<date>/<arxiv-id>/index.html`
- `index.html` is the canonical page; `mini.html`, `simple.html` and `advanced.html` are
  the same paper at other depths and point their canonical here
- [Archive of all papers]({SITE_URL}/{LANG_DIR}/en/archive/index.html)
- [Authors]({SITE_URL}/{LANG_DIR}/en/authors/index.html) — {n_auth} pages, one per researcher
- [Topics]({SITE_URL}/{LANG_DIR}/en/tags/index.html)
- [Laws of nature]({SITE_URL}/{LANG_DIR}/en/laws/index.html) — formulas with their history
- [arXiv sections]({SITE_URL}/{LANG_DIR}/en/sections/index.html)
- [About the project]({SITE_URL}/{LANG_DIR}/en/about.html) — what this is, who it is for
- [Sitemap]({SITE_URL}/sitemap.xml)

## For researchers

Authors may submit their own work for a plain-language retelling, and may correct or
withdraw ours at any time. The last word on any page is theirs.
[How to submit]({SITE_URL}/{LANG_DIR}/en/community/index.html)

## Contact

Own work for review: article@bridge42worlds.academy
Anything else, including "you got this wrong": see the About page above.
"""
    _write_text_retry(Path("llms.txt"), body)
    print(f"  🤖 llms.txt: {n_art} статей, {n_auth} авторов, {len(LANGUAGES)} языков")


def _authors_multi(min_articles: int = 2) -> list:
    """Авторы, у которых в базе больше одной работы, — по графу авторов.

    Граф считается при генерации и лежит в data/authors-graph.json; берём его, а не
    articles-index.json, чтобы имя и число работ совпадали ровно с тем, что на странице.
    """
    p = Path("data/authors-graph.json")
    if not p.exists():
        return []
    try:
        g = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    g = g.get("graph", g)
    out = []
    for name, d in g.items():
        arts = (d or {}).get("articles", [])
        # Страницу пишем только если файл действительно есть: звать поисковика на
        # несуществующий адрес мы уже один раз наступали (mini.html у экспресс-статей).
        if len(arts) >= min_articles and (Path(LANG_DIR) / "en" / "authors" / f"{author_slug(name)}.html").exists():
            out.append(name)
    return out


def generate_sitemaps():
    """sitemap-{lang}.xml (статьи+теги+учёные+авторы+about+index) + индекс sitemap.xml в корне."""
    def urlset(urls):
        # urls — список (адрес, lastmod|None). Честный lastmod из данных статьи: Google
        # переобходит только то, что реально менялось, и бюджет обхода уходит на свежие
        # статьи, а не на переобход старья (владелец 2026-08-04: свежая статья — это автор,
        # который ищет сам себя). Врать датой нельзя: поисковики ловят «всё обновилось
        # сегодня» и перестают верить карте вовсе.
        def one(u):
            if isinstance(u, tuple) and u[1]:
                return f"<url><loc>{u[0]}</loc><lastmod>{u[1]}</lastmod></url>"
            return f"<url><loc>{u[0] if isinstance(u, tuple) else u}</loc></url>"
        body = "".join(one(u) for u in urls)
        return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>'

    tags_graph = json.loads(Path("data/tags-graph.json").read_text(encoding="utf-8")).get("graph", {}) \
        if Path("data/tags-graph.json").exists() else {}
    made = []
    for lang in LANGUAGES:
        urls = [f"{SITE_URL}/{LANG_DIR}/{lang}/index.html",
                f"{SITE_URL}/{LANG_DIR}/{lang}/about.html",
                f"{SITE_URL}/{LANG_DIR}/{lang}/archive/index.html",
                f"{SITE_URL}/{LANG_DIR}/{lang}/tags/index.html",
                f"{SITE_URL}/{LANG_DIR}/en/authors/index.html",
                f"{SITE_URL}/{LANG_DIR}/{lang}/scientists/index.html"]
        authors_dir = Path(LANG_DIR) / "en" / "authors"
        if lang == "en" and authors_dir.exists():
            for p in sorted(authors_dir.glob("[a-z].html")):
                urls.append(f"{SITE_URL}/{LANG_DIR}/en/authors/{p.name}")
            # Персональные страницы авторов — тех, у кого больше одной работы. Учёный,
            # который ищет собственное имя, попадает к своим статьям в нашем пересказе; это
            # прямее любой рассылки и не требует ничьих контактов. Всех 18 506 сразу в карту
            # не даём: мы только что срезали её с 46 662 адресов до 13 566 именно потому,
            # что поисковик захлебнулся. Порог «две работы и больше» оставляет 1 479 — тех,
            # кого мы разбирали не по случайности. Остальных добавим, когда эти осядут.
            for name in sorted(_authors_multi()):
                urls.append(f"{SITE_URL}/{LANG_DIR}/en/authors/{author_slug(name)}.html")
        sections_dir = Path(LANG_DIR) / lang / "sections"
        if sections_dir.exists():
            for p in sorted(sections_dir.glob("*.html")):
                urls.append(f"{SITE_URL}/{LANG_DIR}/{lang}/sections/{p.name}")
        idx = Path(LANG_DIR) / lang / "articles-index.json"
        ids_seen = set()
        if idx.exists():
            for a in json.loads(idx.read_text(encoding="utf-8")):
                if a["id"] in ids_seen: continue
                ids_seen.add(a["id"])
                # Только существующие файлы: у экспресс-статьи без короткого текста mini.html
                # не пишется, а карта сайта звала поисковик на несуществующий адрес.
                art_dir = Path(LANG_DIR) / lang / "archive" / a["date"] / a["id"]
                # lastmod — дата правки данных статьи, не HTML: пересборка не считается
                # изменением содержания.
                lm = None
                dj = art_dir / "data.json"
                try:
                    if dj.exists():
                        import datetime as _dt
                        lm = _dt.date.fromtimestamp(dj.stat().st_mtime).isoformat()
                except Exception:
                    lm = None
                # В карте — только канонический адрес статьи (index.html). Три остальных
                # уровня остаются доступны читателю и открыты для обхода, но в карту не
                # попадают: их canonical всё равно ведёт сюда, а звать поисковика на
                # страницы, которые он по нашей же просьбе индексировать не должен, —
                # значит тратить его бюджет обхода впустую. Отчёт за 8 августа: из 46 662
                # предъявленных адресов проиндексировано 3 535, а 39 500 он не стал даже
                # читать. После правки предъявляем около 11 тысяч.
                if (art_dir / "index.html").exists():
                    urls.append((f"{SITE_URL}/{LANG_DIR}/{lang}/archive/{a['date']}/{a['id']}/index.html", lm))
        for tid in tags_graph:
            urls.append(f"{SITE_URL}/{LANG_DIR}/{lang}/tags/{tid}.html")
        fn = f"sitemap-{lang}.xml"
        _write_text_retry(Path(fn), urlset(urls))
        made.append(fn)
    index = ('<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
             + "".join(f"<sitemap><loc>{SITE_URL}/{f}</loc></sitemap>" for f in made) + "</sitemapindex>")
    _write_text_retry(Path("sitemap.xml"), index)
    print(f"  🗺️ Sitemaps: {', '.join(made)} + sitemap.xml")


def _xml_esc(s):
    return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def generate_feeds(limit=50):
    """Atom-лента (feed-{lang}.xml) из последних N popular-статей — для читалок/учёных,
    не только людей с браузером (RSS/Atom — гигиена для научной аудитории)."""
    made = []
    for lang in LANGUAGES:
        idx = Path(LANG_DIR) / lang / "articles-index.json"
        if not idx.exists(): continue
        items = json.loads(idx.read_text(encoding="utf-8"))
        items = sorted(items, key=lambda a: (a.get("date", ""), a.get("id", "")), reverse=True)[:limit]
        if not items: continue
        updated = items[0].get("date", "") + "T00:00:00Z"
        entries = ""
        for a in items:
            url = f"{SITE_URL}{a['url']}" if a["url"].startswith("/") else f"{SITE_URL}/{a['url']}"
            entries += (
                f'<entry><title>{_xml_esc(a.get("title",""))}</title>'
                f'<link href="{_xml_esc(url)}"/><id>{_xml_esc(url)}</id>'
                f'<updated>{a.get("date","")}T00:00:00Z</updated>'
                f'<summary>{_xml_esc(a.get("description", a.get("oneliner", "")))}</summary></entry>'
            )
        feed = (
            '<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom">'
            f'<title>{SITE_NAME}</title><link href="{SITE_URL}/{LANG_DIR}/{lang}/index.html"/>'
            f'<link rel="self" href="{SITE_URL}/feed-{lang}.xml"/>'
            f'<id>{SITE_URL}/{LANG_DIR}/{lang}/</id><updated>{updated}</updated>{entries}</feed>'
        )
        fn = f"feed-{lang}.xml"
        _write_text_retry(Path(fn), feed)
        made.append(fn)
    if made:
        print(f"  📡 Feeds: {', '.join(made)}")


def write_arxiv_categories_json():
    """Экспортирует ARXIV_CATEGORIES (gen_base.py) в data/arxiv-categories.json — search.js
    подтягивает его вместо своей отдельной хардкоженной копии ARXIV_CAT_NAMES, которая
    неизбежно расходилась с Python-словарём при каждом добавлении новой категории.
    Заодно — ARXIV_CATEGORY_DESCRIPTIONS в data/arxiv-category-descriptions.json (тултипы)."""
    Path("data").mkdir(exist_ok=True)
    Path("data/arxiv-categories.json").write_text(
        json.dumps(ARXIV_CATEGORIES, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("data/arxiv-category-descriptions.json").write_text(
        json.dumps(ARXIV_CATEGORY_DESCRIPTIONS, ensure_ascii=False, indent=2), encoding="utf-8")


_WRITE_FAILURES = []


def _write_text_retry(path, text, retries=5, encoding="utf-8"):
    # encoding принимается только ради совместимости с вызовами вида write_text(..., encoding="utf-8"),
    # переведёнными на этот хелпер: пишем всегда в utf-8.
    """write_text() с ретраем — Windows иногда отдаёт OSError [Errno 22] на ровном месте при
    записи (антивирус/индексатор держит файл долю секунды) — раньше это ронуло ВЕСЬ
    regenerate_all_html() на одной статье из 1000+, приходилось перезапускать с нуля.
    Оба случая, что видели (2508.01648 в ar_backfill, 2601.16015 здесь) — не воспроизвелись
    повторно, чисто транзиентно."""
    import time
    delay = 0.3
    for attempt in range(retries):
        try:
            path.write_text(text, encoding="utf-8")
            return True
        except OSError as e:
            if attempt == retries - 1:
                # Ронять час работы из-за одной сорванной записи нельзя: запоминаем и идём дальше.
                # Список печатается в конце прогона — эти страницы дописываются точечным регеном.
                _WRITE_FAILURES.append((str(path), f"{type(e).__name__}: {e}"))
                return False
            time.sleep(delay)
            delay *= 2



# ── Пересобирать только изменившееся ─────────────────────────────────────────────
#
# Владелец 14 августа: «мы всё пересобираем или только новые? … надо двигаться к этому,
# потому что скоро статей станет 10 000 и все приехали».
#
# До этого `run.py html` перестраивал ВСЕ страницы всех статей на пяти языках — часы
# работы ежедневно ради того, что почти всегда не менялось. Генератор просто не умел
# отличить «данные статьи те же» от «шаблон под ней изменился» и перестраховывался.
#
# Отличаем двумя отпечатками.
#   ПОДПИСЬ СБОРКИ — хэш шаблонов и самого генератора. Изменилась вёрстка или код —
#   пересобираем всё, иначе половина сайта останется на старом шаблоне.
#   ОТПЕЧАТОК СТАТЬИ — хэш её data.json. Совпал и страница на месте — пропускаем.
#
# Стоит это одно чтение файла на статью против полной генерации пяти языков × четырёх
# уровней. Агрегаты (теги, законы, ленты, карты сайта) строятся всегда: они ссылаются
# на все статьи разом, и частичная сборка оставила бы их рассогласованными.
_BUILD_SIG = None
FINGERPRINTS = Path("data") / "build-fingerprints.json"


def build_signature():
    """Хэш всего, что влияет на КАЖДУЮ страницу: шаблоны, генератор, css/js."""
    global _BUILD_SIG
    if _BUILD_SIG is None:
        h = hashlib.sha256()
        for f in sorted(Path("templates").glob("*.html")):
            h.update(f.read_bytes())
        gen = Path("generate.py")
        if gen.exists():
            h.update(gen.read_bytes())
        h.update(asset_ver().encode())
        _BUILD_SIG = h.hexdigest()[:16]
    return _BUILD_SIG


def _load_fingerprints():
    """Отпечатки прошлой сборки. Подпись не та — считаем, что отпечатков нет."""
    try:
        d = json.loads(FINGERPRINTS.read_text(encoding="utf-8"))
        if d.get("подпись") != build_signature():
            print("   шаблоны или генератор изменились — пересобираю всё")
            return {}
        return d.get("статьи") or {}
    except Exception:
        return {}


def _save_fingerprints(fps):
    try:
        FINGERPRINTS.parent.mkdir(exist_ok=True)
        FINGERPRINTS.write_text(json.dumps(
            {"подпись": build_signature(), "когда": datetime.now().isoformat(timespec="minutes"),
             "статьи": fps}, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"   ⚠️ отпечатки не сохранены: {type(e).__name__}")


def _article_fingerprint(folder):
    try:
        return hashlib.sha256((folder / "data.json").read_bytes()).hexdigest()[:16]
    except Exception:
        return ""


def regenerate_all_html(only=None, force=False):
    """Пересобирает HTML статей из data.json (без API). Идёт по источнику правды,
    а не по индексам — устойчиво к их повреждению.

    only — список дат (2026-07-01) и/или id статей (2607.00742). Если задан, страницы статей
    пересобираются только для них, а агрегаты (теги, законы, учёные, архив, ленты, карты сайта,
    индексы) всё равно строятся целиком: они ссылаются на статьи, и частичная сборка оставила бы
    их рассогласованными. Полный проход тратит час на 31 тысячу страниц, точечный — минуты."""
    only = set(only or ())
    print("🔄 Regenerate HTML only (no API)"
          + (f" · выборочно: {', '.join(sorted(only))}" if only else ""))
    _WRITE_FAILURES.clear()
    write_arxiv_categories_json()
    for lang in LANGUAGES: ensure_lang_structure(lang)
    count = 0
    fps = {} if (force or only) else _load_fingerprints()
    fresh, skipped = dict(fps), 0
    for data, folder in iter_articles():
        date_str = data.get("date", folder.parent.name)
        if only and not ({date_str, data.get("id"), folder.parent.name} & only):
            continue
        aid = data.get("id") or folder.name
        fp = _article_fingerprint(folder)
        if fp and fps.get(aid) == fp and not force:
            # Данные те же и подпись сборки та же. Страница на месте? Проверяем ОДИН файл:
            # если исчез он, исчезла и вся папка, а если пропал отдельный уровень — его
            # вернёт ближайшая полная пересборка (run.py html --force).
            probe = Path(LANG_DIR) / DEFAULT_LANG / "archive" / date_str / aid / "index.html"
            if probe.exists():
                skipped += 1
                continue
        fresh[aid] = fp
        # только контентные картинки 0.jpg..N-1.jpg (ai.jpg — обложка, не в мозаике)
        images = sorted([p for p in folder.glob("*.jpg") if p.stem.isdigit()],
                        key=lambda p: int(p.stem))
        captions = data.get("captions") or {}
        article_obj = {
            "id": data["id"],
            "title": data.get("original_title", ""),
            "authors": data.get("authors", []),
            "license_url": data.get("license", ""),
            "license_name": data.get("license_name") or license_label(data.get("license", "")),
            "license_class": data.get("license_class", ""),
            "categories": data.get("categories", []),
            "primary_category": data.get("primary_category", ""),
            "refined": data.get("refined", False),
            "express": data.get("express", False),
            "express_tiers": data.get("express_tiers", []),
            # Авторская работа: те самые три отличия. Без переноса сюда data.json их знает,
            # а страница — нет, и работа собирается неотличимо от статьи с arXiv, включая
            # ложную ссылку «arXiv:b42p-2026-001» на несуществующий препринт.
            "author_work": data.get("author_work", False),
            "kind": data.get("kind", ""),
            "code": data.get("code", ""),
            "sources": data.get("sources", {}),
            "review": data.get("review", {}),
            "author_comment": data.get("author_comment", ""),
            # Рекомендации автору от машины знаний (tools/recommend.py). Без переноса сюда
            # раздел лежит в data.json, а на странице его нет — ровно как было с полями
            # авторской работы выше.
            "recommend": data.get("recommend", {}),
            # Оригинальная аннотация arXiv (tools/abstract_orig.py) — по той же причине.
            "abstract_orig": data.get("abstract_orig", ""),
        }
        abstract = data.get("abstract") or {}
        # Наличие мини считаем ДО страниц уровней: кнопка «Мини» на них должна появляться только
        # там, где mini.html ниже действительно запишется (условие то же — есть короткий текст).
        mini_ok = {}
        for lang in LANGUAGES:
            bs = version_scipop(data, "popular", lang) or version_scipop(data, "simple", lang) or {}
            if bs.get("express_locked"):
                bs = version_scipop(data, "simple", lang) or bs
            if lang != DEFAULT_LANG and payload_in_source_lang(bs):
                bs = untranslated_stub(bs, lang, {"en": version_scipop(data, "popular", "en") or {}})
                bs["threads"] = bs["text"]
            mini_ok[lang] = bool(bs.get("threads") or bs.get("mini"))
        for version in VERSIONS:
            for lang in LANGUAGES:
                scipop = version_scipop(data, version, lang)
                if not scipop: continue
                # version_scipop молча откатывается на DEFAULT_LANG — из-за этого арабские
                # страницы выходили с русским текстом. Нет перевода → честная заглушка.
                if lang != DEFAULT_LANG and payload_in_source_lang(scipop):
                    scipop = untranslated_stub(scipop, lang, {"en": version_scipop(data, version, "en") or {}})
                html = gen_article_html(scipop, article_obj, date_str,
                                        [str(p) for p in images], lang, version,
                                        captions_for_lang(captions, lang), abstract,
                                        has_mini=mini_ok.get(lang, True))
                out = Path(LANG_DIR) / lang / "archive" / date_str / data["id"] / VERSION_FILES[version]
                out.parent.mkdir(parents=True, exist_ok=True)
                _write_text_retry(out, html)
                count += 1
        # Mini-версия — threads-текст (полный, не обрезанный). threads берём ИМЕННО из popular
        # (заглушка express_locked уже несёт туда express-поле mini — см. express_locked_scipop),
        # а title/oneliner — из simple, если popular оказался экспресс-заглушкой (у simple нет
        # своего threads, только у popular/заглушки — брать threads из simple было бы пусто).
        # ПО ЯЗЫКУ: version_scipop(data, v, lang) сам делает откат на DEFAULT_LANG, если перевода
        # нет — раньше здесь везде стоял DEFAULT_LANG жёстко, и mini у en/es всегда был русским.
        for lang in LANGUAGES:
            base_scipop = version_scipop(data, "popular", lang) or version_scipop(data, "simple", lang) or {}
            if base_scipop.get("express_locked"):
                base_scipop = version_scipop(data, "simple", lang) or base_scipop
            if lang != DEFAULT_LANG and payload_in_source_lang(base_scipop):
                base_scipop = untranslated_stub(base_scipop, lang,
                                                {"en": version_scipop(data, "popular", "en") or {}})
                base_scipop["threads"] = base_scipop["text"]   # иначе mini просто не запишется
            # express: реальный тир хранит короткий текст в "mini", не "threads" (см. write_article_pages)
            threads_text = base_scipop.get("threads") or base_scipop.get("mini") or ""
            if not threads_text:
                continue
            mini_scipop = dict(base_scipop)
            mini_scipop["text"] = threads_text
            # mini.html больше НЕ ПИШЕТСЯ: мини убран из уровней чтения
            # (владелец 2026-08-09, причина — у order в gen_base.level_switch_links).
            # Старые файлы не удаляем: на них могли остаться ссылки снаружи.
            continue
            out = Path(LANG_DIR) / lang / "archive" / date_str / data["id"] / "mini.html"
            out.parent.mkdir(parents=True, exist_ok=True)
            html = gen_article_html(mini_scipop, article_obj, date_str,
                                    [str(p) for p in images], lang, "mini",
                                    captions_for_lang(captions, lang), abstract)
            _write_text_retry(out, html)
            count += 1
    build_knowledge_graph_data()
    for lang in LANGUAGES:
        update_all_tags(lang)
        update_all_scientists(lang)
        update_all_laws(lang)
        update_all_sections(lang)
        generate_knowledge_graph_page(lang)
        generate_archive_page(lang)
        generate_analytics_page(lang)
    # rebuild_author_graph() ПЕРЕД update_all_authors() — иначе authors-graph.json остаётся
    # застывшим на моменте последней явной пересборки, и авторы статей, добавленных с тех пор
    # (обычным bulk-генератором, не через add-one-article путь, который сам зовёт rebuild),
    # молча не получают страниц — битые ссылки вида /authors/Имя_Фамилия.html (юзер-фидбек
    # 2026-07-19: обнаружен на реальном примере, Tucker Manton — автор статьи, но не в графе).
    rebuild_author_graph()
    update_all_authors()
    generate_sitemaps()
    generate_llms_txt()
    generate_feeds()
    generate_status_page()
    # Отпечатки пишем ТОЛЬКО после того, как агрегаты собраны: если прогон оборвётся
    # посередине, следующий должен считать эти статьи несобранными, а не пропустить их.
    if not only:
        _save_fingerprints(fresh)
    print(f"  ✅ Regenerated {count} HTML pages + tags/scientists/authors/laws/graph"
          + (f" · пропущено без изменений: {skipped}" if skipped else ""))
    if _WRITE_FAILURES:
        print(f"  ⚠️ не записалось страниц: {len(_WRITE_FAILURES)} — допишите точечно "
              f"(run.py html --only <дата|id>):")
        for path, err in _WRITE_FAILURES[:12]:
            print(f"       {path} — {err}")


ARXIV_BASE_ID_RE = re.compile(r"v\d+$")


def load_generation_inputs():
    tags_input = json.loads(Path(f"lang/{DEFAULT_LANG}/data/tags-list.json").read_text(encoding="utf-8"))
    archive = Path(LANG_DIR) / DEFAULT_LANG / "archive"
    # Базовые id (без суффикса версии vN) уже обработанных статей — arXiv регулярно выпускает
    # v2/v3 той же работы; без этого набора такая новая версия считалась бы совсем другой
    # статьёй (папка с другим именем) и качалась/генерилась заново как дубль по сути.
    existing_base_ids = ({ARXIV_BASE_ID_RE.sub("", p.name) for p in archive.glob("*/*") if p.is_dir()}
                         if archive.exists() else set())
    express_tags_path = Path(CONFIG.get("express", {}).get("tags_file", "lang/ru/data/tags-list-express.json"))
    express_tags_input = (json.loads(express_tags_path.read_text(encoding="utf-8"))
                          if express_tags_path.exists() else tags_input)
    return {
        "tags_input": tags_input,
        "valid_tags": set(t["en"] for t in tags_input),
        "scientists_keys": list(
            json.loads(Path(f"lang/{DEFAULT_LANG}/data/scientists.json").read_text(encoding="utf-8")).keys()),
        "existing_base_ids": existing_base_ids,
        "express_tags_input": express_tags_input,
        "express_valid_tags": set(t["en"] for t in express_tags_input),
        "law_ids": list(json.loads(
            Path(f"lang/{DEFAULT_LANG}/data/laws.json").read_text(encoding="utf-8")).keys()),
    }


def build_article(a, date_str, inputs, force=False, express=False, **kw):
    """Фаза A целиком, но помеченная: все вызовы DeepSeek внутри попадают в журнал
    расхода с id статьи и её видом. Обёртка отдельная, потому что тело фазы длинное
    и с ранними выходами — оборачивать его целиком значило бы переписать двести строк
    ради одной метки. Метка живёт в своём потоке (common.job), а статьи готовятся
    параллельно."""
    with common.job(article=a.get("id"), kind="экспресс" if express else "полная"):
        return _build_article(a, date_str, inputs, force=force, express=express, **kw)


def _build_article(a, date_str, inputs, force=False, express=False, known_license=None, no_fetch=False,
                   only_langs=None, allow_restricted=False):
    """Фаза A: arXiv + PDF + все вызовы DeepSeek. Пишет только в папку статьи (гонок нет).
    Возвращает подготовленный dict либо None (пропущено/ошибка).
    express=True — дешёвый режим (см. TODO.md): один вызов generate_express() по авторской
    аннотации (не по полному тексту PDF) вместо каскада advanced→simple→popular, урезанный
    список тегов в промте (inputs['express_tags_input']). Simple шлифуется (refine_simple) —
    самый частый повод жалоб на сложность языка, теги в шлифовку не идут (см. gen_llm.refine_simple)
    и не нужны там. PDF всё равно качаем и парсим — картинки/обложка/миниатюры настоящие,
    экономим только на тексте генерации. Тиры не из config.express.tiers получают заглушку («полная
    готовится») вместо контента — апгрейд до полной версии: run.py regen <id>.

    only_langs — «полная на языке запроса» (воронка, ПРОЕКТ.md §4): переводим ТОЛЬКО эти языки
    (DEFAULT_LANG генерится всегда — это язык генерации). Остальные языки не платят за перевод:
    им остаётся прежний контент из старого data.json (см. реюз ниже), а без него — честная
    заглушка «перевод готовится» с кнопкой заказа.

    Реюз при force (правило воронки: «экспресс не пропадает при апгрейде»): перед генерацией
    читаем старый data.json и переносим из него всё оплаченное, что не устарело: переводы
    аннотации и подписей (их источник — авторский абстракт и PDF, они не меняются), FLUX-обложку
    (image_model), короткий текст экспресса — он становится mini полной статьи, а его переводы
    остаются на языках, где полной ещё нет."""
    article_folder = Path(LANG_DIR) / DEFAULT_LANG / "archive" / date_str / a["id"]
    if not force and (article_folder / "data.json").exists():
        print(f"  ⏭️ {a['id']} — уже есть, пропускаю (--force чтобы пересоздать)")
        return None
    base_id = ARXIV_BASE_ID_RE.sub("", a["id"])
    if not force and base_id in inputs.get("existing_base_ids", set()):
        print(f"  ⏭️ {a['id']} — новая версия уже обработанной статьи ({base_id}), пропускаю (--force чтобы пересоздать)")
        return None
    # Старый data.json — источник реюза. Только при совпадении id: под тем же именем папки
    # не может лежать другая статья, но битый/чужой json не должен подмешать чужой контент.
    prev = {}
    if force and (article_folder / "data.json").exists():
        try:
            prev = json.loads((article_folder / "data.json").read_text(encoding="utf-8"))
            if prev.get("id") != a["id"]:
                prev = {}
        except Exception:
            prev = {}
    prev_express_upgrade = bool(prev.get("express")) and not express
    try:
        # known_license — лицензия уже известна (из локального Kaggle-дампа arXiv, поле license):
        # НЕ ходим в arXiv за OAI-лицензией. Вызывающий обязан передавать только разрешённые CC-BY/CC0
        # (bio/med-прогон так и фильтрует локально). no_fetch — express-режим без обращения к arXiv
        # вообще: не тянем atom и PDF (текст берём из авторской аннотации a["summary"], обложка —
        # заглушка-мультиязычная карточка). Оба флага дефолт-выключены → обычный путь без изменений.
        if known_license is not None:
            oai_xml, lic_url = "", known_license
        else:
            oai_xml = get_license(a["id"])
            _, lic_url = is_allowed_license(oai_xml)
        # Решение по классу лицензии (владелец 2026-08-18, после пропуска 2606.12457
        # «расширяем забор»): free — полный конвейер; analysis (NC-семейство) — берём,
        # но публикуем ТОЛЬКО собственный текст: авторские рисунки и подписи не
        # используются, на странице признак «собственный разбор» с пояснением легальности
        # и кнопка снятия для автора; no — не берём. allow_restricted оставлен как
        # явный флаг run.py ids, но с расширением забора класс analysis проходит и без него.
        cls = license_class(lic_url)
        if cls == "no":
            print(f"  ⏭️ {a['id']} — license: {lic_url or 'none'}")
            # Журнал отказов. До 2026-08-18 отказ жил только в консоли, и вопрос владельца
            # «почему мы пропустили вот эту работу» был неотвечаем в принципе: id отвергнутой
            # работы не оставался нигде (расследование по 2606.12457). Дозапись jsonl — тот же
            # приём, что у data/gap-suggestions.jsonl: переживает прогоны, грепается за секунду.
            try:
                with open("data/rejected.jsonl", "a", encoding="utf-8") as rj:
                    rj.write(json.dumps({"id": a["id"], "day": date_str, "gate": "license",
                                         "license": lic_url or "",
                                         "ts": datetime.now().isoformat(timespec="minutes")},
                                        ensure_ascii=False) + "\n")
            except Exception:
                pass
            return None
        if cls == "analysis":
            a["license_class"] = "analysis"
            print(f"  ⚠️ {a['id']} — {license_label(lic_url)}: только собственный разбор, "
                  f"авторские рисунки и подписи не берём")
        a["license_url"], a["license_name"] = lic_url, license_label(lic_url)
        # atom.xml только сохраняется для истории, в контенте не участвует — при известной лицензии
        # не тратим на него отдельный запрос к arXiv (юзер 2026-07-24: брать из базы, меньше arXiv).
        atom_xml = "" if known_license is not None else _get_with_retry(
            f"http://es.arxiv.org/api/query?id_list={a['id']}", timeout=30).text
        if no_fetch:
            text, imgs, captions, refs = a.get("summary", ""), [], [], ""
            a["cited_arxiv"] = []
        else:
            # PDF качаем ВСЕГДА (кроме no_fetch) — обложки/картинки настоящие (юзер: «картинки из PDF»).
            # Но сперва смотрим под ноги: у уже сгенерённой статьи original.pdf лежит в её папке
            # (keep_pdf) — апгрейд экспресс→полная не должен перекачивать 2–20 МБ с arXiv,
            # которые уже есть на диске (владелец 2026-07-31: «если он его взял — пусть хранит»).
            # temp-кэш download_pdf этого не покрывал: temp чистится, папка статьи — нет.
            local_pdf = article_folder / "original.pdf"
            if local_pdf.exists() and local_pdf.stat().st_size > 10_000:
                pdf = local_pdf
            else:
                pdf = download_pdf(a["id"])
            text, imgs = parse_pdf(pdf)
            captions = extract_captions(text)  # подписи ищем в полном тексте (в списке литературы их нет)
            body, refs = split_references(text)
            a["cited_arxiv"] = extract_ref_arxiv_ids(refs)  # на будущее: связь с релевантными работами
            text = re.sub(r'https?://\S+', '', body)  # тело без литературы и URL → экономия ~20% токенов в промте
        print(f"  → {a['id']} …{' [no-fetch]' if no_fetch else ''}")
        article_folder.mkdir(parents=True, exist_ok=True)
        # errors="replace" обязателен: в тексте PDF попадаются НЕПАРНЫЕ суррогаты —
        # обломки математических символов Unicode, которые извлекатель отдаёт как есть.
        # utf-8 такое кодировать отказывается, и падала ВСЯ статья на записи списка
        # литературы (2607.27683v1, прогон 2026-07-31). Литература — вспомогательный
        # файл, ронять из-за неё статью нельзя.
        if refs:
            (article_folder / "references.txt").write_text(refs, encoding="utf-8", errors="replace")
        # РАЗОБРАННЫЙ ТЕКСТ СОХРАНЯЕМ. Раньше он уходил в промпт и терялся навсегда: рядом
        # оставались только PDF и список литературы. А это самое ценное, что есть у статьи
        # для вектора — не аннотация-витрина, которую автор пишет для привлечения, а тело
        # с методикой, оговорками и настоящими результатами (владелец 2026-08-09: «нам бы
        # вектор по всем статьям из PDF»). Весит копейки: 12 ГБ исходников дают около
        # 150 МБ текста.
        if text and not no_fetch:
            (article_folder / "fulltext.txt").write_text(text, encoding="utf-8", errors="replace")
        (article_folder / "arxiv-atom.xml").write_text(atom_xml, encoding="utf-8", errors="replace")
        (article_folder / "arxiv-oai.xml").write_text(oai_xml or "", encoding="utf-8", errors="replace")
        if not no_fetch and config.get("keep_pdf", True) and pdf != article_folder / "original.pdf":
            # мёртвый вес на масштабе — можно не хранить; при реюзе PDF файл уже на месте
            (article_folder / "original.pdf").write_bytes(pdf.read_bytes())
        # NC-ND: авторские рисунки и их подписи не берём. Сам рисунок мы бы ещё могли показать
        # неизменным, но подписи к нему у нас переводятся на пять языков — а это уже переработка
        # авторского текста, которую ND запрещает. Обложка у статьи своя (FLUX), страница по
        # существу ничего не теряет.
        if a.get("license_class") == "analysis":
            imgs, captions = [], []
        images = save_images(imgs, a["id"], article_folder) if imgs else []
        captions = captions[:len(images)]  # выравниваем по числу сохранённых картинок
        if not text: text = a["summary"]
        express_tiers = set(CONFIG.get("express", {}).get("tiers", ["mini", "simple"])) if express else None
        if express:
            # Один вызов по авторской аннотации — не полный текст, не advanced→simple→popular каскад.
            express_result = generate_express(a, a["summary"], inputs["express_tags_input"], inputs["scientists_keys"])
            if not express_result: return None
            (article_folder / "api").mkdir(exist_ok=True)
            (article_folder / "api" / "express-ru.json").write_text(
                json.dumps(express_result, ensure_ascii=False, indent=2), encoding="utf-8")
            express_result = validate_tags(express_result, inputs["express_valid_tags"])
            # Шлифовка: refine_simple трогает ТОЛЬКО текст (термины/метафору/тон/длину) — теги и
            # mini защищены и до, и после вызова (см. gen_llm.refine_simple), так что урезанный
            # список тегов сюда передавать не нужно и не мешает. "Просто" — самый частый повод
            # жалоб на сложность языка, поэтому шлифуем даже в экспрессе (единственная доп. трата).
            express_result = refine_simple(express_result)
            (article_folder / "api" / "express-ru_r.json").write_text(
                json.dumps(express_result, ensure_ascii=False, indent=2), encoding="utf-8")
            scipop_simple = express_result if "simple" in express_tiers else express_locked_scipop(express_result, DEFAULT_LANG)
            scipop_pop = express_result if "popular" in express_tiers else express_locked_scipop(express_result, DEFAULT_LANG)
            scipop_adv = express_result if "advanced" in express_tiers else express_locked_scipop(express_result, DEFAULT_LANG)
        else:
            # Словарь тегов сужаем до доменов ЭТОЙ статьи: биологической статье физический
            # список нечего предложить, и она берёт ближайший физический тег (см. tag_domains).
            tags_cloud = tag_domains.cloud_for(a, inputs["tags_input"])
            print(f"    🏷️  {tag_domains.describe(a, inputs['tags_input'])}")
            # Окружение работы: соседи из архива, плотность, группа карты, куст мирового поля.
            # Решение владельца 18.08 — разбор должен видеть поле вокруг, а не одну статью.
            # Собирается ДО вызова модели и кладётся в промпт; пусто — разбор идёт как прежде.
            ctx_block, ctx_meta = gen_context.build_block(a, text)
            scipop_adv = generate_advanced(a, text, tags_cloud, inputs["scientists_keys"],
                                           inputs.get("law_ids"), context_block=ctx_block)
            if not scipop_adv: return None
            (article_folder / "api").mkdir(exist_ok=True)
            (article_folder / "api" / "advanced-ru.json").write_text(
                json.dumps(scipop_adv, ensure_ascii=False, indent=2), encoding="utf-8")
            # Паспорт окружения рядом с сырым ответом: по нему потом видно, писался разбор
            # с полем вокруг или вслепую. Без этого отличить одно от другого нельзя.
            (article_folder / "api" / "context-ru.json").write_text(
                json.dumps({"used": bool(ctx_block), **ctx_meta}, ensure_ascii=False, indent=2),
                encoding="utf-8")
            scipop_adv = _check_neighbourhood(scipop_adv, ctx_meta)
            scipop_adv = validate_tags(scipop_adv, inputs["valid_tags"])
            # Gap-suggestions: чего модели не хватило в справочниках (missing tags/laws/scientists +
            # instruments + open_problems) — копим в отдельный файл для ревью/пополнения, из публичного
            # scipop вырезаем (в data.json это не идёт). Юзер-фидбек 2026-07-21.
            _sug = scipop_adv.pop("suggested", None)
            if isinstance(_sug, dict) and any(_sug.values()):
                try:
                    rec = {"id": a.get("id", ""), "date": date_str,
                           "category": a.get("primary_category", ""), "suggested": _sug}
                    with open("data/gap-suggestions.jsonl", "a", encoding="utf-8") as _gf:
                        _gf.write(json.dumps(rec, ensure_ascii=False) + "\n")
                except Exception as _e:
                    print(f"    ⚠️ gap-suggestions write: {_e}")
            # ЦЕПОЧКА (ТЗ контент-менеджера 2026-07-27, §4): advanced → popular → simple+mini.
            # Раньше был веер (simple и popular независимо из advanced) — версии расходились по
            # фактам и акцентам. Теперь popular наследует advanced, а simple+mini делаются ОДНИМ
            # вызовом из popular; вся фактура переносится кодом (inherit_facts), не пересказом.
            # Конвейер 2.0 (владелец 2026-07-30): конструктор — оба тира+mini одним вызовом
            # из advanced, общие блоки копирует код. Флаг constructor в config.json;
            # выключен или вызов не удался — старый двухшаговый путь, как было.
            scipop_pop = scipop_simple = None
            if config.get("constructor"):
                scipop_pop, scipop_simple = generate_combo(scipop_adv)
                if scipop_pop is None:
                    print("    ⚠️ конструктор не собрал тиры — падаю на старый путь")
            if scipop_pop is None:
                scipop_pop = generate_popular(scipop_adv)
                scipop_simple, mini_ru = generate_simple_mini(scipop_pop)
                if mini_ru:
                    scipop_pop["mini"] = mini_ru
                    scipop_simple["mini"] = mini_ru
            # Апгрейд экспресс→полная: короткий текст экспресса УЖЕ показан читателю как текст
            # статьи — он и остаётся mini полной версии (правило воронки: «экспресс не пропадает»),
            # а не свежая выжимка, которая говорит то же самое другими словами.
            prev_mini_ru = (((prev.get("simple") or prev.get("popular") or {}).get(DEFAULT_LANG) or {}).get("mini")
                            if prev_express_upgrade else None)
            if prev_mini_ru:
                scipop_pop["mini"] = prev_mini_ru
                scipop_simple["mini"] = prev_mini_ru
            (article_folder / "api" / "simple-ru.json").write_text(
                json.dumps(scipop_simple, ensure_ascii=False, indent=2), encoding="utf-8")
            (article_folder / "api" / "popular-ru.json").write_text(
                json.dumps(scipop_pop, ensure_ascii=False, indent=2), encoding="utf-8")

        # Рефлексивная шлифовка — РУЧНОЙ инструмент (ТЗ 2026-07-27, §4): в штатный цикл не входит,
        # чеклисты перенесены в промпты генерации как самопроверка. Остаётся для флагманских статей.
        # Экспресс сюда не заходит — его Simple уже прошлифован раньше (безусловно, не под --refine,
        # см. блок generate_express выше), Popular/Advanced в дефолтной конфигурации не публикуются.
        if REFINE and not express:
            with ThreadPoolExecutor(max_workers=2) as ex:
                fs = ex.submit(refine_simple, scipop_simple)
                fp = ex.submit(refine_popular, scipop_pop)
                scipop_simple_r, scipop_pop_r = fs.result(), fp.result()
            (article_folder / "api" / "simple-ru_r.json").write_text(
                json.dumps(scipop_simple_r, ensure_ascii=False, indent=2), encoding="utf-8")
            (article_folder / "api" / "popular-ru_r.json").write_text(
                json.dumps(scipop_pop_r, ensure_ascii=False, indent=2), encoding="utf-8")
            scipop_simple, scipop_pop = scipop_simple_r, scipop_pop_r

        # Обложка статьи — крупнейшая картинка из самого PDF, не AI-генерация (см. pick_cover_image).
        # Экспресс всё равно качает и парсит PDF (см. выше) специально ради этого — обложка
        # настоящая, экономим только на тексте генерации.
        # Исключение: у статьи уже есть ОПЛАЧЕННАЯ FLUX-обложка (covers_full.py пишет image_model
        # в data.json) — кадром из PDF её не затираем, поле проносим в новый data.json, иначе
        # regen молча превращал pro-обложку в кадр из PDF (техдолг воронки, 2026-07-31).
        if prev.get("image_model") and (article_folder / "ai.jpg").exists():
            a["image_model"] = prev["image_model"]
        else:
            cover = pick_cover_image(images)
            if cover:
                shutil.copy(cover, article_folder / "ai.jpg")
        # Лёгкие миниатюры для ленты (t_ai + до 2 PDF); число PDF-миниатюр → в индекс
        a["thumbs"] = make_thumbnails(article_folder)

        versions_ru = {"popular": scipop_pop, "simple": scipop_simple, "advanced": scipop_adv}
        # Целевые языки перевода. only_langs сужает список: «полная на языке запроса» переводит
        # один язык, остальные живут реюзом из prev (ниже) или заглушкой — и не оплачиваются.
        targets = [l for l in LANGUAGES if l != DEFAULT_LANG]
        if only_langs is not None:
            unknown = [l for l in only_langs if l not in LANGUAGES]
            if unknown:
                print(f"    ⚠️ only_langs: {unknown} нет в config.languages — игнорирую")
            targets = [l for l in targets if l in only_langs]
        # «Аннотация» из авторского arXiv-abstract — ТРИ регистра (popular/simple/advanced), + перевод
        # по языкам. Источник между прогонами не меняется (авторский абстракт той же версии статьи) —
        # реюзим и русскую, и переводы; переводим только языки, которых в prev не было.
        # Реюз аннотации — ТОЛЬКО если она сделана текущим промптом. Промпт «Аннотации»
        # переписан 2026-07-31 (был сухой пересказ структуры статьи, он же попадает на
        # карточку в ленте и формировал первое впечатление); без версии реюз консервировал
        # бы старый текст навсегда — статья апгрейдится, а аннотация остаётся прежней.
        prev_abstract = (prev.get("abstract") or {}) if prev.get("abstract_v") == ABSTRACT_PROMPT_V else {}
        # Аннотацию не считаем, пока её никто не видит (show_abstract=false, решение
        # владельца 2026-07-31): платить ~4 тыс. токенов на статью за скрытый артефакт
        # незачем. Данные прошлых статей лежат нетронутыми; включим показ — включим и счёт.
        abstract_ru = (prev_abstract.get(DEFAULT_LANG)
                       or (generate_abstract(a.get("summary", "")) if config.get("show_abstract", False) else {}))
        if REFINE and abstract_ru and not express and not prev_abstract.get(DEFAULT_LANG):
            abstract_ru = refine_abstract(abstract_ru)
        abstract = {l: t for l, t in prev_abstract.items() if t}
        abstract[DEFAULT_LANG] = abstract_ru
        abs_missing = [l for l in targets if not abstract.get(l)]
        if abstract_ru and abs_missing:
            with ThreadPoolExecutor(max_workers=min(8, len(abs_missing))) as aex:
                afut = {aex.submit(translate_scipop, abstract_ru, l): l for l in abs_missing}
                for fut, l in afut.items():
                    try:
                        abstract[l] = fut.result() or abstract_ru
                    except Exception:
                        abstract[l] = abstract_ru
        # Подписи к рисункам вытащены regex'ом из английского PDF (extract_captions) — переводим
        # на все языки САЙТА, кроме английского (не FROM default_lang, а FROM "en" — источник
        # всегда английский, независимо от того, какой язык у нас DEFAULT_LANG).
        # Реюз: PDF тот же — если английские подписи совпали со старыми, старые переводы верны.
        captions_by_lang = {"en": captions}
        prev_caps = prev.get("captions") or {}
        if captions and prev_caps.get("en") == captions:
            for l, cl in prev_caps.items():
                if cl:
                    captions_by_lang.setdefault(l, cl)
        cap_targets = [l for l in LANGUAGES if l != "en" and l not in captions_by_lang
                       and (only_langs is None or l in only_langs or l == DEFAULT_LANG)]
        if captions and cap_targets:
            with ThreadPoolExecutor(max_workers=min(8, len(cap_targets))) as capex:
                capfut = {capex.submit(translate_captions, captions, l): l for l in cap_targets}
                for fut, l in capfut.items():
                    try:
                        captions_by_lang[l] = fut.result() or captions
                    except Exception:
                        captions_by_lang[l] = captions
        # Языки вне целей и без реюза получают английские подписи — как и раньше при отказе перевода.
        for l in LANGUAGES:
            if l != "en":
                captions_by_lang.setdefault(l, captions)

        # Переводы: каждую версию на каждый целевой язык — параллельно. В экспрессе переводим
        # ТОЛЬКО реально сгенерированные тиры — заблокированные получают заглушку на языке
        # читателя напрямую (статичный текст, LLM не нужен, экономия перевода тоже).
        translations = {v: {} for v in VERSIONS}
        real_tiers = [v for v in VERSIONS if not express or v in express_tiers]
        use_constructor_translate = bool(config.get("constructor")) and not express
        if targets and use_constructor_translate:
            # Конвейер 2.0: на язык — advanced целиком (pro), затем popular/simple слимом
            # (flash, общие поля из переведённого advanced). Служебные поля (metaphor,
            # glossary) не переводятся вовсе — читатель их не видит, см. _INTERNAL_FIELDS.
            # Провал slim — честный откат на полный translate_scipop этого тира.
            def _translate_lang(l):
                adv_l = translate_scipop(versions_ru["advanced"], l)
                out = {"advanced": adv_l}
                for v in ("popular", "simple"):
                    res = translate_scipop_slim(versions_ru[v], adv_l, l)
                    out[v] = res if res is not None else translate_scipop(versions_ru[v], l)
                return out
            with ThreadPoolExecutor(max_workers=min(4, len(targets))) as tex:
                futs = {tex.submit(_translate_lang, l): l for l in targets}
                for fut, l in futs.items():
                    try:
                        per_lang = fut.result()
                    except Exception as e:
                        print(f"    ⚠️ {a['id']} перевод {l} не удался ({e}) — оставляю оригинал")
                        per_lang = {v: versions_ru[v] for v in real_tiers}
                    for v in real_tiers:
                        translations[v][l] = per_lang.get(v, versions_ru[v])
        elif targets:
            with ThreadPoolExecutor(max_workers=min(8, len(targets) * max(1, len(real_tiers)))) as tex:
                futures = {}
                for l in targets:
                    for v in real_tiers:
                        futures[tex.submit(translate_scipop, versions_ru[v], l)] = (v, l)
                for fut, (v, l) in futures.items():
                    try:
                        res = fut.result()
                    except Exception as e:
                        # translate_scipop сама ретраит недо-JSON (см. gen_llm.py); сюда долетает
                        # только если и chat() исчерпала свои ретраи — сетевой сбой. Лог — в файл,
                        # не только print, иначе в большом батче никто не заметит (см. коммент
                        # там же про 60-93% сломанных ar-страниц, найденные только ручной читкой).
                        print(f"    ⚠️ {a['id']} перевод {v}/{l} не удался ({e}) — оставляю оригинал")
                        try:
                            with open("translation-failures.log", "a", encoding="utf-8") as lf:
                                lf.write(f"build_article\t{l}\t{a['id']}/{v}: {e}\n")
                        except Exception:
                            pass
                        res = versions_ru[v]
                    translations[v][l] = res
            if express:
                for l in targets:
                    # locked-тир берёт контент из УЖЕ ПЕРЕВЕДЁННОГО реального тира ЭТОГО языка
                    # (simple/mini в express_tiers), а не из русского express_result — иначе
                    # express_locked_scipop (просто копирует base) оставлял бы русский текст
                    # в слотах en/es/ar (баг 2026-07-17: locked-тиры на нерусских языках были RU).
                    base_l = (translations.get("simple", {}).get(l)
                              or translations.get("mini", {}).get(l) or express_result)
                    for v in VERSIONS:
                        if v not in express_tiers:
                            translations[v][l] = express_locked_scipop(base_l, l)

        # Реюз переводов из prev — два случая:
        # 1) язык в этот прогон не переводился (only_langs его исключил) — прежний контент языка
        #    остаётся как был: экспресс-текст читателю полезнее заглушки «перевод готовится».
        #    Русские молчаливые откаты и старые заглушки не переносим — их pick_scipop и так
        #    превратит в честную заглушку.
        # 2) апгрейд экспресс→полная: в свежих переводах mini заменяем на СТАРЫЙ перевод экспресса —
        #    тот же текст, что читатель уже видел (языковое продолжение правила про mini выше).
        if prev:
            for v in VERSIONS:
                prev_v = prev.get(v) or {}
                for l in LANGUAGES:
                    if l == DEFAULT_LANG:
                        continue
                    cur = translations[v].get(l)
                    if cur and not payload_in_source_lang(cur):
                        continue  # свежий перевод удался — реюз не нужен
                    # Сюда попадают и языки вне целей, и цели, у которых перевод упал в
                    # русский откат: старый хороший текст лучше и заглушки, и русского.
                    old = prev_v.get(l)
                    if (isinstance(old, dict) and old.get("title")
                            and not old.get("untranslated") and not payload_in_source_lang(old)):
                        translations[v][l] = old
        if prev_express_upgrade:
            for v in VERSIONS:
                prev_v = prev.get(v) or {}
                for l, tr in translations[v].items():
                    old = prev_v.get(l) or {}
                    if (isinstance(tr, dict) and old.get("mini")
                            and not old.get("untranslated") and not payload_in_source_lang(old)):
                        tr["mini"] = old["mini"]

        a["refined"] = REFINE and not express  # бейдж ✦/тумблер ⇄ — экспресс не шлифован
        a["express"] = express
        # Дата апгрейда — для воронки «экспресс → полная» на дашборде (сколько экспрессов
        # доросло до разбора и как быстро). При обычном пересоздании дата проносится из prev.
        if prev_express_upgrade:
            a["upgraded"] = datetime.now().strftime("%Y-%m-%d")
        elif prev.get("upgraded"):
            a["upgraded"] = prev["upgraded"]
        if express:
            a["express_tiers"] = sorted(express_tiers)
        elif prev_express_upgrade and prev.get("express_tiers"):
            # Языки, оставшиеся на экспресс-контенте (реюз выше), несут в тирах express_locked-
            # баннер «показана версия X, Y пока не готова» — ему нужен список реальных тиров
            # экспресса (gen_article_html, avail), иначе баннер молча исчезает и экспресс-текст
            # выдаёт себя за полный. Бейджа «экспресс» это не включает — он смотрит на express.
            a["express_tiers"] = prev["express_tiers"]
        save_data_json(versions_ru, a, date_str, article_folder, translations, captions_by_lang, abstract,
                       refined=a["refined"])
        return {"article": a, "versions": versions_ru, "translations": translations,
                "images": images, "captions": captions_by_lang, "abstract": abstract}
    except Exception as e:
        print(f"  ❌ {a['id']}: {e}")
        traceback.print_exc()
        return None


_CYRILLIC = re.compile(r"[Ѐ-ӿ]")

# «Ещё не переведено» — честная заглушка вместо русского текста под арабской обвязкой
# (юзер 2026-07-23: «если нет перевода, лучше говорить что статья ещё не переведена,
# а не показывать русскую версию»). Такую статью НЕ кладём в индекс языка: в ленте её
# не будет вовсе, страница остаётся доступной по прямой ссылке.
NOT_TRANSLATED = {
    "ru": ("Перевод готовится", "Эта статья ещё не переведена на этот язык. Она уже доступна на других языках — переключите язык в шапке."),
    "en": ("Translation in progress", "This article has not been translated into this language yet. It is already available in other languages — switch the language in the header."),
    "es": ("Traducción en curso", "Este artículo aún no está traducido a este idioma. Ya está disponible en otros idiomas: cambie el idioma en la cabecera."),
    "ar": ("الترجمة قيد الإعداد", "لم تُترجم هذه المقالة إلى هذه اللغة بعد. وهي متاحة بالفعل بلغات أخرى، فبدّل اللغة من الشريط العلوي."),
    "fr": ("Traduction en cours", "Cet article n'est pas encore traduit dans cette langue. Il est déjà disponible dans d'autres langues : changez de langue dans l'en-tête."),
    "zh": ("翻译准备中", "本文尚未翻译成该语言，但已有其他语言版本，可在页首切换语言。"),
}


def payload_in_source_lang(payload):
    """True, если в поле перевода лежит русский оригинал. translate_scipop() при неудаче
    молча возвращает исходный scipop, поэтому «переведённая» статья бывает целиком русской."""
    if not isinstance(payload, dict):
        return False
    for key in ("title", "oneliner", "description", "text"):
        v = payload.get(key)
        if isinstance(v, str) and len(v) > 20 and len(_CYRILLIC.findall(v)) / len(v) > 0.30:
            return True
    return False


def untranslated_stub(scipop_ru, lang, per_lang=None):
    """Скелет той же формы, что настоящий scipop (чтобы шаблон не развалился), но без текста.
    Заголовок берём из английской версии, если она есть — она читаема шире русской."""
    head, body = NOT_TRANSLATED.get(lang, NOT_TRANSLATED["en"])
    en = (per_lang or {}).get("en") or {}
    stub = {}
    for k, v in (scipop_ru or {}).items():
        stub[k] = "" if isinstance(v, str) else ([] if isinstance(v, list) else v)
    stub["title"] = en.get("title") or head
    stub["oneliner"] = body
    stub["text"] = body
    stub["untranslated"] = True
    return stub


def pick_scipop(versions_ru, translations, v, lang):
    """Единая точка выбора текста статьи под язык. Раньше здесь был молчаливый откат на
    versions_ru[v] — из-за него арабская страница показывала русский текст."""
    if lang == DEFAULT_LANG:
        return versions_ru[v], True
    per_lang = translations.get(v, {})
    tr = per_lang.get(lang)
    if tr and not payload_in_source_lang(tr):
        return tr, True
    return untranslated_stub(versions_ru.get(v) or {}, lang, per_lang), False


def write_article_pages(item, date_str):
    """Фаза B (последовательно): HTML по языкам×версиям + индексы/графы (read-modify-write)."""
    a, images = item["article"], item["images"]
    versions_ru, translations = item["versions"], item["translations"]
    captions = item.get("captions") or {}
    abstract = item.get("abstract") or {}
    for lang in LANGUAGES:
        lang_captions = captions_for_lang(captions, lang)
        lang_folder = Path(LANG_DIR) / lang / "archive" / date_str / a["id"]
        lang_folder.mkdir(parents=True, exist_ok=True)
        for v in VERSIONS:
            scipop, translated = pick_scipop(versions_ru, translations, v, lang)
            (lang_folder / VERSION_FILES[v]).write_text(
                gen_article_html(scipop, a, date_str, images, lang, v, lang_captions, abstract,
                                 # mini живёт в "mini" у нового конвейера (с 2026-07-27) и в
                                 # "threads" у старого — проверяем ОБА, как regenerate_all_html.
                                 # Проверка только threads молча оставила без mini.html все
                                 # статьи догона 17–28 июля (mini был сгенерирован и оплачен).
                                 has_mini=bool((versions_ru.get("popular", {})).get("threads")
                                               or (versions_ru.get("popular", {})).get("mini"))),
                encoding="utf-8")
            if translated:
                update_index(scipop, a, date_str, lang, v, abstract_for(abstract, lang, v))
    # Mini-версия — threads-текст (полный, до обрезки). Источник title/oneliner для мини —
    # popular, ЕСЛИ он настоящий контент; если popular — экспресс-заглушка (express_locked),
    # берём simple (реально сгенерированный тир) — иначе на mini-странице повиснет
    # заглушечный oneliner «Полная версия готовится» вместо настоящего заголовка.
    # ПО ЯЗЫКУ: раньше mini_scipop строился один раз из versions_ru (русской версии) ВНЕ цикла
    # по языкам и переиспользовался для всех — на mini у en/es был русский текст под локализованной
    # обвязкой. Теперь источник берём per-язык: свой tier из translations, не всегда RU.
    if (versions_ru.get("popular", {})).get("threads") or (versions_ru.get("popular", {})).get("mini"):
        for l in LANGUAGES:
            if l == DEFAULT_LANG:
                mini_source = versions_ru["popular"]
                if mini_source.get("express_locked"):
                    mini_source = versions_ru.get("simple") or mini_source
            else:
                # тот же выбор, что и для обычных тиров: без перевода — заглушка, не русский текст
                mini_source, _ok = pick_scipop(versions_ru, translations, "popular", l)
                if mini_source.get("express_locked"):
                    mini_source, _ok = pick_scipop(versions_ru, translations, "simple", l)
            # express: реальный тир (simple) хранит короткий текст в поле "mini", не "threads"
            # ("threads" — только у попап-заглушки, express_locked_scipop бэкфиллит его из RU).
            threads_text = (mini_source.get("threads") or mini_source.get("mini")
                             or (versions_ru.get("popular", {})).get("threads")
                             or (versions_ru.get("popular", {})).get("mini", ""))
            mini_scipop = dict(mini_source)
            mini_scipop["text"] = threads_text
            lf = Path(LANG_DIR) / l / "archive" / date_str / a["id"]
            lf.mkdir(parents=True, exist_ok=True)
            # mini.html больше НЕ ПИШЕТСЯ: мини убран из уровней чтения
            # (владелец 2026-08-09, причина — у order в gen_base.level_switch_links).
            # Старые файлы не удаляем: на них могли остаться ссылки снаружи.
            continue
            (lf / "mini.html").write_text(
                gen_article_html(mini_scipop, a, date_str, images, l, "mini",
                                 captions_for_lang(captions, l), abstract, has_mini=True),
                encoding="utf-8")
    update_authors_graph(a)
    update_tag_counts(versions_ru["advanced"])
    # Папку считаем здесь, а не берём из чужой области видимости: article_folder — локальная
    # переменная build_article, и эта строка роняла запись статьи с NameError. Три статьи
    # прогона 2026-07-31 были СГЕНЕРИРОВАНЫ (то есть оплачены) и потеряны на записи.
    # Картинки лежат под языком-источником — там же, где их сохранил build_article.
    ensure_article_webp(Path(LANG_DIR) / DEFAULT_LANG / "archive" / date_str / a["id"])
    print(f"  ✅ {a['id']} done")


def process_day(date_str, force=False, refresh_aggregates=True, express=False, limit=None, category=None):
    print(f"\n{'=' * 60}\n📅 {date_str}{' [экспресс]' if express else ''}{f' [{category}]' if category else ''}\n{'=' * 60}")
    for lang in LANGUAGES: ensure_lang_structure(lang)

    # category может быть НЕСКОЛЬКО категорий через запятую (мульти-периметр) — фетчим каждую,
    # объединяем+дедупим по id, и select_best ранжирует ЕДИНЫМ пулом → настоящий топ-N/день по всем
    # разделам, а не по одной категории (юзер-фидбер 2026-07-21: «20 лучших за день по всем разделам»).
    cats = [c.strip() for c in (category or "astro-ph.*").split(",") if c.strip()]
    articles, _seen = [], set()
    gen_arxiv.FETCH_FAILURES.clear()
    for cat in cats:
        for a in fetch_arxiv(date_str, category=cat):
            if a["id"] not in _seen:
                _seen.add(a["id"]); articles.append(a)
    if len(cats) > 1:
        print(f"  🔭 периметр {cats}: {len(articles)} уникальных кандидатов")
    if not articles:
        # Ноль по ВСЕМУ периметру — это не будни, а происшествие. 31 июля — 2 августа 2026
        # ночной прогон трижды подряд вернул ноль по всем 14 разделам, вышел с кодом
        # «успех», опубликовал неизменившийся сайт — и лента простояла три дня незаметно.
        # Такой же простой уже случался в июле, и длился 13 дней. Значит ноль обязан быть
        # слышен: печатаем причину и отдаём наверх отрицательный код, чтобы планировщик
        # записал неудачу, а не «rc=0».
        why = gen_arxiv.FETCH_FAILURES
        print(f"\n  ⛔ НИ ОДНОГО КАНДИДАТА по всем разделам за {date_str}.")
        if why:
            print(f"     arXiv отказал {len(why)} раз(а) из {len(cats)}:")
            for w in why[:5]:
                print(f"       · {w}")
            print("     Это отказ добычи, а не пустой день: статьи есть, мы их не получили.")
        else:
            print("     arXiv ответил без ошибок и отдал пусто. Если это будний день, а не")
            print("     выходной, — смотри лаг выгрузки и не сменился ли формат запроса.")
        return -1
    best = select_best(articles, date_str)
    if limit is not None:
        best = best[:limit]
    # Потолки долей по разделам (config.category_caps, владелец 2026-07-31: «математики
    # максимум 2%, только самое интересное»). Весов в отборе нет — режем уже ранжированный
    # список: статья раздела с потолком остаётся, только если сама вошла в общий топ И не
    # выбрала квоту. Префиксное совпадение по primary_category: "math." ловит math.CO и
    # math.NT, но НЕ math-ph (это физика). Квота от размера дня, минимум 1 — иначе при
    # 25 статьях 2% давали бы вечный ноль и раздел не появлялся бы никогда.
    caps = config.get("category_caps") or {}
    if caps and best:
        quota = {p: max(1, int(share * len(best))) for p, share in caps.items()}
        used = {p: 0 for p in caps}
        kept = []
        for a in best:
            pfx = next((p for p in caps if a.get("primary_category", "").startswith(p)), None)
            if pfx is None or used[pfx] < quota[pfx]:
                kept.append(a)
                if pfx is not None:
                    used[pfx] += 1
            else:
                print(f"  ⏭️ {a['id']} — потолок доли {pfx}* ({quota[pfx]} на день) выбран")
        best = kept
    inputs = load_generation_inputs()

    print(f"  🚀 Обработка {len(best)} статей в {ARTICLE_WORKERS} потока...")
    with ThreadPoolExecutor(max_workers=ARTICLE_WORKERS) as ex:
        prepared = [r for r in ex.map(lambda a: build_article(a, date_str, inputs, force, express), best) if r]

    for item in prepared:
        try:
            write_article_pages(item, date_str)
        except Exception as e:
            print(f"  ❌ {item['article']['id']}: запись страниц упала ({e}) — LLM-контент уже оплачен, но не записан; пропускаю, остальные статьи не теряем")
            traceback.print_exc()

    # ── Транзакционность заготовок ────────────────────────────────────────────────
    # Папка статьи создаётся ДО data.json: сначала references/fulltext/картинки, и если
    # генерация оборвалась между ними, остаётся заготовка — папка без data.json. Аудит
    # 16 августа: 349 таких вычистили руками, за четыре дня наросло 243 новых, и они
    # снова глушили run.py check. Чистим В КОНЦЕ КАЖДОГО дня, но только СВОИ: заготовки
    # этого date_str. Чужие дни не трогаем — там может прямо сейчас работать другой
    # прогон, и его недописанная папка — не мусор, а работа в полёте.
    day_dir = Path(LANG_DIR) / DEFAULT_LANG / "archive" / date_str
    if day_dir.exists():
        for stub in day_dir.iterdir():
            if stub.is_dir() and not (stub / "data.json").exists():
                try:
                    shutil.rmtree(stub)
                    print(f"  🧹 заготовка без data.json удалена: {stub.name}")
                except Exception as _e:
                    print(f"  ⚠️ заготовка {stub.name} не удалилась: {type(_e).__name__}")

    if refresh_aggregates and prepared:
        for lang in LANGUAGES:
            update_all_tags(lang)
            update_all_scientists(lang)
            update_all_sections(lang)
            generate_archive_page(lang)
            generate_analytics_page(lang)
        generate_analytics_page(lang)
        update_all_authors()
        generate_sitemaps()
        generate_llms_txt()
        generate_feeds()
        generate_status_page()
    print(f"\n✅ {date_str}: {len(prepared)} articles generated")
    return len(prepared)


# ── Обслуживание: reindex / графы / удаление / целостность ──
def _index_entry(scipop, data, date_str, lang, version):
    url = f"/{LANG_DIR}/{lang}/archive/{date_str}/{data['id']}/{VERSION_FILES[version]}"
    abstract = abstract_for(data.get("abstract"), lang, version)
    # Проверяем ровно то, что запросит страница: карточка грузит t_ai.webp с откатом на
    # ai.webp, а здесь раньше проверялся ai.jpg. Обычно одно следует из другого (webp
    # делается в точке рождения картинки), но там, где конверсия не прошла или файл вышел
    # вырожденным, индекс обещал обложку, которой нет, и карточка ловила 404.
    _img_dir = Path(LANG_DIR) / DEFAULT_LANG / "archive" / date_str / data["id"]
    has_image = any((_img_dir / n).exists() and (_img_dir / n).stat().st_size > 1000
                    for n in ("t_ai.webp", "ai.webp"))
    return {
        "id": data["id"], "version": version,
        "title": scipop.get("title", data.get("original_title", "")),
        "oneliner": card_cut(strip_markers(scipop.get("oneliner", ""))),
        # В карточку идёт НАЧАЛО ПРОСТОГО ТЕКСТА, а не поле description.
        #
        # description пишется как справка и звучит соответственно: «у ядер-близнецов число
        # протонов и нейтронов меняется местами, физики использовали разницу радиусов, чтобы
        # прощупать тензорные силы». Термины, ни одного образа. А простой текст той же статьи
        # начинается так: «в атомном ядре протоны и нейтроны упакованы так плотно, что между
        # ними действуют силы, напоминающие туго натянутые пружины».
        #
        # Владелец 2026-08-09: «в карточку списка — простой понятный текст». Карточка — первое,
        # что человек видит в ленте, и по ней решает, читать ли дальше. Справкой не заманишь.
        "description": strip_markers(_card_text(scipop)),
        "abstract": strip_markers(abstract)[:1500],
        "threads": strip_markers(data.get("threads", ""))[:480],
        "thumbs": data.get("thumbs", 0),
        "authors": data.get("authors", [])[:50], "date": date_str,  # до 50 — лента показывает ≤20, >20 разворачивает
        # Теги В ИНДЕКС — тоже из вектора. Я поправил показ на странице статьи и забыл
        # про индекс, а по нему живут лента, поиск и облако тегов: после полной пересборки
        # страницы были размечены по смыслу, а облако осталось прежним — 306 тегов вместо
        # 368 и те же 46% на десяти самых частых. Один источник правды, а не два.
        "tags": _display_tags(scipop),
        # Законы в индексе не было вовсе — на карточке их показать было нечем, хотя в data.json
        # они лежат с самого введения слоя «Законы». Владелец 2026-08-02: показывать на карточке
        # теги, учёных и законы в едином графическом ключе.
        # Законы в индексе — из вектора, как и на странице. Иначе карточка в ленте
        # покажет один набор, а страница другой.
        "laws": (scipop.get("laws_vec") or scipop.get("laws") or []),
        "scientists": _display_sci(scipop), "url": url,
        "reading": reading_minutes(scipop),
        "categories": data.get("categories", []),
        "primary_category": data.get("primary_category", ""),
        "express": data.get("express", False),
        # Есть ли у статьи раздел «Взгляд машины знаний» — советы автору разобранной работы.
        # Владелец 14 августа: «я бы добавил такую же галочку для отображения страниц с
        # рекомендациями, мне было бы так удобно их искать». Одного флага хватает: сам
        # текст советов в индекс не кладём — он большой, а искать надо не по нему.
        "advice": bool((data.get("recommend") or {}).get(DEFAULT_LANG)),
        "image": has_image,
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
                # Непереведённую статью в ленту языка не пускаем: version_scipop откатывается
                # на русский оригинал, и карточки в арабской ленте выходили русскими.
                if scipop and not (lang != DEFAULT_LANG and payload_in_source_lang(scipop)):
                    buckets[lang][version].append(_index_entry(scipop, data, date_str, lang, version))
    for lang in LANGUAGES:
        base = Path(LANG_DIR) / lang
        base.mkdir(parents=True, exist_ok=True)
        for version in VERSIONS:
            # Атомарно: 14 августа этот файл уехал в облако обрезанным (7,3 МБ вместо
            # 10,9) — его прочитали ровно в тот миг, когда он был обнулён под новую
            # запись, и главная перестала показывать статьи на всех пяти языках.
            write_json_atomic(base / VERSION_INDEX[version], buckets[lang][version])
            # Маленький индекс последних статей для мгновенной первой отрисовки ленты: полный
            # индекс тира ~3.6МБ, и лента ждала его целиком (юзер 2026-07-23: «долго грузится
            # первый раз»). Тут — только N свежих записей (~150КБ), лента рисуется сразу, полный
            # индекс догружается в фоне для поиска/фильтров/«показать ещё».
            latest = sorted(buckets[lang][version], key=lambda e: e.get("date", ""), reverse=True)[:LATEST_INDEX_N]
            write_json_atomic(base / VERSION_INDEX_LATEST[version], latest)
    total = sum(len(b["popular"]) for b in buckets.values())
    # Дата последней сборки — витрина «обновлено …» на дашборде/в статистике (юзер 2026-07-24).
    import datetime
    Path("data").mkdir(exist_ok=True)
    Path("data/build-info.json").write_text(
        json.dumps({"built": datetime.date.today().isoformat()}, ensure_ascii=False), encoding="utf-8")
    # Снимок в памяти устарел — страницы, которые соберутся дальше в этом же прогоне,
    # должны видеть только что записанные индексы, а не то, что было до перезаписи.
    drop_index_cache()
    print(f"  ✅ Индексы пересобраны ({total} записей popular по всем языкам) + latest-{LATEST_INDEX_N}")


def rebuild_author_graph():
    """authors-graph.json полностью выводится из статей — пересобираем начисто."""
    graph = {}
    for data, _ in iter_articles():
        # Мусорные "авторы" (голая пунктуация — артефакт парсинга списка авторов) ломали
        # author_slug()/запись файла страницы автора — отсекаем на входе в граф.
        authors = [a for a in data.get("authors", []) if any(c.isalpha() for c in a)]
        for a in authors:
            g = graph.setdefault(a, {"articles": [], "coauthors": [], "article_count": 0})
            if data["id"] not in g["articles"]:
                g["articles"].append(data["id"])
            for ca in authors:
                if len(g["coauthors"]) >= MAX_COAUTHORS:
                    break
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
    write_json_atomic(gp, graph)
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
            update_all_sections(lang)
        update_all_authors()
    if not removed:
        print(f"  ⚠️ статья {aid} не найдена")
    return removed


def fetch_one_arxiv(aid):
    """Метаданные одной статьи по arXiv id."""
    try:
        r = _get_with_retry(f"http://es.arxiv.org/api/query?id_list={aid}", timeout=30)
    except requests.exceptions.RequestException:
        return None
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


def regenerate_article(aid, force=True, only_langs=None):
    """Пересоздаёт одну статью (генерит заново ПОВЕРХ старой, чинит агрегаты).

    Папку больше НЕ удаляем перед генерацией (техдолг воронки, 2026-07-31): старый data.json —
    источник реюза оплаченного (mini экспресса, переводы аннотации/подписей, FLUX-обложка,
    см. build_article), а при падении генерации статья остаётся живой, а не исчезает с сайта.
    Раньше delete_article стирал папку ПЕРВЫМ шагом — оплаченный api/express-ru.json и обложка
    гибли до того, как новая генерация хотя бы начиналась. Чистое пересоздание без реюза:
    run.py delete <id>, затем regen.

    only_langs — «полная на языке запроса»: перевести только эти языки; остальные сохраняют
    прежний контент (экспресс) или честную заглушку."""
    dates = find_article_dates(aid)
    date_str = dates[0] if dates else None
    a = fetch_one_arxiv(aid)
    if not a:
        print(f"  ❌ не удалось получить метаданные {aid} с arXiv")
        return False
    if not date_str:
        date_str = iso_day(a.get("published")) or TARGET_DATE
    for lang in LANGUAGES: ensure_lang_structure(lang)
    item = build_article(a, date_str, load_generation_inputs(), force=True, only_langs=only_langs)
    if not item:
        print(f"  ❌ {aid}: генерация не удалась — старая версия статьи не тронута")
        return False
    write_article_pages(item, date_str)
    rebuild_indexes()
    rebuild_author_graph()
    recompute_tag_counts()
    for lang in LANGUAGES:
        update_all_tags(lang)
        update_all_scientists(lang)
        update_all_sections(lang)
    update_all_authors()
    print(f"  ✅ {aid} пересоздана ({date_str})")
    return True


def iso_day(v):
    """Дата статьи в виде ГГГГ-ММ-ДД.

    arXiv отдаёт published то в ISO, то в формате письма («Fri, 03 Jul 2026 12:00:00 GMT»).
    Слепое обрезание до десяти символов давало имя папки «Fri, 03 Ju» — папку-обрубок, из-за
    которой ломались ссылки во всех четырёх языках (ловилось дважды: 2026-07-27)."""
    v = (v or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", v):
        return v[:10]
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})", v)
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}",
                                     "%d %b %Y").strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


def _refresh_all_aggregates():
    for lang in LANGUAGES:
        update_all_tags(lang)
        update_all_scientists(lang)
        update_all_sections(lang)
    update_all_authors()


def generate_ids(id_list, force=False, express=False, allow_restricted=False):
    """Генерирует конкретные статьи по списку arXiv id. Дата берётся из метаданных
    статьи (published), поэтому статьи корректно ложатся в свои дни.

    express=True — режим «опоры пакетом»: когда мы вытаскиваем вокруг разобранной работы
    куст из всего arXiv (tools/field.py), эти соседи нужны не как самостоятельные статьи,
    а как поле вокруг. Полный разбор каждого стоил бы десятикратно дороже экспресса и
    ничего бы не добавил: опоре достаточно аннотации.
    """
    for lang in LANGUAGES: ensure_lang_structure(lang)
    inputs = load_generation_inputs()

    def prep(aid):
        a = fetch_one_arxiv(aid)
        if not a:
            print(f"  ❌ {aid}: нет метаданных на arXiv")
            return None
        date_str = iso_day(a.get("published")) or TARGET_DATE
        item = build_article(a, date_str, inputs, force=force, express=express,
                             allow_restricted=allow_restricted)
        if item: item["date_str"] = date_str
        return item

    print(f"  🚀 Генерация {len(id_list)} статей по id в {ARTICLE_WORKERS} потока...")
    with ThreadPoolExecutor(max_workers=ARTICLE_WORKERS) as ex:
        prepared = [r for r in ex.map(prep, id_list) if r]
    for item in prepared:
        try:
            write_article_pages(item, item["date_str"])
        except Exception as e:
            print(f"  ❌ {item['article']['id']}: запись страниц упала ({e}) — пропускаю, остальные статьи не теряем")
            traceback.print_exc()
    if prepared:
        _refresh_all_aggregates()
    print(f"\n✅ Сгенерировано по id: {len(prepared)} из {len(id_list)}")
    return len(prepared)


def bulk_generate(selection_path, batch_size=100, express=True, force=False, skip_peak_check=False, max_batches=None):
    """Читает результат article_bulk_select.py (уже отобранный/ранжированный/license-audited
    список) и генерит его батчами по batch_size — в порядке приоритета (score), не по дате.
    Перед КАЖДЫМ батчем — проверка DeepSeek peak-hour: если сейчас пик или пик начнётся меньше
    чем через 2ч, останавливаемся (батч может не успеть проехать по обычной цене). Возобновляемо:
    повторный запуск с тем же файлом просто пропустит уже сгенерированные статьи (build_article
    сам идемпотентен) и продолжит с того места, где остановились. max_batches — остановиться
    после N батчей (напр. для пробного прогона), даже если очередь и бюджет позволяют больше."""
    for lang in LANGUAGES: ensure_lang_structure(lang)
    data = json.loads(Path(selection_path).read_text(encoding="utf-8"))
    ready = data.get("ready", [])
    print(f"📋 bulk-generate: {len(ready)} статей в очереди (run {data.get('run_id')}, файл {selection_path})")
    inputs = load_generation_inputs()
    total_batches = max(1, (len(ready) - 1) // batch_size + 1)
    total_generated = 0

    for bi in range(0, len(ready), batch_size):
        batch = ready[bi:bi + batch_size]
        batch_num = bi // batch_size + 1
        if max_batches and batch_num > max_batches:
            print(f"\n🏁 Достигнут лимит --max-batches {max_batches} — останавливаюсь раньше срока.")
            break
        if not skip_peak_check:
            is_peak, hrs = deepseek_peak_status()
            if is_peak or hrs < 2:
                why = "СЕЙЧАС пиковые часы DeepSeek (цена x2)" if is_peak else f"через {hrs:.1f}ч начнутся пиковые часы DeepSeek"
                print(f"\n⏸️ Батч {batch_num}/{total_batches} ({len(batch)} статей) отложен — {why}. "
                      f"Лучше подождать не-пиковое окно. Повторный запуск с тем же файлом продолжит с этого места.")
                break

        print(f"\n🚀 Батч {batch_num}/{total_batches}: {len(batch)} статей...")

        def _prep(a):
            date_str = iso_day(a.get("published")) or TARGET_DATE
            item = build_article(a, date_str, inputs, force, express)
            if item: item["date_str"] = date_str
            return item

        with ThreadPoolExecutor(max_workers=ARTICLE_WORKERS) as ex:
            prepared = [r for r in ex.map(_prep, batch) if r]
        written = 0
        for item in prepared:
            try:
                write_article_pages(item, item["date_str"])
                written += 1
            except Exception as e:
                print(f"  ❌ {item['article']['id']}: запись страниц упала ({e}) — пропускаю, остальные статьи не теряем")
                traceback.print_exc()
        total_generated += written
        print(f"  ✅ Батч {batch_num}: {written}/{len(batch)} сгенерировано (остальные — уже есть/лицензия/ошибка)")

    if total_generated:
        print("\n🔄 Финальный пересчёт агрегатов...")
        for lang in LANGUAGES:
            update_all_tags(lang)
            update_all_scientists(lang)
            update_all_sections(lang)
            generate_archive_page(lang)
            generate_analytics_page(lang)
        generate_analytics_page(lang)
        update_all_authors()
        generate_sitemaps()
        generate_llms_txt()
        generate_feeds()
        generate_status_page()
    print(f"\n🎉 bulk-generate: сгенерировано {total_generated} из {len(ready)} в очереди")
    return total_generated


def search_arxiv_author(name, from_date=None, to_date=None, max_results=200):
    """Ищет статьи автора на arXiv (по строке имени). Возвращает список
    {id, title, published}. Имя-строка → возможны однофамильцы, поэтому режим
    предполагает превью-подтверждение перед генерацией."""
    q = f'au:"{name}"'
    if from_date and to_date:
        f = from_date.replace("-", "") + "0000"
        t = to_date.replace("-", "") + "2359"
        q += f" AND submittedDate:[{f} TO {t}]"
    r = _get_with_retry("http://es.arxiv.org/api/query", params={
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
            "published": iso_day(e.find("atom:published", ns).text),
        })
    return out


def backfill_abstracts(force=False):
    """Бэкфилл «Аннотаций»: адаптирует авторский arXiv-abstract (из arxiv-atom.xml) → data.json.abstract{lang}.
    Возобновляемо: где abstract уже есть — пропускаем (--force переписывает)."""
    import xml.etree.ElementTree as ET
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    targets = [l for l in LANGUAGES if l != DEFAULT_LANG]
    print(f"  📄 Бэкфилл аннотаций (языки: {', '.join(LANGUAGES)})")

    def one(item):
        data, folder = item
        if (data.get("abstract") or {}).get(DEFAULT_LANG) and not force:
            return 0
        summary = ""
        atom = folder / "arxiv-atom.xml"
        if atom.exists():
            try:
                root = ET.fromstring(atom.read_text(encoding="utf-8"))
                el = root.find(".//atom:entry/atom:summary", ns) or root.find(".//atom:summary", ns)
                summary = (el.text or "").strip().replace("\n", " ") if el is not None else ""
            except Exception:
                summary = ""
        if not summary:
            print(f"    · {data['id']} — нет summary, пропуск")
            return 0
        ru = generate_abstract(summary)
        if REFINE and ru:
            ru = refine_abstract(ru)
        if not ru:
            print(f"    · {data['id']} — аннотация пустая")
            return 0
        abstract = {DEFAULT_LANG: ru}
        for l in targets:
            try:
                abstract[l] = translate_scipop(ru, l) or ru
            except Exception:
                abstract[l] = ru
        data["abstract"] = abstract
        (folder / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"    · {data['id']} — аннотация ✓")
        return 1

    items = list(iter_articles())
    with ThreadPoolExecutor(max_workers=min(10, len(items) or 1)) as ex:
        n = sum(ex.map(one, items))
    print(f"  ✅ Аннотаций: {n}")


def backfill_images(force=False, gen_images=False, preset="image_cheap"):
    """Бэкфилл обложек статей — ai.jpg = крупнейшая картинка из самого PDF (см. pick_cover_image),
    не FLUX, БЕСПЛАТНО. Ищет уже сохранённые PDF-картинки в папке статьи (0.jpg, 1.jpg, ... — так
    их называет save_images) и берёт самую крупную по площади.

    Если в PDF картинок вообще не было (~35% корпуса, юзер-фидбек 2026-07-17: "структура не
    должна теряться в списках и на карточках") — фоллбэк на дешёвую AI-генерацию (FLUX-1-schnell
    по умолчанию, ~$0.002/картинка), тем же паттерном, что и backfill_tag_law_images: без ключа
    или без gen_images=True картинку не генерим, только честно метим data["image_pending"]=True
    (карточка не ломается — .ai-cover-ph placeholder), gen_images=True реально тратит бюджет и
    записывает data["image_model"], чтобы дешёвые можно было потом точечно апгрейднуть."""
    has_key = bool(os.environ.get("DEEPINFRA_API_KEY", "")) and gen_images
    print(f"  🖼️ Бэкфилл обложек статей (PDF, бесплатно; AI-фоллбэк: "
          f"{'да, preset=' + preset if has_key else 'НЕТ — только честная пометка pending'})")

    def one(item):
        data, folder = item
        img = folder / "ai.jpg"
        if img.exists() and not force:
            return False, False
        pdf_images = sorted((p for p in folder.glob("*.jpg") if p.stem.isdigit()), key=lambda p: int(p.stem))
        cover = pick_cover_image([str(p) for p in pdf_images])
        got_img = via_ai = False
        if cover:
            shutil.copy(cover, img)
            got_img = True
        elif has_key:
            scipop = (data.get("popular", {}).get(DEFAULT_LANG) or data.get("simple", {}).get(DEFAULT_LANG)
                      or data.get("advanced", {}).get(DEFAULT_LANG) or {})
            prompt = generate_image_prompt(scipop)
            if prompt:
                got_img, model_used = generate_image(prompt, img, preset=preset)
                if got_img:
                    data["image_pending"] = False
                    data["image_model"] = model_used
                    via_ai = True
        if not got_img and not cover:
            data["image_pending"] = True
        nthumbs = make_thumbnails(folder)  # t_ai + до 2 PDF — обновляем всегда
        if data.get("thumbs") != nthumbs or via_ai or (not got_img and not cover):
            data["thumbs"] = nthumbs
            (folder / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"    · {data['id']} (обложка={'ok' if got_img else '—'}{' (AI)' if via_ai else ''}, миниатюр PDF={nthumbs})")
        return got_img, via_ai

    items = list(iter_articles())
    with ThreadPoolExecutor(max_workers=min(10, len(items) or 1)) as ex:
        results = list(ex.map(one, items))
    n_img = sum(1 for i, _ in results if i)
    n_ai = sum(1 for _, a in results if a)
    print(f"  ✅ Обложек: {n_img} (из них AI-фоллбэк: {n_ai})")


def entity_image_url(kind, entity_id):
    """URL AI-обложки тега/закона (единая на все языки, живёт под default_lang), либо '' если нет файла."""
    # Файл на диске остаётся .jpg (его пишет генератор картинок), а отдаём .webp — он в 3 раза
    # легче и уже сконвертирован (webp_convert.py). Аудит 2026-07-27 нашёл, что у тегов и законов
    # ссылки остались старыми, хотя webp-файлы были готовы.
    p = Path(LANG_DIR) / DEFAULT_LANG / kind / "img" / f"{entity_id}.jpg"
    w = p.with_suffix(".webp")
    if w.exists():
        return f"/{LANG_DIR}/{DEFAULT_LANG}/{kind}/img/{entity_id}.webp"
    return f"/{LANG_DIR}/{DEFAULT_LANG}/{kind}/img/{entity_id}.jpg" if p.exists() else ""


def backfill_tag_law_images(force=False, gen_images=False, preset="image"):
    """AI-обложки для тегов и законов — по образцу статей: один промпт+картинка на сущность (не на язык).
    Промпт хранится в источнике (lang/{default}/data/tags.json|laws.json), картинка —
    lang/{default}/{tags|laws}/img/{id}.jpg (общая для всех языков, как ai.jpg у статей).

    gen_images=False (по умолчанию) — реальную FLUX-генерацию НЕ трогаем, только промпт (дёшево).
    Новые сущности без картинки помечаются entry["image_pending"]=True (честно: промпт готов,
    картинки нет — ждёт бюджета); блок .ai-cover просто не рендерится, место не теряется.
    gen_images=True — реальная трата (нужен бюджет): генерит картинку через FLUX и снимает pending
    у тех, кому реально досталась картинка. Уже существующие картинки этот флаг не трогает.
    preset — какой блок config.agents использовать ("image"/"image_cheap"/"image_quality") —
    записывается в entry["image_model"], чтобы потом легко найти дёшево сгенеренные и апгрейднуть."""
    has_key = bool(os.environ.get("DEEPINFRA_API_KEY", "")) and gen_images
    print(f"  🖼️ Обложки тегов/законов (картинки: {'да, трачу бюджет, preset=' + preset if has_key else 'НЕТ — только промпты + честная пометка pending'})")

    def one(kind, entity_id, entry):
        prompt = entry.get("image_prompt", "")
        got_prompt = got_img = False
        if not prompt or force:
            # Ref-промт (полу-схема с верной геометрией принципа), НЕ статейный кинематографичный —
            # юзер-фидбек 2026-07-21: «визуализировать закон, среднее между схемой и принципом,
            # главное не ошибиться в пространстве».
            new_prompt = generate_ref_image_prompt(
                entry.get("name", entity_id),
                entry.get("description_popular", "") or entry.get("description", "") or entry.get("mini", ""))
            if new_prompt:
                prompt = new_prompt
                entry["image_prompt"] = prompt
                got_prompt = True
        img_dir = Path(LANG_DIR) / DEFAULT_LANG / kind / "img"
        img_dir.mkdir(parents=True, exist_ok=True)
        img = img_dir / f"{entity_id}.jpg"
        if has_key and prompt and (force or not img.exists() or entry.get("image_pending")):
            got_img, model_used = generate_image(prompt, img, preset=preset)
            if got_img:
                entry["image_pending"] = False
                entry["image_model"] = model_used
        elif prompt and not img.exists():
            entry["image_pending"] = True
        return got_prompt, got_img

    for kind, fname in (("tags", "tags.json"), ("laws", "laws.json")):
        p = Path(LANG_DIR) / DEFAULT_LANG / "data" / fname
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        items = list(data.items())
        with ThreadPoolExecutor(max_workers=min(10, len(items) or 1)) as ex:
            results = list(ex.map(lambda kv: one(kind, kv[0], kv[1]), items))
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        n_prompt = sum(1 for pr, _ in results if pr)
        n_img = sum(1 for _, im in results if im)
        n_pending = sum(1 for _, entry in items if entry.get("image_pending"))
        print(f"    {kind}: промптов {n_prompt}, картинок {n_img}, ждут бюджета {n_pending}")


def translate_article_lang(aid, target_lang, force=False):
    """Переводит ОДНУ уже существующую статью на ОДИН язык — точечно, без трогания остальных
    языков/статей. Нужно для: 1) добавить конкретный язык одной статье вручную, 2) чистый замер
    стоимости ПЕРЕВОДА отдельно от генерации (генерация уже мерялась через `run.py regen`).
    Возобновляемо (force=False пропускает версии, где перевод уже есть)."""
    if target_lang == DEFAULT_LANG:
        print(f"  ⏭️ {target_lang} — язык по умолчанию, перевод не нужен")
        return False
    dates = find_article_dates(aid)
    if not dates:
        print(f"  ❌ {aid}: не найдена")
        return False
    date_str = dates[0]
    folder = Path(LANG_DIR) / DEFAULT_LANG / "archive" / date_str / aid
    data_path = folder / "data.json"
    if not data_path.exists():
        print(f"  ❌ {aid}: нет data.json в {folder}")
        return False
    data = json.loads(data_path.read_text(encoding="utf-8"))
    ensure_lang_structure(target_lang)

    changed = False
    for version in VERSIONS:
        vdata = data.get(version, {})
        # Наличия ключа мало: если под ним лежит русский оригинал (перевод молча не
        # состоялся), «уже переведено» — неправда. Такую версию сборка индекса всё равно
        # выбросит из ленты языка, и статья исчезнет, оставаясь для нас переведённой.
        # 2026-08-06: так потерялись 47 французских статей, 3 английских, 1 испанская,
        # 2 арабских — и точечный перевод отказывался их чинить без --force, потому что
        # проверял ту же мерку, что и сломала учёт.
        have = vdata.get(target_lang)
        if have and not force and not payload_in_source_lang(have):
            continue
        src = vdata.get(DEFAULT_LANG)
        if not src:
            continue
        got = translate_scipop(src, target_lang)
        # Переводчик отдаёт None, когда проверки не сошлись трижды (числа, маркеры). Записывать
        # это в data.json нельзя: ключ появится, значение будет пустым, и следующий прогон
        # снова сочтёт статью «имеющей перевод». Ровно так и накопились нынешние потери.
        # Нет перевода — значит нет ключа, и статью видно как непереведённую.
        if not got:
            print(f"    ⚠️ {aid} · {version} → {target_lang}: перевод не сошёлся, ключ не пишу")
            continue
        vdata[target_lang] = got
        data[version] = vdata
        changed = True

    abstract = data.get("abstract") or {}
    abstract_ru = abstract.get(DEFAULT_LANG)
    if abstract_ru and (force or not abstract.get(target_lang)):
        abstract[target_lang] = translate_scipop(abstract_ru, target_lang) or abstract_ru
        data["abstract"] = abstract
        changed = True

    captions = data.get("captions") or {}
    if target_lang != "en" and isinstance(captions, dict) and captions.get("en") and (force or not captions.get(target_lang)):
        captions[target_lang] = translate_captions(captions["en"], target_lang)
        data["captions"] = captions
        changed = True

    if not changed:
        print(f"  ⏭️ {aid} → {target_lang}: уже переведено (--force для повтора)")
        return False

    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # HTML только для нового языка — остальные языки этой статьи не трогаем.
    images = sorted([p for p in folder.glob("*.jpg") if p.stem.isdigit()], key=lambda p: int(p.stem))
    lang_captions = captions_for_lang(captions, target_lang)
    article_obj = {
        "id": data["id"], "title": data.get("original_title", ""),
        "authors": data.get("authors", []), "license_url": data.get("license", ""),
        "license_name": data.get("license_name", "CC BY"),
        "categories": data.get("categories", []), "primary_category": data.get("primary_category", ""),
        "refined": data.get("refined", False), "express": data.get("express", False),
        "express_tiers": data.get("express_tiers", []),
    }
    lang_folder = Path(LANG_DIR) / target_lang / "archive" / date_str / aid
    lang_folder.mkdir(parents=True, exist_ok=True)
    base_scipop = version_scipop(data, "popular", target_lang) or version_scipop(data, "simple", target_lang) or {}
    if base_scipop.get("express_locked"):
        base_scipop = version_scipop(data, "simple", target_lang) or base_scipop
    threads_text = base_scipop.get("threads") or base_scipop.get("mini") or ""
    for version in VERSIONS:
        scipop = version_scipop(data, version, target_lang)
        if not scipop:
            continue
        html = gen_article_html(scipop, article_obj, date_str, [str(p) for p in images],
                                 target_lang, version, lang_captions, data.get("abstract") or {},
                                 has_mini=bool(threads_text))
        (lang_folder / VERSION_FILES[version]).write_text(html, encoding="utf-8")
    if threads_text:
        mini_scipop = dict(base_scipop)
        mini_scipop["text"] = threads_text
        html = gen_article_html(mini_scipop, article_obj, date_str, [str(p) for p in images],
                                 target_lang, "mini", lang_captions, data.get("abstract") or {})
        (lang_folder / "mini.html").write_text(html, encoding="utf-8")

    rebuild_indexes()
    print(f"  ✅ {aid} → {target_lang} переведена")
    return True


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
                if vdata.get(DEFAULT_LANG) and lang != DEFAULT_LANG and lang not in vdata:
                    problems.append(("missing_translation", aid, f"{version}/{lang}"))
        # Проверка mini.html
        mini_page = Path(LANG_DIR) / DEFAULT_LANG / "archive" / date_str / aid / "mini.html"
        if data.get("threads") and not mini_page.exists():
            problems.append(("missing_html", aid, "mini"))

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