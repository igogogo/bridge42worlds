#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Популярное объяснение понятия — человеческим голосом, по-русски.

Владелец 29.08: «описание понятия всё-таки формально сложное научное, а популярного
и простого не хватает — чтобы с аналогиями, чтобы было ясно и понятно всем. Читаешь
статью в популярном изложении, а понятия идут всегда в одном сложном ключе».

ЧТО НЕ ТАК СЕЙЧАС. Популярный слой у понятий ЕСТЬ: поля description_popular,
how_it_works, practical_application, fun_fact_popular заполнены у 3 077 понятий
по-русски. Беда в том, что написаны они тем же голосом, что и формальная карточка.
Замер по всем: 40% предложений длиннее 22 слов, и почти каждое описание открывается
повтором собственного имени. Вот метрика Шварцшильда, понятие из двухсот статей:
«Метрика Шварцшильда — это точное решение уравнений поля Эйнштейна в общей теории
относительности, описывающее геометрию пространства-времени вокруг невращающейся
сферически симметричной массы». Поле называется популярным, а это учебник.

ПОЧЕМУ НЕ ВСЕ СРАЗУ. Понятия сильно разные по весу: 23 встречаются в сотне статей
и больше, 902 — в тридцати и больше, 839 — меньше чем в десяти. Первая сотня по
этому счёту закрывает большинство встреч читателя с понятием, и на ней видно, тот
ли получился тон. Переписывать три тысячи вслепую до того, как владелец увидел
десяток, — не то, за что стоит платить.

ПИШЕМ В ОТДЕЛЬНЫЙ ФАЙЛ, НЕ В РЕЕСТР. data/concepts-live.json читают и сборка, и
разметка; переписывать его посреди прогона — верный способ получить страницы из
двух разных состояний. Поэтому предложение живёт в data/concept-popular-ru.json,
а --merge вносит его в реестр отдельным осознанным шагом.

ПРОВЕРКИ РЕЗУЛЬТАТА (то, что не прошло, не записывается — остаётся прежний текст):
  · не открывается определением через собственное имя (проверка тут, opens_with_name);
  · не больше одной пары однокоренных в предложении (card_tautology.echoes);
  · длина в границах, нет предложений длиннее 25 слов;
  · нет предложения, где больше половины слов латиницей — утечка языка;
  · нет обращений к читателю («представьте», «вообразите») — запрет _style-core.

ЧИСЛА В ФАКТАХ ПРОВЕРЯЮТСЯ ОТДЕЛЬНО (--verify). Промт просит не выдумывать, и этого
мало: модель ошибается в арифметике, не замечая этого. Первый прогон дал «площадь
горизонта чёрной дыры с массой Солнца — около 10^12 км²», тогда как при радиусе 3 км
это 4πr², то есть примерно 109. Второй проход пересчитывает: считать заново легче,
чем сочинять, и такие промахи ловятся. Проверяющий тоже не безгрешен и иногда снимает
верное — но ошибается он В СТОРОНУ ОТКАЗА, а отсутствующий факт дешевле неверного.

    python tools/concept_popular.py --top 100            сверка: кого возьмём
    python tools/concept_popular.py --top 100 --run      написать (в отдельный файл)
    python tools/concept_popular.py --verify             пересчитать числа в фактах
    python tools/concept_popular.py --show 5             показать, что получилось
    python tools/concept_popular.py --merge              внести в реестр
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from common import chat, clean_json, load_prompt, write_json_atomic  # noqa: E402
from card_tautology import echoes  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

LIVE = ROOT / "data" / "concepts-live.json"
OUT = ROOT / "data" / "concept-popular-ru.json"
BATCH = 8

LAT = re.compile(r"[A-Za-z]{4,}")
ADDRESS = re.compile(r"\b(представ(ь|ьте|им)|вообрази(те)?|подумайте|а знаете ли)\b", re.I)


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def pick(live, top):
    """Понятия по числу статей: сначала те, кого читатель встречает чаще всего."""
    rows = []
    for cid, v in live.items():
        if v.get("merged_into"):
            continue
        n = len(v.get("articles") or [])
        rows.append((n, cid))
    rows.sort(key=lambda t: (-t[0], t[1]))
    return [cid for _, cid in rows[:top]]


def material(live, cid):
    """Что даём модели: имя, формальная карточка, механика, применение, соседи.
    Заголовки статей не даём — там свой стиль, и он тянет обратно в учебник."""
    v = live[cid]
    ru = (v.get("full_i18n") or {}).get("ru") or {}
    return {
        "id": cid,
        "имя": (v.get("names") or {}).get("ru") or cid.replace("_", " "),
        "класс": v.get("kind") or "",
        "карточка": ru.get("card") or v.get("card_en") or "",
        "механика": (ru.get("how_it_works") or "")[:700],
        "применение": (ru.get("practical_application") or "")[:400],
        "рядом": [r.get("id") for r in (v.get("related") or [])[:5]],
        "статей": len(v.get("articles") or []),
    }


