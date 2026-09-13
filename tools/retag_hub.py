# -*- coding: utf-8 -*-
"""Переразметка v2: поправка на хабность, строгая достоверность, опора минимум 5.

Владелец 26 августа, после просмотра предложения волны 5, дословно по пунктам:
  · «0.5 мало, наобум не надо — надо чтобы была хорошая достоверность, либо вообще не надо»
  · «к общим понятиям не привязывать, только в крайнем случае, если работа прям общая»
  · «чтобы у понятия было минимум 5 статей — тогда это прям понятие»
  · «надо сделать, чтобы эта штука жила: пришла статья, мало связей — вытащили из неё
     своё понятие спецмеханизмом, желательно бесплатным»
  · «доведи до ума сам, пока без ML»

ЧТО БЫЛО НЕ ТАК. articles_retag.py волны 5 отбирал по сырой близости с порогом 0.50.
Проверка смотровой: 26 понятий стояли больше чем на 5% архива — quasi_periodic_oscillation
на 17.5%, charge_density_waves (физика твёрдого тела) на статьях про солнечный ветер.
Причина известна и давно записана у нас в tag_by_vector.py: в многомерном пространстве
часть векторов близка ВООБЩЕ КО ВСЕМУ («хабы»), и сырая близость меряет не родство
статьи с понятием, а общительность понятия.

КАК СЧИТАЕМ ТЕПЕРЬ.

  хабность      hub[j] = средняя близость карточки j ко всем статьям корпуса.
                У честного узкого понятия она ~0.35, у хаба ~0.55.

  сверх обычного margin[i,j] = S[i,j] - hub[j] — насколько ЭТА статья ближе к понятию,
                чем к нему близка средняя статья. Родство меряется этим числом,
                а не сырой близостью.

  двойная планка  берём, если margin >= MARGIN И сырая близость >= THR.
                Сырая планка оставлена как страховка от мусора: маленький margin
                на фоне низкой хабности — это всё ещё «ни о чём».

  общие понятия «не привязывать, только если работа прям общая» — это и есть margin:
                у хаба высокая hub[j], и статья должна быть к нему БЛИЖЕ, чем все,
                на ту же величину, что и у узких понятий. Крайний случай проходит,
                фон — нет. Отдельного списка «общих» не нужно: он вычисляется.

  опора >= 5    понятие, набравшее меньше пяти статей, — не понятие, а кандидат.
                Его привязки из разметки убираются, сам он уходит в отдельный список
                кандидатов: не удалён, а не дорос.

  правила волны 5 сохранены: не больше двух понятий с общим словом на статью,
                отсев синонимов по карточкам, потолок на статью.

ЖИВОЙ МЕХАНИЗМ (заготовка здесь же, --live). Пришла новая статья:
  1. Вектор у неё уже есть — bge-m3 считается при заливке в Vectorize, бесплатно.
  2. Прогоняем через эту же разметку. Связей достаточно — конец, статья легла в граф.
  3. Связей мало (< LIVE_MIN) — статья говорит о том, чего в реестре нет. БЕСПЛАТНЫЙ
     источник имени уже существует: генератор при создании статьи пишет
     data/gap-suggestions.jsonl — «каких тегов/законов не хватило» (479 записей
     накоплено). Берём его missing_tags как кандидатов.
  4. Кандидат копится в data/concept-candidates.jsonl. Набралось >= 5 статей —
     он дорос: карточку пишет модель (доли цента за пачку раз в неделю), понятие
     входит в реестр, статьи переразмечаются. До пяти — лежит и ждёт.
  Так реестр растёт ИЗ СТАТЕЙ и только там, где статьи есть, — без ручного посева.

ЗАПУСК (всё локально, без сети и без денег):
    python tools/retag_hub.py --tune          таблица порогов — выбрать глазами
    python tools/retag_hub.py                 разметить с настройками по умолчанию
    python tools/retag_hub.py --live ID       прогнать одну статью как «новую»
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT.parent / "b42-ml"
OUT = ROOT / "data" / "articles-retag-v2.json"
CAND = ROOT / "data" / "concept-candidates.jsonl"

MAX_PER_ARTICLE = 20
SIB_COS = 0.88          # порог «это синоним уже взятого» — из волны 5, работал
MAX_WORD_REPEAT = 2     # одно слово не чаще чем в двух понятиях статьи — оттуда же
THR = 0.55              # сырая планка-страховка
MARGIN = 0.14           # главная планка: насколько статья ближе к понятию, чем фон
MIN_SUPPORT = 5         # меньше — кандидат, не понятие
LIVE_MIN = 3            # у новой статьи меньше трёх связей = сигнал «чего-то нет»

STOP_W = {"of", "the", "and", "in", "a", "for", "with", "based", "using"}


# ── ДОМЕННЫЙ СТОРОЖ ──────────────────────────────────────────────────────────
# Найдено 13.09.2026 на первых восьми работах с bioRxiv: у статьи про Т-клетки при
# старении стояло stellar_age, stellar_population и asteroseismology, у статьи про
# «часы старения» — atomic_clock, quantum_clock и solar_flare_prediction. Из 41
# назначенной связи 16 пришли из чужих областей.
#
# Причина не в порогах. Вектор ищет ближайшее из ТОГО, ЧТО ЕСТЬ, а в реестре 3510
# понятий физических против 117 биологических и НИ ОДНОГО про старение. Для работы
# про возраст клеток ближайшим честно оказывается «возраст звезды»: слова те же,
# предмет другой. Поднимать порог бессмысленно — станет пусто вместо неверного, а
# неверное вернётся, как только слово совпадёт сильнее.
#
# Поэтому сторож смотрит не на близость, а на ПРЕДМЕТ. У каждого понятия есть дом —
# область, где живёт большинство его статей. Понятие из чужого дома к статье не
# цепляется. Два исключения, и оба нужны:
#   · методы ходят везде — машинное обучение и статистика одинаково уместны у
#     астрофизика и у биолога, и запрещать их значило бы обеднить разметку;
#   · кочующее понятие (живёт сразу в нескольких областях, нигде не большинство) —
#     это и есть общее знание, ради связей ради которого граф и строится.
# Понятие без статей пропускаем: оно новое, дома у него ещё нет.
# СЕМЬИ, А НЕ РАЗДЕЛЫ. Первый замер сторожа по разделам снимал 6,3% разметки всего
# архива — и снимал не там: больше всего в hep-ph, gr-qc, cond-mat, а в примерах стояло
# «у статьи math-ph снять el_nino_southern_oscillation». Но math-ph это та же физика, и
# понятия между физическими разделами ходят законно: разделение на astro-ph и hep-th
# существует для рубрикации, а не для смысла. Различие, которое нам действительно нужно,
# ровно одно — физика против биологии. Поэтому сравниваем СЕМЬИ.
FAMILY = {
    "astro-ph": "phys", "gr-qc": "phys", "hep-ph": "phys", "hep-th": "phys",
    "hep-ex": "phys", "hep-lat": "phys", "nucl-th": "phys", "nucl-ex": "phys",
    "quant-ph": "phys", "cond-mat": "phys", "physics": "phys", "math-ph": "phys",
    "nlin": "phys", "chao-dyn": "phys", "q-bio": "bio", "q-fin": "econ",
    "econ": "econ", "cs": "method", "math": "method", "stat": "method",
    # eess — обработка сигналов, изображения, системы: такая же прикладная
    # методология, и предмет у неё чужой по определению.
    "eess": "method",
}


def family(area):
    """Семья раздела. Незнакомый раздел считаем своей отдельной семьёй, а не чужой."""
    return FAMILY.get(area or "", area or "")


METHOD_AREAS = {"method"}
# Сколько статей понятия должно лежать в области статьи, чтобы понятие считалось здесь
# своим. Двух хватает: одна бывает случайной, две — уже привычка.
AT_HOME_MIN = 2
AT_HOME_SHARE = 0.15


def _areas_of_articles():
    """Область каждой статьи архива по её первому разделу. {номер без версии: 'q-bio'}."""
    import json as _j
    out = {}
    try:
        for a in _j.loads((ROOT / "lang" / "ru" / "articles-index.json")
                          .read_text(encoding="utf-8")):
            cat = (a.get("categories") or [""])[0]
            out[re.sub(r"v\d+$", "", a["id"])] = cat.split(".")[0]
    except (OSError, ValueError, KeyError):
        pass
    return out


def concept_homes(exclude=()):
    """Где живёт каждое понятие. {cid: (главная область, {область: сколько статей})}.

    exclude — номера (без версии), которые в подсчёт не идут. Это не мелочь, а условие
    правильности. Сторож спрашивает у понятия, живёт ли оно в области статьи, и ответ
    берёт из реестра — куда уже записана разметка ЭТОЙ ЖЕ статьи. Получалась петля:
    stellar_age ошибочно приписали двум био-работам, после чего он стал «своим» в
    биологии и продолжал к ним цепляться, подтверждая себя на каждом круге. Перемаркой
    это не лечится — круг сходится на неверном ответе (проверено 13.09: два прохода дали
    одно и то же). Статья не может выдавать понятию прописку сама себе.
    """
    import json as _j
    from collections import Counter
    art_area = _areas_of_articles()
    skip = {re.sub(r"v\d+$", "", x) for x in exclude}
    try:
        reg = _j.loads((ROOT / "data" / "concepts-live.json")
                       .read_text(encoding="utf-8"))["concepts"]
    except (OSError, ValueError, KeyError):
        return {}
    homes = {}
    for cid, v in reg.items():
        arts = [re.sub(r"v\d+$", "", x) for x in (v.get("articles") or [])]
        areas = Counter(family(a) for a in (art_area.get(x) for x in arts if x not in skip) if a)
        homes[cid] = (areas.most_common(1)[0][0] if areas else None, areas)
    return homes


def fits_domain(cid, art_area, homes):
    """Уместно ли понятие у статьи из этой области.

    ПЕРВАЯ ПОПЫТКА БЫЛА НЕВЕРНОЙ, и ошибка поучительная. Сторож спрашивал «кочует ли
    понятие» — то есть расползлись ли его статьи по областям без явного большинства. В
    нашем корпусе это пропускает почти всё: астрофизика занимает 27%, физика 17%, и у
    любого сколько-нибудь общего понятия главная область не дотягивает до порога. Так
    atomic_clock и solar_flare_prediction прошли к статье про часы старения как
    «кочующие».
    Правильный вопрос другой: живёт ли понятие В ЭТОЙ области. Он прямой, не зависит от
    перекоса корпуса и не требует подбирать порог «размазанности».
    """
    art_area = family(art_area)
    if not art_area:
        return True
    # Статья-метод принимает понятия любой семьи. Метод на то и метод, что прикладывается
    # к чужому предмету: работа по машинному обучению про климат законно несёт понятия
    # океана, а по статистике про геном — понятия биологии. Запрет здесь снимал бы ровно
    # те связи, ради которых междисциплинарную работу и интересно читать.
    if art_area in METHOD_AREAS:
        return True
    home, areas = homes.get(cid, (None, None))
    if home is None or not areas:
        return True                       # новое понятие, дома ещё нет
    if home == art_area or home in METHOD_AREAS:
        return True
    n = areas.get(art_area, 0)
    return n >= AT_HOME_MIN or n / sum(areas.values()) >= AT_HOME_SHARE


def load_all():
    """Векторы статей и карточек — из дерева ML, где волна их посчитала."""
    sys.path.insert(0, str(ML))
    import numpy as np
    import concepts_grow as g
    import concepts_super as cs

    art = g.load_corpus("ru")
    rowof, M = g.field_rows()
    have = [a for a in art if a in rowof]
    X = np.empty((len(have), M.shape[1]), dtype=np.float32)
    for i, a in enumerate(have):
        X[i] = M[rowof[a]]
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
    cids, CV = cs.load_cards()
    # Слитые понятия из разметки исключаем: их карточка ещё лежит в матрице, и
    # вектор с радостью назначит статье запись-указатель — ту самую, от которой
    # слияние и уводило. Проверять надо здесь, а не после: переразметка идёт по
    # всему архиву, и вычищать её потом дороже, чем не пустить сюда.
    live_p = ROOT / "data" / "concepts-live.json"
    try:
        import json as _json
        reg = _json.loads(live_p.read_text(encoding="utf-8"))["concepts"]
        keep = [i for i, c in enumerate(cids) if not (reg.get(c) or {}).get("merged_into")]
        if len(keep) != len(cids):
            print(f"  слитых понятий вне разметки: {len(cids) - len(keep)}")
            cids = [cids[i] for i in keep]
            CV = CV[keep]
    except Exception:
        pass
    return np, have, X, cids, CV


def word_sets(cids):
    return [set(w for w in re.split(r"[^a-z0-9]+", c.lower())
                if w and w not in STOP_W) for c in cids]


def rank_article(np, s_row, hub, CC, WORDS, thr, margin):
    """Отбор понятий одной статьи. Возвращает индексы в порядке убывания margin.

    Сортируем по margin, а не по сырой близости: иначе хаб, едва переваливший
    планку, встаёт ВЫШЕ узкого понятия, которое статье действительно родное, —
    и правило слов срезает не того."""
    m = s_row - hub
    j = np.where((m >= margin) & (s_row >= thr))[0]
    j = j[np.argsort(-m[j])]
    picked, seen = [], collections.Counter()
    for x in j:
        x = int(x)
        if WORDS[x] and max((seen[w] for w in WORDS[x]), default=0) >= MAX_WORD_REPEAT:
            continue
        if any(CC[x, y] >= SIB_COS for y in picked):
            continue
        picked.append(x)
        seen.update(WORDS[x])
        if len(picked) >= MAX_PER_ARTICLE:
            break
    return picked


def build(args):
    np, have, X, cids, CV = load_all()
    print(f"статей {len(have):,} · карточек {len(cids)}")

    S = X @ CV.T
    hub = S.mean(axis=0)                     # хабность каждой карточки
    CC = CV @ CV.T
    WORDS = word_sets(cids)
    print(f"хабность: медиана {float(np.median(hub)):.3f} · "
          f"90-й процентиль {float(np.percentile(hub, 90)):.3f} · "
          f"max {float(hub.max()):.3f} ({cids[int(hub.argmax())]})")

    # Сторож нужен и здесь: дневной путь снимает чужие понятия у статей дня, а полная
    # переразметка с --add-only прошлась бы следом и вернула их обратно. Замер 13.09 по
    # всему архиву: снимается 451 связь из 106 615 (0,42%), пустых статей становится на
    # одну больше. У физики убирает две связи, у биологии 391 — индексы Эль-Ниньо,
    # теорию квантового измерения, правило Борна. Ровно то, ради чего он и ставился.
    homes = {} if args.no_guard else concept_homes()
    art_area = _areas_of_articles()

    def run(thr, margin):
        got = {}
        for i, a in enumerate(have):
            picked = rank_article(np, S[i], hub, CC, WORDS, thr, margin)
            if homes:
                ar = art_area.get(re.sub(r"v\d+$", "", a), "")
                picked = [x for x in picked if fits_domain(cids[x], ar, homes)]
            got[a] = picked
        support = collections.Counter(x for v in got.values() for x in v)
        # опора: меньше MIN_SUPPORT — кандидат, из разметки убираем
        weak = {x for x, n in support.items() if n < MIN_SUPPORT}
        for a in got:
            got[a] = [x for x in got[a] if x not in weak]
        return got, support, weak

    if args.tune:
        n = len(have)
        print(f"\n{'порог':>6}{'margin':>8}{'на статью':>11}{'пусто':>7}"
              f"{'шире 5%':>9}{'макс охват':>26}{'кандидатов':>12}")
        for thr in (0.50, 0.55, 0.60):
            for margin in (0.10, 0.12, 0.14, 0.16):
                got, support, weak = run(thr, margin)
                per = [len(v) for v in got.values()]
                strong = {x: k for x, k in support.items() if x not in weak}
                wide = sum(1 for k in strong.values() if k / n > 0.05)
                top = max(strong.items(), key=lambda kv: kv[1]) if strong else (0, 0)
                print(f"{thr:>6.2f}{margin:>8.2f}{sum(per)/n:>11.1f}"
                      f"{sum(1 for p in per if not p):>7}"
                      f"{wide:>9}{cids[top[0]][:18]:>21} {100*top[1]/n:>3.0f}%"
                      f"{len(weak):>12}")
        return 0

    got, support, weak = run(args.thr, args.margin)
    n = len(have)
    per = [len(v) for v in got.values()]
    strong = {cids[x]: k for x, k in support.items() if x not in weak}
    wide = [(c, k) for c, k in strong.items() if k / n > 0.05]
    print(f"\nразметка: {sum(per)/n:.1f} понятий на статью · без понятий "
          f"{sum(1 for p in per if not p)} · понятий в ходу {len(strong)} "
          f"· кандидатов (<{MIN_SUPPORT} статей) {len(weak)}")
    print(f"понятий шире 5% архива: {len(wide)}"
          + (f" — {', '.join(c for c, _ in sorted(wide, key=lambda t: -t[1])[:5])}" if wide else ""))

    # ── ДОРАЗМЕТКА, А НЕ ПЕРЕРАЗМЕТКА ────────────────────────────────────
    # Владелец 30.08: «раз в неделю это доразметка всех статей, так? не полная
    # переразметка». Разница не в вычислении — оно одно и то же, — а в том, что
    # делать с результатом.
    #
    # Полная переразметка ЗАМЕЩАЕТ разметку статьи целиком. Значит любое дрожание
    # порога отбирает у статьи понятие, которое у неё было вчера: страница
    # меняется, отпечаток меняется, и пересобрать приходится весь архив — сорок
    # тысяч страниц ради того, что почти всегда не менялось. Ещё хуже смысл:
    # читатель видел связь, вернулся — связи нет, хотя ничего не случилось.
    #
    # Доразметка ДОПИСЫВАЕТ. Родились понятия — они находят свои старые статьи;
    # всё, что стояло раньше, остаётся стоять. Меняются ровно те статьи, которые
    # что-то получили, и пересобрать нужно только их. Это и есть недельный смысл:
    # реестр вырос — пусть архив об этом узнает.
    #
    # Цена честности: доразметка сама по себе не снимает ошибочную привязку.
    # Снимают их отдельные механизмы, где решение видно и обратимо, — слияние
    # двойников и правки реестра, — а не безымянный сдвиг порога.
    added_arts = added_links = 0
    if getattr(args, "add_only", False):
        try:
            prev = json.loads(OUT.read_text(encoding="utf-8")).get("articles") or {}
        except Exception:
            prev = {}
        merged = {}
        for a_, v in got.items():
            fresh = [cids[x] for x in v]
            old = list(prev.get(a_) or [])
            plus = [c for c in fresh if c not in old]
            if plus:
                added_arts += 1
                added_links += len(plus)
            # Старое впереди: порядок статьи не должен переставляться от того,
            # что реестр подрос. Потолок на статью общий, лишнее не влезает.
            merged[a_] = (old + plus)[:MAX_PER_ARTICLE]
        # Статьи, которых в этом проходе не оказалось вовсе (корпус шире поля),
        # сохраняют свою прежнюю разметку — доразметка ничего не отнимает.
        for a_, old in prev.items():
            merged.setdefault(a_, old)
        articles = merged
        print(f"доразметка: статей получили новое {added_arts} · "
              f"новых привязок {added_links} · всего статей в разметке {len(articles)}")
    else:
        articles = {a_: [cids[x] for x in v] for a_, v in got.items()}

    OUT.write_text(json.dumps({
        "built": "2026-08-26", "threshold": args.thr, "hub_margin": args.margin,
        "mode": "add-only" if getattr(args, "add_only", False) else "rebuild",
        "added_articles": added_arts, "added_links": added_links,
        "min_support": MIN_SUPPORT, "max_per_article": MAX_PER_ARTICLE,
        "density": round(sum(per) / n, 2),
        "note": "Переразметка v2: margin поверх хабности вместо сырой близости; "
                "понятия с опорой меньше пяти статей вынесены в кандидаты. "
                "Предложение, боевые файлы не тронуты.",
        "articles": articles,
    }, ensure_ascii=False), encoding="utf-8")
    print(f"→ {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} КБ)")

    # кандидаты: не удалены, а не доросли — живому механизму с ними работать
    with CAND.open("w", encoding="utf-8") as fh:
        for x in sorted(weak, key=lambda x: -support[x]):
            fh.write(json.dumps({"concept": cids[x], "articles": support[x],
                                 "from": "retag-v2"}, ensure_ascii=False) + "\n")
    print(f"→ {CAND.relative_to(ROOT)} ({len(weak)} кандидатов)")
    return 0


def live(args):
    """Статьи как «новые»: сколько связей даёт разметка и что делать, если мало."""
    np, have, X, cids, CV = load_all()
    S = X @ CV.T
    hub = S.mean(axis=0)
    CC = CV @ CV.T
    words = word_sets(cids)
    # Дома понятий и области статей считаем ОДИН раз: реестр на 47 МБ, а день приносит
    # два десятка статей — платить за разбор дважды незачем.
    _live_ids = [a.strip() for a in args.live.split(",") if a.strip()]
    homes = {} if args.no_guard else concept_homes(exclude=_live_ids)
    art_area = _areas_of_articles()
    out = {}
    # Список через запятую: день приносит два десятка статей сразу, а поле и
    # матрица сходства грузятся секунды — незачем платить за них двадцать раз.
    for aid in [a.strip() for a in args.live.split(",") if a.strip()]:
        # Папка статьи зовётся с версией (2608.21711v1), а корпус и поле — без неё:
        # версия у работы меняется, предмет остаётся тот же. Раньше это значило, что
        # передать сюда имя папки нельзя, и попытка разметить свежую статью честно
        # отвечала «нет в корпусе» — 29.08 на этом встала разметка целого дня.
        if aid not in have:
            base = aid.split("v")[0] if "v" in aid.rsplit("/", 1)[-1] else aid
            if base in have:
                aid = base
        if aid not in have:
            print(f"статьи {aid} нет в корпусе"); continue
        i = have.index(aid)
        picked = rank_article(np, S[i], hub, CC, words, args.thr, args.margin)
        if not args.no_guard:
            area = art_area.get(aid.split("v")[0], "")
            keep, dropped = [], []
            for x in picked:
                (keep if fits_domain(cids[x], area, homes) else dropped).append(x)
            if dropped:
                print(f"{aid}: сторож снял {len(dropped)} из чужих областей — "
                      + ", ".join(cids[x] for x in dropped[:6]))
            picked = keep
        print(f"{aid}: связей {len(picked)}")
        for x in picked:
            print(f"   {S[i][x]:.3f}  сверх фона {S[i][x]-hub[x]:+.3f}  {cids[x]}")
        if len(picked) < LIVE_MIN:
            print(f"связей меньше {LIVE_MIN} — статья говорит о том, чего в реестре нет.")
            print("живой механизм: взять missing_tags этой статьи из data/gap-suggestions.jsonl")
            print("и дописать в data/concept-candidates.jsonl; кандидат с 5+ статьями дорос.")
        # Пишем результат ВСЕГДА, в том числе пустой. Раньше пустое считалось «нечего
        # сохранять» — но при --live статью назвали поимённо, и пустой список это
        # полноценный ответ: старая разметка у неё неверна и должна уйти. Иначе снятое
        # сторожем осталось бы лежать в справочнике разметки навсегда.
        out[aid] = [cids[x] for x in picked]

    if getattr(args, "apply", False) and out:
        try:
            doc = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
        except Exception:
            doc = {}
        doc.setdefault("articles", {}).update(out)
        OUT.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        print(f"записано: {len(out)} статей в {OUT.name}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Переразметка с поправкой на хабность")
    ap.add_argument("--tune", action="store_true", help="таблица порогов, ничего не пишет")
    ap.add_argument("--thr", type=float, default=THR)
    ap.add_argument("--margin", type=float, default=MARGIN)
    ap.add_argument("--live", metavar="ID",
                    help="прогнать статьи как новые (id через запятую)")
    ap.add_argument("--apply", action="store_true",
                    help="с --live: дописать результат в общую разметку")
    ap.add_argument("--add-only", action="store_true",
                    help="ДОразметка: прежние привязки сохранить, дописать только "
                         "новые (недельный прогон)")
    ap.add_argument("--no-guard", action="store_true",
                    help="выключить доменный сторож (для сверки: что он снимает)")
    args = ap.parse_args()
    return live(args) if args.live else build(args)


if __name__ == "__main__":
    sys.exit(main())
