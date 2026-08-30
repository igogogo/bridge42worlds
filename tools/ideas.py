#!/usr/bin/env python3
"""Генератор идей проектов: что можно взять и сделать, опираясь на разобранное нами.

Владелец 12 августа: «делаем презентацию, надо сделать генератор идей проектов».

Чем это отличается от рекомендаций автору. Рекомендации адресованы человеку, чью работу
мы разобрали: они говорят «вот куда ЭТА работа может пойти». Идеи проектов адресованы
тому, у кого работы ещё нет — студенту, кафедре, инженеру: он приходит с областью
(«опреснение воды», «пыль на солнечных панелях») и получает несколько дел, за которые
можно взяться, с опорой на конкретные статьи.

Правило то же, что и у рекомендаций, и оно здесь важнее: **каждая идея обязана опираться
на реальные работы архива, и они названы**. Идея без опоры — это просто красивые слова,
которых любая модель насыплет сколько угодно; ценность нашей ровно в том, что за ней
стоят разобранные статьи, и их видно.

Соседей ищет вектор — Cloudflare Vectorize, индекс b42-articles, модель bge-m3, тот же,
что обслуживает поиск сайта. Когда ML отдаст полный вектор поля (3.13 млн работ arXiv),
tools/field.py подхватит его, и идеи начнут опираться не только на разобранное нами.

    python tools/ideas.py --show "опреснение морской воды"     посмотреть, не записывая
    python tools/ideas.py "dust on solar panels" --save        записать в data/ideas/
    python tools/ideas.py --topics data/idea-topics.txt        пакетом по списку тем
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

OUT = ROOT / "data" / "ideas"
SOURCES = 12          # сколько работ архива показываем модели
MIN_SCORE = 0.42      # ниже — случайный сосед; порог чуть мягче, чем у рекомендаций,
                      # потому что тема запроса шире, чем текст конкретной статьи
LANGS = ("en", "es", "ar", "fr")
# Добирать ли опоры из поля, когда своих мало. Выключается B42_IDEAS_FIELD=0 —
# на случай, когда нужны идеи строго по разобранному нами.
import os as _os                                                       # noqa: E402
USE_FIELD = _os.environ.get("B42_IDEAS_FIELD", "1") != "0"


def _slug(topic):
    s = re.sub(r"[^\w\s-]", "", topic.lower(), flags=re.U)
    return re.sub(r"[\s_]+", "-", s).strip("-")[:60] or "idea"


def sources(topic):
    """Работы архива, на которые идеи будут опираться."""
    import recommend
    nb = recommend.find_neighbours(topic)
    picked = [n for n in nb if (n.get("score") or 0) >= MIN_SCORE][:SOURCES]
    out = []
    for n in picked:
        s = recommend._neighbour(n)
        if s:
            s["url"] = article_url(s)
            s["abstract"] = our_abstract(s)
            out.append(s)
    return out


def our_abstract(src):
    """Короткое изложение НАШЕГО разбора — чтобы модель могла на него опереться.

    Замер 30 августа, тема «слияния чёрных дыр»: в опорах было пять наших работ и
    семь из поля, а модель построила все пять идей ТОЛЬКО на поле. Причина не в
    качестве: у работ поля в промпте стояла аннотация, а у наших — один заголовок
    по-русски. Опереться можно лишь на то, что прочёл.

    Берём популярное изложение из данных статьи: оно наше, короткое и на русском —
    том же языке, на котором модель пишет идеи.
    """
    url = src.get("url") or ""
    if not url:
        return ""
    folder = ROOT / url.replace("{lang}", "ru").strip("/")
    data = folder / "data.json"
    if not data.exists():
        return ""
    try:
        d = json.loads(data.read_text(encoding="utf-8"))
    except Exception:
        return ""
    for tier in ("popular", "simple", "advanced"):
        v = (d.get(tier) or {}).get("ru")
        if isinstance(v, dict):
            for key in ("description", "mini", "oneliner"):
                t = v.get(key)
                if isinstance(t, str) and len(t) > 80:
                    return " ".join(t.split())[:600]
            one = v.get("oneliner")
            if isinstance(one, str) and one.strip():
                return " ".join(one.split())[:600]
    return ""


def article_url(src):
    """Адрес нашей страницы разбора — проверенный по диску, а не собранный на веру.

    Опора приходит с датой и номером, но папка статьи зовётся то с версией
    (2608.21711v1), то без неё (2607.17623): версия зависит от того, какой её
    отдал arXiv в день разбора. Собрать адрес по шаблону значит поставить в идею
    ссылку, которая у половины опор ведёт в 404 — поэтому смотрим, что есть.
    """
    date, aid = src.get("date"), src.get("id")
    if not (date and aid):
        return ""
    base = ROOT / "lang" / "ru" / "archive" / str(date)
    for name in (aid, f"{aid}v1", f"{aid}v2"):
        if (base / name).is_dir():
            return f"/lang/{{lang}}/archive/{date}/{name}/"
    # Папки нет — честно возвращаем пусто: страница поставит поиск по номеру.
    return ""


def field_sources(topic, need):
    """Опоры из ПОЛЯ — всего arXiv, а не только разобранного нами.

    Зачем. Наш архив — шесть с лишним тысяч работ по физике и смежному; инженерный
    факультет приходит с опреснением воды и пылью на солнечных панелях, и по этим
    темам архив честно молчит: замер 30 августа дал ноль опор и ни одной идеи.
    Поле — 2,96 млн работ arXiv с 1991 года — про них знает.

    Почему это стало возможно только теперь. Прямой векторный проход по полю
    считался дорогим (в Vectorize он и правда стоил бы $128 в месяц), поэтому
    tools/field.py искал двухступенчато — словами, потом вектором по тремстам
    кандидатам. Но поле давно лежит у нас на диске, и полный проход по нему занял
    32 секунды на замере: за словесную ступень больше платить нечем.

    Что важно помнить читателю. Работа из поля НАМИ НЕ РАЗОБРАНА — у неё нет нашей
    страницы. Мы помечаем такие опоры (field=True), и это же становится заказом:
    идея, опирающаяся на неразобранную работу, — прямое указание, что её пора
    разбирать (см. tools/strata.py).
    """
    import field
    if not field.have_vectors():
        return []
    try:
        q = field.embed([topic])[0]
    except Exception as ex:
        print(f"  вектор темы не посчитан ({type(ex).__name__}) — поле пропускаю")
        return []
    hits = field.search_vectors(q, limit=need * 3)
    hits = [(sc, field_bare(a)) for sc, a in hits if sc >= MIN_SCORE]
    if not hits:
        return []
    meta = field._abstracts([(a, field._mon_of(a)) for _, a in hits[:need * 2]])
    out = []
    for sc, aid in hits:
        # _abstracts отдаёт кортеж (заголовок, аннотация, разделы, дата) — не словарь.
        m = meta.get(aid)
        if not m:
            continue
        title = (m[0] or "").strip()
        if not title:
            continue
        out.append({"id": aid, "full": False, "field": True, "score": round(sc, 3),
                    "titles": {"ru": title}, "abstract": (m[1] or "")[:600]})
        if len(out) >= need:
            break
    return out


def field_bare(aid):
    """Идентификатор поля без приставки: «arx:hep-th/9901001» → «hep-th/9901001»."""
    a = str(aid)
    return a[4:] if a.startswith("arx:") else a


def build(topic, show=False):
    """Идеи проектов по теме. Возвращает словарь или None."""
    from common import chat, clean_json, job

    src = sources(topic)
    n_ours = len(src)
    if len(src) < SOURCES and USE_FIELD:
        # Добираем полем. Наши разборы идут первыми и остаются главной опорой:
        # у них есть страница, читатель может пойти и прочитать.
        got = field_sources(topic, SOURCES - len(src))
        have = {x["id"] for x in src}
        src += [x for x in got if x["id"] not in have]
        if got:
            print(f"  наших работ {n_ours}, из поля добрано {len(src) - n_ours}")
    if len(src) < 3:
        print(f"«{topic}»: нашлось всего {len(src)} подходящих работ — "
              f"идей не будет (натянутые хуже, чем никаких)")
        return None

    lines = "\n".join(
        f"- [{s['id']}] ("
        + ("работа arXiv, нами ещё не разобрана" if s.get("field")
           else ("наш разбор, полный" if s.get("full") else "наш разбор, экспресс"))
        + f") {(s.get('titles') or {}).get('ru', '')}"
        + (f"{chr(10)}    {s['abstract'][:400]}" if s.get("abstract") else "")
        for s in src)
    NL = "\n"
    parts = [
        "Ты предлагаешь темы проектов человеку, который хочет взяться за дело в этой области:",
        "студенту инженерного факультета, аспиранту, инженеру на производстве.",
        "",
        f"ОБЛАСТЬ ЗАПРОСА: {topic}",
        "",
        "СТРОГИЕ ПРАВИЛА:",
        "1. Каждая идея ОБЯЗАНА опираться на работы из списка ниже — минимум на одну, лучше",
        "   на две. Их id пиши ТОЛЬКО в поле based_on, в тексте id не упоминай.",
        "   Нет опоры — идею не пишем. Красивых слов без основания не надо: их и без нас много.",
        "1а. При прочих равных ПРЕДПОЧИТАЙ работы, помеченные «наш разбор»: читатель может",
        "   открыть их на нашем сайте и прочитать по-русски, а работа поля — это ссылка на",
        "   английскую страницу arXiv. Если наша работа подходит хуже — бери ту, что подходит:",
        "   натянутая опора хуже честной ссылки наружу.",
        "2. Идея должна быть ДЕЛОМ, а не темой для реферата. Проверка простая: понятно ли, что",
        "   человек сделает руками в первую неделю. «Исследовать влияние X на Y» — не идея.",
        "   «Собрать стенд из трёх датчиков и померить, как запылённость меняет отдачу панели»",
        "   — идея.",
        "3. Честно про масштаб: если для дела нужна лаборатория за миллион, так и скажи в",
        "   поле needs. Не притворяйся, что всё делается на коленке, но и не раздувай.",
        "4. Не обещать результат. «Может получиться», «стоит проверить» — да; «позволит",
        "   решить проблему энергетики» — нет.",
        "5. Разные идеи — разного размера: одна на семестр, одна на диплом, одна на",
        "   несколько лет. Человек сам выберет по своим силам.",
        "",
        "ЧТО НАПИСАТЬ ДЛЯ КАЖДОЙ ИДЕИ:",
        "· title — короткое название дела, без пафоса",
        "· what — что именно делается, два-три предложения",
        "· why — почему это может быть интересно и кому пригодится, одно-два предложения",
        "· methods — КАК делать: методики, подходы, приёмы измерения или расчёта, по пунктам,",
        "  два-четыре пункта. Это главное в идее: без «как» она остаётся пожеланием.",
        "  Если методика взята из работы архива, скажи, из какой именно, словами.",
        "· first_step — с чего начать буквально: что собрать, что померить, что посчитать",
        "· needs — что понадобится: оборудование, данные, навыки. Честно.",
        "· risks — где эта затея скорее всего споткнётся, одно-два предложения. Без этого",
        "  идея выглядит легче, чем есть, и человек теряет время.",
        "· origin — ПОЧЕМУ мы это предлагаем: что уже есть в названных работах и чего между",
        "  ними НЕ ХВАТАЕТ. Два-три предложения. Это самое важное поле: читатель должен",
        "  увидеть ход мысли, а не готовый вывод. Пример хода: «в одной работе научились",
        "  мерить X, в другой — считать Y на этих же данных, но никто не проверил, держится",
        "  ли связь при Z». Без «чего не хватает» идея выглядит взятой с потолка.",
        "· scale — одно из: «семестр», «диплом», «годы»",
        "· based_on — id работ из списка, на которые идея опирается",
        "",
        f"РАБОТЫ НАШЕГО АРХИВА ПО ЭТОЙ ОБЛАСТИ:{NL}{lines}",
        "",
        "Ответь JSON: {\"ideas\": [{\"title\": \"...\", \"what\": \"...\", \"why\": \"...\",",
        " \"methods\": [\"...\"], \"origin\": \"...\", \"first_step\": \"...\", \"needs\": \"...\",",
        " \"risks\": \"...\", \"scale\": \"...\", \"based_on\": [\"id\"]}],",
        " \"note\": \"одно предложение о том, что в этой области сейчас происходит — или пустая строка\"}",
    ]
    try:
        with job(kind="идеи проектов"):
            r = chat("article_popular", NL.join(parts),
                     system="Ты инженер-практик и научный редактор. Предлагаешь дело, а не тему "
                            "для реферата. Пишешь коллеге, не ученику.")
        got = json.loads(clean_json(r.choices[0].message.content))
    except Exception as ex:
        print(f"«{topic}»: не сошлось — {type(ex).__name__}: {ex}")
        return None

    known = {s["id"] for s in src}
    ideas = []
    for x in (got.get("ideas") or []):
        based = [b for b in (x.get("based_on") or []) if b in known]
        if not (x.get("title") and x.get("what") and based):
            continue
        ideas.append({
            "title": str(x["title"]).strip(),
            "what": str(x["what"]).strip(),
            "why": str(x.get("why") or "").strip(),
            # methods и origin — то, ради чего раздел затевался. Владелец 12 августа:
            # «главное — почему мы это предлагаем: мы пробурили вектором, запланировали,
            # и вот ссылки почему». origin показывает ход мысли, methods — как делать.
            "methods": [str(m).strip() for m in (x.get("methods") or []) if str(m).strip()][:4],
            "origin": str(x.get("origin") or "").strip(),
            "first_step": str(x.get("first_step") or "").strip(),
            "needs": str(x.get("needs") or "").strip(),
            "risks": str(x.get("risks") or "").strip(),
            "scale": str(x.get("scale") or "").strip(),
            "based_on": based,
        })
    if not ideas:
        print(f"«{topic}»: ни одна идея не оперлась на реальные работы — пропускаю")
        return None

    # Как именно бурили — числа, а не слова. Читатель должен видеть не только вывод,
    # но и замер: сколько работ нашлось по смыслу, насколько близко легла ближайшая,
    # густо ли вокруг. Те же пороги, что у плотности в рекомендациях (recommend.py).
    scores = [s.get("score", 0) for s in src]
    import recommend as _rec
    top = max(scores) if scores else 0
    drill = {
        "found": len(src),
        "nearest": round(top, 3),
        "band": ("sparse" if top <= _rec.FRONTIER_SPARSE else
                 "dense" if top >= _rec.FRONTIER_DENSE else "mid"),
        "near": sum(1 for s in scores if s >= _rec.FRONTIER_NEAR),
        "full": sum(1 for s in src if s.get("full")),
        "model": "bge-m3",
    }
    out = {
        "topic": topic,
        "slug": _slug(topic),
        "built": datetime.now().strftime("%Y-%m-%d"),
        "note": str(got.get("note") or "").strip(),
        "drill": drill,
        "ideas": ideas[:5],
        "sources": src,
    }

    if show:
        print(f"\nОБЛАСТЬ: {topic}")
        if out["note"]:
            print(f"({out['note']})")
        for i, x in enumerate(out["ideas"], 1):
            print(f"\n{i}. {x['title']}  [{x['scale']}]")
            print(f"   {x['what']}")
            if x["why"]:
                print(f"   зачем: {x['why']}")
            if x.get("origin"):
                print(f"   почему: {x['origin']}")
            if x.get("methods"):
                print("   методики:")
                for m in x["methods"]:
                    print(f"     · {m}")
            if x["first_step"]:
                print(f"   первый шаг: {x['first_step']}")
            if x["needs"]:
                print(f"   нужно: {x['needs']}")
            if x.get("risks"):
                print(f"   риск: {x['risks']}")
            print(f"   опора: {', '.join(x['based_on'])}")
        print(f"\nработ архива в основе: {len(src)}")
    return out


def save(out):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{out['slug']}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ {out['topic']}: идей {len(out['ideas'])}, опор {len(out['sources'])} → {p.name}")
    return p


def translate(out):
    """Перевод набора идей ОБЩИМ переводчиком статей — своего здесь заводить нельзя."""
    from gen_llm import translate_scipop

    # Имя темы переводим вместе с содержимым: иначе араб видит арабские идеи под
    # русским заголовком и русские кнопки тем — половину страницы на чужом языке.
    flat = {"note": out.get("note", ""), "topic": out.get("topic", "")}
    for i, x in enumerate(out["ideas"]):
        for k in ("title", "what", "why", "origin", "first_step", "needs", "risks", "scale"):
            if x.get(k):
                flat[f"{k}_{i}"] = x[k]
        for j, m in enumerate(x.get("methods") or []):
            flat[f"m_{i}_{j}"] = m
    got = {}
    for lang in LANGS:
        tr = translate_scipop(flat, lang)
        if not tr:
            print(f"  ⚠️ перевод {lang} не вышел")
            continue
        ideas = []
        for i, x in enumerate(out["ideas"]):
            item = {"based_on": x["based_on"]}
            for k in ("title", "what", "why", "origin", "first_step", "needs", "risks", "scale"):
                item[k] = str(tr.get(f"{k}_{i}") or x.get(k) or "").strip()
            item["methods"] = [str(tr.get(f"m_{i}_{j}") or m).strip()
                               for j, m in enumerate(x.get("methods") or [])]
            ideas.append(item)
        got[lang] = {"note": str(tr.get("note") or "").strip(),
                     "topic": str(tr.get("topic") or "").strip(),
                     "ideas": ideas}
    out["lang"] = got
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("topic", nargs="?")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--translate", action="store_true", help="+4 языка общим переводчиком")
    ap.add_argument("--topics", help="файл со списком тем, по одной на строку")
    ap.add_argument("--fill-langs", action="store_true",
                    help="перевести УЖЕ НАПИСАННЫЕ наборы, не сочиняя их заново: "
                         "иначе идеи, написанные без --translate, остались бы "
                         "русскими навсегда")
    ap.add_argument("--only-new", action="store_true",
                    help="пропустить темы, по которым идеи уже написаны — так шаг "
                         "недельного прогона стоит денег только за новые темы")
    args = ap.parse_args()

    if args.fill_langs:
        # Переводим только то, чего ещё нет: набор с готовой веткой lang пропускаем,
        # иначе шаг платил бы за один и тот же перевод каждую неделю.
        done = 0
        for f in sorted(OUT.glob("*.json")):
            if f.name == "index.json":
                continue
            rec = json.loads(f.read_text(encoding="utf-8"))
            have = set((rec.get("lang") or {}).keys())
            if have >= set(LANGS):
                continue
            print(f"перевожу: {rec.get('topic')}")
            rec = translate(rec)
            f.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
            done += 1
        print(f"переведено наборов: {done}")
        return 0

    topics = []
    if args.topics:
        topics = [t.strip() for t in Path(args.topics).read_text(encoding="utf-8").splitlines()
                  if t.strip() and not t.startswith("#")]
    elif args.topic:
        topics = [args.topic]
    if not topics:
        print("нужна тема или --topics файл")
        return 2

    if args.only_new:
        was = len(topics)
        topics = [t for t in topics if not (OUT / f"{_slug(t)}.json").exists()]
        if was != len(topics):
            print(f"уже написано: {was - len(topics)}, беру {len(topics)}")
    done = 0
    for t in topics:
        out = build(t, show=args.show or not (args.save or args.topics))
        if not out:
            continue
        if args.translate:
            out = translate(out)
        if args.save or args.topics:
            save(out)
        done += 1
    if len(topics) > 1:
        print(f"\nготово: {done} из {len(topics)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
