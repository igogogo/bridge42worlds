#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Связи уроков курса с нашим архивом — по смыслу, вектором.

ЗАЧЕМ. Курс отличается от учебника тем, что из параграфа видно живую науку: разобранные
нами работы по этой самой теме. Прежний подбор (`course_link.py`) делал это по СОВПАДЕНИЮ
ТЕГОВ, и получалось плохо: параграф «Молекулы и температура» вёл на «Тайный ветер нейтронных
звёзд» и «Квантовый маскарад на границе кварковых миров» — общими у них были только теги
`plasma` и `quantum_thermodynamics`. Тег слишком грубая мерка, чтобы на ней строить связь.

КАК ЗДЕСЬ. Сравниваются векторы:

    урок  →  ..\\b42-ml\\data\\lessons-en.f16   (считает ML, скрипт lessons_vectors.py)
    статья→  ..\\b42-ml\\data\\field.f16        (то же поле arXiv, что у остальных слоёв)

Одна модель (bge-m3), одна нормировка, одно правило сборки текста — иначе косинус считался
бы между несопоставимыми числами. Свои эмбеддинги здесь НЕ считаются намеренно: векторный
слой ведёт ML, и второй способ их получить означал бы тихо разъезжающиеся связи.

ПОЧЕМУ АНГЛИЙСКИЕ ВЕКТОРА УРОКОВ. Поле arXiv английское. Замер ML 24 августа на 105
материалах: top-1 косинус en 0,636 против ru 0,597, и ближайшая статья у русской и
английской версии совпадает лишь в 38% случаев. Кросс-языковой косинус систематически ниже,
и пороги с языка на язык не переносятся.

ПОРОГИ (замер ML, 24 августа; они ЖАНРОВЫЕ — урок и аннотация написаны по-разному, поэтому
потолок ниже, чем у пары статья-статья):
    > 0,68   уверенное попадание в предмет
    0,60-0,68  тема та же, угол другой — годится
    < 0,58   статей по этой теме у нас просто нет

Ниже порога ссылка НЕ ставится. Пустой блок честнее слабой ссылки: низкий косинус означает
дырку в нашем корпусе, а не плохую работу связывателя. Такие параграфы попадают в список
дыр (--gaps) — это готовая очередь на догенерацию статей.

    python tools/course_vector_links.py --dry              посмотреть, ничего не писать
    python tools/course_vector_links.py --dry --topic optics   одна тема, с числами
    python tools/course_vector_links.py                    записать связи в уроки
    python tools/course_vector_links.py --gaps data/theory/courses/_link-gaps.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT.parent / "b42-ml"
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

COURSES = ROOT / "data" / "theory" / "courses"
FIELD = ML / "data" / "field"           # field.f16 + field.ids
LESSONS = ML / "data" / "lessons-en"    # lessons-en.f16 + lessons-en.ids
DIM = 1024

# Порог годности ссылки и порог «у нас дырка» — оба из замера ML 24 августа (см. шапку).
MIN_LINK = 0.60
GAP_BELOW = 0.60
# Сколько ссылок показываем. У параграфа четыре — строка связей под текстом, больше
# в неё не помещается по ширине колонки. У обзорной главы пять: она про тему целиком.
TOP_LESSON = 4
TOP_TOPIC = 5

from common import ALL_LANGS  # noqa: E402
LANGS = ALL_LANGS   # список языков один на проект: config.json через common.ALL_LANGS


def our_articles():
    """Разобранные нами работы: базовый id → (id папки, дата, заголовки по языкам).

    Ключ базовый (без версии): в поле arXiv работа лежит под номером без «v2», а у нас
    папка может быть с версией.
    """
    out = {}
    for p in (ROOT / "lang/ru/archive").glob("*/*/data.json"):
        aid = p.parent.name
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue        # файл могут прямо сейчас переписывать — пропускаем, не падаем
        block = d.get("popular") or d.get("simple") or {}
        titles = {l: (block.get(l) or {}).get("title") for l in LANGS
                  if isinstance(block.get(l), dict) and (block.get(l) or {}).get("title")}
        if not titles:
            continue
        out[re.sub(r"v\d+$", "", aid)] = {
            "id": aid, "date": d.get("date") or p.parent.parent.name, "titles": titles}
    return out


def load_lessons():
    sys.path.insert(0, str(ML))
    import vecstore
    ids, m = vecstore.load(str(LESSONS), latest=True)
    return ids, m


