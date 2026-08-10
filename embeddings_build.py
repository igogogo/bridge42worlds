#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Эмбеддинги всего, что у нас есть: статьи, теги, законы, учёные.

ПРАВИЛО ИСТОЧНИКА (решение владельца 2026-07-30): вектор строится ТОЛЬКО из английского
текста. Английский есть у всех документов, научные термины в нём каноничны, модель на нём
обучена лучше. Векторов из переводов не делаем — перевод добавляет шум и множит индекс.
Русский/испанский/арабский запрос приводится к этому пространству самой моделью.

В ВЕКТОР ИДЁТ ТЕКСТ, А НЕ НАЗВАНИЕ (поправка владельца 2026-08-04). У тега есть своя
статья на несколько тысяч знаков, и сравнивать научную работу со строчкой «фрактал»
бессмысленно — сравнивать надо с текстом про фракталы. Замер: теги 4410 знаков в среднем,
законы 3905, учёные 930. Именно это даёт смысловую привязку вместо совпадения слов.

Модель `@cf/baai/bge-m3` через Workers AI. Размерность проверена живым вызовом 2026-08-04:
**1024** (в документации Cloudflare её нет, раньше значение бралось из спецификации модели).
Там же проверена кросс-язычность: английский текст против русского запроса — косинус 0,659.

    python embeddings_build.py --kinds tags,laws,scientists,articles
    python embeddings_build.py --kinds tags --limit 20      # прикинуть на малом
