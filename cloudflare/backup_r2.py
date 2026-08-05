"""Резервная копия исходных данных в ПРИВАТНЫЙ бакет R2 (bridge42worlds-backup).

Зачем отдельный скрипт и отдельный бакет. deploy_r2.py публикует САЙТ — то, что читатель
скачивает браузером; исходники туда намеренно не попадают (SKIP_NAMES/SKIP_PATH_PREFIXES).
Но именно исходники невосстановимы: собранную страницу генератор соберёт заново из data.json,
а сам data.json не соберёт ниоткуда — это текст, за который заплачено модели.

Что копируем (всё, что нельзя восстановить ни из git, ни генератором):
  • lang/*/archive/*/*/data.json — четыре уровня глубины × четыре языка на каждую статью;
  • data/*.json и data/theory/** — реестры тегов/законов/учёных, курсы, справочники;
  • ai.jpg — оригиналы AI-обложек, за них плачено FLUX. Найдено 2026-07-29 при разборе
    задачи 00: они провалились в ту же щель, что и data.json. Из git ушли вместе с lang/**,
    в публикацию не попадают (SKIP_JPG_UNDER в deploy_r2.py — сайт раздаёт webp-двойники).
    Потеря диска = webp останется, а оригинал и деньги за него нет. Отключается R2_BACKUP_COVERS=0.
  • cloudflare/.r2-manifest.json НЕ копируем: он производный, пересчитывается за 15 секунд.

Состояние на 2026-07-29: 1980 data.json (121 МБ) + 1775 обложек (1,1 ГБ). Хранение обоих
бакетов вместе — единицы центов в месяц, укладываемся в бесплатную норму R2 (10 ГБ).

Как запускать: сам, последним шагом любой команды run.py (см. _publish_to_r2/_backup_to_r2).
Руками — только для разовой проверки. Дельта по md5, свой манифест, как у deploy_r2.py.

Восстановление (проверено 2026-07-29):
    python cloudflare/backup_r2.py --restore <arxiv_id> --to <папка>
"""
import os, sys, json, hashlib, argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from dotenv import load_dotenv

# Windows: при выводе в файл/фон Python откатывается на cp1252 и падает на кириллице.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
MANIFEST = ROOT / "cloudflare" / ".backup-manifest.json"
BUCKET = os.environ.get("R2_BACKUP_BUCKET", "bridge42worlds-backup")


def iter_sources():
    """Только невосстановимое. Собранные страницы сюда НЕ попадают — они производные."""
    for p in (ROOT / "lang").glob("*/archive/*/*/data.json"):
        yield p
    # Реестры внутри языковых папок: теги, законы, учёные, имена — по 5–9 файлов на язык.
    # Их не было в копии до 2026-08-05, и это самая дорогая из найденных репетицией дыр:
    # из git они выселены вместе с lang/**, а генератор их не восстановит — это описания,
    # за которые заплачено модели, да ещё переведённые на пять языков. Держались в одном
    # экземпляре на рабочей машине. 24 МБ на всё.
    for p in (ROOT / "lang").glob("*/data/*.json"):
        yield p
    data = ROOT / "data"
    for p in data.glob("*.json"):
        yield p
    for p in (data / "theory").rglob("*"):
        if p.is_file() and p.suffix.lower() in (".json", ".md"):
            yield p
    if os.environ.get("R2_BACKUP_COVERS", "1") != "0":
        for p in (ROOT / "lang").rglob("ai.jpg"):
            yield p


def md5(p):
    h = hashlib.md5()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def client():
    import boto3
    account = os.environ.get("R2_ACCOUNT_ID") or os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    if not (account and os.environ.get("R2_ACCESS_KEY_ID")):
        print("нет R2_ACCOUNT_ID / R2_ACCESS_KEY_ID — бэкап пропущен.")
        return None
    return boto3.client(
        "s3", endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")


def backup():
    s3 = client()
    if not s3:
        return 1
    old = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    new, todo, vanished = {}, [], 0
    for p in iter_sources():
        key = p.relative_to(ROOT).as_posix()
        try:
            h = md5(p)
        except FileNotFoundError:      # параллельная генерация могла переписать файл
            vanished += 1
            continue
        new[key] = h
        if old.get(key) != h:
            todo.append((p, key))
    print(f"исходников: {len(new)} | изменённых к копированию: {len(todo)}" +
          (f" | исчезли на лету: {vanished}" if vanished else ""))

    if todo:
        def put(item):
            p, key = item
            s3.upload_file(str(p), BUCKET, key, ExtraArgs={"ContentType": "application/json"})
        with ThreadPoolExecutor(max_workers=24) as ex:
            for i, _ in enumerate(ex.map(put, todo), 1):
                if i % 500 == 0:
                    print(f"  скопировано {i}/{len(todo)}")

    # Намеренно НЕ удаляем из бакета то, чего не стало локально: бэкап должен переживать
    # случайное «удалил не то» на рабочей машине. Мусор здесь дешевле потери.
    MANIFEST.write_text(json.dumps(new, ensure_ascii=False), encoding="utf-8")
    print(f"✅ резервная копия готова: +{len(todo)} обновлено, всего {len(new)} файлов.")
    return 0


def restore(arxiv_id, dest):
    """Достаёт исходник одной статьи — этим же путём проверяется, что копия рабочая."""
    s3 = client()
    if not s3:
        return 1
    dest = Path(dest)
    found = 0
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix="lang/"):
        for obj in page.get("Contents", []):
            if f"/{arxiv_id}/" not in obj["Key"]:
                continue
            target = dest / obj["Key"]
            target.parent.mkdir(parents=True, exist_ok=True)
            s3.download_file(BUCKET, obj["Key"], str(target))
            print("восстановлено:", target)
            found += 1
    if not found:
        print(f"в бэкапе не нашлось ничего по {arxiv_id}")
        return 1
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--restore", metavar="ARXIV_ID", help="достать исходник статьи из копии")
    ap.add_argument("--to", default="_restore_check", help="куда положить (для --restore)")
    a = ap.parse_args()
    sys.exit(restore(a.restore, a.to) if a.restore else backup())
