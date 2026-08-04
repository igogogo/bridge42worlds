#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Смысловая привязка листьев дерева формул к стволу — рядом с символьной, не поверх.

ЗАЧЕМ. Символьная привязка (tools/formula_layer.py) считает пересечение букв, и на этом
врёт предсказуемо: второй закон Кеплера собрал 51 лист, потому что любая формула с r и t
липнет к нему. Та же болезнь, что была у тегов со списком в промпте — совпадение знаков
не есть смысловая опора.

ЧТО В ВЕКТОР. `meaning` + `latex`, именно в этом порядке. Сама формула для bge-m3
малочитаема: `\\frac{1}{2}[\\xi-\\sqrt{\\xi^2+\\eta^2}]` для модели почти шум. А человеческое
объяснение — обычный текст, и оно есть у каждой формулы. Latex добавлен вторым: если
объяснение куцее, символы хоть что-то дают.

ПРО ЯЗЫК. Правило проекта «вектор только из английского» здесь не нарушается: оно про то,
чтобы наши статьи и чужие абстракты жили в ОДНОМ сопоставимом пространстве. Здесь обе
стороны сравнения — русские объяснения формул, пространство одно по построению.

Пишет в ОТДЕЛЬНЫЙ файл. Символьную привязку не трогает: два способа сравниваются
на слепой выборке, а не заменяют друг друга по решению автора одного из них.

    python formula_tree_vec.py --build      # векторы + привязка
    python formula_tree_vec.py --blind 30   # выборка на проверку глазами
    python formula_tree_vec.py --branches   # спорные ветви: Кеплер, Гросс-Питаевский, Биркгоф
