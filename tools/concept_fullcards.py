# -*- coding: utf-8 -*-
"""Полные карточки новым понятиям + перевекторизация от полного текста.

Владелец 26.08: «да, пиши полные карточки и перевекторизуй — но сначала я посмотрю
описание, и не попадём в дорогой период».

ЧТО ПИШЕМ. У ~686 новых понятий есть только однострочник (card_en, опора вектора).
Полная карточка — определение в 3-5 предложений: что это, как работает или
используется, как проявляется в работах корпуса. По-английски; переводы — отдельным
шагом вместе с остальными.

ТРИ КОМАНДЫ, платное отделено и охраняется:

  --sample N   написать N образцов на просмотр владельцу (микро-трата, ~$0.001/шт)
  --run        все понятия без полной карточки. ПРОВЕРЯЕТ ТАРИФ DeepSeek: дорого
               только в будни 01:00–04:00 и 06:00–10:00 UTC (04:00–07:00 и 09:00–13:00
               по Кувейту), остальное вдвое дешевле. В пик отказывается; --force-peak
               осознанно обходит.
  --revector-all  то же, но и для 527 старых понятий, чей полный текст лежит в
               английских витринах: весь реестр встаёт на одну опору (бесплатно).
  --revector   пересчитать векторы понятий с полной карточкой (bge-m3, тот же движок)
               и обновить матрицу b42-ml/data/concept-cards.f16 (бэкап рядом).
               После него переразметка: python tools/retag_hub.py --thr 0.50 --margin 0.12

Смета --run: ~686 понятий × (~700 токенов вход + ~200 выход) ≈ $0.9-1.4 (развёрнутые записи, решение владельца 26.08).

Результат копится в data/concept-fullcards.json ({id: текст}) и вливается в
data/concepts-live.json полем card_full_en — страницы понятий показывают его
как описание после перегенерации concepts_pages.py.
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT.parent / "b42-ml"
OUT = ROOT / "data" / "concept-fullcards.json"
LIVE = ROOT / "data" / "concepts-live.json"

sys.path.insert(0, str(ROOT))
from common import write_json_atomic  # noqa: E402
from tools.concept_harvest import env, embed  # noqa: E402 — тот же .env и тот же движок

PER_CALL = 3          # развёрнутые записи — простор важнее пачки
MAX_TITLES = 12       # заголовков работ в опоре

SYS = """You write full encyclopedia entries for scientific concepts in a physics
knowledge base for curious adults. Register: popular science, slightly above casual —
a motivated reader without a physics degree follows everything, a physicist finds
nothing to object to.

For each numbered concept you get its id, a one-sentence seed definition, and real
article titles from our corpus where the concept is used.

Return a JSON array, one object per concept, same order:
{"n": <number>,
 "description": "<2-3 paragraphs: what it is, why it matters, what it explains —
                 the main text of the entry>",
 "how_it_works": "<1-2 paragraphs: the mechanism, plainly>",
 "history": "<1 short paragraph: who introduced it and when, if honestly known;
             empty string if you are not sure — never invent>",
 "practical_application": "<1-2 sentences: where it is used in technology or research>",
 "fun_fact": "<1 surprising but TRUE sentence; empty string if none comes honestly>"}

Rules:
1. Ground research context in the given titles; never invent properties or history.
2. No advertising, no "amazing/incredible", no rhetorical questions.
3. Empty string is always better than an invented fact.
4. NEVER define a thing through itself. "Extra time dimensions are additional time
   coordinates" tells a reader who did not know the term exactly nothing. Open the
   term through simpler notions. The same goes for roots standing next to each
   other — "quantum mechanical quantization" says one word twice.
