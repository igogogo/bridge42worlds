#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Приведение архива к лицензиям: класс в data.json и список ограниченных работ в KV.

ЧТО СЛУЧИЛОСЬ. С 18.08 классификатор (gen_arxiv.license_class) считал лицензию
arXiv non-exclusive-distrib «свободной» — рядом с CC BY. Она такой не является: право
распространять работу даётся одному arXiv, третьим лицам ничего сверх цитирования.
Под этой ошибкой на сайт ушли авторские рисунки 2 137 работ, обложки-копии рисунков
у 1 983 и дословный абстракт у всех 3 102 (владелец 02.09: «вопрос серьёзный, могут
закрыть сайт»).

ПОЧЕМУ БЕЗ ПЕРЕСБОРКИ. Сайт динамический: 32 тысячи страниц пересобирать не будем.
Воркер сам не отдаст то, чего нельзя, — по ключу lic:<id> в KV, тем же механизмом,
что снятые авторами работы (wd:). Этот инструмент готовит два входа для него:

  1. license_class в data.json — чтобы ЛЮБАЯ будущая сборка страницы уже знала класс
     (заслоны в generate.py, carousel_frames.py, make_thumbnails читают его);
  2. ключи в KV: lic:<id> = "analysis" | "analysis,cover" — второе значит, что обложка
     тоже чужая (побайтовая копия рисунка из PDF) и её тоже не отдавать.

Обложки, сделанные FLUX, — наши; их ключ не помечает, и воркер их отдаёт.

    python tools/license_fix.py --plan      посчитать, ничего не менять
    python tools/license_fix.py --apply     проставить класс и записать KV
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "cloudflare"))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

from gen_arxiv import license_class  # noqa: E402


def cover_is_copy(folder):
    """Обложка — побайтовая копия одного из авторских рисунков?"""
    ai = folder / "ai.jpg"
    if not ai.exists():
        return False
    h = hashlib.md5(ai.read_bytes()).hexdigest()
    return any(hashlib.md5(g.read_bytes()).hexdigest() == h
               for g in folder.glob("*.jpg") if g.stem.isdigit())


def scan():
    rows = []
    for p in ROOT.glob("lang/ru/archive/*/*/data.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        cls = license_class(d.get("license") or "")
        if cls != "analysis":
            continue
        f = p.parent
        rows.append({
            "id": d.get("id") or f.name, "path": p, "data": d,
            "stale": d.get("license_class") != "analysis",
            "figures": any(g.stem.isdigit() for g in f.glob("*.jpg")),
            # Обложка от FLUX помечена image_model — она наша. Без пометки сверяем байты.
            "cover_copy": (not d.get("image_model")) and cover_is_copy(f),
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    rows = scan()
    print(f"работ класса analysis: {len(rows)}")
    print(f"  без класса в data.json: {sum(r['stale'] for r in rows)}")
    print(f"  с рисунками из PDF:     {sum(r['figures'] for r in rows)}")
    print(f"  обложка — копия рисунка: {sum(r['cover_copy'] for r in rows)}")
    if not a.apply:
        print("\nизменить: --apply")
        return 0

    # 1) класс в data.json
    n = 0
    for r in rows:
        if r["stale"]:
            r["data"]["license_class"] = "analysis"
            r["path"].write_text(json.dumps(r["data"], ensure_ascii=False, indent=2),
                                 encoding="utf-8")
            n += 1
    print(f"\nlicense_class проставлен: {n}")

    # 2) ключи в KV — пачками по 10 000 (предел bulk-ручки), нам хватит одной
    from submissions_sync import kv
    s, base = kv()
    # Одна работа может лежать двумя папками (v1 и v2, или с версией и без): ключ у них
    # один, и KV отказывает на дубле с разными значениями. Сводим: чужая обложка хоть у
    # одной версии — помечаем ключ целиком; лучше не отдать свою, чем отдать чужую.
    merged = {}
    for r in rows:
        k = f"lic:{r['id'].split('v')[0]}"
        merged[k] = merged.get(k, False) or r["cover_copy"]
    pairs = [{"key": k, "value": "analysis,cover" if c else "analysis"} for k, c in merged.items()]
    # Ключ без версии: страница может быть v1, а ссылка прийти без v — воркер
    # сверяет по номеру работы, и ему нужен один ключ на все версии.
    resp = s.put(f"{base}/bulk", json=pairs, timeout=120).json()
    if not resp.get("success"):
        print("⛔ KV не принял:", str(resp.get("errors"))[:200])
        return 1
    print(f"KV: записано ключей lic:* — {len(pairs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
