#!/usr/bin/env python3
"""Страница «изнутри» на всех языках сайта.

Была одна русская страница-файл. Стало: текст отдельно (data/council/страница.<язык>.json),
разметка отдельно (здесь), результат — lang/<язык>/council.html на каждый язык.

Почему так, а не «перевести html целиком». Модель, переводя разметку, рано или поздно
съедает закрывающий тег или переводит имя класса — и страница разъезжается молча.
Кроме того, при любой правке пришлось бы переводить всё заново. Так устроен и гид
(about.json + шаблон), это наш проверенный путь.

Зачем вообще переводить. Приглашение в совет показывается только там, где страница
существует; пока она была русской, арабский читатель — а это приоритетная аудитория —
не получал его вовсе. Отправлять человека на стену на чужом языке хуже, чем не звать.

Запуск:
    python council_page.py             # все языки, у которых есть файл строк
    python council_page.py ru ar       # только указанные
"""
import json
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "data" / "council"
SITE = "https://bridge42worlds.academy"
RTL = {"ar", "he", "fa", "ur"}


def esc(s):
    return (str(s if s is not None else "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def row(*cells):
    return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


def th(*cells):
    return "<tr>" + "".join(f"<th>{esc(c)}</th>" for c in cells) + "</tr>"


# Опросы из документа УБРАНЫ (стратег 2026-08-04, владелец подтвердил: «нажал не то»).
# На одной странице стояли ДВА элемента, выглядящих как голосование, и настоящий из них —
# на двадцать тысяч пикселей ниже: владелец проголосовал в опрос-пустышку, голос остался
# в браузере, в базе совета ноль. Мнение собирается там же, где голосуют, — на панели.
def poll(pid, question, options, t):
    opts = "".join(
        f'<button type="button" data-v="{esc(o)}">{esc(o)}</button>' for o in options)
    return f"""
    <div class="poll" data-poll="{esc(pid)}">
      <p class="q">{esc(t["poll_ask"])}</p>
      <p class="sub">{esc(question)}</p>
      <div class="opts">{opts}</div>
      <p class="said"></p>
    </div>"""


def build(lang, t):
    d = "rtl" if lang in RTL else "ltr"
    url = f"{SITE}/lang/{lang}/council.html"

    believe = "".join(row(f'<b>{esc(t[f"believe_{i}_a"])}</b>', esc(t[f"believe_{i}_b"]))
                      for i in range(1, 6))
    hows = "".join(row(f'<b>{esc(t[f"how_{i}_a"])}</b>', esc(t[f"how_{i}_b"]))
                   for i in range(1, 5))
    nexts = "".join(row(f'<b>{esc(t[f"next_{i}_a"])}</b>', esc(t[f"next_{i}_b"]))
                    for i in range(1, 6))
    opens = "".join(row(esc(t[f"open_{i}_a"]), esc(t[f"open_{i}_b"])) for i in range(1, 4))
    rules = "".join(row(f'<b>{esc(t[f"rule_{i}_a"])}</b>', esc(t[f"rule_{i}_b"]))
                    for i in range(1, 4))

    def st(key, cls):
        return f'<span class="st {cls}">{esc(t[key])}</span>'

    state_rows = (
        row(esc(t["row_articles"]), st("st_works", "st-ok"), esc(t["row_articles_d"])) +
        row(esc(t["row_full"]), st("st_works", "st-ok"), "601") +
        row(esc(t["row_express"]), st("st_works", "st-ok"), "1509") +
        row(esc(t["row_langs"]), f'<span class="st st-ok">{esc(t["row_langs_s"])}</span>', esc(t["row_langs_d"])) +
        row(esc(t["row_depth"]), f'<span class="st st-ok">{esc(t["row_depth_s"])}</span>', esc(t["row_depth_d"])) +
        row(esc(t["row_refs"]), st("st_works", "st-ok"), esc(t["row_refs_d"])) +
        row(esc(t["row_graph"]), st("st_works", "st-ok"), esc(t["row_graph_d"])) +
        row(esc(t["row_search"]), st("st_live", "st-ok"), esc(t["row_search_d"])) +
        row(esc(t["row_course"]), st("st_works", "st-ok"), esc(t["row_course_d"])) +
        row(esc(t["row_tutor"]), st("st_live", "st-ok"), esc(t["row_tutor_d"])) +
        row(esc(t["row_order"]), st("st_part", "st-part"), esc(t["row_order_d"])) +
        row(esc(t["row_reuse"]), st("st_broken", "st-no"), esc(t["row_reuse_d"])) +
        row(esc(t["row_arxiv"]), st("st_plan", "st-plan"), esc(t["row_arxiv_d"])))

    money_rows = (
        row(esc(t["money_1_a"]), "<b>~$0,06–0,09</b>", esc(t["money_1_c"])) +
        row(esc(t["money_2_a"]), "<b>~$0,01–0,02</b>", esc(t["money_2_c"])) +
        row(esc(t["money_3_a"]), "<b>$0</b>", esc(t["money_3_c"])) +
        row(esc(t["money_4_a"]), f'<b>{esc(t["money_4_b"])}</b>', esc(t["money_4_c"])))

    funnel_rows = (
        row(f'<b>{esc(t["funnel_0_a"])}</b>', esc(t["funnel_0_b"]), esc(t["funnel_0_c"]),
            st("st_plan", "st-plan")) +
        row(f'<b>{esc(t["funnel_1_a"])}</b>', esc(t["funnel_1_b"]), "~$0,01–0,02",
            st("st_works", "st-ok")) +
        row(f'<b>{esc(t["funnel_2_a"])}</b>', esc(t["funnel_2_b"]), "~$0,03–0,05",
            st("st_part", "st-part")))

    nums = "".join(
        f'<div><b>{v}</b><span>{esc(t[k])}</span></div>'
        for k, v in (("n_articles", "2110"), ("n_days", "382"), ("n_langs", "5"),
                     ("n_tags", "369"), ("n_laws", "145"), ("n_sci", "201")))

    return f"""<!DOCTYPE html>
<html lang="{lang}" dir="{d}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(t["page_title"])} — bridge42worlds</title>
<meta name="description" content="{esc(t["meta_desc"])}">
<meta property="og:site_name" content="bridge42worlds">
<meta property="og:title" content="{esc(t["og_title"])}">
<meta property="og:description" content="{esc(t["og_desc"])}">
<meta property="og:url" content="{url}">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:opsz@14..32&family=Source+Serif+4:opsz@8..60&family=Noto+Naskh+Arabic:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/css/council.css">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" href="/favicon.png">
</head>
<body>
<div class="page"><div class="wrap">

  <div class="topnav">
    <a class="topnav-logo" href="/lang/{lang}/index.html">bridge42worlds</a>
    <a href="/lang/{lang}/about.html">{esc(t["nav_about"])}</a>
    <a href="/learn.html">{esc(t["nav_learn"])}</a>
    <a href="/council/">{esc(t["nav_sessions"])}</a>
  </div>

  <div class="hero">
    <p class="eyebrow">{esc(t["hero_eyebrow"])}</p>
    <h1>{esc(t["hero_h1_a"])} <span class="n">42</span> {esc(t["hero_h1_b"])}</h1>
    <p class="dek">{esc(t["hero_dek"])}</p>
  </div>

  <section>
    <p class="kicker">{esc(t["why_kicker"])}</p>
    <h2>{esc(t["why_h2"])}</h2>
    <p class="lead">{esc(t["why_lead"])}</p>
    <p>{t["why_body"]}</p>
    <div class="tw"><table>{th(t["why_th_1"], t["why_th_2"])}{believe}</table></div>
  </section>

  <section>
    <p class="kicker">{esc(t["now_kicker"])}</p>
    <h2>{esc(t["now_h2"])}</h2>
    <div class="num" id="live-num">{nums}</div>
    <p class="muted">{esc(t["now_note"])}</p>
    <div class="tw"><table>{th(t["now_th_1"], t["now_th_2"], t["now_th_3"])}{state_rows}</table></div>
  </section>

  <section>
    <p class="kicker">{esc(t["how_kicker"])}</p>
    <h2>{esc(t["how_h2"])}</h2>
    <p>{esc(t["how_p"])}</p>
    <div class="tw"><table>{th(t["how_th_1"], t["how_th_2"])}{hows}</table></div>
    <h3>{esc(t["how_path_h3"])}</h3>
    <p class="muted">{esc(t["how_path"])}</p>
    <p>{esc(t["how_check"])}</p>
  </section>

  <section>
    <p class="kicker">{esc(t["money_kicker"])}</p>
    <h2>{esc(t["money_h2"])}</h2>
    <p>{esc(t["money_p"])}</p>
    <div class="tw"><table>{th(t["money_th_1"], t["money_th_2"], t["money_th_3"])}{money_rows}</table></div>
    <div class="note">{t["money_note"]}</div>
      </section>

  <section>
    <p class="kicker">{esc(t["funnel_kicker"])}</p>
    <h2>{esc(t["funnel_h2"])}</h2>
    <p>{esc(t["funnel_p"])}</p>
    <div class="tw"><table>{th(t["funnel_th_1"], t["funnel_th_2"], t["funnel_th_3"], t["funnel_th_4"])}{funnel_rows}</table></div>
    <div class="note">{t["funnel_note"]}</div>
      </section>

  <section>
    <p class="kicker">{esc(t["next_kicker"])}</p>
    <h2>{esc(t["next_h2"])}</h2>
    <div class="tw"><table>{th(t["next_th_1"], t["next_th_2"])}{nexts}</table></div>
    <h3>{esc(t["open_h3"])}</h3>
    <p>{esc(t["open_p"])}</p>
    <div class="tw"><table>{th(t["open_th_1"], t["open_th_2"])}{opens}</table></div>
      </section>

  <section>
    <p class="kicker">{esc(t["join_kicker"])}</p>
    <h2>{esc(t["join_h2"])}</h2>
    <p class="lead">{esc(t["join_lead"])}</p>
    <p>{esc(t["join_p"])}</p>
    <h3>{esc(t["rules_h3"])}</h3>
    <div class="tw"><table>{th(t["rules_th_1"], t["rules_th_2"])}{rules}</table></div>
    <p class="muted">{esc(t["rules_note"])}</p>
    <h3>{esc(t["enter_h3"])}</h3>
    <p>{esc(t["enter_p"])}</p>

    <div class="join">
      <label for="j-name">{esc(t["f_name"])}</label>
      <input id="j-name" type="text" autocomplete="name" placeholder="{esc(t["f_name_ph"])}">
      <label for="j-mail">{esc(t["f_mail"])}</label>
      <input id="j-mail" type="email" autocomplete="email" placeholder="name@example.com">
      <label for="j-note">{esc(t["f_note"])}</label>
      <textarea id="j-note" placeholder="{esc(t["f_note_ph"])}"></textarea>
      <div class="row">
        <button type="button" id="j-make">{esc(t["b_key"])}</button>
        <button type="button" class="ghost" id="j-mail-btn" hidden>{esc(t["b_mail"])}</button>
        <button type="button" class="ghost" id="j-copy" hidden>{esc(t["b_copy"])}</button>
      </div>
      <div class="token" id="j-token" hidden></div>
    </div>
    <p class="muted" style="margin-top:14px">{esc(t["honest"])}</p>
  </section>

  <footer>
    bridge42worlds · {esc(t["foot"])}
    <a href="mailto:admin@bridge42worlds.academy">admin@bridge42worlds.academy</a>
  </footer>

</div></div>
<script>window.B42_COUNCIL_T = {json.dumps({k: t[k] for k in (
    "poll_saved", "b_key_done", "b_copied", "b_copy_manual", "key_note",
    "letter_subject", "letter_title", "letter_name", "letter_mail", "letter_key",
    "letter_answers", "letter_msg", "sent_ok", "sent_no")}, ensure_ascii=False)};</script>
<script src="/js/council.js"></script>
</body>
</html>
"""


def main():
    langs = sys.argv[1:] or [p.name.split(".")[1] for p in SRC.glob("страница.*.json")]
    made = 0
    for lang in langs:
        f = SRC / f"страница.{lang}.json"
        if not f.exists():
            print(f"{lang}: нет файла строк {f.name} — пропускаю")
            continue
        t = json.loads(f.read_text(encoding="utf-8"))
        base = json.loads((SRC / "страница.ru.json").read_text(encoding="utf-8"))
        # Недостающие ключи берём из русского и ГОВОРИМ об этом: молча подставить
        # чужой язык — ровно та ошибка, за которую мы ловим себя весь проект.
        missing = [k for k in base if k not in t]
        if missing:
            print(f"  ⚠️ {lang}: не переведено ключей {len(missing)} — будут по-русски: "
                  + ", ".join(missing[:6]) + ("…" if len(missing) > 6 else ""))
            t = {**base, **t}
        # Документ переезжает на inside.html: /council.html теперь ПАНЕЛЬ совета
        # (замысел стратега, задачи/СОВЕТ-ПАНЕЛЬ.md; владелец: «я уже зашёл — зачем мне
        # форма; нужны решения, бюджет, состав — это структура управления, а не лирика»).
        out = ROOT / "lang" / lang / "inside.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(build(lang, t), encoding="utf-8")
        print(f"  {lang} → {out.relative_to(ROOT)}")
        made += 1
    print(f"собрано страниц: {made}")
    return 0 if made else 1


if __name__ == "__main__":
    sys.exit(main())
