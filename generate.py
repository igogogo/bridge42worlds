#!/usr/bin/env python3
"""
Bridge For Two Worlds — генератор научно-популярных статей из arXiv.
arXiv astro-ph → DeepSeek → HTML + data.json + API-ответы
"""

import os, sys, json, time, re, random, calendar, requests, traceback, hashlib, shutil, xml.etree.ElementTree as ET
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
from common import CONFIG as config, DEEPSEEK_API_KEY, LANGUAGES, DEFAULT_LANG, LANG_DIR, as_list, deepseek_peak_status  # noqa: F401
from gen_base import *    # noqa: F401,F403 — константы и базовые хелперы
from gen_arxiv import *   # noqa: F401,F403 — arXiv/PDF-слой
from gen_arxiv import _get_with_retry  # leading underscore не попадает в import *

if not DEEPSEEK_API_KEY:
    print("⚠️  DEEPSEEK_API_KEY не задан — доступны только офлайн-операции (html/reindex/check/delete)")

print(f"🚀 {SITE_NAME} generator")
print(f"   Languages: {LANGUAGES}")

_ASSET_VER = None


def asset_ver():
    """Хэш от содержимого всех css/js — заменяет ручной ?v=N (забывали бампать, у части
    посетителей оставался закэшированный старый файл). Меняется контент — меняется хэш
    автоматически, ничего руками поднимать не нужно. Считается один раз за прогон."""
    global _ASSET_VER
    if _ASSET_VER is None:
        h = hashlib.sha256()
        for p in sorted(Path("css").glob("*.css")) + sorted(Path("js").glob("*.js")):
            h.update(p.read_bytes())
        _ASSET_VER = h.hexdigest()[:10]
    return _ASSET_VER


# ── Images ──
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
            f'<figure class="mosaic-item"><a href="{base}/{i}.jpg" class="mosaic-open">'
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


from gen_llm import *  # LLM-слой вынесен в gen_llm.py

REFINE = os.environ.get("REFINE") == "1" or CONFIG.get("refine", False)

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


def build_jsonld(scipop, article, date_str, lang, canonical_url, abstract_full=""):
    data = {
        "@context": "https://schema.org", "@type": "ScholarlyArticle",
        "headline": scipop.get("title", article.get("title", ""))[:110],
        "description": scipop.get("oneliner", "")[:250],
        "inLanguage": lang, "datePublished": date_str,
        "url": canonical_url,
        "image": f"{SITE_URL}/{LANG_DIR}/{DEFAULT_LANG}/archive/{date_str}/{article['id']}/ai.jpg",
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
        for f in formulas if f.get("latex")
    )


def trivia_html(fun_fact, scifi=""):
    """Единый блок «интересный факт + в фантастике» под текстом статьи (одна карточка, не два разрозненных блока)."""
    rows = []
    if fun_fact:
        rows.append(f'<p class="fact">🎯 {safe(fun_fact)}</p>')
    if scifi:
        rows.append(f'<p class="fact fact-scifi">🎬 {safe(scifi)}</p>')
    return f'<div class="fun-fact">{"".join(rows)}</div>' if rows else ""


def abstract_for(abstract, lang, version):
    """Текст «Аннотации» нужного языка+версии с откатами. Обратно совместимо со старым
    плоским форматом (abstract{lang} = строка → одна на все версии). mini берёт popular."""
    a = (abstract or {}).get(lang) or (abstract or {}).get(DEFAULT_LANG) or {}
    if isinstance(a, str):
        return a
    if isinstance(a, dict):
        if version == "mini":
            return ""  # у «мини» аннотация не нужна
        return a.get(version) or a.get("popular") or next((t for t in a.values() if t), "")
    return ""


# Виджет обратной связи (реакции 👍👎⭐ + чипы + коммент) — общий для статей/тегов/законов/учёных.
# entity_type пишется в БД (likes.entity_type/feedback.entity_type) — see docs/engagement-expand-migration.sql.
FEEDBACK_CHIPS_LOC = [
    ("reads_well", {"ru": "Хорошо читается", "en": "Reads well", "zh": "读起来顺畅", "fr": "Se lit bien", "ar": "سهل القراءة"}),
    ("too_long", {"ru": "Многовато текста", "en": "Too long", "zh": "篇幅偏长", "fr": "Trop long", "ar": "طويل جدًا"}),
    ("unclear", {"ru": "Непонятно", "en": "Unclear", "zh": "不易懂", "fr": "Peu clair", "ar": "غير واضح"}),
    ("great", {"ru": "Отлично", "en": "Great", "zh": "很棒", "fr": "Excellent", "ar": "ممتاز"}),
    ("dry", {"ru": "Суховато", "en": "A bit dry", "zh": "略枯燥", "fr": "Un peu sec", "ar": "جاف قليلاً"}),
    ("too_simple", {"ru": "Слишком упрощено", "en": "Too simplified", "zh": "过于简化", "fr": "Trop simplifié", "ar": "مبسّط جدًا"}),
]
FEEDBACK_UI_LOC = {
    "ru": ("Как читается? (поможет улучшить тексты)", "+ написать комментарий", "комментарий (необязательно)", "отправить"),
    "en": ("How does it read? (helps us improve)", "+ add a comment", "comment (optional)", "send"),
    "zh": ("读起来怎么样？(帮助我们改进)", "+ 添加评论", "评论（可选）", "发送"),
    "fr": ("Lecture agréable ? (nous aide à améliorer)", "+ ajouter un commentaire", "commentaire (facultatif)", "envoyer"),
    "ar": ("كيف كانت القراءة؟ (يساعدنا على التحسين)", "+ أضف تعليقًا", "تعليق (اختياري)", "إرسال"),
}


def build_feedback_html(like_id, lang, entity_type="article"):
    fb_title, fb_comment_lbl, fb_placeholder, fb_send = FEEDBACK_UI_LOC.get(
        lang, ("How does it read?", "+ add a comment", "comment (optional)", "send"))
    fb_chips = "".join(f'<span class="fb-chip" data-opt="{k}">{safe(loc.get(lang, loc["en"]))}</span>' for k, loc in FEEDBACK_CHIPS_LOC)
    return (f'<div class="feedback" id="feedback" data-article-id="{like_id}" data-entity-type="{entity_type}">'
            f'<div class="fb-title">{safe(fb_title)}</div>'
            f'<div class="fb-chips">{fb_chips}</div>'
            f'<button type="button" class="fb-comment-toggle">{safe(fb_comment_lbl)}</button>'
            f'<textarea class="fb-comment" rows="2" placeholder="{attr_safe(fb_placeholder)}" style="display:none"></textarea>'
            f'<div class="fb-row"><button class="fb-send">{safe(fb_send)}</button><span class="fb-status"></span></div>'
            f'</div>')


ACTIONS_LOC = {
    "ru": "избранное", "en": "favorite", "zh": "收藏", "fr": "favori", "ar": "مفضلة",
}


def related_row(label, links):
    """Единый плоский список «Связанные X» — без плашек, мелким шрифтом, через « · ».
    links — список готовых строк <a href=...>Name</a>; пусто → пустая строка (блок не рисуется)."""
    if not links:
        return ""
    return f'<div class="related-tags"><strong>{safe(label)}:</strong> {" · ".join(links)}</div>'


def mini_graph_filters_html(lang):
    """Чекбоксы типов узлов для мини-графа на странице тега/закона/учёного — тот же набор
    типов (тег/закон/учёный), что и на большом графе-эксплорере, все включены по умолчанию.
    Метки берём из GRAPH_LABELS (определён ниже в файле — ок, резолвится при вызове, не при импорте)."""
    loc = GRAPH_LABELS.get(lang, GRAPH_LABELS["en"])
    return (
        f'<label><input type="checkbox" class="mg-kind" value="tag" checked> <span style="color:#7F77DD">●</span> {safe(loc["tags"])}</label>'
        f'<label><input type="checkbox" class="mg-kind" value="law" checked> <span style="color:#C0392B">●</span> {safe(loc["laws"])}</label>'
        f'<label><input type="checkbox" class="mg-kind" value="sci" checked> <span style="color:#2e7d32">●</span> {safe(loc["scientists"])}</label>'
    )


def build_og_meta(title, description, url, image_url=""):
    """og:/twitter: + meta description — общий блок для тег/закон/учёный страниц
    (у статьи свой набор в шаблоне — там ещё JSON-LD и hreflang)."""
    title, description = attr_safe(title), attr_safe(description)
    img_html = (f'<meta property="og:image" content="{image_url}">\n    '
                f'<meta name="twitter:card" content="summary_large_image">') if image_url else \
               '<meta name="twitter:card" content="summary">'
    return (f'<meta name="description" content="{description}">\n    '
            f'<meta property="og:title" content="{title}">\n    '
            f'<meta property="og:description" content="{description}">\n    '
            f'<meta property="og:url" content="{attr_safe(url)}">\n    '
            f'<meta property="og:type" content="website">\n    '
            f'{img_html}')


def build_actions_html(like_id, fav_id, lang, entity_type="article"):
    """Реакции 👍👎⭐ + избранное — общий блок для статей/тегов/законов/учёных (без «поделиться»,
    оно у статей особое из-за clickbait-заголовка и своей ссылки)."""
    fav_label = ACTIONS_LOC.get(lang, ACTIONS_LOC["en"])
    return (f'<div class="actions" data-article-id="{like_id}" data-entity-type="{entity_type}">'
            f'<div class="reactions">'
            f'<button class="react-btn" data-react="like" title="Нравится">👍 <span class="rc">…</span></button>'
            f'<button class="react-btn" data-react="dislike" title="Не нравится">👎 <span class="rc">…</span></button>'
            f'<button class="react-btn" data-react="superlike" title="Супер!">⭐ <span class="rc">…</span></button>'
            f'</div>'
            f'<button class="fav-btn" data-fav="{attr_safe(fav_id)}" title="{attr_safe(fav_label)}">'
            f'<span class="fav-ic">☆</span> {safe(fav_label)}</button>'
            f'</div>')


