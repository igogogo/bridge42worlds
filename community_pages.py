#!/usr/bin/env python3
"""Страницы авторских работ: сборка раздела /community/ на пяти языках.

Раздел живёт ОТДЕЛЬНЫМ корпусом, а не флагом в общем архиве. Причина в требовании
владельца «в общую ленту пока не включаем»: с флагом его пришлось бы не забыть в ленте,
в latest-индексе, в лентах подписки, в карте сайта, на дашборде, в аналитике и в графе —
и забыть в каком-нибудь одном из них рано или поздно. Отдельный корпус делает протечку
невозможной по построению: чего нет в articles-index, то в ленту не попадёт.

Что здесь:
    build_work(code)     страница одной работы на всех языках
    build_index(lang)    список раздела
    build_all()          и то, и другое

Данные работы лежат в data/submissions/<code>/publish.json — его готовит
tools/submission.py на стадии publish. Приватное (почта, токен) остаётся в meta.json
и в publish.json не попадает НИКОГДА: файл уезжает на сайт.
"""
import html as H
import json
from urllib.parse import quote
import sys
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

LANGS = ["ru", "en", "es", "ar", "fr"]
RTL = {"ar"}
SUBS = ROOT / "data" / "submissions"
SITE = "https://bridge42worlds.academy"


def _tpl(name):
    p = ROOT / "templates" / f"{name}.html"
    return Template(p.read_text(encoding="utf-8")) if p.exists() else None


def _strings(lang):
    """Строки интерфейса раздела с откатом на язык-источник по КЛЮЧАМ.

    Откат именно по ключам, а не по файлу целиком: перевод может отстать на несколько
    строк, и из-за одной недостающей не должна разваливаться вся страница. Тот же приём,
    что в generate_about_page."""
    def load(l):
        p = ROOT / "lang" / l / "data" / "community.json"
        try:
            return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        except Exception:
            return {}
    return {**load("ru"), **load(lang)}


def _works():
    """Опубликованные работы, свежие сверху. Снятые автором пропускаем."""
    out = []
    if not SUBS.exists():
        return out
    for d in sorted(SUBS.iterdir()):
        p = d / "publish.json"
        if not p.exists():
            continue
        try:
            w = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if w.get("withdrawn"):
            continue
        out.append(w)
    return sorted(out, key=lambda w: w.get("received", ""), reverse=True)


JOIN_SUBJECT = {
    "ru": "Работа на разбор",
    "en": "Paper for review",
    "es": "Trabajo para analizar",
    "fr": "Travail à analyser",
    "ar": "عمل للمراجعة",
}


def _paras(text):
    """Текст в абзацы с экранированием. Работа автора — чужой ввод: никакого сырого html."""
    return "".join(f"<p>{H.escape(x.strip())}</p>"
                   for x in (text or "").split("\n\n") if x.strip())


