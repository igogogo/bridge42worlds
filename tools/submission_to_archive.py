#!/usr/bin/env python3
"""Авторская работа → обычная статья архива. Ничего своего, всё по уставу.

Почему так, а не своим шаблоном. Раздел /community/ строился отдельным генератором со
своей вёрсткой, и владелец 2026-08-08 сказал прямо: «почему ссылки на работы, теги,
похожие статьи внизу, а не как на обычной нашей странице… меню даже изменил… такая же
статья, максимум ещё ссылки, объяснения и так далее, но всё то же самое, просто другой
источник, и всё».

Он прав, и причина глубже, чем вёрстка. Пока у работы отдельный шаблон, каждая правка
дизайна сайта приходит на неё вручную — или не приходит. Пока у неё отдельный корпус,
её нет ни в ленте, ни в поиске, ни в карте сайта, ни в графе: всё это строится по
articles-index, а её там нет.

Поэтому работа кладётся в архив как обычная статья: свой data.json, свой каталог по дате,
свой id (наш препринт-код вместо arXiv-номера). Дальше её собирает, индексирует, ищет и
показывает тот же код, что и остальные 2 200 статей. Отличают её ровно три вещи, и все
три — данные, а не отдельная вёрстка:

    "author_work": true      плашки «авторская работа» и «мы разобрали»
    "kind"                   экспериментальная / теоретическая
    "sources"                HTML, PDF, полные материалы — вместо ссылки на arXiv
    "review"                 наш разбор и слово автора

    python tools/submission_to_archive.py b42p-2026-001
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common import ALL_LANGS  # noqa: E402
LANGS = ALL_LANGS   # список языков один на проект: config.json через common.ALL_LANGS


def build(code: str) -> str:
    """Кладёт работу в архив как статью. Возвращает дату-папку или ''."""
    box = ROOT / "data" / "submissions" / code
    pj = box / "publish.json"
    if not pj.exists():
        print(f"нет publish.json у {code}")
        return ""
    w = json.loads(pj.read_text(encoding="utf-8"))
    date_str = w.get("received") or ""
    if not date_str:
        print("нет даты публикации")
        return ""

    # Тексты берём из обычного конвейера (tools/submission_as_article.py): работа
    # прошла тот же промпт и тот же каскад, что статья с arXiv, и переведена тем же
    # переводчиком. Своего упрощённого пересказа больше нет — он и был причиной того,
    # что страница работы жила отдельной жизнью.
    art_file = box / "article-ru.json"
    if not art_file.exists():
        print("нет article-ru.json — сперва: python tools/submission_as_article.py " + code)
        return ""
    art = json.loads(art_file.read_text(encoding="utf-8"))
    popular = art.get("popular", {})
    simple = art.get("simple", {})
    advanced = art.get("advanced", {})
    # Теги и законы берём из самой статьи: их выбрал тот же промпт, что у остальных.
    ru_adv = advanced.get("ru", {}) or {}
    tags = [ru_adv.get("main_tag")] + list(ru_adv.get("extra_tags") or [])
    tags = [t for t in tags if t]
    laws = list(ru_adv.get("laws") or [])

    data = {
        "id": code,
        "date": date_str,
        "original_title": w.get("title", ""),
        # Автор не представился — в списке авторов пусто, а не выдуманное имя.
        "authors": [w["author_display"]] if w.get("author_display") else [],
        "categories": [], "primary_category": "",
        "license": "", "license_name": "",
        "tags": tags,
        "main_tag": tags[0] if tags else None,
        "scientists": list(ru_adv.get("scientists") or []), "threads": [],
        "cited_arxiv": [], "cited_dois": [],
        "express": False, "express_tiers": [], "refined": False,
        "popular": popular, "simple": simple, "advanced": advanced,
        "abstract": {}, "captions": {},
        # ── то, чем работа отличается от статьи с arXiv ──
        "author_work": True,
        "kind": w.get("kind", ""),
        "code": code,
        "sources": {"live": w.get("live_url", ""), "pdf": w.get("pdf_url", ""),
                    "zip": w.get("archive_url", ""), "zip_mb": w.get("archive_mb", 0)},
        "review": w.get("review", {}),
        "author_comment": w.get("author_comment", ""),
        "similar": w.get("similar", []),
    }

    made = []
    for lang in LANGS:
        d = ROOT / "lang" / lang / "archive" / date_str / code
        d.mkdir(parents=True, exist_ok=True)
        (d / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
        made.append(str(d))

    # Картинки и обложка едут туда, где генератор их ищет: 0.jpg, 1.jpg… и ai.jpg —
    # ровно те имена, по которым собирается галерея статьи.
    src = ROOT / "lang" / "ru" / "community" / code
    dst = ROOT / "lang" / "ru" / "archive" / date_str / code
    n = 0
    figs = sorted((src / "figures").glob("*")) if (src / "figures").exists() else []
    caps_ru = (w.get("captions", {}) or {}).get("ru", {}) or {}
    order = []
    # Имена и формат — ровно те, по которым генератор собирает галерею статьи: 0.jpg,
    # 1.jpg… Положив .png, мы получили страницу с пятью картинками из двадцати семи:
    # генератор ищет folder.glob("*.jpg") с числовым именем и остальное просто не видит.
    from PIL import Image
    for f in figs:
        if not f.is_file():
            continue
        try:
            im = Image.open(f)
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            im.save(dst / f"{n}.jpg", "JPEG", quality=90, optimize=True)
        except Exception as ex:
            print(f"  ⚠️ {f.name}: {ex}")
            continue
        order.append(caps_ru.get(f.name, ""))
        n += 1
    if (src / "cover.jpg").exists():
        shutil.copy2(src / "cover.jpg", dst / "ai.jpg")
    # Подписи в том же виде, что у статьи: список по порядку картинок, по языкам.
    data["captions"] = {lang: [((w.get("captions", {}) or {}).get(lang, {}) or {}).get(f.name, "")
                               for f in figs if f.is_file()][:n]
                        for lang in LANGS}
    data["images_count"] = n
    for lang in LANGS:
        (ROOT / "lang" / lang / "archive" / date_str / code / "data.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ {code} лёг в архив как статья: {date_str}, картинок {n}, языков {len(made)}")
    return date_str


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("нужен код: python tools/submission_to_archive.py b42p-2026-001")
        sys.exit(2)
    sys.exit(0 if build(sys.argv[1]) else 1)
