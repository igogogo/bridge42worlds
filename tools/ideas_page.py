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
    "ru": {"title": "Идеи проектов", "sub": "За что можно взяться — с опорой на работы",
           "none": "Идей пока нет", "scale": "масштаб", "what": "что делаем",
           "why": "зачем", "methods": "как", "first": "первый шаг", "needs": "что нужно",
           "risks": "где споткнётся", "origin": "почему мы это предлагаем",
           "based": "опора", "ours": "наш разбор", "field": "работа arXiv, не разобрана",
           "topics": "Области", "note": "Каждая идея обязана опираться на конкретные "
           "работы, и они названы. Идея без опоры — красивые слова, их и без нас много."},
    "en": {"title": "Project ideas", "sub": "Things you can take on — grounded in papers",
           "none": "No ideas yet", "scale": "scale", "what": "what to do",
           "why": "why", "methods": "how", "first": "first step", "needs": "what you need",
           "risks": "where it stumbles", "origin": "why we suggest it",
           "based": "grounded in", "ours": "our analysis", "field": "arXiv paper, not analysed",
           "topics": "Areas", "note": "Every idea must rest on named papers. "
           "An idea without grounding is just words, and there are plenty of those."},
    "es": {"title": "Ideas de proyectos", "sub": "Qué se puede emprender, apoyado en trabajos",
           "none": "Aún no hay ideas", "scale": "escala", "what": "qué hacer",
           "why": "para qué", "methods": "cómo", "first": "primer paso", "needs": "qué hace falta",
           "risks": "dónde tropezará", "origin": "por qué lo proponemos",
           "based": "apoyo", "ours": "nuestro análisis", "field": "trabajo de arXiv, sin analizar",
           "topics": "Áreas", "note": "Cada idea debe apoyarse en trabajos concretos, y están "
           "nombrados. Una idea sin apoyo son solo palabras, y de esas sobran."},
    "ar": {"title": "أفكار مشاريع", "sub": "ما يمكن الشروع فيه، مستنداً إلى أبحاث",
           "none": "لا توجد أفكار بعد", "scale": "الحجم", "what": "ماذا نفعل",
           "why": "لماذا", "methods": "كيف", "first": "الخطوة الأولى", "needs": "ما يلزم",
           "risks": "أين قد يتعثّر", "origin": "لماذا نقترح ذلك",
           "based": "الاستناد", "ours": "تحليلنا", "field": "بحث في arXiv، لم نحلّله",
           "topics": "المجالات", "note": "كل فكرة يجب أن تستند إلى أبحاث محددة، وهي مذكورة. "
           "الفكرة بلا استناد مجرد كلام، والكلام كثير."},
    "fr": {"title": "Idées de projets", "sub": "Ce qu’on peut entreprendre, appuyé sur des travaux",
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
.id-bar { display: flex; flex-wrap: wrap; gap: 6px; margin: 14px 0 0;
    padding: 10px 0; border-top: 1px solid var(--hair);
    border-bottom: 1px solid var(--hair); }
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
.id-topic { margin: 20px 0 0; }
.id-topic h2 { font-family: var(--serif); font-size: 20px; margin: 0 0 3px; }
.id-topic h2::first-letter { text-transform: uppercase; }
.id-tnote { color: var(--soft); font-size: 12.5px; line-height: 1.5; max-width: 68ch; }
.id-list { display: grid; gap: 12px; margin: 12px 0 0; }
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
    if (LANG === "ru") return {ideas: rec.ideas || [], note: rec.note || ""};
    var l = (rec.lang || {})[LANG];
    return l ? {ideas: l.ideas || [], note: l.note || ""}
             : {ideas: rec.ideas || [], note: rec.note || ""};
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
  function card(x, sources) {
    var f = function (key, val) {
      if (!val) return "";
      return '<div class="id-f"><b>' + esc(D[key]) + "</b>" + val + "</div>";
    };
    var methods = (x.methods || []).length
      ? "<ul>" + x.methods.map(function (m) { return "<li>" + esc(m) + "</li>"; }).join("") + "</ul>"
      : "";
    return '<article class="id-card">' +
      "<h3>" + esc(x.title) + "</h3>" +
      (x.scale ? '<span class="id-scale">' + esc(x.scale) + "</span>" : "") +
      f("what", esc(x.what)) + f("why", esc(x.why)) + f("methods", methods) +
      f("origin", esc(x.origin)) + f("first", esc(x.first_step)) +
      f("needs", esc(x.needs)) + f("risks", esc(x.risks)) +
      '<div class="id-src">' +
      (x.based_on || []).map(function (id) { return srcEl(id, sources); }).join("") +
      "</div></article>";
  }
  function draw(rec) {
    var got = pick(rec);
    box.innerHTML = '<section class="id-topic"><h2>' + esc(rec.topic) + "</h2>" +
      (got.note ? '<p class="id-tnote">' + esc(got.note) + "</p>" : "") +
      '<div class="id-list">' +
      got.ideas.map(function (x) { return card(x, rec.sources); }).join("") +
      "</div></section>";
    document.title = rec.topic + " — " + D.title;
  }
  fetch("/data/ideas/index.json", {cache: "no-store"}).then(function (r) {
    return r.ok ? r.json() : null;
  }).then(function (idx) {
    if (!idx || !idx.topics || !idx.topics.length) {
      box.innerHTML = '<p class="id-empty">' + esc(D.none) + "</p>";
      return;
    }
    idx.topics.forEach(function (t, i) {
      var b = document.createElement("button");
      b.className = "id-chip";
      b.type = "button";
      b.textContent = (t.titles && t.titles[LANG]) || t.topic;
      b.onclick = function () {
        Array.prototype.forEach.call(bar.children, function (c) {
          c.removeAttribute("aria-current");
        });
        b.setAttribute("aria-current", "true");
        /* Ломоть имени файла кириллический — в адресе его надо кодировать,
           иначе запрос уходит битым на части клиентов. */
        fetch("/data/ideas/" + encodeURIComponent(t.slug) + ".json", {cache: "no-store"})
          .then(function (r) { return r.json(); }).then(draw);
      };
      bar.appendChild(b);
      if (i === 0) b.click();
    });
  }).catch(function () {
    box.innerHTML = '<p class="id-empty">' + esc(D.none) + "</p>";
  });
})();
"""


def build_index():
    """Опись тем — маленький файл, чтобы страница не тянула все наборы разом."""
    topics = []
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
        topics.append({"slug": d.get("slug") or p.stem, "topic": d.get("topic") or p.stem,
                       "n": len(d["ideas"]), "titles": titles,
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

<div class="id-head">
  <h1 id="id-title">{d['title']}</h1>
  <div class="id-sub" id="id-sub">{d['sub']}</div>
  <p class="id-note" id="id-note">{d['note']}</p>
</div>

<div class="id-bar" id="id-bar"></div>
<div id="id-body"></div>

<script src="/js/icons.js"></script>
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