def _levels(work, lang, s):
    """Переключатель уровней нашей обработки: мини / просто / подробно.

    Уровни лежат в самой странице скрытыми блоками, а не подгружаются: работа короткая,
    все три версии вместе весят меньше, чем стоил бы лишний запрос, и переключение
    получается мгновенным без сети."""
    order = [("mini", s.get("level_mini", "мини")),
             ("simple", s.get("level_simple", "просто")),
             ("advanced", s.get("level_advanced", "подробно"))]
    have = [(k, t) for k, t in order if (work.get("ours", {}).get(lang, {}) or {}).get(k)]
    if not have:
        return "", ""
    # Классы .lv-switch / .lv-btn — те же, что у обычной статьи, а не свои. Свои
    # выглядели ровно так, как выглядит неоформленная кнопка: 19 пикселей высотой,
    # пальцем не попасть (поймано эмуляцией на экране 375). Общие стили уже знают
    # и про размер касания (42px), и про активное состояние, и про тёмную тему.
    btns = "".join(
        f'<button type="button" class="lv-btn{" active" if i == 0 else ""}" '
        f'data-lvl="{k}">{H.escape(t)}</button>'
        for i, (k, t) in enumerate(have))
    body = "".join(
        f'<div class="cw-lvl-body{" on" if i == 0 else ""}" data-lvl="{k}">'
        f'{_paras((work["ours"][lang] or {}).get(k))}</div>'
        for i, (k, _) in enumerate(have))
    # Переключение — коротким скриптом рядом: страница самодостаточна, js/search.js
    # ей не нужен (ни ленты, ни поиска здесь нет), тащить его ради трёх кнопок незачем.
    js = ("<script>(function(){var s=document.currentScript.parentNode;"
          "s.addEventListener('click',function(e){var b=e.target.closest('.lv-btn');"
          "if(!b)return;var v=b.dataset.lvl;"
          "s.querySelectorAll('.lv-btn').forEach(function(x){x.classList.toggle('active',x===b)});"
          "document.querySelectorAll('.cw-lvl-body').forEach(function(x){"
          "x.classList.toggle('on',x.dataset.lvl===v)});});})();</script>")
    return f'<div class="lv-switch">{btns}</div>{js}', body


_ICO_DOC = ('<svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/>'
            '<path d="M14 3v5h5"/><path d="M9 13h6"/><path d="M9 17h4"/></svg>')
_ICO_BOX = ('<svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            '<path d="M3 7.5h18v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
            '<path d="M3 7.5l1.6-3.2A1.5 1.5 0 0 1 6 3.5h12a1.5 1.5 0 0 1 1.4.8L21 7.5"/>'
            '<path d="M10 12h4"/></svg>')


def _src_btn(url, label, primary=False, size=None):
    """Кнопка к материалам работы. Нет файла — нет и кнопки.

    Кнопка, ведущая в 404, хуже отсутствующей: читатель решит, что у нас сломано, а не
    что материала нет. Так уже было — на странице стояла ссылка на source.zip, который
    никто никуда не клал."""
    if not url or not label:
        return ""
    cls = "cw-src-btn primary" if primary else "cw-src-btn"
    ico = _ICO_DOC if primary else _ICO_BOX
    mb = f'<span class="cw-src-size">{size} МБ</span>' if size else ""
    return f'<a class="{cls}" href="{H.escape(url)}">{ico}{H.escape(label)}{mb}</a>'


def _source_inline(work, s):
    """Ссылки на первоисточник прямо в строке-паспорте — там, где у статьи стоит arXiv.

    Читатель ищет первоисточник по привычке в этом месте, а не в конце страницы. У нас его
    три вида, и порядок не случаен (владелец 2026-08-08: «давай HTML и PDF как опция»):

        работа: HTML        живой файл автора — с работающими визуализациями
        PDF                 то же самое на бумагу; динамики в нём нет по природе
        полные материалы    данные, код, графики — то, чем работа проверяется

    HTML первым именно потому, что PDF теряет интерактив, а он в этой работе есть.
    Чего нет — того и в строке нет: ссылка в 404 хуже отсутствующей.
    """
    out = []
    if work.get("live_url"):
        out.append((work["live_url"], s.get("src_live", "HTML")))
    if work.get("pdf_url"):
        out.append((work["pdf_url"], s.get("src_pdf", "PDF")))
    if work.get("archive_url"):
        mb = work.get("archive_mb")
        out.append((work["archive_url"],
                    s.get("src_zip", "ZIP") + (f" · {mb} МБ" if mb else "")))
    if not out:
        return ""
    return "".join(f'<span>·</span><a href="{H.escape(u)}">{H.escape(t)}</a>' for u, t in out)


_LOC_CACHE = {}


def _loc_json(lang, name):
    """Локализованный справочник (tags.json, laws.json) — читаем раз за прогон."""
    key = (lang, name)
    if key not in _LOC_CACHE:
        p = ROOT / "lang" / lang / "data" / f"{name}.json"
        try:
            _LOC_CACHE[key] = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            _LOC_CACHE[key] = {}
    return _LOC_CACHE[key]


