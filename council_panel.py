#!/usr/bin/env python3
"""Панель совета: /lang/<язык>/council.html на всех языках.

Замысел стратега (задачи/СОВЕТ-ПАНЕЛЬ.md), слова владельца 2026-08-04: «я уже зашёл —
зачем мне форму заполнять; нужны предыдущие голосования, принятие решений, текущий
бюджет; кто в совете, их роли — это структура управления, а не просто лирика; где
переключался на английский — путь будет стандартный».

Правило панели: первый экран без прокрутки отвечает на три вопроса — что решается сейчас,
подал ли я голос, что от меня ждут. Объяснений нет: «общие слова ок, но это всё есть
в about». Документ «Проект изнутри» живёт отдельно на /inside.html.

Живая часть (вступление, голоса, кабинет) — js/council-live.js, той же ручкой API.
Здесь — каркас: шапка-строка, решения, состав, неделя, подвал.

    python council_panel.py            все языки
    python council_panel.py ru en      выбранные
"""
import json
import string
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", line_buffering=True)
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent
LANGS = ("ru", "en", "es", "ar", "fr")

# Строки панели. ru и en полные; es/ar/fr временно падают на en — владелец: «английский ок»,
# но путь и переключатель нужны сразу, а не после перевода.
T = {
    "ru": {
        "title": "Совет", "h1": "Наблюдательный совет",
        "meeting": "Заседание №1 · воскресенье 9 августа · повестка закрывается в пятницу",
        "decisions": "Решения совета",
        "no_decisions": "Решений пока нет — заседание идёт. Итоги появятся здесь вечером {d} {m}.",
        "council": "Состав совета", "members_n": "участников",
        "r_owner": "Инвестор", "r_owner_d": "пока проект не самодостаточен: оплачивает конвейер и решает ценностные развилки. Роль временная — переход к самодостаточности вынесен на голосование",
        "r_arch": "Архитектор", "r_arch_d": "готовит вопросы, отвечает за исполнение решений",
        "r_strat": "Стратег", "r_strat_d": "секретарь: повестка, резюме, отчёт о сделанном",
        "r_members": "Участники", "r_members_d": "читатели, дошедшие до порога: предлагают и голосуют",
        "ai": "ИИ",
        "rules_line": "голос ИИ всегда с обоснованием · решающий голос ИИ вопрос не закрывает · предложение нельзя отклонить по существу",
        "week": "Неделя",
        "w_budget": "Бюджет", "w_done": "Сделано", "w_plan": "План",
        "w_plan_v": "вектор как несущая конструкция · панель совета · карточки и французский",
        "w_done_v": "формулы на проде · заседание №1 подготовлено · перевод чинится по полям",
        "more": "подробнее",
        "rules": "Правила совета", "inside": "Проект изнутри",
        "memo_h": "Как устроен совет",
        "memo": [('Совет решает, а не советует', 'Решение, принятое голосованием, исполняется. Спорить можно до голосования и на следующем заседании — но не молча не выполнять.'), ('Заседания по воскресеньям', 'В пятницу повестка закрывается и уходит письмом. В воскресенье вечером голосование закрывается, итоги приходят почтой и открываются всем.'), ('Голос можно изменить', 'Пока заседание идёт, решение переписывается: мнение меняется, когда читаешь чужие доводы. После закрытия — нет.'), ('Расклад скрыт до конца', 'Видно только, сколько человек уже высказалось. Иначе первый голос подсказывает ответ остальным.'), ('Любой может заморозить вопрос', 'Заморозка снимает вопрос с голосования и требует объяснения. Имя заморозившего не раскрывается, вопрос возвращается переформулированным.'), ('ИИ-участники равны, но не решают за людей', 'Их голос всегда с обоснованием. Решающий голос машины вопрос не закрывает — кроме случая, когда вопрос заморожен второй раз.'), ('Предложить может каждый участник', 'Предложение нельзя отклонить по существу — только вынести на голосование. Пока оно не в повестке, автор может его изменить или снять.')],
    },
    "en": {
        "title": "Council", "h1": "Observers' council",
        "meeting": "Meeting #1 · Sunday, August 9 · agenda closes Friday",
        "decisions": "Council decisions",
        "no_decisions": "No decisions yet — the meeting is under way. Results will appear here in the evening of {m} {d}.",
        "council": "Council members", "members_n": "members",
        "r_owner": "Investor", "r_owner_d": "while the project is not yet self-sufficient: pays for the pipeline and decides value trade-offs. A temporary role — the move to self-sufficiency is on the ballot",
        "r_arch": "Architect", "r_arch_d": "prepares questions, answers for execution of decisions",
        "r_strat": "Strategist", "r_strat_d": "secretary: agenda, summaries, progress report",
        "r_members": "Members", "r_members_d": "readers past the threshold: propose and vote",
        "ai": "AI",
        "rules_line": "AI votes always come with reasoning · a decisive AI vote does not close a question · a proposal cannot be rejected on merits",
        "week": "This week",
        "w_budget": "Budget", "w_done": "Done", "w_plan": "Plan",
        "w_plan_v": "vector as the core · council panel · cards and French",
        "w_done_v": "formulas live · meeting #1 prepared · translation now repairs by fields",
        "more": "details",
        "rules": "Council rules", "inside": "Inside the project",
        "memo_h": "How the council works",
        "memo": [('The council decides, it does not advise', 'A decision taken by vote is carried out. Argue before the vote or at the next meeting — but do not silently ignore it.'), ('Meetings on Sundays', 'The agenda closes on Friday and goes out by email. On Sunday evening voting closes, results are mailed and opened to everyone.'), ('A vote can be changed', "While the meeting runs, your decision can be rewritten: opinions change when you read other people's reasoning. After it closes, they cannot."), ('The tally is hidden until the end', 'Only the number of people who have spoken is visible. Otherwise the first vote tells everyone else the answer.'), ('Anyone may freeze a question', 'Freezing takes the question off the vote and requires an explanation. The author is not disclosed; the question returns rephrased.'), ('AI members are equal but do not decide for people', 'Their vote always comes with reasoning. A decisive AI vote does not close a question — except when it has been frozen twice.'), ('Any member may propose', 'A proposal cannot be rejected on merits, only put to a vote. Until it reaches the agenda, its author can edit or withdraw it.')],
    },
}


