#!/usr/bin/env python3
"""Письмо автору в нашем оформлении: сплошной текст читать нельзя.

Владелец 01.09: «письмо можно отформатировать html, а то просто текст нечитабельно,
используй наш шаблон». Текстовая версия остаётся первой — она нужна там, где HTML не
показывают, — а рядом идёт вторая, свёрстанная теми же средствами, что сайт: тёплый
айвори, серифный заголовок, охряная линейка у обещаний.

Стили ВСТРОЕНЫ в каждый тег. Почтовые клиенты вырезают <style> из головы письма, а
Gmail вдобавок переписывает имена классов — внешняя таблица стилей до читателя не
доходит. Шрифты с запасными: Source Serif в почте подставится не везде, и Georgia
честнее безымянного гротеска.

Ссылок нет ни одной, и это не оплошность: писем со ссылками столько, что нажимать их
перестали. Адрес сайта — обычным текстом, набрать его человек может сам.
"""
import html as H

SITE = "bridge42worlds.academy"

WORDS = {
    "en": {
        "tagline": "arXiv papers retold in plain language, in five languages",
        "hello": "Hello {who},",
        "who_we": ("We are bridge42worlds, a small non-commercial project. We read arXiv "
                   "papers in full and retell them in plain language, so that a student or "
                   "an engineer outside the field can follow what was done."),
        "did": "We did that with your paper {aid}. The whole retelling is below.",
        "howto_head": ("On the site the same text has figures, a map of the concepts it "
                       "touches, and a section written for you: where this work can go next."),
        "howto_note": ("There is no link in this letter on purpose. The address is "
                       "<b>{site}</b>, and there are two ways to find yourself:"),
        "howto_1": "type <b>{aid}</b> into the search box, or",
        "howto_2": "open the authors section and look for your name: <b>{who}</b>.",
        "fix": "If we got something wrong, tell us and we will fix it.",
        "down": ("If you would rather not be there at all, reply with one line and the page "
                 "comes down the same day. No questions asked."),
        "closing": ("Nothing is for sale here and there is nothing to sign up for. We wrote "
                    "because it is your work and you should know where it is."),
    },
    "ru": {
        "tagline": "работы с arXiv простым языком, на пяти языках",
        "hello": "Здравствуйте, {who}!",
        "who_we": ("Мы bridge42worlds, небольшой некоммерческий проект. Читаем работы с arXiv "
                   "целиком и пересказываем простым языком — чтобы студент или инженер не из "
                   "вашей области понял, что сделано."),
        "did": "Так мы поступили с вашей работой {aid}. Весь пересказ ниже.",
        "howto_head": ("На сайте у этого же текста есть рисунки, карта понятий, которых он "
                       "касается, и раздел, написанный для вас: куда работа может пойти дальше."),
        "howto_note": ("Ссылки в письме нет намеренно. Адрес — <b>{site}</b>, "
                       "найти себя можно двумя способами:"),
        "howto_1": "введите <b>{aid}</b> в строку поиска, или",
        "howto_2": "откройте раздел авторов и найдите своё имя: <b>{who}</b>.",
        "fix": "Если мы что-то переврали, скажите, и мы поправим.",
        "down": ("Если вы предпочли бы вовсе там не быть, ответьте одной строкой, и страница "
                 "уйдёт в тот же день. Без выяснений."),
        "closing": ("Мы ничего не продаём, и подписываться не на что. Написали потому, что "
                    "работа ваша и вы должны знать, где она лежит."),
    },
    "ar": {
        "tagline": "أبحاث arXiv بلغة مبسّطة، بخمس لغات",
        "hello": "السلام عليكم {who}،",
        "who_we": ("نحن bridge42worlds، مشروع صغير غير ربحي. نقرأ أبحاث arXiv كاملةً ونعيد "
                   "سردها بلغة مبسّطة ليتمكّن طالب أو مهندس من خارج التخصّص من متابعة ما أُنجز."),
        "did": "فعلنا ذلك ببحثكم {aid}. السرد كاملاً أدناه.",
        "howto_head": ("على الموقع للنص نفسه رسوم، وخريطة للمفاهيم التي يلامسها، وقسم كُتب "
                       "لكم: إلى أين يمكن أن يمضي هذا العمل."),
        "howto_note": ("لا رابط في هذه الرسالة عن قصد. العنوان <b>{site}</b>، وهناك طريقتان "
                       "لتجدوا أنفسكم:"),
        "howto_1": "اكتبوا <b>{aid}</b> في خانة البحث، أو",
        "howto_2": "افتحوا قسم المؤلفين وابحثوا عن اسمكم: <b>{who}</b>.",
        "fix": "إن كان في سردنا خطأ، أخبرونا ونصحّحه.",
        "down": ("وإن كنتم تفضّلون ألّا تظهر الصفحة أصلًا، يكفي سطر واحد في الرد وتُزال في "
                 "اليوم نفسه، دون أسئلة."),
        "closing": ("لا نبيع شيئًا ولا تسجيل هنا. كتبنا إليكم لأن العمل عملكم، ومن حقّكم أن "
                    "تعرفوا أين هو."),
    },
}