def _tags_laws(work, lang, s):
    """Теги и законы работы — теми же чипами, что на обычной статье.

    Владелец 2026-08-08: «не вижу наших обычных тегов, законов и так далее — немного не по
    уставу всё». Без этой разметки работа выпадает из графа знаний: её не находят ни через
    облако тегов, ни со страницы закона, ни в перекрёстных связях. Выделять авторскую
    работу должна плашка, а не отсутствие обычного устройства страницы.
    """
    tags = work.get("tags") or []
    laws = work.get("laws") or []
    if not tags and not laws:
        return ""
    tloc = _loc_json(lang, "tags")
    lloc = _loc_json(lang, "laws")
    parts = []
    if tags:
        chips = "".join(
            f'<a href="/lang/{lang}/tags/{H.escape(t)}.html" class="side-tag" '
            f'data-tag="{H.escape(t, quote=True)}">'
            f'{H.escape((tloc.get(t) or {}).get("name", t))}</a>' for t in tags)
        parts.append(f'<div class="side-tags-label">{H.escape(s.get("tags_label", ""))}</div>{chips}')
    if laws:
        chips = "".join(
            f'<a href="/lang/{lang}/laws/{H.escape(lid)}.html" class="side-law" '
            f'data-law="{H.escape(lid, quote=True)}">'
            f'{H.escape((lloc.get(lid) or {}).get("name", lid))}</a>' for lid in laws)
        parts.append(f'<div class="side-laws-label">{H.escape(s.get("laws_label", ""))}</div>{chips}')
    return f'<div class="cw-tags side-tags">{"".join(parts)}</div>'


def _cover(work, title):
    """Обложка работы. Рисуется своим пресетом (tools/submission_cover.py) — ярче и
    контрастнее, чем у обычной статьи: таких работ единицы, и они должны выделяться."""
    url = work.get("cover_url")
    if not url:
        return ""
    return (f'<figure class="cw-cover"><img src="{H.escape(url)}" '
            f'alt="{H.escape(title)}" fetchpriority="high"></figure>')


def _video_slide(work, lang, s):
    """Видео — ПЕРВЫМ кадром той же галереи, что и картинки, а не своей секцией.

    Сперва оно стояло отдельным блоком, и владелец сказал: «видео в том же ряду, что и
    картинки, ну всё так же». Он прав — это ещё одна иллюстрация к работе, просто
    движущаяся; отдельная секция под неё ломает единый ряд и заставляет читателя
    переучиваться. Первым — потому что живая съёмка установки объясняет больше, чем
    любой график.
    """
    vids = work.get("videos") or []
    if not vids:
        return ""
    caps = (work.get("captions", {}) or {}).get(lang, {}) or {}
    v = vids[0]
    poster = f' poster="{H.escape(v["poster"])}"' if v.get("poster") else ""
    cap = caps.get(v.get("file", "")) or s.get("video_note", "")
    return (f'<div class="gallery-video">'
            f'<video controls preload="metadata"{poster} playsinline>'
            f'<source src="{H.escape(v["url"])}" type="{H.escape(v["type"])}"></video>'
            + (f'<figcaption class="gallery-caption">{H.escape(cap)}</figcaption>' if cap else "")
            + '</div>')


