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
        "join_url": f"/lang/{lang}/community/",
    }
    out = tpl.safe_substitute({**s, **vals})
    d = ROOT / "lang" / lang / "community"
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(out, encoding="utf-8")
    return str(d / "index.html")


def build_all():
    n = 0
    for w in _works():
        n += len(build_work(w["code"]))
    for lang in LANGS:
        build_index(lang)
    print(f"✅ раздел собран: {len(_works())} работ, {n} страниц + {len(LANGS)} списков")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "all":
        build_work(sys.argv[1])
    else:
        sys.exit(build_all())
