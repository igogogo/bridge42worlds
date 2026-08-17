#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Техлист — закрытая страница для владельца: все живые пункты техчасти одной таблицей.

Владелец 17 августа: «на сайте должен быть техлист: все актуальные пункты на русском,
таблицей, сгруппированные по смыслу в эпики; что делает тех-часть — тултипом подробное
описание; сколько стоит (разово или месячно); от чего зависит; что сделано на текущем
спринте с воскресенья по воскресенье; блокеры от меня; приоритет; диаграмма Ганта;
там же ссылка на архитектуру — визуально всё нарисовать: общая архитектура, схема
данных (что где лежит, облако/локально), потоки загрузки, UX, основные сервисы;
поддерживать и обновлять раз в неделю; раздел закрытый, прямая ссылка мне; и чтобы
я мог ставить галочки и выбирать приоритеты — живая форма: ты делаешь, я прохожусь,
отвечаю, помечаю, и работаем неделю».

Как устроено:
  · данные — data/tech/plan.json (правится руками ведущей, пересборка — этим скриптом);
  · страница живёт по СЕКРЕТНОМУ пути (в sitemap не попадает, noindex, ссылок с сайта
    на неё нет) — это «закрытость по ссылке», достаточная для внутреннего документа
    без персональных данных; настоящих секретов на странице нет и быть не должно;
  · схемы — Mermaid, свезённый локально (js/vendor-mermaid.min.js): CSP запрещает CDN.
    Инструмент выбран за то, что схема — это ТЕКСТ в git: обновить схему = поправить
    строку, а не перерисовать картинку. Ровно то, что нужно для «обновлять раз в неделю»;
  · ответы владельца (галочки, приоритеты, комментарии) уходят POST'ом на
    /api/tech/feedback — Worker кладёт их в R2 и шлёт строку в канал;
  · еженедельное обновление: бесплатный шаг «tech» в фабрике пересобирает страницу
    из plan.json каждый прогон — дёшево, а страница всегда свежая.

    python tools/tech_page.py            собрать и напечатать путь
"""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Секретное имя страницы. Постоянное, а не случайное на каждую сборку: владелец
# сохраняет ссылку один раз, и она не должна протухать от пересборки.
SLUG = "tech-vq7k4m"
OUT = ROOT / f"{SLUG}.html"

СТАТУС_ЦВЕТ = {"работает": "#3d8f5a", "новое": "#2a8fa8", "в работе": "#b8860b",
               "запланировано": "#8a8a86", "блокировано": "#c2564a"}
ПРИОРИТЕТ_ЗНАК = {"высокий": "▲", "средний": "●", "низкий": "▽"}


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def gantt(plan):
    """Гант по эпикам текущего спринта: полоса от дня начала до дня конца."""
    s = plan["спринт"]
    days = list(range(17, 24))  # спринт вс-вс; подписи — числа месяца
    head = "".join(f"<span>{d}</span>" for d in days)
    rows = []
    for e in plan["эпики"]:
        g = e.get("гант") or [days[0], days[-1]]
        left = (g[0] - days[0]) / len(days) * 100
        width = (g[1] - g[0] + 1) / len(days) * 100
        rows.append(
            f'<div class="g-row"><span class="g-name">{esc(e["имя"])}</span>'
            f'<span class="g-track"><i style="left:{left:.0f}%;width:{width:.0f}%"></i></span></div>')
    return (f'<div class="gantt"><div class="g-head"><span class="g-name"></span>'
            f'<span class="g-days">{head}</span></div>{"".join(rows)}</div>')


def item_row(it):
    q = it.get("вопрос")
    ask = ""
    if q:
        if q["тип"] == "галочка":
            ask = (f'<label class="ask"><input type="checkbox" data-item="{it["id"]}" '
                   f'data-kind="галочка"> {esc(q["текст"])}</label>')
        else:
            opts = "".join(f'<option>{esc(v)}</option>' for v in q.get("варианты", []))
            ask = (f'<div class="ask">{esc(q["текст"])}<br>'
                   f'<select data-item="{it["id"]}" data-kind="выбор">'
                   f'<option value="">— выбрать —</option>{opts}</select></div>')
    col = СТАТУС_ЦВЕТ.get(it.get("статус", ""), "#888")
    pr = it.get("приоритет", "средний")
    return f"""<tr data-item="{it['id']}">
  <td class="c-name"><span class="tip" tabindex="0">{esc(it['имя'])}
      <span class="tipbox">{esc(it['тултип'])}</span></span></td>
  <td class="c-cost">{esc(it['стоимость'])}</td>
  <td class="c-dep">{esc(it['зависит'])}</td>
  <td class="c-sprint">{esc(it['спринт'])}</td>
  <td class="c-status"><i style="background:{col}"></i>{esc(it['статус'])}</td>
  <td class="c-prio"><select data-item="{it['id']}" data-kind="приоритет">
      {''.join(f'<option{" selected" if p == pr else ""}>{p}</option>' for p in ('высокий', 'средний', 'низкий'))}
      </select></td>
  <td class="c-ask">{ask}
      <input type="text" class="note" data-item="{it['id']}" data-kind="комментарий"
             placeholder="комментарий / блокер"></td>