def _figures(work, lang, s):
    """Иллюстрации автора — НАШЕЙ галереей, той же, что у обычной статьи.

    Сначала это была сетка из 27 карточек подряд, и владелец сказал прямо: «картинки из
    работы россыпью, а не как у нас положено… понятно, что должно выделяться, но хотя бы
    чтобы близко было». Он прав: выделять авторскую работу должна плашка и обложка, а не
    другой способ показывать картинки. Читатель, пришедший со статьи, не должен заново
    учиться смотреть.

    Поэтому здесь ровно та же разметка, что рендерит gen_mosaic() в generate.py: одно
    главное изображение, лента превью снизу, стрелки, клик — полноэкранный просмотр.
    Работают те же js/gallery.js и js/lightbox.js.

    Подписи пишет модель по тексту работы и переводит на все языки: имя файла
    comb_histogram.png читателю не говорит ничего.
    """
    imgs = work.get("images") or []
    if not imgs:
        return ""
    caps = (work.get("captions", {}) or {}).get(lang, {}) or {}
    items = [(im["url"], caps.get(im.get("file", "")) or "") for im in imgs]
    video_html = _video_slide(work, lang, s)

    n = len(items)
    thumbs = "".join(
        f'<button type="button" class="gallery-thumb{" is-active" if k == 0 else ""}" '
        f'data-i="{k}" data-src="{H.escape(u)}" data-cap="{H.escape(c, quote=True)}" '
        f'aria-label="{H.escape(c, quote=True) or f"Image {k + 1}"}">'
        f'<img src="{H.escape(u)}" alt="" loading="lazy"></button>'
        for k, (u, c) in enumerate(items))
    u0, c0 = items[0]
    nav = ('<button type="button" class="gallery-nav gallery-prev" aria-label="Prev">‹</button>'
           '<button type="button" class="gallery-nav gallery-next" aria-label="Next">›</button>'
           ) if n > 1 else ""
    thumbs_html = f'<div class="gallery-thumbs">{thumbs}</div>' if n > 1 else ""
    gallery = (
        f'<div class="gallery" data-count="{n}">'
        f'<div class="gallery-stage">{nav}'
        f'<a class="gallery-main" href="{H.escape(u0)}" aria-label="Open image">'
        f'<img class="gallery-main-img" src="{H.escape(u0)}" alt="{H.escape(c0, quote=True)}"></a>'
        f'<figcaption class="gallery-caption"{"" if c0 else " style=\'display:none\'"}>'
        f'{H.escape(c0)}</figcaption>'
        f'</div>{thumbs_html}</div>')
    # Ровно как у статьи: галерея стоит в .mosaic сразу под шапкой, без своего заголовка
    # и пояснений. Видео — первым кадром того же ряда.
    return f'<div class="mosaic">{video_html}{gallery}</div>'


_TITLES = {}


def _local_title(item, lang):
    """Заголовок статьи на нужном языке из индекса; при отсутствии — как есть.

    Индекс каждого языка читаем один раз за прогон: на пяти языках и пяти похожих
    работах повторное чтение семимегабайтного файла заняло бы дольше, чем вся сборка."""
    if lang not in _TITLES:
        try:
            idx = json.loads((ROOT / "lang" / lang / "articles-index.json").read_text(encoding="utf-8"))
            _TITLES[lang] = {a["id"]: a.get("title", "") for a in idx}
        except Exception:
            _TITLES[lang] = {}
    return _TITLES[lang].get(item.get("id"), "") or item.get("title", "")


