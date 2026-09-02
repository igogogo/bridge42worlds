# -*- coding: utf-8 -*-
"""Схема конвейера — живая: лампочки статусов, история прогонов, ошибки, план.

Владелец 28.08: «сделай покомпактнее и подинамичнее, как потоковая диаграмма с
лампочками статусов; чтобы можно было смотреть по разным датам, ошибки видеть,
зашёл — и историю увидел, и проблемы, и текущее состояние, и что запланировано».

Прежняя страница была подробной статичной картой: тридцать три узла с описаниями
и пометкой «пока схема статичная». Описания сохранены (data/pipeline-nodes.json,
извлечены из той разметки) и живут теперь в подсказках, а сама схема ужалась до
потока лампочек — на экран помещается весь цикл разом.

ОТКУДА ДАННЫЕ. tools/full_run.py пишет журнал data/pipeline-runs.json: по записи
на прогон — что запланировано, что прошло, что идёт, что упало, сколько заняло.
Страница читает журнал и красит; журнала нет — показывает честную заглушку, а не
выдуманные зелёные лампочки.

ПОЧЕМУ ФАЗЫ ЗАШИТЫ ЗДЕСЬ, А ШАГИ — НЕТ. Шаги берутся из журнала: цепочка меняется,
и страница не должна разъезжаться с ней. А раскладка по фазам — это про смысл, а
не про данные; неизвестный шаг попадает в «прочее» и остаётся видимым.

    python tools/pipeline_page.py        собрать /pipeline.html
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "pipeline.html"
NODES = ROOT / "data" / "pipeline-nodes.json"

# Фаза → какие шаги цепочки в неё входят. Порядок фаз — порядок работы.
PHASES = [
    ("Забор и разбор", "день с arXiv: отбор, тексты, обложки, переводы", ["day"]),
    ("Насыщение", "новые понятия из текстов, формулы, рождения, чистка",
     ["harvest", "anatomy", "flink", "match", "distill", "births", "g-grow",
      "f-support", "twins", "consts", "units-fix"]),
    ("Записи", "карточки, переводы, имена; разметка статей дня и доразметка архива",
     ["live-1", "cards", "tr-cards", "tr-formulas", "names-ru",
      "field", "retag-day", "hl-day", "retag", "apply"]),
    ("Связность", "суперпонятия, соседи, области, связи знанием, граф",
     ["super", "live-2", "vecnb", "live-3", "gnames", "gnames-tr", "weave", "live-4", "graph",
      "mentions-ru", "highlight"]),
    ("Пласты и идеи", "спрос машины знаний → работы из прошлого; идеи проектов",
     ["strata", "strata-gen", "ideas", "ideas-tr", "ideas-page"]),
    ("Сборка", "страницы понятий и формул, весь сайт, авторы, дашборд",
     ["pages-c", "pages-f", "related", "cited", "carousel", "fx", "html", "html-force", "authors", "status"]),
    ("Облако", "D1, векторы, карточки статей, выкладка воркера",
     ["cloud-d1", "cloud-vec", "cards-sync", "side-sync", "deploy"]),
    ("Проверка", "эндпоинты, страницы, аудиты, связность ссылок",
     ["api", "pages", "audit", "gaudit", "links"]),
]

# Шаг цепочки → узел прежней карты, чей текст объясняет, что здесь происходит.
EXPLAIN = {
    "harvest": "harvest", "match": "sift", "distill": "sift", "births": "birth",
    "consts": "consts", "g-grow": "stats", "f-support": "stats",
    "anatomy": "anatomy", "flink": "anatomy", "super": "super2", "live-2": "super2",
    "cards": "cards", "tr-cards": "cards", "retag": "retag", "apply": "reapply",
    "live-3": "reapply", "mentions-ru": "anchors", "highlight": "hl-model",
    "weave": "hl-vec", "gnames": "hl-dict", "pages-c": "pages", "pages-f": "pages",
    "html": "pages", "lang-pages": "pages", "graph": "data", "status": "dash", "authors": "dash",
    "cloud-d1": "d1", "cloud-vec": "vz", "deploy": "r2", "api": "watch",
    "pages": "watch", "links": "watch",
}

# Имя шага на схеме. Своё у каждого — прежняя карта давала одно описание на
# несколько шагов, и в ряду выходило «Формулы, Формулы», «Перегенерация,
# Перегенерация, Перегенерация». Подробное объяснение осталось в подсказке.
SHORT = {
    "harvest": "Добыча понятий", "anatomy": "Анатомия формул",
    "flink": "Привязка формул", "match": "Сверка кандидатов",
    "distill": "Дистилляция", "births": "Рождение понятий",
    "g-grow": "Дорост областей", "f-support": "Опора формул",
    "twins": "Двойники", "consts": "Константы из формул", "units-fix": "Единицы",
    "live-1": "В реестр ①", "live-2": "В реестр ②", "live-3": "В реестр ③",
    "live-4": "В реестр ④",
    "cards": "Полные карточки", "tr-cards": "Перевод карточек",
    "tr-formulas": "Перевод формул", "names-ru": "Имена по-русски",
    "field": "Вектор свежим статьям", "retag-day": "Разметка статей дня",
    "hl-day": "Подсветка статей дня",
    "retag": "Доразметка статей", "apply": "Применение разметки",
    "super": "Суперпонятия", "vecnb": "Соседи вектором",
    "gnames": "Имена областей", "gnames-tr": "Перевод областей", "weave": "Связи знанием",
    "graph": "Экспорт графа", "mentions-ru": "Упоминания",
    "highlight": "Подсветка терминов",
    "pages-c": "Страницы понятий", "pages-f": "Страницы формул",
    "html": "Сборка сайта", "html-force": "Полная пересборка",
    "lang-pages": "Верхние страницы по языкам",
    "strata": "Пласты: поиск в прошлом", "strata-gen": "Разборы из прошлого",
    "uplift": "Дотяжка «Популярно»", "upgrade": "Доращивание по заявкам", "recommend": "Рекомендации автору", "rec-links": "Связи рекомендаций",
    "idea-topics": "Темы для идей", "ideas": "Идеи проектов", "ideas-tr": "Перевод идей",
    "ideas-page": "Страница идей", "authors": "Страницы авторов", "status": "Дашборд",
    "cloud-d1": "Заливка D1", "cloud-vec": "Векторы в облако",
    "cards-sync": "Карточки статей в D1", "side-sync": "Обвязка статей в D1",
    "related": "Похожие по смыслу", "cited": "Цитатные связи",
    "carousel": "Кадры карусели", "fx": "Формулы в тексте", "deploy": "Выкладка воркера",
    "api": "Проверка API", "pages": "Проверка страниц",
    "audit": "Аудит понятий", "gaudit": "Аудит областей", "links": "Проверка ссылок",
}

CSS = """
/* СТАТУС ЧИТАЕТСЯ БЕЗ ЦВЕТА. Владелец 28.08: «я дальтоник, для меня лучше
   квадратики, в них надписи и статус значком или штриховкой». Поэтому каждый
   шаг — прямоугольник с именем, а состояние отличается ЗНАКОМ и РИСУНКОМ рамки:
   сплошная с галочкой — прошло; штриховка по диагонали с восклицанием — сбой;
   пунктир с двойной стрелкой и пульсом — идёт; светлая точечная с точкой —
   впереди. Цвет остаётся, но он вторая подсказка, а не единственная. */