</tr>"""


MERMAID_SCHEMES = [
("Общая архитектура", """flowchart LR
  subgraph Ноутбук["Машина владельца (временная, план: VPS)"]
    SCHED["Планировщик Windows\\n9 задач b42_*"] --> FACTORY["Фабрика\\nplan() по бюджету"]
    FACTORY --> GEN["Генератор\\ngenerate.py + gen_llm"]
    GEN --> DATA[("lang/*/archive\\ndata.json + страницы")]
    DATA --> DEPLOY["deploy_r2\\nдельта по манифесту"]
  end
  ARXIV["arXiv\\nAPI + дамп Kaggle 5.4 ГБ"] --> FACTORY
  DS["DeepSeek V4\\nflash/pro"] <--> GEN
  DI["DeepInfra\\nQwen-reranker, bge-m3"] <--> FACTORY
  DEPLOY --> R2[("Cloudflare R2\\n154 тыс. файлов")]
  R2 --> WORKER["Worker\\nотдача + API + сторожа"]
  WORKER --> READER(["Читатель\\n5 языков"])
  WORKER <--> D1[("D1: совет, события,\\nочередь заказов")]
  WORKER <--> VEC[("Vectorize\\nb42-articles, bge-m3")]
  WORKER --> TG["Telegram\\nканал команды + дайджест"]"""),
("Схема данных: что где лежит", """flowchart TB
  subgraph Локально["Локально (ноутбук + флешка-бэкап)"]
    L1[("lang/*/archive — статьи\\n30 ГБ, источник правды")]
    L2[("data/ — справочники, графы,\\nвектор 1.5 ГБ, дамп-чанки 4 ГБ")]
    L3[("../b42-ml/data\\nполе вектора 3.2 ГБ")]
    L4[("data/submissions\\nзаявки читателей — только тут")]
  end
  subgraph Облако["Cloudflare"]
    C1[("R2: весь сайт\\nкопия страниц и данных")]
    C2[("D1: живое состояние\\nсовет, голоса, события")]
    C3[("Vectorize: вектор статей\\nдля /api/search")]
  end
  subgraph GitHub
    G1[("Код + промпты + задачи\\nБЕЗ lang/**, БЕЗ ключей")]
  end
  L1 -->|deploy_r2| C1
  L2 -->|deploy_r2, витринные| C1
  L1 -->|vector_build| C3
  L4 -.->|никогда не публикуется| X["⛔"]"""),
("Поток: ночная генерация", """flowchart LR
  A["arXiv: ~1058\\nкандидатов дня"] --> B["Предфильтр вектором\\n−81% (края: дубли и не наш профиль)"]
  B --> C["Реранкер Qwen\\nинтересно ли читателю"]
  C --> D["DeepSeek select\\n~200 → лучшие"]
  D --> E["Генерация: 5 языков\\n× уровни чтения"]
  E --> F["Валидация тегов\\nпо реестру (новое)"]
  F --> G["data.json + страницы\\n+ related-vec + дотяжка"]
  G --> H["Пересборка агрегатов\\nтолько изменившееся (отпечатки)"]
  H --> I["deploy_r2 → R2\\nатомарно, со сверкой"]
  I --> J["verify_publish + page_watch\\nцелы ли индексы, жива ли лента"]"""),
("UX: путь читателя", """flowchart LR
  SEO["Google/боты\\nsitemap + честный lastmod"] --> HOME["Главная: лента\\n12 карточек, фильтры"]
  TG2["Дайджест Telegram\\nежедневно 18:00"] --> ART
  HOME --> ART["Статья: 3 уровня чтения\\n+ похожие + советы автору"]
  ART --> REL["Похожие по смыслу\\n(related-vec)"] --> ART
  ART --> TAGS["Теги / законы / учёные\\nграф знаний"]
  HOME --> ANAL["Аналитика: карта, полёт,\\n11 режимов"]
  ART --> ORDER["Заказать разбор\\n→ очередь D1"]
  HOME --> COUNCIL["Совет: голосование,\\nзаморозка, история"]
  style REL stroke:#3d8f5a,stroke-width:2px"""),
