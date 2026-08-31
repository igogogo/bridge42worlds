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
        "subject": "Your paper is retold in plain language on bridge42worlds",
        "body": """Hello{name},

We run bridge42worlds, a small project that retells arXiv papers in plain
language and publishes them in five languages, Arabic among them. The point is
that a student or an engineer outside your field can follow what was done.

Your work is one of those we covered:
{papers}
We also keep a page that gathers your papers we have retold:
  {page}

Two things, and then we leave you alone.

If we got something wrong, tell us and we will fix it. That page has buttons for
it; they open your own mail program with the letter already written, so it costs
you a few seconds.

If you would rather not be there at all, reply with one line and the page comes
down the same day. No questions asked.

Nothing is for sale here and there is nothing to sign up for. We wrote because
it is your work and you should know where it is.

{sign}
{site}""",
    },
    "ar": {
        "subject": "عملكم مُعاد سرده بلغة مبسّطة على bridge42worlds",
        "body": """السلام عليكم{name}،

نحن مشروع صغير اسمه bridge42worlds، نعيد سرد أبحاث arXiv بلغة مبسّطة وننشرها
بخمس لغات، من بينها العربية. الغاية أن يتمكّن طالب أو مهندس من خارج تخصّصكم من
متابعة ما أُنجز.

عملكم من بين ما تناولناه:
{papers}
ولدينا أيضًا صفحة تجمع أبحاثكم التي أعدنا سردها:
  {page}

أمران فقط، ثم لا نشغلكم.

إن كان في سردنا خطأ، أخبرونا ونصحّحه. في الصفحة أزرار لذلك: تفتح بريدكم ورسالته
مكتوبة سلفًا، فلا يكلّفكم الأمر سوى ثوانٍ.

وإن كنتم تفضّلون ألّا تظهر الصفحة أصلًا، يكفي سطر واحد في الرد وتُزال في اليوم
نفسه، دون أسئلة.

لا نبيع شيئًا ولا تسجيل هنا. كتبنا إليكم لأن العمل عملكم، ومن حقّكم أن تعرفوا
أين هو.

{sign}
{site}""",
    },
    "ru": {
        "subject": "Ваша работа пересказана простым языком на bridge42worlds",
        "body": """Здравствуйте{name}!

Мы небольшой проект bridge42worlds: пересказываем работы с arXiv простым языком
и публикуем на пяти языках, включая арабский. Смысл в том, чтобы студент или
инженер не из вашей области понял, что сделано.

Ваша работа среди разобранных:
{papers}
И есть страница, которая собирает ваши работы, которые мы пересказали:
  {page}

Две вещи, и мы вас больше не тревожим.

Если мы что-то переврали, скажите, и мы поправим. На странице для этого есть
кнопки: они открывают вашу почтовую программу с уже написанным письмом, это
несколько секунд.

Если вы предпочли бы вовсе там не быть, ответьте одной строкой, и страница
уйдёт в тот же день. Без выяснений.

Мы ничего не продаём, и подписываться не на что. Написали потому, что работа
ваша и вы должны знать, где она лежит.

{sign}
{site}""",
    },
}
SIGN = {"en": "bridge42worlds", "ar": "فريق bridge42worlds", "ru": "bridge42worlds"}


def graph():
    g = json.loads(GRAPH.read_text(encoding="utf-8"))
    return g.get("graph", g)


def slug_of(name):
    import generate as G
    return G.author_slug(name)


def papers_of(name, lang, cap=6):
    """Строки со ссылками на разборы.

    Ссылка ведёт на язык письма: араб получает арабскую страницу, а не английскую
    с кнопкой переключения. Больше шести не перечисляем — остальное на его странице.
    """
    import generate as G
    g = graph()
    ids = (g.get(name) or {}).get("articles") or []
    idx = {}
    for a in G.load_index("en"):
        if a.get("version") == "popular":
            idx[a["id"]] = a
            idx[a["id"].split("v")[0]] = a
    out, used = [], 0
    for aid in ids:
        a = idx.get(aid) or idx.get(aid.split("v")[0])
        if not a:
            continue
        title = (a.get("title") or "").strip()
        url = f"{SITE}/lang/{lang}/archive/{a['date']}/{a['id']}/index.html"
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


def compose(name, lang="en"):
    t = LETTER.get(lang) or LETTER["en"]
    page = f"{SITE}/lang/en/authors/{slug_of(name)}.html"
    body = t["body"].format(name=" " + name, papers=papers_of(name, lang),
                            page=page, sign=SIGN.get(lang, SIGN["en"]),
                            site=SITE.replace("https://", ""))
    return t["subject"], body


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


def main():
    ap = argparse.ArgumentParser(description="Письмо автору о его же работе")
    ap.add_argument("author", nargs="?", help="имя автора как в реестре")
    ap.add_argument("--lang", default="en", choices=sorted(LETTER))
    ap.add_argument("--to", help="адрес получателя (из самой работы)")
    ap.add_argument("--send", action="store_true", help="отправить (иначе только показать)")
    ap.add_argument("--dry", action="store_true", help="показать письмо и выйти")
    ap.add_argument("--log", action="store_true", help="кому уже писали")
    a = ap.parse_args()

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

    subj, body = compose(a.author, a.lang)
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