def gen_article_html(scipop, article, date_str, images, lang, version, captions=None, abstract=None):
    tpl = load_template("article")
    if not tpl.template: return "<html><body>Template not found</body></html>"
    abstract_text = abstract_for(abstract, lang, version)
    abstract_html = ""
    if abstract_text:  # аннотация из авторского абстракта — постоянно на виду, не по клику
        abstract_html = (f'<div class="abstract-lead"><div class="abstract-label">'
                         f'{safe(ABSTRACT_LABEL.get(lang, ABSTRACT_LABEL["en"]))}</div>'
                         f'<p>{safe(abstract_text)}</p></div>')

    like_id = f"{article['id']}_{lang}_{version}"
    feedback_html = build_feedback_html(like_id, lang, "article")

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
    loc["min"] = {"ru": "мин", "en": "min", "zh": "分钟", "fr": "min", "ar": "دقيقة"}.get(lang, "min")
    loc["related_articles"] = {"ru": "Похожие статьи", "en": "Related articles", "zh": "相关文章",
                               "fr": "Articles similaires", "ar": "مقالات ذات صلة"}.get(lang, "Related articles")
    loc["feedback_nav"] = {"ru": "Отклик", "en": "Feedback", "zh": "反馈",
                            "fr": "Retour", "ar": "التعليقات"}.get(lang, "Feedback")

    tags = [t for t in [scipop.get("main_tag", "")] + scipop.get("extra_tags", []) if t]
    authors = article.get("authors", [])
    authors_html = ", ".join(
        (f'<a href="/{LANG_DIR}/{DEFAULT_LANG}/authors/{attr_safe(author_slug(a))}.html" class="text-author-link" data-author="{attr_safe(a)}">{safe(a)}</a>'
         if any(c.isalpha() for c in a) else safe(a))  # мусорное "имя" (парсинг-артефакт без букв) — без ссылки, страницы для него нет
        for a in authors
    )
    scientists = scipop.get("scientists", [])

    # Пункты левого меню-навигатора, актуальные на ЛЮБОМ режиме (не только advanced) —
    # разделы статьи (context/methods/...) добавляются ниже отдельно, только когда они есть.
    nav_extra_items = [f'<li><a href="#feedback">{loc["feedback_nav"]}</a></li>',
                        f'<li><a href="#related">{loc["related_articles"]}</a></li>']

    if version in SIMPLE_LIKE:
        if scipop.get("text"):
            paragraphs = [p.strip() for p in re.split(r'\n\s*\n', scipop["text"]) if p.strip()]
            text_html = "".join(_render_paragraph(p, lang) for p in paragraphs)
        else:
            parts = [scipop.get(k, "") for k in ("context", "metaphor", "future")]
            text_html = "".join(f"<p>{parse_markers(p, lang)}</p>" for p in parts if p)
        key_numbers_html = ""
        nav_html = '<nav class="article-nav" id="section-nav"><ul>' + "".join(nav_extra_items) + '</ul></nav>'
        formulas_html = render_formulas(scipop.get("formulas", []))
        fun_html = trivia_html(scipop.get("fun_fact", ""), scipop.get("scifi", ""))
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
        nav_html += '<li class="article-nav-sep"></li>' + "".join(nav_extra_items) + '</ul></nav>'

        formulas_html = render_formulas(scipop.get("formulas", []))
        kn = scipop.get("key_numbers", {})
        key_numbers_html = ""
        if kn:
            key_numbers_html = f'<div class="key-numbers"><h3>{safe(loc["key_numbers"])}</h3><ul>' + \
                               "".join(f"<li><strong>{k}:</strong> {v}</li>" for k, v in kn.items()) + '</ul></div>'
        fun_html = trivia_html(scipop.get("fun_fact", ""), scipop.get("scifi", ""))

    if scipop.get("express_locked"):
        # Заглушка ("полная версия готовится") иначе не говорит, что вообще-то часть уровней
        # уже готова — ссылка на реально существующий (не текущий) уровень строится на лету при
        # рендере из article["express_tiers"], не при генерации (общая для всех статей заглушка).
        avail = [v for v in ("popular", "simple", "mini") if v in (article.get("express_tiers") or [])]
        if avail:
            target = avail[0]
            tier_name = (MINI_VERSION_LABEL.get(lang, MINI_VERSION_LABEL["en"]) if target == "mini"
                         else version_label(target, lang))
            target_url = f'/{LANG_DIR}/{lang}/archive/{date_str}/{article["id"]}/{VERSION_FILES[target]}'
            hint_tpl = EXPRESS_LOCKED_HINT.get(lang, EXPRESS_LOCKED_HINT["en"])
            text_html += f'<p>{hint_tpl.format(tier=safe(tier_name), url=target_url)}</p>'

    scientists_html = ""
    if scientists:
        scientists_html = f'<div class="scientists-section"><strong>{safe(loc["scientists"])}</strong> ' + \
                          ', '.join(scientist_link_or_text(s, lang) for s in scientists) + '</div>'

    mosaic_html = gen_mosaic(images, article["id"], date_str, captions)
    ai_jpg = Path(LANG_DIR) / DEFAULT_LANG / "archive" / date_str / article["id"] / "ai.jpg"
    if ai_jpg.exists():
        ai_url = f'/{LANG_DIR}/{DEFAULT_LANG}/archive/{date_str}/{article["id"]}/ai.jpg'
        ai_cover_html = f'<div class="ai-cover"><a href="{ai_url}" class="mosaic-open"><img src="{ai_url}" alt=""></a></div>'
    else:
        ai_cover_html = ""
    tags_side_html = gen_tags_side(tags, lang)
    if tags_side_html:
        tags_lbl = SIDE_TAGS_LABEL.get(lang, SIDE_TAGS_LABEL["en"])
        tags_side_html = f'<div class="side-tags-label">{safe(tags_lbl)}</div>' + tags_side_html
    # Законы статьи (через её теги, закон↔тег) — в правый сайдбар столбиком под тегами
    laws_loc = load_laws_loc(lang)
    tagset = set(tags)
    side_laws = []
    for lid, ld in laws_loc.items():
        if tagset & set(ld.get("tags", [])):
            side_laws.append((lid, ld.get("name", lid)))
        if len(side_laws) >= 6:
            break
    if side_laws:
        lbl = SIDE_LAWS_LABEL.get(lang, SIDE_LAWS_LABEL["en"])
        tags_side_html += (f'<div class="side-laws-label">{safe(lbl)}</div>' + "".join(
            f'<a href="/{LANG_DIR}/{lang}/laws/{attr_safe(lid)}.html" class="side-law" '
            f'data-law="{attr_safe(lid)}">{safe(name)}</a>' for lid, name in side_laws))

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
    jsonld_html = build_jsonld(scipop, article, date_str, lang, canonical_url, abstract_for(abstract, lang, "advanced"))

    return tpl.substitute(
        lang=lang, site_name=SITE_NAME, site_url=SITE_URL, goatcounter=GOATCOUNTER,
        authors_lang=DEFAULT_LANG, asset_ver=asset_ver(),
        clickbait=safe(scipop.get("title", article["title"])),
        clickbait_escaped=safe(scipop.get("title", "").replace("'", "\\'")),
        refine_badge='<span class="refine-badge" title="Отшлифовано редактором">✦</span>' if article.get("refined") else "",
        express_badge='<span class="express-badge" title="Экспресс-версия: по аннотации автора, без разбора полного текста статьи">⚡ экспресс</span>' if article.get("express") else "",
        original_title=safe(article["title"]),
        oneliner=safe(scipop.get("oneliner", "")),
        oneliner_short=safe(scipop.get("oneliner", "")[:160]),
        oneliner_og=safe(scipop.get("oneliner", "")[:200]),
        description=safe(scipop.get("description", scipop.get("oneliner", ""))[:300]),
        id=article["id"], date=date_str,
        like_id=like_id,
        version_toggle_html=version_toggle_html,
        authors_full=authors_html,
        search_placeholder=safe(loc.get("search", "")),
        search_hint=safe(loc.get("hint", "# tag · @ author · ! scientist")),
        author_verify_label=safe(loc.get("author_verify_label", "I am the author — verify & edit")),
        author_verify_body=safe(loc.get("author_verify_body", "")),
        share_label=safe(loc.get("share", "Share")),
        next_label=safe(loc.get("next", "Next article")),
        next_arrow="←" if lang in RTL_LANGS else "→",
        express_locked_js="true" if scipop.get("express_locked") else "false",
        license_label=safe(loc.get("license", "Original")),
        license_url=lic, license_name=lic_name,
        canonical_url=canonical_url, hreflang_links=hreflang_links,
        tags_side_html=tags_side_html, mosaic_html=mosaic_html, ai_cover_html=ai_cover_html,
        abstract_html=abstract_html,
        feedback_html=feedback_html,
        nav_html=nav_html, text_html=text_html,
        formulas_html=formulas_html, key_numbers_html=key_numbers_html,
        scientists_html=scientists_html,
        fun_fact_html=fun_html,
        reading_html=reading_html, jsonld_html=jsonld_html,
        related_label=safe(loc.get("related_articles", "Related articles")),
        categories_html=categories_html,
    )


