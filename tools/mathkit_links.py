"""Собирает обратные ссылки матсправочника: какая карточка в каких параграфах работает.

В карточке было поле `where` — строка вроде «Работа и энергия, теплота в термодинамике».
Читать приятно, пойти некуда: мёртвый текст. Теперь рядом появляется список настоящих
ссылок, и собирается он не руками, а из самих врезок: во врезке параграфа стоит `kit`
с ключом карточки — это и есть связь, объявленная автором материала.

Плюс такого способа: связь не может разойтись с текстом. Убрали врезку — ссылка исчезла
сама; добавили новую тему — она появилась после прогона, без правки справочника руками.

    python tools/mathkit_links.py --check   что получится
    python tools/mathkit_links.py           записать в data/theory/mathkit.json
"""
import json
import io
import sys
from pathlib import Path

COURSES = Path("data/theory/courses")
KIT = Path("data/theory/mathkit.json")


def collect():
    used = {}
    for f in sorted(COURSES.glob("*/[0-9]*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        ru = d.get("ru") or {}
        for it in ((ru.get("math") or {}).get("items") or []):
            key = it.get("kit")
            if not key:
                continue
            used.setdefault(key, []).append({
                "topic": f.parent.name,
                "lesson": d["id"],
                "title": ru.get("title", d["id"]),
            })
    return used


def main():
    check = "--check" in sys.argv
    used = collect()
    kit = json.loads(KIT.read_text(encoding="utf-8"))
    known = {x["id"] for x in kit["items"]}
    unknown = sorted(set(used) - known)
    if unknown:
        print("⚠️ во врезках есть ссылки на несуществующие карточки: " + ", ".join(unknown))

    total = 0
    for card in kit["items"]:
        links = used.get(card["id"], [])
        total += len(links)
        if links:
            card["usedIn"] = links
        else:
            card.pop("usedIn", None)
    print("карточек: %d | из них с живыми ссылками: %d | всего ссылок: %d"
          % (len(kit["items"]), sum(1 for c in kit["items"] if c.get("usedIn")), total))
    if check:
        for c in kit["items"]:
            if c.get("usedIn"):
                print("  %-14s ← %s" % (c["id"], ", ".join(u["topic"] + "/" + u["lesson"] for u in c["usedIn"][:4])))
        return 1 if unknown else 0
    io.open(KIT, "w", encoding="utf-8").write(json.dumps(kit, ensure_ascii=False, indent=1) + "\n")
    print("записано")
    return 1 if unknown else 0


if __name__ == "__main__":
    sys.exit(main())
