#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ТЕМА как объект проекта — наравне со статьёй, понятием, законом и учёным.

Владелец 03.09: «поскольку мы взяли тематику, таких тематик много будет; допустим, пусть
тематика тоже станет нашим объектом».

ЧТО ТАКОЕ ТЕМА. Не папка и не тег, а собранный вокруг вопроса кусок работы:
  · вопрос, на который тема отвечает, и почему он стоит труда;
  · ОТБОР: как из трёх миллионов работ arXiv выбираются её работы — слова дают кандидатов,
    вектор решает, что из них действительно про это (порог считается, а не выдумывается);
  · РАЗБОР: те же наши правила, что у ленты, кусками, с ожиданием дешёвого окна;
  · СВЯЗИ: контекстные ссылки от утверждений темы к разобранным работам (tools/enso/links.py);
  · ЛИЦО: страница. У живой темы это панель с данными (Эль-Ниньо), у обычной — сводка.

ПОЧЕМУ ЭТО ОДИН ФАЙЛ НА ТЕМУ. Тема должна переживать сессию и человека: в data/topics/
лежит всё, что нужно, чтобы повторить отбор и разбор через месяц и получить то же самое.
Никаких «я помню, какими словами мы это искали».

    python tools/topics.py list                     что у нас есть и в каком состоянии
    python tools/topics.py new <slug> --title ...   завести тему
    python tools/topics.py select <slug>            отобрать работы (слова → вектор)
    python tools/topics.py select <slug> --dry      посмотреть, ничего не записывая
    python tools/topics.py run <slug> [--limit N]   разобрать отобранное
    python tools/topics.py status <slug>            подробно по одной теме
