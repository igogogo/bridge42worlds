"""Теги и законы ПО СМЫСЛУ, а не по списку в промпте.

Владелец 2026-08-04: «давай уходить от передачи облака тегов в промпт — у нас теперь есть
вектор, можно загнать теги, законы и их описания в вектор и индексировать ими напрямую,
перестроить логику привязки. И главный тег, кажется, можно получить из вектора».

Зачем — замер, а не ощущение. В архиве 363 тега, и:
  · 179 из них НЕ проставлены ни одной статье — половина словаря мертва;
  · на десять самых частых приходится 45% всех проставлений;
  · медицинских тегов в ходу практически нет.
Причина в механизме: мы отдаём модели список из 363 названий и просим выбрать. Модель
берёт знакомое и частое (спектроскопия, энтропия, чёрные дыры), редкое и точное не берёт
никогда — «безопаснее» назвать общее. Так теряется структура: была астрофизика — стала
астрофизика, а фрактал, перколяция и фазовый переход стоят пустые.

Здесь другое: у каждого тега есть человеческое описание (name + mini + практическое
применение), у каждой статьи — свой текст. Сравниваем СМЫСЛЫ и берём ближайшие. Привязка
становится воспроизводимой (один и тот же текст всегда получит те же теги), бесплатной
(модель не вызывается) и одинаковой для всех языков.

    python tools/tag_by_vector.py --check          сверить с нынешними тегами, ничего не менять
    python tools/tag_by_vector.py --show 2607.123  что предложит для одной статьи
    python tools/tag_by_vector.py --apply          записать в data.json (поле tags_vec)

ВАЖНО: --apply пишет в ОТДЕЛЬНОЕ поле tags_vec, не трогая нынешние теги. Сначала смотрим,
что получилось, потом решаем, переключать ли на них ленту.
"""
import argparse
import json
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

ROOT = Path(__file__).resolve().parent.parent
MARK = re.compile(r"\[(?:tag|scientist|law):[^\]]+\]|\[/(?:tag|scientist|law)\]")


def tag_texts():
    """Тег как ТЕКСТ: название + простое объяснение + практическое применение.
    Голого названия мало — «энтропия» и «фрактал» одним словом ничем не отличаются для
    сравнения смыслов. Описание даёт тегу собственное смысловое поле."""
    d = json.loads((ROOT / "lang/ru/data/tags.json").read_text(encoding="utf-8"))
    ids, texts = [], []
    for tid, v in d.items():
        if not isinstance(v, dict):
            continue
        parts = [v.get("name", ""), v.get("mini", ""), v.get("practical_application", ""),
                 v.get("description_popular", ""), v.get("description_simple", "")]
        t = " ".join(p for p in parts if p)
        if len(t) < 40:
            continue
        ids.append(tid)
        texts.append(t)
    return ids, texts, d


def article_texts():
    ids, texts, meta = [], [], {}
    for p in sorted((ROOT / "lang/ru/archive").glob("*/*/data.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        v = (d.get("popular", {}) or {}).get("ru") or (d.get("simple", {}) or {}).get("ru") or {}
        if not isinstance(v, dict) or not v.get("title"):
            continue
        t = MARK.sub(" ", " ".join(str(v.get(k, "")) for k in ("title", "description", "text")))
        if len(t) < 200:
            continue
        ids.append(p.parent.name)
        texts.append(t)
        meta[p.parent.name] = {"title": v["title"], "tags": v.get("extra_tags", []),
                               "main": v.get("main_tag", ""), "path": p}
    return ids, texts, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--show")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--min", type=float, default=0.045)
    args = ap.parse_args()

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import linear_kernel
    import numpy as np

    tids, ttexts, tdict = tag_texts()
    aids, atexts, ameta = article_texts()
    print(f"тегов с описанием: {len(tids)} · статей: {len(aids)}")

    # Общее словарное пространство: теги и статьи должны меряться одной линейкой,
    # поэтому обучаем на объединении, а не на каждом корпусе отдельно.
    vec = TfidfVectorizer(min_df=2, max_df=0.5, sublinear_tf=True,
                          token_pattern=r"(?u)\b\w[\w-]{2,}\b")
    vec.fit(ttexts + atexts)
    T = vec.transform(ttexts)
    A = vec.transform(atexts)

    if args.show:
        i = aids.index(args.show) if args.show in aids else None
        if i is None:
            print("статья не найдена")
            return 1
        sim = linear_kernel(A[i], T)[0]
        order = np.argsort(sim)[::-1][:args.top]
        print(f"\n{ameta[aids[i]]['title']}")
        print(f"  сейчас:   {ameta[aids[i]]['main']} · {', '.join(ameta[aids[i]]['tags'][:5])}")
        print("  по смыслу:")
        for j in order:
            print(f"     {sim[j]:.3f}  {tids[j]}  ({tdict[tids[j]].get('name', '')})")
        return 0

    # массовая привязка
    revived = set()
    now_used = set()
    got = {}
    CH = 300
    for s in range(0, A.shape[0], CH):
        sim = linear_kernel(A[s:s + CH], T)
        for i, row in enumerate(sim):
            aid = aids[s + i]
            order = np.argsort(row)[::-1]
            picked = [tids[j] for j in order[:args.top] if row[j] >= args.min]
            got[aid] = picked
            now_used.update(ameta[aid]["tags"] + [ameta[aid]["main"]])
            revived.update(picked)

    old_dead = set(tdict) - now_used
    new_dead = set(tdict) - revived
    print(f"\nбыло тегов без единой статьи: {len(old_dead)} из {len(tdict)}")
    print(f"стало по смысловой привязке:   {len(new_dead)} из {len(tdict)}")
    print(f"ожили: {len(old_dead - new_dead)} тегов")
    ex = sorted(old_dead - new_dead)[:12]
    print("например:", ex)

    if args.apply:
        n = 0
        for aid, tags in got.items():
            p = ameta[aid]["path"]
            d = json.loads(p.read_text(encoding="utf-8"))
            for tier in ("simple", "popular", "advanced"):
                v = d.get(tier, {}).get("ru")
                if isinstance(v, dict):
                    v["tags_vec"] = tags
            p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            n += 1
        print(f"\nзаписано в tags_vec: {n} статей (нынешние теги не тронуты)")
    else:
        print("\nэто сверка — ничего не записано; --apply запишет в поле tags_vec")
    return 0


if __name__ == "__main__":
    sys.exit(main())
