# -*- coding: utf-8 -*-
"""Русские версии карточек знаний (владелец 27.08: «поблажка — пока на двух языках,
русский и английский; остальные потом дотянем»).

ДВА ФРОНТА, один инструмент:

  --concepts   полные записи понятий (full: описание/история/как работает/
               практика/факт + card_en-эпиграф) → full_i18n.ru прямо в live.
               Переводим и СТАРЫЕ понятия без full: у них русский уже есть в
               rich-справочниках (tags.json/laws.json) — их не трогаем.
  --formulas   анатомии формул (description/history/applicability + m-поля
               переменных/констант/операторов + unit_systems notes) →
               блок "ru" внутри записи анатомии.

Инкрементально: сделанное не повторяется (признак — наличие ru-блока).
Дешёвое окно DeepSeek уважается; --force-peak обходит. Смета: ~700 понятий
× ~600 ток + 642 анатомии × ~500 ток ≈ $1-2 в дешёвое окно.

    python tools/cards_translate_ru.py --concepts [--force-peak]
    python tools/cards_translate_ru.py --formulas [--force-peak]
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.concept_harvest import env  # noqa: E402
from tools.concept_fullcards import cheap_window  # noqa: E402
from common import CONFIG  # noqa: E402, write_json_atomic

# Потоки берём из той же настройки, что описание тегов, но не больше восьми: там
# в одном запросе двадцать тегов, здесь — одна карточка, и пятнадцать мелких
# запросов разом дают лишний риск отказа ради выигрыша, которого уже не видно.
WORKERS = min(CONFIG.get("tags", {}).get("workers", 5), 8)

LIVE = ROOT / "data" / "concepts-live.json"
ANAT = ROOT / "data" / "formula-anatomy.json"
# Хранилище переводов — отдельный файл: live переписывается apply с нуля,
# build_live (wave5_apply) вливает это хранилище при каждой сборке.
I18N = ROOT / "data" / "concept-fullcards-i18n.json"

SYS_T = """You are a translator for a Russian popular-science knowledge base.

Translate the given JSON values from English to Russian. Return the SAME JSON
structure with every string value translated. Rules:
1. Natural literate Russian, popular-science register («чуть сильнее популярного»).
2. Keep LaTeX, formulas, numbers, unit symbols and proper names of instruments
   (Fermi-LAT, LIGO) as they are; translate unit names (kilogram → килограмм).
3. Scientist names → accepted Russian spelling (Einstein → Эйнштейн).
4. Terminology must match Russian physics usage (momentum → импульс, NOT момент).
5. Do not let the Russian sentence repeat one root twice where the English did not:
   «квантово-механическое квантование» says one word twice. If a literal rendering
   produces such an echo, choose a synonym — the meaning matters, not the mirror.