def opens_with_name(name, text):
    """Открывается ли текст определением через собственное имя.

    Проверять надо ИМЕННО ЗАЧИН, а не весь текст. Готовая проверка circular() из
    card_tautology ловит имя понятия ГДЕ УГОДНО в тексте — она писалась для
    коротких карточек, где любое повторение лишнее. На объяснении в пятьсот знаков
    она отвергла семь работ из восьми: там слово честно встречалось в середине,
    и без него было бы не написать. Здесь плохо другое — «Метрика Шварцшильда —
    это точное решение…», то есть первая фраза, потраченная на пересказ заголовка.
    """
    head = (text or "").strip()[:90].lower()
    n = (name or "").strip().lower()
    if not head or not n:
        return False
    first = n.split()[0]
    if len(first) < 5:
        return False
    if not head.startswith(first):
        return False
    # После имени идёт связка определения: тире, «это», «называется».
    return bool(re.match(r"^\S+(\s+\S+){0,2}\s*(—|–|-|это|называ)", head))


def leaks(text):
    """Похоже ли на утечку языка — английская фраза посреди русского текста.

    Сначала здесь стояло «любое латинское слово вне скобок». Это отвергло восемь
    работ из ста, и все восемь напрасно: в русском научном тексте латиницей пишут
    имена приборов и объектов — LIGO, TESS, M87, GW170817, Event Horizon Telescope.
    Вычитать имя понятия не помогло: по-русски оно «м87» и «тесс», а в тексте стоит
    «M87» и «TESS», то есть та самая латиница, которая тут уместна.

    Утечка выглядит иначе — это ПРЕДЛОЖЕНИЕ на чужом языке. Его и ищем: фраза
    длиной от пяти слов, где больше половины слов латинские. Имя прибора такой
    проверки не задевает, а забытый по-английски абзац задевает сразу.
    """
    for sent in re.split(r"[.!?]", text or ""):
        words = re.findall(r"[^\W\d_]+", sent)
        if len(words) < 5:
            continue
        lat = sum(1 for w in words if re.fullmatch(r"[A-Za-z]+", w))
        if lat * 2 > len(words):
            return True
    return False


def ok(name, popular, fact):
    """Причина отказа или None. Молчаливая подмена текста хуже старого текста."""
    if not popular or len(popular) < 200:
        return "слишком коротко"
    if len(popular) > 900:
        return "слишком длинно"
    if opens_with_name(name, popular):
        return "начинается с повтора имени"
    # Одна пара однокоренных на пятьсот знаков — не беда; две и больше — уже стиль.
    ech = echoes(popular)
    if len(ech) >= 2:
        return f"однокоренные рядом ({ech[0][0]}/{ech[0][1]})"
    if ADDRESS.search(popular) or ADDRESS.search(fact or ""):
        return "обращение к читателю"
    if leaks(popular):
        return "похоже на утечку языка"
    for s in re.split(r"[.!?]", popular):
        if len(s.split()) > 25:
            return "предложение длиннее 25 слов"
    if fact and len(fact) > 400:
        return "факт слишком длинный"
    return None


def run(live, ids, done):
    """Пачками по восемь: длинный ответ модель обрывает, короткий не окупает запрос."""
    todo = [c for c in ids if c not in done]
    print(f"писать: {len(todo)} из {len(ids)} (готово {len(ids) - len(todo)})")
    tpl = load_prompt("concept-popular")
    got, bad = {}, {}
    for i in range(0, len(todo), BATCH):
        part = todo[i:i + BATCH]
        items = json.dumps([material(live, c) for c in part], ensure_ascii=False, indent=1)
        try:
            raw = chat("tags_describe", tpl.format(items=items)).choices[0].message.content
            ans = json.loads(clean_json(raw))
        except Exception as e:
            print(f"  !! пачка пропущена ({type(e).__name__}: {str(e)[:80]})")
            continue
        for cid in part:
            rec = ans.get(cid) or {}
            pop = (rec.get("popular") or "").strip()
            fact = (rec.get("fact") or "").strip()
            name = (live[cid].get("names") or {}).get("ru") or cid
            why = ok(name, pop, fact)
            if why:
                bad[cid] = why
                continue
            got[cid] = {"popular": pop, "fact": fact}
        print(f"  {min(i + BATCH, len(todo)):3}/{len(todo)} · принято {len(got)} · "
              f"отклонено {len(bad)}")
    return got, bad


VERIFY = (
    "Ты проверяешь ЧИСЛА и утверждения в коротких научных фактах. Для каждого факта "
    "посчитай или вспомни величину сам и сравни. Отвечай JSON: ключ факта к объекту "
    "{\"verdict\": \"ok\"|\"wrong\", \"why\": \"кратко, что не так\"}. "
    "Ставь wrong, если число ошибочно хотя бы на порядок, если утверждение неверно "
    "физически, или если ты не можешь его подтвердить. Сомневаешься — wrong: "
    "выкинутый факт дешевле неверного.\n\nФАКТЫ:\n"
)