def build_work(code, langs=None):
    """Страница одной работы на каждом языке. Возвращает список готовых путей."""
    tpl = _tpl("community-work")
    if not tpl:
        print("⚠️ нет templates/community-work.html")
        return []
    p = SUBS / code / "publish.json"
    if not p.exists():
        print(f"⚠️ {code}: нет publish.json — работа ещё не подготовлена к публикации")
        return []
    w = json.loads(p.read_text(encoding="utf-8"))
    made = []
    for lang in (langs or LANGS):
        s = _strings(lang)
        loc = (w.get("ours", {}).get(lang) or {})
        title = loc.get("title") or w.get("title") or code
        kind = w.get("kind", "")
        # Класс вида — общий словарь на обе страницы раздела; расхождение имён однажды
        # уже стоило нам разного цвета одного и того же признака.
        kind_cls = {"экспериментальная": "experimental", "теоретическая": "theoretical",
                    "experimental": "experimental", "theoretical": "theoretical"}.get(kind, "")
        sw, body = _levels(w, lang, s)
        # Разбор своего языка; откат на язык-источник, если перевод не сошёлся.
        rev_all = w.get("review", {})
        rev = rev_all.get(lang) or rev_all.get("ru") or (rev_all if "strength" in rev_all else {})
        # Заголовки похожих работ — на языке страницы. В similar.json они лежат
        # по-русски (подбирались по русскому корпусу), и без подстановки арабская
        # страница показывала русский список.
        sim = "".join(
            f'<li><a href="/lang/{lang}/archive/{x["id"]}/">'
            f'{H.escape(_local_title(x, lang))}</a></li>'
            for x in (w.get("similar") or [])[:5])

        vals = {
            "lang": lang, "dir": "rtl" if lang in RTL else "ltr",
            "slug": code, "page_file": "index.html",
            "canonical_url": f"{SITE}/lang/{lang}/community/{code}/",
            "page_title": title, "og_title": title,
            "work_title": H.escape(title),
            "oneliner": H.escape(loc.get("oneliner") or ""),
            "description": H.escape((loc.get("oneliner") or title)[:180]),
            "og_image_html": "", "hreflang_links": "", "goatcounter": "bridge42worlds",
            "received_date": w.get("received", ""),
            "author_display": H.escape(w.get("author_display") or s.get("author_anon", "автор не представился")),
            # Подпись «автор» — только когда есть имя. Иначе строка читалась
            # «автор автор не представился»: слово шло и в подписи, и в значении.
            "author_label_shown": H.escape(s.get("author_label", "")) if w.get("author_display") else "",
            "kind": kind_cls, "author_kind": kind_cls,
            "kind_label": H.escape(s.get(f"kind_{kind_cls}", kind)),
            "level_switch_html": sw, "level_switch_bottom_html": "",
            "text_html": body,
            "review_strength_html": _paras(rev.get("strength")),
            "review_advice_html": "".join(f"<li>{H.escape(x)}</li>" for x in (rev.get("advice") or [])),
            "review_questions_html": "".join(f"<li>{H.escape(x)}</li>" for x in (rev.get("questions") or [])),
            "author_comment_html": _paras(w.get("author_comment")),
            "similar_html": f"<ul>{sim}</ul>" if sim else "",
            # Подсказка про публичный код — ТОЛЬКО когда автор не представился.
            # Иначе страница писала «автор Сергей» и «автор не назвал себя» подряд.
            "author_hint_html": ("" if w.get("author_display")
                                 else f'<p class="cw-token-note">{H.escape(s.get("author_hint", ""))}</p>'),
            # Блок «слово автора» показываем, только если слово есть. Пустая врезка с его
            # подписью приписывала бы автору молчание, которого он не выбирал.
            "author_word_open": '<section class="cw-sec">' if w.get("author_comment") else "<!--",
            "author_word_close": "</section>" if w.get("author_comment") else "-->",
            "source_url": w.get("source_url") or "",
            "source_meta": H.escape(w.get("source_meta") or ""),
            # Живая версия — ГЛАВНАЯ кнопка: это работа автора как он её сверстал, с
            # работающими визуализациями. PDF рядом, обычной: он их теряет по природе.
            "source_live_html": _src_btn(w.get("live_url"), s.get("source_live_label", ""), primary=True),
            "source_pdf_html": _src_btn(w.get("pdf_url"), s.get("source_pdf_label", "")),
            "source_zip_html": _src_btn(w.get("archive_url"), s.get("source_zip_label", ""),
                                        size=w.get("archive_mb")),
            "figures_html": _figures(w, lang, s),
            "source_inline_html": _source_inline(w, s),
            "tags_html": _tags_laws(w, lang, s),
            "cover_html": _cover(w, title),
            # Обложка уезжает в карточку при пересылке: без неё работа выглядит в
            # мессенджере серым прямоугольником, тогда как все наши статьи с картинкой.
            "og_image_html": (f'<meta property="og:image" content="{SITE}{H.escape(w["cover_url"])}">'
                              '\n    <meta name="twitter:card" content="summary_large_image">'
                              if w.get("cover_url") else ""),
        }
        # Остальное — строки интерфейса; недостающие не роняют страницу, а видны как пустота
        out = tpl.safe_substitute({**{k: "" for k in ()}, **s, **vals})
        d = ROOT / "lang" / lang / "community" / code
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(out, encoding="utf-8")
        made.append(str(d / "index.html"))
    return made


