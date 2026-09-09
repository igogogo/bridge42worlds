#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Снять с сайта индексы статей, которые там больше не нужны.

Владелец 09.09: «убери лишние индексы и почисти R2».

Что происходит. Пока поиск и лента жили на клиенте, браузер качал lang/<язык>/articles-index*.json.
01.09 всё это переехало в воркер, загрузчики из js убраны, а файлы продолжали уезжать: пять
языков × три уровня чтения = 209 МБ, которые не читает никто. Причина закрыта в deploy_r2.py
(_stale_index), этот скрипт убирает уже лежащее.

ОДИН ФАЙЛ ОСТАЁТСЯ: lang/ru/articles-index.json. Его читает сам воркер из R2 — сторож
публикации смотрит, жива ли выкладка и какая дата самая свежая, и по нему же считается
ежедневная сводка. Уберём — сторож будет ежечасно кричать «публикация сломана».

Локально файлы не трогаем: их читает сборка и разметка понятиями.

    python cloudflare/drop_stale_indexes.py            показать, что удалит
    B42_DEPLOY_OK=1 python cloudflare/drop_stale_indexes.py --apply
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

import deploy_r2 as D  # noqa: E402
from common import ALL_LANGS  # noqa: E402


def main():
    apply = "--apply" in sys.argv
    if apply and os.environ.get("B42_DEPLOY_OK") != "1":
        sys.exit("нужен B42_DEPLOY_OK=1 — правка сайта делается осознанно")

    keys = [f"lang/{lang}/{name}"
            for lang in ALL_LANGS
            for name in ("articles-index.json", "articles-index-simple.json",
                         "articles-index-advanced.json")
            if f"lang/{lang}/{name}" != D.KEEP_INDEX]
    # Сверяем со своим же правилом выкладки: если оно и этот список разойдутся, файл
    # вернётся следующей заливкой, и чистка окажется бессмысленной.
    bad = [k for k in keys if not D._stale_index(k)]
    if bad:
        sys.exit(f"эти ключи выкладка НЕ считает лишними, стоп: {bad}")

    mb = sum((ROOT / k).stat().st_size for k in keys if (ROOT / k).exists()) / 1048576
    print(f"к снятию: {len(keys)} файлов, ~{mb:.0f} МБ")
    print(f"остаётся на сайте: {D.KEEP_INDEX} (его читает воркер)")
    for k in keys:
        print("   ", k)
    if not apply:
        print("\nэто показ. Удалить: B42_DEPLOY_OK=1 python cloudflare/drop_stale_indexes.py --apply")
        return 0

    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or os.environ.get("R2_ACCOUNT_ID")
    bucket = os.environ.get("R2_BUCKET", "bridge42worlds-site")
    if not account:
        sys.exit("нет CLOUDFLARE_ACCOUNT_ID / R2_ACCOUNT_ID")
    if os.environ.get("R2_ACCESS_KEY_ID") and os.environ.get("R2_SECRET_ACCESS_KEY"):
        backend = D.S3Backend(account, bucket)
    elif os.environ.get("CLOUDFLARE_API_TOKEN"):
        backend = D.TokenBackend(account, bucket, os.environ["CLOUDFLARE_API_TOKEN"])
    else:
        sys.exit("нет ключей R2")
    backend.delete_many(keys)
    print(f"✅ снято с сайта: {len(keys)}")

    # Опись: без этого выкладка считает файлы уже залитыми и не заметит, что их нет.
    # Строки просто убираем — файлы теперь внутренние, их отпечатки нам не нужны.
    try:
        man = json.loads(D.MANIFEST.read_text(encoding="utf-8"))
        files = man.get("files", man)
        gone = [k for k in keys if k in files]
        for k in gone:
            files.pop(k, None)
        D.save_manifest(D.MANIFEST, man)
        print(f"опись: убрано записей {len(gone)}")
    except FileNotFoundError:
        print("описи нет — пропускаю")
    return 0


if __name__ == "__main__":
    sys.exit(main())
