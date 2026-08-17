#!/usr/bin/env python3
"""Окружение работы для промпта полного разбора: что лежит рядом и чем эта работа отличается.

Задача p3 техлиста, решение владельца 18.08: «отточи промпты, чтобы разбор был серьёзный,
с подключением вектора». До сих пор модель видела ТОЛЬКО текст самой статьи (gen_llm:249):
ни соседей, ни поля вокруг — и писала «работа продолжает известное направление», потому что
проверить это было нечем. Здесь собирается блок, который отвечает на три вопроса измерением,
а не догадкой: кто рядом у нас, кто рядом во всём arXiv, густо тут или пусто.

Механика взята у tools/recommend.py целиком — вектор ищет, модель формулирует, каждое
утверждение с опорой на конкретный id. Своего вектора, своих порогов и своего формата строки
соседа здесь нет намеренно: пороги 0.61/0.65/0.70 откалиброваны по корпусу 11 августа, и
второй набор чисел рядом с ними означал бы, что через месяц они разъедутся.

Ничего не падает. Разбор статьи дороже окружения в сто раз, поэтому любая осечка вектора —
это пустой блок и СТРОКА В ЛОГЕ, а не исключение. Молчаливых откатов не делаем: в проекте
они уже стоили нам перевода, ушедшего по-русски на четырёх языках (см. `_log`).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Карту читаем ту же, что показываем читателю: v2 (UMAP+HDBSCAN) с откатом на v1.
MAP_V2 = ROOT / "data" / "analytics" / "articles-map-v2.json"
MAP_V1 = ROOT / "data" / "analytics" / "articles-map.json"

OURS_WANT = 8       # соседей из нашего архива в блок
WORLD_WANT = 5      # соседей из мирового поля
_map_cache = None


def _log(msg):
    """Осечки видны в логе прогона. Тихий откат здесь — это разбор, который выглядит
    обогащённым, но собран вслепую; отличить его потом невозможно."""
    print(f"    🌐 окружение: {msg}")


def _base_id(aid):
    """id без версии: на карте и в поле версий нет, в архиве есть."""
    return re.sub(r"v\d+$", "", (aid or "").strip())


def _load_map():
    """Точки карты → {базовый id: номер кластера} + расшифровка кластеров топ-тегами."""
    global _map_cache
    if _map_cache is not None:
        return _map_cache
    for p in (MAP_V2, MAP_V1):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        pts = {_base_id(x.get("id")): x.get("c") for x in d.get("points", [])}
        _map_cache = (pts, d.get("clusters") or {}, p.name)
        return _map_cache
    _map_cache = ({}, {}, None)
    return _map_cache


def cluster_of(neighbours):
    """Тематическая группа карты — по большинству соседей, а не по самой статье.

    Свежая работа на карте ещё не стоит (карта пересобирается после генерации), поэтому
    её положение определяется тем, куда попали соседи. Это и честнее: одна точка может
    сесть на границе двух групп, восемь соседей — уже мнение.

    Кластер -1 у v2 означает «работа не примыкает к плотной группе» и в счёт не идёт:
    это ответ карты, но не тема, и называть его темой нельзя.
    """
    pts, clusters, src = _load_map()
    if not pts:
        return None
    votes = {}
    for n in neighbours:
        c = pts.get(_base_id(n.get("id")))
        if c is None or int(c) < 0:
            continue
        votes[int(c)] = votes.get(int(c), 0) + 1
    if not votes:
        return None
    c, cnt = max(votes.items(), key=lambda kv: kv[1])
    tags = clusters.get(str(c)) or []
    if not tags:
        return None
    return {"cluster": c, "votes": cnt, "of": len(neighbours),
            "tags": list(tags), "source": src}


def neighbours_ours(query, aid):
    """Соседи из нашего архива. Готовая find_neighbours: Workers AI bge-m3 + Vectorize."""
    try:
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        import recommend
    except Exception as e:
        _log(f"recommend не импортируется ({type(e).__name__}) — соседей из архива не будет")
        return [], None
    try:
        nb = [n for n in recommend.find_neighbours(query)
              if _base_id(n.get("id")) != _base_id(aid)]
    except Exception as e:
        _log(f"вектор архива недоступен ({type(e).__name__}: {e}) — соседей из архива не будет")
        return [], None
    if not nb:
        _log("вектор архива вернул пусто")
        return [], None
    return nb[:OURS_WANT], recommend._frontier(nb)


def neighbours_world(aid, seed):
    """Куст по всему arXiv: 1.5 млн работ поля, из них берём тех, кого у нас НЕТ.

    Сюда и смотрит вопрос «чем работа отличается»: наш архив — это 5 тысяч работ, и
    «рядом никого» в нём означает лишь то, что мы этой темы не касались. Мировое поле
    отвечает на другой вопрос — одиноко ли работе в науке вообще.
    """
    try:
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        import field
    except Exception as e:
        _log(f"field не импортируется ({type(e).__name__}) — мирового куста не будет")
        return []
    try:
        out = field.bush(aid, want=WORLD_WANT, only_new=True, quiet=True, seed=seed)
        if not out:
            # Пустой куст бывает по двум причинам, и они требуют разных действий: либо
            # работа правда одинока в поле, либо у этой копии репозитория нет дампа
            # аннотаций (он лежит только в главной папке). Молча — не отличить.
            if not field.BULK.exists():
                _log(f"мировой куст пуст: нет дампа аннотаций {field.BULK} — "
                     f"куст считается только из главной папки")
            else:
                _log("мировой куст пуст: рядом в поле никого не нашлось")
        return out
    except TypeError:
        # Старая сигнатура без seed: для свежей статьи abstract_orig ещё не заполнен,
        # и bush молча вернёт пусто. Лучше сказать вслух, чем отдать пустой куст.
        _log("tools/field.py без параметра seed — мировой куст пропущен")
        return []
    except Exception as e:
        _log(f"мировое поле недоступно ({type(e).__name__}: {e}) — куста не будет")
        return []


def _kind_of(aid):
    """Полный разбор или экспресс: опираться на пересказ аннотации слабее, чем на разбор."""
    hits = list(ROOT.glob(f"lang/ru/archive/*/{_base_id(aid)}*/data.json"))
    if not hits:
        return "экспресс"
    try:
        d = json.loads(hits[0].read_text(encoding="utf-8"))
    except Exception:
        return "экспресс"
    return "экспресс" if d.get("express") else "полный разбор"


BAND_RU = {
    "sparse": "работа стоит на отшибе — рядом почти никого",
    "mid": "обычная плотность окружения",
    "dense": "тема хожена — рядом плотно",
}


def build_block(article, text, aid=None):
    """Готовый кусок промпта + паспорт того, что в него вошло.

    Возвращает (block, meta). Пустой block — законный результат: значит вектор ничего
    не дал, и промпт останется прежним. meta уходит в api/context-ru.json, чтобы потом
    можно было отличить разбор, написанный с окружением, от написанного вслепую.
    """
    aid = aid or article.get("id", "")
    title = article.get("title", "")
    summary = article.get("summary", "")
    # Запрос по СУТИ, как в recommend.py: заголовок + аннотация arXiv + начало текста.
    # Наш образный заголовок здесь ещё не написан, и это к лучшему — вектор не уводит в поэзию.
    query = f"{title}. {summary} {(text or '')[:1200]}".strip()
    seed = f"{title} {summary}".strip()

    nb, frontier = neighbours_ours(query, aid)
    world = neighbours_world(aid, seed) if seed else []
    cluster = cluster_of(nb) if nb else None

    meta = {"neighbours": [{"id": n.get("id"), "score": n.get("score")} for n in nb],
            "frontier": frontier, "cluster": cluster,
            "world": [{"id": w.get("id"), "score": w.get("score")} for w in world]}

    if not nb and not world:
        _log("пусто со всех сторон — разбор пойдёт без окружения")
        return "", meta

    L = ["ОКРУЖЕНИЕ РАБОТЫ — найдено вектором по смыслу, это измерение, а не мнение."]

    if nb:
        L.append("")
        L.append("Рядом в нашем архиве:")
        for n in nb:
            kind = _kind_of(n.get("id", ""))
            desc = (n.get("description") or "")[:200]
            L.append(f"- [{n.get('id')}] ({kind}) {n.get('title', '')}" + (f" — {desc}" if desc else ""))

    if frontier:
        L.append("")
        L.append(f"Плотность: {BAND_RU.get(frontier['band'], frontier['band'])} "
                 f"(ближайший сосед {frontier['nearest']}, вплотную {frontier['dense']} работ).")

    if cluster:
        L.append(f"Тематическая группа карты: {', '.join(cluster['tags'])} "
                 f"({cluster['votes']} из {cluster['of']} соседей).")

    if world:
        L.append("")
        L.append("Рядом во всём arXiv (этих работ у нас нет):")
        for w in world:
            cats = ", ".join(w.get("categories") or [])
            L.append(f"- [{w.get('id')}] {w.get('title', '')} ({cats}; {w.get('published', '')})")

    L += [
        "",
        "КАК ЭТИМ ПОЛЬЗОВАТЬСЯ (это меняет два поля разбора, остальные — нет):",
        "- В поле context поставь работу на её место: рядом с чем она стоит и что вокруг",
        "  уже сделано. Не пересказывай соседей — назови направление, в котором они лежат.",
        "- В поле implications скажи, ЧЕМ эта работа отличается от соседей: другой метод,",
        "  другой масштаб, другой объект, первая проверка того, что раньше предполагали.",
        "- Опирайся только на список выше. Если по нему отличие не видно — так и напиши,",
        "  что работа идёт в общем русле. Придуманная новизна хуже честного «как у соседей»:",
        "  читатель-учёный проверит по своей памяти и перестанет верить всему остальному.",
        "- Идентификаторы работ ([2508.13272] и подобные) в текст НЕ вставляй — ссылки",
        "  подставит сайт. Опоры перечисли в поле neighbourhood.based_on.",
        "- Плотность и группа даны для тона, а не для пересказа: не пиши «плотность 0.74».",
    ]
    return "\n".join(L), meta