:root { --ok: #1f9d76; --run: #c8892a; --fail: #c0392b; --wait: #b9b2a6; }
body { max-width: 1100px; padding-bottom: 70px; }
.pp-head h1 { font-size: 25px; margin: 24px 0 4px; }
.pp-sub { color: var(--soft); font-size: 13.5px; max-width: 74ch; line-height: 1.55; }
.pp-bar { display: flex; flex-wrap: wrap; gap: 10px 16px; align-items: center;
    margin: 16px 0 6px; font-family: var(--mono); font-size: 12px; }
.pp-bar select { font-family: var(--mono); font-size: 12px; padding: 4px 8px;
    border: 1px solid var(--hair); border-radius: 6px; background: var(--bg);
    color: var(--fg); }
.pp-now { color: var(--muted); }
.pp-now b { color: var(--fg); font-weight: 600; }
.pp-legend { display: flex; gap: 12px; flex-wrap: wrap; margin-left: auto;
    color: var(--muted); }
.pp-legend span { display: inline-flex; align-items: center; gap: 5px; }
.pp-legend i { width: 16px; height: 16px; display: inline-grid; place-items: center;
    font-size: 10px; font-style: normal; border-radius: 3px; }

.pp-flow { margin: 14px 0 0; }
.pp-phase { display: grid; grid-template-columns: 175px 1fr; gap: 12px;
    padding: 10px 0; border-top: 1px solid var(--hair); align-items: start; }
.pp-phase:last-child { border-bottom: 1px solid var(--hair); }
.pp-pname { font-family: var(--serif); font-size: 14.5px; line-height: 1.3; }
.pp-pdesc { color: var(--soft); font-size: 11.5px; line-height: 1.4; margin-top: 2px; }
.pp-steps { display: flex; flex-wrap: wrap; gap: 7px; }

/* Квадратик шага: имя, знак статуса, под ними — время и итог. */
.pp-step { position: relative; min-width: 132px; max-width: 208px; flex: 0 1 auto;
    border: 1.5px solid var(--hair); border-radius: 5px; padding: 6px 9px 6px 24px;
    background: var(--bg); font-size: 11.5px; line-height: 1.35; }
.pp-mark { position: absolute; left: 6px; top: 6px; width: 13px; height: 13px;
    display: grid; place-items: center; font-size: 10px; font-weight: 700;
    border-radius: 2px; font-family: var(--mono); }
.pp-name { display: block; font-weight: 500; }
.pp-meta { display: block; font-family: var(--mono); font-size: 10px;
    color: var(--muted); margin-top: 2px; }

/* СТРЕЛКИ МЕЖДУ ШАГАМИ. Раньше порядок читался только по тому, что плитки идут
   слева направо — а это догадка, а не изображение. Владелец 02.09: «чтобы пайплайн
   рисовался аккуратно со стрелочками». Стрелка — псевдоэлемент у каждой плитки,
   кроме последней в строке фазы: не лишние узлы в разметке и не ломается при
   переносе строки. Цветом не пользуемся (владелец дальтоник) — стрелка серая
   всегда, она про порядок, а не про состояние. */
.pp-flow .pp-steps { gap: 7px 16px; }        /* место под стрелку между плитками */
.pp-step { position: relative; }
.pp-step:not(:last-child)::after {
    content: ""; position: absolute; right: -14px; top: 50%;
    width: 10px; height: 1px; background: var(--muted); opacity: .55;
}
.pp-step:not(:last-child)::before {
    content: ""; position: absolute; right: -14px; top: 50%;
    margin-top: -3px; border: 3px solid transparent;
    border-left-color: var(--muted); border-right: 0; opacity: .55;
}
html[dir="rtl"] .pp-step:not(:last-child)::after,
html[dir="rtl"] .pp-step:not(:last-child)::before { right: auto; left: -7px; }
/* Происхождение прогона: по расписанию или руками. */
.pp-origin { border: 1px solid var(--hair); border-radius: 4px; padding: 1px 6px;
    font-size: 10.5px; color: var(--soft); margin-left: 6px; white-space: nowrap; }
.pp-out { display: block; font-size: 10.5px; color: var(--soft); margin-top: 3px;
    line-height: 1.35; }
/* Числа шага — то, ради чего он запускался. Моноширинные, чтобы столбик цифр
   читался сверху вниз, а не терялся в тексте итога. */
.pp-nums { display: block; margin-top: 3px; font-family: var(--mono);
    font-size: 10px; line-height: 1.45; }
.pp-nums b { font-weight: 700; }
.pp-nums span { color: var(--muted); }

/* Свод прогона: то же, но крупно и наверху — «что этот прогон сделал». */
.pp-totals { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 0; }
.pp-tot { border: 1.5px solid var(--hair); border-radius: 5px;
    padding: 6px 10px; background: var(--bg); }
.pp-tot b { display: block; font-family: var(--mono); font-size: 16px;
    line-height: 1.2; }
.pp-tot span { display: block; font-size: 10.5px; color: var(--soft);
    margin-top: 1px; }
.pp-kind { font-family: var(--mono); font-size: 10.5px; border-radius: 3px;
    padding: 1px 6px; border: 1px solid var(--hair); margin-right: 6px; }

.pp-step[data-s="empty"] { border-style: solid; border-color: var(--hair); }
.pp-step[data-s="empty"] .pp-mark { border: 1.5px solid var(--muted);
    color: var(--muted); }
.pp-step[data-s="done"] { border-style: solid; border-color: var(--ok); }
.pp-step[data-s="done"] .pp-mark { border: 1.5px solid var(--ok); color: var(--ok); }
.pp-step[data-s="fail"] { border-style: solid; border-color: var(--fail);
    background-image: repeating-linear-gradient(45deg,
        rgba(192,57,43,.10) 0 6px, transparent 6px 12px); }
.pp-step[data-s="fail"] .pp-mark { border: 1.5px solid var(--fail); color: var(--fail); }
.pp-step[data-s="run"] { border-style: dashed; border-color: var(--run);
    animation: pp-pulse 1.3s ease-in-out infinite; }
.pp-step[data-s="run"] .pp-mark { border: 1.5px solid var(--run); color: var(--run); }
.pp-step[data-s="wait"] { border-style: dotted; border-color: var(--wait); opacity: .72; }
.pp-step[data-s="wait"] .pp-mark { border: 1.5px dotted var(--wait); color: var(--wait); }
@keyframes pp-pulse { 0%,100% { opacity: 1; } 50% { opacity: .55; } }

.pp-fails { margin: 18px 0 0; border: 1.5px solid var(--fail); border-radius: 8px;
    padding: 10px 13px; font-size: 12.5px;
    background-image: repeating-linear-gradient(45deg,
        rgba(192,57,43,.07) 0 7px, transparent 7px 14px); }
.pp-fails h3 { margin: 0 0 6px; font-size: 13px; }
.pp-fails li { margin: 4px 0; }
.pp-fails code { font-size: 11px; color: var(--muted); }


/* ПАНЕЛЬ УПРАВЛЕНИЯ РАССЫЛКОЙ. Появляется ТОЛЬКО на рабочей машине: её данные
   отдаёт локальный сервер (tools/dev_server.py), а на публичном адресе такой
   ручки нет. Почты авторов на общедоступной странице показывать нельзя. */
.pp-panel { margin: 20px 0 0; border: 1px solid var(--hair); border-radius: 8px;
    padding: 16px 18px; background: var(--bg); }
.pp-panel h3 { margin: 0 0 4px; font-size: 14px; }
.pp-panel .pp-note { margin: 0 0 12px; }
.pp-tbl { width: 100%; border-collapse: collapse; font-size: 12px; font-family: var(--mono); }
.pp-tbl th { text-align: left; font-weight: 600; color: var(--soft);
    border-bottom: 1px solid var(--hair); padding: 4px 8px 7px; }
.pp-tbl td { padding: 6px 8px; border-bottom: 1px solid var(--hair); vertical-align: top; }
.pp-tbl tr.done td { opacity: .45; }
.pp-tbl .pp-mail { color: var(--muted); }
.pp-tbl button { font: inherit; font-size: 11px; padding: 2px 8px; cursor: pointer;
    border: 1px solid var(--hair); border-radius: 4px; background: var(--bg); color: var(--fg); }
.pp-act { display: flex; gap: 10px; align-items: center; margin: 14px 0 0; flex-wrap: wrap; }
.pp-send { font: inherit; font-size: 12px; font-family: var(--mono); padding: 7px 16px;
    border: 1.5px solid var(--ok); border-radius: 6px; background: var(--bg);
    color: var(--ok); cursor: pointer; }
.pp-send[disabled] { opacity: .4; cursor: not-allowed; }
.pp-tpl textarea { width: 100%; min-height: 260px; font-family: var(--mono); font-size: 11.5px;
    line-height: 1.5; padding: 10px; border: 1px solid var(--hair); border-radius: 6px;
    background: var(--bg); color: var(--fg); resize: vertical; }
.pp-tpl input[type=text] { width: 100%; font-family: var(--mono); font-size: 12px;
    padding: 6px 8px; border: 1px solid var(--hair); border-radius: 5px;
    background: var(--bg); color: var(--fg); margin: 0 0 8px; }
.pp-tabs { display: flex; gap: 6px; margin: 0 0 10px; }
.pp-tabs button.on { border-color: var(--run); color: var(--run); }
/* РАССЫЛКА АВТОРАМ. Числа — здесь и для всех; имена — во всплывающем окне и только
   на рабочей машине: страница публичная, она есть в карте сайта, и кому мы написали
   — не её дело. Подробности лежат в .jsonl, а .jsonl заливка в R2 не публикует. */
.pp-out { margin: 28px 0 0; padding-top: 18px; border-top: 1px solid var(--hair); }
.pp-out h2 { font-size: 16px; margin: 0 0 4px; }
.pp-out .pp-sub2 { color: var(--soft); font-size: 12.5px; max-width: 74ch;
    line-height: 1.55; margin: 0 0 12px; }
.pp-out-btn { margin-top: 12px; font: inherit; font-size: 12px; padding: 6px 12px;
    border: 1.5px solid var(--hair); border-radius: 6px; background: var(--bg);
    color: var(--fg); cursor: pointer; font-family: var(--mono); }
.pp-out-btn:hover { border-color: var(--run); }
.pp-modal { position: fixed; inset: 0; background: rgba(15,22,38,.45); z-index: 60;
    display: flex; align-items: center; justify-content: center; padding: 20px; }
.pp-modal-in { background: var(--bg); border: 1px solid var(--hair); border-radius: 10px;
    max-width: 780px; width: 100%; max-height: 82vh; overflow: auto; padding: 20px 22px; }
.pp-modal h3 { margin: 0 0 12px; font-size: 15px; }
.pp-modal table { width: 100%; border-collapse: collapse; font-size: 12px;
    font-family: var(--mono); }
.pp-modal th { text-align: left; font-weight: 600; color: var(--soft);
    border-bottom: 1px solid var(--hair); padding: 4px 8px 7px; }
.pp-modal td { padding: 6px 8px; border-bottom: 1px solid var(--hair); }
.pp-modal .pp-x { float: right; cursor: pointer; color: var(--soft); border: 0;
    background: none; font-size: 20px; line-height: 1; padding: 0 4px; }
.pp-note { color: var(--soft); font-size: 12px; line-height: 1.55; margin: 10px 0 0; }
.pp-hint { margin: 16px 0 0; font-size: 12px; color: var(--soft); line-height: 1.5; }
.pp-empty { margin: 22px 0; padding: 14px; border: 1px dashed var(--hair);
    border-radius: 8px; color: var(--soft); font-size: 13px; }
@media (max-width: 720px) {
  .pp-phase { grid-template-columns: 1fr; gap: 4px; }
  .pp-legend { margin-left: 0; }
  .pp-step { min-width: 0; flex: 1 1 100%; max-width: none; }
}
"""

JS = """
(function () {
  var PHASES = %PHASES%, EXPLAIN = %EXPLAIN%, SHORT = %SHORT%, NODES = %NODES%;
  /* Знак статуса — не цвет, а символ: его видно в любом зрении и в чёрно-белой
     распечатке. */
  var MARK = {done: "✓", fail: "!", run: "▶", wait: "·", empty: "○"};
  var WORD = {done: "прошло", fail: "сбой", run: "идёт", wait: "впереди",
              empty: "пусто"};
  var runs = [];
  /* Прогонов два и они разные: ежедневный ведёт новые статьи от arXiv до
     выкладки, недельный доразмечает весь архив на выросшем реестре. Старые
     записи журнала рода не знают — им отвечаем по признаку: есть дни, значит
     ежедневный. */
  function KIND_NAME(run) {
    var k = run.kind || ((run.days && run.days.length) ? "daily" : "weekly");
    return k === "weekly" ? "недельный" : "ежедневный";
  }

  function label(step) {
    if (step.indexOf("day-") === 0) return step.slice(4);
    if (SHORT[step]) return SHORT[step];
    var n = NODES[EXPLAIN[step] || step];
    return n ? n.t : step;
  }
  function tip(step, st) {
    var n = NODES[EXPLAIN[step] || step];
    var base = step.indexOf("day-") === 0
      ? "Забор и разбор дня " + step.slice(4)
      : (n ? (n.t + " — " + n.d + (n.n ? " · " + n.n : "")) : step);
    var extra = st && st.out && st.out.length ? String.fromCharCode(10, 10)
      + st.out.join(String.fromCharCode(10)) : "";
    return base + String.fromCharCode(10) + "(" + step + ")" + extra;
  }
  function secs(s) {
    if (s === undefined || s === null) return "";
    return s < 60 ? s + " с" : Math.floor(s / 60) + " м " + (s % 60) + " с";
  }
  /* ПУСТО — НЕ СБОЙ. День, за который arXiv ничего не объявил (выходной, лаг
     объявления пятничных работ), проходит правильно и не приносит ничего. Красная
     лампочка тут врёт дважды: пугает и делает «прогон без ошибок» недостижимым по
     календарю. Отдельный знак — кружок. */
  function stateOf(run, step) {
    var info = (run.steps || {})[step] || {};
    if (info.empty) return "empty";
    if ((run.failed || []).indexOf(step) >= 0) return "fail";
    if (run.current === step) return "run";
    if ((run.done || []).indexOf(step) >= 0) return "done";
    return "wait";
  }

  function stepEl(step, run) {
    var s = stateOf(run, step);
    var info = (run.steps || {})[step] || {};
    var el = document.createElement("div");
    el.className = "pp-step";
    el.dataset.s = s;
    el.title = tip(step, info);
    var meta = [];
    if (info.started) meta.push(info.started + (info.finished ? "–" + info.finished : "…"));
    var t = info.secs !== undefined ? info.secs : (run.secs || {})[step];
    if (t !== undefined) meta.push(secs(t));
    if (!meta.length) meta.push(WORD[s]);
    /* Итог шага — то, чем он сам отчитался: числа, ради которых он и запускался. */
    var out = (info.out || []).slice(-2).join(" · ");
    /* ЧИСЛА ШАГА отдельной строкой, а не внутри итога. Итог — это фраза, которой
       шаг о себе отчитался; число — то, что сравнивают между прогонами. Шаг,
       своего числа не печатающий, не показывает ничего: выдумывать нечем. */
    var nums = (info.nums || []).map(function (kv) {
      return '<b>' + String(kv[1]).replace(/[<>&]/g, "") + '</b> <span>' +
        String(kv[0]).replace(/[<>&]/g, "") + '</span>';
    }).join('<br>');
    el.innerHTML =
      '<i class="pp-mark">' + MARK[s] + '</i>' +
      '<b class="pp-name">' + label(step) + '</b>' +
      '<span class="pp-meta">' + meta.join(" · ") + '</span>' +
      (nums ? '<span class="pp-nums">' + nums + '</span>' : "") +
      (out ? '<span class="pp-out">' + out.replace(/[<>&]/g, "") + '</span>' : "");
    return el;
  }

  function phaseEl(name, desc, steps, run) {
    var row = document.createElement("div");
    row.className = "pp-phase";
    var left = document.createElement("div");
    left.innerHTML = '<div class="pp-pname">' + name + '</div>' +
                     '<div class="pp-pdesc">' + desc + '</div>';
    var right = document.createElement("div");
    right.className = "pp-steps";
    steps.forEach(function (s) { right.appendChild(stepEl(s, run)); });
    row.appendChild(left);
    row.appendChild(right);
    return row;
  }

  function draw(run) {
    var flow = document.getElementById("pp-flow");
    flow.innerHTML = "";
    var all = (run.plan || []).slice();
    (run.done || []).concat(run.failed || []).forEach(function (s) {
      if (all.indexOf(s) < 0) all.push(s);
    });
    var placed = {};
    PHASES.forEach(function (ph) {
      var mine = all.filter(function (s) {
        return ph[2].some(function (k) {
          return s === k || (k === "day" && s.indexOf("day-") === 0);
        });
      });
      mine.forEach(function (s) { placed[s] = 1; });
      if (mine.length) flow.appendChild(phaseEl(ph[0], ph[1], mine, run));
    });
    var rest = all.filter(function (s) { return !placed[s]; });
    if (rest.length) flow.appendChild(phaseEl("Прочее", "шаги вне известных фаз", rest, run));

    var fails = run.failed || [];
    var box = document.getElementById("pp-fails");
    box.innerHTML = "";
    box.style.display = fails.length ? "" : "none";
    if (fails.length) {
      var h = document.createElement("h3");
      h.textContent = "! Не удалось — " + fails.length;
      box.appendChild(h);
      var ul = document.createElement("ul");
      fails.forEach(function (s) {
        var info = (run.steps || {})[s] || {};
        var li = document.createElement("li");
        li.innerHTML = "<b>" + label(s) + "</b> <code>" + s + "</code>" +
          (info.started ? " · " + info.started + (info.finished ? "–" + info.finished : "") : "") +
          (info.secs !== undefined ? " · " + secs(info.secs) : "") +
          (info.out && info.out.length ? "<br><span class='pp-out'>" +
            info.out.join(" · ").replace(/[<>&]/g, "") + "</span>" : "");
        ul.appendChild(li);
      });
      box.appendChild(ul);
    }

    /* СВОД ПРОГОНА. Владелец 30.08: «я должен увидеть, что прошли эти два
       пайплайна, все их шаги со статистикой — сколько статей, понятий новых,
       дедупликация, отбор кандидатов, доразметка». Числа собирает сам прогон
       (tools/full_run.py, finish) из того, что напечатали шаги. */
    /* Пока прогон идёт, время окончания не показываем ни при каких данных:
       журнал мог сохранить отметку прошлого захода, и читатель увидел бы
       законченным то, что работает у него на глазах. */
    var live = !!run.current;
    var tot = document.getElementById("pp-totals");
    tot.innerHTML = "";
    (live ? [] : (run.totals || [])).forEach(function (kv) {
      var d = document.createElement("div");
      d.className = "pp-tot";
      d.innerHTML = "<b>" + String(kv[1]).replace(/[<>&]/g, "") + "</b><span>" +
        String(kv[0]).replace(/[<>&]/g, "") + "</span>";
      tot.appendChild(d);
    });

    var left = all.filter(function (s) { return stateOf(run, s) === "wait"; }).length;
    var when = (run.started || "") +
      (!live && run.finished ? " → " + run.finished : "") +
      (!live && run.secs_total ? " · " + secs(run.secs_total) : "");
    /* Происхождение прогона рядом с родом: «ежедневный · по расписанию».
       Старым записям поля неоткуда взяться — тогда молчим, а не выдумываем. */
    var ORIGIN = {scheduled: "по расписанию", manual: "запущен вручную"};
    var org = ORIGIN[run.origin] ? '<i class="pp-origin">' + ORIGIN[run.origin] + '</i>' : '';
    document.getElementById("pp-now").innerHTML =
      '<i class="pp-kind">' + KIND_NAME(run) + '</i>' + org +
      (run.current
        ? "идёт: <b>" + label(run.current) + "</b> · пройдено " + (run.done || []).length +
          " из " + all.length + " · осталось " + left
        : "завершён · пройдено " + (run.done || []).length + " из " + all.length +
          (fails.length ? " · сбоев " + fails.length : "")) +
      (when ? " · " + when : "");
  }

  fetch("/data/pipeline-runs.json", {cache: "no-store"}).then(function (r) {
    return r.ok ? r.json() : null;
  }).then(function (data) {
    if (!data || !data.length) {
      document.getElementById("pp-empty").style.display = "";
      return;
    }
    runs = data.slice().reverse();
    var sel = document.getElementById("pp-run");
    runs.forEach(function (r, i) {
      var o = document.createElement("option");
      o.value = i;
      o.textContent = KIND_NAME(r) +
        (r.origin === "scheduled" ? " (расписание)" : r.origin === "manual" ? " (вручную)" : "") +
        " · " + (r.started || r.id || "прогон") +
        (r.days && r.days.length ? " · дни " + r.days[0] + "…" + r.days[r.days.length - 1] : "") +
        ((r.failed || []).length ? " · сбоев " + r.failed.length : "");
      sel.appendChild(o);
    });
    sel.onchange = function () { draw(runs[+sel.value]); };
    document.getElementById("pp-live").style.display = "";
    draw(runs[0]);
    if (runs[0].current) setTimeout(function () { location.reload(); }, 20000);
  }).catch(function () {
    document.getElementById("pp-empty").style.display = "";
  });
})();

/* РАССЫЛКА: числа из открытой сводки, имена — из закрытого файла.
   Открытая сводка (data/outreach-stats.json) едет вместе с сайтом. Подробности
   (data/outreach-sent.jsonl) не едут: заливка пропускает все .jsonl. На публичном
   сайте запрос за ними честно не найдёт файла — и окно скажет об этом словами,
   а не покажет пустую таблицу. */
(function () {
  var box = document.getElementById("pp-out");
  if (!box) return;
  function tile(n, cap) {
    return '<div class="pp-tot"><b>' + n + '</b><span>' + cap + '</span></div>';
  }
  fetch("/data/outreach-stats.json", {cache: "no-store"}).then(function (r) {
    return r.ok ? r.json() : null;
  }).then(function (d) {
    if (!d) return;
    box.style.display = "";
    var s = d.sent || {}, plus = d.plus || {};
    document.getElementById("pp-out-nums").innerHTML =
      tile(s.total || 0, "писем всего") +
      tile(s.week || 0, "за неделю") +
      tile((s.today || 0) + " / " + ((s.today || 0) + (s.can_today || 0)), "сегодня") +
      tile(d.came || 0, "зашли после письма") +
      tile(d.queue || 0, "готовы к отправке") +
      tile(plus["with"] || 0, "работ с плюсиком") +
      tile(plus["without"] || 0, "ждут разбора");
    var seen = d.seen || {};
    if (seen.authors) {
      document.getElementById("pp-out-seen").textContent =
        "За " + seen.days + " дней страницы авторов открывали " + seen.authors.views +
        " раз (" + seen.authors.pages + " разных страниц, " + seen.authors.devices +
        " устройств), страницы статей — " + seen.papers.views + " раз (" +
        seen.papers.pages + " страниц, " + seen.papers.devices + " устройств).";
    }
  }).catch(function () {});

  document.getElementById("pp-out-btn").onclick = function () {
    fetch("/data/outreach-sent.jsonl", {cache: "no-store"}).then(function (r) {
      return r.ok ? r.text() : null;
    }).then(function (t) {
      var rows = [];
      (t || "").split(String.fromCharCode(10)).forEach(function (ln) {
        if (ln.trim()) { try { rows.push(JSON.parse(ln)); } catch (e) {} }
      });
      var body;
      if (t === null) {
        body = '<div class="pp-note">Подробности не публикуются вместе с сайтом: ' +
          'кому мы написали — не дело публичной страницы. Файл ' +
          '<code>data/outreach-sent.jsonl</code> лежит на рабочей машине, и это окно ' +
          'показывает его там. Собрать заново: <code>python tools/outreach_stats.py</code>.</div>';
      } else if (!rows.length) {
        body = '<div class="pp-note">Писем ещё не отправляли.</div>';
      } else {
        body = '<table><tr><th>Когда</th><th>Кому</th><th>Работа</th><th>Язык</th>' +
          '<th>Зашёл</th></tr>' + rows.map(function (r) {
            var came = r.came
              ? "да · " + ((r.author_visits || 0) + (r.paper_visits || 0)) + " заходов"
              : "нет";
            return "<tr><td>" + r.at + "</td><td>" + r.author + "</td><td>" +
              (r.aid || "") + "</td><td>" + r.lang + "</td><td>" + came + "</td></tr>";
          }).join("") + "</table>" +
          '<div class="pp-note">Считается заход на страницу, а не человек: видно, что ' +
          'адрес открывали после письма, и не видно, кто именно.</div>';
      }
      var m = document.createElement("div");
      m.className = "pp-modal";
      m.innerHTML = '<div class="pp-modal-in"><button class="pp-x" type="button">&times;</button>' +
        "<h3>Кому отправлено</h3>" + body + "</div>";
      m.onclick = function (e) {
        if (e.target === m || e.target.className === "pp-x") m.remove();
      };
      document.body.appendChild(m);
    });
  };
})();
/* ПАНЕЛЬ УПРАВЛЕНИЯ РАССЫЛКОЙ — ТОЛЬКО ЛОКАЛЬНО.
   Ручка /api/outreach есть только у tools/dev_server.py на этой машине. На сайте
   запрос не найдёт её, панель просто не появится — и почты авторов на публичной
   странице не окажутся ни при каких обстоятельствах. */
(function () {
  var box = document.getElementById("pp-panel");
  if (!box) return;
  var CAND = [], TPL = null, LANG = "en", CAP = 0;

  function esc(t) {
    return String(t == null ? "" : t).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function drawTable() {
    var rows = CAND.map(function (r, i) {
      var lang = r.lang === "ar" ? "арабский" : "английский";
      return '<tr class="' + (r.written ? "done" : "") + '">' +
        '<td><input type="checkbox" data-i="' + i + '"' + (r.written ? " disabled" : "") + '></td>' +
        "<td>" + esc(r.author) + "</td>" +
        '<td class="pp-mail">' + esc(r.to) + "</td>" +
        "<td>" + esc(r.id) + "</td>" +
        "<td>" + esc(r.date) + "</td>" +
        "<td>" + lang + "</td>" +
        "<td>" + (r.written ? "уже писали" :
          '<button type="button" data-prev="' + i + '">письмо</button>') + "</td></tr>";
    }).join("");
    document.getElementById("pp-cand").innerHTML =
      "<tr><th></th><th>Автор</th><th>Почта</th><th>Работа</th><th>Разбор</th>" +
      "<th>Язык</th><th></th></tr>" + rows;
    document.getElementById("pp-panel-note").textContent =
      "Кандидатов " + CAND.length + ". Все они уже прошли отбор: разбор машины знаний, " +
      "неделя выдержки, адрес найден в самой работе и сходится с именем автора. " +
      "Сегодня можно отправить ещё " + CAP + " — это разгон домена, он соблюдается при отправке.";
    box.querySelectorAll("input[type=checkbox]").forEach(function (c) {
      c.onchange = function () {
        var n = box.querySelectorAll("input[type=checkbox]:checked").length;
        document.getElementById("pp-send").disabled = n === 0;
        document.getElementById("pp-send-note").textContent =
          n ? "выбрано " + n + (n > CAP ? " — больше сегодняшней нормы, лишние не уйдут" : "") : "";
      };
    });
    box.querySelectorAll("button[data-prev]").forEach(function (b) {
      b.onclick = function () { preview(CAND[+b.dataset.prev]); };
    });
  }

  function preview(r) {
    var u = "/api/outreach/preview?id=" + encodeURIComponent(r.id) +
            "&who=" + encodeURIComponent(r.author) + "&lang=" + encodeURIComponent(r.lang || "en");
    fetch(u).then(function (x) { return x.json(); }).then(function (d) {
      var m = document.createElement("div");
      m.className = "pp-modal";
      m.innerHTML = '<div class="pp-modal-in"><button class="pp-x" type="button">&times;</button>' +
        "<h3>" + esc(d.subject || "") + "</h3>" +
        '<div class="pp-note">Кому: ' + esc(r.to) + " · это ровно то письмо, которое уйдёт.</div>" +
        (d.html ? '<div style="border:1px solid var(--hair);border-radius:8px;overflow:hidden;margin:10px 0">'
                  + d.html + "</div>"
                : '<pre style="white-space:pre-wrap;font-size:12px">' + esc(d.text) + '</pre>');
      m.onclick = function (e) { if (e.target === m || e.target.className === "pp-x") m.remove(); };
      document.body.appendChild(m);
    });
  }

  function drawTemplate() {
    var tabs = Object.keys(TPL.langs);
    document.getElementById("pp-tpl-tabs").innerHTML = tabs.map(function (l) {
      return '<button type="button" data-l="' + l + '" class="' + (l === LANG ? "on" : "") + '">' +
             l.toUpperCase() + "</button>";
    }).join("");
    document.getElementById("pp-tpl-tabs").querySelectorAll("button").forEach(function (b) {
      b.onclick = function () { saveDraft(); LANG = b.dataset.l; drawTemplate(); };
    });
    document.getElementById("pp-tpl-subject").value = TPL.langs[LANG].subject || "";
    document.getElementById("pp-tpl-body").value = TPL.langs[LANG].body || "";
    document.getElementById("pp-tpl-note").textContent =
      "Правка ложится поверх зашитого шаблона в " + TPL.file +
      ". Места подстановки обязаны остаться: " + TPL.slots.join(" ") +
      " — без них письмо уйдёт с дырой вместо пересказа.";
  }

  function saveDraft() {
    if (!TPL) return;
    TPL.langs[LANG].subject = document.getElementById("pp-tpl-subject").value;
    TPL.langs[LANG].body = document.getElementById("pp-tpl-body").value;
  }

  fetch("/api/outreach").then(function (r) {
    if (!r.ok) throw 0;
    return r.json();
  }).then(function (d) {
    CAND = d.items || []; CAP = d.can_today || 0;
    box.style.display = "";
    drawTable();
    return fetch("/api/outreach/template").then(function (r) { return r.json(); });
  }).then(function (t) {
    TPL = t; drawTemplate();
  }).catch(function () { /* публичный сайт: панели нет, и это правильно */ });

  document.getElementById("pp-send").onclick = function () {
    var ids = [];
    box.querySelectorAll("input[type=checkbox]:checked").forEach(function (c) {
      ids.push(CAND[+c.dataset.i].id);
    });
    if (!ids.length) return;
    if (!confirm("Отправить " + ids.length + " писем? Отменить будет нельзя.")) return;
    var btn = this; btn.disabled = true;
    document.getElementById("pp-send-note").textContent = "отправляю…";
    fetch("/api/outreach/send", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ids: ids}),
    }).then(function (r) { return r.json(); }).then(function (d) {
      var ok = (d.sent || []).filter(function (x) { return x.ok; }).length;
      document.getElementById("pp-send-note").textContent =
        "отправлено " + ok + " из " + ids.length +
        (ok < ids.length ? " · остальные не прошли: норма дня, уже писали или отказ почты" : "");
      setTimeout(function () { location.reload(); }, 2500);
    }).catch(function () {
      document.getElementById("pp-send-note").textContent = "не удалось — смотри вывод сервера";
      btn.disabled = false;
    });
  };

  document.getElementById("pp-tpl-save").onclick = function () {
    saveDraft();
    fetch("/api/outreach/template", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({langs: TPL.langs}),
    }).then(function (r) { return r.json(); }).then(function (d) {
      document.getElementById("pp-tpl-saved").textContent = d.saved
        ? "сохранено в " + d.file
        : "не сохранено: " + (d.problems || []).map(function (p) {
            return p.lang + " — нет " + p.missing.join(" ");
          }).join("; ");
    });
  };
})();

