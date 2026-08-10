#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Умеет ли реранкер выбирать то же, что выбирает дорогая модель.

Наряд архитектора, круг 2: «отбор bge-m3 (грубо) → Qwen3-Reranker (точно) → в модель
идёт только верх». Отбор кандидатов — треть стоимости ночного прогона, и он единственный
шаг, где модель читает СОТНИ текстов, чтобы оставить два десятка.

Почему именно реранкер, а не ещё один вектор. Вектор — би-энкодер: он превращает запрос
и документ в числа ОТДЕЛЬНО и потом сравнивает. Поэтому он умеет вычёркивать («это не
наш профиль»), но не умеет выбирать: замер 2026-08-08 показал, что три ранжирующие оси
для него закрыты. Реранкер — кросс-энкодер: он читает запрос и документ ВМЕСТЕ и отвечает
на вопрос «подходит ли этот текст под это описание». Это другой механизм, а не тот же
самый подешевле.

ЧЕМ МЕРИМ. Не «нравится ли мне выбор» — это не мерка. У нас лежат десятки дней, где
сохранены И кандидаты (temp/ДАТА/arxiv-api.xml), И то, что выбрала из них модель
(temp/ДАТА/selection.json). Значит вопрос ставится точно: если отдать модели не всех
кандидатов, а только верх списка реранкера — сколько её собственных находок мы потеряем?

    python rerank_eval.py --days 10            прогнать мерку на 10 последних днях
    python rerank_eval.py --days 10 --model 8B сравнить с тяжёлой моделью

