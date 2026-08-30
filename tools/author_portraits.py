#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Портрет автора: чем занимается, годы активности, график наших разборов.

Владелец 2026-08-19: «для странички автора реализовать описание его портфолио — чем
занимается, какие годы активности публикаций, график публикаций всех нами обработанных,
небольшой дашбордик, что-то лестное написать: судя по его работам, широкий кругозор.
Но чтобы его одного не выпячивать — собрать активных авторов, для них потом тиражироваться».

ЧТО СЧИТАЕТСЯ, А ЧТО ПИШЕТСЯ МОДЕЛЬЮ. Числа — годы, счётчики, разделы, соавторы, график —
считаются кодом по нашему архиву. Модель пишет ОДИН абзац и только по этим числам: она не
знает об авторе ничего сверх того, что мы разобрали, и врать ей нечем. Это важно: страница
автора — то место, где человек может найти себя, и выдуманная похвала там хуже молчания.

ЧЕСТНОСТЬ ФОРМУЛИРОВОК. Мы видим не всего автора, а только его работы в нашем архиве.
Поэтому портрет всегда оговаривает объём: «по работам, которые мы разобрали». Без этой
оговорки получится притязание на полное знание о человеке, которого у нас нет.

    python tools/author_portraits.py --show "Alexander Panov"   посмотреть, не записывая
    python tools/author_portraits.py --min 8 --limit 20         портреты активным авторам
    python tools/author_portraits.py --authors "A. D. Panov"    точечно, через запятую
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from common import ALL_LANGS, write_json_atomic  # noqa: E402

OUT = ROOT / "data" / "author-portraits.json"
LANGS = ALL_LANGS   # один список на проект: config.json через common.ALL_LANGS

# Имя из одних инициалов не опознаёт человека: «Y. Li» в нашем архиве — это десятки разных
# людей, слитых в один узел графа. Портрет такому узлу — заведомая ложь про несуществующего
# учёного с сорока восемью работами по всему на свете. Пишем портреты только тем, у кого есть
# развёрнутое имя хотя бы в одном слове.
FULL_NAME = re.compile(r"(^|[\s.])[A-ZА-Я][a-zа-яё]{2,}")


def load_index():
    """id статьи → (дата, теги, разделы). Берём русский индекс: он полный."""
    idx = json.loads((ROOT / "lang/ru/articles-index.json").read_text(encoding="utf-8"))
    out = {}
    for a in idx:
        aid = a.get("id")
        if not aid or aid in out:
            continue
        out[aid] = (a.get("date", ""), a.get("tags") or [], a.get("categories") or [])
    return out


def ids_from_archive(variants):
    """Работы автора прямо из архива, а не из графа.

    Граф авторов пересобирается вместе с агрегатами и потому отстаёт: свежесгенерированных
    работ в нём ещё нет, и портрет получился бы «нет разобранных работ» у автора, который
    только что появился на сайте. Архив — источник правды, он на диске сразу.
    """
    import glob
    want = {v.strip() for v in variants}
    out, first = [], {}
    for p in glob.glob(str(ROOT / "lang/ru/archive/*/*/data.json")):
        try:
            d = json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception:
            continue
        if want & set(d.get("authors") or []):
            aid = d.get("id", "")
            out.append(aid)
            first[aid] = (d.get("date", ""), d.get("authors") or [])
    return out, first



def _from_disk(aid):
    """Дата, теги и разделы статьи с диска — на случай, если индекс ещё не пересобран."""
    import glob
    for p in glob.glob(str(ROOT / f"lang/ru/archive/*/{aid}/data.json")):
        try:
            d = json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception:
            break
        tier = (d.get("popular") or {}).get("ru") or {}
        return (d.get("date", ""), tier.get("tags_vec") or d.get("tags") or [],
                d.get("categories") or [])
    return ("", [], [])


