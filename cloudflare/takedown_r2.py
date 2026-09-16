# -*- coding: utf-8 -*-
"""Снять работу с сайта по-настоящему: удалить её объекты из бакета.

ПОЧЕМУ ОТДЕЛЬНЫЙ ИНСТРУМЕНТ. `run.py delete` удаляет статью с диска и чистит индексы, а
следом зовёт обычную выкладку. Но выкладка ДОЗАЛИВАЕТ изменённое и ничего не удаляет:
ключ --prune выключен по умолчанию, и даже с ним он сверяется с описью, которую та же
выкладка уже перезаписала, — снятых файлов в описи больше нет, и удалять ему нечего.

Итог 16.09.2026: автор попросил снять свою работу («remove it from public access»), мы её
удалили — и страница продолжала отдаваться с кодом 200 на всех пяти языках. Обещание
«страница снимается в тот же день» осталось невыполненным, а выглядело выполненным: с
диска работа исчезла, из индекса тоже, лента её не показывала. Проверять надо было
ответом сервера, а не отсутствием папки.

Здесь удаление идёт по адресу и с перечислением: спрашиваем у хранилища всё, что лежит
под путями работы, и удаляем. Ключи хранилища те же, что у выкладки.

    python cloudflare/takedown_r2.py 2609.04078v1          показать, что удалит
    python cloudflare/takedown_r2.py 2609.04078v1 --apply  удалить
"""
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Доступы берём оттуда же, откуда выкладка: свой способ читать секреты — лишний способ
# их потерять или засветить.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

LANGS = ("ru", "en", "es", "ar", "fr")


def client():
    """Тот же доступ, которым пользуется выкладка. Иначе — внятный отказ, а не обход."""
    import boto3
    from botocore.config import Config
    acc = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or os.environ.get("R2_ACCOUNT_ID")
    key = os.environ.get("R2_ACCESS_KEY_ID")
    sec = os.environ.get("R2_SECRET_ACCESS_KEY")
    if not (acc and key and sec):
        raise SystemExit("⛔ нет доступов R2 в окружении (CLOUDFLARE_ACCOUNT_ID, "
                         "R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY)")
    return boto3.client(
        "s3", endpoint_url=f"https://{acc}.r2.cloudflarestorage.com",
        aws_access_key_id=key, aws_secret_access_key=sec,
        region_name="auto", config=Config(retries={"max_attempts": 5, "mode": "adaptive"})
    ), os.environ.get("R2_BUCKET", "bridge42worlds-site")


def find(s3, bucket, aid):
    """Все объекты работы во всех языках. Ищем перечислением: имена файлов у работы
    разные (уровни чтения, обложка, превью, api), и угадывать их нельзя."""
    keys = []
    for lang in LANGS:
        token = None
        while True:
            kw = {"Bucket": bucket, "Prefix": f"lang/{lang}/archive/", "MaxKeys": 1000}
            if token:
                kw["ContinuationToken"] = token
            r = s3.list_objects_v2(**kw)
            for o in r.get("Contents") or []:
                if f"/{aid}/" in o["Key"]:
                    keys.append(o["Key"])
            token = r.get("NextContinuationToken")
            if not token:
                break
    return sorted(set(keys))


def main():
    ap = argparse.ArgumentParser(description="Снять работу с сайта: удалить объекты из бакета")
    ap.add_argument("aid", help="номер работы, как в архиве (например 2609.04078v1)")
    ap.add_argument("--apply", action="store_true", help="удалить; без ключа — только показ")
    a = ap.parse_args()

    s3, bucket = client()
    print(f"ищу объекты работы {a.aid} в бакете {bucket} …")
    keys = find(s3, bucket, a.aid)
    print(f"найдено: {len(keys)}")
    for k in keys[:12]:
        print("   ", k)
    if len(keys) > 12:
        print(f"    … и ещё {len(keys) - 12}")
    if not keys:
        print("нечего удалять")
        return 0
    if not a.apply:
        print("\nэто показ. Удалить: --apply")
        return 0
    for i in range(0, len(keys), 1000):
        batch = keys[i:i + 1000]
        s3.delete_objects(Bucket=bucket, Delete={"Objects": [{"Key": k} for k in batch]})
    print(f"✅ удалено {len(keys)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