Ответ — recall@k: доля выбранных моделью статей, попавших в верхние k реранкера.
Случайный порядок даёт k/N — с ним и сравниваем, иначе непонятно, есть ли вообще сигнал.
"""
import argparse
import json
import pathlib
import random
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")
NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
MODELS = {"0.6B": "Qwen/Qwen3-Reranker-0.6B",
          "4B": "Qwen/Qwen3-Reranker-4B",
          "8B": "Qwen/Qwen3-Reranker-8B"}
# Цена DeepInfra за миллион входных токенов, проверено ответом сервиса 2026-08-10.
PRICE = {"0.6B": 0.010, "4B": 0.025, "8B": 0.050}

# Запрос к реранкеру — это НАШИ критерии отбора, пересказанные одним абзацем.
# Взяты из data/prompts/article-select.txt, а не придуманы заново: мерка проверяет,
# воспроизводим ли мы существующий вкус, и запрос не имеет права быть другим вкусом.
# По-английски, потому что аннотации английские, а лишний перевод — лишний шум.
QUERY = (
    "A research paper worth retelling for a curious general reader: a breakthrough or "
    "first discovery, a long-standing problem solved, a surprising or counter-intuitive "
    "result, a macroscopic manifestation of quantum physics, practical use close to "
    "real application, human health and life — medicine, biology, neuroscience, drugs, "
    "diagnostics — or a question of philosophical and worldview significance. "
    "Real scientific contribution, not noise, and at the same time genuinely interesting "
    "to someone without scientific training."
)


def load_env():
    for line in (MAIN / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() == "DEEPINFRA_API_KEY":
                return v.strip().strip('"').strip("'")
    sys.exit("нет DEEPINFRA_API_KEY в .env")


def base_id(s):
    """arXiv-идентификатор без версии: 2508.00529v1 и 2508.00529 — одна работа."""
    s = str(s).strip().split("/")[-1]
    return s.split("v")[0] if "v" in s[-3:] else s


def day_data(day):
    """Кандидаты дня и то, что выбрала из них модель. None, если день неполный."""
    d = MAIN / "temp" / day
    xml, sel = d / "arxiv-api.xml", d / "selection.json"
    if not (xml.exists() and sel.exists()):
        return None
    try:
        root = ET.fromstring(xml.read_text(encoding="utf-8"))
    except ET.ParseError:
        return None
    cands = []
    for e in root.findall("atom:entry", NS):
        try:
            prim = e.find("arxiv:primary_category", NS)
            cands.append({
                "id": base_id(e.find("atom:id", NS).text.split("/abs/")[-1]),
                "title": e.find("atom:title", NS).text.strip().replace("\n", " "),
                "summary": e.find("atom:summary", NS).text.strip().replace("\n", " "),
                "cat": prim.get("term", "") if prim is not None else "",
            })
        except Exception:
            pass
    txt = sel.read_text(encoding="utf-8")
    if txt.startswith("```"):
        txt = txt.split("```")[1]
        txt = txt[4:] if txt.startswith("json") else txt
    try:
        data = json.loads(txt)
    except Exception:
        return None
    items = data.get("articles") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return None
    chosen = {base_id(x.get("id", "")) for x in items if isinstance(x, dict)}
    have = {c["id"] for c in cands}
    # Считаем только те находки, что действительно были в этом файле кандидатов:
    # день мог собираться из нескольких категорий, а сохранился один запрос.
    chosen &= have
    if len(cands) < 30 or not chosen:
        return None
    return cands, chosen


def rerank(query, docs, key, model, tries=4, stats=None):
    """Оценки «подходит / не подходит» для пачки документов. Одна пачка — один вызов."""
    url = f"https://api.deepinfra.com/v1/inference/{MODELS[model]}"
    body = json.dumps({"queries": [query] * len(docs), "documents": docs}).encode("utf-8")
    for a in range(tries):
        try:
            req = urllib.request.Request(url, data=body, headers={
                "Authorization": f"bearer {key}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read().decode("utf-8"))
            sc = d.get("scores")
            if not sc or len(sc) != len(docs):
                raise ValueError(f"ответ не по размеру: {len(sc or [])} на {len(docs)}")
            if stats is not None:
                stats["tokens"] = stats.get("tokens", 0) + int(d.get("input_tokens") or 0)
            return sc
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503):
                time.sleep(2 ** a * 2)
                continue
            raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
        except Exception:
            if a == tries - 1:
                raise
            time.sleep(2 ** a * 2)
    raise RuntimeError("реранкер не ответил после повторов")


# Критерии отбора соединены союзом ИЛИ: работа про здоровье человека не обязана быть
# ещё и прорывом, а прорыв в гравитации не обязан лечить. Слепив их в один абзац, мы
# спрашиваем «похоже ли на всё сразу» — и лучший ответ получает средняя работа обо всём
# понемногу. Поэтому спрашиваем по каждому критерию отдельно и берём ЛУЧШИЙ ответ.
QUERIES = [
    "A breakthrough: the first observation, discovery or direct evidence of something, "
    "or a solution to a long-standing open problem in science.",
    "A surprising, counter-intuitive result that overturns what was expected, or an "
    "unexpected connection between two distant fields.",
    "Human health and life: medicine, biology, neuroscience, drugs, diagnostics, "
    "how the body or the brain works.",
    "A macroscopic, visible manifestation of quantum physics, or fundamental gravity: "
    "black holes, the early universe, uniting relativity and quantum mechanics.",
    "Practical use close to real application: a working device, material or method, "
    "not theory for the sake of theory.",
    "A result with philosophical or worldview significance: what it says about reality, "
    "time, life or knowledge itself.",
]


def score_day(cands, key, model, stats, batch=16, multi=False):
    docs = [f"{c['title']}. {c['summary'][:900]}" for c in cands]
    queries = QUERIES if multi else [QUERY]
    best = [0.0] * len(docs)
    for q in queries:
        for i in range(0, len(docs), batch):
            sc = rerank(q, docs[i:i + batch], key, model, stats=stats)
            for j, v in enumerate(sc):
                best[i + j] = max(best[i + j], v)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--model", default="0.6B", choices=list(MODELS))
    ap.add_argument("--ks", default="20,30,50,100")
    ap.add_argument("--multi", action="store_true",
                    help="спрашивать по каждому критерию отдельно, брать лучший ответ")
    args = ap.parse_args()
    key = load_env()
    ks = [int(x) for x in args.ks.split(",")]

    days = sorted(p.name for p in (MAIN / "temp").glob("20??-??-??") if p.is_dir())
    picked, data = [], {}
    for d in reversed(days):
        r = day_data(d)
        if r:
            data[d] = r
            picked.append(d)
        if len(picked) >= args.days:
            break
    picked.reverse()
    if not picked:
        sys.exit("нет ни одного дня, где сохранились и кандидаты, и отбор")

    print(f"дней в мерке: {len(picked)} · модель: {MODELS[args.model]}")
    stats = {}
    # Считаем ПУЛОМ, а не средним по дням. День, где модель выбрала одну статью, даёт
    # либо 0%, либо 100% — и в среднем по дням весит столько же, сколько день с
    # семнадцатью находками. Это не мерка, а лотерея: складываем находки, потом делим.
    fracs = [0.20, 0.33, 0.50]
    hit_k = {k: 0 for k in ks}
    hit_f = {f: 0 for f in fracs}
    rnd_k = {k: 0 for k in ks}
    rnd_f = {f: 0 for f in fracs}
    tot_chosen = 0
    kept_f = {f: 0 for f in fracs}
    tot_cands = 0
    random.seed(42)
    for d in picked:
        cands, chosen = data[d]
        sc = score_day(cands, key, args.model, stats, multi=args.multi)
        order = sorted(range(len(cands)), key=lambda i: -sc[i])
        n = len(cands)
        tot_chosen += len(chosen)
        tot_cands += n
        sh = list(range(n))
        random.shuffle(sh)
        line = []
        for k in ks:
            hit_k[k] += len({cands[i]["id"] for i in order[:k]} & chosen)
            rnd_k[k] += len({cands[i]["id"] for i in sh[:k]} & chosen)
            line.append(f"@{k} {len({cands[i]['id'] for i in order[:k]} & chosen)}/{len(chosen)}")
        for f in fracs:
            kf = max(1, int(n * f))
            kept_f[f] += kf
            hit_f[f] += len({cands[i]["id"] for i in order[:kf]} & chosen)
            rnd_f[f] += len({cands[i]["id"] for i in sh[:kf]} & chosen)
        print(f"  {d}: кандидатов {n:4d} · выбрано моделью {len(chosen):2d} · " + " ".join(line))

    print(f"\nвсего находок модели: {tot_chosen} из {tot_cands} кандидатов")
    print("recall — сколько находок остаётся, если отдать модели только верх списка:")
    for k in ks:
        m = hit_k[k] / tot_chosen * 100
        r = rnd_k[k] / tot_chosen * 100
        print(f"  топ-{k:3d}: реранкер {m:5.1f}%   случайно {r:5.1f}%   ×{m / max(r, 0.1):.1f}")
    print("то же в долях — число кандидатов в день скачет вдвое, фиксированное k нечестно:")
    for f in fracs:
        m = hit_f[f] / tot_chosen * 100
        r = rnd_f[f] / tot_chosen * 100
        print(f"  верхние {int(f*100)}% ({kept_f[f]} кандидатов): реранкер {m:5.1f}%   "
              f"случайно {r:5.1f}%   ×{m / max(r, 0.1):.1f}")
    tok = stats.get("tokens", 0)
    print(f"\nтокенов: {tok:,} на {len(picked)} дней · ${tok / 1e6 * PRICE[args.model]:.4f} "
          f"· ${tok / 1e6 * PRICE[args.model] / len(picked):.5f} за ночь")
    return 0


if __name__ == "__main__":
    sys.exit(main())