("Основные сервисы и расписание", """flowchart TB
  subgraph Планировщик["Задачи планировщика (локальное время, UTC+3)"]
    T1["19:00 overnight — накачка архива\\n(вне пика DeepSeek)"]
    T2["05:00 dump — дамп arXiv"]
    T3["07:00/15:00/23:00 stats — витрина"]
    T4["07:30 upkeep — разметка вектором"]
    T5["13:00 factory — план по бюджету"]
    T6["18:00 digest — дайджест в канал"]
    T7["пт 10:00 совет: повестка\\nвс 21:00 совет: закрытие"]
  end
  subgraph WorkerCron["Worker cron (UTC)"]
    W1["каждый час: молчание сторожей"]
    W2["09:00: свежесть ленты, чистка событий"]
  end"""),
]


def mermaid_section():
    blocks = []
    for title, code in MERMAID_SCHEMES:
        blocks.append(f'<h3>{esc(title)}</h3><pre class="mermaid">{code}</pre>')
    return "\n".join(blocks)


def build():
    plan = json.loads((ROOT / "data" / "tech" / "plan.json").read_text(encoding="utf-8"))
    epics_html = []
    for e in plan["эпики"]:
        rows = "".join(item_row(it) for it in e["пункты"])
        epics_html.append(f"""
<section class="epic">
  <h2>{esc(e['имя'])} <small>{esc(e['что'])}</small></h2>
  <table>
    <thead><tr><th>что</th><th>стоимость</th><th>зависит от</th>
    <th>спринт {esc(plan['спринт']['с'][5:])}–{esc(plan['спринт']['по'][5:])}</th>
    <th>статус</th><th>приоритет</th><th>от владельца</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</section>""")

    html = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Техлист · bridge42worlds</title>
