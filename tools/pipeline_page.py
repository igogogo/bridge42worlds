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
    ("Записи", "карточки, переводы, имена, переразметка",
     ["live-1", "cards", "tr-cards", "tr-formulas", "names-ru", "retag", "apply"]),
    ("Связность", "суперпонятия, соседи, области, связи знанием, граф",
     ["super", "live-2", "vecnb", "live-3", "gnames", "weave", "live-4", "graph",
      "mentions-ru", "highlight"]),
    ("Сборка", "страницы понятий и формул, весь сайт, авторы, дашборд",
     ["pages-c", "pages-f", "html", "authors", "status"]),
    ("Облако", "D1, векторы, карточки статей, выкладка воркера",
     ["cloud-d1", "cloud-vec", "cards-sync", "deploy"]),
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
    "html": "pages", "graph": "data", "status": "dash", "authors": "dash",
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
    "retag": "Переразметка статей", "apply": "Применение разметки",
    "super": "Суперпонятия", "vecnb": "Соседи вектором",
    "gnames": "Имена областей", "weave": "Связи знанием",
    "graph": "Экспорт графа", "mentions-ru": "Упоминания",
    "highlight": "Подсветка терминов",
    "pages-c": "Страницы понятий", "pages-f": "Страницы формул",
    "html": "Сборка сайта", "authors": "Страницы авторов", "status": "Дашборд",
    "cloud-d1": "Заливка D1", "cloud-vec": "Векторы в облако",
    "cards-sync": "Карточки статей в D1", "deploy": "Выкладка воркера",
    "api": "Проверка API", "pages": "Проверка страниц",
    "audit": "Аудит понятий", "gaudit": "Аудит областей", "links": "Проверка ссылок",
}

CSS = """
:root { --ok: #1f9d76; --run: #c8892a; --fail: #c0392b; --wait: #b9b2a6; }
body { max-width: 1100px; padding-bottom: 70px; }
.pp-head h1 { font-size: 25px; margin: 24px 0 4px; }
.pp-sub { color: var(--soft); font-size: 13.5px; max-width: 74ch; line-height: 1.55; }
.pp-bar { display: flex; flex-wrap: wrap; gap: 10px 16px; align-items: center;
    margin: 16px 0 6px; font-family: var(--mono); font-size: 12px; }
.pp-bar select { font-family: var(--mono); font-size: 12px; padding: 4px 8px;
    border: 1px solid var(--hairline); border-radius: 6px; background: var(--bg);
    color: var(--fg); }
.pp-now { color: var(--muted); }
.pp-now b { color: var(--run); font-weight: 500; }
.pp-legend { display: flex; gap: 14px; flex-wrap: wrap; margin-left: auto;
    color: var(--muted); }
.pp-legend i { width: 8px; height: 8px; border-radius: 50%; display: inline-block;
    margin-right: 5px; vertical-align: 1px; }

/* Поток: фазы идут строками, шаги внутри — лампочками в ряд. Так весь цикл
   виден целиком, без прокрутки на сорок узлов. */
.pp-flow { margin: 14px 0 0; }
.pp-phase { display: grid; grid-template-columns: 190px 1fr; gap: 12px;
    padding: 9px 0; border-top: 1px solid var(--hairline); align-items: start; }
.pp-phase:last-child { border-bottom: 1px solid var(--hairline); }
.pp-pname { font-family: var(--serif); font-size: 14.5px; line-height: 1.3; }
.pp-pdesc { color: var(--soft); font-size: 11.5px; line-height: 1.4; margin-top: 2px; }
.pp-steps { display: flex; flex-wrap: wrap; gap: 6px; }
.pp-step { display: flex; align-items: center; gap: 6px; padding: 4px 9px 4px 7px;
    border: 1px solid var(--hairline); border-radius: 999px; font-size: 11.5px;
    background: var(--bg); cursor: default; transition: border-color .15s, transform .15s; }
.pp-step:hover { border-color: var(--muted); transform: translateY(-1px); }
.pp-lamp { width: 8px; height: 8px; border-radius: 50%; background: var(--wait);
    flex: none; }
.pp-step[data-s="done"] .pp-lamp { background: var(--ok); }
.pp-step[data-s="fail"] .pp-lamp { background: var(--fail); }
.pp-step[data-s="run"]  .pp-lamp { background: var(--run);
    animation: pp-pulse 1.2s ease-in-out infinite; }
.pp-step[data-s="fail"] { border-color: var(--fail); }
.pp-step[data-s="run"]  { border-color: var(--run); }
.pp-secs { color: var(--muted); font-family: var(--mono); font-size: 10.5px; }
@keyframes pp-pulse { 0%,100% { opacity: 1; } 50% { opacity: .35; } }

.pp-fails { margin: 18px 0 0; border: 1px solid var(--fail); border-radius: 8px;
    padding: 10px 13px; font-size: 12.5px; }
.pp-fails h3 { margin: 0 0 6px; font-size: 13px; color: var(--fail); }
.pp-fails li { margin: 3px 0; }
.pp-hint { margin: 16px 0 0; font-size: 12px; color: var(--soft); line-height: 1.5; }
.pp-empty { margin: 22px 0; padding: 14px; border: 1px dashed var(--hairline);
    border-radius: 8px; color: var(--soft); font-size: 13px; }
.pp-tip { max-width: 320px; }
@media (max-width: 720px) {
  .pp-phase { grid-template-columns: 1fr; gap: 4px; }
  .pp-legend { margin-left: 0; }
}
"""

