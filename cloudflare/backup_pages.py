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
        raw += size
        if old.get(key) != h:
            # В опись попадёт ПОСЛЕ удачной отправки, не раньше.
            todo.append((p, key, h))
        else:
            new[key] = h
    print(f"страниц перевода: {len(new) + len(todo)} ({raw / 2 ** 30:.2f} ГБ до сжатия) | "
          f"изменённых: {len(todo)}" + (f" | исчезли на лету: {vanished}" if vanished else ""))
    if a.plan:
        return 0

    cl = client()
    if not cl:
        return 1
    sent = [0]

    """ОБРЫВ НЕ ДОЛЖЕН ОБЕСЦЕНИВАТЬ КОПИЮ.

    Опись писалась одной строкой в самом конце. Значит любой обрыв — kill, сеть,
    выключение — стирал память о тридцати тысячах уже отправленных страниц, и
    следующий прогон гнал их заново. Поймано 30 августа на живом примере: прогон
    остановили посреди копии, и следующий день начал с тех же 30 819 страниц.
    Ровно этот изъян в тот же день чинили в cloudflare/deploy_r2.py — лечим и здесь,
    тем же способом: страница попадает в опись только после удачной отправки, а
    опись сохраняется по ходу.
    """
    SAVE_EVERY = 2000
    failed = []

    def put(item):
        p, key, h = item
        try:
            blob = gzip.compress(p.read_bytes(), 6)
            cl.put_object(Bucket=BUCKET, Key=f"{PREFIX}/{key}.gz", Body=blob,
                          ContentType="text/html", ContentEncoding="gzip")
            sent[0] += len(blob)
            return key, h
        except Exception as e:
            failed.append((key, f"{type(e).__name__}: {str(e)[:60]}"))
            return key, None

    if todo:
        done_since_save = 0
        with ThreadPoolExecutor(max_workers=24) as ex:
            for i, (key, h) in enumerate(ex.map(put, todo), 1):
                if h is not None:
                    new[key] = h
                    done_since_save += 1
                if i % 2000 == 0:
                    print(f"  отправлено {i}/{len(todo)} · {sent[0] / 2 ** 20:.0f} МБ"
                          + (f" · не удалось {len(failed)}" if failed else ""))
                if done_since_save >= SAVE_EVERY:
                    MANIFEST.write_text(json.dumps(new, ensure_ascii=False),
                                        encoding="utf-8")
                    done_since_save = 0
    if failed:
        print(f"⚠️  не удалось отправить {len(failed)} страниц — в опись они НЕ "
              f"записаны, следующий прогон возьмётся за них. Первые:")
        for k, why in failed[:5]:
            print(f"   {k}  ({why})")

    # Как и в backup_r2.py: из бакета ничего не удаляем. Копия должна переживать
    # случайное «снёс не ту папку» на рабочей машине.
    MANIFEST.write_text(json.dumps(new, ensure_ascii=False), encoding="utf-8")
    print(f"✅ переводы скопированы: +{len(todo) - len(failed)} обновлено "
          f"({sent[0] / 2 ** 20:.0f} МБ сжатыми), всего {len(new)} страниц."
          + (f" Не удалось: {len(failed)}." if failed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
