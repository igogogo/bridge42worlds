"""Разовый перенос реакций и откликов из Supabase в наш D1.

Зачем. Ключ Supabase лежал открытым в `js/likes.js`: любой, кто открыл исходник страницы,
мог писать в нашу базу напрямую. Теперь у нас есть своя база и свой счётчик — держать ради
одиннадцати строк чужой сервис незачем.

Что переносим и что нет:
  • likes (11) и feedback (11) → в D1. Это живые следы читателей, восстановить их неоткуда.
  • views (21 158) → НЕ в D1, а архивом в приватный бакет. Просмотры заменил наш счётчик
    (`/api/ev`), и схема у него другая: uid/sid/путь против entity_id/source/device. Влить
    старое в новое значило бы получить статистику, в которой ничего не сходится. Но и стереть
    нельзя — это год живой истории, пусть лежит файлом.

Запуск (разово):
    python cloudflare/migrate_supabase.py            # показать, что будет
    python cloudflare/migrate_supabase.py --apply    # перенести
"""
import os, re, sys, json, time, argparse
from pathlib import Path
import requests
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
DB_ID = os.environ.get("D1_QUEUE_ID", "44ca0737-e27f-4cb5-bac8-9b132c935e4d")
BACKUP_BUCKET = os.environ.get("R2_BACKUP_BUCKET", "bridge42worlds-backup")


def supabase():
    """Ключ берём из клиента — он там и так открыт всему миру, в этом и была беда."""
    src = (ROOT / "js" / "likes.js").read_text(encoding="utf-8")
    url = re.search(r"SUPABASE_URL\s*=\s*'([^']+)'", src)
    key = re.search(r"SUPABASE_KEY\s*=\s*'([^']+)'", src)
    if not (url and key):
        raise RuntimeError("в js/likes.js больше нет доступов Supabase — перенос уже сделан?")
    return url.group(1), key.group(1)


def fetch_all(url, key, table, page=1000):
    H = {"apikey": key, "Authorization": f"Bearer {key}"}
    out, offset = [], 0
    while True:
        r = requests.get(f"{url}/rest/v1/{table}", headers={**H, "Range": f"{offset}-{offset+page-1}"},
                         params={"select": "*"}, timeout=90)
        r.raise_for_status()
        chunk = r.json()
        out.extend(chunk)
        if len(chunk) < page:
            return out
        offset += page


def d1(sql, params=None):
    acc = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    r = requests.post(
        f"https://api.cloudflare.com/client/v4/accounts/{acc}/d1/database/{DB_ID}/query",
        headers={"Authorization": f"Bearer {os.environ['CLOUDFLARE_API_TOKEN']}",
                 "Content-Type": "application/json"},
        json={"sql": sql, "params": params or []}, timeout=90)
    d = r.json()
    if not d.get("success"):
        raise RuntimeError(f"D1: {d.get('errors')}")
    return d["result"][0].get("results", [])


def ms(value):
    """Время из Supabase (ISO) в миллисекунды. Нет времени — ставим ноль, а не сегодняшнее:
    выдуманная дата хуже отсутствующей, по ней потом сделают неверный вывод."""
    if not value:
        return 0
    try:
        from datetime import datetime
        return int(datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp() * 1000)
    except Exception:
        return 0


def archive_views(rows):
    """Просмотры — в приватный бакет одним файлом. Дёшево и переживает нас."""
    import boto3
    body = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows).encode("utf-8")
    s3 = boto3.client(
        "s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
    key = f"archive/supabase-views-{time.strftime('%Y-%m-%d')}.jsonl"
    s3.put_object(Bucket=BACKUP_BUCKET, Key=key, Body=body, ContentType="application/x-ndjson")
    return key, len(body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="перенести (без флага — только показать)")
    a = ap.parse_args()

    url, key = supabase()
    likes = fetch_all(url, key, "likes")
    feedback = fetch_all(url, key, "feedback")
    views = fetch_all(url, key, "views")
    print(f"в Supabase: реакций {len(likes)}, откликов {len(feedback)}, просмотров {len(views)}")

    if not a.apply:
        print("\nпробный проход. Что сделал бы:")
        print(f"  • перенёс в D1 {len(likes)} реакций и {len(feedback)} откликов")
        print(f"  • сложил {len(views)} просмотров архивом в бакет {BACKUP_BUCKET}")
        print("\nповторить с --apply")
        return 0

    for r in likes:
        d1("""INSERT INTO reactions (article_id, reaction, entity_type, uid, ts)
              VALUES (?, ?, ?, '', ?)""",
           [str(r.get("article_id") or ""), str(r.get("reaction") or ""),
            str(r.get("entity_type") or "article"), ms(r.get("created_at"))])
    print(f"перенесено реакций: {len(likes)}")

    for r in feedback:
        opts = r.get("options")
        d1("""INSERT INTO article_feedback (article_id, options, comment, entity_type, lang, ts)
              VALUES (?, ?, ?, ?, '', ?)""",
           [str(r.get("article_id") or ""),
            json.dumps(opts, ensure_ascii=False) if opts else None,
            r.get("comment"), str(r.get("entity_type") or "article"), ms(r.get("created_at"))])
    print(f"перенесено откликов: {len(feedback)}")

    if views:
        k, size = archive_views(views)
        print(f"просмотры сложены архивом: {k} ({size // 1024} КБ)")

    print("\n✅ перенос завершён. Supabase можно отключать — но сначала убедитесь,")
    print("   что новые ручки работают и js/likes.js уже без его ключа.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
