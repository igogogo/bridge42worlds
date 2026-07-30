"""Вливает затравку доменных тегов (data/tag-seeds.json) в активный словарь.

Зачем отдельным шагом. Словарь тегов ЗАКРЫТЫЙ: статья выбирает только из того, что
пришло в промпт. Пока в словаре нет ни одного тега информатики, статья по cs.LG будет
размечена физическими тегами — и это не лечится ни промптом, ни моделью.

Догенерация моделью (`tag_list.py --grow`) для пустого домена работает плохо: она
предлагает то, что видит в корпусе, а корпус физический. Костяк новой области дешевле
и точнее написать руками — этим и занят data/tag-seeds.json.

Скрипт детерминированный, вызовов модели нет. Дубли отсеиваются и по en-идентификатору,
и по русскому названию (в словаре уже есть, например, dimensionality_reduction).

    python tag_seeds_merge.py --dry     # показать, что добавится
    python tag_seeds_merge.py           # влить

ВНИМАНИЕ: пишет в lang/ru/data/tags-list.json — это данные генератора. После вливания
нужны карточки новых тегов (`run.py tags describe`) и пересборка — это уже платный
прогон и решение ведущей сессии.
"""
import json
import sys
from pathlib import Path

SEEDS = Path("data/tag-seeds.json")
ACTIVE = Path("lang/ru/data/tags-list.json")
DRY = "--dry" in sys.argv


def main():
    if not SEEDS.exists():
        print(f"нет {SEEDS}")
        return
    if not ACTIVE.exists():
        print(f"нет {ACTIVE} — запускать из корня проекта")
        return

    seeds = json.loads(SEEDS.read_text(encoding="utf-8"))
    active = json.loads(ACTIVE.read_text(encoding="utf-8"))
    known_en = {t.get("en") for t in active}
    known_ru = {(t.get("ru") or "").strip().lower() for t in active}

    added, skipped = [], []
    for domain, items in seeds.items():
        if domain.startswith("_"):
            continue
        for item in items:
            if item["en"] in known_en or item["ru"].strip().lower() in known_ru:
                skipped.append((domain, item["en"]))
                continue
            record = {"ru": item["ru"], "en": item["en"], "type": item["type"], "domain": domain}
            added.append(record)
            known_en.add(item["en"])
            known_ru.add(item["ru"].strip().lower())

    by_domain = {}
    for record in added:
        by_domain[record["domain"]] = by_domain.get(record["domain"], 0) + 1
    print(f"словарь: {len(active)} тегов, затравка добавит {len(added)}, дублей пропущено {len(skipped)}")
    for domain, count in sorted(by_domain.items()):
        print(f"  +{count:>3}  {domain}")
    if skipped:
        print("  дубли: " + ", ".join(en for _, en in skipped[:10])
              + (" …" if len(skipped) > 10 else ""))

    if DRY:
        print("\n--dry: ничего не записано")
        return
    ACTIVE.write_text(json.dumps(active + added, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ {ACTIVE}: стало {len(active) + len(added)} тегов")
    print("дальше: карточки новых тегов (run.py tags describe) и пересборка — ведущая сессия")


if __name__ == "__main__":
    main()
