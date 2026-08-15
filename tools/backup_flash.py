#!/usr/bin/env python3
"""Резервная копия на флешку: то, чего НЕТ в GitHub.

Владелец 15 августа: «на флешку скинь всё, что важно, у нас бэкап — ну без статей,
но код, вектор, там всё, что поместится».

Главная мысль этой копии. Исходники уже лежат в GitHub и восстанавливаются одной
командой clone — дублировать их на флешку бессмысленно, они съедят место, которое
нужно незаменимому. Незаменимое у нас четырёх видов:

  1. КЛЮЧИ (.env). Восстановить нельзя ниоткуда: часть ключей выдана один раз.
     Без них не работает ни генерация, ни почта, ни выкладка.
  2. ВЕКТОР. Поле на 3,13 млн работ и векторы статей. Пересобирается, но это часы
     машинного времени и повторная закачка пятигигабайтного дампа.
  3. СПРАВОЧНИКИ И ГРАФЫ. Теги, законы, учёные, граф знаний, аналитика — результат
     месяцев разметки; часть строилась платными прогонами.
  4. ЗАЯВКИ ЧИТАТЕЛЕЙ (data/submissions). Чужие письма и заказы, второго экземпляра
     нет нигде.

Статьи (lang/**) не берём по прямому указанию владельца: это 30 ГБ и они на сайте.

Порядок копирования — по важности, а не по алфавиту: если место кончится, кончится
оно на наименее ценном. Что не поместилось — перечисляется в отчёте, а не пропадает
молча.

    python tools/backup_flash.py D:            копировать на диск D:
    python tools/backup_flash.py D: --dry      показать план и объёмы
"""
import argparse
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ML = ROOT.parent / "b42-ml"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

# (что копировать, куда внутри копии, зачем — в порядке убывания незаменимости)
PLAN = [
    (ROOT / ".env", "ключи/.env", "ключи ко всем сервисам, восстановить неоткуда"),
    (ROOT / "data" / "council", "справочники/council", "совет: заседания, регламент, участники"),
    (ROOT / "data" / "prompts", "справочники/prompts", "промпты генерации"),
    (ROOT / "data" / "analytics", "справочники/analytics", "карта статей, кластеры, со-встречаемость"),
    (ROOT / "data" / "knowledge-graph.json", "справочники/knowledge-graph.json", "граф знаний с весами"),
    (ROOT / "data" / "tags-graph.json", "справочники/tags-graph.json", "облако тегов"),
    (ROOT / "data" / "laws-graph.json", "справочники/laws-graph.json", "законы и связи"),
    (ROOT / "data" / "corpus-stats.json", "справочники/corpus-stats.json", "покрытие arXiv"),
    (ROOT / "data" / "authors-graph.json", "справочники/authors-graph.json", "граф авторов"),
    (ROOT / "data" / "theory", "справочники/theory", "исследования и точки схождения"),
    (ROOT / "data" / "submissions", "заявки", "письма и заказы читателей — второго экземпляра нет"),
    (ROOT / "data" / "embeddings-articles.jsonl", "вектор/embeddings-articles.jsonl", "векторы наших статей"),
    (ROOT / "data" / "tagvec-cache.jsonl", "вектор/tagvec-cache.jsonl", "векторы тегов"),
    (ROOT / "data" / "arxiv-field.sqlite", "вектор/arxiv-field.sqlite", "поиск по 3,13 млн аннотаций"),
    (ML / "data" / "field.f16", "вектор/field.f16", "полное поле вектора (ML)"),
    (ML / "data" / "arxiv.f16", "вектор/arxiv.f16", "векторы arXiv (ML)"),
]


def size(p):
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def human(n):
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if n < 1024 or unit == "ГБ":
            return f"{n:.1f} {unit}" if unit != "Б" else f"{n} Б"
        n /= 1024