def _load_translations():
    """ar/es/fr — из файлов стратега (data/council/panel-strings.<lang>.json), а не из
    словаря в коде. Разграничение прямое: формулировки — его работа, каркас — моя;
    он не лезет в py/js, я не переписываю его тексты. Сверка состава ключей — при
    загрузке, молча подставленный английский хуже честного падения."""
    for lang in ("ar", "es", "fr"):
        f = ROOT / "data" / "council" / f"panel-strings.{lang}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        missing = set(T["ru"]) - set(d)
        if missing:
            print(f"  ⚠️ {lang}: в переводе панели нет ключей {sorted(missing)[:5]} — падаю на en")
            continue
        T[lang] = d


_load_translations()


def budget_line():
    """Строка бюджета из данных, а не из головы: cost-summary пишет tools/cost_report.py.
    Нет файла — честный прочерк, выдуманное число хуже пустого."""
    p = ROOT / "data" / "cost-summary.json"
    if not p.exists():
        return "—"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        month = d.get("month_usd") or d.get("month") or 0
        return f"${month:.2f} / $250"
    except Exception:
        return "—"


# Шапка панели — из НАСТОЯЩЕЙ повестки, а не из строки в коде.
#
# 13 августа страница совета встречала фразой «Заседание №1 · воскресенье 9 августа»,
# хотя шло заседание №2 от 16-го: дата была вписана руками при сборке первой панели и
# устарела в тот же день, когда заседание сменилось. Дата на видном месте, которая врёт,
# хуже отсутствующей: по ней люди планируют, успеют ли проголосовать.
_MONTHS = {
    "ru": ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
           "сентября", "октября", "ноября", "декабря"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December"],
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
           "septiembre", "octubre", "noviembre", "diciembre"],
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
           "septembre", "octobre", "novembre", "décembre"],
    "ar": ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس",
           "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
}
_MEET_FMT = {
    "ru": "Заседание №{n} · {d} {m} · повестка закрывается в пятницу",
    "en": "Meeting #{n} · {m} {d} · agenda closes on Friday",
    "es": "Sesión n.º {n} · {d} de {m} · el orden del día se cierra el viernes",
    "fr": "Séance n° {n} · {d} {m} · l'ordre du jour se clôt vendredi",
    "ar": "الجلسة رقم {n} · {d} {m} · يُغلق جدول الأعمال يوم الجمعة",
}


def meeting_line(lang):
    """Строка «Заседание №N · дата» по data/council/upcoming.json."""
    import datetime
    p = ROOT / "data" / "council" / "upcoming.json"
    if not p.exists():
        return T.get(lang, T["en"])["meeting"]
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        dt = datetime.date.fromisoformat(str(d.get("date")))
    except Exception:
        return T.get(lang, T["en"])["meeting"]
    months = _MONTHS.get(lang, _MONTHS["en"])
    fmt = _MEET_FMT.get(lang, _MEET_FMT["en"])
    return fmt.format(n=d.get("number") or 1, d=dt.day, m=months[dt.month - 1])


