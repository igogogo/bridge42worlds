#!/usr/bin/env python3
"""Страница «Идеи проектов» — то, за что можно взяться, с опорой на работы.

Владелец 30 августа спросил, жив ли генератор идей. Жив: `tools/ideas.py` пишет
дельные идеи с методиками, первым шагом и честным риском. Но продукта не было —
`data/ideas/` был пуст, и ни одна страница на него не ссылалась. Здесь продукт.

КОМУ ЭТО. Не читателю ленты, а тому, у кого работы ещё нет: студенту инженерного
факультета, аспиранту, инженеру. Он приходит с областью — «опреснение воды»,
«пыль на солнечных панелях» — и получает дела, за которые можно взяться завтра.

ОТКУДА ОПОРЫ И ПОЧЕМУ ЭТО ВАЖНО ВИДЕТЬ. У идеи всегда названы работы, на которых
она стоит, и они бывают двух родов. Наши разборы — ссылка ведёт на страницу сайта.
Работы поля arXiv, которых мы ещё не разбирали, — ссылка ведёт на arXiv, и это
честно помечено. Второе не недостаток, а признание: по прикладным темам наш архив
пока молчит, а поле в 2,96 млн работ — нет.

ЯЗЫК. Русский лежит в корне записи, остальные четыре — в ветке lang (их пишет
`ideas.py --translate` общим переводчиком статей). Страница выбирает язык сама и
показывает только те, что готовы: полупереведённое хуже, чем честно непереведённое.

    python tools/ideas_page.py        собрать /ideas.html и /data/ideas/index.json
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "ideas"
OUT = ROOT / "ideas.html"
INDEX = SRC / "index.json"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LANGS = ("ru", "en", "es", "ar", "fr")

T = {
    "ru": { "pickLbl": "Тема", "origins": {"applied": "Прикладное", "core": "Наше ядро", "area": "Области машины знаний", "demand": "Спрос машины знаний"}, "like": "нравится", "dislike": "не то", "comment": "+ комментарий", "commentHint": "отклики читаем пачками — идею можем поправить", "send": "отправить", "expressMark": "экспресс", "open": "Открыть идею","title": "Идеи проектов", "sub": "За что можно взяться — с опорой на работы",
           "none": "Идей пока нет", "scale": "масштаб", "what": "что делаем",
           "why": "зачем", "methods": "как", "first": "первый шаг", "needs": "что нужно",
           "risks": "где споткнётся", "origin": "почему мы это предлагаем",
           "based": "опора", "ours": "наш разбор", "field": "работа arXiv, не разобрана",
           "topics": "Области", "note": "Каждая идея обязана опираться на конкретные "
           "работы, и они названы. Идея без опоры — красивые слова, их и без нас много."},
    "en": { "pickLbl": "Topic", "origins": {"applied": "Applied", "core": "Our core", "area": "Areas the machine found", "demand": "What the machine lacks"}, "like": "like", "dislike": "not for me", "comment": "+ comment", "commentHint": "we read replies in batches — the idea may change", "send": "send", "expressMark": "express", "open": "Open the idea","title": "Project ideas", "sub": "Things you can take on — grounded in papers",
           "none": "No ideas yet", "scale": "scale", "what": "what to do",
           "why": "why", "methods": "how", "first": "first step", "needs": "what you need",
           "risks": "where it stumbles", "origin": "why we suggest it",
           "based": "grounded in", "ours": "our analysis", "field": "arXiv paper, not analysed",
           "topics": "Areas", "note": "Every idea must rest on named papers. "
           "An idea without grounding is just words, and there are plenty of those."},
    "es": { "pickLbl": "Tema", "origins": {"applied": "Aplicado", "core": "Nuestro núcleo", "area": "Áreas halladas por la máquina", "demand": "Lo que le falta a la máquina"}, "like": "me gusta", "dislike": "no es lo mío", "comment": "+ comentario", "commentHint": "leemos las respuestas por lotes — la idea puede cambiar", "send": "enviar", "expressMark": "exprés", "open": "Abrir la idea","title": "Ideas de proyectos", "sub": "Qué se puede emprender, apoyado en trabajos",
           "none": "Aún no hay ideas", "scale": "escala", "what": "qué hacer",
           "why": "para qué", "methods": "cómo", "first": "primer paso", "needs": "qué hace falta",
           "risks": "dónde tropezará", "origin": "por qué lo proponemos",
           "based": "apoyo", "ours": "nuestro análisis", "field": "trabajo de arXiv, sin analizar",
           "topics": "Áreas", "note": "Cada idea debe apoyarse en trabajos concretos, y están "
           "nombrados. Una idea sin apoyo son solo palabras, y de esas sobran."},
    "ar": { "pickLbl": "الموضوع", "origins": {"applied": "تطبيقية", "core": "صميم عملنا", "area": "مجالات وجدتها آلة المعرفة", "demand": "ما ينقص آلة المعرفة"}, "like": "يعجبني", "dislike": "ليس لي", "comment": "+ تعليق", "commentHint": "نقرأ الردود على دفعات — قد تتغيّر الفكرة", "send": "إرسال", "expressMark": "سريعة", "open": "افتح الفكرة","title": "أفكار مشاريع", "sub": "ما يمكن الشروع فيه، مستنداً إلى أبحاث",
           "none": "لا توجد أفكار بعد", "scale": "الحجم", "what": "ماذا نفعل",
           "why": "لماذا", "methods": "كيف", "first": "الخطوة الأولى", "needs": "ما يلزم",
           "risks": "أين قد يتعثّر", "origin": "لماذا نقترح ذلك",
           "based": "الاستناد", "ours": "تحليلنا", "field": "بحث في arXiv، لم نحلّله",
           "topics": "المجالات", "note": "كل فكرة يجب أن تستند إلى أبحاث محددة، وهي مذكورة. "
           "الفكرة بلا استناد مجرد كلام، والكلام كثير."},
    "fr": { "pickLbl": "Sujet", "origins": {"applied": "Appliqué", "core": "Notre cœur", "area": "Domaines trouvés par la machine", "demand": "Ce qui manque à la machine"}, "like": "j’aime", "dislike": "pas pour moi", "comment": "+ commentaire", "commentHint": "nous lisons les réponses par lots — l’idée peut changer", "send": "envoyer", "expressMark": "express", "open": "Ouvrir l’idée","title": "Idées de projets", "sub": "Ce qu’on peut entreprendre, appuyé sur des travaux",
           "none": "Pas encore d’idées", "scale": "échelle", "what": "quoi faire",
           "why": "pourquoi", "methods": "comment", "first": "première étape", "needs": "ce qu’il faut",
           "risks": "où ça coince", "origin": "pourquoi nous le proposons",
           "based": "appui", "ours": "notre analyse", "field": "article arXiv, non analysé",
           "topics": "Domaines", "note": "Chaque idée doit s’appuyer sur des travaux nommés. "
           "Une idée sans appui n’est que des mots, et il y en a assez."},
}

CSS = """
.id-head { margin: 0 0 6px; }
.id-head h1 { font-family: var(--serif); font-size: 27px; margin: 0 0 4px; }
.id-sub { color: var(--soft); font-size: 13px; }
.id-note { color: var(--muted); font-size: 12px; margin: 8px 0 0; max-width: 62ch;
    line-height: 1.5; }