"""

def main():
    nodes = json.loads(NODES.read_text(encoding="utf-8")) if NODES.exists() else {}
    js = (JS.replace("%PHASES%", json.dumps(PHASES, ensure_ascii=False))
            .replace("%EXPLAIN%", json.dumps(EXPLAIN, ensure_ascii=False))
            .replace("%SHORT%", json.dumps(SHORT, ensure_ascii=False))
            .replace("%NODES%", json.dumps(nodes, ensure_ascii=False)))
    html = f"""<!DOCTYPE html>
<html lang="ru" dir="ltr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Конвейер — bridge42worlds</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:opsz@14..32&family=Source+Serif+4:opsz@8..60&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/css/style.css">
<link rel="icon" href="/favicon.ico" sizes="any">
<style>{CSS}</style>
</head>
<body>

<div class="pp-head">
  <h1>Конвейер</h1>
  <div class="pp-sub">Полный цикл производства: от свежих работ с arXiv до
  выложенного сайта. Лампочка у каждого шага показывает, что прошло, что идёт
  сейчас и что не удалось; список прогонов слева переключает историю.</div>
</div>

<div class="pp-bar" id="pp-live" style="display:none">
  <label>Прогон: <select id="pp-run"></select></label>
  <span class="pp-now" id="pp-now"></span>
  <span class="pp-legend">
    <span><i style="border:1.5px solid var(--ok);color:var(--ok)">&#10003;</i>прошло</span>
    <span><i style="border:1.5px dashed var(--run);color:var(--run)">&#9654;</i>идёт</span>
    <span><i style="border:1.5px solid var(--fail);color:var(--fail)">!</i>сбой</span>
    <span><i style="border:1.5px solid var(--muted);color:var(--muted)">&#9675;</i>пусто</span>
    <span><i style="border:1.5px dotted var(--wait);color:var(--wait)">&middot;</i>впереди</span>
  </span>
