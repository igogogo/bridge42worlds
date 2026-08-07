"""Выгрузка всей резервной копии на локальный носитель (флешку, внешний диск).

Владелец 2026-08-06: «давай выгрузку сейчас; и наш код там тоже будет, тот что в гите?
ну без данных, но со всем содержимым». Ответ: да — код кладём рабочим деревом, без истории
git. История весит 22 ГБ (старые картинки, которые давно удалены, но живут в коммитах),
на флешку не влезет и не нужна: полная история с ветками лежит на GitHub, а здесь смысл
в другом — чтобы при потере доступа к облаку и к GitHub осталось невосстановимое.

Что кладём:
  lang/    исходники статей — data.json и PDF; их не пересоберёт ничто, каждая стоила денег
  pages/   собранные страницы переводов (единственный экземпляр четырёх языков)
  data/    справочники: теги, законы, учёные, графы, цитирования
  d1/      выгрузка базы: голоса совета, реакции читателей, очередь работ
  code/    рабочее дерево репозитория на текущий коммит, без .git
  ВОССТАНОВЛЕНИЕ.txt  что откуда поднимать, если этот диск — всё, что осталось

    python tools/backup_local.py --to E:\\b42                проверить и выгрузить
    python tools/backup_local.py --to E:\\b42 --dry          только посчитать объём
    python tools/backup_local.py --to E:\\b42 --skip lang    без статей, если места мало
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import boto3
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
BUCKET = os.environ.get("R2_BACKUP_BUCKET", "bridge42worlds-backup")

README = """РЕЗЕРВНАЯ КОПИЯ bridge42worlds — {stamp}

Это снимок всего, что нельзя восстановить генерацией. Если у вас на руках только этот
диск, поднимать проект нужно так.

1. КОД. Папка code/ — рабочее дерево репозитория на коммит {commit}.
   История git сюда не входит (22 ГБ старых картинок в коммитах), она на GitHub:
   {remote}
   Если GitHub недоступен, кода из code/ достаточно, чтобы всё собрать заново — не хватит
   только истории правок.

2. КЛЮЧИ. Файла .env здесь НЕТ и быть не должно: пароли и ключи на носитель не пишем.
   Без них проект соберётся, но не сможет обращаться к моделям, почте и облаку.
   Ключи держит владелец отдельно.

3. ДАННЫЕ. lang/ — исходники статей, data/ — справочники, pages/ — готовые переводы.
   Положить в корень проекта, сохранив пути, и запустить: python run.py html