/* ВЫБОР ТЕМЫ — СПИСКОМ, А НЕ РЯДОМ КНОПОК. Двадцать четыре кнопки занимали четверть
   экрана и отодвигали сами идеи ниже сгиба; а тем в очереди девяносто четыре, и ряд
   вырос бы на весь экран (владелец 01.09: «верхний список разделов занимает всё место,
   сделать выпадающим списком»). Список занимает одну строку при любом числе тем и
   сохраняет пласты: они становятся группами внутри него. */
.id-bar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
    margin: 14px 0 0; padding: 10px 0; border-top: 1px solid var(--hair);
    border-bottom: 1px solid var(--hair); }
.id-picklbl { font-family: var(--mono); font-size: 10.5px; text-transform: uppercase;
    letter-spacing: .08em; color: var(--muted); }
.id-pick { font: inherit; font-size: 13.5px; max-width: min(100%, 460px);
    padding: 6px 10px; border: 1.5px solid var(--hair); border-radius: 6px;
    background: var(--bg); color: var(--fg); cursor: pointer; }
.id-pick:hover, .id-pick:focus { border-color: var(--accent); outline: none; }
.id-count { font-family: var(--mono); font-size: 11px; color: var(--muted); }
/* Ширину рамки задаём вместе с классом-родителем: общий стиль сайта обнуляет
   границу у button, и без этого кнопка темы выглядела простым текстом. */
