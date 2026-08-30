#!/usr/bin/env python3
"""Раздел «Что мы предлагаем исследовать»: план работы, а не пожелание.

Владелец 12 августа: «раздел, где предлагаются исследования — короткое описание, куда
смотреть, как делать, какие работы прочесть, прямо чтобы был описан план исследования;
5–6 предложений, плюс разобранные статьи с нашими рекомендациями и опорами. Тогда будет
полный пример работы». И главное его требование: «почему мы это предлагаем — мы пробурили
вектором, и вот ссылки почему».

ОТКУДА БЕРЁТСЯ. Только из того, что уже проверено: у статьи есть раздел «Взгляд машины
знаний» (`recommend` в data.json), где каждое направление опирается на конкретные работы
архива, а идентификаторы опор проверены кодом при записи. Здесь мы эти направления
разворачиваем в план и добавляем замер окружения по полному полю arXiv.

ЧЕГО ЗДЕСЬ НЕТ И ПОЧЕМУ. Находок «поиска пробелов» (карта бурения ML: 600 областей,
74 пустых) на этой странице нет и не будет без явной пометки. Требование ML, 12 августа,
и оно верное: рекомендации — это развитие ИЗВЕСТНОГО с проверенными опорами, а пустоты
карты — претензия на неизвестное, которую мы пока не умеем отличить от правдоподобного
шума. Если положить рядом без пометки, читатель решит, что мы предсказали неизведанное.

    python tools/research.py --pick 8        показать, что отобралось, ничего не тратя
    python tools/research.py --build 6       собрать шесть направлений (модель + переводы)
    python tools/research.py --pages         пересобрать страницы из готовых карточек
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

# Кладём туда же, где живут остальные справочные страницы сайта: одна страница
# на все языки, содержимое фетчем из data/theory/<имя>.json с ветками по языкам.
# Так устроены hypotheses/frontier/discoveries — заводить своё устройство рядом
# с общим нельзя, это уже дважды кончалось переделкой.
OUT = ROOT / "data" / "theory" / "research.json"
from common import ALL_LANGS  # noqa: E402
LANGS = ALL_LANGS   # список языков один на проект: config.json через common.ALL_LANGS
TR_LANGS = ("en", "es", "ar", "fr")
# Насколько близко работа мирового поля должна лежать, чтобы считаться «про то же».
# Порог тот же, что у плотности в рекомендациях: ниже — это уже соседняя тема.
WORLD_NEAR = 0.70

# Тексты самой страницы. Живут здесь, а не в HTML: страница одна на пять языков и берёт
# всё содержимое из этого файла — так же, как соседние справочные разделы сайта.
# Оговорка (honest) обязательна и стоит вверху: раздел предлагает, а не отчитывается.
PAGE_TEXT = {
    "ru": {"title": "Что мы предлагаем исследовать",
           "subtitle": "Направления с планом работы — для тех, кто ищет, за что взяться",
           "lead": "Мы разбираем работы с arXiv и для каждой смотрим, что лежит рядом по "
                   "смыслу. Там, где вокруг работы собирается несколько независимых линий, "
                   "видно продолжение — вопрос, за который можно взяться. Здесь такие "
                   "вопросы собраны с планом: куда смотреть, как делать, что прочесть.",
           "honest": "Это предложения, а не результаты. Каждое опирается на конкретные "
                     "разобранные работы — они названы, и на них можно перейти. Мы "
                     "показываем развитие известного, а не предсказываем неизведанное: "
                     "искать пустоты в самой науке мы пока не умеем настолько, чтобы "
                     "отличать находку от правдоподобного шума."},
    "en": {"title": "What we suggest researching",
           "subtitle": "Directions with a work plan — for those looking for something to take on",
           "lead": "We review papers from arXiv and, for each one, look at what lies nearby "
                   "in meaning. Where several independent lines gather around a paper, a "
                   "continuation becomes visible — a question someone can take on. Those "
                   "questions are collected here with a plan: where to look, how to do it, "
                   "what to read.",
           "honest": "These are proposals, not results. Each rests on specific papers we "
                     "have reviewed — they are named and linked. We show the development of "
                     "the known; we do not predict the unknown: finding true gaps in science "
                     "itself is not something we can yet tell apart from plausible noise."},
    "es": {"title": "Qué proponemos investigar",
           "subtitle": "Direcciones con plan de trabajo, para quien busca en qué embarcarse",
           "lead": "Analizamos trabajos de arXiv y, para cada uno, miramos qué hay cerca por "
                   "significado. Donde se juntan varias líneas independientes, se ve una "
                   "continuación: una pregunta que alguien puede tomar. Aquí están esas "
                   "preguntas con un plan: dónde mirar, cómo hacerlo, qué leer.",
           "honest": "Son propuestas, no resultados. Cada una se apoya en trabajos concretos "
                     "que hemos analizado: están nombrados y enlazados. Mostramos el "
                     "desarrollo de lo conocido; no predecimos lo desconocido."},
    "fr": {"title": "Ce que nous proposons d’étudier",
           "subtitle": "Des directions avec un plan de travail, pour qui cherche par où commencer",
           "lead": "Nous analysons des travaux d’arXiv et regardons, pour chacun, ce qui se "
                   "trouve à côté par le sens. Là où plusieurs lignes indépendantes se "
                   "rejoignent, une suite apparaît : une question dont on peut se saisir. "
                   "Elles sont réunies ici avec un plan : où regarder, comment faire, que lire.",
           "honest": "Ce sont des propositions, pas des résultats. Chacune s’appuie sur des "
                     "travaux précis que nous avons analysés : ils sont nommés et liés. Nous "
                     "montrons le développement du connu ; nous ne prédisons pas l’inconnu."},
    "ar": {"title": "ما نقترح بحثه",
           "subtitle": "اتجاهات مع خطة عمل — لمن يبحث عن عمل يبدأ به",
           "lead": "نحلّل أبحاث arXiv وننظر لكل بحث في ما يقع قريبًا منه من حيث المعنى. وحين "
                   "تجتمع حول عمل عدة خطوط مستقلة، يظهر امتداد له: سؤال يمكن لأحد أن يتناوله. "
                   "هذه الأسئلة مجموعة هنا مع خطة: أين ننظر، كيف نعمل، وماذا نقرأ.",
           "honest": "هذه اقتراحات لا نتائج. كل اقتراح يستند إلى أبحاث محددة حلّلناها، وهي "
                     "مذكورة بالاسم مع روابطها. نعرض تطوير المعروف، ولا ندّعي التنبؤ "
                     "بالمجهول."},
}


def candidates():
    """Статьи с готовым разделом, отсортированные по силе основания.

    Сила — это не «красивее написано», а сколько под направлением реальной опоры:
    сперва число опор на ПОЛНЫЕ разборы (мы читали работу целиком, а не аннотацию),
    потом близость ближайшего соседа, потом число направлений.
    """
    rows = []
    for p in ROOT.glob("lang/ru/archive/*/*/data.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        rec = (d.get("recommend") or {}).get("ru")
        if not rec or not rec.get("directions"):
            continue
        nb = {n["id"]: n for n in (rec.get("neighbours") or []) if n.get("id")}
        cited = [b for x in rec["directions"] for b in (x.get("based_on") or [])]
        full_cited = sum(1 for c in cited if (nb.get(c) or {}).get("full"))
        rows.append({
            "id": p.parent.name,
            "date": p.parent.parent.name,
            "title": ((d.get("popular") or {}).get("ru") or {}).get("title", ""),
            "dirs": len(rec["directions"]),
            "full_cited": full_cited,
            "nearest": (rec.get("frontier") or {}).get("nearest", 0),
            "path": str(p),
        })
    rows.sort(key=lambda r: (-r["full_cited"], -r["nearest"], -r["dirs"]))
    return rows


def world(aid):
    """Замер по МИРОВОМУ полю: сколько работ arXiv лежит вплотную к этой теме.

    Это ответ на «куда смотреть»: не наше мнение, а число. Если рядом три тысячи работ —
    тема хожена, и надо искать щель; если двадцать — вокруг просторно.
    """
    try:
        import field
    except Exception:
        return {}
    if not field.have_vectors():
        return {}
    rows = field.bush(aid, want=200, quiet=True)
    if not rows:
        return {}
    near = [r for r in rows if r["score"] >= WORLD_NEAR]
    return {
        "checked": len(rows),
        "near": len(near),
        "nearest": rows[0]["score"],
        "ours": sum(1 for r in near if r.get("have")),
        "sample": [{"id": r["id"], "title": r["title"][:110], "score": r["score"],
                    "have": r["have"]} for r in near[:6]],
    }


def build_one(row, show=False):
    """Одно направление: вопрос + план + чтение. Один вызов модели."""
    from common import chat, clean_json, job
    import recommend as _rec

    d = json.loads(Path(row["path"]).read_text(encoding="utf-8"))
    rec = d["recommend"]["ru"]
    nb = {n["id"]: n for n in (rec.get("neighbours") or []) if n.get("id")}
    adv = (d.get("advanced") or {}).get("ru") or {}

    dirs = "\n".join(
        f"- {x['text']} (опоры: {', '.join(x.get('based_on') or [])})"
        for x in rec["directions"])
    reads = "\n".join(
        f"- [{i}] {(nb[i].get('titles') or {}).get('ru', '')} "
        f"({'полный разбор' if nb[i].get('full') else 'экспресс'})"
        for i in dict.fromkeys(b for x in rec["directions"] for b in (x.get("based_on") or []))
        if i in nb)
    w = world(row["id"])
    NL = "\n"
    parts = [
        "Ты оформляешь ПЛАН ИССЛЕДОВАНИЯ для страницы «Что мы предлагаем исследовать».",
        "Читатель — студент, аспирант или инженер, который ищет, за что взяться.",
        "",
        "ИСХОДНОЕ. Мы разобрали работу и уже написали её автору, куда она может пойти.",
        "Теперь из этих направлений надо сделать план, за который может взяться посторонний.",
        "",
        f"РАЗОБРАННАЯ РАБОТА: {adv.get('title') or row['title']}",
        f"О ЧЁМ ОНА: {(adv.get('description') or '')[:900]}",
        "",
        f"НАПРАВЛЕНИЯ, КОТОРЫЕ МЫ УЖЕ НАШЛИ:{NL}{dirs}",
        "",
        f"РАБОТЫ-ОПОРЫ:{NL}{reads}",
        "",
        "СТРОГИЕ ПРАВИЛА:",
        "1. Ничего не выдумывать сверх названного. Всё, что пишешь, должно выводиться из",
        "   направлений и опор выше.",
        "2. План — это ДЕЛО. Понятно, что человек делает в первую неделю, что меряет, чем",
        "   проверяет. «Исследовать влияние» — не план.",
        "3. Не обещать результат. «Может оказаться», «стоит проверить» — да. «Позволит",
        "   решить» — нет.",
        "4. Не поучать и не хвалить разобранную работу: мы не рецензируем.",
        "",
        "ЧТО НАПИСАТЬ:",
        "· question — сам вопрос, ОДНИМ предложением. Не тема («квантовая телепортация"
        " энергии»), а вопрос, на который можно ответить да/нет или числом.",
        "· plan — 5-6 предложений подряд, связным текстом: с чего начать, что собрать или",
        "  посчитать, что померить, чем проверить, на чём споткнётесь. Это главное поле.",
        "· skills — что нужно уметь и иметь: приборы, данные, расчётные средства. Коротко.",
        "· scale — одно из: «семестр», «диплом», «годы».",
        "· why_now — почему за это стоит браться сейчас, одно-два предложения, опираясь на",
        "  то, что уже сделано в названных работах.",
        "",
        'Ответь JSON: {"question": "...", "plan": "...", "skills": "...", "scale": "...",'
        ' "why_now": "..."}',
    ]
    try:
        with job(article=row["id"], kind="что исследовать"):
            r = chat("article_popular", NL.join(parts),
                     system="Ты научный руководитель, который выдаёт тему студенту. "
                            "Говоришь конкретно и без пафоса.")
        got = json.loads(clean_json(r.choices[0].message.content))
    except Exception as ex:
        print(f"  ⚠️ {row['id']}: не сошлось — {type(ex).__name__}")
        return None
    if not (got.get("question") and got.get("plan")):
        print(f"  ⚠️ {row['id']}: пустой ответ модели")
        return None

    reads_list = []
    for i in dict.fromkeys(b for x in rec["directions"] for b in (x.get("based_on") or [])):
        n = nb.get(i)
        if n:
            reads_list.append({"id": i, "date": n.get("date", ""), "full": n.get("full", False),
                               "score": n.get("score", 0), "titles": n.get("titles") or {}})

    out = {
        "id": row["id"], "date": row["date"], "slug": row["id"].replace(".", "-"),
        "built": datetime.now().strftime("%Y-%m-%d"),
        "source": {"id": row["id"], "date": row["date"], "title": row["title"]},
        # Идентификаторы вычищаем той же рукой, что и в рекомендациях: модель всё равно
        # пишет «из работы 2606.03634v1», а работа тут же стоит ссылкой с человеческим
        # заголовком в списке «что прочесть». Голый номер в тексте — только помеха.
        "question": _rec._drop_ids(got["question"]),
        "plan": _rec._drop_ids(got["plan"]),
        "skills": _rec._drop_ids(got.get("skills") or ""),
        "scale": str(got.get("scale") or "").strip(),
        "why_now": _rec._drop_ids(got.get("why_now") or ""),
        "reads": reads_list,
        "archive": {"nearest": (rec.get("frontier") or {}).get("nearest", 0),
                    "band": (rec.get("frontier") or {}).get("band", "")},
        "world": w,
    }
    if show:
        print(f"\n▸ {out['question']}")
        print(f"  {out['plan'][:400]}")
        print(f"  масштаб: {out['scale']} · опор: {len(reads_list)} · "
              f"в мире рядом: {w.get('near', '?')}")
    return out


def translate(out):
    """Перевод карточки общим переводчиком статей."""
    from gen_llm import translate_scipop
    flat = {k: out[k] for k in ("question", "plan", "skills", "scale", "why_now") if out.get(k)}
    got = {}
    for lang in TR_LANGS:
        tr = translate_scipop(flat, lang)
        if not tr:
            print(f"  ⚠️ перевод {lang} не вышел")
            continue
        got[lang] = {k: str(tr.get(k) or out.get(k) or "").strip() for k in flat}
    out["lang"] = got
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pick", type=int, help="показать N лучших кандидатов и выйти")
    ap.add_argument("--build", type=int, help="собрать N направлений (платно)")
    ap.add_argument("--pages", action="store_true", help="пересобрать страницы")
    args = ap.parse_args()

    if args.pick:
        rows = candidates()[:args.pick]
        print(f"кандидатов всего: {len(candidates())}\n")
        for r in rows:
            print(f"{r['full_cited']} полных опор · ближайший {r['nearest']:.3f} · "
                  f"{r['dirs']} напр. · {r['id']} · {r['title'][:60]}")
        return 0

    if args.build:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        book = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
        book.setdefault("page", PAGE_TEXT)
        items = book.get("items") or []
        have = {x.get("id") for x in items}
        done = 0
        for row in candidates():
            if row["id"] in have:
                continue
            out = build_one(row, show=True)
            if not out:
                continue
            out = translate(out)
            items.append(out)
            done += 1
            # Пишем после КАЖДОЙ карточки: прогон платный, и обрыв на середине не должен
            # стоить того, что уже посчитано.
            book["items"] = items
            book["built"] = datetime.now().strftime("%Y-%m-%d")
            OUT.write_text(json.dumps(book, ensure_ascii=False, indent=1), encoding="utf-8")
            if done >= args.build:
                break
        print(f"\nготово: +{done} направлений, всего {len(items)} → {OUT.name}")
        return 0

    print("нужен --pick N или --build N")
    return 2


if __name__ == "__main__":
    sys.exit(main())
