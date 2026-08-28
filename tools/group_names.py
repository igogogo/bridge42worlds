# -*- coding: utf-8 -*-
"""Человеческие названия групп графа знаний.

Владелец 28.08: «группы вызывают вопросы. Я понимаю, что это кластеризация, но её
надо как-то понятно трактовать — это как раз твоя задача как интеллекта.
Статистика просто даёт что-то, а ты уже можешь дать понятное название группе,
тогда мы придём к интересным выводам и понятному представлению. Сейчас название
группы мне ни о чём не говорит, а у нас с этого начинается граф знаний».

Что было. Граф подписывал группу склейкой трёх её участников — «течение жидкости
· гидродинамика · поверхностное натяжение». Это не название, а первые три строки
списка: по нему нельзя понять, чем область занимается и чем отличается от
соседней. Автоназвания от кластеризатора («Quantum Foundations») лежали в
concepts-super.json и до графа не доходили вовсе, а качество их среднее: та самая
«Quantum Foundations» собрана из центра обработки данных, скейлинга и томографии
— это не основания квантовой механики, а измерительная кухня квантовых
вычислений.

Что здесь. Модель читает РЕАЛЬНЫЙ состав группы — двадцать понятий по весу плюс
десять из хвоста, чтобы разнородность было видно, — и даёт четыре вещи:
имя по-русски и по-английски (2–4 слова) и строку «о чём эта область» на обоих
языках. Отдельно просим честности: если состав разнородный, назвать по
преобладающей теме и сказать об этом в пояснении, а не выдумывать зонтик.

    python tools/group_names.py            # показать, что получится (3 группы)
    python tools/group_names.py --run      # все 50, записать в data/group-names.json
    python tools/group_names.py --run --force-peak
"""
import argparse
import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.concept_harvest import env  # noqa: E402
from tools.concept_fullcards import cheap_window  # noqa: E402

LIVE = ROOT / "data" / "concepts-live.json"
OUT = ROOT / "data" / "group-names.json"
PER_CALL = 6          # групп в одном запросе: больше — модель начинает лениться
WORKERS = 5
TOP = 20              # сколько сильнейших понятий показать
TAIL = 10             # и сколько из хвоста — чтобы разнородность была видна

SYS = """You name clusters of physics concepts for a knowledge graph.

For each numbered cluster you get its member concepts: first the strongest ones
(most articles), then a few from the tail. Your job is to say what this area IS,
in a way a curious reader understands.

Rules that matter:
- The name must fit the ACTUAL members, not the first two of them. If the cluster
  mixes topics, name it after what dominates and say so in the note.
- 2-4 words. A field or a subject, not a sentence, not a list of members.
- No generic labels like "Physics", "Various topics", "Miscellaneous".
- The note is ONE sentence: what this area studies and what unites these
  concepts. Concrete, no filler, no "this cluster contains".
- Russian must read as natural Russian, not as a translation of the English.

Return a JSON array, one object per cluster, same order:
[{"n": 1, "name_ru": "...", "name_en": "...", "note_ru": "...", "note_en": "..."}]
Nothing else."""


def ask(batch, key):
    lines = []
    for i, (gid, strong, tail) in enumerate(batch, 1):
        lines.append(f"{i}. strongest: {', '.join(strong)}")
        if tail:
            lines.append(f"   tail: {', '.join(tail)}")
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": SYS},
                     {"role": "user", "content": "\n".join(lines)}],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        raw = json.loads(r.read().decode("utf-8"))["choices"][0]["message"]["content"]
    got = json.loads(raw)
    if isinstance(got, dict):
        for v in got.values():
            if isinstance(v, list):
                got = v
                break
    out = {}
    for it in (got if isinstance(got, list) else []):
        try:
            n = int(it["n"])
            if not (1 <= n <= len(batch)):
                continue
            gid = batch[n - 1][0]
            out[gid] = {k: str(it.get(k, "")).strip()[:200]
                        for k in ("name_ru", "name_en", "note_ru", "note_en")}
        except (KeyError, ValueError, TypeError):
            continue
    return out


def batches(limit=None, skip=()):
    doc = json.loads(LIVE.read_text(encoding="utf-8"))
    live, groups = doc["concepts"], doc.get("groups") or {}

    def name_en(cid):
        v = live.get(cid) or {}
        return (v.get("names") or {}).get("en") or cid.replace("_", " ")

    items = []
    for gid, members in groups.items():
        if gid in skip:
            continue                    # уже названа — не переспрашиваем
        members = [m for m in members if m in live]
        if not members:
            continue
        ranked = sorted(members, key=lambda m: -len(live[m].get("articles") or []))
        strong = [name_en(m) for m in ranked[:TOP]]
        tail = [name_en(m) for m in ranked[TOP:][-TAIL:]]
        items.append((gid, strong, tail))
    items.sort(key=lambda t: int(t[0]) if str(t[0]).isdigit() else 0)
    if limit:
        items = items[:limit]
    return [items[i:i + PER_CALL] for i in range(0, len(items), PER_CALL)]


def main():
    ap = argparse.ArgumentParser(description="Названия групп графа знаний")
    ap.add_argument("--run", action="store_true", help="все группы, записать")
    ap.add_argument("--force-peak", action="store_true")
    a = ap.parse_args()
    if a.run and not cheap_window() and not a.force_peak:
        print("сейчас пиковый тариф DeepSeek; --force-peak обойдёт")
        return 1
    key = env("DEEPSEEK_API_KEY")
    # Копилка, а не снимок: пачка иногда возвращается неполной (первый прогон
    # 28.08 дал 26 названий из 50), и повторный запуск должен доназвать
    # оставшиеся, а не переспрашивать всё заново.
    done = {}
    if OUT.exists():
        try:
            done = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            done = {}
    bs = batches(None if a.run else 3, skip=set(done) if a.run else ())
    print(f"уже названо: {len(done)} · осталось групп: {sum(len(b) for b in bs)} "
          f"· запросов: {len(bs)}")
    if not bs:
        print("всё названо")
        return 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for got in ex.map(lambda b: ask(b, key), bs):
            done.update(got or {})
    for gid, v in sorted(done.items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 0):
        print(f"  {gid}: {v['name_ru']} / {v['name_en']}")
        print(f"      {v['note_ru']}")
    if not a.run:
        print("\nпроба. записать все: --run")
        return 0
    OUT.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {OUT.name}: {len(done)} названий")
    return 0


if __name__ == "__main__":
    sys.exit(main())
