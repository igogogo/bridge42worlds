#!/usr/bin/env python3
"""Письмо автору: его работа пересказана, вот ссылка, вот его страница.

Владелец 31.08: «рассылка отличная штука, мы даже что-то начали, но застопорилось;
нужен текст письма, ссылка — и начнём». Начиналось это ещё 31 июля: «целевая
аудитория — арабский мир, это АВТОРЫ; они найдут себя на сайте и будут писать».
Сторож почты (tools/mail_watch.py) с тех пор ждёт ответов на пяти ящиках, а писем
не было, потому что первым письмом должны были написать мы.

Правила, зашитые сюда, важнее кода:

  · пишем ЧЕЛОВЕКУ О ЕГО РАБОТЕ. Не рассылка, не предложение, не подписка. Адрес
    берётся из самой работы, где он напечатан для переписки, и используется один
    раз по назначению;
  · один автор — одно письмо. Кому написали, помним (data/outreach-log.jsonl), и
    второй раз не пишем никогда;
  · в каждом письме сказано, как убрать свою страницу одной строкой. Попросили —
    убираем в тот же день, без выяснений;
  · отправляем с author@bridge42worlds.academy: ответ приходит в ящик, за которым
    следит сторож, а не в пустоту.

    python tools/author_letter.py "Y. Li" --dry            показать письмо
    python tools/author_letter.py "Y. Li" --lang ar --dry  по-арабски
    python tools/author_letter.py "Y. Li" --to a@b.edu --send
    python tools/author_letter.py --log                    кому уже писали
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SITE = "https://bridge42worlds.academy"
FROM = "author@bridge42worlds.academy"
LOG = ROOT / "data" / "outreach-log.jsonl"
GRAPH = ROOT / "data" / "authors-graph.json"

# Тон: делимся, а не учим; коротко, без хайпа. Каждый абзац отвечает на вопрос,
# который человек задаст сам: кто вы, при чём тут я, что от меня хотят, как это убрать.
LETTER = {
    "en": {
        "subject": "We retold your paper {aid} in plain language",
        "body": """Hello{name},

We are bridge42worlds, a small non-commercial project. We read arXiv papers in
full and retell them in plain language in five languages, Arabic among them, so
that a student or an engineer outside the field can follow what was done.

We did that with your paper {aid}. The whole retelling is below, so you can judge
it without going anywhere and without opening any link.

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{retitle}

{retext}
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{machine}
On the site the same text has {figures_note}a map of the concepts it touches. We put
no link in this letter on purpose — for your own safety: letters with links are
exactly how people get caught, and a stranger's link deserves no trust. The address
is {site}, and you will find the paper there yourself: by your name or by its
number {aid}.

Two more things and we leave you alone.

If we got something wrong, tell us and we will fix it.

If you would rather not be there at all, reply with one line and the page comes
down the same day. No questions asked.

Nothing is for sale here and there is nothing to sign up for. We wrote because it
is your work and you should know where it is.

{sign}""",
    },
    "ar": {
        "subject": "أعدنا سرد بحثكم {aid} بلغة مبسّطة",
        "body": """السلام عليكم{name}،

نحن bridge42worlds، مشروع صغير غير ربحي. نقرأ أبحاث arXiv كاملةً ونعيد سردها بلغة
مبسّطة بخمس لغات، من بينها العربية، ليتمكّن طالب أو مهندس من خارج التخصّص من متابعة
ما أُنجز.

فعلنا ذلك ببحثكم {aid}. السرد كاملاً أدناه، لتحكموا عليه دون الذهاب إلى أي مكان
ودون فتح أي رابط.

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{retitle}

{retext}
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{machine}
على الموقع للنص نفسه {figures_note}خريطة للمفاهيم التي يلامسها. لم نضع رابطًا في هذه الرسالة
عن قصد، حفاظًا على سلامتكم: الرسائل التي تحمل روابط هي بالضبط ما يوقع الناس، ورابط
من غريب لا يستحق الثقة. العنوان {site}، وستجدون البحث بأنفسكم: باسمكم أو برقمه
{aid}.

أمران أخيران ثم لا نشغلكم.

إن كان في سردنا خطأ، أخبرونا ونصحّحه.

وإن كنتم تفضّلون ألّا تظهر الصفحة أصلًا، يكفي سطر واحد في الرد وتُزال في اليوم
نفسه، دون أسئلة.

لا نبيع شيئًا ولا تسجيل هنا. كتبنا إليكم لأن العمل عملكم، ومن حقّكم أن تعرفوا
أين هو.

{sign}""",
    },
    "ru": {
        "subject": "Мы пересказали вашу работу {aid} простым языком",
        "body": """Здравствуйте{name}!

Мы bridge42worlds, небольшой некоммерческий проект. Читаем работы с arXiv целиком
и пересказываем простым языком на пяти языках, включая арабский, — чтобы студент
или инженер не из вашей области понял, что сделано.

Так мы поступили с вашей работой {aid}. Весь пересказ ниже: можно судить о нём,
никуда не переходя и не открывая ни одной ссылки.

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{retitle}

{retext}
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
{machine}
На сайте у этого же текста есть {figures_note}карта понятий, которых он касается.
Ссылку мы намеренно не вкладываем — из соображений вашей же безопасности: письма
со ссылками ровно так и ловят людей, и ссылке от незнакомых доверять не стоит.
Адрес — {site}. Работу вы найдёте там сами: по своему
имени или по номеру {aid}.