"""
import json, math, pathlib, random, sys, time, argparse, collections
import urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")
DATA = ROOT / "data"
MODEL = "@cf/baai/bge-m3"
BATCH = 20
SEED = 42


def load_env():
    env = {}
    for line in (MAIN / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def tree():
    p = DATA / "formula-tree.json"
    if not p.exists():
        p = MAIN / "data" / "formula-tree.json"
    return json.loads(p.read_text(encoding="utf-8"))


def formulas():
    p = DATA / "formulas.json"
    if not p.exists():
        p = MAIN / "data" / "formulas.json"
    return json.loads(p.read_text(encoding="utf-8"))


_LAWS = None


def laws_ru():
    global _LAWS
    if _LAWS is None:
        p = MAIN / "lang" / "ru" / "data" / "laws.json"
        _LAWS = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return _LAWS


def text_of(rec, trunk_rich=False):
    """Объяснение вперёд, формула следом — см. шапку про читаемость latex.

    ДЛЯ СТВОЛА берём НЕ только meaning формулы. Замер 2026-08-04: поле `meaning`
    у стволовых формул — это легенда обозначений («F — сила притяжения (Н), G —
    гравитационная постоянная…»), а не описание закона. Вектор от такого текста
    кодирует список переменных, и расширенное уравнение Фридмана не находит
    `friedmann_equations`, хотя тот стоит в стволе. Поэтому к стволу добавляем
    название закона и его описание из laws.json — то, ЧТО закон утверждает.
    """
    m = (rec.get("meaning") or "").strip()
    lx = (rec.get("latex") or "").strip()
    head = ""
    if trunk_rich:
        law = rec.get("law")
        obj = laws_ru().get(law) or {}
        head = " ".join(filter(None, [
            rec.get("law_name") or obj.get("name") or law or "",
            (obj.get("description") or "").strip(),
            (obj.get("how_it_works") or "").strip(),
        ]))
    return " ".join(f"{head} {m} {lx}".split())[:4000]


def embed(texts, acc, tok, tries=5):
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{MODEL}"
    body = json.dumps({"text": texts}).encode("utf-8")
    for a in range(tries):
        req = urllib.request.Request(url, data=body, headers={
            "Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read().decode("utf-8"))
            v = (d.get("result") or {}).get("data")
            if v and len(v) == len(texts):
                return v
            raise ValueError("ответ не по размеру")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503):
                time.sleep(2 ** a * 2); continue
            raise
        except Exception:
            if a == tries - 1:
                raise
            time.sleep(2 ** a * 2)
    raise RuntimeError("эмбеддинги не получены")


def nz(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def build():
    env = load_env()
    acc, tok = env["CLOUDFLARE_ACCOUNT_ID"], env["CLOUDFLARE_API_TOKEN"]
    t, f = tree(), formulas()
    trunk = [(k, v) for k, v in t["trunk"].items() if text_of(v, True).strip()]
    leaves = [(k, v) for k, v in f.items() if text_of(v).strip()]
    print(f"ствол {len(trunk)}, листьев {len(leaves)}")

    def vecs(items, label, rich=False):
        out = []
        for i in range(0, len(items), BATCH):
            ch = items[i:i + BATCH]
            vs = embed([text_of(v, rich) for _, v in ch], acc, tok)
            out.extend(nz(v) for v in vs)
            if (i // BATCH) % 10 == 0:
                print(f"  {label}: {min(i+BATCH, len(items))}/{len(items)}")
        return out

    tv = vecs(trunk, "ствол", rich=True)
    lv = vecs(leaves, "листья")

    attach = t.get("attach", {})
    res, dist = {}, collections.Counter()
    for (lk, _), v in zip(leaves, lv):
        best = max(((sum(a * b for a, b in zip(v, w)), i) for i, w in enumerate(tv)))
        cos, idx = best
        law = trunk[idx][1]["law"]
        res[lk] = {"law": law, "law_name": trunk[idx][1].get("law_name", ""),
                   "trunk": trunk[idx][0], "cos": round(cos, 4),
                   "sym_law": (attach.get(lk) or {}).get("law"),
                   "sym_how": (attach.get(lk) or {}).get("how")}
        dist[law] += 1

    out = DATA / "formula-tree-vec.json"
    out.write_text(json.dumps({"model": MODEL, "n_trunk": len(trunk), "n_leaves": len(leaves),
                               "leaves": res}, ensure_ascii=False), encoding="utf-8")
    agree = sum(1 for r in res.values() if r["sym_law"] and r["sym_law"] == r["law"])
    hadsym = sum(1 for r in res.values() if r["sym_law"])
    print(f"\nзаписано: {out}")
    print(f"совпало с символьной: {agree} из {hadsym} ({100*agree/max(1,hadsym):.1f}%)")
    print(f"сирот было {len(res)-hadsym}, теперь у всех есть смысловая ветвь")
    print("\nсамые населённые ветви ПО СМЫСЛУ:")
    for k, v in dist.most_common(10):
        print(f"  {v:>4}  {k}")


def load_res():
    p = DATA / "formula-tree-vec.json"
    if not p.exists():
        sys.exit("сначала --build")
    return json.loads(p.read_text(encoding="utf-8"))


def blind(n):
    res, f = load_res()["leaves"], formulas()
    rnd = random.Random(SEED)
    keys = rnd.sample(sorted(res), min(n, len(res)))
    for k in keys:
        r = res[k]
        rec = f.get(k, {})
        print(f"\n{(rec.get('latex') or k)[:80]}")
        print(f"  смысл : {(rec.get('meaning') or '')[:150]}")
        print(f"  символ: {r['sym_law'] or '— (сирота)'}  [{r['sym_how'] or '-'}]")
        print(f"  вектор: {r['law']}  cos={r['cos']}")


def branches():
    res = load_res()["leaves"]
    sym = collections.Counter(r["sym_law"] for r in res.values() if r["sym_law"])
    print(f"{'ветвь':<42} {'символы':>8} {'вектор':>7} {'осталось':>9}")
    for law, cnt in sym.most_common(12):
        vec = sum(1 for r in res.values() if r["law"] == law)
        kept = sum(1 for r in res.values() if r["sym_law"] == law and r["law"] == law)
        print(f"{law:<42} {cnt:>8} {vec:>7} {kept:>9}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--blind", type=int, default=0)
    ap.add_argument("--branches", action="store_true")
    a = ap.parse_args()
    if a.build: build()
    elif a.blind: blind(a.blind)
    elif a.branches: branches()
    else: ap.print_help()