SHELL = """<div style="margin:0;padding:24px 16px;background:#F4F2EC;
 font-family:-apple-system,'Segoe UI',Helvetica,Arial,sans-serif;color:#2A303C"{dir}>
<div style="max-width:620px;margin:0 auto;background:#FBFAF6;border:1px solid #E3DFD4;
 border-radius:10px;padding:28px 30px">
<div style="font-family:Georgia,'Times New Roman',serif;font-size:19px;font-weight:600;
 color:#0F1626;margin:0 0 4px">bridge42worlds</div>
<div style="font-size:12.5px;color:#5A6273;margin:0 0 22px">{tagline}</div>
{intro}
<div style="border:1px solid #E3DFD4;border-radius:8px;background:#F4F2EC;
 padding:20px 22px;margin:22px 0">
<div style="font-family:Georgia,'Times New Roman',serif;font-size:18px;font-weight:600;
 color:#0F1626;line-height:1.3;margin:0 0 14px">{retitle}</div>
{retext}</div>
{howto}
<div style="border-left:2px solid #C77F3A;padding-left:16px;margin:22px 0">{promises}</div>
<div style="font-size:14px;line-height:1.62;margin:0 0 18px">{closing}</div>
<div style="border-top:1px solid #E3DFD4;padding-top:14px;font-size:12.5px;color:#5A6273">
{sign} · {site}</div>
</div></div>"""


def _p(text, size="14.5px", color="#2A303C"):
    return (f'<div style="font-size:{size};line-height:1.62;color:{color};margin:0 0 12px">'
            f'{H.escape(text)}</div>')


def build(who, aid, lang, retitle, retext, sign):
    """Ту же мысль, что в текстовой версии, но глазами.

    Текст берём уже готовый — второй раз его не сочиняем, иначе две версии письма
    разойдутся на первой же правке.
    """
    w = WORDS.get(lang) or WORDS["en"]
    rtl = ' dir="rtl"' if lang == "ar" else ""
    intro = (f'<div style="font-size:15.5px;line-height:1.6;color:#0F1626;margin:0 0 14px">'
             f'{H.escape(w["hello"].format(who=who))}</div>'
             + _p(w["who_we"]) + _p(w["did"].format(aid=aid)))
    body = "".join(_p(x) for x in retext.split("\n\n") if x.strip())
    howto = (_p(w["howto_head"])
             + f'<div style="font-size:14.5px;line-height:1.62;margin:0 0 8px">'
               f'{w["howto_note"].format(site=SITE)}</div>'
             + f'<div style="font-size:14.5px;line-height:1.8;padding-left:14px;margin:0 0 6px">'
               f'· {w["howto_1"].format(aid=H.escape(aid))}<br>'
               f'· {w["howto_2"].format(who=H.escape(who))}</div>')
    promises = _p(w["fix"], size="14px") + _p(w["down"], size="14px")
    return SHELL.format(dir=rtl, tagline=H.escape(w["tagline"]), intro=intro,
                        retitle=H.escape(retitle), retext=body, howto=howto,
                        promises=promises, closing=H.escape(w["closing"]),
                        sign=H.escape(sign), site=SITE)