<style>
:root {{ --bg:#12151c; --surface:#1a1f29; --ink:#e8e6e0; --muted:#a5a29a; --hair:#2c3240;
        --ochre:#c9963f; --cyan:#4db3c9; --ok:#3d8f5a; }}
* {{ box-sizing:border-box; margin:0; }}
body {{ background:var(--bg); color:var(--ink); font:15px/1.6 Georgia, serif; padding:28px 20px 80px; }}
.wrap {{ max-width:1200px; margin:0 auto; }}
h1 {{ font-size:26px; margin-bottom:4px; }}
.sub {{ color:var(--muted); font-size:13.5px; margin-bottom:6px; }}
.goal {{ background:var(--surface); border:1px solid var(--hair); border-left:3px solid var(--ochre);
        border-radius:10px; padding:12px 16px; margin:16px 0 22px; }}
.epic {{ margin:26px 0; }}
h2 {{ font-size:19px; color:var(--ochre); margin-bottom:2px; }}
h2 small {{ display:block; font-size:13px; color:var(--muted); font-weight:normal; }}
table {{ width:100%; border-collapse:collapse; margin-top:10px; font-size:13.5px; }}
th {{ text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:.06em;
     color:var(--muted); padding:6px 8px; border-bottom:1px solid var(--hair); }}
td {{ padding:9px 8px; border-bottom:1px solid var(--hair); vertical-align:top; }}
.c-name {{ min-width:170px; font-weight:bold; }}
.c-status i {{ display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:6px; }}
.tip {{ position:relative; cursor:help; border-bottom:1px dotted var(--muted); }}
.tipbox {{ display:none; position:absolute; z-index:9; left:0; top:100%; width:380px;
          background:#0e1116; border:1px solid var(--hair); border-radius:10px; padding:12px 14px;
          font-weight:normal; font-size:13px; line-height:1.55; box-shadow:0 16px 40px rgba(0,0,0,.5); }}
.tip:hover .tipbox, .tip:focus .tipbox {{ display:block; }}
select, .note {{ background:#0e1116; color:var(--ink); border:1px solid var(--hair);
                border-radius:7px; padding:4px 7px; font:inherit; font-size:12.5px; }}
.note {{ width:100%; margin-top:6px; }}
.ask {{ display:block; font-size:12.5px; color:#dfc999; }}
.gantt {{ background:var(--surface); border:1px solid var(--hair); border-radius:10px;
         padding:14px 16px; margin:14px 0; }}
.g-row, .g-head {{ display:flex; align-items:center; gap:10px; margin:5px 0; }}
.g-name {{ width:180px; font-size:12.5px; color:var(--muted); flex:none; }}
.g-days {{ flex:1; display:flex; justify-content:space-between; font-size:10.5px; color:var(--muted); }}
.g-track {{ flex:1; position:relative; height:14px; background:#0e1116; border-radius:7px; }}
.g-track i {{ position:absolute; top:2px; bottom:2px; background:linear-gradient(90deg,var(--ochre),var(--cyan));
             border-radius:5px; opacity:.85; }}
.savebar {{ position:fixed; bottom:0; left:0; right:0; background:#0e1116e6; backdrop-filter:blur(6px);
           border-top:1px solid var(--hair); padding:10px 20px; display:flex; gap:14px; align-items:center; }}
.savebar button {{ background:var(--ochre); color:#14100a; border:none; border-radius:999px;
                  padding:9px 22px; font:inherit; font-size:14px; cursor:pointer; }}
.savebar .msg {{ color:var(--muted); font-size:13px; }}
.arch h3 {{ margin:22px 0 8px; font-size:16px; color:var(--cyan); }}
pre.mermaid {{ background:var(--surface); border:1px solid var(--hair); border-radius:10px;
              padding:14px; overflow-x:auto; }}
a {{ color:var(--cyan); }}
</style></head><body><div class="wrap">
<h1>Техлист bridge42worlds</h1>
<p class="sub">обновлено {esc(plan['обновлено'])} · спринт {esc(plan['спринт']['с'])} → {esc(plan['спринт']['по'])} · страница закрытая, обновляется еженедельно фабрикой</p>
<div class="goal"><b>Большая цель:</b> {esc(plan['большая_цель'])}.<br>
<b>Спринт:</b> {esc(plan['спринт']['цель'])}.<br>
<span style="color:var(--muted);font-size:13px">Наведите на название пункта — подробное описание. В колонке «от владельца» — вопросы к вам:
галочки, выборы, комментарии. Нажмите «Отправить ответы» внизу — я получу их в канал и размечу неделю.</span></div>
{gantt(plan)}
{''.join(epics_html)}
<section class="arch">
<h2>Архитектура — визуально</h2>
<p class="sub">Схемы — Mermaid (текст в git, рендер локально, без CDN): обновить схему = поправить строку.</p>
{mermaid_section()}
</section>
</div>
<div class="savebar">
  <button id="send">Отправить ответы</button>
  <span class="msg" id="msg">Галочки, приоритеты и комментарии уйдут одним пакетом.</span>
</div>
<script src="/js/vendor-mermaid.min.js"></script>
<script>
mermaid.initialize({{ startOnLoad: true, theme: 'dark', securityLevel: 'strict' }});
document.getElementById('send').onclick = function () {{
  var out = [];
  document.querySelectorAll('[data-item]').forEach(function (el) {{
    var v = el.type === 'checkbox' ? (el.checked ? 'да' : '') : el.value;
    if (v && el.dataset.kind !== undefined && el.tagName !== 'TR')
      out.push({{ item: el.dataset.item, kind: el.dataset.kind, value: v }});
  }});
  var btn = this, msg = document.getElementById('msg');
  if (!out.length) {{ msg.textContent = 'Пока ничего не отмечено.'; return; }}
  btn.disabled = true; msg.textContent = 'Отправляю…';
  fetch('/api/tech/feedback', {{ method: 'POST', headers: {{ 'content-type': 'application/json' }},
    body: JSON.stringify({{ page: '{SLUG}', answers: out }}) }})
    .then(function (r) {{ return r.json(); }})
    .then(function (r) {{ btn.disabled = false;
      msg.textContent = r && r.ok ? ('Записано: ' + out.length + ' ответов. Я увижу их в канале.') : 'Не получилось, попробуйте ещё раз.'; }})
    .catch(function () {{ btn.disabled = false; msg.textContent = 'Не получилось, попробуйте ещё раз.'; }});
}};
</script></body></html>"""
    OUT.write_text(html, encoding="utf-8")
    print(f"✅ {OUT.name}: {len(plan['эпики'])} эпиков, "
          f"{sum(len(e['пункты']) for e in plan['эпики'])} пунктов, {len(MERMAID_SCHEMES)} схем")
    return 0


if __name__ == "__main__":
    sys.exit(build())
