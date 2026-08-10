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