JS = """
(function () {
  var PHASES = %PHASES%, EXPLAIN = %EXPLAIN%, SHORT = %SHORT%, NODES = %NODES%;
  var runs = [], cur = null;

  function label(step) {
    if (step.indexOf("day-") === 0) return step.slice(4);
    if (SHORT[step]) return SHORT[step];
    var n = NODES[EXPLAIN[step] || step];
    return n ? n.t : step;
  }
  function tip(step) {
    var n = NODES[EXPLAIN[step] || step];
    if (step.indexOf("day-") === 0) return "Забор и разбор дня " + step.slice(4);
    return n ? (n.t + " — " + n.d + (n.n ? " · " + n.n : "")) : step;
  }
  function secs(s) {
    if (!s) return "";
    return s < 60 ? s + "с" : Math.round(s / 60) + "м";
  }

  function stateOf(run, step) {
    if ((run.failed || []).indexOf(step) >= 0) return "fail";
    if (run.current === step) return "run";
    if ((run.done || []).indexOf(step) >= 0) return "done";
    return "wait";
  }

  function draw(run) {
    var flow = document.getElementById("pp-flow");
    flow.innerHTML = "";
    /* Шаги берём из журнала, а не из страницы: цепочка живёт своей жизнью, и
       зашитый список разъехался бы с ней при первой правке. */
    var all = (run.plan || []).slice();
    (run.done || []).concat(run.failed || []).forEach(function (s) {
      if (all.indexOf(s) < 0) all.push(s);
    });
    var placed = {};
    PHASES.forEach(function (ph) {
      var mine = all.filter(function (s) {
        return ph[2].some(function (k) { return s === k || (k === "day" && s.indexOf("day-") === 0); });
      });
      mine.forEach(function (s) { placed[s] = 1; });
      if (!mine.length) return;
      flow.appendChild(phaseEl(ph[0], ph[1], mine, run));
    });
    var rest = all.filter(function (s) { return !placed[s]; });
    if (rest.length) flow.appendChild(phaseEl("Прочее", "шаги вне известных фаз", rest, run));

    var fails = (run.failed || []);
    var box = document.getElementById("pp-fails");
    box.innerHTML = "";
    box.style.display = fails.length ? "" : "none";
    if (fails.length) {
      var h = document.createElement("h3");
      h.textContent = "Не удалось — " + fails.length;
      box.appendChild(h);
      var ul = document.createElement("ul");
      fails.forEach(function (s) {
        var li = document.createElement("li");
        li.textContent = label(s) + " (" + s + ")" + (run.secs && run.secs[s] ? " · " + secs(run.secs[s]) : "");
        ul.appendChild(li);
      });
      box.appendChild(ul);
    }

    var left = all.filter(function (s) { return stateOf(run, s) === "wait"; }).length;
    var now = document.getElementById("pp-now");
    now.innerHTML = run.current
      ? "идёт: <b>" + label(run.current) + "</b> · пройдено " + (run.done || []).length
        + " из " + all.length + " · осталось " + left
      : "прогон завершён · пройдено " + (run.done || []).length + " из " + all.length
        + (fails.length ? " · с ошибками" : "");
  }

  function phaseEl(name, desc, steps, run) {
    var row = document.createElement("div");
    row.className = "pp-phase";
    var left = document.createElement("div");
    left.innerHTML = '<div class="pp-pname">' + name + '</div><div class="pp-pdesc">' + desc + '</div>';
    var right = document.createElement("div");
    right.className = "pp-steps";
    steps.forEach(function (s) {
      var el = document.createElement("span");
      el.className = "pp-step";
      el.dataset.s = stateOf(run, s);
      el.title = tip(s);
      var sec = run.secs && run.secs[s] ? '<span class="pp-secs">' + secs(run.secs[s]) + '</span>' : "";
      el.innerHTML = '<i class="pp-lamp"></i>' + label(s) + sec;
      right.appendChild(el);
    });
    row.appendChild(left);
    row.appendChild(right);
    return row;
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
      o.textContent = (r.started || r.id || "прогон")
        + (r.days && r.days.length ? " · дни " + r.days[0] + "…" + r.days[r.days.length - 1] : "")
        + ((r.failed || []).length ? " · сбои" : "");
      sel.appendChild(o);
    });
    sel.onchange = function () { draw(runs[+sel.value]); };
    document.getElementById("pp-live").style.display = "";
    draw(runs[0]);
    /* Пока прогон идёт, страница обновляет себя сама: смотреть на неподвижную
       картинку работающего конвейера — то же, что не иметь её вовсе. */
    if (runs[0].current) setTimeout(function () { location.reload(); }, 20000);
  }).catch(function () {
    document.getElementById("pp-empty").style.display = "";
  });
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
    <span><i style="background:var(--ok)"></i>прошло</span>
    <span><i style="background:var(--run)"></i>идёт</span>
    <span><i style="background:var(--fail)"></i>сбой</span>
    <span><i style="background:var(--wait)"></i>впереди</span>
  </span>
</div>

<div class="pp-empty" id="pp-empty" style="display:none">
  Журнала прогонов ещё нет. Он появится после первого запуска
  <code>tools/full_run.py</code> — страница читает <code>data/pipeline-runs.json</code>
  и ничего не выдумывает, пока файла нет.
</div>

<div class="pp-flow" id="pp-flow"></div>
<div class="pp-fails" id="pp-fails" style="display:none"></div>

<div class="pp-hint">Наведите на шаг — покажет, что он делает. Время рядом с
именем — сколько шаг занял в этом прогоне. Пока конвейер работает, страница
обновляется сама.</div>

<script>{js}</script>
</body>
</html>
"""
    OUT.write_text(html, encoding="utf-8")
    print(f"✅ {OUT.name}: {len(PHASES)} фаз, описаний узлов {len(nodes)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
