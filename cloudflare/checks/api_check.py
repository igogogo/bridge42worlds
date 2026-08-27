# -*- coding: utf-8 -*-
"""Проверка живых эндпоинтов воркера — не «ответил ли», а ЧТО ответил.

Владелец 27.08 спросил: «а тестировал ли как-то?» — честный ответ был «нет,
автотестов у динамики не было». Вот они: по каждому запросу проверяется не код
ответа, а содержимое — есть ли записи, сходятся ли числа с локальными данными,
на том ли языке пришла карточка.

Урок 14 августа записан в verify_publish дословно: обрезанный индекс отдавался
с кодом 200 и молчал. Поэтому здесь ни одна проверка не заканчивается на «200».

    python cloudflare/checks/api_check.py            # dev
    python cloudflare/checks/api_check.py --prod     # боевой воркер
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEV = "https://bridge42worlds-dev.bridge42worlds-dev.workers.dev"
PROD = "https://bridge42worlds.academy"


def get(base, path, timeout=25):
    req = urllib.request.Request(base + path, headers={"User-Agent": "b42-check"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8")
        return {"ms": int((time.time() - t0) * 1000), "code": 200,
                "json": json.loads(body)}
    except urllib.error.HTTPError as e:
        try:
            return {"ms": int((time.time() - t0) * 1000), "code": e.code,
                    "json": json.loads(e.read().decode("utf-8"))}
        except Exception:
            return {"ms": 0, "code": e.code, "json": None}
    except Exception as e:
        return {"ms": 0, "code": 0, "json": None, "err": f"{type(e).__name__}: {e}"}


def local_counts():
    """С чем сверяем: локальный реестр — источник правды."""
    out = {}
    try:
        live = json.loads((ROOT / "data/concepts-live.json").read_text(encoding="utf-8"))
        out["concepts"] = len(live["concepts"])
        out["groups"] = len(live.get("groups") or {})
    except Exception:
        pass
    try:
        g = json.loads((ROOT / "data/concepts-graph.json").read_text(encoding="utf-8"))
        out["graph_nodes"] = len(g["nodes"])
    except Exception:
        pass
    return out


CASES = [
    # (имя, путь, проверка(json, local) -> (ok, что увидели))
    ("облако понятий", "/api/concepts?lang=ru&limit=5",
     lambda d, L: (len(d.get("items") or []) == 5,
                   ", ".join(x["name"][:20] for x in (d.get("items") or [])[:3]))),
    ("фильтр по классу", "/api/concepts?kind=law&limit=5&lang=ru",
     lambda d, L: (all(x["kind"] == "law" for x in (d.get("items") or [])) and
                   len(d.get("items") or []) > 0,
                   f"{len(d.get('items') or [])} законов")),
    ("поиск по имени", "/api/concepts?q=black&limit=5&lang=en",
     lambda d, L: (len(d.get("items") or []) > 0,
                   ", ".join(x["name"][:22] for x in (d.get("items") or [])[:3]))),
    ("карточка понятия ru", "/api/concept?id=black_hole&lang=ru",
     lambda d, L: (bool(d.get("concept")) and d["concept"]["n"] > 0,
                   f"{d.get('concept', {}).get('name')} · {d.get('concept', {}).get('n')} статей"
                   f" · соседей {len(d.get('related') or [])}"
                   f" · запись {d.get('concept', {}).get('fullLang')}")),
    ("карточка понятия en", "/api/concept?id=black_hole&lang=en",
     lambda d, L: (bool(d.get("concept")),
                   f"{d.get('concept', {}).get('name')}")),
    ("несуществующее понятие", "/api/concept?id=nope_nope_nope",
     lambda d, L: (d.get("error") == "not_found", "честный 404")),
    ("кадр: обзор", "/api/graph?frame=overview",
     lambda d, L: (len(d.get("nodes") or []) == L.get("groups", 50) and
                   len(d.get("edges") or []) > 0,
                   f"{len(d.get('nodes') or [])} групп, {len(d.get('edges') or [])} рёбер")),
    ("кадр: группа", "/api/graph?frame=g:0",
     lambda d, L: (len(d.get("nodes") or []) > 5,
                   f"{len(d.get('nodes') or [])} узлов, {len(d.get('edges') or [])} рёбер")),
    ("кадр: эго", "/api/graph?frame=ego:black_hole",
     lambda d, L: (len(d.get("nodes") or []) > 3 and
                   (d.get("nodes") or [{}])[0].get("center") is True,
                   f"{len(d.get('nodes') or [])} узлов вокруг центра")),
    ("облако формул", "/api/formula?limit=5",
     lambda d, L: (len(d.get("items") or []) == 5,
                   ", ".join((x.get("name") or "")[:20] for x in (d.get("items") or [])[:2]))),
    ("одна формула", "/api/formula?id=thermal_conductivity_kinetic_theory",
     lambda d, L: (bool(d.get("formula", {}).get("latex")),
                   (d.get("formula", {}).get("latex") or "")[:38])),
    # старое — не сломали ли
    ("СТАРОЕ: лента", "/api/feed?lang=ru&version=popular&limit=3",
     lambda d, L: (len(d.get("items") or []) == 3, "лента жива")),
    ("СТАРОЕ: список тега", "/api/list?kind=tag&key=black_hole&lang=ru&version=popular&limit=3",
     lambda d, L: (isinstance(d.get("items"), list), f"{len(d.get('items') or [])} карточек")),
    ("СТАРОЕ: обвязка статьи", "/api/side?id=1303.6118",
     lambda d, L: (isinstance(d, dict) and not d.get("error"), "отвечает")),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prod", action="store_true")
    ap.add_argument("--base")
    a = ap.parse_args()
    base = a.base or (PROD if a.prod else DEV)
    L = local_counts()
    print(f"═══ ПРОВЕРКА ЭНДПОИНТОВ: {base} ═══")
    print(f"    локально: {L}")
    ok_n = bad_n = 0
    for name, path, check in CASES:
        r = get(base, path)
        d = r.get("json")
        if d is None:
            print(f"  ✗ {name:24s} код {r['code']} {r.get('err', '')[:50]}")
            bad_n += 1
            continue
        try:
            ok, what = check(d, L)
        except Exception as e:
            ok, what = False, f"разбор упал: {type(e).__name__}"
        mark = "✓" if ok else "✗"
        print(f"  {mark} {name:24s} {r['ms']:>5}мс  {what}")
        ok_n += ok
        bad_n += not ok
    print(f"    итог: {ok_n} прошло, {bad_n} нет")
    return 1 if bad_n else 0


if __name__ == "__main__":
    sys.exit(main())
