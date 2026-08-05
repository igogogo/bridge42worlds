"""Восстановление рабочей копии из R2 на пустой машине — «плохой день».

Зачем отдельный скрипт, если есть backup_r2.py --restore. Тот достаёт ОДНУ статью и годится
как проверка, что копия читается. Здесь другая задача: человек, у которого нет ничего, кроме
доступа к бакетам, должен получить работающее дерево. Он в этот момент не читает исходники
и не помнит, какой бакет за что отвечает, — поэтому скрипт сам говорит, что делает дальше
и чего в бакетах нет.

Два бакета — две разные роли:
  • bridge42worlds-backup — ИСХОДНИКИ (data.json, реестры, оригиналы обложек). Невосстановимы
    ничем: за этот текст заплачено модели, за обложки — FLUX. Это то, ради чего всё.
  • bridge42worlds-site   — СОБРАННЫЙ САЙТ. Восстанавливается генератором из исходников,
    но пересборка — это часы; в аварии быстрее скачать готовое.

Чего в бакетах НЕТ и почему (печатается в конце каждого прогона — см. missing_report):
ключи, состояние Cloudflare (D1/KV/Vectorize) и код. Это не забывчивость, а граница:
секреты в резервной копии = вторая точка утечки, состояние Cloudflare живёт у Cloudflare,
код живёт в git.

    python cloudflare/restore_r2.py --to <папка>              # исходники (1,4 ГБ)
    python cloudflare/restore_r2.py --to <папка> --what all   # + собранный сайт (5,3 ГБ)
    python cloudflare/restore_r2.py --to <папка> --no-covers  # без обложек, быстрая проверка
    python cloudflare/restore_r2.py --plan                    # ничего не качать, только показать

Проверено живым прогоном 2026-08-05 (см. задачи/отчёты/devops.md).
"""
import os, sys, json, time, argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from dotenv import load_dotenv

# Windows: при выводе в файл/фон Python откатывается на cp1252 и падает на кириллице.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BACKUP_BUCKET = os.environ.get("R2_BACKUP_BUCKET", "bridge42worlds-backup")
SITE_BUCKET = os.environ.get("R2_BUCKET", "bridge42worlds-site")


def client():
    import boto3
    from botocore.config import Config
    account = os.environ.get("R2_ACCOUNT_ID") or os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    key = os.environ.get("R2_ACCESS_KEY_ID")
    if not (account and key):
        print("Нет R2_ACCOUNT_ID / R2_ACCESS_KEY_ID.")
        print("Это и есть первый шаг восстановления: получить .env у владельца — см. конец вывода.")
        return None
    return boto3.client(
        "s3", endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
        aws_access_key_id=key, aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
        # Скачиваем десятки тысяч объектов в 24 потока: дефолтный пул соединений (10)
        # становится узким горлом и сыпет предупреждениями.
        config=Config(retries={"max_attempts": 5, "mode": "adaptive"},
                      max_pool_connections=32, s3={"addressing_style": "path"}))


def listing(s3, bucket, skip_covers=False):
    """Полный листинг бакета. Отдаёт [(ключ, размер)]."""
    out = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        for o in page.get("Contents", []):
            if skip_covers and o["Key"].endswith("ai.jpg"):
                continue
            out.append((o["Key"], o["Size"]))
    return out


def pull(s3, bucket, items, dest, label):
    """Качает объекты в dest, сохраняя пути. Уже скачанное с тем же размером пропускает —
    прогон можно прервать и повторить, он продолжит с места обрыва, а не начнёт заново."""
    dest.mkdir(parents=True, exist_ok=True)
    total = sum(sz for _, sz in items)
    print(f"\n{label}: {len(items)} объектов, {total / 2 ** 30:.2f} ГБ → {dest}")
    done, got, started, errors = 0, 0, time.time(), []

    def one(item):
        key, size = item
        target = dest / key
        if target.exists() and target.stat().st_size == size:
            return size, True
        target.parent.mkdir(parents=True, exist_ok=True)
        s3.download_file(bucket, key, str(target))
        return size, False

    with ThreadPoolExecutor(max_workers=24) as ex:
        futures = {ex.submit(one, it): it for it in items}
        for i, f in enumerate(futures, 1):
            try:
                size, skipped = f.result()
                done += 1
                if not skipped:
                    got += size
            except Exception as e:
                errors.append((futures[f][0], str(e)[:120]))
            if i % 2000 == 0:
                el = time.time() - started
                print(f"  {i}/{len(items)} · {got / 2 ** 20:.0f} МБ · {el:.0f} с")

    el = time.time() - started
    print(f"  готово: {done}/{len(items)} за {el:.0f} с ({got / 2 ** 20:.0f} МБ скачано)")
    if errors:
        print(f"  ⚠️  не скачалось: {len(errors)}")
        for k, e in errors[:10]:
            print(f"     {k} — {e}")
    return done, errors