.id-bar .id-chip { border: 1.5px solid var(--hair); border-radius: 5px;
    padding: 4px 10px; font-size: 12px; background: var(--bg); cursor: pointer;
    font-family: inherit; color: var(--fg); line-height: 1.4;
    transition: border-color .15s, background .15s; }
.id-bar .id-chip:first-letter { text-transform: uppercase; }
.id-bar .id-chip:hover { border-color: var(--accent); }
.id-bar .id-chip[aria-current="true"] { border-color: var(--accent);
    background: var(--surface); font-weight: 600; }
/* Пласты тем. Ряд из девяноста кнопок подряд читается как свалка; разложенный
   по происхождению — как оглавление, и заодно отвечает на вопрос «откуда это». */
.id-glab { flex: 0 0 100%; margin: 6px 0 0; font-family: var(--mono); font-size: 10.5px;
    text-transform: uppercase; letter-spacing: .08em; color: var(--muted); }
.id-glab:first-child { margin-top: 0; }
.id-topic { margin: 20px 0 0; }
.id-topic h2 { font-family: var(--serif); font-size: 20px; margin: 0 0 3px; }
.id-topic h2::first-letter { text-transform: uppercase; }
.id-tnote { color: var(--soft); font-size: 12.5px; line-height: 1.5; max-width: 68ch; }
/* СПИСОК ИДЕЙ — КАРТОЧКАМИ, как список статей. Раньше вся идея вываливалась
   целиком: девять полей подряд, и пять идей подряд читались как простыня. Читатель
   выбирает по названию и одной строке сути, а разворачивает то, что выбрал. */
.id-list { display: grid; gap: 10px; margin: 12px 0 0; }
.id-brief { border: 1.5px solid var(--hair); border-radius: 6px; padding: 11px 14px;
    background: var(--bg); cursor: pointer; transition: border-color .15s; }
.id-brief:hover { border-color: var(--accent); }
.id-brief h3 { font-family: var(--serif); font-size: 16px; margin: 0 0 3px;
    line-height: 1.3; }
.id-brief p { margin: 3px 0 0; font-size: 13px; color: var(--soft); line-height: 1.5; }
.id-brief .id-scale { margin-right: 8px; }
.id-open { margin: 8px 0 0; font-size: 12px; color: var(--muted); }

/* Работы, на которых стоит идея, — теми же карточками, что в ленте. Ссылка списком
   номеров требовала от читателя доверия; карточка показывает, на чём идея стоит. */
.id-srccards { display: grid; gap: 10px; margin: 10px 0 0; }
.id-card-art { display: grid; grid-template-columns: 74px 1fr; gap: 12px;
    align-items: start; text-decoration: none; color: inherit;
    border: 1px solid var(--hair); border-radius: 6px; padding: 9px 11px;
    background: var(--bg); transition: border-color .15s; }
