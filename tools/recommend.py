#!/usr/bin/env python3
"""Рекомендации автору: куда работа может пойти дальше. Полным статьям.

Владелец 10 августа: «к каждой статье при полном разборе давай на основе ML рекомендации:
вот можно идти сюда, посмотрите сюда… рекомендации очень аккуратные — типа советы по
развитию или рассуждения на тему важности этого, если уместно. Вот тогда да, это подарок
авторам, понимаешь».

Чем это отличается от «похожих статей». Похожие — про читателя: он дочитал и хочет ещё.
Рекомендации — про АВТОРА: он знает свою тему лучше нас, но не может держать в голове три
тысячи соседних работ, а мы можем. Мы не оцениваем его работу и не учим — мы показываем
поле вокруг неё.

Откуда берётся содержание. Соседей ищет ВЕКТОР (Cloudflare Vectorize, индекс b42-articles,
модель bge-m3 — тот же, что обслуживает поиск на сайте): не по совпадению слов, а по смыслу.
Формулирует модель, но только по найденному: каждая рекомендация обязана опираться на
конкретную статью, и эта статья названа. Нет опоры — нет рекомендации.

    python tools/recommend.py --show 2310.15936    посмотреть, ничего не записывая
    python tools/recommend.py 2310.15936           записать в data.json
    python tools/recommend.py --all-full           всем полным статьям
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv                                       # noqa: E402

load_dotenv(ROOT / ".env")

# Та же модель и тот же индекс, что обслуживают поиск на сайте — иначе «соседи» в
# рекомендациях и «похожее» в поиске начали бы жить разными жизнями.
EMBED_MODEL = "bge-m3"
VECTOR_INDEX = "b42-articles"
# Сколько соседей просим у вектора. Больше десяти модель начинает выбирать «покрасивее»,
# а не «по делу»: ей всё равно нужно назвать два-три направления.
NEIGHBOURS = 10
# Ниже этого сходства сосед считается случайным. Порог выше, чем у поиска: читателю
# сгодится «примерно про то же», автору — нет.
MIN_SCORE = 0.45
# Языки, кроме русского: раздел живёт на всех страницах статьи, иначе араб откроет
# продвинутую версию и увидит посреди неё русский блок.
LANGS = ("en", "es", "ar", "fr")


def find_neighbours(text, lang="ru"):
    """Соседи по смыслу: эмбеддинг запроса Workers AI + запрос в Vectorize напрямую.

    Сначала это ходило через наш публичный `/api/search` — «у Worker'а уже всё есть,
    зачем второй путь». Путь оказался закрыт: у поиска стоит защита от ботов, десять
    запросов в минуту и ШЕСТЬДЕСЯТ В СУТКИ с одного адреса (worker.js, botLimits), и
    массовый прогон честно упёрся в неё на восемнадцатой статье. Обходить собственную
    защиту лазейкой в Worker'е было бы хуже: дыру потом найдёт не только свой инструмент.

    Расхождения с поиском сайта здесь нет — та же модель bge-m3 и тот же индекс
    b42-articles, просто без публичного турникета перед ними.
    """
    import requests
    acc, tok = os.environ.get("CLOUDFLARE_ACCOUNT_ID"), os.environ.get("CLOUDFLARE_API_TOKEN")
    if not (acc and tok):
        print("  ⚠️ нет CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN — соседей не найти")
        return []
    h = {"Authorization": f"Bearer {tok}"}
    try:
        r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{acc}"
                          f"/ai/run/@cf/baai/{EMBED_MODEL}",
                          headers=h, json={"text": [text[:2000]]}, timeout=90)
        vec = ((r.json().get("result") or {}).get("data") or [None])[0]
        if not vec:
            print(f"  ⚠️ эмбеддинг не посчитался ({r.status_code})")
            return []
        r2 = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{acc}"
                           f"/vectorize/v2/indexes/{VECTOR_INDEX}/query",
                           headers=h, json={"vector": vec, "topK": NEIGHBOURS + 5,
                                            "returnMetadata": "all"}, timeout=90)
        j = r2.json()
        if not j.get("success"):
            print(f"  ⚠️ Vectorize: {str(j.get('errors'))[:120]}")
            return []
        matches = (j.get("result") or {}).get("matches") or []
    except Exception as ex:
        print(f"  ⚠️ вектор не ответил: {type(ex).__name__}")
        return []
    out = []
    for m in matches:
        if (m.get("score") or 0) < MIN_SCORE:
            continue
        md = m.get("metadata") or {}
        out.append({"id": m.get("id"), "score": m.get("score"),
                    "title": md.get("title") or "", "description": md.get("summary") or ""})
    return out[:NEIGHBOURS]


def _abstract(d):
    """Аннотация arXiv. Поле бывает и строкой, и словарём по языкам — у статей разных лет."""
    a = d.get("abstract")
    if isinstance(a, dict):
        a = a.get("ru") or a.get("en") or ""
    if isinstance(a, dict):          # abstract.ru = {popular, advanced, ...}
        a = a.get("advanced") or a.get("popular") or a.get("simple") or ""
    return a if isinstance(a, str) else ""


_ID_RE = re.compile(r"\s*(?:arXiv:)?[\[(]\s*(?:arXiv:)?[\w.\-]*\d{4}\.\d{4,5}(?:v\d+)?\s*[\])]"
                    r"|\s*(?:arXiv:)\s*\d{4}\.\d{4,5}(?:v\d+)?")


def _drop_ids(text):
    """Убираем идентификаторы статей из текста направления.

    Модель всё равно вставляет «…рядом лежит работа [2506.03282v2]», сколько ни проси —
    а на странице тот же сосед уже стоит ссылкой с настоящим заголовком под строкой
    «опора:». Читать одно и то же дважды, второй раз голым номером, незачем.
    """
    t = _ID_RE.sub("", str(text))
    t = re.sub(r"\s+([,.;:])", r"\1", t)
    return re.sub(r"\s{2,}", " ", t).strip()


# Пороги плотности откалиброваны по корпусу, а не взяты с потолка: у bge-m3 косинусы
# лежат в узком коридоре, и «0.6» ничего не значит. Замер 11 августа по выборке статей
# архива: лучший сосед — медиана 0.639, десятый процентиль 0.606, девяностый 0.760.
# Отсюда: ниже 0.61 — работа стоит на отшибе, выше 0.70 — тема хожена. Между — молчим:
# у большинства статей именно так, и вердикт был бы шумом. Числа пересчитывать, когда
# архив заметно вырастет; настоящую карту плотности облака делает ML (задача №19).
FRONTIER_SPARSE = 0.61
FRONTIER_DENSE = 0.70
FRONTIER_NEAR = 0.65      # с этого сходства сосед считается «рядом», а не «где-то там»


def _frontier(nb):
    """Плотность окружения: измерение, а не мнение модели."""
    top = max((n.get("score") or 0) for n in nb)
    band = ("sparse" if top <= FRONTIER_SPARSE else
            "dense" if top >= FRONTIER_DENSE else "mid")
    return {"nearest": round(top, 3), "band": band,
            "dense": sum(1 for n in nb if (n.get("score") or 0) >= FRONTIER_NEAR)}


def _cited(dirs):
    """Идентификаторы, на которые опираются направления."""
    return {b for x in dirs for b in (x.get("based_on") or [])}


def _neighbour(n):
    """Сосед для ссылки: заголовки сразу на всех языках, взятые из его же data.json.

    Через перевод их гонять незачем — они уже переведены, когда сосед публиковался.
    Заодно это единственный способ не разойтись с настоящим заголовком статьи.
    """
    aid = n.get("id")
    if not aid:
        return None
    hits = list(ROOT.glob(f"lang/ru/archive/*/{aid}/data.json"))
    if not hits:
        return None
    try:
        d = json.loads(hits[0].read_text(encoding="utf-8"))
    except Exception:
        return None
    titles = {}
    for lang in ("ru",) + LANGS:
        for tier in ("popular", "advanced", "simple"):
            t = ((d.get(tier) or {}).get(lang) or {}).get("title")
            if t:
                titles[lang] = t
                break
    if "ru" not in titles:
        return None
    # full — есть ли у соседа НАСТОЯЩАЯ продвинутая версия. Читатель раздела уже стоит на
    # продвинутом уровне, и уводить его оттуда на популярный — потеря глубины (владелец
    # 11 августа). Но у экспресса продвинутой версии нет: там баннер «полная готовится»,
    # и ссылка на неё была бы обманом. Поэтому решаем по данным соседа, а не по желанию.
    return {"id": aid, "date": hits[0].parent.parent.name, "full": not d.get("express"),
            "titles": titles, "score": round(n.get("score", 0), 3)}


def translate_recommend(out, lang):
    """Перевод раздела ОБЩИМ переводчиком статей, а не своим вызовом.

    Своё здесь уже стоило дня: 8 августа я написал отдельный перевод для авторской работы,
    и арабская страница вышла на 12% по-русски — модель молча вернула оригинал. У общего
    `translate_scipop` есть и проверка языка, и добор грязных полей, и журнал отказов;
    пустой перевод он возвращает честным None, а не подделкой.

    Переводим ПЛОСКУЮ форму: направления идут списком строк, а `based_on` — идентификаторы
    статей — приклеиваются обратно кодом. Переводчику идентификаторы не показываем вовсе:
    он их переводил (проверено на тегах, /tags/markov_chain → арабский в пути ссылки).
    """
    from gen_llm import translate_scipop
    flat = {"seen": out["seen"], "strength": out["strength"],
            "significance": out["significance"], "ideas": list(out["ideas"]),
            "directions": [x["text"] for x in out["directions"]]}
    flat = {k: v for k, v in flat.items() if v}
    try:
        tr = translate_scipop(flat, lang)
    except Exception as ex:
        print(f"  ⚠️ перевод {lang}: {type(ex).__name__}")
        return None
    if not tr:
        print(f"  ⚠️ перевод {lang} не вышел — язык пропущен")
        return None
    got_dirs = tr.get("directions") or []
    dirs = []
    for i, x in enumerate(out["directions"]):
        t = got_dirs[i] if i < len(got_dirs) and isinstance(got_dirs[i], str) else ""
        if t.strip():
            dirs.append({"text": t.strip(), "based_on": x["based_on"]})
    if not dirs:
        print(f"  ⚠️ перевод {lang}: направления потерялись — язык пропущен")
        return None
    return {"seen": str(tr.get("seen") or "").strip(),
            "strength": str(tr.get("strength") or "").strip(),
            "directions": dirs,
            "ideas": [str(i).strip() for i in (tr.get("ideas") or []) if str(i).strip()],
            "significance": str(tr.get("significance") or "").strip(),
            "neighbours": out["neighbours"], "frontier": out.get("frontier") or {}}


def build(aid, show=False):
    """Рекомендации для одной статьи. Возвращает словарь или None."""
    hits = list(ROOT.glob(f"lang/ru/archive/*/{aid}/data.json"))
    if not hits:
        print(f"нет статьи {aid}")
        return None
    p = hits[0]
    d = json.loads(p.read_text(encoding="utf-8"))
    if d.get("express"):
        print(f"{aid}: экспресс — рекомендации только полным статьям")
        return None

    adv = (d.get("advanced", {}) or {}).get("ru") or {}
    pop = (d.get("popular", {}) or {}).get("ru") or {}
    title = adv.get("title") or pop.get("title") or ""
    # Текст продвинутого уровня лежит не одним полем, а разделами — собираем в том же
    # порядке, в каком его читает автор. Аннотацию arXiv добавляем в конец: она короткая,
    # но именно в ней стоят термины, которых наш пересказ мог не сохранить.
    body = "\n\n".join(x for x in [
        adv.get("description"), adv.get("context"), adv.get("methods"),
        adv.get("results"), adv.get("implications"), _abstract(d),
    ] if x)[:6000]
    if not body:
        print(f"{aid}: нет полного текста")
        return None

    # Ищем соседей по СУТИ работы, а не по заголовку: заголовок у нас образный
    # («Цифровая гребёнка в шуме»), и вектор по нему уводит в поэзию.
    query = f"{title}. {adv.get('oneliner', '')} {body[:1200]}"
    nb = [n for n in find_neighbours(query) if n.get("id") != aid]
    if len(nb) < 3:
        print(f"{aid}: соседей мало ({len(nb)}) — рекомендаций не будет")
        return None

    # Помечаем, что за сосед. Экспресс — пересказ авторской аннотации, а не разбор работы,
    # и опираться на него слабее: разведка 11 августа показала, что 26 «опор» из 31 были
    # экспрессами. Запрещать их совсем нельзя — полных разборов в архиве всего шестая часть,
    # раздел бы просто перестал появляться. Поэтому не запрет, а предпочтение в промпте.
    out_nb = [x for x in (_neighbour(n) for n in nb) if x]
    kind = {n["id"]: ("полный разбор" if n.get("full") else "экспресс") for n in out_nb}
    lines_txt = "\n".join(
        f"- [{n.get('id')}] ({kind.get(n.get('id'), '?')}) {n.get('title', '')} — "
        f"{(n.get('description') or n.get('oneliner') or '')[:200]}"
        for n in nb)

    from common import chat, clean_json, job
    NL = "\n"
    parts = [
        "Ты пишешь короткий раздел в конце научно-популярной статьи. Он адресован НЕ читателю,",
        "а АВТОРУ разобранной работы и его коллегам.",
        "",
        "Задача: показать, куда эта работа может пойти дальше, опираясь на соседние работы",
        "из нашего архива. Мы не рецензируем и не оцениваем — мы показываем поле вокруг.",
        "",
        "СТРОГИЕ ПРАВИЛА, они важнее полноты:",
        "1. Каждое направление ОБЯЗАНО опираться на конкретную работу из списка ниже.",
        "   Её id пиши ТОЛЬКО в поле based_on. В самом тексте id не упоминай — ссылку на",
        "   работу подставит сайт. Нет опоры — направление не пишем.",
        "   У каждого соседа в скобках стоит, что это: «полный разбор» — мы читали работу",
        "   целиком; «экспресс» — только авторскую аннотацию. Опирайся В ПЕРВУЮ ОЧЕРЕДЬ на",
        "   полные разборы; на экспресс — только если подходящего полного в списке нет.",
        "2. Не поучать. Автор знает свою тему лучше нас. Тон: «может быть интересно",
        "   посмотреть», «рядом лежит вот такой ход» — не «вам следует», не «вы упустили».",
        "3. Не оценивать работу: никаких «убедительно», «слабо», «недостаточно обосновано».",
        "4. Если сказать нечего — верни пустой список. Натянутая рекомендация хуже, чем её",
        "   отсутствие: она обесценивает настоящие.",
        "5. Не изображать научный авторитет. Мы говорим «в нашем архиве рядом лежит вот это»,",
        "   а не «наука считает».",
        "6. ТОЛЬКО КОНСТРУКТИВНОЕ. Владелец 10 августа: «всё только позитивное — куда двигаться",
        "   дальше, в чём сила, какие идеи можно апробировать». Это подарок автору, а не разбор",
        "   полётов.",
        "",
        "ЧТО ИМЕННО НАПИСАТЬ (порядок задан владельцем: сначала что сделано, потом наши",
        "мысли, потом заключение):",
        "· seen — что сделано в работе, как мы её прочли: два-три предложения. Без оценок,",
        "  просто: что взяли, как считали, что получили. Автор должен узнать свою работу.",
        "· strength — в чём сила, одно-два предложения. Не похвала вообще, а конкретно:",
        "  что здесь сделано такого, на чём можно строить дальше.",
        "· directions — два-три направления развития, каждое с опорой на статью из списка.",
        "· ideas — что можно апробировать: конкретный ход, приём, проверка. Коротко,",
        "  два-три пункта, каждый — одно предложение.",
        "· significance — почему это может быть важно. Пустая строка, если сказать нечего.",
        "",
        f"РАЗОБРАННАЯ РАБОТА:{NL}{title}{NL}{body[:3500]}",
        "",
        f"СОСЕДНИЕ РАБОТЫ ИЗ АРХИВА (найдены по смыслу):{NL}{lines_txt}",
        "",
        "Ответь JSON:",
        '{"seen": "...", "strength": "...",',
        ' "directions": [{"text": "...", "based_on": ["id"]}],',
        ' "ideas": ["..."], "significance": "..."}',
    ]
    prompt = NL.join(parts)
    try:
        # job() помечает вызовы этого потока — иначе расход раздела растворяется в «прочем»
        # и в отчёте по деньгам его не видно ни отдельно, ни внутри полной статьи.
        with job(article=aid, kind="машина знаний"):
            r = chat("article_popular", prompt,
                     system="Ты научный редактор. Пишешь коллеге, а не ученику.")
        got = json.loads(clean_json(r.choices[0].message.content))
    except Exception as ex:
        print(f"  ⚠️ {aid}: рекомендации не сошлись — {type(ex).__name__}")
        return None

    dirs = []
    known = {n.get("id") for n in nb}
    for x in (got.get("directions") or []):
        based = [b for b in (x.get("based_on") or []) if b in known]
        # Направление без опоры на реальную статью выбрасываем: это ровно тот случай,
        # когда модель придумывает связь, которой в архиве нет.
        if x.get("text") and based:
            dirs.append({"text": _drop_ids(x["text"]), "based_on": based})

    out = {
        "seen": str(got.get("seen") or "").strip(),
        "strength": str(got.get("strength") or "").strip(),
        "directions": dirs[:3],
        "ideas": [str(i).strip() for i in (got.get("ideas") or []) if str(i).strip()][:3],
        "significance": str(got.get("significance") or "").strip(),
        # В список соседей идут первые шесть — И ВСЕ, на кого опираются направления, даже
        # если сосед был девятым по близости. Иначе у направления пропадает строка «опора:»:
        # ссылку не на что построить, и совет повисает словами без источника.
        "neighbours": [x for x in out_nb
                       if x["id"] in _cited(dirs) or [n["id"] for n in nb].index(x["id"]) < 6],
        "frontier": _frontier(nb),
    }
    if not dirs:
        print(f"{aid}: модель не нашла, что посоветовать — раздела не будет")
        return None

    if show:
        print(f"\n{title}")
        if out["seen"]:
            print(f"\nЧТО СДЕЛАНО В РАБОТЕ:\n  {out['seen']}")
        if out["strength"]:
            print(f"\nВ ЧЁМ СИЛА:\n  {out['strength']}")
        print(f"\nНАПРАВЛЕНИЯ ({len(dirs)}):")
        for i, x in enumerate(dirs, 1):
            print(f"  {i}. {x['text']}")
            print(f"     опора: {', '.join(x['based_on'])}")
        if out["ideas"]:
            print("\nЧТО МОЖНО ПОПРОБОВАТЬ:")
            for i in out["ideas"]:
                print(f"  · {i}")
        if out["significance"]:
            print(f"\nПОЧЕМУ ЭТО МОЖЕТ БЫТЬ ВАЖНО:\n  {out['significance']}")
        print(f"\nсоседей найдено: {len(nb)}, лучший {nb[0].get('score', 0):.3f}")
        return out

    # Отдельным полем верхнего уровня, а не внутри уровня чтения: раздел один на статью
    # и показывается только в продвинутой версии («у полной продвинутой версии или где-то
    # прям отдельным пунктом» — владелец 10 августа). Внутри уровней он бы лежал в трёх
    # копиях на каждый из пяти языков.
    rec = d.setdefault("recommend", {})
    rec["ru"] = out
    for lang in LANGS:
        tr = translate_recommend(out, lang)
        if tr:
            rec[lang] = tr
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    langs_ok = [l for l in LANGS if l in rec]
    print(f"✅ {aid}: направлений {len(dirs)}, соседей {len(nb)}, языки ru+{'/'.join(langs_ok)}")
    return out


def fix_links():
    """Дописать соседям поле `full` там, где раздел уже построен. Без модели, бесплатно.

    Зачем отдельный режим: поле появилось 11 августа, а к тому времени раздел уже стоял
    у первых статей — и у ВСЕХ их соседей поля не было. Страница в таком случае честно
    считает, что продвинутой версии у соседа нет, и ведёт на популярную: ровно та потеря
    глубины, на которую владелец и указал. Перезапускать `build()` ради этого нельзя —
    он перепишет тексты и заплатит за них второй раз.
    """
    fixed = 0
    for p in sorted(ROOT.glob("lang/ru/archive/*/*/data.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        rec = d.get("recommend") or {}
        if not rec:
            continue
        touched = False
        for lang_rec in rec.values():
            for n in (lang_rec.get("neighbours") or []):
                if "full" in n or not n.get("id"):
                    continue
                hits = list(ROOT.glob(f"lang/ru/archive/*/{n['id']}/data.json"))
                if not hits:
                    continue
                try:
                    nd = json.loads(hits[0].read_text(encoding="utf-8"))
                except Exception:
                    continue
                n["full"] = not nd.get("express")
                touched = True
        if touched:
            p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            fixed += 1
    print(f"✅ ссылки на соседей выправлены у {fixed} статей")
    return 0


def _queue():
    """Очередь на разбор машиной знаний — по ценности, а не по алфавиту.

    Хронологический обход (он был первым) начинал с 2023 года и упирался в самые старые
    статьи, тогда как раздел нужнее всего там, где есть живой автор и свежая работа.
    Порядок: авторские работы → свежие полные разборы → всё остальное по убыванию даты.
    """
    rows = []
    for p in ROOT.glob("lang/ru/archive/*/*/data.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("express") or (d.get("recommend") or {}).get("ru"):
            continue
        rows.append((0 if d.get("author_work") else 1, p.parent.parent.name, p.parent.name))
    # Свежие вперёд: сортируем по дате в обратную сторону внутри каждой группы.
    rows.sort(key=lambda r: (r[0], [-ord(c) for c in r[1]]))
    return [r[2] for r in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("aid", nargs="?")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--all-full", action="store_true")
    ap.add_argument("--fix-links", action="store_true",
                    help="дописать соседям признак полной версии (бесплатно, без модели)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--force", action="store_true",
                    help="пересчитать, даже если раздел уже есть (после добора опор)")
    args = ap.parse_args()

    if args.fix_links:
        return fix_links()

    if args.all_full:
        done = 0
        for aid in _queue():
            if build(aid):
                done += 1
            if args.limit and done >= args.limit:
                break
        print(f"\nготово: {done} статей")
        return 0

    if not args.aid:
        print("нужен id статьи или --all-full")
        return 2
    if args.force and not args.show:
        # Куст из всего поля вырос — старый раздел опирался на то, чего рядом ещё не было.
        p = next(ROOT.glob(f"lang/ru/archive/*/{args.aid}/data.json"), None)
        if p:
            d = json.loads(p.read_text(encoding="utf-8"))
            if d.pop("recommend", None):
                p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"{args.aid}: прежний раздел убран, считаем заново")
    build(args.aid, show=args.show)
    return 0


if __name__ == "__main__":
    sys.exit(main())