4. БАЗА. d1/b42-queue/ДАТА.sql — голоса наблюдательного совета, реакции читателей,
   очередь работ. Это следы живых людей, генератор их не восстановит.
   Заливается в новую базу D1 через wrangler d1 execute.
{secrets_note}
Состав копии на момент выгрузки:
{inventory}
"""


def human(n):
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if n < 1024 or unit == "ГБ":
            return f"{n:.1f} {unit}" if unit != "Б" else f"{n} Б"
        n /= 1024


def client():
    acc = os.environ.get("R2_ACCOUNT_ID") or os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    return boto3.client("s3", endpoint_url=f"https://{acc}.r2.cloudflarestorage.com",
                        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
                        region_name="auto")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", required=True, help="куда выгружать, например E:\\b42")
    ap.add_argument("--dry", action="store_true", help="посчитать объём, ничего не писать")
    ap.add_argument("--skip", nargs="*", default=[], help="папки бакета, которые не нужны (lang pages …)")
    ap.add_argument("--with-secrets", action="store_true",
                    help="положить .env и прочие ключи (владелец 2026-08-06: «пишем всё на носитель, "
                         "пароли особенно»). По умолчанию ВЫКЛЮЧЕНО: потерянная флешка с этой папкой "
                         "отдаёт нашедшему почту, облако, домен и деньги на счёте моделей")
    args = ap.parse_args()

    dest = Path(args.to)
    cl = client()

    # ── что есть в облаке ──
    groups, sizes = {}, {}
    objs = []
    for page in cl.get_paginator("list_objects_v2").paginate(Bucket=BUCKET):
        for o in page.get("Contents", []):
            top = o["Key"].split("/")[0]
            if top in args.skip:
                continue
            groups[top] = groups.get(top, 0) + 1
            sizes[top] = sizes.get(top, 0) + o["Size"]
            objs.append((o["Key"], o["Size"]))
    total = sum(sizes.values())

    print(f"бакет {BUCKET}: {len(objs):,} объектов, {human(total)}")
    for k in sorted(groups, key=lambda x: -sizes[x]):
        print(f"   {k:10} {groups[k]:>7,} шт   {human(sizes[k]):>10}")
    if args.skip:
        print(f"   пропускаем: {', '.join(args.skip)}")

    # ── код ──
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    remote = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split("\n")
    files = [f for f in files if f]
    code_size = sum((ROOT / f).stat().st_size for f in files if (ROOT / f).exists())
    print(f"код: {len(files):,} файлов, {human(code_size)} (коммит {commit})")
    print(f"ИТОГО: {human(total + code_size)}")

    if args.dry:
        return 0

    # ── проверяем место ──
    dest.mkdir(parents=True, exist_ok=True)
    free = __import__("shutil").disk_usage(dest).free
    need = total + code_size
    if free < need * 1.05:
        print(f"⛔ на носителе {human(free)}, нужно {human(need)} — не помещается.")
        print("   Освободите место или запустите с --skip lang (статьи) либо --skip pages (переводы).")
        return 1

    # ── код ──
    print("\nкопирую код…")
    for i, f in enumerate(files, 1):
        src = ROOT / f
        if not src.exists():
            continue
        dst = dest / "code" / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if i % 500 == 0:
            print(f"   {i}/{len(files)}", flush=True)
    print(f"   {len(files)}/{len(files)} готово")

    # ── данные из облака ──
    print("\nскачиваю копию из облака…")
    done = bytes_done = 0
    failed = []
    t0 = time.time()
    for key, size in objs:
        dst = dest / key
        # Пропускаем то, что уже скачано целиком — повторный запуск дописывает, а не начинает
        # заново: на двух гигабайтах и медленной флешке это разница между минутой и часом.
        if dst.exists() and dst.stat().st_size == size:
            done += 1
            bytes_done += size
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        # Обрыв связи на 60-тысячном файле не должен обнулять час работы. Первый прогон
        # 2026-08-06 умер на 80% с EndpointConnectionError — сеть моргнула, и всё встало.
        # Три попытки с нарастающей паузой; если и они не помогли, файл пропускаем и идём
        # дальше, а список пропущенных печатаем в конце: лучше копия с дырой и честным
        # списком, чем полное отсутствие копии из-за одного файла.
        for attempt in range(3):
            try:
                cl.download_file(BUCKET, key, str(dst))
                break
            except Exception as e:
                if attempt == 2:
                    print(f"   ⚠️ пропущен {key}: {type(e).__name__}")
                    failed.append(key)
                else:
                    time.sleep(2 * (attempt + 1))
        done += 1
        bytes_done += size
        if done % 500 == 0:
            el = time.time() - t0
            print(f"   {done:,}/{len(objs):,} · {human(bytes_done)} · {el/60:.1f} мин", flush=True)

    # ── ключи ──
    secrets_note = ""
    if args.with_secrets:
        sec_dir = dest / "КЛЮЧИ"
        sec_dir.mkdir(parents=True, exist_ok=True)
        put = []
        for rel in (".env", "cloudflare/.dev.vars", "cloudflare/wrangler.toml"):
            src = ROOT / rel
            if src.exists():
                dst = sec_dir / rel.replace("/", "_")
                shutil.copy2(src, dst)
                put.append(f"{rel} → КЛЮЧИ/{dst.name}")
        (sec_dir / "ЧТО ЭТО.txt").write_text(
            "Здесь боевые ключи и пароли проекта.\n\n"
            "Тот, кто получит эту папку, получит: почту проекта, облако Cloudflare с сайтом\n"
            "и резервными копиями, управление доменом, счёт у моделей и Telegram-бота.\n"
            "Восстановить после чужого доступа можно всё, кроме репутации и потраченных денег.\n\n"
            "Поэтому: держите носитель там же, где держали бы паспорт и банковскую карту.\n"
            "Если он потеряется — ротировать нужно ВСЁ перечисленное, а не только то,\n"
            "что кажется важным.\n\n"
            "Положено по прямому распоряжению владельца 2026-08-06: «пишем всё на носитель,\n"
            "пароли особенно». Копия без ключей делается запуском без --with-secrets.\n",
            encoding="utf-8")
        print(f"\n🔑 ключи положены: {', '.join(put)}")
        secrets_note = ("\n5. КЛЮЧИ. Папка КЛЮЧИ/ — боевые пароли и токены. Носитель с ней равен\n"
                        "   полному доступу к проекту: почта, облако, домен, счёт у моделей.\n"
                        "   Хранить как паспорт. При потере — ротировать всё разом.\n")

    inventory = "\n".join(f"  {k:10} {groups[k]:>7,} файлов  {human(sizes[k])}" for k in sorted(groups))
    inventory += f"\n  code       {len(files):>7,} файлов  {human(code_size)}"
    (dest / "ВОССТАНОВЛЕНИЕ.txt").write_text(
        README.format(stamp=time.strftime("%Y-%m-%d %H:%M"), commit=commit,
                      remote=remote or "(удалённый репозиторий не задан)", inventory=inventory,
                      secrets_note=secrets_note),
        encoding="utf-8")

    if failed:
        print(f"\n⚠️ не скачались {len(failed)} файлов — запустите команду ещё раз, "
              f"она добирает только недостающее:")
        for k in failed[:10]:
            print(f"   {k}")
        if len(failed) > 10:
            print(f"   … и ещё {len(failed) - 10}")

    print(f"\n✅ готово: {done:,} объектов + {len(files):,} файлов кода, {human(bytes_done + code_size)}")
    print(f"   {dest}")
    print("   Ключей (.env) в копии НЕТ — это намеренно.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
