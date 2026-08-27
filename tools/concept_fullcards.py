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
  --run        все понятия без полной карточки. ПРОВЕРЯЕТ ДЕШЁВОЕ ОКНО DeepSeek:
               скидка 50% действует 16:30–00:30 UTC (19:30–03:30 по Кувейту).
               Вне окна отказывается; --force-peak осознанно обходит.
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
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT.parent / "b42-ml"
OUT = ROOT / "data" / "concept-fullcards.json"
LIVE = ROOT / "data" / "concepts-live.json"

sys.path.insert(0, str(ROOT))
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
Output ONLY the JSON array."""


def cheap_window(now=None):
    """Дешёвое окно DeepSeek: 16:30-00:30 UTC, скидка 50%."""
    now = now or datetime.now(timezone.utc)
    m = now.hour * 60 + now.minute
    return m >= 16 * 60 + 30 or m < 30


def targets():
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
        if cid in done:
            continue
        if cid in rich:
            continue   # старое понятие: развёрнутый текст уже лежит в справочнике
        titles = []
        for aid in c.get("articles", [])[:MAX_TITLES]:
            a = idx.get(aid) or idx.get(aid.split("v")[0])
            if a and a.get("title"):
                titles.append(a["title"])
        out.append((cid, c.get("card_en", ""), titles))
    return out, done, live


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
            rec = {
                # имена полей — ТЕ ЖЕ, что в старых справочниках: страница рисует
                # старые и новые записи одним кодом, без второй ветки
                "description_popular": str(it.get("description", "")).strip()[:4000],
                "how_it_works": str(it.get("how_it_works", "")).strip()[:2500],
                "history": str(it.get("history", "")).strip()[:1500],
                "practical_application": str(it.get("practical_application", "")).strip()[:600],
                "fun_fact_popular": str(it.get("fun_fact", "")).strip()[:400],
            }
            if len(rec["description_popular"]) > 200:
                out[batch[n - 1][0]] = rec
        except (KeyError, ValueError, TypeError):
            continue
    return out


def write_cards(limit=None, force_peak=False):
    try:
        from tools.freeze import guard
        guard("полные карточки понятий (DeepSeek)")
    except ImportError:
        pass
    if limit is None and not cheap_window() and not force_peak:
        now = datetime.now(timezone.utc)
        print(f"сейчас {now:%H:%M} UTC — ПИКОВЫЙ тариф DeepSeek.")
        print("дешёвое окно: 16:30–00:30 UTC (19:30–03:30 по Кувейту).")
        print("владелец просил не попадать в дорогой период; --force-peak обойдёт.")
        return 1
    key = env("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit("нет DEEPSEEK_API_KEY")
    todo, done, _ = targets()
    if limit:
        todo = todo[:limit]
    print(f"понятий без полной карточки: {len(todo)}")
    for s in range(0, len(todo), PER_CALL):
        batch = todo[s:s + PER_CALL]
        try:
            got = ask_batch(batch, key)
        except Exception as e:
            print(f"  сбой пачки {s}: {e} — пауза и дальше")
            time.sleep(5)
            continue
        done.update(got)
        OUT.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  {len(done)} готово (+{len(got)})")
    # вливаем в живой справочник — страницы возьмут при перегенерации
    live_all = json.loads(LIVE.read_text(encoding="utf-8"))
    for cid, rec in done.items():
        if cid in live_all["concepts"]:
            live_all["concepts"][cid]["full"] = rec
    LIVE.write_text(json.dumps(live_all, ensure_ascii=False), encoding="utf-8")
    print(f"✅ полных карточек: {len(done)}; влиты в concepts-live.json")
    return 0


def revector():
    """Вектор — от полного текста карточки. Матрица правится на месте, бэкап рядом.

    Пересчитываются ТОЛЬКО понятия с полной карточкой: у старых вектор остаётся
    от однострочника — их полный текст живёт в языковых витринах и в вектор не
    входил никогда; менять им опору сейчас значило бы сдвинуть всю разметку разом.
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
    rows = [(i, cid) for i, cid in enumerate(cids) if cid in done]
    print(f"пересчитываю {len(rows)} векторов от полного текста…")
    texts = [f"{cid.replace('_', ' ')}: {done[cid]['description_popular'][:1500]}"
             for _, cid in rows]
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
    ap.add_argument("--revector", action="store_true")
    a = ap.parse_args()
    if a.revector:
        return revector()
    if a.sample:
        return write_cards(limit=a.sample, force_peak=True)
    if a.run:
        return write_cards(force_peak=a.force_peak)
    todo, done, _ = targets()
    print(f"без полной карточки: {len(todo)} · готово: {len(done)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