def stats_for(name, graph, index, tags_loc, variants=None, force_merge=False):
    """variants — все написания одного человека.

    Один учёный приходит к нам под несколькими именами: A. D. Panov, A. Panov,
    Alexander Panov, Alexander D. Panov — так его записали разные редакции arXiv. Для графа
    это четыре узла, для читателя один человек. Портрет считаем по всем написаниям сразу,
    иначе у каждого «половина себя»: годы короче, работ меньше, широта не видна.
    """
    if variants:
        ids, per_article = ids_from_archive(variants)
        # Сведение написаний — САМОЕ рискованное место всей затеи: имя не опознаёт человека.
        # Проверка 19 августа на Панове: «A. D. Panov» и «A. Panov» делят трёх соавторов по
        # коллаборации, а «Alexander Panov» на работе о PIC-коде не делит ни одного — почти
        # наверняка другой человек. Поэтому основанием для слияния служит не похожесть имён,
        # а ОБЩИЙ СОАВТОР: двух разных людей общая работа не связывает случайно.
        mine = {v.strip() for v in variants}
        per_variant = {}
        for v in mine:
            got, _ = ids_from_archive([v])
            per_variant[v] = {a for aid in got
                              for a in (per_article.get(aid) or ("", []))[1]} - mine
        base = max(per_variant, key=lambda v: len(per_variant[v]))
        weak = [v for v in per_variant
                if v != base and not (per_variant[v] & per_variant[base])]
        if weak:
            print("  ⚠️ нет общих соавторов с «%s»: %s" % (base, ", ".join(weak)))
            # Решение владельца 19.08: «с китайскими именами осторожно, лучше два, чем слить
            # в одного»; «есть сомнения — раздельно, а на странице ссылка: это же имя, и это
            # тоже я. Главное предупредить, дальше сами разберутся — пусть пишут письма».
            # Сомнение всегда решается В ПОЛЬЗУ РАЗДЕЛЕНИЯ: приписать человеку чужие работы
            # хуже, чем показать ему две страницы и дать способ их объединить.
            if not force_merge:
                print("     не свожу — это может быть другой человек. "
                      "Свести сознательно: --force-merge")
                variants = [v for v in variants if v not in weak]
                ids, per_article = ids_from_archive(variants)
        # Соавторов тоже берём из архива, а не из графа. Через граф вышла ложь в первом же
        # портрете: «все работы выполнены без соавторов» у человека, который состоит в
        # коллаборациях на восемьдесят имён — просто его узлов в графе ещё не было. Модель
        # честно пересказала ноль, который ей дали. Числа для портрета обязаны приходить
        # оттуда же, откуда сами работы.
        mine = {v.strip() for v in variants}
        coauth = {a for _aid, (_d, authors) in per_article.items() for a in authors} - mine
        data = {"articles": ids, "coauthors": sorted(coauth)}
    else:
        data = graph.get(name) or {}
    ids = data.get("articles", [])
    years, tags, cats = Counter(), Counter(), Counter()
    for aid in ids:
        d, tg, ct = index.get(aid) or _from_disk(aid)
        if d[:4].isdigit():
            years[int(d[:4])] += 1
        for t in tg:
            tags[t] += 1
        for c in ct:
            cats[c.split(".")[0]] += 1
    if not years:
        return None
    span = sorted(years)
    return {
        "name": name,
        "papers": len(ids),
        "first_year": span[0],
        "last_year": span[-1],
        "by_year": {str(y): years[y] for y in range(span[0], span[-1] + 1)},
        "top_tags": [t for t, _ in tags.most_common(8)],
        "top_tag_names": [str(tags_loc.get(t, {}).get("name", t)) for t, _ in tags.most_common(6)],
        "fields": [c for c, _ in cats.most_common(4)],
        "coauthors": len(data.get("coauthors", [])),
        # Какие написания сведены в один портрет. Страница показывает это читателю и
        # автору: он должен видеть допущение и иметь возможность сказать «это не я».
        "merged_names": sorted(variants) if variants else [],
    }


PROMPT = """Ты пишешь короткий портрет учёного для страницы автора на научно-популярном сайте.

ЧТО У ТЕБЯ ЕСТЬ. Только цифры ниже — они посчитаны по работам этого автора, которые мы
разобрали. Больше об этом человеке ты не знаешь НИЧЕГО и придумывать не имеешь права:
ни места работы, ни званий, ни открытий, ни биографии.

СТРОГИЕ ПРАВИЛА:
1. Два-три предложения. Не список, не анкета — связный абзац.
2. Обязательно оговорить объём: мы судим по работам в нашем архиве, а не обо всём авторе.
3. Похвала уместна, но только та, что следует из чисел. Работы в разных областях — можно
   сказать о широте. Двадцать лет между первой и последней — можно сказать о постоянстве.
   Если из чисел ничего такого не следует, просто опиши, чем занимается, без комплимента.
4. Не оценивать качество работ: «важный вклад», «прорыв», «выдающийся» — запрещено.
   Мы не рецензенты, мы читатели.
5. Не обращаться к автору на «вы» и не писать письмо — это описание для читателя сайта.

ДАННЫЕ:
Имя: {name}
Работ у нас разобрано: {papers}
Годы работ: с {first_year} по {last_year}
Области arXiv: {fields}
Чаще всего встречающиеся темы: {topics}
Соавторов в нашем архиве: {coauthors}

Ответь JSON: {{"portrait": "текст на русском"}}"""


