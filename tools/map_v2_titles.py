#!/usr/bin/env python3
"""Человеческие имена группам карты v2 — через тот же кеш трактовки, что у карты v1.

Волна 18.08: «Имена кластеров — через тот же кеш трактовки». Карту v2 строит
analytics_v2.py, и трактовку он не зовёт вовсе: в файле есть points и clusters, но нет
поля titles. Без него страница показывает характерные теги группы («quantum algorithm ·
quantum error correction») — читаемо, но это не имя, а перечисление.

Отдельным скриптом, а не правкой analytics_v2.py, по двум причинам. Во-первых, карта —
зона ML, и трактовка ей не нужна: пересъёмка проекции и именование групп живут в разном
темпе (проекция подсаживает новые работы каждый день, имена меняются раз в месяц).
Во-вторых, вызов платный, и его должно быть видно отдельной строкой в плане фабрики,
а не внутри бесплатного шага.

    python tools/map_v2_titles.py --dry     показать, сколько групп и что уже в кеше
    python tools/map_v2_titles.py           дописать titles в карту

ДЕНЬГИ. Кеш индексируется сигнатурой характерных тегов, а у v2 они считаются иначе, чем
у v1 (по превышению над фоном, а не по средней частоте) — значит попаданий из кеша v1
почти не будет, и первый прогон платит за все группы: 60 групп × 5 языков. Дальше платятся
только новые группы. Запускать по решению ведущей.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MAP = ROOT / "data" / "analytics" / "articles-map-v2.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="ничего не тратить, только показать")
    ap.add_argument("--map", default=str(MAP), help="путь к карте")
    args = ap.parse_args()

    p = Path(args.map)
    d = json.loads(p.read_text(encoding="utf-8"))
    clusters = d.get("clusters") or {}
    if not clusters:
        print("в карте нет групп — нечего называть")
        return 1

    import analytics_build as ab

    # Примеры заголовков каждой группы: с ними трактовка перестаёт быть игрой в слова.
    samples = {}
    for pt in d.get("points", []):
        c = pt.get("c")
        if c is None or int(c) < 0:
            continue
        samples.setdefault(int(c), [])
        if len(samples[int(c)]) < 4 and pt.get("t"):
            samples[int(c)].append(pt["t"])

    cache = {}
    try:
        cache = json.loads(ab._INTERPRET_CACHE.read_text(encoding="utf-8"))
    except Exception:
        pass
    hits = sum(1 for tags in clusters.values()
               if ab._cluster_signature(tags) in cache)
    print(f"групп: {len(clusters)} · уже в кеше: {hits} · к трактовке: {len(clusters) - hits}")
    if args.dry:
        print("(сухо) ничего не вызывали")
        return 0

    titles = ab.interpret_clusters({int(c): tags for c, tags in clusters.items()},
                                   samples, "articles")
    if not titles:
        print("трактовка пуста — карта не тронута")
        return 1
    d["titles"] = titles
    # Пишем атомарно: карту читает живая страница, и оборванная запись оставила бы
    # битый JSON, у которого на клиенте только .catch(→ '—').
    from common import write_json_atomic
    write_json_atomic(p, d, indent=None)
    print(f"✅ titles записаны: {len(titles)} групп → {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