"""
import argparse
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOPICS = ROOT / "data" / "topics"
FIELD_DB = ROOT / "data" / "arxiv-field.sqlite"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

CHUNK = 8               # столько работ уходит в один вызов run.py ids
FLOOR = 0.50            # пол по косинусу к семени темы; bge-m3 лежит узко, см. vector-direct-access
CAND = 600              # сколько кандидатов на запрос берут слова, прежде чем решает вектор


# ---------------------------------------------------------------- файл темы
def path_of(slug):
    return TOPICS / f"{slug}.json"


def load(slug):
    p = path_of(slug)
    if not p.exists():
        sys.exit(f"нет темы {slug}: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def save(t):
    TOPICS.mkdir(parents=True, exist_ok=True)
    path_of(t["slug"]).write_text(json.dumps(t, ensure_ascii=False, indent=2), encoding="utf-8")


def data_dir(t):
    d = ROOT / (t.get("data") or f"data/topics/{t['slug']}")
    d.mkdir(parents=True, exist_ok=True)
    return d


def works_file(t, tier):
    named = (t.get("works") or {}).get(f"tier{tier}")
    return ROOT / named if named else data_dir(t) / f"works-tier{tier}.txt"


def read_ids(p):
    if not Path(p).exists():
        return []
    return [l.strip() for l in Path(p).read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]


def parsed_ids():
    """Что уже разобрано: номера работ без версии."""
    return {p.parent.name.split("v")[0]
            for p in ROOT.glob("lang/ru/archive/*/*/advanced.html")}


# ---------------------------------------------------------------- отбор
def fts_candidates(queries, limit=CAND):
    """Слова: грубая сеть по 3 млн аннотаций, локально и бесплатно."""
    if not FIELD_DB.exists():
        sys.exit(f"нет поля arXiv: {FIELD_DB} (tools/field.py build)")
    con = sqlite3.connect(FIELD_DB)
    out = {}
    for q in queries:
        try:
            rows = con.execute(
                "select d.aid, d.mon, bm25(fts) from fts join doc d on d.rowid = fts.rowid "
                "where fts match ? order by bm25(fts) limit ?", (q, limit)).fetchall()
        except sqlite3.OperationalError as e:
            print(f"  ⚠️ запрос отвергнут ({e}): {q[:60]}")
            continue
        for aid, mon, score in rows:
            base = aid.split("v")[0]
            if base not in out:
                out[base] = {"aid": aid, "mon": mon, "fts": round(score, 2)}
    con.close()
    return out


def rank_by_vector(seed, cands, cache):
    """Вектор: из кандидатов оставляем те, что действительно про эту тему.

    Слова ловят по совпадению букв и тащат чужое (сезонный прогноз урожая и сезонный
    прогноз океана делят половину словаря). Семя темы — одно предложение о том, что мы
    ищем; косинус к нему и решает."""
    sys.path.insert(0, str(ROOT / "tools"))
    import field as FLD
    from embeddings_build import embed_cached, load_env
    import numpy as np

    key = load_env(ROOT).get("DEEPINFRA_API_KEY", "")
    if not key:
        sys.exit("нет DEEPINFRA_API_KEY в .env — вектор не посчитать")
    pairs = [(c["aid"], c["mon"]) for c in cands.values()]
    got = FLD._abstracts(pairs)
    texts, keys = [], []
    for base, c in cands.items():
        g = got.get(c["aid"]) or got.get(base)
        if not g:
            continue
        texts.append(" ".join((g[0] + ". " + g[1]).split())[:2400])
        keys.append(base)
    if not texts:
        return []
    m = np.asarray(embed_cached(texts, key, cache, "работы темы", agent="topics"), dtype=np.float32)
    m /= np.linalg.norm(m, axis=1, keepdims=True) + 1e-9
    s = np.asarray(embed_cached([seed], key, cache, "семя темы", agent="topics"), dtype=np.float32)
    s /= np.linalg.norm(s, axis=1, keepdims=True) + 1e-9
    sim = (m @ s[0]).tolist()
    rows = []
    for base, score in zip(keys, sim):
        c = cands[base]
        rows.append({"id": c["aid"], "mon": c["mon"], "score": round(float(score), 3)})
    rows.sort(key=lambda r: -r["score"])
    return rows


def cmd_select(a):
    t = load(a.slug)
    sel = t.get("select") or {}
    queries = [q["fts"] for q in sel.get("queries") or []]
    if not queries:
        sys.exit("у темы нет запросов в select.queries")
    print(f"тема «{t['title']}»: запросов {len(queries)}")
    cands = fts_candidates(queries)
    print(f"слова дали кандидатов: {len(cands)}")
    rows = rank_by_vector(sel["seed"], cands, data_dir(t) / "select-cache.jsonl")
    floor = sel.get("floor", FLOOR)
    keep = [r for r in rows if r["score"] >= floor]
    caps = sel.get("caps") or {}
    t1 = keep[:caps.get("tier1", 300)]
    t2 = keep[len(t1):len(t1) + caps.get("tier2", 300)]
    have = parsed_ids()
    print(f"выше порога {floor}: {len(keep)} из {len(rows)}; "
          f"первый ярус {len(t1)} (уже разобрано {sum(1 for r in t1 if r['id'].split('v')[0] in have)}), "
          f"второй {len(t2)}")
    print("верхние по смыслу:")
    for r in rows[:8]:
        print(f"   {r['score']:.3f}  {r['id']}  {r['mon']}")
    if a.dry:
        return 0
    for tier, rowset in ((1, t1), (2, t2)):
        p = works_file(t, tier)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"# {t['title']} · ярус {tier} · отобрано {datetime.now():%Y-%m-%d %H:%M} "
                     f"· порог {floor}\n" + "\n".join(r["id"] for r in rowset) + "\n",
                     encoding="utf-8")
        print(f"записано: {p.relative_to(ROOT)} ({len(rowset)})")
    t.setdefault("state", {})["selected"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    t["state"]["n_tier1"], t["state"]["n_tier2"] = len(t1), len(t2)
    save(t)
    return 0


# ---------------------------------------------------------------- разбор
def wait_window(now):
    from common import deepseek_peak_status
    while True:
        peak, hrs = deepseek_peak_status()
        if now or not peak:
            return
        print(f"⏸ пик DeepSeek (x2) — жду {hrs:.1f} ч")
        time.sleep(min(1800, max(60, int(hrs * 3600))))


def needs_reco(aid):
    """У работы ещё нет раздела машины знаний?"""
    p = next(ROOT.glob(f"lang/ru/archive/*/{aid}*/data.json"), None)
    if not p:
        return False
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:                                        # noqa: BLE001
        return False
    return not (d.get("recommend") or {}).get("ru") and not d.get("express")


def post(t, ids, say, env):
    """Пост-шаги ровно по работам темы: разметка, понятия, формулы, машина знаний.

    Общий `run.py ids` без --no-post зовёт recommend --all-full — очередь по всему архиву;
    для темы это не то. Здесь те же шаги, но машина знаний идёт поимённо по её работам."""
    for title, cmd in (("разметка вектором", [sys.executable, "tools/tag_by_vector.py", "--apply"]),
                       ("понятия в тексте", [sys.executable, "tools/highlight_concepts.py"]),
                       ("формулы", [sys.executable, "tools/fix_inline_math.py"])):
        say(f"· {title}")
        subprocess.run(cmd, cwd=str(ROOT), env=env)
    todo = [i for i in ids if needs_reco(i.split("v")[0])]
    say(f"· машина знаний: {len(todo)} работ")
    for n, aid in enumerate(todo, 1):
        rc = subprocess.run([sys.executable, "tools/recommend.py", aid],
                            cwd=str(ROOT), env=env).returncode
        if rc:
            say(f"  ⚠️ {aid}: машина знаний вернула код {rc}")
        if n % 10 == 0:
            say(f"  машина знаний: {n}/{len(todo)}")


def cmd_run(a):
    t = load(a.slug)
    ids = read_ids(works_file(t, a.tier))
    have = parsed_ids()
    todo = [i for i in ids if i.split("v")[0] not in have]
    log = data_dir(t) / "works-log.txt"
    n_have = len(ids) - len(todo)
    if a.limit:
        todo = todo[:a.limit]

    def say(msg):
        line = f"{datetime.now():%Y-%m-%d %H:%M} {msg}"
        print(line)
        with log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    langs = a.lang or t.get("lang") or "all"
    say(f"▶ {t['slug']} ярус {a.tier}: в списке {len(ids)}, уже есть {n_have}, "
        f"к разбору {len(todo)}, языки " + ("все" if langs == "all" else "ru+" + langs))
    if not todo:
        return 0
    import runlock
    runlock.acquire("tree", f"topic {t['slug']}")
    env = dict(os.environ, B42_RUN_ORIGIN="manual", PYTHONIOENCODING="utf-8")
    chunks = [todo[i:i + CHUNK] for i in range(0, len(todo), CHUNK)]
    try:
        for n, ch in enumerate(chunks, 1):
            wait_window(a.now)
            # Языки: по умолчанию как везде на сайте — русский плюс все переводы (владелец
            # 03.09). Английский только у панели дашборда; сузить можно флагом --lang.
            # ВСЕГДА --no-post: общий пост-шаг зовёт recommend --all-full, а это очередь по
            # ВСЕМУ архиву, не по теме. Свои шаги делаем сами после всех кусков — там же и
            # машина знаний, по каждой работе темы поимённо (владелец 03.09: «всё делать
            # полностью, с разбором машиной знаний»).
            cmd = [sys.executable, "run.py", "ids", *ch, "--allow-restricted", "--no-post"]
            if langs != "all":
                cmd += ["--lang", langs]
            say(f"кусок {n}/{len(chunks)}: {' '.join(ch)}")
            t0 = time.time()
            rc = subprocess.run(cmd, cwd=str(ROOT), env=env).returncode
            done = sum(1 for i in ch if i.split("v")[0] in parsed_ids())
            say(f"  кусок {n}: код {rc}, готово {done}/{len(ch)}, {int(time.time() - t0)} с")
        if not a.no_post:
            post(t, todo, say, env)
    finally:
        runlock.release("tree")
    have = parsed_ids()
    say(f"■ конец: разобрано {sum(1 for i in ids if i.split('v')[0] in have)}/{len(ids)}")
    t.setdefault("state", {})["parsed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save(t)
    return 0


# ---------------------------------------------------------------- обзор
def summary(t):
    have = parsed_ids()
    out = {"slug": t["slug"], "title": t["title"], "kind": t.get("kind", "digest"),
           "page": t.get("page") or f"/topic.html?t={t['slug']}"}
    for tier in (1, 2):
        ids = read_ids(works_file(t, tier))
        out[f"tier{tier}"] = (len(ids), sum(1 for i in ids if i.split("v")[0] in have))
    lk = ROOT / (t.get("links") or f"data/topics/{t['slug']}/links.json")
    out["links"] = 0
    if lk.exists():
        try:
            out["links"] = len(json.loads(lk.read_text(encoding="utf-8")).get("anchors") or {})
        except Exception:                                    # noqa: BLE001
            pass
    out["state"] = t.get("state") or {}
    return out


def cmd_list(a):
    rows = [summary(json.loads(p.read_text(encoding="utf-8")))
            for p in sorted(TOPICS.glob("*.json"))]
    if not rows:
        print("тем пока нет: python tools/topics.py new <slug> --title ... --seed ...")
        return 0
    print(f"{'тема':22s} {'вид':7s} {'ярус 1':>14s} {'ярус 2':>14s} {'связей':>7s}  страница")
    for r in rows:
        print(f"{r['slug']:22s} {r['kind']:7s} "
              f"{r['tier1'][1]:>6}/{r['tier1'][0]:<7} {r['tier2'][1]:>6}/{r['tier2'][0]:<7} "
              f"{r['links']:>7}  {r['page']}")
    return 0


def cmd_status(a):
    t = load(a.slug)
    s = summary(t)
    print(json.dumps({**s, "question": t.get("question"), "select": t.get("select")},
                     ensure_ascii=False, indent=1))
    return 0


def cmd_new(a):
    if path_of(a.slug).exists() and not a.force:
        sys.exit(f"тема {a.slug} уже есть; --force чтобы переписать")
    t = {"slug": a.slug, "title": a.title, "question": a.question or "",
         "kind": a.kind, "created": datetime.now().strftime("%Y-%m-%d"),
         "lang": a.lang, "page": a.page or f"/topic.html?t={a.slug}",
         "data": f"data/topics/{a.slug}",
         "select": {"seed": a.seed, "queries": [], "floor": FLOOR,
                    "caps": {"tier1": a.cap1, "tier2": a.cap2}},
         "state": {}}
    save(t)
    print(f"заведена тема {a.slug}: {path_of(a.slug).relative_to(ROOT)}")
    print("дальше: впиши запросы в select.queries (список {\"tier\":1,\"fts\":\"…\"}) и запусти select")
    return 0


def cmd_daily(a):
    """Ежедневный прогон идёт ПО ТЕМЕ, а не по ленте (владелец 03.09: «вместо дневного
    прогона прогон пойдёт по ней»). Тема с флагом daily одна; сколько брать за день —
    в её daily_limit."""
    picked = None
    for p in sorted(TOPICS.glob("*.json")):
        t = json.loads(p.read_text(encoding="utf-8"))
        if t.get("daily"):
            picked = t
            break
    if not picked:
        print("ни одна тема не помечена daily — дневной прогон нечем занять")
        return 1
    a.slug = picked["slug"]
    a.tier = a.tier or 1
    a.limit = a.limit or picked.get("daily_limit") or 25
    ids = read_ids(works_file(picked, 1))
    have = parsed_ids()
    left1 = [i for i in ids if i.split("v")[0] not in have]
    if not left1:                                            # первый ярус кончился — идём во второй
        a.tier = 2
    print(f"дневной прогон по теме {picked['slug']}, ярус {a.tier}, до {a.limit} работ")
    return cmd_run(a)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("list", help="все темы и их состояние")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("status", help="одна тема подробно")
    s.add_argument("slug")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("new", help="завести тему")
    s.add_argument("slug")
    s.add_argument("--title", required=True)
    s.add_argument("--seed", required=True, help="одно-два предложения о том, что ищем")
    s.add_argument("--question", default="")
    s.add_argument("--kind", default="digest", choices=("digest", "live"))
    s.add_argument("--lang", default="all", help="all — русский и все переводы, как везде")
    s.add_argument("--page", default="")
    s.add_argument("--cap1", type=int, default=300)
    s.add_argument("--cap2", type=int, default=300)
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_new)

    s = sub.add_parser("select", help="отобрать работы: слова → вектор")
    s.add_argument("slug")
    s.add_argument("--dry", action="store_true")
    s.set_defaults(func=cmd_select)

    s = sub.add_parser("daily", help="дневной прогон по теме, помеченной daily")
    s.add_argument("--limit", type=int)
    s.add_argument("--tier", type=int, default=0)
    s.add_argument("--lang", default="")
    s.add_argument("--now", action="store_true")
    s.add_argument("--no-post", action="store_true")
    s.set_defaults(func=cmd_daily)

    s = sub.add_parser("run", help="разобрать отобранное")
    s.add_argument("slug")
    s.add_argument("--tier", type=int, default=1)
    s.add_argument("--limit", type=int)
    s.add_argument("--lang", default="", help="пусто — как записано у темы; all — все языки")
    s.add_argument("--now", action="store_true", help="не ждать дешёвого окна")
    s.add_argument("--no-post", action="store_true")
    s.set_defaults(func=cmd_run)

    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
