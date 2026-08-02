#!/usr/bin/env python3
"""Архив наблюдательного совета: страницы заседаний из data/council/*.json.

Зачем страницами, а не закрытым протоколом. Третье правило совета — «любой труд
должен быть оплачен честно, прозрачно и справедливо». Прозрачность начинается не с
денег, а с того, видно ли, как принимаются решения. Поэтому каждое заседание
превращается в страницу: повестка, кто предложил, как проголосовали, что решили —
и, после спринта, что из этого вышло.

Даёт два вида страниц:
  /council/<дата>.html — одно заседание
  /council/index.html  — список всех, свежие сверху

Оформление — золотая тема council.html: это одна комната, и она должна выглядеть
одинаково. Стиль вынесен в css/council.css, чтобы не жить двумя копиями.

Запуск: python council_build.py
"""
import json
import sys
from datetime import date
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "data" / "council"
OUT = ROOT / "council"
SITE = "https://bridge42worlds.academy"

DECISION_LABEL = {
    "принято": ("принято", "d-ok"),
    "отклонено": ("отклонено", "d-no"),
    "отложено": ("отложено", "d-wait"),
}
STATUS_LABEL = {"план": "повестка", "идёт": "идёт", "закрыто": "закрыто"}


def esc(s):
    return (str(s if s is not None else "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def head(title, desc, url):
    """Общая шапка. Шрифты и favicon — как на остальном сайте, стиль — золотой."""
    return f"""<!DOCTYPE html>
<html lang="ru" dir="ltr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)} — bridge42worlds</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:site_name" content="bridge42worlds">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(url)}">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:opsz@14..32&family=Source+Serif+4:opsz@8..60&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/css/council.css">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" href="/favicon.png">
</head>
<body>
<div class="page"><div class="wrap">
  <div class="topnav">
    <a class="topnav-logo" href="/lang/ru/index.html">bridge42worlds</a>
    <a href="/council.html">о проекте изнутри</a>
    <a href="/council/">заседания</a>
  </div>
"""


FOOT = """
  <footer>
    bridge42worlds · наблюдательный совет ·
    <a href="mailto:admin@bridge42worlds.academy">admin@bridge42worlds.academy</a>
  </footer>
</div></div>
</body>
</html>
"""


def votes_bar(item):
    """Полоска голосов. Показываем ЧИСЛА, а не только проценты: при пяти голосующих
    «60%» звучит солиднее, чем есть на самом деле, и это было бы враньём формой."""
    votes = item.get("votes") or {}
    total = sum(votes.values())
    if not total:
        return ""
    rows = []
    for opt in (item.get("options") or list(votes)):
        n = votes.get(opt, 0)
        pct = round(n * 100 / total)
        rows.append(
            f'<div class="vrow"><span class="vname">{esc(opt)}</span>'
            f'<span class="vbar"><i style="width:{pct}%"></i></span>'
            f'<span class="vnum">{n}</span></div>')
    return f'<div class="votes">{"".join(rows)}<p class="vtotal">всего голосов: {total}</p></div>'


def agenda_item(item, n):
    label, cls = DECISION_LABEL.get(item.get("decision", ""), ("на голосовании", "d-open"))
    frm = item.get("from") or []
    frm_html = (f'<p class="from">предложил{"и" if len(frm) > 1 else ""}: '
                f'{esc(" · ".join(frm))}</p>') if frm else ""

    merged = item.get("merged") or []
    merged_html = ""
    if merged:
        # Исходные формулировки показываем всегда: человек должен узнать своё
        # предложение в сведённой повестке, иначе сведение выглядит как подмена.
        li = "".join(f"<li>{esc(m)}</li>" for m in merged)
        merged_html = (f'<details class="merged"><summary>сведено из '
                       f'{len(merged)} предложений</summary><ul>{li}</ul></details>')

    why = item.get("why")
    why_html = f'<p class="why"><b>Почему:</b> {esc(why)}</p>' if why else ""

    outcome = item.get("outcome")
    out_html = (f'<p class="outcome"><b>Что вышло:</b> {esc(outcome)}</p>'
                if outcome else "")

    # Голоса с обоснованием. Публикуем ОБЯЗАТЕЛЬНО: голос без объяснения от участника,
    # который не устаёт и не спит, — это не участие, а давление числом. Люди должны
    # видеть, почему модель решила так, и иметь по чему возразить.
    voices = item.get("voices") or []
    voices_html = ""
    if voices:
        rows = "".join(
            f'<div class="voice"><span class="vby">{esc(v.get("by",""))}</span>'
            f'<span class="vch">{esc(v.get("choice",""))}</span>'
            f'<p class="vwhy">{esc(v.get("why",""))}</p></div>'
            for v in voices)
        voices_html = f'<div class="voices"><h4>Как голосовали и почему</h4>{rows}</div>'

    # Модель не решает в одиночку. Если её голос оказался решающим — вопрос ждёт живых.
    need_html = ("" if not item.get("needs_human") else
                 '<p class="needhuman">Голос модели здесь оказался решающим — '
                 'вопрос ждёт живых голосов и на этом заседании не закрывается.</p>')

    return f"""
  <article class="item">
    <div class="ihead">
      <span class="inum">{n}</span>
      <h3>{esc(item.get("title", "Без названия"))}</h3>
      <span class="dec {cls}">{esc(label)}</span>
    </div>
    {frm_html}
    <p class="body">{esc(item.get("body", ""))}</p>
    {merged_html}
    {votes_bar(item)}
    {voices_html}
    {need_html}
    {why_html}
    {out_html}
  </article>"""


def sprint_block(s):
    if not s:
        return ""
    def lst(key, title, cls=""):
        items = s.get(key) or []
        if not items:
            return ""
        li = "".join(f"<li>{esc(x)}</li>" for x in items)
        return f'<div class="sp {cls}"><h4>{title}</h4><ul>{li}</ul></div>'
    span = ""
    if s.get("from") and s.get("to"):
        span = f'<p class="muted">{esc(s["from"])} — {esc(s["to"])}</p>'
    return f"""
  <section>
    <p class="kicker">Спринт по итогам</p>
    <h2>Что взяли в работу</h2>
    {span}
    <div class="sprint">
      {lst("planned", "Запланировано")}
      {lst("done", "Сделано", "sp-done")}
      {lst("carried", "Перенесено", "sp-carry")}
    </div>
  </section>"""


def build_session(data):
    d = data.get("date", "")
    num = data.get("number", "?")
    status = STATUS_LABEL.get(data.get("status", ""), data.get("status", ""))
    title = f"Заседание №{num} · {d}"
    desc = data.get("opened", "Наблюдательный совет bridge42worlds")

    items = data.get("agenda") or []
    items_html = "".join(agenda_item(it, i + 1) for i, it in enumerate(items))
    nxt = data.get("next") or []
    nxt_html = ""
    if nxt:
        li = "".join(f"<li>{esc(x)}</li>" for x in nxt)
        nxt_html = f"""
  <section>
    <p class="kicker">Дальше</p>
    <h2>Уже видно в следующую повестку</h2>
    <ul class="next">{li}</ul>
  </section>"""

    html = head(title, desc, f"{SITE}/council/{d}.html") + f"""
  <div class="hero">
    <p class="eyebrow">наблюдательный совет · {esc(status)}</p>
    <h1>Заседание <span class="n">№{esc(num)}</span></h1>
    <p class="dek">{esc(d)}{" · " + esc(data["opened"]) if data.get("opened") else ""}</p>
  </div>

  <section>
    <p class="kicker">Повестка</p>
    <h2>{len(items)} {"вопрос" if len(items) == 1 else "вопроса" if 1 < len(items) < 5 else "вопросов"}</h2>
    {items_html or '<p class="muted">Повестка пока пуста.</p>'}
  </section>
{sprint_block(data.get("sprint"))}{nxt_html}
""" + FOOT
    return html


def build_index(sessions):
    rows = []
    for s in sessions:
        d = s.get("date", "")
        items = s.get("agenda") or []
        decided = sum(1 for i in items if i.get("decision"))
        status = STATUS_LABEL.get(s.get("status", ""), s.get("status", ""))
        rows.append(
            f'<tr><td><a href="/council/{esc(d)}.html">№{esc(s.get("number","?"))}</a></td>'
            f'<td>{esc(d)}</td><td>{len(items)}</td><td>{decided}</td>'
            f'<td class="st">{esc(status)}</td></tr>')
    table = ("".join(rows) if rows else
             '<tr><td colspan="5" class="muted">Заседаний пока не было.</td></tr>')
    html = head("Заседания совета", "Архив заседаний наблюдательного совета bridge42worlds",
                f"{SITE}/council/") + f"""
  <div class="hero">
    <p class="eyebrow">наблюдательный совет</p>
    <h1>Заседания и <span class="n">решения</span></h1>
    <p class="dek">Ничего закрытого: повестка, голоса, решения и то, что из них вышло.
      Отклонённое остаётся здесь вместе с причиной.</p>
  </div>

  <section>
    <p class="kicker">Архив</p>
    <h2>Все заседания</h2>
    <div class="tw"><table>
      <tr><th>№</th><th>Дата</th><th>Вопросов</th><th>Решено</th><th>Статус</th></tr>
      {table}
    </table></div>
    <p class="muted">Как попасть в совет и предложить вопрос — на странице
      <a href="/council.html">о проекте изнутри</a>.</p>
  </section>
""" + FOOT
    return html


def main():
    if not SRC.exists():
        print("нет data/council — нечего собирать")
        return 1
    # Заседание — это файл с датой в имени, и только он. Раньше сюда шёл любой *.json
    # из папки: рядом лежат строки страницы (страница.<язык>.json) и тексты писем,
    # и они превращались в «заседание №?» с пустой повесткой, а список показывал
    # семь заседаний вместо одного. Соседние файлы будут появляться и дальше —
    # значит отбирать надо по признаку заседания, а не по расширению.
    #
    # Черновики повестки (черновик-<дата>.json) тоже не берём: у них та же дата, что
    # у заседания, и они перезаписывали бы его страницу — поймано первым же прогоном.
    # Черновик становится заседанием только когда человек перенесёт его руками.
    files = sorted((f for f in SRC.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].json")),
                   reverse=True)
    if not files:
        print("в data/council нет заседаний — собираю только пустой список")
    sessions = []
    OUT.mkdir(parents=True, exist_ok=True)
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"битый файл {f.name}: {e}")
            continue
        if not data.get("date"):
            print(f"  ⚠️ {f.name}: нет даты — это не заседание, пропускаю")
            continue
        sessions.append(data)
        page = OUT / f"{data.get('date', f.stem)}.html"
        page.write_text(build_session(data), encoding="utf-8")
        print(f"  заседание №{data.get('number','?')} → {page.relative_to(ROOT)}")
    (OUT / "index.html").write_text(build_index(sessions), encoding="utf-8")
    print(f"список → {(OUT / 'index.html').relative_to(ROOT)} ({len(sessions)} заседаний)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
