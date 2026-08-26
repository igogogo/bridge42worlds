# -*- coding: utf-8 -*-
"""Живой рост реестра: промпт по группам → кандидаты → сверка вектором → копилка.

Механизм владельца, 26 августа, дословно: «промптом спрашивать, какие методы, принципы
и т.д. — дать наш список ГРУПП, только те, что есть в статье, выдать их и копить; там
будут общие и частные; каждый промпт возвращает кандидатов, а потом их вектором
сравнивать и кормить, растить. Мы в промпт не отдаём весь список понятий — и это
правильно, — но группы можем, и тогда сразу структурировано придёт. Не нашёл
совпадение — пусть создаётся понятие. Потом пройтись, почистить, дистиллировать».

ЧЕТЫРЕ ШАГА, каждый отдельной командой — чтобы платное было отделено от бесплатного:

  --show ID     собрать промпт для статьи и показать. Бесплатно, без сети.
  --ask ID...   спросить модель. ПЛАТНО (DeepSeek, ~копейки на статью) — стоит под
                общим замком tools/freeze.py, как любой прогон.
  --ingest F    разобрать ответ модели и доложить кандидатов в копилку. Бесплатно.
  --match       сверить кандидатов с карточками реестра вектором. Почти бесплатно
                (Workers AI bge-m3 — тот же движок, каким считались карточки волны 5;
                другой движок дал бы несравнимые числа).
  --distill     слить кандидатов-дубли между собой. Использует векторы, уже
                посчитанные в --match, поэтому бесплатно.

ПОЧЕМУ В ПРОМПТ ИДУТ ГРУППЫ, А НЕ РЕЕСТР. Реестр (1222 понятия) в промпт не влезает
и не должен влезать: модель, которой показали список, стремится ВЫБИРАТЬ из него,
а нам нужно, чтобы она называла то, что видит в статье. Пятьдесят групп — это не
словарь для выбора, а система координат: ответ приходит уже структурированным
(вид, группа, общее/частное), и его не надо доразмечать.

ЧЕМ ЭТО ЛУЧШЕ gap-suggestions. Тот механизм копит «чего не хватило» без определений;
здесь каждый кандидат приходит С ОДНОСТРОЧНОЙ КАРТОЧКОЙ — и потому сравним вектором
с карточками реестра тем же способом, каким волна 5 сравнивала понятия между собой.
Совпал с существующим (>= MATCH_T) — это не новое понятие, а ещё одна статья к
старому. Не совпал — копится; набрал ARTICLES_MIN статей — дорос до понятия.

КОПИЛКА: data/concept-harvest.jsonl — по строке на кандидата:
  {"name", "kind", "group", "scope", "line", "articles": [...], "matched": null | id}

ДИСТИЛЛЯЦИЯ. Кандидаты приходят от разных статей чуть разными словами
(plasma_confinement / magnetic_plasma_confinement). --distill сливает пары со
сходством карточек >= DISTILL_T: копилки статей объединяются, имя остаётся у того,
кто набрал больше статей. Это та же логика, что в шаге «непересекаемость» волны 5.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT.parent / "b42-ml"
PROMPT = ROOT / "data" / "prompts" / "concept-extract.txt"
HARVEST = ROOT / "data" / "concept-harvest.jsonl"
REVIEW = ROOT / "data" / "wave5-review.json"

MATCH_T = 0.80        # с этого сходства кандидат = существующее понятие
DISTILL_T = 0.86      # с этого сходства два кандидата = один кандидат
ARTICLES_MIN = 5      # столько статей — и кандидат дорос до понятия
KINDS = ("concept method phenomenon object instrument law equation effect "
         "principle theorem substance math process property theory "
         # особые классы (владелец 26.08): величина с единицами и эталоном,
         # константа с числом — формула раскладывается в реестр целиком
         "quantity constant unit").split()

_ENV = {}


def env(k):
    if not _ENV:
        p = ROOT / ".env"
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    a, b = line.split("=", 1)
                    _ENV[a.strip()] = b.strip()
    return os.environ.get(k) or _ENV.get(k)


def groups_text():
    """Подписи 50 групп — из выжимки смотровой. Подписи пока НАШИ временные
    (super_names от ML не доехал); для промпта это терпимо: они система координат,
    а не словарь. Когда ML доименует группы — текст обновится сам."""
    d = json.loads(REVIEW.read_text(encoding="utf-8"))
    rows = sorted(d["groups"].items(), key=lambda kv: -kv[1]["n"])
    return "\n".join(f"- {v['label']}" for _, v in rows)


def article_text(aid, lang="en"):
    """Английский текст статьи. data.json лежит ТОЛЬКО в ru-дереве — внутри него
    срезы всех языков (d[tier][lang]); отдельных data.json у языков нет."""
    base = ROOT / "lang" / "ru" / "archive"
    hits = list(base.glob(f"*/{aid}/data.json")) or list(base.glob(f"*/{aid.split('v')[0]}*/data.json"))
    if not hits:
        return None, None
    d = json.loads(hits[0].read_text(encoding="utf-8"))
    v = (d.get("advanced", {}) or {}).get(lang) or (d.get("popular", {}) or {}).get(lang) or {}
    if not isinstance(v, dict):
        return None, None
    title = v.get("title") or ""
    body = " ".join(str(v.get(k) or "") for k in ("description", "abstract", "text"))
    return title, re.sub(r"\s+", " ", body)[:6000]


def build_prompt(aid):
    title, text = article_text(aid)
    if not title:
        return None
    return (PROMPT.read_text(encoding="utf-8")
            .replace("{kinds}", ", ".join(KINDS))
            .replace("{groups}", groups_text())
            .replace("{title}", title)
            .replace("{text}", text))


def parse_answer(raw):
    """Ответ модели → список кандидатов. Модель просили отвечать чистым JSON,
    но страховка от ```json-обёртки обязательна — это самый частый сбой."""
    m = re.search(r"\[.*\]", raw, re.S)
    if not m:
        return []
    try:
        items = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    out = []
    for it in items:
        # Дефисы и пробелы — в подчёркивания ДО чистки, иначе Stripe-Phase слипается
        # в stripephase и перестаёт совпадать с самим собой из другой статьи.
        name = re.sub(r"[\s\-]+", "_", str(it.get("name", "")).strip().lower())
        name = re.sub(r"[^a-z0-9_]", "", name).strip("_")
        if not name or len(name) > 60:
            continue
        out.append({
            "name": name,
            "kind": it.get("kind") if it.get("kind") in KINDS else "concept",
            "group": str(it.get("group") or "other")[:80],
            "scope": "general" if it.get("scope") == "general" else "specific",
            "line": str(it.get("line") or "")[:220],
        })
    return out


def load_harvest():
    rows = {}
    if HARVEST.exists():
        for line in HARVEST.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                rows[r["name"]] = r
    return rows


def save_harvest(rows):
    with HARVEST.open("w", encoding="utf-8") as fh:
        for r in sorted(rows.values(), key=lambda r: -len(r["articles"])):
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def ingest(aid, cands):
    rows = load_harvest()
    added = grown = 0
    for c in cands:
        r = rows.get(c["name"])
        if r:
            if aid not in r["articles"]:
                r["articles"].append(aid)
                grown += 1
        else:
            rows[c["name"]] = {**c, "articles": [aid], "matched": None}
            added += 1
    save_harvest(rows)
    ready = [r for r in rows.values()
             if not r.get("matched") and len(r["articles"]) >= ARTICLES_MIN]
    print(f"{aid}: новых кандидатов {added}, подросло {grown}; "
          f"в копилке {len(rows)}, доросло до понятия {len(ready)}")


def embed(texts):
    """Workers AI bge-m3 — ТОТ ЖЕ движок, каким считались карточки волны 5.
    Другой движок дал бы числа, которые не с чем сравнивать."""
    acc, tok = env("CLOUDFLARE_ACCOUNT_ID"), env("CLOUDFLARE_API_TOKEN")
    if not (acc and tok):
        raise SystemExit("нет CLOUDFLARE_ACCOUNT_ID/CLOUDFLARE_API_TOKEN в .env")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/@cf/baai/bge-m3"
    out = []
    for s in range(0, len(texts), 50):
        chunk = texts[s:s + 50]
        body = json.dumps({"text": chunk}).encode("utf-8")
        for attempt in range(5):
            req = urllib.request.Request(url, data=body, headers={
                "Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    d = json.loads(r.read().decode("utf-8"))
                v = (d.get("result") or {}).get("data")
                if v and len(v) == len(chunk):
                    out.extend(v)
                    break
                raise ValueError("ответ не по размеру")
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(2 ** attempt)
    return out


def match():
    """Кандидаты против карточек реестра. Совпал — это старое понятие, а не новое."""
    import numpy as np
    sys.path.insert(0, str(ML))
    import concepts_super as cs
    cids, CV = cs.load_cards()

    rows = load_harvest()
    todo = [r for r in rows.values() if r.get("matched") is None and not r.get("vec")]
    if todo:
        vecs = embed([f"{r['name'].replace('_', ' ')}: {r['line']}" for r in todo])
        for r, v in zip(todo, vecs):
            r["vec"] = [round(x, 5) for x in v]
    n_match = 0
    for r in rows.values():
        if r.get("matched") is not None or not r.get("vec"):
            continue
        v = np.asarray(r["vec"], dtype=np.float32)
        v /= np.linalg.norm(v) + 1e-9
        sims = CV @ v
        j = int(sims.argmax())
        if float(sims[j]) >= MATCH_T:
            r["matched"] = cids[j]
            r["matched_sim"] = round(float(sims[j]), 3)
            n_match += 1
    save_harvest(rows)
    new = [r for r in rows.values() if not r.get("matched")]
    ready = [r for r in new if len(r["articles"]) >= ARTICLES_MIN]
    print(f"кандидатов {len(rows)} · совпало со старым {n_match} · новых {len(new)} "
          f"· доросло (>= {ARTICLES_MIN} статей) {len(ready)}")
    for r in sorted(ready, key=lambda r: -len(r["articles"]))[:10]:
        print(f"   {len(r['articles']):>3} статей  {r['name']}  — {r['line'][:60]}")


def distill():
    """Слить кандидатов-дубли: разные статьи называют одно чуть разными словами."""
    import numpy as np
    rows = load_harvest()
    keyed = [(k, r) for k, r in rows.items() if r.get("vec") and not r.get("matched")]
    if len(keyed) < 2:
        print("дистиллировать нечего"); return
    V = np.asarray([r["vec"] for _, r in keyed], dtype=np.float32)
    V /= np.linalg.norm(V, axis=1, keepdims=True) + 1e-9
    S = V @ V.T
    gone = set()
    merged = 0
    for i in range(len(keyed)):
        if keyed[i][0] in gone:
            continue
        for j in range(i + 1, len(keyed)):
            if keyed[j][0] in gone or S[i, j] < DISTILL_T:
                continue
            a, b = keyed[i][1], keyed[j][1]
            # имя остаётся у того, кто набрал больше статей
            win, lose = (a, b) if len(a["articles"]) >= len(b["articles"]) else (b, a)
            win["articles"] = sorted(set(win["articles"]) | set(lose["articles"]))
            gone.add(lose["name"])
            merged += 1
    for k in gone:
        rows.pop(k, None)
    save_harvest(rows)
    print(f"слито дублей: {merged}, осталось кандидатов {len(rows)}")


def ask(ids):
    # Платный шаг — под общим замком, как любой прогон.
    try:
        from tools.freeze import guard
        guard("сбор понятий (DeepSeek)")
    except ImportError:
        pass
    key = env("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit("нет DEEPSEEK_API_KEY в .env")
    for aid in ids:
        p = build_prompt(aid)
        if not p:
            print(f"{aid}: нет английского текста"); continue
        body = json.dumps({
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": p}],
            "temperature": 0.2, "max_tokens": 1400,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.deepseek.com/chat/completions", data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as r:
            d = json.loads(r.read().decode("utf-8"))
        raw = d["choices"][0]["message"]["content"]
        cands = parse_answer(raw)
        if not cands:
            print(f"{aid}: ответ не разобрался — {raw[:120]!r}"); continue
        ingest(aid, cands)


def main():
    ap = argparse.ArgumentParser(description="Живой рост реестра понятий")
    ap.add_argument("--show", metavar="ID", help="собрать промпт, ничего не звать")
    ap.add_argument("--ask", nargs="+", metavar="ID", help="спросить модель (ПЛАТНО, под замком)")
    ap.add_argument("--ingest", metavar="FILE", help="разобрать сохранённый ответ: FILE = id.txt")
    ap.add_argument("--match", action="store_true", help="сверить кандидатов с реестром вектором")
    ap.add_argument("--distill", action="store_true", help="слить кандидатов-дубли")
    a = ap.parse_args()
    if a.show:
        p = build_prompt(a.show)
        print(p if p else "нет английского текста")
    elif a.ask:
        ask(a.ask)
    elif a.ingest:
        f = Path(a.ingest)
        ingest(f.stem, parse_answer(f.read_text(encoding="utf-8")))
    elif a.match:
        match()
    elif a.distill:
        distill()
    else:
        rows = load_harvest()
        new = [r for r in rows.values() if not r.get("matched")]
        ready = [r for r in new if len(r["articles"]) >= ARTICLES_MIN]
        print(f"копилка: {len(rows)} кандидатов · новых {len(new)} · доросло {len(ready)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