def make_portrait(st):
    from common import chat, clean_json, job
    prompt = PROMPT.format(
        name=st["name"], papers=st["papers"], first_year=st["first_year"],
        last_year=st["last_year"], fields=", ".join(st["fields"]) or "не определены",
        topics=", ".join(st["top_tag_names"]) or "не определены", coauthors=st["coauthors"])
    with job(article=st["name"], kind="портрет автора"):
        r = chat("article_popular", prompt,
                 system="Ты научный редактор. Пишешь коротко и честно, без рекламных слов.")
    got = json.loads(clean_json(r.choices[0].message.content))
    text = (got.get("portrait") or "").strip()
    return text or None


def translate(text):
    """Портрет на остальные языки — общим переводчиком статей, не своим вызовом."""
    from gen_llm import translate_scipop
    out = {"ru": text}
    for lang in LANGS:
        if lang == "ru":
            continue
        try:
            tr = translate_scipop({"portrait": text}, lang)
        except Exception as ex:
            print(f"    перевод {lang}: {type(ex).__name__}")
            continue
        got = (tr or {}).get("portrait")
        if got and str(got).strip():
            out[lang] = str(got).strip()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", help="показать данные и портрет одного автора, ничего не записывая")
    ap.add_argument("--authors", help="список имён через запятую")
    ap.add_argument("--variants", help="написания ОДНОГО человека через | — портрет один "
                                       "на всех, страница каждого варианта его покажет")
    ap.add_argument("--force-merge", action="store_true",
                    help="свести написания, даже если общих соавторов нет (решение человека)")
    ap.add_argument("--min", type=int, default=8, help="минимум работ у нас, чтобы писать портрет")
    ap.add_argument("--limit", type=int, default=25, help="сколько авторов за прогон")
    ap.add_argument("--stats-only", action="store_true", help="только числа и график, без модели")
    args = ap.parse_args()

    graph = json.loads((ROOT / "data/authors-graph.json").read_text(encoding="utf-8"))
    graph = graph.get("graph", graph)
    index = load_index()
    tags_loc = json.loads((ROOT / "lang/ru/data/tags.json").read_text(encoding="utf-8"))

    variants = [v.strip() for v in args.variants.split("|")] if args.variants else None
    if variants:
        names = list(variants)
    elif args.authors:
        names = [n.strip() for n in args.authors.split(",") if n.strip()]
    elif args.show:
        names = [args.show]
    else:
        names = [n for n, d in graph.items()
                 if len(d.get("articles", [])) >= args.min and FULL_NAME.search(n)]
        names.sort(key=lambda n: -len(graph[n].get("articles", [])))
        names = names[:args.limit]

    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    done = 0
    for name in names:
        st = stats_for(name, graph, index, tags_loc, variants=variants,
                       force_merge=args.force_merge)
        if not st:
            print(f"  ⏭️ {name}: нет разобранных работ")
            continue
        if args.show:
            print(json.dumps(st, ensure_ascii=False, indent=1))
        entry = {"stats": st}
        if not args.stats_only:
            prev = old.get(name) or {}
            # Портрет переписываем, только если число работ изменилось: платить за один
            # и тот же абзац каждую неделю незачем.
            if prev.get("text") and (prev.get("stats") or {}).get("papers") == st["papers"]:
                entry["text"] = prev["text"]
            else:
                text = make_portrait(st)
                if not text:
                    print(f"  ⚠️ {name}: портрет не вышел")
                    continue
                entry["text"] = translate(text)
            if args.show:
                print(entry["text"]["ru"])
        if args.show:
            return 0
        keep = st.get("merged_names") or []
        if variants and name not in keep:
            # Имя, которое проверка отвергла, портрета не получает вовсе. Иначе выходит
            # ровно тот вред, ради которого проверка писалась: «Alexander Panov» с одной
            # работой о PIC-коде получал бы портрет чужих шестнадцати.
            print(f"  ⏭️ {name}: проверка не подтвердила, что это тот же человек — пропускаю")
            continue
        old[name] = entry
        if keep and entry.get("text"):
            # Один портрет — на все ПОДТВЕРЖДЁННЫЕ написания.
            for v in keep:
                old[v] = entry
        done += 1
        print(f"  ✅ {name}: {st['papers']} работ, {st['first_year']}–{st['last_year']}")

    write_json_atomic(OUT, old, indent=1)
    print(f"\nпортретов записано: {done} · всего в файле: {len(old)} · {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