def git_head():
    try:
        r = subprocess.run(["git", "log", "-1", "--pretty=%H %ci %s"], cwd=ROOT,
                           capture_output=True, text=True, encoding="utf-8")
        return (r.stdout or "").strip()
    except Exception:
        return "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("drive", help="буква диска, например D:")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    dst_root = Path(args.drive + "/") / f"bridge42worlds-backup-{date.today()}"
    free = shutil.disk_usage(args.drive + "/").free
    print(f"назначение: {dst_root}\nсвободно на диске: {human(free)}\n")

    plan, total = [], 0
    for src, rel, why in PLAN:
        if not src.exists():
            print(f"  ⏭️ нет: {src.name}")
            continue
        s = size(src)
        plan.append((src, rel, why, s))
        total += s
        print(f"  {human(s):>9}  {rel:<40} {why}")
    print(f"\nвсего к копированию: {human(total)}")

    if args.dry:
        print("(сухой прогон)")
        return 0

    dst_root.mkdir(parents=True, exist_ok=True)
    copied, skipped, used = [], [], 0
    for src, rel, why, s in plan:
        # Оставляем 200 МБ запаса: файловая система не любит заполняться под ноль.
        if used + s > free - 200 * 1024 ** 2:
            skipped.append((rel, s, why))
            print(f"  ⏭️ не влезло: {rel} ({human(s)})")
            continue
        target = dst_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        print(f"  → {rel} ({human(s)})…", flush=True)
        if src.is_dir():
            shutil.copytree(src, target, dirs_exist_ok=True)
        else:
            shutil.copy2(src, target)
        copied.append((rel, s, why))
        used += s

    manifest = {
        "когда": str(date.today()),
        "коммит": git_head(),
        "что скопировано": [{"файл": r, "размер": human(s), "зачем": w} for r, s, w in copied],
        "не поместилось": [{"файл": r, "размер": human(s), "зачем": w} for r, s, w in skipped],
        "чего здесь нет и почему": {
            "исходники": "лежат в GitHub (igogogo/bridge42worlds) — clone восстанавливает всё",
            "статьи lang/**": "30 ГБ, они на сайте и в R2 — по указанию владельца не берём",
            "data/arxiv-bulk": "4 ГБ, пересобирается из дампа Kaggle за три минуты",
        },
    }
    (dst_root / "ОПИСЬ.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    readme = f"""РЕЗЕРВНАЯ КОПИЯ bridge42worlds · {date.today()}

Здесь лежит то, чего НЕТ в GitHub. Исходники не дублируются: они восстанавливаются
командой git clone, а место на флешке нужно незаменимому.

ЧТО ДЕЛАТЬ, ЕСЛИ МАШИНА ПОГИБЛА
  1. git clone https://github.com/igogogo/bridge42worlds.git
  2. скопировать ключи/.env в корень проекта
  3. скопировать содержимое «справочники» в data/
  4. скопировать «вектор» в data/ (field.f16 и arxiv.f16 — в соседнюю копию b42-ml/data)
  5. заявки читателей вернуть в data/submissions
  6. дамп arXiv скачать заново: python tools/update_arxiv_dump.py --force
  7. статьи не нужны: сайт живёт в Cloudflare R2, локальная копия пересобирается

ВНИМАНИЕ
  В папке «ключи» лежит .env — это доступы ко ВСЕМ сервисам: модель, почта,
  Cloudflare, Telegram. Флешку с этим файлом нельзя оставлять без присмотра и
  нельзя передавать кому-либо целиком.
  В папке «заявки» — письма и заказы читателей, то есть чужие персональные данные.

Состояние кода на момент копии: {git_head()}
"""
    (dst_root / "КАК ВОССТАНОВИТЬ.txt").write_text(readme, encoding="utf-8")

    print(f"\n✅ скопировано {human(used)} в {dst_root}")
    if skipped:
        print("не поместилось: " + ", ".join(r for r, _, _ in skipped))
    return 0


if __name__ == "__main__":
    sys.exit(main())