def load_ours(base_ids):
    """Векторы наших статей — строками из общего поля arXiv, без пересчёта."""
    import numpy as np
    want = set(base_ids)
    rows, ids = [], []
    with (FIELD.with_suffix(".ids")).open(encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            s = line.strip()
            if s.startswith("arx:"):
                s = s[4:]
            if s in want:
                rows.append(i)
                ids.append(s)
    n_rows = FIELD.with_suffix(".f16").stat().st_size // (DIM * 2)
    m = np.memmap(FIELD.with_suffix(".f16"), dtype=np.float16, mode="r", shape=(n_rows, DIM))
    order = sorted(range(len(rows)), key=lambda k: rows[k])   # memmap любит возрастающий доступ
    take = [rows[k] for k in order]
    vecs = np.asarray(m[take], dtype=np.float32)
    return [ids[k] for k in order], vecs


def indent_of(text):
    """С каким отступом записан файл. Уроки лежат и с двумя пробелами, и с одним (следы
    разных прогонов). Пишем тем же — иначе одна строка связей даёт diff на весь файл,
    и правку невозможно прочитать глазами."""
    for line in text.splitlines()[1:]:
        s = len(line) - len(line.lstrip(" "))
        if s:
            return s
    return 1


def lesson_path(uid):
    """les:<тема>/<файл> → путь к JSON урока. Расширения в идентификаторе нет."""
    rel = uid.split(":", 1)[1]
    return COURSES / (rel if rel.endswith(".json") else rel + ".json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="показать, ничего не писать")
    ap.add_argument("--topic", default="", help="только одна тема")
    ap.add_argument("--min", type=float, default=MIN_LINK)
    ap.add_argument("--gaps", default="", help="куда записать список пустых мест")
    args = ap.parse_args()

    import numpy as np

    if not (LESSONS.with_suffix(".f16")).exists():
        print(f"нет векторов уроков ({LESSONS}.f16). Пересчёт: python lessons_vectors.py в b42-ml")
        return 2
    if not (FIELD.with_suffix(".f16")).exists():
        print(f"нет поля ({FIELD}.f16)")
        return 2

    arts = our_articles()
    print(f"наших статей: {len(arts)}")
    lids, LM = load_lessons()
    print(f"векторов уроков: {len(lids)}")
    aids, AM = load_ours(arts.keys())
    print(f"из них в поле нашлось: {len(aids)}")

    L = np.asarray(LM, dtype=np.float32)
    sims = L @ AM.T                       # оба набора нормированы: скалярное = косинус

    written = changed = 0
    gaps = []
    for i, uid in enumerate(lids):
        f = lesson_path(uid)
        if args.topic and f.parent.name != args.topic:
            continue
        if not f.exists():
            print(f"  ⚠️ нет файла урока {uid}")
            continue
        kind = "topic" if f.name == "course.json" else ("guide" if f.name == "guide.json" else "lesson")
        if kind == "guide":
            continue                      # страница путеводителя связи не показывает
        want = TOP_TOPIC if kind == "topic" else TOP_LESSON

        row = sims[i]
        order = np.argsort(row)[::-1]
        best = float(row[order[0]]) if len(order) else 0.0
        picked = []
        for j in order[:want * 3]:
            s = float(row[j])
            if s < args.min or len(picked) >= want:
                break
            a = arts[aids[j]]
            picked.append({"id": a["id"], "date": a["date"], "title": a["titles"],
                           "score": round(s, 3)})

        if best < GAP_BELOW:
            gaps.append({"lesson": uid.split(":", 1)[1], "best": round(best, 3),
                         "kind": kind})

        if args.dry:
            print(f"\n{uid.split(':', 1)[1]}  (лучший {best:.3f}, годных {len(picked)})")
            for p in picked:
                print(f"   {p['score']:.3f}  {p['title'].get('ru', p['id'])[:70]}")
            continue

        raw = f.read_text(encoding="utf-8")
        d = json.loads(raw)
        ent = d.setdefault("entities", {})
        old = json.dumps(ent.get("examples_from_articles"), ensure_ascii=False, sort_keys=True)
        if picked:
            ent["examples_from_articles"] = picked
        else:
            ent.pop("examples_from_articles", None)   # пусто честнее слабой ссылки
        new = json.dumps(ent.get("examples_from_articles"), ensure_ascii=False, sort_keys=True)
        written += 1
        if old != new:
            changed += 1
            # перевод строки в конце — иначе каждый прогон помечает изменённым каждый урок
            f.write_text(json.dumps(d, ensure_ascii=False, indent=indent_of(raw)) + "\n",
                         encoding="utf-8")

    if not args.dry:
        print(f"\nобработано материалов: {written}, изменено файлов: {changed}")
    print(f"пустых мест (лучший косинус < {GAP_BELOW}): {len(gaps)}")
    for g in sorted(gaps, key=lambda x: x["best"])[:15]:
        print(f"   {g['best']:.3f}  {g['lesson']}")
    if args.gaps:
        Path(args.gaps).write_text(
            json.dumps({"threshold": GAP_BELOW, "built_from": "lessons-en × field.f16",
                        "gaps": sorted(gaps, key=lambda x: x["best"])},
                       ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"список дыр: {args.gaps}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
