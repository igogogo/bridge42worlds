# -*- coding: utf-8 -*-
"""Применение волны 5 к боевым данным: разметка v2 в статьи + живой справочник понятий.

Владелец 26 августа: «да, делай применение и вторую сборку». До этого предложение
лежало в шести файлах соседнего дерева; здесь оно становится данными сайта.

ДВА ПРОДУКТА:

1. В data.json каждой статьи пишется поле `concepts_v2` — разметка v2 (хабность,
   опора >= 5), во все уровни и языки: идентификаторы общие, язык — дело подписи.
   Старые tags_vec/laws_vec НЕ трогаются: страницы старых разделов продолжают
   работать, а генератор статьи сам решает, что рисовать (v2, если есть).

2. data/concepts-live.json — справочник для генератора страниц понятий: карточка,
   вид, группы, соседи по весу, учёные (НОВЫЕ, из concept-scientists — в v3 лежат
   старые списки, их не берём), формулы, переводы названий.

ПЕРЕВОДЫ НАЗВАНИЙ — ОТКУДА ЕСТЬ. У 527 понятий, переживших волну, названия уже
переведены в старых справочниках (tags.json / laws.json по языкам) — забираем их.
У новых ~686 перевода нет: название остаётся английским до прогона перевода.
Разметка от этого не страдает — идентификаторы языка не имеют.

ОТКАТ: --restore удаляет поле concepts_v2 из статей и справочник. Прочее не трогалось.

    python tools/wave5_apply.py            сверка: что будет сделано
    python tools/wave5_apply.py --apply    применить
    python tools/wave5_apply.py --restore  откатить
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT.parent / "b42-ml"
RETAG = ROOT / "data" / "articles-retag-v2.json"
LIVE = ROOT / "data" / "concepts-live.json"
LANGS = ("ru", "en", "es", "ar", "fr")
TIERS = ("simple", "popular", "advanced")


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def old_names():
    """Переводы названий из старых справочников — по языкам, где понятие жило раньше."""
    names = defaultdict(dict)   # id → {lang: name}
    for lang in LANGS:
        for fname in ("tags.json", "laws.json"):
            p = ROOT / "lang" / lang / "data" / fname
            if not p.exists():
                continue
            try:
                d = load(p)
            except Exception:
                continue
            for cid, v in d.items():
                if isinstance(v, dict) and v.get("name"):
                    names[cid].setdefault(lang, v["name"])
    return names


def build_live():
    v3 = load(ML / "data" / "concepts-v3.json")["concepts"]
    # Рождённые живым циклом (data/concepts-grown.json) — полноправные члены реестра:
    # без этого ночная добыча рожает понятия, а справочник их не видит — статьи
    # размечены, страниц нет, ссылки в пустоту.
    grown_p = ROOT / "data" / "concepts-grown.json"
    if grown_p.exists():
        for cid, g in load(grown_p).items():
            v3.setdefault(cid, {
                "kind": g.get("kind") or "concept",
                "card_en": g.get("card_en") or "",
                "origin": g.get("origin") or "live-harvest",
                "aliases": g.get("aliases") or [],
                "related": [], "scientists": [], "article_count": 0,
            })
    sup = load(ML / "data" / "concepts-super.json")
    sci = load(ML / "data" / "concept-scientists.json")["concepts"]
    bases = load(ML / "data" / "formulas-linked.json")["bases"]
    retag = load(RETAG)["articles"]

    # соседи по весу — из взвешенных связей
    nb = defaultdict(list)
    for e in sup["links"]:
        nb[e["a"]].append((e["b"], e["w"]))
        nb[e["b"]].append((e["a"], e["w"]))
    for k in nb:
        nb[k].sort(key=lambda t: -t[1])

    # формулы к понятию: форма целиком, включая применения — страница понятия
    # показывает оба яруса
    fml = defaultdict(list)
    for b in bases:
        for i, c in enumerate(b.get("concepts") or []):
            fml[c["concept"]].append({
                "id": b["base_id"], "name": b.get("name") or b["base_id"],
                "latex": b.get("latex", ""), "card": b.get("card", ""),
                "rank": i,
                "apps": [{"art": (a.get("article") or a.get("art") or ""),
                          "latex": (a.get("record") or "")[:160]}
                         for a in (b.get("applications") or [])[:8]],
            })
    for k in fml:
        fml[k].sort(key=lambda f: f["rank"])

    # опора по разметке v2 — сколько статей у понятия на самом деле
    support = defaultdict(list)
    for aid, cs_ in retag.items():
        for cid in cs_:
            support[cid].append(aid)

    names = old_names()
    membership = sup["membership"]
    groups = {int(k): v for k, v in sup["groups"].items()}

    out = {}
    for cid, v in v3.items():
        out[cid] = {
            "card_en": v.get("card_en", ""),
            "kind": v.get("kind") or "concept",
            "origin": v.get("origin") or "",
            "names": names.get(cid, {}),          # {lang: название}, где есть
            "supers": membership.get(cid, []),
            "related": [{"id": a, "w": round(w, 3)} for a, w in nb.get(cid, [])[:10]],
            # учёные — ТОЛЬКО новые: в v3 старые свалки, их не переносим
            "scientists": [{"name": s["name"], "n": s.get("articles", 0)}
                           for s in (sci.get(cid) or [])[:6]],
            "formulas": fml.get(cid, [])[:6],
            "articles": support.get(cid, []),
            "aliases": v.get("aliases") or [],
        }

    # ПОБОЧНЫЕ ХРАНИЛИЩА — вливаются при КАЖДОЙ сборке live, иначе apply,
    # переписывая live с нуля, терял бы полные записи (баг 27.08: fullcards в
    # ночной цепочке идёт до apply — full исчезал из live к моменту pages).
    # Каждое знание живёт в своём файле-хранилище; live — всегда производная.
    fc = ROOT / "data" / "concept-fullcards.json"
    if fc.exists():
        for cid, rec in load(fc).items():
            if cid in out:
                out[cid]["full"] = rec
    fci = ROOT / "data" / "concept-fullcards-i18n.json"
    if fci.exists():
        for cid, byl in load(fci).items():
            if cid in out and isinstance(byl, dict):
                out[cid]["full_i18n"] = byl
    usl = ROOT / "data" / "unit-systems-links.json"
    if usl.exists():
        for cid, rec in load(usl).items():
            if cid in out and isinstance(rec, dict):
                out[cid].update({k: v for k, v in rec.items()
                                 if k in ("systems", "si_definition",
                                          "units_by_system")})
    # имена, приехавшие с рождением (сид систем единиц кладёт en-название)
    if grown_p.exists():
        for cid, g in load(grown_p).items():
            for l, nm in (g.get("names") or {}).items():
                if cid in out:
                    out[cid]["names"].setdefault(l, nm)
    meta = {
        "built": load(ML / "data" / "concepts-super.json").get("built", ""),
        "groups": {str(g): m for g, m in groups.items()},
        "concepts": out,
    }
    return meta, retag


def apply_articles(retag, dry):
    """concepts_v2 → data.json. Во все уровни и языки, как пишет tag_by_vector."""
    n = 0
    for p in sorted((ROOT / "lang" / "ru" / "archive").glob("*/*/data.json")):
        aid = p.parent.name
        cs_ = retag.get(aid)
        if cs_ is None:
            bare = aid.split("v")[0]
            cs_ = retag.get(bare)
        if cs_ is None:
            continue
        d = load(p)
        changed = False
        for tier in TIERS:
            for lang in LANGS:
                v = (d.get(tier, {}) or {}).get(lang)
                if isinstance(v, dict) and v.get("concepts_v2") != cs_:
                    v["concepts_v2"] = cs_
                    changed = True
        if changed and not dry:
            p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        n += changed
    return n


def restore():
    n = 0
    for p in sorted((ROOT / "lang" / "ru" / "archive").glob("*/*/data.json")):
        d = load(p)
        changed = False
        for tier in TIERS:
            for lang in LANGS:
                v = (d.get(tier, {}) or {}).get(lang)
                if isinstance(v, dict) and "concepts_v2" in v:
                    del v["concepts_v2"]
                    changed = True
        if changed:
            p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            n += 1
    if LIVE.exists():
        LIVE.unlink()
    print(f"откат: очищено статей {n}, справочник удалён")


def main():
    ap = argparse.ArgumentParser(description="Применение волны 5 к боевым данным")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--restore", action="store_true")
    a = ap.parse_args()
    if a.restore:
        restore()
        return 0

    live, retag = build_live()
    c = live["concepts"]
    with_name_ru = sum(1 for v in c.values() if v["names"].get("ru"))
    with_sci = sum(1 for v in c.values() if v["scientists"])
    with_fml = sum(1 for v in c.values() if v["formulas"])
    print(f"справочник: {len(c)} понятий · русское название у {with_name_ru} · "
          f"учёные у {with_sci} · формулы у {with_fml}")

    n = apply_articles(retag, dry=not a.apply)
    if a.apply:
        LIVE.write_text(json.dumps(live, ensure_ascii=False), encoding="utf-8")
        print(f"→ {LIVE.relative_to(ROOT)} ({LIVE.stat().st_size // 1024} КБ)")
        print(f"разметка v2 записана в {n} статей")
    else:
        print(f"будет записано в {n} статей; --apply применит")
    return 0


if __name__ == "__main__":
    sys.exit(main())