def build_index(lang):
    tpl = _tpl("community-index")
    if not tpl:
        return None
    s = _strings(lang)
    cards = []
    for w in _works():
        loc = (w.get("ours", {}).get(lang) or {})
        title = loc.get("title") or w.get("title") or w["code"]
        kind_cls = {"экспериментальная": "experimental", "теоретическая": "theoretical",
                    "experimental": "experimental", "theoretical": "theoretical"}.get(w.get("kind", ""), "")
        cards.append(
            f'<a class="work" href="/lang/{lang}/community/{w["code"]}/">'
            f'<span class="work-kind work-kind-{kind_cls}">{H.escape(s.get(f"kind_{kind_cls}", ""))}</span>'
            f'<span class="work-title">{H.escape(title)}</span>'
            f'<span class="work-meta">{w.get("received", "")} · '
            f'{H.escape(w.get("author_display") or s.get("author_anon", ""))}</span>'
            f'<span class="work-lead">{H.escape((loc.get("oneliner") or "")[:200])}</span></a>')
    vals = {
        "lang": lang, "dir": "rtl" if lang in RTL else "ltr",
        "og_meta_html": "", "page_title": s.get("section_h1", "Авторские работы"),
        "works_html": "".join(cards),
        # Кнопка «написать нам» вела на саму эту страницу — то есть никуда: человек,
        # решившийся прислать работу, нажимал и оставался на месте (владелец 2026-08-19).
        # Ведём в почту, куда смотрит mail_watch, и подставляем тему: по ней письмо
        # опознаётся автоматом, а автору не надо гадать, что писать в заголовке.
        # Правила оформления и промпт подготовки уходят ответом на это письмо — так
        # и написано абзацем выше, поэтому отдельной страницы с процедурой не заводим.
        "join_url": "mailto:article@bridge42worlds.academy?subject="
                    + quote(JOIN_SUBJECT.get(lang, JOIN_SUBJECT["en"])),
    }
    out = tpl.safe_substitute({**s, **vals})
    d = ROOT / "lang" / lang / "community"
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(out, encoding="utf-8")
    return str(d / "index.html")



def build_prepare(lang):
    """Страница подготовки: промпт и порядок проверки.

    Отдельная страница, а не раздел гида. Владелец 2026-08-07: «я давал на вход наш about,
    а надо было дать страницу, где описан промт и условия». Гид объясняет, что у нас есть;
    автору нужно знать, что сделать, — это разные тексты и разные адреса.

    Промпт экранируем: он уходит внутрь <pre> как текст, и любой угловой скобкой в нём
    страница бы поломалась."""
    tpl = _tpl("community-prepare")
    if not tpl:
        return None
    s = _strings(lang)
    vals = {
        "lang": lang, "dir": "rtl" if lang in RTL else "ltr",
        "prep_prompt_text": H.escape(s.get("prep_prompt_text", "")),
    }
    out = tpl.safe_substitute({**s, **vals})
    d = ROOT / "lang" / lang / "community" / "prepare"
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(out, encoding="utf-8")
    return str(d / "index.html")


def build_all():
    n = 0
    for w in _works():
        n += len(build_work(w["code"]))
    for lang in LANGS:
        build_index(lang)
        build_prepare(lang)
    print(f"✅ раздел собран: {len(_works())} работ, {n} страниц + {len(LANGS)} списков")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "all":
        build_work(sys.argv[1])
    else:
        sys.exit(build_all())