def verify(dest):
    """Проверка, что скачалось не «сколько-то байт», а рабочие данные.

    Считать файлы бесполезно: битый JSON тоже файл. Поэтому читаем то, без чего дерево
    мертво, — реестры и выборку статей — и пробуем разобрать их как JSON."""
    print("\nПроверка восстановленного:")
    ok = True

    arts = sorted((dest / "lang").glob("*/archive/*/*/data.json")) if (dest / "lang").exists() else []
    print(f"  исходников статей: {len(arts)}")
    # Только русский — это НОРМА, а не потеря: исходник статьи один, остальные четыре языка
    # существуют собранными страницами. Проверка это печатает, чтобы в плохой день никто
    # не решил, что копия неполная, и не начал искать несуществующее.
    bad, langs = [], {}
    for p in arts:
        lang = p.relative_to(dest / "lang").parts[0]
        langs[lang] = langs.get(lang, 0) + 1
    # Обязательные поля исходника — те, без которых страница не соберётся.
    for p in arts[:: max(1, len(arts) // 50)]:      # выборка ~50 штук по всему дереву
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            missing = [f for f in ("id", "original_title", "abstract") if not d.get(f)]
            if missing:
                bad.append((p.parent.name, "нет полей: " + ", ".join(missing)))
        except Exception as e:
            bad.append((str(p.relative_to(dest)), str(e)[:80]))
    print(f"  по языкам: {', '.join(f'{k}={v}' for k, v in sorted(langs.items())) or '—'}"
          f"  (исходник только ru — так и должно быть)")
    print(f"  выборочно разобрано {min(50, len(arts))}: " + ("битых нет" if not bad else f"БИТЫХ {len(bad)}"))
    for n, e in bad[:5]:
        print(f"     {n} — {e}")
    ok &= not bad

    # Реестры лежат в языковых папках, а не в data/ — легко ошибиться, проверяя вслепую.
    for rel in ("lang/ru/data/tags.json", "lang/ru/data/laws.json",
                "lang/ru/data/scientists.json", "data/knowledge-graph.json"):
        p = dest / rel
        if not p.exists():
            print(f"  ⚠️  нет {rel}")
            ok = False
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            n = len(d) if isinstance(d, (list, dict)) else "?"
            print(f"  {rel}: разбирается, записей {n}")
        except Exception as e:
            print(f"  ⚠️  {rel} не разбирается: {str(e)[:80]}")
            ok = False

    covers = list((dest / "lang").rglob("ai.jpg")) if (dest / "lang").exists() else []
    if covers:
        empty = [c for c in covers if c.stat().st_size < 1024]
        print(f"  оригиналов обложек: {len(covers)}" + (f", подозрительно мелких: {len(empty)}" if empty else ""))
    return ok


def missing_report(dest):
    """Главная ценность этого скрипта: честный список того, чего в бакетах нет.

    Порядок шагов — не произвольный. Ключи первым пунктом, потому что без них не читается
    сам бакет; Cloudflare последним, потому что это единственное, что нельзя добыть
    самому и придётся восстанавливать руками из панели."""
    print("\n" + "=" * 72)
    print("ЧЕГО В БАКЕТАХ НЕТ — доделать руками, по порядку:")
    print("=" * 72)
    print("""
1. КЛЮЧИ (.env). В резервной копии их нет намеренно: бэкап читается теми же ключами,
   которые в нём лежали бы, и это вторая точка утечки. Взять у владельца.
   Минимум, чтобы дерево ожило: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
   CLOUDFLARE_API_TOKEN, DEEPSEEK_API_KEY. Образец полей — cloudflare/.env.example.

2. КОД. git clone https://github.com/igogogo/bridge42worlds — сам сайт в git больше
   не хранится (lang/** выселен), поэтому клон лёгкий, но и пустой на вид: это нормально.
   Данные приезжают сюда, этим скриптом.

3. СОСТОЯНИЕ CLOUDFLARE — единственное, чего нет НИГДЕ, кроме самой Cloudflare:
     • D1: реакции/просмотры, очередь, совет  → лежит в этой же копии, d1/<база>/<дата>.sql
     • KV: контекст бота, нормы читателей     → context_build.py соберёт заново из исходников
     • Vectorize: индекс поиска               → vector_build.py соберёт заново
     • секреты Worker                         → wrangler secret put, значения из .env
   Пересобираемое (KV, Vectorize) — это часы работы, но не потеря. D1 не пересобирается
   ничем, поэтому с 2026-08-05 выгружается сюда каждый прогон (backup_d1.py, 14 суток).

3б. ПЕРЕВОДЫ. Исходник статьи существует только по-русски; английский, испанский,
   арабский и французский живут собранными страницами и больше нигде. Значит, бакет
   сайта — не только витрина, но и единственный экземпляр переводов. Не чистите его
   `--prune` вслепую и не считайте, что его потеря — «просто пересоберём».

4. ПРОВЕРКА, что дерево живое (ничего не стоит, модель не зовётся):
     python run.py stats
""".rstrip())
    print(f"\nВосстановленное дерево: {dest}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", default="_restore", help="куда восстанавливать (пустая папка)")
    ap.add_argument("--what", choices=["sources", "site", "all"], default="sources")
    ap.add_argument("--no-covers", action="store_true", help="без оригиналов обложек (1,2 ГБ)")
    ap.add_argument("--plan", action="store_true", help="ничего не качать, показать объём")
    a = ap.parse_args()

    s3 = client()
    if not s3:
        return 1
    dest = Path(a.to).resolve()

    jobs = []
    if a.what in ("sources", "all"):
        jobs.append((BACKUP_BUCKET, "исходники (невосстановимое)", a.no_covers))
    if a.what in ("site", "all"):
        jobs.append((SITE_BUCKET, "собранный сайт", False))

    plans = []
    for bucket, label, skip in jobs:
        items = listing(s3, bucket, skip_covers=skip)
        plans.append((bucket, label, items))
        print(f"{bucket}: {len(items)} объектов, {sum(s for _, s in items) / 2 ** 30:.2f} ГБ")
    if a.plan:
        missing_report(dest)
        return 0

    failed = 0
    for bucket, label, items in plans:
        _, errors = pull(s3, bucket, items, dest, label)
        failed += len(errors)

    ok = verify(dest)
    missing_report(dest)
    if failed:
        print(f"\n⚠️  объектов не скачалось: {failed} — прогон можно повторить, "
              f"уже скачанное пропустится.")
    return 0 if ok and not failed else 1


if __name__ == "__main__":
    sys.exit(main())
