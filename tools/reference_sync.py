"""Досыпает в справочник формул те параграфы курса, которых в нём ещё нет.

Справочник `data/theory/reference.json` — это витрина формул курса: у каждого параграфа своя
карточка (название закона, формула, кто и когда, обозначения). Собиралась она руками, поэтому
отставала: темы «Теоретическая механика» и «Космология» появились позже, и их формул в
справочнике не было — 42 карточки против 48 параграфов.

Писать карточки заново незачем: всё нужное уже лежит в самих уроках (блок `formula` на пяти
языках) и в их `entities` (теги и законы). Инструмент просто переносит это в справочник —
и делает это для ЛЮБОГО нового параграфа, так что следующая тема встанет в справочник одной
командой, а не «когда вспомним».

    python tools/reference_sync.py --check   чего не хватает
    python tools/reference_sync.py           досыпать
"""
import json
import sys
from pathlib import Path

COURSES = Path("data/theory/courses")
REF = Path("data/theory/reference.json")
LANGS = ("ru", "en", "es", "ar", "fr")
# что переносим из блока formula урока в карточку справочника
FIELDS = ("name", "latex", "alsoKnown", "authors", "symbols")


def lessons():
    out = []
    for f in sorted(COURSES.glob("*/[0-9]*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out.append((f.parent.name, d))
    return out


def main():
    check = "--check" in sys.argv
    ref = json.loads(REF.read_text(encoding="utf-8"))
    have = {(x["topic"], x["lesson"]) for x in ref["formulas"]}
    added = []

    for topic, d in lessons():
        key = (topic, d["id"])
        if key in have:
            continue
        ru = d.get("ru") or {}
        if not ru.get("formula"):
            print("  ⚠️ %s/%s: нет блока formula — пропуск" % key)
            continue
        ent = d.get("entities") or {}
        card = {
            "topic": topic,
            "lesson": d["id"],
            "model": d.get("model", ""),
            "tags": list(ent.get("tags") or []),
            "laws": list(ent.get("laws") or []),
        }
        for lang in LANGS:
            br = d.get(lang)
            if not br or not br.get("formula"):
                continue
            src = br["formula"]
            card[lang] = {k: src[k] for k in FIELDS if k in src}
            card[lang]["title"] = br.get("title", "")
        ref["formulas"].append(card)
        added.append("%s/%s — %s" % (topic, d["id"], ru["formula"]["name"]))

    print("карточек в справочнике: %d | добавлено: %d" % (len(ref["formulas"]), len(added)))
    for a in added:
        print("  +", a)
    if added and not check:
        # порядок карточек — как в дереве: сначала тема, потом номер параграфа
        ref["formulas"].sort(key=lambda x: (x["topic"], x["lesson"]))
        REF.write_text(json.dumps(ref, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("записано")
    return 0


if __name__ == "__main__":
    sys.exit(main())