Две вещи, и мы больше не тревожим.

Если мы что-то переврали, скажите, и мы поправим.

Если вы предпочли бы вовсе там не быть, ответьте одной строкой, и страница уйдёт
в тот же день. Без выяснений.

Мы ничего не продаём, и подписываться не на что. Написали потому, что работа ваша
и вы должны знать, где она лежит.

{sign}""",
    },
}
SIGN = {"en": "bridge42worlds", "ar": "فريق bridge42worlds", "ru": "bridge42worlds"}

# ── ШАБЛОН ПИСЬМА ЖИВЁТ В ДАННЫХ, А НЕ ТОЛЬКО В КОДЕ ──────────────────────────
# Владелец 2026-09-02: «в идеале виден шаблон письма, чтобы я мог его отредактировать».
# Пока тексты были словарём в .py, править их мог только тот, кто правит код.
#
# Устройство простое и обратимое: если рядом лежит data/letter-template.json, его
# поля НАКЛАДЫВАЮТСЯ на зашитые. Нет файла — работает как раньше. Испорчен файл —
# тоже как раньше, и об этом говорится вслух, а не молча.
#
# Накладываем ПОЛЯМИ, а не целиком: правка русской темы не должна снести арабское
# тело. И «испорчен» здесь значит не только битый JSON: тело письма обязано
# сохранить все места подстановки, иначе письмо уйдёт с дырами вместо пересказа.
TEMPLATE_FILE = ROOT / "data" / "letter-template.json"
REQUIRED_SLOTS = ("{retitle}", "{retext}", "{machine}", "{sign}", "{site}", "{aid}")


def template_problems(lang, body):
    """Чего не хватает в теле письма. Пусто — можно сохранять."""
    return [slot for slot in REQUIRED_SLOTS if slot not in (body or "")]


def load_template():
    """Наложить пользовательскую правку шаблона на зашитый."""
    if not TEMPLATE_FILE.exists():
        return
    try:
        over = json.loads(TEMPLATE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"⚠ {TEMPLATE_FILE.name} не читается ({type(e).__name__}) — беру зашитый шаблон")
        return
    for lang, item in (over or {}).items():
        if lang not in LETTER or not isinstance(item, dict):
            continue
        if item.get("subject"):
            LETTER[lang]["subject"] = item["subject"]
        body = item.get("body")
        if body:
            missing = template_problems(lang, body)
            if missing:
                print(f"⚠ шаблон {lang}: нет мест подстановки {' '.join(missing)} — беру зашитый")
            else:
                LETTER[lang]["body"] = body
        if item.get("sign"):
            SIGN[lang] = item["sign"]


load_template()


def graph():
    g = json.loads(GRAPH.read_text(encoding="utf-8"))
    return g.get("graph", g)


def slug_of(name):
    import generate as G
    return G.author_slug(name)


def papers_of(name, lang, cap=6, first=None):
    """Строки со ссылками на разборы.

    Ссылка ведёт на язык письма: араб получает арабскую страницу, а не английскую
    с кнопкой переключения. Больше шести не перечисляем — остальное на его странице.
    """
    import generate as G
    g = graph()
    ids = (g.get(name) or {}).get("articles") or []
    # Названия берём из индекса ЯЗЫКА ПИСЬМА: арабское письмо со ссылкой на арабскую
    # страницу и английским заголовком читается как машинная склейка. Реестр авторов
    # общий, а заголовки у каждого языка свои.
    idx = {}
    try:
        rows = G.load_index(lang)
    except Exception:
        rows = G.load_index("en")
    for a in (rows or G.load_index("en")):
        if a.get("version") == "popular":
            idx[a["id"]] = a
            idx[a["id"].split("v")[0]] = a
    # Работа, ради которой пишем, идёт ПЕРВОЙ: человек должен узнать своё с первой
    # строки, а не искать себя в списке.
    if first:
        ids = [first] + [x for x in ids if x != first and x.split("v")[0] != first.split("v")[0]]
    out, used = [], 0
    for aid in ids:
        a = idx.get(aid) or idx.get(aid.split("v")[0])
        if not a:
            continue
        title = (a.get("title") or "").strip()
        # НАЗВАНИЕ ИЗ ПОПУЛЯРНОЙ ВЕРСИИ, ССЫЛКА — В ПРОДВИНУТУЮ (владелец 31.08).
        # Название популярного уровня человечнее: оно написано, чтобы объяснить, а не
        # чтобы повторить исходный заголовок. А раздел рекомендаций — тот самый ✛,
        # ради которого мы и пишем, — живёт ТОЛЬКО в продвинутой версии. Приводить
        # автора на популярную страницу значит показать ему пересказ и спрятать то,
        # что написано для него.
        url = f"{SITE}/lang/{lang}/archive/{a['date']}/{a['id']}/advanced.html"
        out.append(f"  {title}\n  {url}")
        used += 1
        if used >= cap:
            break
    if len(ids) > used:
        more = {"en": f"  and {len(ids) - used} more on the page below",
                "ar": f"  و{len(ids) - used} أخرى في الصفحة أدناه",
                "ru": f"  и ещё {len(ids) - used} на странице ниже"}
        out.append(more.get(lang, more["en"]))
    return "\n".join(out) + "\n"


def retelling(aid, lang):
    """Сам пересказ — заголовок и текст популярного уровня, без разметки.

    Владелец 01.09: «в письмо включить разобранную версию статьи, ссылку дать на сайт,
    и не давать ссылку — пусть сам поищет, только адрес сайта». Резон прямой: писем со
    ссылками столько, что нажимать их перестали, а нам нужно не нажатие, а доверие.
    Письмо, которое несёт готовый текст и ничего не просит, читается как подарок, а не
    как рассылка. Ссылка при этом остаётся возможной — но её человек наберёт сам,
    когда захочет.

    Разметку понятий ([tag:id]слово[/tag]) снимаем: в почте она мусор.
    """
    import re as _re
    for base in (ROOT / "lang" / "ru" / "archive", ROOT / "lang" / "en" / "archive"):
        hits = list(base.glob(f"*/{aid}/data.json"))
        if not hits:
            continue
        d = json.loads(hits[0].read_text(encoding="utf-8"))
        pop = (d.get("popular") or {}).get(lang) or (d.get("popular") or {}).get("en") or {}
        if not pop:
            pop = (d.get("simple") or {}).get(lang) or (d.get("simple") or {}).get("en") or {}
        title = (pop.get("title") or "").strip()
        text = (pop.get("text") or pop.get("description") or "").strip()
        # Снимаем ВСЮ нашу разметку, а не только теги понятий: в тексте есть ещё
        # [callout]…[/callout] — врезки, которые на странице становятся плашкой, а в
        # почте остаются словом в скобках. Скобки читателя мы не трогаем: убираем
        # только формы [слово] и [/слово] из нашего набора.
        text = _re.sub(r"\[/?[a-z_]+(?::[^\]]*)?\]", "", text)
        # Абзацы оставляем как есть: пересказ писался абзацами, и в почте они читаются.
        # ПЕРЕНОСЫ РУКАМИ. Почтовые клиенты ломают длинные строки как придётся, и
        # абзац в тысячу знаков приезжает лесенкой. Раскладываем сами по 78 колонок —
        # ширина, на которой письмо читается и в терминале, и в телефоне.
        import textwrap as _tw
        nl = chr(10)
        paras = [x.strip() for x in text.split(nl) if x.strip()]
        wrapped = [_tw.fill(x, width=78) for x in paras]
        return title, (nl + nl).join(wrapped)
    return "", ""


# ── ✛ РАЗБОР МАШИНЫ ЗНАНИЙ: ЕДИНСТВЕННОЕ В ПИСЬМЕ, ЧТО НАПИСАНО ДЛЯ АВТОРА ─────
# Терминология, в которой я путался и которую владелец 2026-09-01 развёл: «разобранная
# версия» — это просто уровни чтения, пересказ для читателя. «Машина знаний» — другое:
# это НАШИ рекомендации автору, значок ✛ на карточке. Письмо несло пересказ и лишь
# ОБЕЩАЛО, что на сайте есть «раздел, написанный для вас». То есть самое ценное для
# адресата оставалось за поиском — в письме без единой ссылки, по нашему же решению.
#
# Теперь раздел идёт целиком в письме. Пересказ показывает, что мы работу прочли;
# ✛ показывает, что мы её поняли и нам есть что сказать по существу.
MACHINE = {
    "ru": {"head": "ЧТО УВИДЕЛА НАША МАШИНА ЗНАНИЙ",
           "dirs": "Куда работа может пойти дальше:",
           "near": "рядом в нашем архиве"},
    "en": {"head": "WHAT OUR KNOWLEDGE MACHINE SAW",
           "dirs": "Where this work can go next:",
           "near": "neighbours in our archive"},
    "ar": {"head": "ما رأته آلة المعرفة لدينا",
           "dirs": "إلى أين يمكن أن يمضي هذا العمل:",
           "near": "أعمال مجاورة في أرشيفنا"},
}


def machine(aid, lang):
    """Раздел ✛ для письма: (готовый текст, данные для HTML).

    Пусто — значит у работы разбора нет, и такую работу мы не рассылаем вовсе
    (см. отбор кандидатов ниже: ✛ там обязательное условие, а не пожелание).

    Номера соседних работ даём простым текстом. Ссылок в письме нет намеренно, но
    номер arXiv — не ссылка, а доказательство: видно, что совет опирается на реальные
    работы рядом, а не на общие слова.
    """
    import textwrap as _tw
    nl = chr(10)
    w = MACHINE.get(lang) or MACHINE["en"]
    for base in (ROOT / "lang" / "ru" / "archive", ROOT / "lang" / "en" / "archive"):
        hits = list(base.glob(f"*/{aid}/data.json"))
        if not hits:
            continue
        rec = (json.loads(hits[0].read_text(encoding="utf-8")).get("recommend") or {})
        d = rec.get(lang) or rec.get("en") or rec.get("ru") or {}
        if not d:
            return "", None
        parts = [w["head"], ""]
        for k in ("seen", "strength"):
            if (d.get(k) or "").strip():
                parts += [_tw.fill(d[k].strip(), width=78), ""]
        dirs = [x for x in (d.get("directions") or []) if (x.get("text") or "").strip()]
        if dirs:
            parts.append(w["dirs"])
            for i, x in enumerate(dirs, 1):
                parts.append(_tw.fill(x["text"].strip(), width=74,
                                      initial_indent=f"  {i}. ", subsequent_indent="     "))
                near = [str(b) for b in (x.get("based_on") or []) if b]
                if near:
                    parts.append(f"     ({w['near']}: {', '.join(near)})")
                parts.append("")
        line = "- " * 39
        return nl + line + nl + nl + nl.join(parts).rstrip() + nl + nl + line + nl, d
    return "", None


def best_paper(name):
    """Свежая работа автора, у которой ЕСТЬ разбор машины знаний.

    Это условие рассылки, а не удобство: владелец 2026-09-01 — «отправляем только тем,
    чьи работы разобрала машина знаний, именно эти статьи я и хочу отправлять». Нет ✛ —
    писать не о чем: письмо без раздела, написанного для автора, это обычная рассылка.
    """
    ids = (graph().get(name) or {}).get("articles") or []
    best = None
    for aid in ids:
        for base in (ROOT / "lang" / "ru" / "archive", ROOT / "lang" / "en" / "archive"):
            hits = list(base.glob(f"*/{aid}/data.json"))
            if not hits:
                continue
            d = json.loads(hits[0].read_text(encoding="utf-8"))
            if d.get("recommend"):
                day = hits[0].parent.parent.name
                if best is None or day > best[0]:
                    best = (day, aid)
            break
    return best[1] if best else None


def licence_restricted(aid):
    """Класс «только собственный разбор» — рисунков на сайте у работы нет."""
    if not aid:
        return False
    for base in (ROOT / "lang" / "ru" / "archive",):
        for hit in base.glob(f"*/{aid}/data.json"):
            try:
                return json.loads(hit.read_text(encoding="utf-8")).get("license_class") == "analysis"
            except Exception:
                return False
    return False


def compose(name, lang="en", first=None):
    """Возвращает тему, текстовую версию и HTML-версию письма.

    Две версии одного письма, а не два разных письма: HTML собирается из того же
    пересказа и тех же обещаний. Текстовая уходит первой частью — она нужна там, где
    HTML не показывают.
    """
    t = LETTER.get(lang) or LETTER["en"]
    aid = (first or "").split("v")[0] or first or ""
    retitle, retext = retelling(first, lang) if first else ("", "")
    mtext, mdata = machine(first, lang) if first else ("", None)
    sign = SIGN.get(lang, SIGN["en"])
    # РИСУНКИ УПОМИНАЕМ ТОЛЬКО ТАМ, ГДЕ ОНИ ЕСТЬ. Для работ под arXiv non-exclusive и
    # NC авторские рисунки на сайте не показываются (лицензия не разрешает), и фраза
    # «у этого текста есть рисунки» была бы неправдой — а письмо и так одно на автора.
    figs = {"en": "figures and ", "ru": "рисунки и ", "ar": "رسوم و"}
    fn = figs.get(lang, figs["en"]) if not licence_restricted(first) else ""
    body = t["body"].format(name=" " + name, who=name, aid=aid,
                            retitle=retitle, retext=retext, machine=mtext, sign=sign,
                            site=SITE.replace("https://", ""), figures_note=fn)
    html = None
    if retext:
        try:
            import letter_html
            html = letter_html.build(name, aid, lang, retitle, retext, sign, mdata)
        except Exception as e:
            print(f"⚠ оформление письма не собралось ({type(e).__name__}) — уйдёт текстом")
    return t["subject"].format(aid=aid), body, html


# ── КОМУ ПИСАТЬ: АВТОРЫ СВЕЖИХ РАЗБОРОВ ──────────────────────────────────
# Владелец 31.08: «начать надо с авторов со свежими разборами — всё свежее».
# Резон простой: работа у человека ещё в голове, и письмо про неё не выглядит
# археологией. Адрес берём из самой работы: в статьях он напечатан для переписки,
# и лежит у нас же в fulltext.txt рядом со статьёй — качать ничего не надо.
MAIL_RE = __import__("re").compile(r"[A-Za-z0-9._%+-]+\s*@\s*[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Общие адреса редакций и коллабораций: писать туда бессмысленно и назойливо.
SKIP_MAIL = ("arxiv.org", "example.com", "noreply", "no-reply", "support@",
             "editor@", "journals@", "info@", "admin@")


def emails_of(date, aid, cap=4000):
    """Адреса из первых килобайт работы — там, где авторы их и печатают."""
    for base in (ROOT / "lang" / "ru" / "archive" / str(date) / aid,
                 ROOT / "lang" / "en" / "archive" / str(date) / aid):
        f = base / "fulltext.txt"
        if not f.exists():
            continue
        head = f.read_text(encoding="utf-8", errors="ignore")[:cap]
        out = []
        for m in MAIL_RE.findall(head):
            a = m.replace(" ", "").strip(".,;")
            # ХВОСТ ОТ ВЁРСТКИ. В PDF за адресом часто идёт значок сноски или начало
            # следующего слова, и они прилипают к домену: «…@eli-alps.huE». Домен
            # верхнего уровня пишется строчными; если после строчных идут заглавные,
            # это уже не адрес, а соседний текст.
            import re as _re
            a = _re.sub(r"(\.[a-z]{2,24})[A-Z].*$", r"\1", a)
            if any(s in a.lower() for s in SKIP_MAIL):
                continue
            if a not in out:
                out.append(a)
        return out
    return []


def _name_forms(name):
    """Как фамилия автора может выглядеть в адресе.

    Адрес почти всегда собран из имени, но по-разному: `rongan` (имя+фамилия),
    `kvogiatz` (инициал + обрезанная фамилия), `awliu` (два инициала + фамилия),
    `martina.conte` (имя.фамилия). Собираем все формы, чтобы сверять с локальной частью.
    """
    parts = [x for x in name.replace(".", " ").replace("-", " ").split() if x]
    if not parts:
        return []
    surname = parts[-1].lower()
    firsts = [x.lower() for x in parts[:-1]]
    ini = "".join(x[0] for x in firsts if x)
    forms = {surname, ini + surname, (firsts[0] if firsts else "") + surname,
             surname + ini}
    if firsts:
        forms.add(firsts[0] + "." + surname)
        forms.add(firsts[0][0] + "." + surname)
        # Только ПЕРВЫЙ инициал плюс фамилия: у «Konstantinos D. Vogiatzis» ящик
        # kvogiatz@ — без среднего инициала, с обрезанной фамилией. Форма «kd…»
        # такой адрес не ловит, и письмо уходило первому автору вместо настоящего.
        forms.add(firsts[0][0] + surname)
    return [f for f in forms if len(f) >= 4], surname


def addressee(article, mails):
    """Кому адресовать письмо — и НИКОМУ, если не уверены.

    Прежнее правило искало фамилию в адресе, а не нашло — писало первому автору.
    Третий аудит (01.09) поймал на этом первое же письмо очереди: работа Brody
    Quebedeaux и четверых соавторов, адрес для переписки `kvogiatz@utk.edu` — то есть
    Konstantinos Vogiatzis, последний автор. Письмо ушло бы человеку с чужим именем в
    обращении. Для рассылки, вся ценность которой в «мы про ВАШУ работу», это худшая
    из возможных ошибок.

    Теперь: сверяем локальную часть со всеми формами имени каждого автора, включая
    обрезанные (`kvogiatz` — начало `kvogiatzis`). Совпадений нет — возвращаем None, и
    работа выпадает из очереди. Лучше не написать, чем написать не тому.
    """
    authors = article.get("authors") or []
    if not authors:
        return None
    best = None
    best_mail = None
    best_len = 0
    for m in mails:
        local = re.sub(r"[^a-z.]", "", m.split("@")[0].lower())
        if len(local) < 4:
            continue
        for a in authors:
            forms, surname = _name_forms(a)
            for f in forms:
                # Точное совпадение, адрес длиннее формы, или адрес — обрезанное начало
                # формы (не короче шести знаков, иначе «liu» совпадёт с половиной Китая).
                # Точки в адресах ставят не все: «martina.conte» и «martinaconte» —
                # один человек. Сверяем и с точками, и без них.
                lf, ll = f.replace(".", ""), local.replace(".", "")
                hit = (local == f or ll == lf
                       or (ll.startswith(lf) and len(lf) >= 5)
                       or (lf.startswith(ll) and len(ll) >= 6))
                if hit and len(f) > best_len:
                    best, best_mail, best_len = a, m, len(f)
    # Возвращаем ПАРУ: кому и на какой адрес. В работе адресов бывает несколько
    # (jphu@ и yang.xu@ у одной и той же), и раньше мы брали имя по совпадению с
    # одним, а слали на первый попавшийся — то есть снова чужому человеку.
    return best, best_mail


def written():
    if not LOG.exists():
        return {}
    out = {}
    for line in LOG.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                r = json.loads(line)
                out[r.get("author")] = r
            except json.JSONDecodeError:
                pass
    return out


def remember(name, to, lang, aid=""):
    """Запись об отправке. Номер работы храним не для порядка: по нему видно потом,
    открыл ли человек страницу своей РАБОТЫ, а не только страницу автора. Письмо не
    несёт ссылок и предлагает два пути — поиск по номеру и раздел авторов, — так что
    засчитывать надо оба (tools/outreach_visits.py)."""
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"author": name, "to": to, "lang": lang, "aid": aid,
                             "at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                            ensure_ascii=False) + "\n")


CAND = ROOT / "data" / "outreach-candidates.jsonl"


def fresh_articles(days):
    import generate as G
    from datetime import timedelta
    edge = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    return [a for a in G.load_index("en")
            if a.get("version") == "popular" and (a.get("date") or "") >= edge]


RETAG = ROOT / "data" / "articles-retag-v2.json"


def advice_on_page(date, aid, lang="en"):
    """Стоит ли раздел рекомендаций НА СТРАНИЦЕ, а не только в данных.

    Проверять данные оказалось мало. 31 августа у сорока четырёх свежих работ раздел
    был записан, а страница собрана раньше — и письмо привело бы автора туда, где для
    него ничего не написано. Проверка данных отвечает «мы это посчитали», проверка
    страницы — «человек это увидит». Письмо обещает второе.
    """
    p = ROOT / "lang" / lang / "archive" / str(date) / aid / "advanced.html"
    if not p.exists():
        return False
    return "km-advice" in p.read_text(encoding="utf-8", errors="ignore")


def has_advice(date, aid):
    """Есть ли у работы раздел рекомендаций — тот самый значок ✛ на карточке.

    Владелец 31.08: «те, что с плюсиками, по ним и рассылку». Это самый строгий и
    самый честный отбор из возможных. Плюсик значит, что работа разобрана полностью
    (а не пересказана по аннотации) и что машина знаний написала автору раздел «куда
    это может пойти дальше», опираясь на конкретных векторных соседей. Письмо ведёт
    человека ровно туда, где для него что-то написано.
    """
    for lang in ("ru", "en"):
        p = ROOT / "lang" / lang / "archive" / str(date) / aid / "data.json"
        if p.exists():
            d = json.loads(p.read_text(encoding="utf-8"))
            rec = d.get("recommend") or {}
            return bool(rec.get("ru") or rec.get("en"))
    return False


def machine_marked():
    """Работы, которые ПРОШЛИ машину знаний: у них есть разметка понятий.

    Владелец 31.08: «отправляем только тем, чьи работы были обработаны машиной
    знаний». Резон прямой: письмо ведёт человека на страницу, где его работа стоит
    в графе понятий, со связями и соседями. Разбор без разметки такой страницы не
    даёт — там пусто, и письмо обещает больше, чем показывает.

    Разметку кладёт шаг retag (ежедневный — только работам дня, недельный —
    доразметкой всему корпусу), а лежит она в data/articles-retag-v2.json.
    """
    if not RETAG.exists():
        return {}
    arts = json.loads(RETAG.read_text(encoding="utf-8")).get("articles") or {}
    out = {}
    for aid, concepts in arts.items():
        out[aid] = len(concepts or [])
        out[aid.split("v")[0]] = len(concepts or [])
    return out


# ── ВЫДЕРЖКА И ЯЗЫК: ДВА ПРАВИЛА, БЕЗ КОТОРЫХ РАССЫЛКУ НЕ НАЧИНАЕМ ────────────
# Владелец 2026-09-01: «отправлять письма не раньше, чем прошла полная неделя с момента
# нашего разбора, и только с плюсиком; начинай с самых старых по времени».
#
# ЗАЧЕМ НЕДЕЛЯ. Разбор в первый день ещё догоняют шаги конвейера: разметка понятий,
# соседи, перевод на четыре языка, пересборка страницы. Письмо, ушедшее в тот же день,
# зовёт человека на страницу, которая ещё меняется. Неделя — это срок, за который работа
# успевает встать окончательно, а мы успеваем заметить и починить брак.
RECO_WAIT_DAYS = 7

# Арабский мир — приоритетная аудитория (решение владельца 31.07). Язык письма выбираем
# ПО АВТОРУ, а не флагом: флаг со значением по умолчанию `en` слал англоязычное письмо
# и профессору в Эр-Рияде тоже. Признак — страна в адресе для переписки, а если домен
# общий, то название учреждения в шапке работы.
ARAB_TLD = {"sa", "ae", "kw", "qa", "bh", "om", "eg", "jo", "lb", "sy", "iq", "ye",
            "sd", "ly", "tn", "dz", "ma", "mr", "ps", "so", "dj", "km"}
ARAB_WORDS = ("saudi", "kuwait", "qatar", "emirates", "abu dhabi", "dubai", "sharjah",
              "bahrain", "oman", "muscat", "egypt", "cairo", "alexandria", "jordan",
              "amman", "lebanon", "beirut", "iraq", "baghdad", "riyadh", "jeddah",
              "dhahran", "kaust", "kfupm", "khalifa university", "zayed university",
              "united arab emirates", "morocco", "rabat", "tunisia", "tunis", "algeria",
              "algiers", "yemen", "sudan", "khartoum", "palestine", "birzeit", "doha")


def analysed_at(date, aid):
    """Когда МЫ разобрали работу — от этого дня и считается выдержка.

    Точную отметку пишет tools/recommend.py (поле recommend_at). У работ, разобранных
    до появления отметки, её нет — там берём день самой работы. Это занижает выдержку
    в нашу же пользу: день работы всегда РАНЬШЕ дня разбора, значит семь дней от него
    уже прошли наверняка.
    """
    for base in (ROOT / "lang" / "ru" / "archive", ROOT / "lang" / "en" / "archive"):
        f = base / str(date) / aid / "data.json"
        if f.exists():
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                break
            at = (d.get("recommend_at") or "")[:10]
            if at:
                return at
            break
    return str(date)[:10]


def matured(date, aid, days=RECO_WAIT_DAYS):
    """Прошла ли неделя с разбора."""
    from datetime import timedelta
    edge = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    return analysed_at(date, aid) <= edge


def letter_lang(date, aid, to, default="en"):
    """Язык письма по автору: арабский арабскому миру, английский остальным."""
    dom = (to or "").rsplit("@", 1)[-1].lower()
    if dom.rsplit(".", 1)[-1] in ARAB_TLD:
        return "ar"
    for base in (ROOT / "lang" / "ru" / "archive", ROOT / "lang" / "en" / "archive"):
        f = base / str(date) / aid / "fulltext.txt"
        if f.exists():
            head = f.read_text(encoding="utf-8", errors="ignore")[:4000].lower()
            if any(w in head for w in ARAB_WORDS):
                return "ar"
            break
    return default


# ── СКОЛЬКО ПИСЕМ В ДЕНЬ ──────────────────────────────────────────────────────
# Вопрос владельца 2026-09-01: «по сколько в день, по 20-30, чтобы в спам не попасть?»
#
# Дело не в числе, а в РАЗГОНЕ. Домен ни разу не рассылал писем, и для Gmail с Outlook
# он чистый лист: тридцать холодных писем в первый же день с нового домена — самый
# заметный признак рассылочной машины, какой вообще бывает. Тридцать писем в день после
# двух недель ровной истории — обычное поведение живой переписки.
#
# Разгон вдвое каждые несколько дней: 5 → 10 → 20 → 30. Две недели до крейсерской
# скорости, и это не потеря: в очереди сейчас десятки работ, а не тысячи.
#
# Что у нас уже в пользу доставки: SPF и DKIM на домене стоят, письмо уходит одному
# человеку, текст у каждого свой, ссылок нет ни одной, есть заголовок отказа. Профиль
# лучше, чем у большинства настоящих рассылок.
RAMP = ((3, 5), (7, 10), (14, 20))
RAMP_TOP = 30


def daily_cap():
    """Сколько писем ещё можно отправить сегодня. Ноль — на сегодня хватит."""
    from datetime import date
    rows = list(written().values())
    today = date.today().isoformat()
    if not rows:
        return RAMP[0][1]
    first = min((r.get("at") or "")[:10] for r in rows if r.get("at"))
    try:
        age = (date.today() - date.fromisoformat(first)).days
    except ValueError:
        age = 0
    cap = RAMP_TOP
    for edge, n in RAMP:
        if age < edge:
            cap = n
            break
    sent_today = sum(1 for r in rows if (r.get("at") or "")[:10] == today)
    return max(0, cap - sent_today)


def candidates(days, limit):
    """Кому писать: разборы с ✛, выдержанные неделю, с адресом из работы.

    ПОРЯДОК — ОТ САМЫХ СТАРЫХ (владелец 2026-09-01: «по времени самые старые я имею в
    виду»). Раньше список шёл от свежих, и хвост архива не был бы разослан никогда:
    свежее прибывает каждый день и всегда становилось бы первым.
    """
    done = written()
    marked = machine_marked()
    rows, no_mark, no_mail, no_adv, no_wait = [], 0, 0, 0, 0
    for art in sorted(fresh_articles(days), key=lambda x: x.get("date", "")):
        n_con = marked.get(art["id"]) or marked.get(art["id"].split("v")[0]) or 0
        if not n_con:
            no_mark += 1
            continue
        # Плюсик обязателен, и считается он ПО СТРАНИЦЕ: раздел в данных без раздела
        # на странице — это обещание, которого читатель не увидит.
        if not (has_advice(art.get("date"), art["id"])
                and advice_on_page(art.get("date"), art["id"])):
            no_adv += 1
            continue
        # Выдержка: неделя с нашего разбора. Работа, разобранная вчера, ещё догоняется
        # шагами конвейера — письмо позвало бы человека на страницу, которая меняется.
        if not matured(art.get("date"), art["id"]):
            no_wait += 1
            continue
        mails = emails_of(art.get("date"), art["id"])
        if not mails:
            no_mail += 1
            continue
        who, to = addressee(art, mails)
        if not who or who in done:
            continue
        rows.append({"id": art["id"], "date": art["date"], "author": who,
                     "to": to, "others": [x for x in mails if x != to][:2],
                     "concepts": n_con, "lang": letter_lang(art.get("date"), art["id"], to),
                     "analysed": analysed_at(art.get("date"), art["id"]),
                     "title": (art.get("title") or "")[:70],
                     "page": f"{SITE}/lang/en/authors/{slug_of(who)}.html"})
        if len(rows) >= limit:
            break
    CAND.parent.mkdir(parents=True, exist_ok=True)
    CAND.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                    encoding="utf-8")
    ar = sum(1 for r in rows if r.get("lang") == "ar")
    print(f"разборов за {days} дней: готовых к письму {len(rows)} "
          f"(по-арабски {ar}, по-английски {len(rows) - ar})  → {CAND.relative_to(ROOT)}")
    print(f"  отсеяно: без разметки понятий {no_mark} · без плюсика (нет рекомендаций) "
          f"{no_adv} · моложе недели {no_wait} · без адреса в работе {no_mail}")
    print(f"  сегодня можно отправить: {daily_cap()} (разгон домена)\n")
    for r in rows[:limit]:
        print(f"  {r['date']}  {r['id']:16} {r.get('lang','en')}  {r['to']:34} "
              f"{r['author'][:22]:24} {r['title'][:34]}")
    if rows:
        print(f"\nписьмо по одной работе:  python tools/author_letter.py --id {rows[0]['id']} --dry")
    return 0


def by_paper(aid, lang, to, send, test=False, lang_explicit=False):
    """Письмо про КОНКРЕТНУЮ свежую работу — она идёт первой строкой.

    ЯЗЫК ВЫЧИСЛЯЕТСЯ ПО АВТОРУ, а не берётся из флага. У --lang значение по
    умолчанию «en», и команда `--id … --send` без явного языка отправляла бы
    англоязычное письмо профессору в Эр-Рияде — при том, что арабский мир у нас
    приоритетная аудитория, а кандидат уже помечен lang='ar' при отборе.
    Явно указанный --lang сильнее: это осознанный выбор человека.
    """
    import generate as G
    art = None
    for x in G.load_index("en"):
        if x.get("version") == "popular" and (x["id"] == aid or x["id"].split("v")[0] == aid):
            art = x
            break
    if not art:
        print(f"нет такой работы в индексе: {aid}")
        return 2
    mails = emails_of(art.get("date"), art["id"])
    who, matched = addressee(art, mails)
    if not lang_explicit:
        lang = letter_lang(art.get("date"), art["id"], matched, default=lang)
    if not who:
        print("не нашлось, кому адресовать: ни один адрес в работе не сходится с именем")
        return 2
    to = to or matched
    subj, body, html = compose(who, lang, first=art["id"])
    if not send:
        print(f"РАБОТА: {art['id']} · {art.get('date')}")
        print(f"КОМУ:  {who} <{to or 'адрес не найден'}>")
        print(f"ТЕМА:  {subj}\n")
        print(body)
        print("\n(показ; чтобы отправить, добавьте --send)")
        return 0
    if not to:
        print("нет адреса — укажите --to")
        return 2
    # ПРОБНОЕ ПИСЬМО СЕБЕ в журнал не пишется: иначе автор, на чьём письме мы
    # проверяли вид, навсегда попал бы в «уже написали» и настоящего письма не получил.
    if not test:
        was = written().get(who)
        if was:
            print(f"этому автору уже писали {was['at'][:10]} — второй раз не пишем")
            return 1
        # РАЗГОН СОБЛЮДАЕТСЯ, А НЕ ПЕЧАТАЕТСЯ. Ограничение 5→10→20→30 писем в день
        # считалось функцией daily_cap() и попадало в статистику, но НИГДЕ не
        # проверялось перед отправкой: целый блок обоснования существовал как цифра
        # на экране (найдено разбором 02.09). Кнопка «отправить» в панели легко
        # послала бы за раз всю очередь — ровно то, от чего разгон и защищает.
        if daily_cap() <= 0:
            print("на сегодня норма писем выбрана — разгон домена (5→10→20→30). "
                  "Остальные уйдут завтра.")
            return 1
    import council_mail
    if council_mail.send(to, subj, body, sender=FROM, html=html):
        if test:
            print(f"✅ пробное письмо ушло на {to} (в журнал не записано)")
        else:
            remember(who, to, lang)
            print(f"✅ отправлено: {who} → {to}")
        return 0
    return 1


def main():
    ap = argparse.ArgumentParser(description="Письмо автору о его же работе")
    ap.add_argument("author", nargs="?", help="имя автора как в реестре")
    ap.add_argument("--lang", default="en", choices=sorted(LETTER))
    ap.add_argument("--to", help="адрес получателя (из самой работы)")
    ap.add_argument("--send", action="store_true", help="отправить (иначе только показать)")
    ap.add_argument("--dry", action="store_true", help="показать письмо и выйти")
    ap.add_argument("--log", action="store_true", help="кому уже писали")
    ap.add_argument("--candidates", action="store_true",
                    help="авторы свежих разборов с найденными адресами")
    ap.add_argument("--days", type=int, default=30, help="глубина свежести, дней")
    ap.add_argument("--limit", type=int, default=40, help="сколько показать")
    ap.add_argument("--id", help="писать по конкретной работе (её arXiv-номер)")
    ap.add_argument("--test", action="store_true",
                    help="пробное письмо себе: уходит, но в журнал не пишется")
    a = ap.parse_args()

    if a.candidates:
        return candidates(a.days, a.limit)
    if a.id:
        return by_paper(a.id, a.lang, a.to, a.send or a.test, a.test,
                        lang_explicit=("--lang" in sys.argv))

    if a.log:
        w = written()
        print(f"написано авторам: {len(w)}")
        for name, r in list(w.items())[-20:]:
            print(f"  {r['at'][:10]}  {name:32} {r['to']}")
        return 0

    if not a.author:
        print("нужно имя автора (или --log)")
        return 2
    if a.author not in graph():
        print(f"нет такого автора в реестре: {a.author}")
        return 2

    # РАБОТА ОБЯЗАТЕЛЬНА, А НЕ ЖЕЛАТЕЛЬНА. Этот путь звал compose() без номера работы —
    # и письмо уходило БЕЗ пересказа, БЕЗ раздела машины знаний и без вёрстки (HTML
    # собирается только когда есть пересказ). То есть по имени автора можно было отправить
    # пустое «мы вас пересказали», не показав ни строчки. Свежую работу с ✛ берём сами:
    # без разбора машины знаний мы не пишем вовсе (владелец 2026-09-01).
    first = best_paper(a.author)
    if not first:
        print(f"у автора {a.author} нет работ с разбором машины знаний (✛) — таким не пишем")
        return 2
    subj, body, html = compose(a.author, a.lang, first=first)
    if a.dry or not (a.send or a.test):
        print(f"КОМУ:   {a.to or '(адрес не задан)'}")
        print(f"РАБОТА: {first}")
        print(f"ТЕМА:   {subj}\n")
        print(body)
        if not a.dry:
            print("\n(это показ; чтобы отправить, добавьте --to АДРЕС --send)")
        return 0

    if not a.to:
        print("для отправки нужен --to АДРЕС")
        return 2
    if not a.test:
        was = written().get(a.author)
        if was:
            print(f"этому автору уже писали {was['at'][:10]} на {was['to']} — второй раз не пишем")
            return 1
    import council_mail
    if council_mail.send(a.to, subj, body, sender=FROM, html=html):
        if a.test:
            print(f"✅ пробное письмо ушло на {a.to} (в журнал не записано)")
        else:
            remember(a.author, a.to, a.lang, first)
            print(f"✅ отправлено: {a.author} → {a.to}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