</div>

<div class="pp-empty" id="pp-empty" style="display:none">
  Журнала прогонов ещё нет. Он появится после первого запуска
  <code>tools/full_run.py</code> — страница читает <code>data/pipeline-runs.json</code>
  и ничего не выдумывает, пока файла нет.
</div>

<div class="pp-totals" id="pp-totals"></div>
<div class="pp-flow" id="pp-flow"></div>
<div class="pp-fails" id="pp-fails" style="display:none"></div>


<div class="pp-out" id="pp-out" style="display:none">
  <h2>Рассылка авторам</h2>
  <div class="pp-sub2">Письмо уходит только автору работы, которую разобрала машина
  знаний, и не раньше чем через неделю после разбора. Очередь идёт от самых старых
  работ. Здесь только числа: кому именно написано — в закрытом окне, оно открывается
  на рабочей машине.</div>
  <div class="pp-totals" id="pp-out-nums"></div>
  <button class="pp-out-btn" id="pp-out-btn" type="button">Кому отправлено &rarr;</button>
  <div class="pp-note" id="pp-out-seen"></div>
</div>

<div class="pp-panel" id="pp-panel" style="display:none">
  <h3>Управление рассылкой</h3>
  <div class="pp-note" id="pp-panel-note"></div>
  <table class="pp-tbl" id="pp-cand"></table>
  <div class="pp-act">
    <button class="pp-send" id="pp-send" type="button" disabled>Отправить выбранным</button>
    <span class="pp-note" id="pp-send-note"></span>
  </div>
  <div class="pp-tpl" style="margin-top:22px">
    <h3>Шаблон письма</h3>
    <div class="pp-note" id="pp-tpl-note"></div>
    <div class="pp-tabs" id="pp-tpl-tabs"></div>
    <input type="text" id="pp-tpl-subject" placeholder="Тема письма">
    <textarea id="pp-tpl-body" spellcheck="false"></textarea>
    <div class="pp-act">
      <button class="pp-send" id="pp-tpl-save" type="button">Сохранить шаблон</button>
      <span class="pp-note" id="pp-tpl-saved"></span>
    </div>
  </div>
</div>


<div class="pp-hint">Статус читается знаком и рамкой, не цветом: галочка и
сплошная — прошло, стрелка и пунктир — идёт, восклицание и штриховка — сбой,
точка и точечная рамка — впереди. Под именем шага стоит время начала и окончания,
дальше — то, чем шаг отчитался. Наведите на квадрат: покажет, что он делает, и
полный итог. Пока конвейер работает, страница обновляется сама.</div>

<script>{js}</script>
</body>
</html>


"""
    OUT.write_text(html, encoding="utf-8")
    print(f"✅ {OUT.name}: {len(PHASES)} фаз, описаний узлов {len(nodes)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
