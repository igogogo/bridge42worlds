"""Выгрузка баз D1 в приватный бакет R2 — единственное, что не пересобирается ничем.

Найдено репетицией восстановления 2026-08-05. Всё остальное на случай смерти машины у нас
закрыто: страницы лежат в R2, исходники статей — в резервной копии, индекс поиска и контекст
бота пересобираются из исходников. А в D1 живут вещи, которых больше нет нигде: очередь
работ, реакции и просмотры читателей, голоса совета. Их никакой генератор не восстановит —
это следы живых людей. До сегодняшнего дня их копии не существовало.

Выгружаем через API самой Cloudflare (POST .../export): она собирает дамп SQL и отдаёт
ссылку. Тянуть таблицы запросами не годится — дамп обязан быть согласованным, а не
собранным по кускам в разные моменты.

Держим ПОСЛЕДНИЕ 14 выгрузок посуточно. Не одну: беда «база испортилась» замечается не в
тот же час, и единственная свежая копия успела бы затереть здоровую.

    python cloudflare/backup_d1.py            # выгрузить все базы
    python cloudflare/backup_d1.py --list     # что уже лежит в копии
"""
import os, sys, time, argparse, datetime
from pathlib import Path
import requests
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
BUCKET = os.environ.get("R2_BACKUP_BUCKET", "bridge42worlds-backup")
KEEP = 14


def api():
    acc = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or os.environ.get("R2_ACCOUNT_ID")
    tok = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not (acc and tok):
        print("нет CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN — выгрузка D1 пропущена.")
        return None, None
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {tok}"
    return s, f"https://api.cloudflare.com/client/v4/accounts/{acc}/d1/database"


def s3():
    import boto3
    account = os.environ.get("R2_ACCOUNT_ID") or os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    return boto3.client(
        "s3", endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")


def export_one(sess, base, db):
    """Просит Cloudflare собрать дамп и ждёт ссылку. Отдаёт байты SQL."""
    r = sess.post(f"{base}/{db['uuid']}/export", timeout=60,
                  json={"output_format": "polling"}).json()
    if not r.get("success"):
        raise RuntimeError(f"{db['name']}: {r.get('errors')}")
    # Выгрузка асинхронная: опрашиваем тем же запросом с закладкой первого ответа.
    # Две ловушки этого API, обе стоили времени 2026-08-05:
    #   • `result` приходит буквальным null — `.get("result", {})` не спасает;
    #   • ссылка лежит НЕ в result, а в result.result, и только в ответе со
    #     статусом complete. Опрос после него отдаёт пустоту: работа уже забрана,
    #     и ссылку взять больше неоткуда — придётся заказывать выгрузку заново.
    bookmark = (r.get("result") or {}).get("at_bookmark")
    for _ in range(60):
        res = r.get("result") or {}
        url = (res.get("result") or {}).get("signed_url")
        if url:
            return requests.get(url, timeout=300).content
        time.sleep(2)
        r = sess.post(f"{base}/{db['uuid']}/export", timeout=60,
                      json={"output_format": "polling",
                            "current_bookmark": bookmark}).json()
    raise TimeoutError(f"{db['name']}: Cloudflare не отдала ссылку за две минуты")


def prune(cl, prefix):
    """Оставляем KEEP свежих выгрузок. Старые не жалко: они про мир, которого уже нет."""
    keys = []
    for page in cl.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=prefix):
        keys += [o["Key"] for o in page.get("Contents", [])]
    old = sorted(keys)[:-KEEP]
    if old:
        cl.delete_objects(Bucket=BUCKET, Delete={"Objects": [{"Key": k} for k in old]})
        print(f"  убрано старых выгрузок: {len(old)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="показать, что уже лежит в копии")
    a = ap.parse_args()

    sess, base = api()
    if not sess:
        return 1
    cl = s3()

    if a.list:
        for page in cl.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix="d1/"):
            for o in page.get("Contents", []):
                print(f"{o['Key']:50} {o['Size'] / 1024:8.0f} КБ  {o['LastModified']:%Y-%m-%d %H:%M}")
        return 0

    dbs = sess.get(base, timeout=60).json().get("result", [])
    if not dbs:
        print("баз D1 не найдено — это подозрительно, проверьте права токена.")
        return 1
    day = datetime.date.today().isoformat()
    for db in dbs:
        try:
            blob = export_one(sess, base, db)
        except Exception as e:
            print(f"⚠️  {db['name']}: не выгрузилась — {e}")
            return 1
        key = f"d1/{db['name']}/{day}.sql"
        cl.put_object(Bucket=BUCKET, Key=key, Body=blob, ContentType="application/sql")
        print(f"✅ {db['name']}: {len(blob) / 1024:.0f} КБ → {key}")
        prune(cl, f"d1/{db['name']}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