"""
import json, math, os, pathlib, sys, time, argparse
import urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent
MODEL = "@cf/baai/bge-m3"
DIM = 1024
# Ограничитель на документ. Модель держит 60k токенов, упереться мы не можем —
# это защита от аномалии в данных, а не режим работы.
MAX_CHARS = 12000
BATCH = 20
# Служебные поля справочников: в текст не идут. `raw` — сырой ответ модели, дубль
# остальных полей; image_prompt — задание художнику, к смыслу понятия отношения не имеет.
SKIP_FIELDS = {"raw", "image_prompt", "image_model", "image_pending", "refined",
               "educational", "name", "formulas"}


def load_env(main_repo):
    env = {}
    p = pathlib.Path(main_repo) / ".env"
    if not p.exists():
        sys.exit(f"нет .env: {p}")
    for line in p.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def flatten(v):
    """Поле справочника → текст. Списки и словари разворачиваем, а не печатаем как json."""
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        return " ".join(flatten(x) for x in v)
    if isinstance(v, dict):
        return " ".join(flatten(x) for x in v.values())
    return ""


def ref_docs(main_repo, name, kind):
    """Тексты тегов/законов/учёных из АНГЛИЙСКОГО справочника."""
    p = pathlib.Path(main_repo) / "lang" / "en" / "data" / name
    if not p.exists():
        print(f"  !! нет {p}")
        return []
    j = json.loads(p.read_text(encoding="utf-8"))
    items = j.items() if isinstance(j, dict) else ((x.get("id") or x.get("name"), x) for x in j)
    out = []
    for key, obj in items:
        if not isinstance(obj, dict):
            continue
        parts = [str(obj.get("name") or key)]
        for f, v in obj.items():
            if f in SKIP_FIELDS:
                continue
            t = flatten(v).strip()
            if t:
                parts.append(t)
        text = " ".join(" ".join(parts).split())[:MAX_CHARS]
        if len(text) > 30:
            out.append({"id": f"{kind}:{key}", "kind": kind, "text": text})
    return out


def arxiv_docs(main_repo, months=None, limit=0):
    """ВСПОМОГАТЕЛЬНЫЙ индекс: сырые английские аннотации всего arXiv, как есть.

    Решение владельца 2026-08-10: отдельный вектор, не смешанный с нашим. Причина
    в том, ЧТО в них лежит: у нас — наша интерпретация (пересказ, аналогия, упрощение),
    здесь — первоисточник без нашего слоя.

    ПОЧЕМУ ПОРОЗНЬ, А НЕ ОДНИМ ИНДЕКСОМ. Обе стороны считаются одной моделью по
    английскому тексту, то есть живут в ОДНОМ пространстве и спрашиваются друг о друге:
    наша статья → что рядом в трёх миллионах и чего мы не взяли; чужая аннотация →
    писали мы про это или нет. Слить их в один индекс — значит потерять сам вопрос
    «что есть там, чего нет здесь», а он и есть карта покрытия.

    Ничего не обрабатываем: заголовок и аннотация как пришли из дампа.
    """
    bulk = pathlib.Path(main_repo) / "data" / "arxiv-bulk"
    files = sorted(p for p in bulk.glob("*.jsonl") if p.stat().st_size > 0)
    if months:
        want = set(months)
        files = [p for p in files if p.stem in want]
    out = []
    for f in files:
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    j = json.loads(line)
                except Exception:
                    continue
                t = " ".join(f"{j.get('title','')} {j.get('abstract','')}".split())
                if j.get("id") and len(t) > 80:
                    out.append({"id": f"arx:{j['id']}", "kind": "arxiv",
                                "text": t[:MAX_CHARS], "cat": (j.get("categories") or [""])[0],
                                "published": j.get("published")})
                if limit and len(out) >= limit:
                    return out
    return out


def article_docs(main_repo, limit=0):
    """Статьи: авторский заголовок с arXiv + наш английский разбор уровня advanced.

    Заголовок берём АВТОРСКИЙ, не наш популярный: наши заголовки намеренно расжаргонены
    («Vibration-Absorbing Layer Cake»), и вектор от них уезжает от исходной работы.
    """
    arch = pathlib.Path(main_repo) / "lang" / "ru" / "archive"
    out = []
    for p in sorted(arch.rglob("data.json")):
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        aid = j.get("id")
        title = (j.get("original_title") or "").strip()
        en = (j.get("abstract") or {}).get("en") or {}
        body = (en.get("advanced") or "").strip() if isinstance(en, dict) else ""
        if not body:
            body = ((j.get("advanced") or {}).get("en") or {}).get("description", "").strip()
        text = " ".join(f"{title}\n\n{body}".split())[:MAX_CHARS]
        if aid and len(text) > 40:
            out.append({"id": f"art:{aid}", "kind": "article", "text": text,
                        "date": j.get("date"), "express": bool(j.get("express"))})
        if limit and len(out) >= limit:
            break
    return out


def embed(texts, acc, tok, tries=5):
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{MODEL}"
    body = json.dumps({"text": texts}).encode("utf-8")
    for attempt in range(tries):
        req = urllib.request.Request(url, data=body, headers={
            "Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read().decode("utf-8"))
            vecs = (d.get("result") or {}).get("data")
            if not vecs or len(vecs) != len(texts):
                raise ValueError(f"ответ не по размеру: {len(vecs or [])} на {len(texts)}")
            return vecs
        except urllib.error.HTTPError as e:
            # 429 — наш же сторож квот. Не обходим, а ждём: задача разовая, спешить некуда.
            if e.code in (429, 500, 502, 503):
                time.sleep(2 ** attempt * 2)
                continue
            raise
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt * 2)
    raise RuntimeError("не удалось получить эмбеддинги после повторов")


DI_URL = "https://api.deepinfra.com/v1/inference/BAAI/bge-m3"
# Предел контекста у bge-m3 — 60k токенов, и он на ПАЧКУ целиком, а не на текст
# (выяснено 2026-08-08: батч из 20 аннотаций получил «Max context reached 78440 tokens»).
# Считаем токены как знаки/1,5: на научном тексте с формулами привычное «знаки/4»
# занижает втрое. 40k — запас к пределу, чтобы промах оценки не ронял прогон.
DI_BATCH_TOKENS = 40000


def embed_di(texts, key, tries=5, stats=None):
    """Та же bge-m3, но через DeepInfra: своя карта, свой счёт, без квоты Workers AI.

    Зачем второй адрес к одной модели. У Workers AI платится не за вызов, а за индекс,
    и дневная квота у нас общая с поиском на сайте. Разметка тегов — разовый тяжёлый
    прогон, он не должен занимать канал, которым живёт продакшн. Модель та же самая,
    размерность та же (1024, проверено живым вызовом 2026-08-10), значит векторы одного
    прогона сравнимы с другим.
    """
    body = json.dumps({"inputs": texts}).encode("utf-8")
    for attempt in range(tries):
        req = urllib.request.Request(DI_URL, data=body, headers={
            "Authorization": f"bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read().decode("utf-8"))
            vecs = d.get("embeddings")
            if not vecs or len(vecs) != len(texts):
                raise ValueError(f"ответ не по размеру: {len(vecs or [])} на {len(texts)}")
            if stats is not None:
                # Токены берём У ПОСТАВЩИКА, а не считаем по знакам: наша оценка «знаки/1,5»
                # нужна, чтобы не превысить контекст, и для денег она грубовата.
                stats["tokens"] = stats.get("tokens", 0) + int(d.get("input_tokens") or 0)
            return vecs
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503):
                time.sleep(2 ** attempt * 2)
                continue
            # Тело ответа несёт причину («Max context reached ...»), а urllib её глотает.
            # Без этой строки 400 выглядит как «просто 400» и час уходит на догадки.
            detail = e.read().decode("utf-8", "replace")[:300]
            raise RuntimeError(f"HTTP {e.code}: {detail}") from None
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt * 2)
    raise RuntimeError("не удалось получить эмбеддинги после повторов")


def _di_split(texts, key, stats=None):
    """Пачка не прошла по контексту — делим пополам, в пределе до одного текста.

    Одна аномально длинная статья не должна ронять прогон на три тысячи: оценка
    токенов по знакам приблизительная, и промахивается она именно на редких текстах.
    """
    try:
        return embed_di(texts, key, stats=stats)
    except RuntimeError as e:
        if len(texts) == 1 or "context" not in str(e).lower():
            raise
        mid = len(texts) // 2
        return _di_split(texts[:mid], key, stats) + _di_split(texts[mid:], key, stats)


def log_usage(agent, tokens, model="bge-m3"):
    """Запись в общий журнал расхода — тот же файл и тот же формат, что у генерации.

    Отдельного журнала у вектора нет намеренно: владелец смотрит один отчёт
    (tools/cost_report.py), и статья расходов, которой в нём нет, для него не существует.
    Эмбеддинги пишутся как cache_miss — у них нет ни кэша поставщика, ни выхода.
    """
    try:
        rec = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "agent": agent, "model": model,
               "prompt": tokens, "completion": 0, "cache_hit": 0, "cache_miss": tokens}
        with (ROOT / "data/usage-log.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        # Журнал не должен ронять расчёт: деньги уже потрачены, запись — вторична.
        pass


def embed_cached(texts, key, cache_path, label="", agent="embed"):
    """Векторы для списка текстов; посчитанное однажды лежит на диске.

    Кэш по отпечатку текста, а не по номеру строки: статьи дописываются и правятся,
    порядок и количество меняются от прогона к прогону, а сам текст — нет. Поэтому
    повторная разметка после добавления двадцати статей считает двадцать, а не три тысячи.
    """
    import hashlib
    cache = {}
    cache_path = pathlib.Path(cache_path)
    if cache_path.exists():
        for line in cache_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    r = json.loads(line)
                    cache[r["h"]] = r["v"]
                except Exception:
                    pass

    keys = [hashlib.sha1(t.encode("utf-8")).hexdigest() for t in texts]
    todo, seen = [], set()
    for h, t in zip(keys, texts):
        if h not in cache and h not in seen:
            seen.add(h)
            todo.append((h, t))
    if todo:
        chars = sum(len(t) for _, t in todo)
        print(f"  {label}: считаю {len(todo)} из {len(texts)}, знаков {chars:,}, "
              f"~${chars / 1.5 / 1e6 * 0.010:.4f}")
        done, stats = 0, {}
        with cache_path.open("a", encoding="utf-8") as f:
            batch, budget = [], 0
            for h, t in todo + [(None, None)]:
                cost = len(t) / 1.5 if t else 0
                if batch and (h is None or budget + cost > DI_BATCH_TOKENS or len(batch) >= 32):
                    vecs = _di_split([x[1] for x in batch], key, stats)
                    for (bh, bt), v in zip(batch, vecs):
                        cache[bh] = v
                        f.write(json.dumps({"h": bh, "v": [round(x, 6) for x in v]}) + "\n")
                    f.flush()
                    done += len(batch)
                    print(f"    {done}/{len(todo)}")
                    batch, budget = [], 0
                if h is not None:
                    batch.append((h, t))
                    budget += cost
        log_usage(agent, stats.get("tokens", 0))
        print(f"  {label}: {stats.get('tokens', 0):,} токенов "
              f"(${stats.get('tokens', 0) / 1e6 * 0.010:.4f}) — записано в журнал")
    else:
        print(f"  {label}: всё из кэша ({len(texts)})")
    return [cache[h] for h in keys]


def run(kind_docs, kind, acc, tok, out_path):
    """Считает и дописывает в файл. Повторный запуск добирает недостающее."""
    done = {}
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    r = json.loads(line)
                    done[r["id"]] = True
                except Exception:
                    pass
        print(f"  уже посчитано: {len(done)}")

    todo = [d for d in kind_docs if d["id"] not in done]
    if not todo:
        print(f"  {kind}: всё на месте")
        return 0
    chars = sum(len(d["text"]) for d in todo)
    print(f"  {kind}: считаю {len(todo)}, знаков {chars:,}, "
          f"~${chars/4/1e6*0.012:.4f}")

    n = 0
    with out_path.open("a", encoding="utf-8") as f:
        for i in range(0, len(todo), BATCH):
            chunk = todo[i:i + BATCH]
            vecs = embed([d["text"] for d in chunk], acc, tok)
            for d, v in zip(chunk, vecs):
                if len(v) != DIM:
                    sys.exit(f"размерность {len(v)}, ожидалась {DIM} — проверь модель")
                rec = {k: d[k] for k in d if k != "text"}
                rec["len"] = len(d["text"])
                rec["vec"] = [round(x, 6) for x in v]
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n += 1
            f.flush()
            print(f"    {min(i + BATCH, len(todo))}/{len(todo)}")
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=r"C:\Users\nadez\PycharmProjects\bridge42worlds",
                    help="главная папка проекта: там .env и lang/** (в git их нет)")
    ap.add_argument("--kinds", default="tags,laws,scientists,articles")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--months", default="", help="через запятую, напр. 2026-07,2026-06")
    args = ap.parse_args()

    env = load_env(args.repo)
    acc, tok = env.get("CLOUDFLARE_ACCOUNT_ID"), env.get("CLOUDFLARE_API_TOKEN")
    if not acc or not tok:
        sys.exit("в .env нет CLOUDFLARE_ACCOUNT_ID/CLOUDFLARE_API_TOKEN")

    (ROOT / "data").mkdir(exist_ok=True)
    sources = {
        "tags": lambda: ref_docs(args.repo, "tags.json", "tag"),
        "laws": lambda: ref_docs(args.repo, "laws.json", "law"),
        "scientists": lambda: ref_docs(args.repo, "scientists.json", "sci"),
        "articles": lambda: article_docs(args.repo, args.limit),
        # вспомогательный индекс: сырые аннотации arXiv, отдельным файлом
        "arxiv": lambda: arxiv_docs(args.repo, args.months.split(",") if args.months else None,
                                    args.limit),
    }
    total = 0
    for kind in [k.strip() for k in args.kinds.split(",") if k.strip()]:
        if kind not in sources:
            print(f"  !! неизвестный вид: {kind}")
            continue
        docs = sources[kind]()
        if args.limit and kind != "articles":
            docs = docs[:args.limit]
        if not docs:
            continue
        lens = [len(d["text"]) for d in docs]
        print(f"{kind}: документов {len(docs)}, знаков в среднем {sum(lens)//len(lens)}, "
              f"макс {max(lens)}")
        total += run(docs, kind, acc, tok, ROOT / "data" / f"embeddings-{kind}.jsonl")
    print(f"\nпосчитано новых векторов: {total}")


if __name__ == "__main__":
    main()