def no_decisions_line(lang):
    """«Итогов пока нет» — с датой ТЕКУЩЕГО заседания, а не первого."""
    import datetime
    txt = T.get(lang, T["en"])["no_decisions"]
    if "{d}" not in txt:
        return txt
    p = ROOT / "data" / "council" / "upcoming.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        dt = datetime.date.fromisoformat(str(d.get("date")))
    except Exception:
        return txt.replace(" вечером {d} {m}", "").replace(" in the evening of {m} {d}", "")
    months = _MONTHS.get(lang, _MONTHS["en"])
    return txt.format(d=dt.day, m=months[dt.month - 1])


def memo_html(lang):
    """Памятка «как устроен совет» — принципы и порядок работы, без ссылок в сторону.

    Раньше внизу панели стояла ссылка «Проект изнутри»: она вела на большой документ,
    который начинается с гида по сайту и ссылки на about. Человек, дочитавший до состава
    совета, хочет узнать правила совета, а не открыть ещё одну страницу про проект
    (владелец 15 августа). Семь пунктов отвечают на всё, что спрашивают в первый раз.
    """
    t = T.get(lang, T["en"])
    return chr(10).join(
        f"<dt>{h}</dt><dd>{d}</dd>" for h, d in t.get("memo", T["en"]["memo"]))


def build(lang):
    t = T.get(lang, T["en"])
    b = budget_line()
    return f"""
<div class="cp">
  <div class="cp-head">{meeting_line(lang)}</div>

  <div id="council-live"></div>

  <h2>{t["decisions"]}</h2>
  <div class="cp-decisions"><p class="cp-empty">{no_decisions_line(lang)}</p></div>

  <h2>{t["council"]} <span class="fx-n" id="cp-members"></span></h2>
  <div class="cp-roles">
    <div class="cp-role"><b>{t["r_owner"]}</b><span>{t["r_owner_d"]}</span></div>
    <div class="cp-role"><b>{t["r_arch"]}</b><i class="cp-ai">{t["ai"]}</i><span>{t["r_arch_d"]}</span></div>
    <div class="cp-role"><b>{t["r_strat"]}</b><i class="cp-ai">{t["ai"]}</i><span>{t["r_strat_d"]}</span></div>
    <div class="cp-role"><b>{t["r_members"]}</b><span>{t["r_members_d"]}</span></div>
  </div>
  <p class="cp-rules-line">{t["rules_line"]}</p>

  <h2>{t["week"]}</h2>
  <div class="cp-week">
    <div class="cp-row"><b>{t["w_budget"]}</b><span>{b}</span></div>
    <div class="cp-row"><b>{t["w_done"]}</b><span>{t["w_done_v"]}</span></div>
    <div class="cp-row"><b>{t["w_plan"]}</b><span>{t["w_plan_v"]}</span></div>
  </div>

  <h2>{t["memo_h"]}</h2>
  <dl class="cp-memo">
    {memo_html(lang)}
  </dl>
</div>
"""


def main():
    langs = sys.argv[1:] or LANGS
    sys.path.insert(0, str(ROOT))
    import generate

    raw = (ROOT / "templates" / "tags-cloud.html").read_text(encoding="utf-8")
    i = raw.find('<div class="tag-cloud"')
    j = raw.find('<script', i)
    made = 0
    for lang in langs:
        t = T.get(lang, T["en"])
        shell = raw[:i] + "${PANEL}\n" + raw[j:]
        page = string.Template(shell).safe_substitute(
            lang=lang, dir=generate.dir_for(lang), asset_ver=generate.asset_ver(),
            goatcounter=getattr(generate, "GOATCOUNTER", ""),
            fav_title="", version_toggle_html="", mini_graph_filters_html="",
            selected_tags_html="", tags_cloud_html="", treemap_data="[]",
            tags_title=t["h1"], tags_subtitle="",
            PANEL=build(lang))
        page = page.replace("<title>Tags — bridge42worlds</title>",
                            f"<title>{t['title']} — bridge42worlds</title>")
        page = page.replace("</body>",
                            f'<script src="/js/council-live.js?v={generate.asset_ver()}"></script></body>')
        out = ROOT / "lang" / lang / "council.html"
        out.write_text(page, encoding="utf-8")
        made += 1
        print(f"  ✅ {lang} → {out}")

    # Корневой /council.html — перенаправление на язык читателя: старые ссылки и письма
    # не должны умереть. Язык берём из сохранённого выбора, иначе из браузера.
    redirect = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>bridge42worlds council</title>
<script>
var l = null;
try { l = localStorage.getItem('b42_lang'); } catch (e) {}
if (!l) { l = (navigator.language || 'en').slice(0, 2); }
if (['ru','en','es','ar','fr'].indexOf(l) < 0) l = 'en';
location.replace('/lang/' + l + '/council.html' + location.search);
</script>
<meta http-equiv="refresh" content="1;url=/lang/en/council.html">
</head><body><a href="/lang/en/council.html">council</a></body></html>"""
    (ROOT / "council.html").write_text(redirect, encoding="utf-8")
    print(f"  ✅ корневой /council.html — перенаправление; страниц: {made}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
