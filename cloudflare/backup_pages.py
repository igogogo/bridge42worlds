"""Резервная копия ПЕРЕВОДОВ — страниц на четырёх языках, кроме русского.

Почему это отдельная копия, а не «ну сайт же лежит в R2». Исходник статьи существует
только по-русски: `data.json`. Английский, испанский, арабский и французский нигде не
хранятся как текст — они живут собранными страницами, и больше их нет. То есть бакет
сайта был не витриной, а единственным экземпляром того, за что заплачено модели.
Найдено репетицией восстановления 2026-08-05, решение владельца задачи — копировать.

Русские страницы сюда НЕ кладём сознательно: они пересобираются из `data.json`, который
уже в копии. Это часы работы генератора, но не потеря денег. Копируем только то, чего
нельзя получить заново, не заплатив.

Жмём gzip перед отправкой: страницы — это HTML, у них девять десятых объёма повторяются
от файла к файлу. 2,1 ГБ превращаются в ~600 МБ, и вся резервная копия остаётся внутри
бесплатных 10 ГБ R2. Разжимать при восстановлении умеет restore_r2.py.

    python cloudflare/backup_pages.py            # дельта по md5
    python cloudflare/backup_pages.py --plan     # только посчитать
"""
import os, sys, gzip, json, hashlib, argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
MANIFEST = ROOT / "cloudflare" / ".pages-manifest.json"
BUCKET = os.environ.get("R2_BACKUP_BUCKET", "bridge42worlds-backup")
LANGS = ("en", "es", "ar", "fr")
PREFIX = "pages"


def iter_pages():
    for lang in LANGS:
        d = ROOT / "lang" / lang
        if d.exists():
            yield from (p for p in d.rglob("*.html"))


def md5(p):
    h = hashlib.md5()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def client():
    import boto3
    from botocore.config import Config
    account = os.environ.get("R2_ACCOUNT_ID") or os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    if not (account and os.environ.get("R2_ACCESS_KEY_ID")):
        print("нет R2_ACCOUNT_ID / R2_ACCESS_KEY_ID — копия переводов пропущена.")
        return None
    return boto3.client(
        "s3", endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto",
        config=Config(retries={"max_attempts": 5, "mode": "adaptive"},
                      max_pool_connections=32, s3={"addressing_style": "path"}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true", help="посчитать, ничего не отправляя")
    a = ap.parse_args()

    old = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    new, todo, raw, vanished = {}, [], 0, 0
    for p in iter_pages():
        key = p.relative_to(ROOT).as_posix()
        try:
            h, size = md5(p), p.stat().st_size
        except FileNotFoundError:      # параллельная сборка могла переписать страницу
            vanished += 1
            continue
        new[key] = h
        raw += size
        if old.get(key) != h:
            todo.append((p, key))
    print(f"страниц перевода: {len(new)} ({raw / 2 ** 30:.2f} ГБ до сжатия) | "
          f"изменённых: {len(todo)}" + (f" | исчезли на лету: {vanished}" if vanished else ""))
    if a.plan:
        return 0

    cl = client()
    if not cl:
        return 1
    sent = [0]

    def put(item):
        p, key = item
        blob = gzip.compress(p.read_bytes(), 6)
        cl.put_object(Bucket=BUCKET, Key=f"{PREFIX}/{key}.gz", Body=blob,
                      ContentType="text/html", ContentEncoding="gzip")
        sent[0] += len(blob)

    if todo:
        with ThreadPoolExecutor(max_workers=24) as ex:
            for i, _ in enumerate(ex.map(put, todo), 1):
                if i % 2000 == 0:
                    print(f"  отправлено {i}/{len(todo)} · {sent[0] / 2 ** 20:.0f} МБ")

    # Как и в backup_r2.py: из бакета ничего не удаляем. Копия должна переживать
    # случайное «снёс не ту папку» на рабочей машине.
    MANIFEST.write_text(json.dumps(new, ensure_ascii=False), encoding="utf-8")
    print(f"✅ переводы скопированы: +{len(todo)} обновлено ({sent[0] / 2 ** 20:.0f} МБ сжатыми), "
          f"всего {len(new)} страниц.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