.id-card-art:hover { border-color: var(--accent); }
.id-card-art:not(:has(.id-cimg)) { grid-template-columns: 1fr; }
.id-cimg { width: 74px; height: 74px; object-fit: cover; border-radius: 4px; }
.id-ctext { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.id-ctext b { font-family: var(--serif); font-size: 14.5px; font-weight: 600;
    line-height: 1.3; }
.id-ctext i { font-style: normal; font-size: 12.5px; color: var(--soft);
    line-height: 1.45; }
.id-ctext u { text-decoration: none; font-family: var(--mono); font-size: 10.5px;
    color: var(--muted); }
.id-srchead { font-size: 11.5px; font-family: var(--mono); text-transform: uppercase;
    letter-spacing: .08em; color: var(--muted); margin: 14px 0 0; }
.id-back { font: inherit; font-size: 13px; background: transparent; cursor: pointer;
    border: 1px solid var(--hair); border-radius: 999px; padding: 3px 12px;
    color: var(--soft); margin-bottom: 12px; }
.id-back:hover { color: var(--fg); border-color: var(--fg); }
.id-card { border: 1.5px solid var(--hair); border-radius: 6px; padding: 12px 14px;
    background: var(--bg); }
.id-card h3 { font-family: var(--serif); font-size: 16.5px; margin: 0 0 2px;
    line-height: 1.3; }
.id-scale { font-family: var(--mono); font-size: 10.5px; border: 1px solid var(--hair);
    border-radius: 3px; padding: 1px 6px; color: var(--muted); }
.id-f { margin: 8px 0 0; font-size: 13px; line-height: 1.55; }
.id-f b { display: block; font-size: 10.5px; font-family: var(--mono);
    text-transform: uppercase; letter-spacing: .04em; color: var(--muted);
    font-weight: 500; margin-bottom: 1px; }
.id-f ul { margin: 2px 0 0; padding-left: 18px; }
.id-f li { margin: 2px 0; }
.id-src { margin: 10px 0 0; display: flex; flex-wrap: wrap; gap: 6px; }
.id-src a { font-family: var(--mono); font-size: 11px; text-decoration: none;
    border: 1px solid var(--hair); border-radius: 3px; padding: 2px 7px;
    color: var(--fg); }
.id-src a[data-k="field"] { border-style: dashed; color: var(--muted); }
.id-empty { color: var(--muted); font-size: 13px; margin: 18px 0; }
@media (max-width: 700px) { .id-head h1 { font-size: 23px; } }
"""

JS = """
(function () {
  var LANG = (new URLSearchParams(location.search).get("lang") || "").slice(0, 2)
    || document.documentElement.lang || "ru";
  var T = __T__, D = T[LANG] || T.ru;
  var box = document.getElementById("id-body"), bar = document.getElementById("id-bar");
  /* ШАПКА НА ЯЗЫКЕ ЧИТАТЕЛЯ. Разметка собирается по-русски (страница одна на все
     языки, как /research.html), поэтому подписи ставит скрипт. Арабский вдобавок
     разворачивает страницу: читать слева направо он не станет. */
  document.documentElement.lang = LANG;
  document.documentElement.dir = (LANG === "ar") ? "rtl" : "ltr";
  var set = function (id, txt) {
    var el = document.getElementById(id);
    if (el) el.textContent = txt;
  };
  set("id-title", D.title);
  set("id-sub", D.sub);
  set("id-note", D.note);
  document.title = D.title + " — bridge42worlds";
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c];
    });
  }
  /* Запись хранит русский в корне, остальные языки — в ветке lang. Нет перевода —
     показываем русский: полупустая страница хуже, чем страница на другом языке. */
  function pick(rec) {
    if (LANG === "ru") {
      return {ideas: rec.ideas || [], note: rec.note || "", topic: rec.topic};
    }
    var l = (rec.lang || {})[LANG];
    return l ? {ideas: l.ideas || [], note: l.note || "", topic: l.topic || rec.topic}
             : {ideas: rec.ideas || [], note: rec.note || "", topic: rec.topic};
  }
  function srcEl(id, sources) {
    var s = (sources || []).filter(function (x) { return x.id === id; })[0] || {};
    var ours = !s.field;
    /* Адрес разбора записан с местом под язык: одна статья живёт на пяти языках,
       и вести читателя надо на его. Адреса нет — ведём в поиск по номеру. */
    var href = ours
      ? (s.url ? s.url.replace("{lang}", LANG)
               : "/lang/" + LANG + "/search.html?q=" + encodeURIComponent(id))
      : ("https://arxiv.org/abs/" + id);
    return '<a href="' + esc(href) + '" data-k="' + (ours ? "ours" : "field") + '"' +
      (ours ? "" : ' target="_blank" rel="noopener"') +
      ' title="' + esc(ours ? D.ours : D.field) + '">' + esc(id) + "</a>";
  }
  /* КАРТОЧКА ИДЕИ В СПИСКЕ. Название, масштаб и одна строка сути — ровно столько,
     сколько нужно, чтобы выбрать. Всё остальное открывается по нажатию. */
  /* СУТЬ В СПИСКЕ. Резали по первой точке — и обрывались на «E. coli», «B. subtilis»,
     «т. д.»: сокращение с точкой выглядит концом предложения, а мысль остаётся
     недосказанной (владелец 01.09: «иногда обрезана суть идеи»). Берём до двухсот
     знаков и режем по границе слова, а не по первой попавшейся точке. */
  function brief_what(t) {
    t = String(t || "").trim();
    if (t.length <= 200) return t;
    var cut = t.slice(0, 200), i = cut.lastIndexOf(" ");
    return (i > 120 ? cut.slice(0, i) : cut) + "…";
  }

  function brief(x, i) {
    return '<article class="id-brief" data-i="' + i + '">' +
      "<h3>" + esc(x.title) + "</h3>" +
      (x.scale ? '<span class="id-scale">' + esc(x.scale) + "</span>" : "") +
      "<p>" + esc(brief_what(x.what)) + "</p>" +
      '<p class="id-open">' + esc(D.open) + "</p></article>";
  }

  function srcEl(id, sources) {
    var s = (sources || []).filter(function (x) { return x.id === id; })[0] || {};
    var ours = !s.field;
    var href = ours
      ? (s.url ? s.url.replace("{lang}", LANG)
               : "/lang/" + LANG + "/search.html?q=" + encodeURIComponent(id))
      : ("https://arxiv.org/abs/" + id);
    return '<a href="' + esc(href) + '" data-k="' + (ours ? "ours" : "field") + '"' +
      (ours ? "" : ' target="_blank" rel="noopener"') +
      ' title="' + esc(ours ? D.ours : D.field) + '">' + esc(id) + "</a>";
  }

  /* ПОЛНАЯ ИДЕЯ. Здесь и появляются работы — настоящими карточками, теми же, что
     в ленте: ссылка списком номеров требовала от читателя доверия, карточка
     показывает, на чём идея стоит. Наши разборы приходят из облака одним запросом;
     работы поля карточек не имеют — их мы не разбирали, — и остаются ссылкой. */
  function full(x, rec, i) {
    var f = function (key, val) {
      if (!val) return "";
      return '<div class="id-f"><b>' + esc(D[key]) + "</b>" + val + "</div>";
    };
    var methods = (x.methods || []).length
      ? "<ul>" + x.methods.map(function (m) { return "<li>" + esc(m) + "</li>"; }).join("") + "</ul>"
      : "";
    var key = "idea:" + (rec.key || rec.slug) + "-" + i;
    return '<article class="id-card" data-article-id="' + esc(key) + '" ' +
      'data-entity-type="idea">' +
      "<h3>" + esc(x.title) + "</h3>" +
      (x.scale ? '<span class="id-scale">' + esc(x.scale) + "</span>" : "") +
      f("what", esc(x.what)) + f("why", esc(x.why)) + f("methods", methods) +
      f("origin", esc(x.origin)) + f("first", esc(x.first_step)) +
      f("needs", esc(x.needs)) + f("risks", esc(x.risks)) +
      '<div class="id-srchead">' + esc(D.based) + "</div>" +
      '<div class="id-src">' +
      (x.based_on || []).map(function (id) { return srcEl(id, rec.sources); }).join("") +
      '</div><div class="id-srccards"></div>' +
      /* Отклик — той же разметкой, что у статьи: js/likes.js цепляется за
         .feedback, data-article-id и data-entity-type, и своего кода здесь не
         нужно. Тип сущности «idea» ручка принимает как есть — она не знает
         заранее, о чём пишут. */
      '<div class="feedback" data-article-id="' + esc(key) + '" ' +
      'data-entity-type="idea">' +
      '<div class="fb-react">' +
      '<button type="button" class="fb-r" data-react="like" aria-label="' +
      esc(D.like) + '">&#9825;</button>' +
      '<button type="button" class="fb-r" data-react="dislike" aria-label="' +
      esc(D.dislike) + '">&#8595;</button>' +
      '<button type="button" class="fb-comment-toggle">' + esc(D.comment) +
      "</button></div>" +
      '<div class="fb-expand" hidden>' +
      '<textarea class="fb-comment" rows="2" placeholder="' + esc(D.commentHint) +
      '"></textarea>' +
      '<div class="fb-row"><button class="fb-send">' + esc(D.send) + "</button></div>" +
      '</div><span class="fb-status"></span>' +
      "</div></article>";
  }

  /* Карточки наших работ под идеей. Один запрос на идею, только за теми, что мы
     разбирали: у работ поля карточек нет и быть не может. */
  function drawSources(box, rec, x) {
    var ours = (x.based_on || []).filter(function (id) {
      return (rec.sources || []).some(function (s) { return s.id === id && !s.field; });
    });
    if (!ours.length) return;
    fetch("/api/cards?ids=" + encodeURIComponent(ours.join(",")) +
          "&lang=" + LANG + "&version=popular")
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        var items = (d && (d.items || d.cards)) || [];
        if (!items.length) return;
        /* Карточку рисуем свою, а не тянем js/search.js: там 176 килобайт и своя
           жизнь — он строит ленту, ищет контейнеры и сам решает, что показать.
           Здесь нужны четыре поля: обложка, заголовок, одна строка сути, дата. */
        box.innerHTML = items.map(function (a) {
          /* В карточке облака поле image — ПРИЗНАК «обложка есть», а не адрес: там
             true/false. Мы подставляли его в src, браузер шёл за картинкой «true»
             и получал 404 (владелец 01.09: «нет картинки у карточки»). Адрес
             собираем сами из адреса статьи — миниатюра лежит рядом с ней. */
          var thumb = a.image && a.url
            ? a.url.replace(/[^/]*$/, "") + "t_ai.webp" : "";
          var img = thumb
            ? '<img class="id-cimg" src="' + esc(thumb) + '" alt="" loading="lazy">' : "";
          return '<a class="id-card-art" href="' + esc(a.url || "#") + '">' + img +
            '<span class="id-ctext"><b>' + esc(a.title || a.id) + "</b>" +
            (a.oneliner ? "<i>" + esc(a.oneliner) + "</i>" : "") +
            '<u>' + esc(a.date || "") +
            (a.express ? " · " + esc(D.expressMark) : "") + "</u></span></a>";
        }).join("");
      }).catch(function () {});
  }

  /* АДРЕС — ЧАСТЬ СТРАНИЦЫ. Идея, на которую нельзя дать ссылку, живёт только у
     того, кто её нашёл. Тема пишется в адрес как #тема, идея — как #тема/2:
     «назад» браузера начинает работать сам собой, ссылка на идею открывает именно
     её, а не первую тему списка. */
  var CUR = null, CACHE = {}, IDX = {}, TOPICS = [];

  function draw(rec) {
    CUR = rec;
    var got = pick(rec);
    box.innerHTML = '<section class="id-topic"><h2>' + esc(got.topic || rec.topic) + "</h2>" +
      (got.note ? '<p class="id-tnote">' + esc(got.note) + "</p>" : "") +
      '<div class="id-list">' +
      got.ideas.map(function (x, i) { return brief(x, i); }).join("") +
      "</div></section>";
    document.title = (got.topic || rec.topic) + " — " + D.title;
  }

  function openIdea(i) {
    var got = pick(CUR);
    var x = got.ideas[i];
    if (!x) { draw(CUR); return; }
    box.innerHTML = '<section class="id-topic">' +
      '<button type="button" class="id-back">&larr; ' + esc(got.topic || CUR.topic) +
      "</button>" + full(x, CUR, i) + "</section>";
    drawSources(box.querySelector(".id-srccards"), CUR, x);
    document.title = x.title + " — " + D.title;
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function mark(slug) {
    var sel = bar.querySelector(".id-pick");
    if (sel && sel.value !== slug) sel.value = slug;
  }

  function load(slug) {
    if (CACHE[slug]) return Promise.resolve(CACHE[slug]);
    /* Ломоть имени файла кириллический — в адресе его надо кодировать, иначе запрос
       уходит битым на части клиентов. */
    return fetch("/data/ideas/" + encodeURIComponent(slug) + ".json", {cache: "no-store"})
      .then(function (r) { return r.json(); })
      .then(function (rec) {
        rec.slug = rec.slug || slug;
        rec.key = (IDX[slug] || {}).key || rec.slug;
        CACHE[slug] = rec;
        return rec;
      });
  }

  function route() {
    var h = decodeURIComponent(String(location.hash || "").replace(/^#/, ""));
    var part = h.split("/");
    var slug = IDX[part[0]] ? part[0] : (TOPICS[0] || {}).slug;
    if (!slug) return;
    mark(slug);
    load(slug).then(function (rec) {
      if (part[1] !== undefined && part[1] !== "") openIdea(+part[1]);
      else draw(rec);
    }).catch(function () {
      box.innerHTML = '<p class="id-empty">' + esc(D.none) + "</p>";
    });
  }
  window.addEventListener("hashchange", route);

  box.addEventListener("click", function (e) {
    var b = e.target.closest(".id-brief");
    if (b) {
      location.hash = "#" + encodeURIComponent(CUR.slug) + "/" + b.dataset.i;
      return;
    }
    if (e.target.closest(".id-back")) {
      location.hash = "#" + encodeURIComponent(CUR.slug);
    }
  });

  fetch("/data/ideas/index.json", {cache: "no-store"}).then(function (r) {
    return r.ok ? r.json() : null;
  }).then(function (idx) {
    if (!idx || !idx.topics || !idx.topics.length) {
      box.innerHTML = '<p class="id-empty">' + esc(D.none) + "</p>";
      return;
    }
    TOPICS = idx.topics;
    var ORDER = ["applied", "core", "area", "demand", ""];
    var byOrigin = {};
    TOPICS.forEach(function (t) {
      IDX[t.slug] = t;
      var k = ORDER.indexOf(t.origin || "") >= 0 ? (t.origin || "") : "";
      (byOrigin[k] = byOrigin[k] || []).push(t);
    });
    var lbl = document.createElement("span");
    lbl.className = "id-picklbl";
    lbl.textContent = D.pickLbl;
    bar.appendChild(lbl);

    var sel = document.createElement("select");
    sel.className = "id-pick";
    sel.setAttribute("aria-label", D.pickLbl);
    ORDER.forEach(function (k) {
      if (!byOrigin[k]) return;
      /* Пласты остаются: они становятся группами внутри списка, и человек по-прежнему
         видит, откуда тема — рука, область машины знаний или её спрос. */
      var box = document.createElement("optgroup");
      box.label = (D.origins && D.origins[k]) || "";
      byOrigin[k].forEach(function (t) {
        var o = document.createElement("option");
        o.value = t.slug;
        o.textContent = ((t.titles && t.titles[LANG]) || t.topic) + " · " + t.n;
        box.appendChild(o);
      });
      sel.appendChild(box);
    });
    sel.onchange = function () {
      var want = "#" + encodeURIComponent(sel.value);
      if (location.hash === want) route(); else location.hash = want;
    };
    bar.appendChild(sel);

    var cnt = document.createElement("span");
    cnt.className = "id-count";
    cnt.textContent = TOPICS.length + " · " +
      TOPICS.reduce(function (a, t) { return a + (t.n || 0); }, 0);
    bar.appendChild(cnt);
    route();
  }).catch(function () {
    box.innerHTML = '<p class="id-empty">' + esc(D.none) + "</p>";
  });
})();
"""


def _origins():
    """Слой → откуда тема. Список тем собирает tools/idea_topics.py из четырёх
    пластов; странице это нужно, чтобы не валить в один ряд «опреснение морской
    воды» и «квантовая информатика»: первое просил читатель, второе машина знаний
    нашла сама."""
    src = ROOT / "data" / "idea-topics.json"
    if not src.exists():
        return {}
    import re as _re
    out = {}
    for r in json.loads(src.read_text(encoding="utf-8")).get("topics", []):
        t = _re.sub(r"[^\w\s-]", "", str(r.get("topic", "")).lower(), flags=_re.U)
        out[_re.sub(r"[\s_]+", "-", t).strip("-")[:60]] = r.get("origin") or ""
    return out


def build_index():
    """Опись тем — маленький файл, чтобы страница не тянула все наборы разом."""
    topics = []
    origins = _origins()
    for p in sorted(SRC.glob("*.json")):
        if p.name == "index.json":
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not d.get("ideas"):
            continue
        titles = {}
        for lang in LANGS[1:]:
            l = (d.get("lang") or {}).get(lang)
            # Имя темы на другом языке берём из перевода первой идеи, только если
            # перевод есть: выдумывать название темы нам нечем.
            if l and l.get("topic"):
                titles[lang] = l["topic"]
        # КЛЮЧ ОТКЛИКА — короткий. Ручка /api/react режет опознаватель на 60 знаках,
        # а кириллический ломоть темы уже упирался в эту границу («охлаждение-
        # фотоэлектрических-модулей-в-жарком-климате» — ровно 60 с номером идеи).
        # Ещё одна буква в названии — и номер идеи отрезало бы молча: лайки всех идей
        # темы слились бы в один. Восемь знаков от хеша ломтя устойчивы к пересборке.
        slug = d.get("slug") or p.stem
        topics.append({"slug": slug, "topic": d.get("topic") or p.stem,
                       "key": hashlib.sha1(slug.encode("utf-8")).hexdigest()[:8],
                       "n": len(d["ideas"]), "titles": titles,
                       "origin": origins.get(slug, ""),
                       "sources": len(d.get("sources") or [])})
    INDEX.write_text(json.dumps({"topics": topics}, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    return topics


def main():
    if not SRC.exists():
        print("data/ideas/ ещё нет — сначала tools/ideas.py --topics data/idea-topics.txt")
        return 1
    topics = build_index()
    d = T["ru"]
    # ШАПКА ОБЩАЯ, А НЕ СВОЯ. Была своя из логотипа и кнопки темы: ни поиска, ни
    # избранного, ни разделов, ни языков — и один значок приезжал нулевого размера
    # (владелец 01.09: «иконки поехавшие»). Общая шапка вырезается из живого шаблона
    # тем же кодом, что у страниц понятий, и разъехаться с сайтом уже не может.
    import sys as _sys
    _sys.path.insert(0, str(ROOT))
    from concepts_pages import site_chrome as _chrome_of
    _chrome = _chrome_of("ru")[0]
    html = f"""<!DOCTYPE html>
<html lang="ru" dir="ltr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{d['title']} — bridge42worlds</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:opsz@14..32&family=Source+Serif+4:opsz@8..60&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/css/style.css">
<link rel="icon" href="/favicon.ico" sizes="any">
<style>{CSS}</style>
</head>
<body>

{_chrome}

<div class="id-head">
  <h1 id="id-title">{d['title']}</h1>
  <div class="id-sub" id="id-sub">{d['sub']}</div>
  <p class="id-note" id="id-note">{d['note']}</p>
</div>

<div class="id-bar" id="id-bar"></div>
<div id="id-body"></div>

<script src="/js/icons.js"></script>
<script src="/js/sitenav.js"></script>
<script src="/js/likes.js"></script>
<script src="/js/search-ui.js"></script>
<script src="/js/site-search.js"></script>
<script src="/js/search.js"></script>
<script src="/js/b42-card.js"></script>
<script>{JS.replace('__T__', json.dumps(T, ensure_ascii=False))}</script>
</body>
</html>
"""
    OUT.write_text(html, encoding="utf-8")
    print(f"✅ {OUT.name}: тем {len(topics)}, идей "
          f"{sum(t['n'] for t in topics)} · опись {INDEX.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
