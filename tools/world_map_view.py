#!/usr/bin/env python3
"""Карта мира → в формат, который уже умеет рисовать страница аналитики.

ML собрал `data/analytics/world-map.json`: 600 областей, нарезанных по полю из 1 556 983
работ arXiv, координаты — главные компоненты центров областей. Ключевое отличие от
нынешней карты статей: координаты задаёт МИР, а не мы, и они фиксированы. Прежняя карта
строилась t-SNE по нашим тегам — она честно показывала структуру нашей разметки, но
пересчитывалась каждый день заново, и читатель, вернувшийся через неделю, видел то же
самое в другом месте.

Здесь мы только перекладываем данные в формат `points` + `clusters`, который страница
уже рисует. Своего рисовальщика не заводим: у аналитики их шесть, седьмой никто не
будет чинить.

Что видно на этой карте:
· размер точки — сколько работ в области у МИРА;
· цвет — доля наших разборов от мировых (покрытие);
· отдельно помечены значимые пустоты: там, где ноль наших работ не объясняется
  случайностью (проверка ML: ожидание по размеру области, вероятность нуля < 5%).

    python tools/world_map_view.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "analytics" / "world-map.json"
OUT = ROOT / "data" / "analytics" / "world-view.json"

# Подписи на пяти языках: страница одна на всех, тексты приходят с данными.
LEGEND = {
    "ru": {"title": "Карта мира и наше покрытие",
           "note": "600 областей науки, нарезанных по 1,56 млн работ arXiv. Размер — "
                   "сколько работ у мира, цвет — какую долю разобрали мы. Координаты "
                   "фиксированы: карта не перестраивается от новых статей.",
           "gap": "значимая пустота", "world": "работ у мира", "ours": "разобрано нами",
           "cover": "покрытие"},
    "en": {"title": "The world map and our coverage",
           "note": "600 areas of science carved out of 1.56M arXiv papers. Size is how "
                   "many papers the world has, colour is the share we reviewed. The "
                   "coordinates are fixed: the map does not rebuild as articles arrive.",
           "gap": "significant gap", "world": "papers worldwide", "ours": "reviewed by us",
           "cover": "coverage"},
    "es": {"title": "El mapa del mundo y nuestra cobertura",
           "note": "600 áreas de la ciencia recortadas de 1,56 millones de trabajos de "
                   "arXiv. El tamaño es cuántos trabajos tiene el mundo; el color, la "
                   "parte que hemos analizado. Las coordenadas son fijas.",
           "gap": "vacío significativo", "world": "trabajos en el mundo",
           "ours": "analizados por nosotros", "cover": "cobertura"},
    "fr": {"title": "La carte du monde et notre couverture",
           "note": "600 domaines découpés dans 1,56 million de travaux d’arXiv. La taille "
                   "indique le nombre de travaux dans le monde, la couleur la part que "
                   "nous avons analysée. Les coordonnées sont fixes.",
           "gap": "vide significatif", "world": "travaux dans le monde",
           "ours": "analysés par nous", "cover": "couverture"},
    "ar": {"title": "خريطة العالم وتغطيتنا",
           "note": "600 مجال علمي مقتطعة من 1.56 مليون بحث في arXiv. الحجم يدل على عدد "
                   "الأبحاث في العالم، واللون على النسبة التي حلّلناها. الإحداثيات ثابتة.",
           "gap": "فراغ ذو دلالة", "world": "أبحاث في العالم", "ours": "حلّلناها",
           "cover": "التغطية"},
}


def main():
    if not SRC.exists():
        print(f"нет {SRC.name} — сначала соберите карту (world_map.py у ML)")
        return 1
    d = json.loads(SRC.read_text(encoding="utf-8"))
    regions = d.get("regions_list") or []
    if not regions:
        print("в карте нет областей")
        return 1

    top = max((r.get("world") or 0) for r in regions) or 1
    points = []
    for r in regions:
        cov = r.get("coverage") or 0
        # Цветовая группа — по покрытию, а не по номеру области: читателю важно «сколько
        # мы прочли здесь», а не «какой это кластер по счёту».
        if r.get("significant_gap"):
            grp = 0                     # значимая пустота
        elif cov <= 0.002:
            grp = 1
        elif cov <= 0.01:
            grp = 2
        elif cov <= 0.03:
            grp = 3
        else:
            grp = 4
        points.append({
            "id": f"r{r.get('id')}",
            "t": r.get("name", ""),
            "x": r.get("x", 0), "y": r.get("y", 0),
            "z": round((r.get("world") or 0) / top, 4),
            "c": grp,
            "w": r.get("world") or 0,
            "o": r.get("ours") or 0,
            "cov": round(cov * 100, 2),
            "gap": bool(r.get("significant_gap")),
        })

    # Формат ровно тот, который страница уже читает: clusters — словарь {номер: [подписи]},
    # titles — человеческие названия по языкам. Свой рисовальщик заводить не будем:
    # у аналитики их шесть, седьмой никто не станет чинить.
    names = {
        0: {"ru": "значимая пустота", "en": "significant gap", "es": "vacío significativo",
            "fr": "vide significatif", "ar": "فراغ ذو دلالة"},
        1: {"ru": "почти не читали", "en": "barely read", "es": "apenas leído",
            "fr": "à peine lu", "ar": "بالكاد قرأنا"},
        2: {"ru": "тронули", "en": "touched", "es": "tocado", "fr": "effleuré", "ar": "لمسناه"},
        3: {"ru": "читаем", "en": "reading", "es": "leyendo", "fr": "en lecture", "ar": "نقرأ"},
        4: {"ru": "плотно читаем", "en": "well covered", "es": "bien cubierto",
            "fr": "bien couvert", "ar": "تغطية جيدة"},
    }
    clusters = {str(k): [v["ru"]] for k, v in names.items()}
    titles = {str(k): {lang: {"title": v[lang]} for lang in v} for k, v in names.items()}

    out = {
        "points": points, "clusters": clusters, "titles": titles, "n": len(points),
        "legend": LEGEND,
        "field": d.get("field"), "ours": d.get("ours"),
        "empty_regions": d.get("empty_regions"), "significant_gaps": d.get("significant_gaps"),
        "built": d.get("built"),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"✅ {OUT.name}: {len(points)} областей, "
          f"значимых пустот {out['significant_gaps']}, размер {OUT.stat().st_size // 1024} КБ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