6. Output ONLY the JSON, no commentary."""


def ask(payload, key, max_tokens=3000):
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": SYS_T},
                     {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        "temperature": 0.2, "max_tokens": max_tokens,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read().decode("utf-8"))
    raw = d["choices"][0]["message"]["content"]
    m = re.search(r"[{\[].*[}\]]", raw, re.S)
    return json.loads(m.group(0)) if m else None


def gate(force_peak):
    if not cheap_window() and not force_peak:
        print("ПИКОВЫЙ тариф DeepSeek — дешёвое окно 19:30–03:30 Кувейта; --force-peak обойдёт.")
        return False
    return True


def concepts(force_peak=False):
    if not gate(force_peak):
        return 1
    key = env("DEEPSEEK_API_KEY")
    doc = json.loads(LIVE.read_text(encoding="utf-8"))
    lc = doc["concepts"]
    store = json.loads(I18N.read_text(encoding="utf-8")) if I18N.exists() else {}
    # Полные записи — и отдельно короткие карточки без полной записи. Вторых
    # оказалось 415, и среди них энтропия: у понятия есть старое описание из
    # справочника, но нет поля full, поэтому переводчик его не видел — и русская
    # страница встречала читателя английским определением-эпиграфом.
    todo = [cid for cid, v in lc.items()
            if not v.get("merged_into") and v.get("full")
            and "ru" not in (store.get(cid) or {})]
    card_only = [cid for cid, v in lc.items()
                 if not v.get("merged_into") and not v.get("full")
                 and (v.get("card_en") or "").strip()
                 and not ((v.get("full_i18n") or {}).get("ru") or {}).get("card")]
    print(f"понятий с full без ru: {len(todo)} · только карточка без ru: {len(card_only)}")

    def one(cid):
        """Одна карточка. Ошибка не валит прогон — вернём None и пойдём дальше."""
        v = lc[cid]
        src = {k: v["full"].get(k, "") for k in
               ("description_popular", "history", "how_it_works",
                "practical_application", "fun_fact_popular")}
        src["card"] = v.get("card_en") or ""
        try:
            got = ask(src, key)
        except Exception as e:
            print(f"  сбой {cid}: {e}")
            return cid, None
        if not isinstance(got, dict) or not got.get("description_popular"):
            print(f"  пустой ответ {cid}")
            return cid, None
        return cid, {k: str(got.get(k, ""))[:4000] for k in src}

    # Пять потоков — столько же, сколько у описания тегов (config: tags.workers),
    # то есть проверенная доза для DeepSeek. Последовательно 2293 карточки шли бы
    # почти четыре часа: по шесть секунд на карточку, и всё это время впустую
    # ждётся ответ. Пишем в хранилище из ГЛАВНОГО потока, по мере готовности.
    n_done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for cid, ru in ex.map(one, todo):
            if not ru:
                continue
            store.setdefault(cid, {})["ru"] = ru
            n_done += 1
            if n_done % 25 == 0:
                I18N.write_text(json.dumps(store, ensure_ascii=False, indent=1),
                                encoding="utf-8")
                print(f"  переведено {n_done}/{len(todo)}", flush=True)
    I18N.write_text(json.dumps(store, ensure_ascii=False, indent=1),
                    encoding="utf-8")

    # Короткие карточки — отдельным заходом: у них нет полной записи, переводить
    # нужно одну строку, и просить за неё пять полей значило бы выдумывать текст.
    def one_card(cid):
        try:
            got = ask({"card": lc[cid].get("card_en") or ""}, key)
        except Exception as e:
            print(f"  сбой карточки {cid}: {e}")
            return cid, None
        c = (got or {}).get("card") if isinstance(got, dict) else None
        return cid, (str(c)[:1000] if c else None)

    n_card = 0
    if card_only:
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for cid, ru_card in ex.map(one_card, card_only):
                if not ru_card:
                    continue
                lc[cid].setdefault("full_i18n", {}).setdefault("ru", {})["card"] = ru_card
                n_card += 1
                if n_card % 50 == 0:
                    print(f"  карточек переведено {n_card}/{len(card_only)}", flush=True)
        print(f"✅ коротких карточек на русском: +{n_card}")

    # и в текущий live — чтобы страницы можно было гнать сразу, не дожидаясь apply
    for cid, byl in store.items():
        if cid not in lc:
            continue
        # Сливаем, а не заменяем: в full_i18n уже могут лежать короткие карточки,
        # переведённые заходом выше, и целая подстановка стёрла бы их.
        cur = lc[cid].get("full_i18n") or {}
        for lng, val in byl.items():
            if isinstance(val, dict) and isinstance(cur.get(lng), dict):
                cur[lng] = {**cur[lng], **val}
            else:
                cur[lng] = val
        lc[cid]["full_i18n"] = cur
    write_json_atomic(LIVE, doc, indent=None)
    print(f"✅ русских карточек понятий: +{n_done} (хранилище {I18N.name})")
    return 0


def formulas(force_peak=False):
    if not gate(force_peak):
        return 1
    if not ANAT.exists():
        print("анатомий нет — сначала formula_anatomy --run")
        return 1
    key = env("DEEPSEEK_API_KEY")
    done = json.loads(ANAT.read_text(encoding="utf-8"))
    # карточки форм (эпиграф) — из formulas-linked, переводим заодно
    try:
        _bases = {b["base_id"]: b.get("card", "") for b in json.loads(
            (ROOT.parent / "b42-ml" / "data" / "formulas-linked.json")
            .read_text(encoding="utf-8"))["bases"]}
    except Exception:
        _bases = {}
    todo = [bid for bid, rec in done.items() if "ru" not in rec]
    print(f"анатомий без ru: {len(todo)}")
    def one(bid):
        rec = done[bid]
        src = {
            "description": rec.get("description", ""),
            "history": rec.get("history", ""),
            "applicability": rec.get("applicability", ""),
            "card": _bases.get(bid, ""),
            "variables": [v.get("m", "") for v in rec.get("variables") or []],
            "constants": [c.get("m", "") for c in rec.get("constants") or []],
            "operators": [o.get("m", "") for o in rec.get("operators") or []],
            "system_notes": [u.get("note", "") for u in rec.get("unit_systems") or []],
        }
        try:
            got = ask(src, key)
        except Exception as e:
            print(f"  сбой {bid}: {e}")
            return bid, None
        if not isinstance(got, dict) or not got.get("description"):
            print(f"  пустой ответ {bid}")
            return bid, None

        def lst(k, n):
            v = got.get(k) or []
            return [str(x)[:300] for x in v][:n] if isinstance(v, list) else []
        return bid, {
            "description": str(got.get("description", ""))[:1500],
            "history": str(got.get("history", ""))[:800],
            "applicability": str(got.get("applicability", ""))[:1000],
            "card": str(got.get("card", ""))[:600],
            "variables": lst("variables", len(src["variables"])),
            "constants": lst("constants", len(src["constants"])),
            "operators": lst("operators", len(src["operators"])),
            "system_notes": lst("system_notes", len(src["system_notes"])),
        }

    # Те же потоки, что и у карточек понятий: перевод — это ожидание ответа,
    # а не работа, и делать его последовательно значит просто дольше ждать.
    n_done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for bid, ru in ex.map(one, todo):
            if not ru:
                continue
            done[bid]["ru"] = ru
            n_done += 1
            if n_done % 25 == 0:
                ANAT.write_text(json.dumps(done, ensure_ascii=False, indent=1),
                                encoding="utf-8")
                print(f"  переведено {n_done}/{len(todo)}", flush=True)
    ANAT.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ русских анатомий: +{n_done}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Русские карточки понятий и формул")
    ap.add_argument("--concepts", action="store_true")
    ap.add_argument("--formulas", action="store_true")
    ap.add_argument("--force-peak", action="store_true")
    a = ap.parse_args()
    if a.concepts:
        return concepts(force_peak=a.force_peak)
    if a.formulas:
        return formulas(force_peak=a.force_peak)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
