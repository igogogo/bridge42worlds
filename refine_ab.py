"""Сравнение «до/после шлифовки» числом, а не впечатлением.

Решение о включении REFINE принимается по этому отчёту. Впечатление «стало живее»
невоспроизводимо и через неделю не проверяется; здесь — оси, которые прямо следуют
из запретов в article-refine-simple.txt / article-refine-popular.txt.

Что меряем (каждая ось — это чей-то явный запрет в промпте шлифовки):

    метафора      — заменена ли центральная метафора (запрещено: она общая с другим уровнем)
    факты         — появились ли числа, которых не было во входном тексте (запрещено: выдумывание)
    плотность     — стало ли больше терминов/чисел (запрещено: уплотнение)
    объём         — насколько изменилась длина (сокращать смысл нельзя)
    стиль         — нарушения _style-core: обращения к читателю, усилители
    маркеры       — совпадает ли состав [tag:]/[scientist:] (иначе рвутся связи)

Вход — папка с парами файлов <id>.before.json и <id>.after.json (по одному уровню статьи).
Такую пару даёт пробный прогон с REFINE=1: до шлифовки и после.

    python refine_ab.py --dir прогон-refine/

Ничего не запускает и не тратит вызовов модели: только читает готовые пары.
"""
import argparse
import json
import re
from pathlib import Path

MARKER = re.compile(r"\[(tag|scientist|law):([^\]]+)\]")
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
ADDRESS = re.compile(r"\b(представьте|вообразите|подумайте только|заметьте|согласитесь)\b", re.I)
FILLER = re.compile(r"\b(поистине|невероятн\w*|уникальн\w*|революционн\w*|прорывн\w*)\b", re.I)
TEXT_FIELDS = ("text", "title", "oneliner", "description", "fun_fact")


def plain(scipop):
    parts = [str(scipop.get(f, "")) for f in TEXT_FIELDS]
    return MARKER.sub("", " ".join(parts))


def compare(before, after):
    b, a = plain(before), plain(after)
    b_num, a_num = set(NUMBER.findall(b)), set(NUMBER.findall(a))
    b_mark = sorted(m.group(0) for m in MARKER.finditer(json.dumps(before, ensure_ascii=False)))
    a_mark = sorted(m.group(0) for m in MARKER.finditer(json.dumps(after, ensure_ascii=False)))
    return {
        "метафора_заменена": bool(before.get("metaphor")) and before.get("metaphor") != after.get("metaphor"),
        "новые_числа": sorted(a_num - b_num),
        "чисел_было": len(b_num),
        "чисел_стало": len(a_num),
        "длина_до": len(b),
        "длина_после": len(a),
        "стиль_до": len(ADDRESS.findall(b)) + len(FILLER.findall(b)),
        "стиль_после": len(ADDRESS.findall(a)) + len(FILLER.findall(a)),
        "маркеры_совпали": b_mark == a_mark,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="папка с парами <id>.before.json / <id>.after.json")
    ap.add_argument("--list", action="store_true", help="построчно по каждой статье")
    args = ap.parse_args()

    root = Path(args.dir)
    pairs = sorted(root.glob("*.before.json"))
    if not pairs:
        print(f"в {root} нет пар *.before.json — нечего сравнивать")
        return

    rows = []
    for before_path in pairs:
        after_path = before_path.with_name(before_path.name.replace(".before.", ".after."))
        if not after_path.exists():
            print(f"  ⚠️ нет пары для {before_path.name}")
            continue
        before = json.loads(before_path.read_text(encoding="utf-8"))
        after = json.loads(after_path.read_text(encoding="utf-8"))
        # id статьи сам содержит точку (2607.19705v1) — режем по суффиксу, а не по первой точке
        rows.append((before_path.name[:-len(".before.json")], compare(before, after)))

    if not rows:
        return
    n = len(rows)
    broke_metaphor = sum(1 for _, r in rows if r["метафора_заменена"])
    invented = [(i, r["новые_числа"]) for i, r in rows if r["новые_числа"]]
    denser = sum(1 for _, r in rows if r["чисел_стало"] > r["чисел_было"])
    lost_markers = sum(1 for _, r in rows if not r["маркеры_совпали"])
    style_before = sum(r["стиль_до"] for _, r in rows)
    style_after = sum(r["стиль_после"] for _, r in rows)
    length = sum(r["длина_после"] for _, r in rows) / max(1, sum(r["длина_до"] for _, r in rows))

    print(f"пар сравнено: {n}\n")
    print(f"  метафора заменена:      {broke_metaphor} из {n}   (запрещено промптом)")
    print(f"  выдуманы числа:         {len(invented)} из {n}   (запрещено промптом)")
    print(f"  текст уплотнён:         {denser} из {n}   (запрещено промптом)")
    print(f"  маркеры разъехались:    {lost_markers} из {n}   (рвутся связи тег/учёный)")
    print(f"  нарушений стиля:        было {style_before} → стало {style_after}")
    print(f"  объём:                  {length:.0%} от исходного")
    print()
    verdict_ok = (broke_metaphor == 0 and not invented and lost_markers == 0
                  and style_after <= style_before and 0.9 <= length <= 1.25)
    print("ВЕРДИКТ: шлифовку можно включать" if verdict_ok else
          "ВЕРДИКТ: включать нельзя — сначала поправить промпт по нарушенным осям")
    if invented:
        print("\nвыдуманные числа (первые 5 статей):")
        for article_id, numbers in invented[:5]:
            print(f"  {article_id}: {', '.join(numbers[:8])}")
    if args.list:
        print()
        for article_id, r in rows:
            print(f"  {article_id}: метафора {'СМЕНЕНА' if r['метафора_заменена'] else 'ок'}, "
                  f"числа {r['чисел_было']}→{r['чисел_стало']}, "
                  f"стиль {r['стиль_до']}→{r['стиль_после']}, "
                  f"объём {r['длина_после'] / max(1, r['длина_до']):.0%}")


if __name__ == "__main__":
    main()
