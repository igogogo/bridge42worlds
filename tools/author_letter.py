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

On the site the same text has figures, a map of the concepts it touches, and a
section written for you: where this work can go next. There is no link in this
letter on purpose. The address is {site} and there are two ways to find yourself:

  · type {aid} into the search box, or
  · open the authors section and look for your name: {who}.

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

على الموقع للنص نفسه رسوم، وخريطة للمفاهيم التي يلامسها، وقسم كُتب لكم: إلى أين
يمكن أن يمضي هذا العمل. لا رابط في هذه الرسالة عن قصد. العنوان {site}، وهناك
طريقتان لتجدوا أنفسكم:

  · اكتبوا {aid} في خانة البحث، أو
  · افتحوا قسم المؤلفين وابحثوا عن اسمكم: {who}.

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

На сайте у этого же текста есть рисунки, карта понятий, которых он касается, и
раздел, написанный для вас: куда работа может пойти дальше. Ссылки в письме нет
намеренно. Адрес — {site}, найти себя можно двумя способами:

  · введите {aid} в строку поиска, или
  · откройте раздел авторов и найдите своё имя: {who}.

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


def compose(name, lang="en", first=None):
    """Возвращает тему, текстовую версию и HTML-версию письма.

    Две версии одного письма, а не два разных письма: HTML собирается из того же
    пересказа и тех же обещаний. Текстовая уходит первой частью — она нужна там, где
    HTML не показывают.
    """
    t = LETTER.get(lang) or LETTER["en"]
    aid = (first or "").split("v")[0] or first or ""
    retitle, retext = retelling(first, lang) if first else ("", "")
    sign = SIGN.get(lang, SIGN["en"])
    body = t["body"].format(name=" " + name, who=name, aid=aid,
                            retitle=retitle, retext=retext, sign=sign,
                            site=SITE.replace("https://", ""))
    html = None
    if retext:
        try:
            import letter_html
            html = letter_html.build(name, aid, lang, retitle, retext, sign)
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


def remember(name, to, lang):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"author": name, "to": to, "lang": lang,
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


def candidates(days, limit):
    """Кому писать: свежие разборы, прошедшие машину знаний, с адресом из работы."""
    done = written()
    marked = machine_marked()
    rows, no_mark, no_mail, no_adv = [], 0, 0, 0
    for art in sorted(fresh_articles(days), key=lambda x: x.get("date", ""), reverse=True):
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
        mails = emails_of(art.get("date"), art["id"])
        if not mails:
            no_mail += 1
            continue
        who, to = addressee(art, mails)
        if not who or who in done:
            continue
        rows.append({"id": art["id"], "date": art["date"], "author": who,
                     "to": to, "others": [x for x in mails if x != to][:2],
                     "concepts": n_con,
                     "title": (art.get("title") or "")[:70],
                     "page": f"{SITE}/lang/en/authors/{slug_of(who)}.html"})
        if len(rows) >= limit:
            break
    CAND.parent.mkdir(parents=True, exist_ok=True)
    CAND.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                    encoding="utf-8")
    print(f"свежих разборов за {days} дней: готовых к письму {len(rows)}"
          f"  → {CAND.relative_to(ROOT)}")
    print(f"  отсеяно: без разметки понятий {no_mark} · без плюсика (нет рекомендаций) "
          f"{no_adv} · без адреса в работе {no_mail}\n")
    for r in rows[:limit]:
        print(f"  {r['date']}  {r['id']:16} {r['concepts']:3} пон.  {r['to']:36} "
              f"{r['author'][:22]:24} {r['title'][:36]}")
    if rows:
        print(f"\nписьмо по одной работе:  python tools/author_letter.py --id {rows[0]['id']} --dry")
    return 0


def by_paper(aid, lang, to, send, test=False):
    """Письмо про КОНКРЕТНУЮ свежую работу — она идёт первой строкой."""
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
        return by_paper(a.id, a.lang, a.to, a.send or a.test, a.test)

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

    subj, body, html = compose(a.author, a.lang)
    if a.dry or not a.send:
        print(f"КОМУ:  {a.to or '(адрес не задан)'}")
        print(f"ТЕМА:  {subj}\n")
        print(body)
        if not a.dry:
            print("\n(это показ; чтобы отправить, добавьте --to АДРЕС --send)")
        return 0

    if not a.to:
        print("для отправки нужен --to АДРЕС")
        return 2
    was = written().get(a.author)
    if was:
        print(f"этому автору уже писали {was['at'][:10]} на {was['to']} — второй раз не пишем")
        return 1
    import council_mail
    if council_mail.send(a.to, subj, body, sender=FROM):
        remember(a.author, a.to, a.lang)
        print(f"✅ отправлено: {a.author} → {a.to}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