def verify(live, done):
    """Второй проход по фактам: числа проверяются отдельным запросом.

    Первый прогон дал ошибку, которую видно невооружённым глазом: «площадь горизонта
    чёрной дыры с массой Солнца — около 10^12 квадратных километров», тогда как при
    радиусе 3 км это 4πr², то есть примерно 113. Промт просил не выдумывать, и этого
    оказалось мало: модель ошибается в арифметике, не заметив этого. Просить ту же
    модель ПЕРЕСЧИТАТЬ — приём дешёвый и ловит ровно такие промахи: считать заново
    легче, чем сочинять. Что не подтвердилось, теряет факт, но сохраняет описание.
    """
    items = {c: r["fact"] for c, r in done.items() if (r.get("fact") or "").strip()}
    ids = list(items)
    bad = {}
    for i in range(0, len(ids), 10):
        part = ids[i:i + 10]
        body = json.dumps({c: items[c] for c in part}, ensure_ascii=False, indent=1)
        try:
            raw = chat("tags_describe", VERIFY + body).choices[0].message.content
            ans = json.loads(clean_json(raw))
        except Exception as e:
            print(f"  !! пачка пропущена ({type(e).__name__}: {str(e)[:70]})")
            continue
        for c in part:
            v = (ans.get(c) or {})
            if str(v.get("verdict", "")).lower() != "ok":
                bad[c] = v.get("why") or "не подтверждено"
        print(f"  {min(i + 10, len(ids)):3}/{len(ids)} · снято {len(bad)}")
    return bad


def main():
    ap = argparse.ArgumentParser(description="Популярное объяснение понятий, русский")
    ap.add_argument("--top", type=int, default=100, help="сколько самых ходовых взять")
    ap.add_argument("--run", action="store_true", help="написать (тратит модель)")
    ap.add_argument("--show", type=int, default=0, help="показать столько готовых")
    ap.add_argument("--merge", action="store_true", help="внести в реестр понятий")
    ap.add_argument("--verify", action="store_true",
                    help="перепроверить числа в фактах и снять неподтверждённые")
    a = ap.parse_args()

    live = load(LIVE).get("concepts") or {}
    if not live:
        sys.exit("нет data/concepts-live.json")
    done = load(OUT, {})
    ids = pick(live, a.top)

    if a.show:
        for cid in list(done)[:a.show]:
            nm = (live.get(cid, {}).get("names") or {}).get("ru") or cid
            old = ((live.get(cid, {}).get("full_i18n") or {}).get("ru") or {}) \
                .get("description_popular") or "—"
            print(f"\n╔ {nm}  ({len(live.get(cid, {}).get('articles') or [])} статей)")
            print(f"║ было:  {old[:230]}")
            print(f"║ стало: {done[cid]['popular'][:230]}")
            print(f"╚ факт:  {done[cid].get('fact', '')[:200]}")
        return 0

    if a.verify:
        bad = verify(live, done)
        for c, why in bad.items():
            done[c]["fact"] = ""
            done[c]["fact_dropped"] = why
        write_json_atomic(OUT, done, indent=None)
        print(f"\nснято фактов: {len(bad)} из {len(done)}")
        for c, why in list(bad.items())[:15]:
            nm = (live.get(c, {}).get("names") or {}).get("ru") or c
            print(f"   {nm[:30]:30} {why[:90]}")
        return 0

    if a.merge:
        n = 0
        for cid, rec in done.items():
            v = live.get(cid)
            if not v:
                continue
            ru = (v.setdefault("full_i18n", {})).setdefault("ru", {})
            ru["description_popular"] = rec["popular"]
            if rec.get("fact"):
                ru["fun_fact_popular"] = rec["fact"]
            n += 1
        doc = load(LIVE)
        doc["concepts"] = live
        write_json_atomic(LIVE, doc, indent=None)
        print(f"внесено в реестр: {n:,} понятий")
        print("дальше: cloudflare/concepts_sync.py (карточки) и concepts_pages.py (страницы)")
        return 0

    if not a.run:
        print(f"возьмём {len(ids)} понятий, от {len(live[ids[0]].get('articles') or [])} "
              f"до {len(live[ids[-1]].get('articles') or [])} статей")
        print("  " + ", ".join((live[c].get("names") or {}).get("ru") or c for c in ids[:12]))
        print(f"уже написано: {len(done)} · --run напишет остальные")
        return 0

    got, bad = run(live, ids, done)
    done.update(got)
    write_json_atomic(OUT, done, indent=None)
    print(f"\n→ {OUT.name}: всего {len(done):,}")
    if bad:
        print(f"отклонено {len(bad)}:")
        for cid, why in list(bad.items())[:12]:
            print(f"   {cid:32} {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
