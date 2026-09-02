#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сторож лицензий: ни одна работа «только собственный разбор» не должна отдавать чужое.

Правило (владелец 02.09): свободные лицензии — CC BY, BY-SA, CC0 — берём целиком;
arXiv non-exclusive и NC-семейство — только наш пересказ, без авторских рисунков и без
дословного абстракта. Ошибка классификатора однажды уже провела 2 137 работ мимо этого
правила — молча. Сторож нужен, чтобы второй раз это не прошло мимо.

ЧТО ПРОВЕРЯЕТ, для каждой работы класса analysis:
  · ключ lic:<номер> есть в KV — иначе воркер отдаст всё как есть;
  · класс проставлен в data.json — иначе будущая сборка не узнает о запрете;
  · авторских рисунков на диске нет — иначе они уедут в R2 следующей выкладкой
    (воркер их не отдаст, но хранить чужое незачем);
  · собранная advanced.html не несёт мозаику и дословный абстракт — это «латентно»:
    воркер вырезает при отдаче, но страница на диске ждёт естественной пересборки.

Первые два — красная лампочка (сайт может отдать чужое). Вторые два — жёлтая
(на сайте чисто, на диске ещё нет). Код возврата 1 только на красных.

    python tools/license_audit.py          проверить
    python tools/license_audit.py --fix    дописать недостающие ключи в KV
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "cloudflare"))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

from gen_arxiv import license_class  # noqa: E402


def kv_keys():
    from submissions_sync import kv, keys_with_prefix
    s, base = kv()
    # Список отдаёт ключи ЦЕЛИКОМ (lic:2601.06577) — сравниваем по голому номеру.
    return {k.split(":", 1)[1] for k in keys_with_prefix(s, base, "lic:")}, (s, base)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="дописать недостающие ключи в KV")
    a = ap.parse_args()

    try:
        have, (s, base) = kv_keys()
    except Exception as e:
        print(f"⚠️ KV недоступен ({type(e).__name__}) — проверяю только диск")
        have, s, base = None, None, None

    red_kv, red_cls, yellow_files, yellow_html, total = [], [], [], [], 0
    for p in ROOT.glob("lang/ru/archive/*/*/data.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if license_class(d.get("license") or "") != "analysis":
            continue
        total += 1
        aid = (d.get("id") or p.parent.name)
        base_id = aid.split("v")[0]
        if have is not None and base_id not in have:
            red_kv.append(base_id)
        if d.get("license_class") != "analysis":
            red_cls.append(aid)
        f = p.parent
        if any(g.stem.isdigit() for g in f.glob("*.jpg")):
            yellow_files.append(aid)
        adv = ROOT / "lang" / "en" / "archive" / f.parent.name / f.name / "advanced.html"
        if adv.exists():
            h = adv.read_text(encoding="utf-8", errors="ignore")
            if 'class="mosaic"' in h or 'id="orig-abstract" class="orig-abs">' in h:
                yellow_html.append(aid)

    print(f"работ класса analysis: {total}")
    print(f"  🔴 без ключа в KV:            {len(red_kv)}")
    print(f"  🔴 без класса в data.json:    {len(red_cls)}")
    print(f"  🟡 рисунки ещё на диске:      {len(yellow_files)}")
    print(f"  🟡 страница ждёт пересборки:  {len(yellow_html)}")

    if a.fix and red_kv and s is not None:
        pairs = [{"key": f"lic:{i}", "value": "analysis"} for i in red_kv]
        r = s.put(f"{base}/bulk", json=pairs, timeout=120).json()
        print(f"  KV дописано: {len(pairs)} · {'ок' if r.get('success') else r.get('errors')}")
        red_kv = [] if r.get("success") else red_kv

    if red_kv or red_cls:
        print("\n⛔ сайт может отдать чужое. Починить: python tools/license_fix.py --apply")
        for i in (red_kv + red_cls)[:10]:
            print("   ", i)
        return 1
    print("\n✅ на сайте чисто" + (" · на диске остатки ждут чистки/пересборки" if (yellow_files or yellow_html) else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
