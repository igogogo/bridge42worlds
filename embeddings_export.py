#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Выгрузка наших статей для эмбеддинга — АНГЛИЙСКИЙ текст, namespace `ours`.

ПРАВИЛО (решение владельца 2026-07-30): вектор всегда строится из АНГЛИЙСКОГО текста.
И для наших статей, и для абстрактов arXiv. Причина: научная терминология в английском
канонична, модели эмбеддингов на нём обучены лучше, и это единственный язык, который есть
у документов обоих типов — значит наши статьи и чужие абстракты живут в одном
сопоставимом пространстве. Векторов из переводов НЕ делаем.

ПОЧЕМУ ИМЕННО ЭТИ ПОЛЯ (решение ML 2026-07-30, задача 00 п.2):
    original_title + abstract.en.advanced
Заголовок берём авторский с arXiv, а не наш popular.en.title: наши популярные заголовки
намеренно броские и расжаргоненные («Vibration-Absorbing Layer Cake»), вектор от них
уезжает от arXiv-абстракта той же самой работы — ровно то, чего нельзя допустить.
Аннотацию берём advanced по той же причине: это ближайший к научному регистру уровень.

Ничего не пересобирает и не публикует. Только читает data.json и пишет один файл.

    python embeddings_export.py [--out data/embeddings-ours.jsonl] [--limit N]
"""
import json, os, sys, pathlib, argparse

ROOT = pathlib.Path(__file__).resolve().parent
# Собранный сайт (lang/**) с 28.07.2026 не в git, поэтому в отдельном worktree его нет.
# Путь к архиву задаётся флагом --archive или переменной B42_ARCHIVE; по умолчанию —
# рядом со скриптом, как в главной папке проекта.
ARCHIVE = ROOT / "lang" / "ru" / "archive"

# Модель @cf/baai/bge-m3 держит 60k токенов — обрезка тут страховка от аномалий,
# а не режим работы: самый длинный текст в корпусе ~5,5k знаков.
MAX_CHARS = 8000


def pick_text(j):
    """Английский текст для вектора + пометка, откуда он взят."""
    title = (j.get("original_title") or "").strip()
    if not title:
        title = ((j.get("popular") or {}).get("en") or {}).get("title", "").strip()

    en_abs = (j.get("abstract") or {}).get("en") or {}
    body, src = "", ""
    if isinstance(en_abs, dict):
        body = (en_abs.get("advanced") or "").strip()
        src = "abstract.en.advanced"
    if not body:
        body = ((j.get("advanced") or {}).get("en") or {}).get("description", "").strip()
        src = "advanced.en.description"
    if not body:
        body = ((j.get("popular") or {}).get("en") or {}).get("description", "").strip()
        src = "popular.en.description"

    text = f"{title}\n\n{body}".strip()
    return text[:MAX_CHARS], src


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/embeddings-ours.jsonl")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--archive", default=os.environ.get("B42_ARCHIVE", ""),
                    help="путь к lang/ru/archive, если запускаем не из главной папки")
    ap.add_argument("--since", default="",
                    help="только статьи с датой >= ГГГГ-ММ-ДД — ежедневная дозаливка индекса")
    args = ap.parse_args()

    archive = pathlib.Path(args.archive) if args.archive else ARCHIVE
    if not archive.exists():
        sys.exit(f"нет папки архива: {archive}\n"
                 f"укажи --archive или B42_ARCHIVE (lang/** не хранится в git)")

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows, skipped, by_src, chars = [], [], {}, 0
    for p in sorted(archive.rglob("data.json")):
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            skipped.append((str(p), f"битый json: {e}"))
            continue

        aid = j.get("id")
        # Дельта для ежедневной дозаливки. Отбираем по дате статьи, а не по времени файла:
        # пересборка HTML трогает файлы, но статью не меняет — по mtime мы бы каждый раз
        # перезаливали весь архив и платили за это.
        if args.since and (j.get("date") or "") < args.since:
            continue

        text, src = pick_text(j)
        if not aid or len(text) < 40:
            skipped.append((aid or str(p), "нет английского текста"))
            continue

        by_src[src] = by_src.get(src, 0) + 1
        chars += len(text)
        rows.append({
            "id": aid,
            "text": text,
            "namespace": "ours",
            "metadata": {
                # 10 KiB на вектор — влезает с запасом; всё нужное для ссылки в ответе бота.
                # Состав согласован с ведущей сессией (круг 3): title_en, date, has_full —
                # обязательные; остальное наше.
                "title_en": (j.get("original_title") or "")[:300],
                "date": j.get("date"),
                # has_full=true у наших статей с полным разбором; false — у экспрессов
                # (сделаны по аннотации) и потом у чужих абстрактов arXiv в namespace `arxiv`.
                "has_full": not bool(j.get("express")),
                "cat": j.get("primary_category"),
                "title_ru": ((j.get("popular") or {}).get("ru") or {}).get("title", "")[:200],
                "url": f"/ru/archive/{j.get('date')}/{aid}/",
                "src": src,
            },
        })
        if args.limit and len(rows) >= args.limit:
            break

    with out_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # ~4 знака на токен для английского — оценка, не замер
    tokens = chars / 4
    print(f"выгружено: {len(rows)}   пропущено: {len(skipped)}")
    print(f"источник текста: {by_src}")
    print(f"знаков всего: {chars:,}   ~токенов: {tokens:,.0f}")
    print(f"эмбеддинг @cf/baai/bge-m3 ($0,012/млн токенов): ${tokens/1e6*0.012:.4f}")
    print(f"хранение 1024 измерения: {len(rows)*1024:,} измерений")
    print(f"файл: {out_path}  ({out_path.stat().st_size/1024/1024:.1f} МБ)")
    if skipped[:5]:
        print("первые пропуски:", skipped[:5])


if __name__ == "__main__":
    main()