Output ONLY the JSON array."""


# Пиковые часы DeepSeek — единственное место, где записан тариф. Действующее правило
# (владелец прислал 08.09): «Peak hours are 01:00-04:00 and 06:00-10:00 UTC, Monday
# through Friday; all other hours are off-peak», off-peak вдвое дешевле.
PEAK_UTC = ((1, 4), (6, 10))


def cheap_window(now=None):
    """Половинный тариф DeepSeek: всё, КРОМЕ будних 01:00-04:00 и 06:00-10:00 UTC.

    Прежняя редакция описывала старый прейскурант — «дёшево 16:30-00:30 UTC и выходные».
    Переплатой это не грозило (старое окно целиком внутри нового), но запирало работу:
    во вторник в 13:35 UTC семь инструментов отказывались считать, хотя час половинный.
    Теперь дорого 7 часов в будни, дёшево 133 часа в неделю из 168.

    ДЕНЬ НЕДЕЛИ БЕРЁМ ПО UTC, и двусмысленности здесь нет, хотя DeepSeek живёт по Пекину:
    все пиковые часы раньше 16:00 UTC, а Пекин это UTC+8 — прибавка восьми часов день не
    перекатывает, поэтому пекинский и всемирный день на этих часах совпадают. Отдельного
    правила про выходные больше не нужно: суббота и воскресенье не будни, значит дёшевы
    целиком — ровно то, что мы отдельно чинили 23.08.

    Функция одна на все инструменты (её импортируют formula_anatomy, bc_run, night_run,
    group_names, cards_translate_ru, unit_systems_seed): правило про деньги должно жить
    в одном месте, иначе следующее изменение тарифа найдут не везде.
    """
    now = now or datetime.now(timezone.utc)
    if now.weekday() >= 5:                 # суббота и воскресенье — дёшево целиком
        return True
    h = now.hour + now.minute / 60
    return not any(a <= h < b for a, b in PEAK_UTC)


def peak_hint(now=None):
    """Строка для человека: сейчас дорого или дёшево и когда сменится."""
    now = now or datetime.now(timezone.utc)
    if cheap_window(now):
        return f"{now:%H:%M} UTC — половинный тариф DeepSeek"
    h = now.hour + now.minute / 60
    end = next(b for a, b in PEAK_UTC if a <= h < b)
    return f"{now:%H:%M} UTC — ПИКОВЫЙ тариф, дешевеет в {end:02d}:00 UTC"


def targets(with_legacy=False):
    live = json.loads(LIVE.read_text(encoding="utf-8"))["concepts"]
    done = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    idx = {}
    try:
        for a in json.loads((ROOT / "lang" / "ru" / "articles-index.json")
                            .read_text(encoding="utf-8")):
            idx[a["id"]] = a
            idx[a["id"].split("v")[0]] = a
    except Exception:
        pass
    # У КОГО УЖЕ ЕСТЬ ТЕКСТ — из старых справочников: это и есть настоящий
    # признак «описание не нужно». Раньше здесь стояло «есть русское имя»:
    # прокси работал, пока русские имена были только у 529 переживших понятий.
    # 27.08 переводчик дал имена всем 3231 — и шаг стал считать, что у всех
    # уже есть описания, написав 284 карточки вместо 2800 и отрапортовав
    # «готово». Прокси заменён на факт.
    rich = set()
    for fname in ("tags.json", "laws.json"):
        p = ROOT / "lang" / "ru" / "data" / fname
        if not p.exists():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for cid_, v in d.items():
            if isinstance(v, dict) and (v.get("description_popular")
                                        or v.get("how_it_works")):
                rich.add(cid_)

    out = []
    for cid, c in live.items():
        # Слитому понятию карточка не нужна: страница отдаёт переадресацию, а
        # запрос к модели за текстом для указателя — деньги на ветер.
        if c.get("merged_into"):
            continue
        if cid in done:
            continue
        if cid in rich and not with_legacy:
            # Старое понятие: развёрнутый текст уже лежит в справочнике, и странице он
            # и нужен — она берёт справочник первым, карточку только после него.
            # Но ВЕКТОР от справочника считать нельзя: замер 08.09 показал, что текст
            # витрины (писан читателю, медиана 790 знаков против 515 у карточек) сдвигает
            # разметку у 70% статей и теряет верные привязки. Поэтому --with-legacy:
            # написать этим понятиям карточку по общей мерке, чтобы весь реестр стоял
            # на одной опоре. На страницы это не влияет — там справочник в приоритете.
            continue
        titles = []
        for aid in c.get("articles", [])[:MAX_TITLES]:
            a = idx.get(aid) or idx.get(aid.split("v")[0])
            if a and a.get("title"):
                titles.append(a["title"])
        out.append((cid, c.get("card_en", ""), titles))
    return out, done, live


_PREFIX = re.compile(
    r"^(Why it matters|How it works|In practice|Fun fact|History|Description|"
    r"Practical application)\s*[:—–-]\s*", re.I)


def ask_batch(batch, key):
    lines = []
    for i, (cid, seed, titles) in enumerate(batch, 1):
        tl = "; ".join(t[:70] for t in titles[:MAX_TITLES]) or "(no titles)"
        lines.append(f"{i}. id={cid}\n   seed: {seed}\n   titles: {tl}")
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": SYS},
                     {"role": "user", "content": "\n".join(lines)}],
        "temperature": 0.3, "max_tokens": 4000,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        d = json.loads(r.read().decode("utf-8"))
    raw = d["choices"][0]["message"]["content"]
    import re
    m = re.search(r"\[.*\]", raw, re.S)
    got = json.loads(m.group(0)) if m else []
    out = {}
    for it in got:
        try:
            n = int(it["n"])
            if not (1 <= n <= len(batch)):
                continue

            def clean(s, cap):
                """Срезать заголовок раздела, если модель начала с него текст.

                Иногда ответ приходит в виде «Why it matters: MLE — рабочая
                лошадка…»: модель повторяет название поля из промпта первым же
                словом. На странице это выглядит английским заголовком посреди
                текста. Срезаем только с двоеточием или тире — «In practice, …»
                это нормальное начало предложения, а не заголовок.
                """
                return _PREFIX.sub("", str(s or "").strip())[:cap]
            rec = {
                # имена полей — ТЕ ЖЕ, что в старых справочниках: страница рисует
                # старые и новые записи одним кодом, без второй ветки
                "description_popular": clean(it.get("description"), 4000),
                "how_it_works": clean(it.get("how_it_works"), 2500),
                "history": clean(it.get("history"), 1500),
                "practical_application": clean(it.get("practical_application"), 600),
                "fun_fact_popular": clean(it.get("fun_fact"), 400),
            }
            if len(rec["description_popular"]) > 200:
                out[batch[n - 1][0]] = rec
        except (KeyError, ValueError, TypeError):
            continue
    return out


def write_cards(limit=None, force_peak=False, with_legacy=False):
    try:
        from tools.freeze import guard
        guard("полные карточки понятий (DeepSeek)")
    except ImportError:
        pass
    if limit is None and not cheap_window() and not force_peak:
        print(peak_hint() + ".")
        print("пик: будни 01:00–04:00 и 06:00–10:00 UTC, остальное — половина цены.")
        print("владелец просил не попадать в дорогой период; --force-peak обойдёт.")
        return 1
    key = env("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit("нет DEEPSEEK_API_KEY")
    todo, done, _ = targets(with_legacy)
    if limit:
        todo = todo[:limit]
    print(f"понятий без полной карточки: {len(todo)}")
    batches = [todo[s:s + PER_CALL] for s in range(0, len(todo), PER_CALL)]

    def one(batch):
        try:
            return ask_batch(batch, key)
        except Exception as e:
            print(f"  сбой пачки: {e}")
            return {}

    # Шесть пачек разом. Ночью 27.08 этот шаг писал две тысячи карточек четыре
    # часа — по пятнадцать в минуту, и почти всё это время процесс ждал ответа.
    # Копилка пишется из главного потока: она уже страдала от обрыва на записи,
    # и класть в неё из нескольких потоков нельзя.
    with ThreadPoolExecutor(max_workers=6) as ex:
        for i, got in enumerate(ex.map(one, batches), 1):
            done.update(got)
            if i % 4 == 0 or i == len(batches):
                OUT.write_text(json.dumps(done, ensure_ascii=False, indent=1),
                               encoding="utf-8")
                print(f"  {len(done)} готово", flush=True)
    # вливаем в живой справочник — страницы возьмут при перегенерации
    live_all = json.loads(LIVE.read_text(encoding="utf-8"))
    for cid, rec in done.items():
        if cid in live_all["concepts"]:
            live_all["concepts"][cid]["full"] = rec
    write_json_atomic(LIVE, live_all, indent=None)
    print(f"✅ полных карточек: {len(done)}; влиты в concepts-live.json")
    return 0


LEGACY_CHARS = 560      # ≈ медиана полной карточки (515), с запасом на границу фразы


def legacy_texts():
    """Полный текст СТАРЫХ понятий — из английских витрин, где он и лежит.

    527 понятий (accretion_disk, active_galactic_nuclei, adscft_correspondence…) пришли
    из прежних справочников тегов и законов. Развёрнутое описание у них написано давно,
    но живёт в lang/en/data/*.json, а не в concept-fullcards.json, — и поэтому в вектор
    не входило никогда. Берём английские витрины, а не русские: пространство построено
    на английском, и подмешать русский текст значило бы испортить меру сходства.
    """
    out = {}
    for fname in ("tags.json", "laws.json"):
        fp = ROOT / "lang" / "en" / "data" / fname
        if not fp.exists():
            continue
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for cid_, v in d.items():
            if not isinstance(v, dict):
                continue
            body = (v.get("description_popular") or "").strip()
            # ДЛИНУ РАВНЯЕМ НА КАРТОЧКУ. Замер 08.09: у карточек медиана 515 знаков, у
            # витрин 790 — они писались читателю, а не индексу. Первый заход брал текст
            # витрины целиком и даже приклеивал «как работает»: вектор старых понятий
            # становился длиннее и «центральнее» остальных, и разметка поехала не по
            # смыслу, а по жанру — 71% статей, с явными потерями (quantum_entanglement
            # снимался со статьи про запутывание). Берём только начало описания, где
            # стоит определение, и режем по границе предложения.
            if len(body) > LEGACY_CHARS:
                cut = body[:LEGACY_CHARS]
                dot = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
                body = cut[:dot + 1] if dot > LEGACY_CHARS // 2 else cut
            if body:
                out.setdefault(cid_, body.strip())
    return out


def revector(everyone=False):
    """Вектор — от полного текста. Матрица правится на месте, бэкап рядом.

    По умолчанию пересчитываются понятия с полной карточкой. С everyone=True к ним
    добавляются старые, чей текст лежит в английских витринах: тогда ВЕСЬ реестр стоит
    на одной опоре. Раньше этого не делали намеренно — «менять им опору значило бы
    сдвинуть всю разметку разом», — и сдвиг действительно происходит: разметка после
    этого пересобирается заново (retag_hub.py) и её надо смотреть числами, а не на веру.
    """
    import numpy as np
    done = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    if not done:
        print("полных карточек нет — нечего перевекторизовать")
        return 1
    ids_p = ML / "data" / "concept-cards.ids"
    vec_p = ML / "data" / "concept-cards.f16"
    cids = ids_p.read_text(encoding="utf-8").splitlines()
    V = np.fromfile(vec_p, dtype=np.float16).reshape(len(cids), -1)
    bak = vec_p.with_suffix(".f16.bak")
    if not bak.exists():
        V.tofile(bak)
        print(f"бэкап матрицы: {bak.name}")
    legacy = legacy_texts() if everyone else {}
    src = {}
    for cid in cids:
        if cid in done:
            src[cid] = done[cid].get("description_popular") or ""
        elif cid in legacy:
            src[cid] = legacy[cid]
    rows = [(i, cid) for i, cid in enumerate(cids) if src.get(cid)]
    n_leg = sum(1 for _, cid in rows if cid not in done)
    print(f"пересчитываю {len(rows)} векторов от полного текста"
          + (f" (из них {n_leg} старых — по тексту витрин)" if n_leg else "") + "…")
    texts = [f"{cid.replace('_', ' ')}: {src[cid][:1500]}" for _, cid in rows]
    vecs = embed(texts)
    for (i, _), v in zip(rows, vecs):
        a = np.asarray(v, dtype=np.float32)
        V[i] = (a / (np.linalg.norm(a) + 1e-9)).astype(np.float16)
    V.tofile(vec_p)
    print(f"✅ матрица обновлена ({len(rows)} строк). Дальше:")
    print("   python tools/retag_hub.py --thr 0.50 --margin 0.12   (переразметка)")
    print("   python tools/wave5_apply.py --apply                  (в статьи)")
    print("   python tools/concepts_to_vectorize.py --apply        (в облако)")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Полные карточки понятий")
    ap.add_argument("--sample", type=int, metavar="N", help="N образцов на просмотр")
    ap.add_argument("--run", action="store_true", help="все, только в дешёвое окно")
    ap.add_argument("--force-peak", action="store_true")
    ap.add_argument("--with-legacy", action="store_true", dest="with_legacy",
                    help="писать карточки и старым понятиям, у которых текст есть в "
                         "справочнике: их вектор считается по однострочнику")
    ap.add_argument("--revector-all", action="store_true",
                    dest="revector_all",
                    help="вектор ВСЕХ понятий: у старых — по тексту английских витрин")
    ap.add_argument("--revector", action="store_true")
    a = ap.parse_args()
    if a.revector_all:
        return revector(everyone=True)
    if a.revector:
        return revector()
    if a.sample:
        return write_cards(limit=a.sample, force_peak=True)
    if a.run:
        return write_cards(force_peak=a.force_peak, with_legacy=a.with_legacy)
    todo, done, _ = targets()
    print(f"без полной карточки: {len(todo)} · готово: {len(done)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