# ── Data.json ──
def save_data_json(versions_ru, article, date_str, folder, translations=None, captions=None, abstract=None, refined=False):
    """versions_ru: {version: scipop_ru}; translations: {version: {lang: scipop}};
    abstract: {lang: текст} — «Аннотация» из авторского arXiv-abstract (версионно-независимо).
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
        "threads": (versions_ru.get("popular", {}).get("threads", "") or "")[:480],
        "abstract": abstract or {},
        "thumbs": article.get("thumbs", 0),
        "refined": refined,
        "express": article.get("express", False),
        "express_tiers": article.get("express_tiers", []),
    }
    has_captions = any(captions.values()) if isinstance(captions, dict) else bool(captions)
    if has_captions:
        payload["captions"] = captions
    for v in VERSIONS:
        vdata = {DEFAULT_LANG: versions_ru.get(v, {})}
        vdata.update(translations.get(v, {}))
        payload[v] = vdata
    (folder / "data.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Indexes ──
_MARKER_RE = re.compile(r'\[(?:tag:[^\]]+|/tag|scientist:[^\]]+|/scientist|callout|/callout)\]')


def strip_markers(s):
    """Убирает разметку [tag:..]/[scientist:..]/[callout] для карточек/индекса, оставляя внутренний текст."""
    return _MARKER_RE.sub('', s or '')


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
        "title": scipop.get("title", article["title"]),
        "oneliner": strip_markers(scipop.get("oneliner", ""))[:300],
        "description": strip_markers(scipop.get("description", ""))[:300],
        "abstract": strip_markers(abstract)[:1500],
        "threads": strip_markers(scipop.get("threads", ""))[:480],
        "thumbs": article.get("thumbs", 0),
        "authors": article.get("authors", [])[:50], "date": date_str,  # до 50 — лента показывает ≤20, >20 разворачивает
        "tags": [scipop.get("main_tag", "")] + scipop.get("extra_tags", []),
        "scientists": scipop.get("scientists", []), "url": url,
        "reading": reading_minutes(scipop),
        "categories": article.get("categories", []),
        "primary_category": article.get("primary_category", ""),
        "express": article.get("express", False),
    })
    ip.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")


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
        lang=lang, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG, asset_ver=asset_ver(),
        search_placeholder=safe(loc["search"]), search_hint=safe(loc["hint"]),
        loading_text=safe(loc["loading"]), footer_text=safe(loc["footer"]),
        intro_html=loc["intro"], calendar_title=safe(calendar_title), about_title=safe(about_title),
        version_toggle_html=version_toggle_spans(lang, "popular", include_mini=True)
    )
    base = Path(LANG_DIR) / lang
    (base / "index.html").write_text(html, encoding="utf-8")
    # Вкладка «Избранное» — тот же шаблон/лента; search.js показывает favorites по URL (клиент, localStorage).
    (base / "favorites.html").write_text(html, encoding="utf-8")


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
        lang=lang, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG, asset_ver=asset_ver(),
        version_toggle_html=version_toggle_spans(lang, "popular", include_mini=True),
        title=safe(loc["title"]), body=safe(loc["body"]), footer_text=safe(loc["footer"])
    ), encoding="utf-8")


def generate_tags_cloud(lang):
    tpl = load_template("tags-cloud")
    if not tpl.template: return
    tags_loc = load_tags_loc(lang)
    idx_path = Path(LANG_DIR) / lang / "articles-index.json"
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else []

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

    (Path(LANG_DIR) / lang / "tags" / "index.html").write_text(tpl.substitute(
        lang=lang, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG, asset_ver=asset_ver(),
        version_toggle_html=version_toggle_spans(lang, "popular", include_mini=True),
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

    related_html = " · ".join(
        f'<a href="/{LANG_DIR}/{lang}/tags/{rt}.html" data-tag="{attr_safe(rt)}">{tags_loc.get(rt, {}).get("name", rt)}</a>'
        for rt in tag_graph.get("related", [])[:8]
    )
    formulas_html = render_formulas(tag_data.get("formulas", []))
    loc = {
        "en": {"related": "Related tags", "history": "History", "how": "How it works", "problems": "Open problems & fun facts",
               "search": "Search...", "hint": "# tag · @ author · ! scientist", "footer": "science made simple",
               "scientists": "Scientists:", "no_articles": "No articles yet", "practical": "In practice"},
        "ar": {"related": "وسوم ذات صلة", "history": "التاريخ", "how": "كيف يعمل",
               "problems": "مسائل مفتوحة وحقائق طريفة", "search": "بحث...",
               "hint": "# وسم · @ مؤلف · ! عالم", "footer": "العلم ببساطة",
               "scientists": "العلماء:", "no_articles": "لا مقالات بعد", "practical": "في الواقع"},
        "ru": {"related": "Связанные теги", "history": "История", "how": "Как работает",
               "problems": "Открытые проблемы и интересные факты", "search": "Поиск...",
               "hint": "# тег · @ автор · ! учёный", "footer": "наука простыми словами",
               "scientists": "Учёные:", "no_articles": "Пока нет статей", "practical": "На практике"},
        "zh": {"related": "相关标签", "history": "历史", "how": "工作原理", "problems": "未解决的问题与趣味知识",
               "search": "搜索...", "hint": "# 标签 · @ 作者 · ! 科学家", "footer": "让科学变简单",
               "scientists": "科学家：", "no_articles": "暂无文章", "practical": "实际应用"},
        "fr": {"related": "Tags associés", "history": "Histoire", "how": "Fonctionnement",
               "problems": "Problèmes ouverts et anecdotes", "search": "Rechercher...",
               "hint": "# tag · @ auteur · ! scientifique", "footer": "la science simplifiée",
               "scientists": "Scientifiques :", "no_articles": "Pas encore d'articles", "practical": "En pratique"}
    }.get(lang, {"related": "Related", "history": "History", "how": "How it works", "problems": "Open problems & fun facts",
                 "search": "Search...", "hint": "# tag · @ author · ! scientist", "footer": "",
                 "scientists": "Scientists:", "no_articles": "No articles yet", "practical": "In practice"})

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

    scientists_link_list = [scientist_link_or_text(s, lang) for s in tag_data.get("scientists", [])]
    scientists_section_html = related_row(loc["scientists"].rstrip(":"), scientists_link_list)

    mini_html = f'<p class="mini-desc">{safe(tag_data["mini"])}</p>' if tag_data.get("mini") else ""
    if tag_data.get("practical_application"):
        mini_html += f'<div class="practical-app"><strong>{safe(loc["practical"])}:</strong> {safe(tag_data["practical_application"])}</div>'

    tag_img_url = entity_image_url("tags", tag_id)
    ai_cover_html = f'<div class="ai-cover"><img src="{tag_img_url}" alt=""></div>' if tag_img_url else ""

    # id НЕ переименовываем в tag-version-toggle: search.js слушает именно #version-toggle,
    # чтобы синхронно перерисовать список статей внизу при смене версии (был баг — текст тега
    # переключался, а список статей оставался на старой версии).
    tag_version_toggle = version_toggle_spans(lang, "popular", include_mini=True)

    desc_pop = tag_data.get("description_popular") or tag_data.get("description_simple") or tag_data.get("description", "")
    desc_simple = tag_data.get("description_simple") or tag_data.get("description", "")
    hist_simple = tag_data.get("history_simple") or tag_data.get("history", "")
    how_simple = tag_data.get("how_it_works_simple") or tag_data.get("how_it_works", "")
    raw = tag_data.get("raw") or {}
    raw_pop = raw.get("description_popular") or raw.get("description_simple") or raw.get("description", "")
    raw_simple = raw.get("description_simple") or raw.get("description", "")
    raw_adv = raw.get("description", "")
    tag_like_id = f"{tag_id}_{lang}_page"
    actions_html = build_actions_html(tag_like_id, tag_id, lang, "tag")
    feedback_html = build_feedback_html(tag_like_id, lang, "tag")
    og_meta_html = build_og_meta(
        f'#{tag_data.get("name", tag_id)} — bridge42worlds', desc_pop,
        f"{SITE_URL}/{LANG_DIR}/{lang}/tags/{tag_id}.html", tag_img_url and f"{SITE_URL}{tag_img_url}")

    (Path(LANG_DIR) / lang / "tags" / f"{tag_id}.html").write_text(tpl.substitute(
        lang=lang, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG, asset_ver=asset_ver(),
        og_meta_html=og_meta_html,
        tag_id=attr_safe(tag_id),
        tag_name=safe(tag_data.get("name", tag_id)), article_count=tag_graph.get("article_count", 0),
        ai_cover_html=ai_cover_html,
        actions_html=actions_html, feedback_html=feedback_html,
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
        search_hint=safe(loc["hint"]), graph_mini_label=safe(MINI_LABEL.get(lang, MINI_LABEL["en"])),
        mini_graph_filters_html=mini_graph_filters_html(lang),
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
           "search": "Найти закон...", "tags": "Связанные понятия", "related_laws": "Связанные законы", "articles": "Статьи по теме", "scientists": "Открыли:", "practical": "На практике"},
    "en": {"title": "Laws & Principles", "subtitle": "Fundamental laws of science. The formula is just a representation; the idea is in the text.",
           "history": "Discovery", "how": "How it works", "problems": "Caveats", "laws": "Laws:", "footer": "science made simple",
           "search": "Find a law...", "tags": "Related concepts", "related_laws": "Related laws", "articles": "Related articles", "scientists": "Discovered by:", "practical": "In practice"},
    "zh": {"title": "定律与原理", "subtitle": "科学的基本定律。公式只是表现形式，本质在文字中。",
           "history": "发现历史", "how": "工作原理", "problems": "注意事项", "laws": "定律：", "footer": "让科学变简单",
           "search": "查找定律...", "tags": "相关概念", "related_laws": "相关定律", "articles": "相关文章", "scientists": "发现者：", "practical": "实际应用"},
    "fr": {"title": "Lois et principes", "subtitle": "Lois fondamentales de la science. La formule n'est qu'une représentation.",
           "history": "Découverte", "how": "Fonctionnement", "problems": "Nuances", "laws": "Lois :", "footer": "la science simplifiée",
           "search": "Trouver une loi...", "tags": "Concepts liés", "related_laws": "Lois liées", "articles": "Articles liés", "scientists": "Découverte par :", "practical": "En pratique"},
    "ar": {"title": "القوانين والمبادئ", "subtitle": "القوانين الأساسية للعلم. الصيغة مجرد تمثيل؛ الفكرة في النص.",
           "history": "تاريخ الاكتشاف", "how": "كيف يعمل", "problems": "ملاحظات", "laws": "القوانين:", "footer": "العلم ببساطة",
           "search": "ابحث عن قانون...", "tags": "مفاهيم ذات صلة", "related_laws": "قوانين ذات صلة", "articles": "مقالات ذات صلة", "scientists": "اكتشفه:", "practical": "في الواقع"},
}

LAW_TYPE_COLORS = {"закон": "#C0392B", "принцип": "#8E44AD", "теорема": "#2471A3",
                   "эффект": "#B9770E", "уравнение": "#148F77", "теория": "#5D6D7E"}

# Раздел науки тега (для группировки облака списком) — фиксированный английский slug (НЕ переводится
# через LLM, чтобы группировка/цвета не разъезжались по языкам); подписи — тут, локализуются вручную.
TAG_DOMAIN_LABELS = {
    "cosmology":              {"ru": "Космология", "en": "Cosmology"},
    "astrophysics":           {"ru": "Астрофизика", "en": "Astrophysics"},
    "particles_nuclear":      {"ru": "Физика частиц и ядерная физика", "en": "Particle & Nuclear Physics"},
    "quantum":                {"ru": "Квантовая механика", "en": "Quantum Mechanics"},
    "relativity_gravity":     {"ru": "Относительность и гравитация", "en": "Relativity & Gravity"},
    "thermo_stat":            {"ru": "Термодинамика и статфизика", "en": "Thermodynamics & Stat. Physics"},
    "electromagnetism_optics": {"ru": "Электромагнетизм и оптика", "en": "Electromagnetism & Optics"},
    "chemistry_materials":    {"ru": "Химия и материалы", "en": "Chemistry & Materials"},
    "mathematics":            {"ru": "Математика", "en": "Mathematics"},
    "instruments_methods":    {"ru": "Инструменты и методы", "en": "Instruments & Methods"},
}
TAG_DOMAIN_FALLBACK = {"ru": "Другое", "en": "Other"}


def tag_domain_label(domain, lang):
    entry = TAG_DOMAIN_LABELS.get(domain)
    if not entry:
        return TAG_DOMAIN_FALLBACK.get(lang, TAG_DOMAIN_FALLBACK["en"])
    return entry.get(lang, entry["en"])

MINI_LABEL = {"ru": "Связи в графе знаний", "en": "Links in the knowledge graph",
              "zh": "知识图谱中的关联", "fr": "Liens dans le graphe des savoirs", "ar": "الروابط في شبكة المعرفة"}

SIDE_LAWS_LABEL = {"ru": "Законы", "en": "Laws", "zh": "定律", "fr": "Lois", "ar": "قوانين"}
SIDE_TAGS_LABEL = {"ru": "Теги", "en": "Tags", "zh": "标签", "fr": "Tags", "ar": "الوسوم"}

ABSTRACT_LABEL = {"ru": "Аннотация", "en": "Abstract", "zh": "摘要", "fr": "Résumé", "ar": "الملخّص"}

# ── Экспресс-режим: заглушка для tier'ов, которые не входят в express.tiers ──
# Клик на такую вкладку — сигнал интереса (см. logExpressInterest в likes.js), помогает
# приоритизировать, какие статьи апгрейдить до полной версии (run.py regen <id>) в первую очередь.
EXPRESS_LOCKED = {
    "ru": {"oneliner": "Полная версия готовится",
           "text": "Сейчас есть только облегчённая экспресс-версия этой статьи. Добавьте её в "
                    "избранное — если её ждут, мы подготовим полную версию в первую очередь."},
    "en": {"oneliner": "Full version coming soon",
           "text": "Only a lightweight express version of this article exists right now. Add it "
                    "to favorites — articles people are waiting for get the full treatment first."},
    "es": {"oneliner": "Versión completa próximamente",
           "text": "Por ahora solo existe una versión exprés ligera de este artículo. Añádelo a "
                    "favoritos — los artículos más esperados reciben antes el tratamiento completo."},
    "zh": {"oneliner": "完整版本准备中",
           "text": "目前只有这篇文章的精简速览版。收藏它——大家关注的文章会优先制作完整版本。"},
    "fr": {"oneliner": "Version complète à venir",
           "text": "Seule une version express allégée de cet article existe pour l'instant. "
                    "Ajoutez-le aux favoris — les articles attendus sont complétés en priorité."},
    "ar": {"oneliner": "النسخة الكاملة قيد الإعداد",
           "text": "يتوفر حاليًا فقط نسخة سريعة مبسّطة من هذا المقال. أضفه إلى المفضّلة — "
                    "المقالات التي ينتظرها القراء تحصل على نسختها الكاملة أولًا."},
}

# Подсказка со ссылкой на реально доступный уровень (mini/simple/popular — какой из них
# express_tiers содержит), добавляется К тексту-заглушке EXPRESS_LOCKED при рендере (не при
# генерации — заглушка одна и та же для всех статей, ссылка/URL подставляются на лету).
EXPRESS_LOCKED_HINT = {
    "ru": 'Сейчас доступна статья в изложении «{tier}» — <a href="{url}">открыть</a>.',
    "en": 'Right now the article is available in "{tier}" mode — <a href="{url}">open it</a>.',
    "zh": '目前该文章有"{tier}"版本可看 — <a href="{url}">打开</a>。',
    "fr": 'L’article est disponible en version « {tier} » — <a href="{url}">l’ouvrir</a>.',
    "ar": 'يتوفر المقال حاليًا بمستوى «{tier}» — <a href="{url}">فتحه</a>.',
}


def express_locked_scipop(base, lang):
    """base — реальный express-результат (main_tag/extra_tags/scientists/mini сохраняем, иначе
    сломается сайдбар/индекс/mini-версия); тело текста подменяем на «скоро полная версия».
    ВАЖНО: advanced рендерится ИНАЧЕ, чем popular/simple/mini (gen_article_html: SIMPLE_LIKE
    читает поле text, advanced — секции context/methods/... маркерами) — заполняем оба пути,
    иначе на advanced-вкладке страница окажется пустой.
    title ТОЖЕ переопределяем (раньше не трогали — комментарий говорил «title... сохраняем», но
    base всегда RU-контент независимо от lang, на которую эта заглушка рендерится: на en/es
    страницах title/<h1> молча оставался русским, хотя весь остальной текст уже был на языке
    страницы) — берём тот же локализованный oneliner, что и в тексте, не настоящий заголовок."""
    loc = EXPRESS_LOCKED.get(lang, EXPRESS_LOCKED["en"])
    return {
        **base,
        "title": loc["oneliner"], "oneliner": loc["oneliner"], "description": "", "text": loc["text"],
        "fun_fact": "", "scifi": "", "formulas": [], "key_numbers": {},
        "context": loc["text"], "methods": "", "results": "", "implications": "",
        "future_development": "", "impact_on": "", "next_steps": "", "key_problems_connection": "",
        "threads": base.get("mini", "") or base.get("threads", ""),
        "express_locked": True,
    }


def laws_for_tag(tag_id, lang):
    """Ссылки на СТРАНИЦЫ законов, относящихся к тегу (секция «Законы» на странице тега)."""
    laws = load_laws_loc(lang)
    loc = LAWS_LABELS.get(lang, LAWS_LABELS["en"])
    related = [(lid, L) for lid, L in laws.items() if tag_id in (L.get("tags") or [])]
    links = [
        f'<a href="/{LANG_DIR}/{lang}/laws/{attr_safe(lid)}.html" class="law-chip" data-law="{attr_safe(lid)}">{safe(L.get("name", lid))}</a>'
        for lid, L in related[:14]]
    return related_row(loc["laws"].rstrip(":"), links)


def generate_laws_cloud(lang):
    """Облако ИМЁН законов (как теги): каждое имя — ссылка на страницу закона. + граф."""
    tpl = load_template("laws-cloud")
    if not tpl.template: return
    laws = load_laws_loc(lang)
    loc = LAWS_LABELS.get(lang, LAWS_LABELS["en"])

    # Счётчики статей по законам (через пересечение тегов)
    idx_path = Path(LANG_DIR) / lang / "articles-index.json"
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else []
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
        color = LAW_TYPE_COLORS.get(L.get("type", ""), "#888")
        cnt = law_counts.get(lid, 0)
        count_html = f'<span class="cat-chip-n">{cnt}</span>' if cnt else ""
        return (
            f'<a href="/{LANG_DIR}/{lang}/laws/{attr_safe(lid)}.html" class="tag-item law-item" data-law="{attr_safe(lid)}">'
            f'<span><span class="law-type-dot" style="background:{color}"></span>{safe(L.get("name", lid))}</span>{count_html}</a>\n'
        )

    cloud = ""
    for t in sorted(by_type.keys()):
        cloud += f'<div class="cloud-group-label">{safe(t)}</div>\n'
        cloud += "".join(law_row(lid) for lid in sorted(by_type[t], key=lambda x: laws[x].get("name", x)))
    (Path(LANG_DIR) / lang / "laws").mkdir(parents=True, exist_ok=True)
    (Path(LANG_DIR) / lang / "laws" / "index.html").write_text(tpl.substitute(
        lang=lang, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG, asset_ver=asset_ver(),
        version_toggle_html=version_toggle_spans(lang, "popular", include_mini=True),
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

    # id НЕ переименовываем (см. тот же комментарий у тегов) — иначе список статей внизу не
    # синхронизируется с переключением версии.
    toggle = version_toggle_spans(lang, "popular", include_mini=True)
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
    related_laws = [rl for rl in (L.get("related_laws") or []) if rl in laws]
    related_laws_links = [
        f'<a href="/{LANG_DIR}/{lang}/laws/{attr_safe(rl)}.html" class="law-chip" data-law="{attr_safe(rl)}">{safe(laws[rl].get("name", rl))}</a>'
        for rl in related_laws]
    related_laws_block = related_row(loc["related_laws"], related_laws_links)

    def sec(label, text):
        return f'<div class="section"><h2>{safe(label)}</h2><p>{safe(text)}</p></div>' if text else ""
    mini_html = f'<p class="mini-desc">{safe(L["mini"])}</p>' if L.get("mini") else ""
    if L.get("practical_application"):
        mini_html += f'<div class="practical-app"><strong>{safe(loc["practical"])}:</strong> {safe(L["practical_application"])}</div>'
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

    lraw = L.get("raw") or {}
    raw_pop = lraw.get("description_popular") or lraw.get("description_simple") or lraw.get("description", "")
    raw_simple = lraw.get("description_simple") or lraw.get("description", "")
    raw_adv = lraw.get("description", "")
    law_like_id = f"{law_id}_{lang}_page"
    actions_html = build_actions_html(law_like_id, law_id, lang, "law")
    feedback_html = build_feedback_html(law_like_id, lang, "law")
    desc_pop_for_og = L.get("description_popular") or L.get("description_simple") or L.get("description", "")
    og_meta_html = build_og_meta(
        f'{L.get("name", law_id)} — bridge42worlds', desc_pop_for_og,
        f"{SITE_URL}/{LANG_DIR}/{lang}/laws/{law_id}.html", law_img_url and f"{SITE_URL}{law_img_url}")

    (Path(LANG_DIR) / lang / "laws" / f"{law_id}.html").write_text(tpl.substitute(
        lang=lang, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG, asset_ver=asset_ver(),
        og_meta_html=og_meta_html,
        law_name=safe(L.get("name", law_id)), law_type=safe(L.get("type", "")),
        ai_cover_html=ai_cover_html,
        actions_html=actions_html, feedback_html=feedback_html,
        law_version_toggle=toggle,
        law_mini_html=mini_html,
        desc_popular_raw=attr_safe(raw_pop),
        desc_simple_raw=attr_safe(raw_simple),
        desc_advanced_raw=attr_safe(raw_adv),
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
        graph_mini_label=safe(MINI_LABEL.get(lang, MINI_LABEL["en"])), law_id=attr_safe(law_id),
        mini_graph_filters_html=mini_graph_filters_html(lang),
        articles_label=safe(loc["articles"]),
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


GRAPH_LABELS = {
    "ru": {"title": "Граф знаний", "subtitle": "Теги, законы и учёные и все их связи. Переключай, что показывать.",
           "nodes": "Узлы:", "edges": "Связи:", "presets": "Пресеты:",
           "tags": "теги", "laws": "законы", "scientists": "учёные", "footer": "наука простыми словами",
           "search_tag": "Найти тег…", "search_law": "Найти закон…", "search_sci": "Найти учёного…",
           "depth": "Глубина:", "clear": "Сбросить",
           "warning": "⚠ Отображение оптимизировано под большой экран, формирование графа может занять некоторое время."},
    "en": {"title": "Knowledge graph", "subtitle": "Tags, laws and scientists and all their links. Toggle what to show.",
           "nodes": "Nodes:", "edges": "Edges:", "presets": "Presets:",
           "tags": "tags", "laws": "laws", "scientists": "scientists", "footer": "science made simple",
           "search_tag": "Find a tag…", "search_law": "Find a law…", "search_sci": "Find a scientist…",
           "depth": "Depth:", "clear": "Clear",
           "warning": "⚠ Optimized for large screens — building the graph may take a moment."},
    "zh": {"title": "知识图谱", "subtitle": "标签、定律与科学家及其关联。切换显示内容。",
           "nodes": "节点：", "edges": "关联：", "presets": "预设：",
           "tags": "标签", "laws": "定律", "scientists": "科学家", "footer": "让科学变简单",
           "search_tag": "查找标签…", "search_law": "查找定律…", "search_sci": "查找科学家…",
           "depth": "深度：", "clear": "重置",
           "warning": "⚠ 界面针对大屏幕优化，图谱生成可能需要一些时间。"},
    "fr": {"title": "Graphe des savoirs", "subtitle": "Tags, lois et scientifiques et leurs liens. Choisissez l'affichage.",
           "nodes": "Nœuds :", "edges": "Liens :", "presets": "Préréglages :",
           "tags": "tags", "laws": "lois", "scientists": "scientifiques", "footer": "la science simplifiée",
           "search_tag": "Trouver un tag…", "search_law": "Trouver une loi…", "search_sci": "Trouver un scientifique…",
           "depth": "Profondeur :", "clear": "Réinitialiser",
           "warning": "⚠ Optimisé pour grand écran — la construction du graphe peut prendre un moment."},
    "ar": {"title": "شبكة المعرفة", "subtitle": "الوسوم والقوانين والعلماء وكل روابطهم. بدّل ما تريد عرضه.",
           "nodes": "العقد:", "edges": "الروابط:", "presets": "إعدادات:",
           "tags": "وسوم", "laws": "قوانين", "scientists": "علماء", "footer": "العلم ببساطة",
           "search_tag": "ابحث عن وسم…", "search_law": "ابحث عن قانون…", "search_sci": "ابحث عن عالِم…",
           "depth": "العمق:", "clear": "إعادة تعيين",
           "warning": "⚠ الواجهة محسّنة للشاشات الكبيرة، وقد يستغرق إنشاء الرسم البياني بعض الوقت."},
}


def generate_knowledge_graph_page(lang):
    """Страница единого графа знаний (теги⇄законы⇄учёные) с тумблерами типов узлов/рёбер."""
    tpl = load_template("graph-explorer")
    if not tpl.template:
        return
    loc = GRAPH_LABELS.get(lang, GRAPH_LABELS["en"])
    (Path(LANG_DIR) / lang / "graph").mkdir(parents=True, exist_ok=True)
    (Path(LANG_DIR) / lang / "graph" / "index.html").write_text(tpl.substitute(
        lang=lang, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG, asset_ver=asset_ver(),
        version_toggle_html=version_toggle_spans(lang, "popular", include_mini=True),
        graph_title=safe(loc["title"]), graph_subtitle=safe(loc["subtitle"]),
        nodes_label=safe(loc["nodes"]), edges_label=safe(loc["edges"]), presets_label=safe(loc["presets"]),
        tags_label=safe(loc["tags"]), laws_label=safe(loc["laws"]), scientists_label=safe(loc["scientists"]),
        search_tag_placeholder=safe(loc["search_tag"]), search_law_placeholder=safe(loc["search_law"]),
        search_sci_placeholder=safe(loc["search_sci"]), depth_label=safe(loc["depth"]), clear_label=safe(loc["clear"]),
        footer_text=safe(loc["footer"]), graph_warning=safe(loc["warning"])
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
    idx_path = Path(LANG_DIR) / lang / "articles-index.json"
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else []
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
        lang=lang, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG, asset_ver=asset_ver(),
        version_toggle_html=version_toggle_spans(lang, "popular", include_mini=True),
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
    related_tags_links = [
        f'<a href="/{LANG_DIR}/{lang}/tags/{t}.html" data-tag="{attr_safe(t)}">{tags_loc.get(t, {}).get("name", t)}</a>'
        for t in data.get("related_tags", [])[:8]
    ]
    lp = Path(f"lang/{lang}/data/laws.json")
    if not lp.exists(): lp = Path(f"lang/{DEFAULT_LANG}/data/laws.json")
    laws_data = json.loads(lp.read_text(encoding="utf-8")) if lp.exists() else {}
    related_laws_links = [
        f'<a href="/{LANG_DIR}/{lang}/laws/{attr_safe(lid)}.html" class="law-chip" data-law="{attr_safe(lid)}">{safe(ld.get("name", lid))}</a>'
        for lid, ld in laws_data.items() if sid in ld.get("scientists", [])
    ]
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
        "en": {"related": "Related tags", "related_laws": "Related laws", "related_scientists": "Related scientists", "discoveries": "Key discoveries", "bio": "Biography", "quote": "Quote",
               "search": "Search...", "hint": "! scientist · # tag · @ author", "footer": "science made simple",
               "no_articles": "No articles yet"},
        "ar": {"related": "وسوم ذات صلة", "related_laws": "قوانين ذات صلة", "related_scientists": "علماء ذوو صلة", "discoveries": "اكتشافات رئيسية", "bio": "سيرة", "quote": "اقتباس",
               "search": "بحث...", "hint": "! عالم · # وسم · @ مؤلف", "footer": "العلم ببساطة",
               "no_articles": "لا مقالات بعد"},
        "ru": {"related": "Связанные теги", "related_laws": "Связанные законы", "related_scientists": "Связанные учёные", "discoveries": "Ключевые открытия", "bio": "Биография", "quote": "Цитата",
               "search": "Поиск...", "hint": "! учёный · # тег · @ автор", "footer": "наука простыми словами",
               "no_articles": "Пока нет статей"},
        "zh": {"related": "相关标签", "related_laws": "相关定律", "related_scientists": "相关科学家", "discoveries": "重要发现", "bio": "生平", "quote": "名言",
               "search": "搜索...", "hint": "! 科学家 · # 标签 · @ 作者", "footer": "让科学变简单",
               "no_articles": "暂无文章"},
        "fr": {"related": "Tags associés", "related_laws": "Lois associées", "related_scientists": "Scientifiques associés", "discoveries": "Découvertes clés", "bio": "Biographie", "quote": "Citation",
               "search": "Rechercher...", "hint": "! scientifique · # tag · @ auteur", "footer": "la science simplifiée",
               "no_articles": "Pas encore d'articles"}
    }.get(lang, {"related": "Related", "related_laws": "Related laws", "related_scientists": "Related scientists", "discoveries": "Discoveries", "bio": "Biography", "quote": "Quote",
                 "search": "Search...", "hint": "! scientist · # tag · @ author", "footer": "",
                 "no_articles": "No articles yet"})

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

    sci_like_id = f"{author_slug(sid)}_{lang}_page"
    actions_html = build_actions_html(sci_like_id, sid, lang, "scientist")
    feedback_html = build_feedback_html(sci_like_id, lang, "scientist")
    og_meta_html = build_og_meta(
        f'{sid} — bridge42worlds', data.get("description", ""),
        f"{SITE_URL}/{LANG_DIR}/{lang}/scientists/{author_slug(sid)}.html")

    (Path(LANG_DIR) / lang / "scientists" / f"{author_slug(sid)}.html").write_text(tpl.substitute(
        lang=lang, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG, asset_ver=asset_ver(),
        og_meta_html=og_meta_html,
        scientist_id=attr_safe(sid),
        version_toggle_html=version_toggle_spans(lang, "popular", include_mini=True),
        actions_html=actions_html, feedback_html=feedback_html,
        scientist_name=safe(sid), lifespan=data.get("lifespan", ""),
        fields=", ".join(as_list(data.get("fields", []))),
        scientist_description=safe(data.get("description", "")),
        scientist_biography=safe(data.get("biography", "")),
        scientist_discoveries="".join(f"<li>{safe(d)}</li>" for d in as_list(data.get("key_discoveries", []))),
        scientist_quote=safe(data.get("quote", "")), scientist_fun_fact=safe(data.get("fun_fact", "")),
        discoveries_label=safe(loc["discoveries"]), bio_label=safe(loc["bio"]),
        quote_label=safe(loc["quote"]),
        related_tags_block=related_tags_block, related_laws_block=related_laws_block,
        related_scientists_html=related_scientists_html,
        search_placeholder=safe(loc["search"]),
        search_hint=safe(loc["hint"]), graph_mini_label=safe(MINI_LABEL.get(lang, MINI_LABEL["en"])),
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
               "articles": "articles", "coauthors_word": "co-authors", "tags": "Tags", "laws": "Laws",
               "default_hint": 'Showing authors starting with "{letter}" — search above covers everyone.'},
        "ru": {"title": "Авторы", "subtitle": "Исследователи, публикующиеся в arXiv.", "find": "Найти авторов...",
               "search": "Поиск статей...", "hint": "@ автор · # тег · ! учёный",
               "coauthors": "Соавторы", "no_articles": "Пока нет статей", "footer": "наука простыми словами",
               "articles": "статей", "coauthors_word": "соавторов", "tags": "Теги", "laws": "Законы",
               "default_hint": 'Показаны авторы на «{letter}» — поиск выше ищет среди всех.'},
        "zh": {"title": "作者", "subtitle": "在 arXiv 上发表论文的研究人员。", "find": "查找作者...",
               "search": "搜索文章...", "hint": "@ 作者 · # 标签 · ! 科学家",
               "coauthors": "合著者", "no_articles": "暂无文章", "footer": "让科学变简单",
               "articles": "篇文章", "coauthors_word": "位合著者", "tags": "标签", "laws": "定律",
               "default_hint": '显示以「{letter}」开头的作者 — 上方搜索涵盖所有作者。'},
        "fr": {"title": "Auteurs", "subtitle": "Chercheurs publiant sur arXiv.", "find": "Rechercher des auteurs...",
               "search": "Rechercher des articles...", "hint": "@ auteur · # tag · ! scientifique",
               "coauthors": "Co-auteurs", "no_articles": "Pas encore d'articles", "footer": "la science simplifiée",
               "articles": "articles", "coauthors_word": "co-auteurs", "tags": "Tags", "laws": "Lois",
               "default_hint": 'Auteurs commençant par « {letter} » — la recherche ci-dessus couvre tout le monde.'}
    }.get(DEFAULT_LANG, {"title": "Authors", "subtitle": "Researchers publishing on arXiv.", "find": "Find authors...",
                          "search": "Search articles...", "hint": "@ author · # tag · ! scientist",
                          "coauthors": "Co-authors", "no_articles": "No articles yet", "footer": "science made simple",
                          "articles": "articles", "coauthors_word": "co-authors", "tags": "Tags", "laws": "Laws",
                          "default_hint": 'Showing authors starting with "{letter}" — search above covers everyone.'})
    ap = Path("data/authors-graph.json")
    graph = json.loads(ap.read_text(encoding="utf-8")) if ap.exists() else {}
    tags_loc = load_tags_loc(DEFAULT_LANG)
    laws_loc = load_laws_loc(DEFAULT_LANG)

    # id -> дата и id -> теги (из индекса языка по умолчанию) для «свежести» и графа тегов автора
    id_date = {}
    id_tags = {}
    di = Path(LANG_DIR) / DEFAULT_LANG / "articles-index.json"
    if di.exists():
        for a in json.loads(di.read_text(encoding="utf-8")):
            id_date[a["id"]] = a["date"]
            id_tags[a["id"]] = [t for t in a.get("tags", []) if t]
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
    tags_loc = load_tags_loc(DEFAULT_LANG)
    authors = sorted([{"name": n, "count": d.get("article_count", 0), "last": last_date_of(d),
                       "tags": list(dict.fromkeys(t for aid in d.get("articles", [])
                                                  for t in id_tags.get(aid, [])))}
                      for n, d in graph.items()], key=lambda x: x["name"].lower())

    # Group by first letter (A-Z)
    sections = {}
    for a in authors:
        letter = a["name"][0].upper() if a["name"] else "#"
        if letter < "A" or letter > "Z":
            letter = "#"
        sections.setdefault(letter, []).append(a)

    ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    letters_with_content = [l for l in ALPHABET if sections.get(l)]

    def gen_alphabet_nav(active_letter=None):
        parts = []
        for l in ALPHABET:
            count = len(sections.get(l, []))
            cls = " active" if active_letter == l else ""
            href = f"/{LANG_DIR}/{DEFAULT_LANG}/authors/{l.lower()}.html"
            if count:
                parts.append(f'<a href="{href}" class="alpha-link{cls}" data-letter="{l}">{l}</a>')
            else:
                parts.append(f'<span class="alpha-link alpha-empty">{l}</span>')
        if sections.get("#"):
            cls = " active" if active_letter == "#" else ""
            parts.append(f'<a href="/{LANG_DIR}/{DEFAULT_LANG}/authors/other.html" class="alpha-link{cls}" data-letter="#">#</a>')
        return "".join(parts)

    def gen_letter_section(letter, is_link=True):
        items = sections.get(letter, [])
        if not items:
            return ""
        def author_tags_html(a):
            tags = a.get("tags", [])[:6]
            base = LANG_DIR + "/" + DEFAULT_LANG
            return " ".join(
                '<span onclick="event.stopPropagation();window.location=`/{}/tags/{}.html`" class="text-tag" data-tag="{}">{}</span>'.format(
                    base, t, t,
                    safe(tags_loc.get(t, {}).get("name", t)))
                for t in tags
            )
        rows = "".join(
            '<a href="/{}/authors/{}.html" class="author-row" data-author="{}">'
            '<span class="author-name">{}</span>'
            '<span class="author-tags">{}</span>'
            '<span class="author-count">{} {}</span></a>'.format(
                LANG_DIR + "/" + DEFAULT_LANG, author_slug(a["name"]), attr_safe(a["name"]),
                safe(a["name"]), author_tags_html(a),
                a["count"], safe(loc["articles"]))
            for a in items
        )
        return f'<div class="letter-section" id="letter-{letter}"><h2 class="letter-heading">{letter}</h2><div class="author-list">{rows}</div></div>'

    # Index page — БЕЗ выбранной буквы список из тысяч авторов слишком длинный, поэтому
    # рендерим только один ярус-по-умолчанию как ориентир; поиск на странице (js/search.js)
    # всё равно ищет по ВСЕМ авторам через authors-graph.json, независимо от того, какая
    # буква отрендерена в HTML. Буква — случайная (не всегда "S", который у западных имён
    # непропорционально большой сам по себе) — так дефолтный список обычно меньше и легче.
    default_letter = random.choice(letters_with_content) if letters_with_content else None
    index_sections = gen_letter_section(default_letter) if default_letter else ""
    index_nav = gen_alphabet_nav()
    index_subtitle = loc["subtitle"] + (
        " " + loc["default_hint"].format(letter=default_letter) if default_letter else "")
    (Path(LANG_DIR) / DEFAULT_LANG / "authors" / "index.html").write_text(tpl_cloud.substitute(
        lang=DEFAULT_LANG, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG, asset_ver=asset_ver(),
        version_toggle_html=version_toggle_spans(DEFAULT_LANG, "popular", include_mini=True),
        page_title=safe(loc["title"]), authors_title=safe(loc["title"]),
        authors_subtitle=safe(index_subtitle), alphabet_nav_html=index_nav,
        search_placeholder=safe(loc["find"]), author_sections_html=index_sections,
        footer_text=safe(loc["footer"])
    ), encoding="utf-8")

    author_count_label = {"ru": "авторов", "en": "authors", "zh": "位作者", "fr": "auteurs"}.get(DEFAULT_LANG, "authors")
    # Per-letter pages
    for letter in letters_with_content:
        section_html = gen_letter_section(letter)
        letter_nav = gen_alphabet_nav(active_letter=letter)
        (Path(LANG_DIR) / DEFAULT_LANG / "authors" / f"{letter.lower()}.html").write_text(tpl_cloud.substitute(
            lang=DEFAULT_LANG, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG, asset_ver=asset_ver(),
            version_toggle_html=version_toggle_spans(DEFAULT_LANG, "popular", include_mini=True),
            page_title=safe(f"{loc['title']} — {letter}"), authors_title=loc["title"],
            authors_subtitle=safe(f"{letter} — {len(sections[letter])} {author_count_label}"),
            alphabet_nav_html=letter_nav, search_placeholder=safe(loc["find"]),
            author_sections_html=section_html, footer_text=safe(loc["footer"])
        ), encoding="utf-8")
    # "#" (имена не A-Z) — gen_alphabet_nav безусловно ссылается на other.html, если в
    # sections["#"] что-то есть, но саму страницу раньше нигде не писали (цикл выше — только
    # A-Z) — отсюда битая ссылка на every letter page.
    if sections.get("#"):
        section_html = gen_letter_section("#")
        other_nav = gen_alphabet_nav(active_letter="#")
        (Path(LANG_DIR) / DEFAULT_LANG / "authors" / "other.html").write_text(tpl_cloud.substitute(
            lang=DEFAULT_LANG, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG, asset_ver=asset_ver(),
            version_toggle_html=version_toggle_spans(DEFAULT_LANG, "popular", include_mini=True),
            page_title=safe(f"{loc['title']} — #"), authors_title=loc["title"],
            authors_subtitle=safe(f"# — {len(sections['#'])} {author_count_label}"),
            alphabet_nav_html=other_nav, search_placeholder=safe(loc["find"]),
            author_sections_html=section_html, footer_text=safe(loc["footer"])
        ), encoding="utf-8")
    # Индекс по id ЗАРАНЕЕ, один раз на язык — раньше здесь на КАЖДОГО из тысяч авторов ×
    # каждый язык заново читался и парсился весь articles-index.json с диска (O(авторы×языки×
    # статьи)) — на 10000+ авторов и растущем архиве это тянулось по 15+ минут на пустом месте.
    articles_by_lang = {}
    for lc in LANGUAGES:
        ip = Path(LANG_DIR) / lc / "articles-index.json"
        if ip.exists():
            articles_by_lang[lc] = {a["id"]: a for a in json.loads(ip.read_text(encoding="utf-8"))}

    for author_name, data in graph.items():
        slug = author_slug(author_name)
        articles_html = ""
        author_article_ids = data.get("articles", [])
        for lc in LANGUAGES:
            for aid in author_article_ids:
                a = articles_by_lang.get(lc, {}).get(aid)
                if a:
                    articles_html += f"""<div class="article-card"><div class="card-content">
                        <h3><a href="{a['url']}">{a['title']}</a></h3>
                        <div class="oneliner">{a.get('description', a.get('oneliner', ''))}</div>
                        <div class="meta">arXiv:{a['id']} · {a['date']}</div></div></div>"""
        coauthors_html = "".join(
            f'<a href="/{LANG_DIR}/{DEFAULT_LANG}/authors/{author_slug(ca)}.html" data-author="{attr_safe(ca)}">{ca}</a>'
            for ca in data.get("coauthors", [])[:15]
        )
        # теги статей автора (по объединению), для мини-графа тем автора + видимого списка
        author_tags = []
        for aid in data.get("articles", []):
            for t in id_tags.get(aid, []):
                if t not in author_tags: author_tags.append(t)
        author_tags_set = set(author_tags)
        author_tags_html = " ".join(
            f'<a href="/{LANG_DIR}/{DEFAULT_LANG}/tags/{attr_safe(t)}.html" data-tag="{attr_safe(t)}">{safe(tags_loc.get(t, {}).get("name", t))}</a>'
            for t in author_tags[:20]
        )
        # законы автора — через пересечение тегов (закон↔тег), как секция «Законы» на странице тега
        author_law_ids = [lid for lid, L in laws_loc.items() if set(L.get("tags", [])) & author_tags_set]
        author_laws_html = " ".join(
            f'<a href="/{LANG_DIR}/{DEFAULT_LANG}/laws/{attr_safe(lid)}.html" class="law-chip" data-law="{attr_safe(lid)}">{safe(laws_loc[lid].get("name", lid))}</a>'
            for lid in author_law_ids[:20]
        )
        (Path(LANG_DIR) / DEFAULT_LANG / "authors" / f"{slug}.html").write_text(tpl_page.substitute(
            lang=DEFAULT_LANG, goatcounter=GOATCOUNTER, authors_lang=DEFAULT_LANG, asset_ver=asset_ver(),
            version_toggle_html=version_toggle_spans(DEFAULT_LANG, "popular", include_mini=True),
            author_slug=attr_safe(slug),
            author_name=author_name, author_name_attr=attr_safe(author_name),
            author_tags_attr=attr_safe(",".join(author_tags)),
            graph_mini_label=safe(MINI_LABEL.get(DEFAULT_LANG, MINI_LABEL["en"])),
            article_count=len(data.get("articles", [])),
            articles_label=safe(loc["articles"]), coauthors_word=safe(loc["coauthors_word"]),
            last_seen=f'{last_label}: {last_date_of(data)}' if last_date_of(data) else '',
            coauthor_count=len(data.get("coauthors", [])), coauthors_label=safe(loc["coauthors"]),
            coauthors_html=coauthors_html, search_placeholder=safe(loc["search"]),
            search_hint=safe(loc["hint"]),
            tags_label=safe(loc["tags"]), author_tags_html=author_tags_html or "—",
            laws_label=safe(loc["laws"]), author_laws_html=author_laws_html or "—",
            articles_list_html=articles_html or f'<p>{safe(loc["no_articles"])}</p>',
            footer_text=safe(loc["footer"])
        ), encoding="utf-8")
    print(f"  👥 Authors updated ({len(graph)} authors)")


# ── Main ──


def generate_archive_page(lang):
    """Страница /archive: та же лента+календарь-фильтр, что на главной (js/search.js
    showLatest()/initCalendar()) — новые статьи сверху, подгрузка по скроллу батчами.
    Раньше рендерили ВСЕ статьи по всем дням разом одной гигантской HTML-страницей (якорные
    ссылки календаря вели на #{date} внутри неё) — при росте архива до тысяч статей это
    и тяжёлая страница, и всё видно сразу без фильтрации. Теперь — тот же ленивый JS-фид."""
    loc = {"ru": {"title": "Архив", "footer": "наука простыми словами"},
           "en": {"title": "Archive", "footer": "science made simple"},
           "zh": {"title": "存档", "footer": "让科学变简单"},
           "fr": {"title": "Archives", "footer": "la science simplifiée"},
           "ar": {"title": "الأرشيف", "footer": "العلم ببساطة"}}.get(lang,
           {"title": "Archive", "footer": "science made simple"})
    html = f'''<!DOCTYPE html><html lang="{lang}"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{loc["title"]} — bridge42worlds</title>
<link rel="stylesheet" href="/css/style.css?v={asset_ver()}">
<script data-goatcounter="https://{GOATCOUNTER}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script></head><body>
<div class="top-bar"><a href="/{LANG_DIR}/{lang}/index.html" class="logo">bridge42worlds</a>
<div class="header-right"><div class="nav-links">
<a href="/{LANG_DIR}/{lang}/index.html">main</a><a href="/{LANG_DIR}/{lang}/tags/">tags</a>
<a href="/{LANG_DIR}/{lang}/laws/">laws</a><a href="/{LANG_DIR}/{lang}/scientists/">scientists</a>
<a href="/{LANG_DIR}/{DEFAULT_LANG}/authors/">authors</a><a href="/{LANG_DIR}/{lang}/graph/">graph</a>
<a href="/{LANG_DIR}/{DEFAULT_LANG}/theory/">theory</a>
<a href="/{LANG_DIR}/{lang}/favorites.html" title="Избранное">★</a>
<a href="/{LANG_DIR}/{lang}/about.html">about</a>
</div></div></div>
<div class="langs-row">
    <div class="langs" id="langs-bar"></div>
    <div class="cal-bar">
        <button type="button" id="calendar-btn" class="cal-btn" title="{loc["title"]}">📅</button>
        <div class="calendar-panel" id="calendar-panel"></div>
    </div>
</div>
<h1>🗓️ {loc["title"]}</h1>
<div class="category-bar" id="category-bar"></div>
<label class="express-filter"><input type="checkbox" id="express-filter-toggle"><span id="express-filter-label"></span></label>
<div id="search-results"></div>
<footer><p>bridge42worlds — {loc["footer"]}</p></footer>
<script src="/js/search.js?v={asset_ver()}"></script></body></html>'''
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
                f"{SITE_URL}/{LANG_DIR}/{lang}/authors/index.html",
                f"{SITE_URL}/{LANG_DIR}/{lang}/scientists/index.html"]
        authors_dir = Path(LANG_DIR) / lang / "authors"
        if authors_dir.exists():
            for p in sorted(authors_dir.glob("[a-z].html")):
                urls.append(f"{SITE_URL}/{LANG_DIR}/{lang}/authors/{p.name}")
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
        Path(fn).write_text(feed, encoding="utf-8")
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


def regenerate_all_html():
    """Пересобирает HTML всех статей из data.json (без API). Идёт по источнику правды,
    а не по индексам — устойчиво к их повреждению."""
    print("🔄 Regenerate HTML only (no API)")
    write_arxiv_categories_json()
    for lang in LANGUAGES: ensure_lang_structure(lang)
    count = 0
    for data, folder in iter_articles():
        date_str = data.get("date", folder.parent.name)
        # только контентные картинки 0.jpg..N-1.jpg (ai.jpg — обложка, не в мозаике)
        images = sorted([p for p in folder.glob("*.jpg") if p.stem.isdigit()],
                        key=lambda p: int(p.stem))
        captions = data.get("captions") or {}
        article_obj = {
            "id": data["id"],
            "title": data.get("original_title", ""),
            "authors": data.get("authors", []),
            "license_url": data.get("license", ""),
            "license_name": data.get("license_name", "CC BY"),
            "categories": data.get("categories", []),
            "primary_category": data.get("primary_category", ""),
            "refined": data.get("refined", False),
            "express": data.get("express", False),
            "express_tiers": data.get("express_tiers", []),
        }
        abstract = data.get("abstract") or {}
        for version in VERSIONS:
            for lang in LANGUAGES:
                scipop = version_scipop(data, version, lang)
                if not scipop: continue
                html = gen_article_html(scipop, article_obj, date_str,
                                        [str(p) for p in images], lang, version,
                                        captions_for_lang(captions, lang), abstract)
                out = Path(LANG_DIR) / lang / "archive" / date_str / data["id"] / VERSION_FILES[version]
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(html, encoding="utf-8")
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
            # express: реальный тир хранит короткий текст в "mini", не "threads" (см. write_article_pages)
            threads_text = base_scipop.get("threads") or base_scipop.get("mini") or ""
            if not threads_text:
                continue
            mini_scipop = dict(base_scipop)
            mini_scipop["text"] = threads_text
            out = Path(LANG_DIR) / lang / "archive" / date_str / data["id"] / "mini.html"
            out.parent.mkdir(parents=True, exist_ok=True)
            html = gen_article_html(mini_scipop, article_obj, date_str,
                                    [str(p) for p in images], lang, "mini",
                                    captions_for_lang(captions, lang), abstract)
            out.write_text(html, encoding="utf-8")
            count += 1
    build_knowledge_graph_data()
    for lang in LANGUAGES:
        update_all_tags(lang)
        update_all_scientists(lang)
        update_all_laws(lang)
        generate_knowledge_graph_page(lang)
        generate_archive_page(lang)
    update_all_authors()
    generate_sitemaps()
    generate_feeds()
    generate_status_page()
    print(f"  ✅ Regenerated {count} HTML pages + tags/scientists/authors/laws/graph")


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
    }


def build_article(a, date_str, inputs, force=False, express=False):
    """Фаза A: arXiv + PDF + все вызовы DeepSeek. Пишет только в папку статьи (гонок нет).
    Возвращает подготовленный dict либо None (пропущено/ошибка).
    express=True — дешёвый режим (см. TODO.md): один вызов generate_express() по авторской
    аннотации (не по полному тексту PDF) вместо каскада advanced→simple→popular, урезанный
    список тегов в промте (inputs['express_tags_input']). Simple шлифуется (refine_simple) —
    самый частый повод жалоб на сложность языка, теги в шлифовку не идут (см. gen_llm.refine_simple)
    и не нужны там. PDF всё равно качаем и парсим — картинки/обложка/миниатюры настоящие,
    экономим только на тексте генерации. Тиры не из config.express.tiers получают заглушку («полная
    готовится») вместо контента — апгрейд до полной версии: run.py regen <id>."""
    article_folder = Path(LANG_DIR) / DEFAULT_LANG / "archive" / date_str / a["id"]
    if not force and (article_folder / "data.json").exists():
        print(f"  ⏭️ {a['id']} — уже есть, пропускаю (--force чтобы пересоздать)")
        return None
    base_id = ARXIV_BASE_ID_RE.sub("", a["id"])
    if not force and base_id in inputs.get("existing_base_ids", set()):
        print(f"  ⏭️ {a['id']} — новая версия уже обработанной статьи ({base_id}), пропускаю (--force чтобы пересоздать)")
        return None
    try:
        oai_xml = get_license(a["id"])
        allowed, lic_url = is_allowed_license(oai_xml)
        if not allowed:
            print(f"  ⏭️ {a['id']} — license: {lic_url or 'none'}")
            return None
        atom_xml = _get_with_retry(f"http://es.arxiv.org/api/query?id_list={a['id']}", timeout=30).text
        a["license_url"], a["license_name"] = lic_url, ("CC BY 4.0" if "by/4.0" in lic_url else "CC BY")
        pdf = download_pdf(a["id"])
        text, imgs = parse_pdf(pdf)
        captions = extract_captions(text)  # подписи ищем в полном тексте (в списке литературы их нет)
        body, refs = split_references(text)
        a["cited_arxiv"] = extract_ref_arxiv_ids(refs)  # на будущее: связь с релевантными работами
        text = re.sub(r'https?://\S+', '', body)  # тело без литературы и URL → экономия ~20% токенов в промте
        print(f"  → {a['id']} …")
        article_folder.mkdir(parents=True, exist_ok=True)
        if refs:
            (article_folder / "references.txt").write_text(refs, encoding="utf-8")
        (article_folder / "arxiv-atom.xml").write_text(atom_xml, encoding="utf-8")
        (article_folder / "arxiv-oai.xml").write_text(oai_xml or "", encoding="utf-8")
        if config.get("keep_pdf", True):  # мёртвый вес на масштабе — можно не хранить
            (article_folder / "original.pdf").write_bytes(pdf.read_bytes())
        images = save_images(imgs, a["id"], article_folder)
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
            scipop_adv = generate_advanced(a, text, inputs["tags_input"], inputs["scientists_keys"])
            if not scipop_adv: return None
            (article_folder / "api").mkdir(exist_ok=True)
            (article_folder / "api" / "advanced-ru.json").write_text(
                json.dumps(scipop_adv, ensure_ascii=False, indent=2), encoding="utf-8")
            scipop_adv = validate_tags(scipop_adv, inputs["valid_tags"])
            # Simple и Popular зависят ТОЛЬКО от Advanced (не друг от друга) → генерим параллельно.
            with ThreadPoolExecutor(max_workers=2) as ex:
                fs, fp = ex.submit(generate_simple, scipop_adv), ex.submit(generate_popular, scipop_adv)
                scipop_simple, scipop_pop = fs.result(), fp.result()
            (article_folder / "api" / "simple-ru.json").write_text(
                json.dumps(scipop_simple, ensure_ascii=False, indent=2), encoding="utf-8")
            (article_folder / "api" / "popular-ru.json").write_text(
                json.dumps(scipop_pop, ensure_ascii=False, indent=2), encoding="utf-8")

        # Рефлексивная шлифовка (--refine) — Simple и Popular независимы, шлифуем параллельно.
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
        cover = pick_cover_image(images)
        if cover:
            shutil.copy(cover, article_folder / "ai.jpg")
        # Лёгкие миниатюры для ленты (t_ai + до 2 PDF); число PDF-миниатюр → в индекс
        a["thumbs"] = make_thumbnails(article_folder)

        versions_ru = {"popular": scipop_pop, "simple": scipop_simple, "advanced": scipop_adv}
        # «Аннотация» из авторского arXiv-abstract — ТРИ регистра (popular/simple/advanced), + перевод по языкам
        abstract_ru = generate_abstract(a.get("summary", ""))
        if REFINE and abstract_ru and not express:
            abstract_ru = refine_abstract(abstract_ru)
        abstract = {DEFAULT_LANG: abstract_ru}
        targets = [l for l in LANGUAGES if l != DEFAULT_LANG]
        if abstract_ru and targets:
            with ThreadPoolExecutor(max_workers=min(8, len(targets))) as aex:
                afut = {aex.submit(translate_scipop, abstract_ru, l): l for l in targets}
                for fut, l in afut.items():
                    try:
                        abstract[l] = fut.result() or abstract_ru
                    except Exception:
                        abstract[l] = abstract_ru
        # Подписи к рисункам вытащены regex'ом из английского PDF (extract_captions) — переводим
        # на все языки САЙТА, кроме английского (не FROM default_lang, а FROM "en" — источник
        # всегда английский, независимо от того, какой язык у нас DEFAULT_LANG).
        captions_by_lang = {"en": captions}
        cap_targets = [l for l in LANGUAGES if l != "en"]
        if captions and cap_targets:
            with ThreadPoolExecutor(max_workers=min(8, len(cap_targets))) as capex:
                capfut = {capex.submit(translate_captions, captions, l): l for l in cap_targets}
                for fut, l in capfut.items():
                    try:
                        captions_by_lang[l] = fut.result() or captions
                    except Exception:
                        captions_by_lang[l] = captions
        else:
            for l in cap_targets:
                captions_by_lang[l] = captions

        # Переводы: каждую версию на каждый целевой язык — параллельно. В экспрессе переводим
        # ТОЛЬКО реально сгенерированные тиры — заблокированные получают заглушку на языке
        # читателя напрямую (статичный текст, LLM не нужен, экономия перевода тоже).
        translations = {v: {} for v in VERSIONS}
        real_tiers = [v for v in VERSIONS if not express or v in express_tiers]
        if targets:
            with ThreadPoolExecutor(max_workers=min(8, len(targets) * max(1, len(real_tiers)))) as tex:
                futures = {}
                for l in targets:
                    for v in real_tiers:
                        futures[tex.submit(translate_scipop, versions_ru[v], l)] = (v, l)
                for fut, (v, l) in futures.items():
                    try:
                        res = fut.result()
                    except Exception as e:
                        print(f"    ⚠️ {a['id']} перевод {v}/{l} не удался ({e}) — оставляю оригинал")
                        res = versions_ru[v]
                    translations[v][l] = res
            if express:
                for l in targets:
                    for v in VERSIONS:
                        if v not in express_tiers:
                            translations[v][l] = express_locked_scipop(express_result, l)

        a["refined"] = REFINE and not express  # бейдж ✦/тумблер ⇄ — экспресс не шлифован
        a["express"] = express
        if express:
            a["express_tiers"] = sorted(express_tiers)
        save_data_json(versions_ru, a, date_str, article_folder, translations, captions_by_lang, abstract,
                       refined=a["refined"])
        return {"article": a, "versions": versions_ru, "translations": translations,
                "images": images, "captions": captions_by_lang, "abstract": abstract}
    except Exception as e:
        print(f"  ❌ {a['id']}: {e}")
        traceback.print_exc()
        return None


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
            scipop = versions_ru[v] if lang == DEFAULT_LANG else translations.get(v, {}).get(lang, versions_ru[v])
            (lang_folder / VERSION_FILES[v]).write_text(
                gen_article_html(scipop, a, date_str, images, lang, v, lang_captions, abstract), encoding="utf-8")
            update_index(scipop, a, date_str, lang, v, abstract_for(abstract, lang, v))
    # Mini-версия — threads-текст (полный, до обрезки). Источник title/oneliner для мини —
    # popular, ЕСЛИ он настоящий контент; если popular — экспресс-заглушка (express_locked),
    # берём simple (реально сгенерированный тир) — иначе на mini-странице повиснет
    # заглушечный oneliner «Полная версия готовится» вместо настоящего заголовка.
    # ПО ЯЗЫКУ: раньше mini_scipop строился один раз из versions_ru (русской версии) ВНЕ цикла
    # по языкам и переиспользовался для всех — на mini у en/es был русский текст под локализованной
    # обвязкой. Теперь источник берём per-язык: свой tier из translations, не всегда RU.
    if (versions_ru.get("popular", {})).get("threads"):
        for l in LANGUAGES:
            if l == DEFAULT_LANG:
                mini_source = versions_ru["popular"]
                if mini_source.get("express_locked"):
                    mini_source = versions_ru.get("simple") or mini_source
            else:
                mini_source = translations.get("popular", {}).get(l) or versions_ru["popular"]
                if mini_source.get("express_locked"):
                    mini_source = translations.get("simple", {}).get(l) or versions_ru.get("simple") or mini_source
            # express: реальный тир (simple) хранит короткий текст в поле "mini", не "threads"
            # ("threads" — только у попап-заглушки, express_locked_scipop бэкфиллит его из RU).
            threads_text = (mini_source.get("threads") or mini_source.get("mini")
                             or (versions_ru.get("popular", {})).get("threads", ""))
            mini_scipop = dict(mini_source)
            mini_scipop["text"] = threads_text
            lf = Path(LANG_DIR) / l / "archive" / date_str / a["id"]
            lf.mkdir(parents=True, exist_ok=True)
            (lf / "mini.html").write_text(
                gen_article_html(mini_scipop, a, date_str, images, l, "mini",
                                 captions_for_lang(captions, l), abstract), encoding="utf-8")
    update_authors_graph(a)
    update_tag_counts(versions_ru["advanced"])
    print(f"  ✅ {a['id']} done")


def process_day(date_str, force=False, refresh_aggregates=True, express=False, limit=None, category=None):
    print(f"\n{'=' * 60}\n📅 {date_str}{' [экспресс]' if express else ''}{f' [{category}]' if category else ''}\n{'=' * 60}")
    for lang in LANGUAGES: ensure_lang_structure(lang)

    articles = fetch_arxiv(date_str, category=category or "astro-ph.*")
    if not articles: return 0
    best = select_best(articles, date_str)
    if limit is not None:
        best = best[:limit]
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

    if refresh_aggregates and prepared:
        for lang in LANGUAGES:
            update_all_tags(lang)
            update_all_scientists(lang)
            generate_archive_page(lang)
        update_all_authors()
        generate_sitemaps()
        generate_feeds()
        generate_status_page()
    print(f"\n✅ {date_str}: {len(prepared)} articles generated")
    return len(prepared)


# ── Обслуживание: reindex / графы / удаление / целостность ──
def _index_entry(scipop, data, date_str, lang, version):
    url = f"/{LANG_DIR}/{lang}/archive/{date_str}/{data['id']}/{VERSION_FILES[version]}"
    abstract = abstract_for(data.get("abstract"), lang, version)
    has_image = (Path(LANG_DIR) / DEFAULT_LANG / "archive" / date_str / data["id"] / "ai.jpg").exists()
    return {
        "id": data["id"], "version": version,
        "title": scipop.get("title", data.get("original_title", "")),
        "oneliner": strip_markers(scipop.get("oneliner", ""))[:300],
        "description": strip_markers(scipop.get("description", ""))[:300],
        "abstract": strip_markers(abstract)[:1500],
        "threads": strip_markers(data.get("threads", ""))[:480],
        "thumbs": data.get("thumbs", 0),
        "authors": data.get("authors", [])[:50], "date": date_str,  # до 50 — лента показывает ≤20, >20 разворачивает
        "tags": [scipop.get("main_tag", "")] + scipop.get("extra_tags", []),
        "scientists": scipop.get("scientists", []), "url": url,
        "reading": reading_minutes(scipop),
        "categories": data.get("categories", []),
        "primary_category": data.get("primary_category", ""),
        "express": data.get("express", False),
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
            date_str = (a.get("published") or "")[:10] or TARGET_DATE
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
            generate_archive_page(lang)
        update_all_authors()
        generate_sitemaps()
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


def backfill_images(force=False):
    """Бэкфилл обложек статей — ai.jpg = крупнейшая картинка из самого PDF (см. pick_cover_image),
    не FLUX. Ищет уже сохранённые PDF-картинки в папке статьи (0.jpg, 1.jpg, ... — так их
    называет save_images) и берёт самую крупную по площади."""
    print("  🖼️ Бэкфилл обложек статей (источник — картинки из PDF, не AI-генерация)")

    def one(item):
        data, folder = item
        img = folder / "ai.jpg"
        if img.exists() and not force:
            return False
        pdf_images = sorted((p for p in folder.glob("*.jpg") if p.stem.isdigit()), key=lambda p: int(p.stem))
        cover = pick_cover_image([str(p) for p in pdf_images])
        got_img = False
        if cover:
            shutil.copy(cover, img)
            got_img = True
        nthumbs = make_thumbnails(folder)  # t_ai + до 2 PDF — обновляем всегда
        if data.get("thumbs") != nthumbs:
            data["thumbs"] = nthumbs
            (folder / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"    · {data['id']} (обложка={'ok' if got_img else '—'}, миниатюр PDF={nthumbs})")
        return got_img

    items = list(iter_articles())
    with ThreadPoolExecutor(max_workers=min(10, len(items) or 1)) as ex:
        results = list(ex.map(one, items))
    n_img = sum(1 for i in results if i)
    print(f"  ✅ Обложек: {n_img}")


def entity_image_url(kind, entity_id):
    """URL AI-обложки тега/закона (единая на все языки, живёт под default_lang), либо '' если нет файла."""
    p = Path(LANG_DIR) / DEFAULT_LANG / kind / "img" / f"{entity_id}.jpg"
    return f"/{LANG_DIR}/{DEFAULT_LANG}/{kind}/img/{entity_id}.jpg" if p.exists() else ""


def backfill_tag_law_images(force=False, gen_images=False):
    """AI-обложки для тегов и законов — по образцу статей: один промпт+картинка на сущность (не на язык).
    Промпт хранится в источнике (lang/{default}/data/tags.json|laws.json), картинка —
    lang/{default}/{tags|laws}/img/{id}.jpg (общая для всех языков, как ai.jpg у статей).

    gen_images=False (по умолчанию) — реальную FLUX-генерацию НЕ трогаем, только промпт (дёшево).
    Новые сущности без картинки помечаются entry["image_pending"]=True (честно: промпт готов,
    картинки нет — ждёт бюджета); блок .ai-cover просто не рендерится, место не теряется.
    gen_images=True — реальная трата (нужен бюджет): генерит картинку через FLUX и снимает pending
    у тех, кому реально досталась картинка. Уже существующие картинки этот флаг не трогает."""
    has_key = bool(os.environ.get("DEEPINFRA_API_KEY", "")) and gen_images
    print(f"  🖼️ Обложки тегов/законов (картинки: {'да, трачу бюджет' if has_key else 'НЕТ — только промпты + честная пометка pending'})")

    def one(kind, entity_id, entry):
        prompt = entry.get("image_prompt", "")
        got_prompt = got_img = False
        if not prompt or force:
            fake = {
                "title": entry.get("name", entity_id),
                "oneliner": entry.get("description_popular", "") or entry.get("description", ""),
                "description": entry.get("description", ""),
                "main_tag": entity_id, "extra_tags": [],
            }
            new_prompt = generate_image_prompt(fake)
            if new_prompt:
                prompt = new_prompt
                entry["image_prompt"] = prompt
                got_prompt = True
        img_dir = Path(LANG_DIR) / DEFAULT_LANG / kind / "img"
        img_dir.mkdir(parents=True, exist_ok=True)
        img = img_dir / f"{entity_id}.jpg"
        if has_key and prompt and (force or not img.exists() or entry.get("image_pending")):
            got_img = generate_image(prompt, img)
            if got_img:
                entry["image_pending"] = False
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
        if vdata.get(target_lang) and not force:
            continue
        src = vdata.get(DEFAULT_LANG)
        if not src:
            continue
        vdata[target_lang] = translate_scipop(src, target_lang)
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
    for version in VERSIONS:
        scipop = version_scipop(data, version, target_lang)
        if not scipop:
            continue
        html = gen_article_html(scipop, article_obj, date_str, [str(p) for p in images],
                                 target_lang, version, lang_captions, data.get("abstract") or {})
        (lang_folder / VERSION_FILES[version]).write_text(html, encoding="utf-8")
    base_scipop = version_scipop(data, "popular", target_lang) or version_scipop(data, "simple", target_lang) or {}
    if base_scipop.get("express_locked"):
        base_scipop = version_scipop(data, "simple", target_lang) or base_scipop
    threads_text = base_scipop.get("threads") or base_scipop.get("mini") or ""
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