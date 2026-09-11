# -*- coding: utf-8 -*-
"""Приём работы не из arXiv: завести номер, метаданные и текст — дальше обычный прогон.

Владелец 11.09.2026: «источники разные, они могут быть не PDF; найди оригиналы, а не чужие
пересказы; дальше идёт обычным прогоном».

Первая такая работа (2609.90001, OpenAI про Навье–Стокса) делалась целиком руками: пять
языковых модулей, три уровня, свой сборщик — сорок тысяч строк на одну статью. Здесь всё
иначе: руками только ПРИЁМ, а разбор пишет тот же конвейер, что и для arXiv. Дверь у него
одна — fetch_one_arxiv() сперва смотрит в локальную базу метаданных; работа, положенная
туда, для конвейера неотличима от обычной.

Чужую вёрстку кодом не разбираем: издателей десятки, у каждого своя, и надёжнее прочитать
страницу глазами. Поэтому на вход идёт готовая заготовка JSON — её собирает тот, кто читал
источник. Инструмент делает механическое: проверяет, присваивает номер, кладёт текст.

    python tools/outside/intake.py заготовка.json           показать, что будет
    python tools/outside/intake.py заготовка.json --apply   завести работу
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

WORKS = Path(__file__).resolve().parent / "works"
REQUIRED = ("title", "date", "abstract", "url", "licence_url", "categories")
# Ниже этого размера генератор не доверяет fulltext.txt и идёт за PDF на arXiv — которого
# у нашей работы нет. Предупреждаем на приёме, а не ловим потом на пустом разборе.
THIN_TEXT = 2000


def next_id(date_str):
    """Свободный номер вида YYMM.900NN для месяца этой работы.

    Номер свой, из хвоста 900xx: формат YYMM.NNNNN нужен генератору (из номера выводится
    месяц), а 900xx на arXiv не бывает — по номеру сразу видно, что работа наша.
    """
    yymm = date_str[2:4] + date_str[5:7]
    used = set()
    for p in WORKS.glob(f"{yymm}.900*.json"):
        used.add(p.stem)
    for p in (ROOT / "lang" / "ru" / "archive").glob(f"*/{yymm}.900*"):
        used.add(p.name)
    for n in range(1, 100):
        aid = f"{yymm}.900{n:02d}"
        if aid not in used:
            return aid
    raise SystemExit(f"⛔ в месяце {yymm} кончились свои номера (900 01–99)")


def text_from_pdf(url):
    """Текст работы из PDF по адресу. Качаем и разбираем ТЕМ ЖЕ кодом, что и arXiv-PDF."""
    import requests
    from gen_arxiv import parse_pdf
    import tempfile
    r = requests.get(url, timeout=120, headers={"User-Agent": "bridge42worlds/1.0"})
    r.raise_for_status()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(r.content)
        tmp = Path(f.name)
    try:
        text, _imgs = parse_pdf(tmp)
        return text or ""
    finally:
        tmp.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser(description="Приём работы не из arXiv")
    ap.add_argument("record", help="заготовка JSON (см. tools/outside/README.md)")
    ap.add_argument("--apply", action="store_true", help="записать; без ключа — только показ")
    ap.add_argument("--id", help="взять этот номер, а не следующий свободный")
    a = ap.parse_args()

    src = json.loads(Path(a.record).read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED if not src.get(k)]
    if missing:
        raise SystemExit(f"⛔ в заготовке нет обязательных полей: {', '.join(missing)}")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", src["date"]):
        raise SystemExit(f"⛔ дата должна быть YYYY-MM-DD, а не {src['date']!r}")

    # ПОЛ ПО ЛИЦЕНЗИИ: ниже «только пересказ» работа в этом канале не опускается.
    #
    # Владелец 11.09.2026: «пересказывать для любых работ, которые нас заинтересуют».
    # Основание то же, что записано у первой такой работы (gen_arxiv.RETELL_ONLY_HOSTS):
    # охраняется ВЫРАЖЕНИЕ, а не факты и идеи. Пересказ своими словами законен даже там,
    # где стоит «все права защищены», — при условии, что чужой текст и рисунки мы не
    # воспроизводим. Класс analysis ровно это и обеспечивает: воркер вырезает авторские
    # рисунки и дословную аннотацию при отдаче страницы.
    #
    # Списком хостов это решать нельзя: издателей и лабораторий сотни, список устаревал
    # бы каждую неделю, а забытый хост молча превращался бы в отказ. Поэтому порог стоит
    # у канала: сюда работы попадают поштучно и осознанно, и для каждой мы заранее знаем,
    # что публикуем только собственный разбор.
    #
    # Вверх порог НЕ поднимает: free остаётся только там, где лицензия действительно
    # свободная (CC BY, CC BY-SA, CC0) — это решает код, а не заполняющий заготовку.
    from gen_arxiv import license_class
    cls = license_class(src["licence_url"])
    if cls == "no":
        cls = "analysis"
        print(f"· лицензия {src['licence_url'][:60]} — свободной не является.")
        print("  Берём как «только собственный разбор»: чужие рисунки и дословная")
        print("  аннотация на страницу не идут, охраняется выражение, а не факты.")

    # УЖЕ ЛИ ОНА У НАС. Поиск честно приносит то, что нашёл, и первым же прогоном 11.09
    # принёс работу OpenAI о Навье–Стоксе — она у нас лежит с 08.09 под номером 2609.90001.
    # Сверяем по адресу источника и по DOI: название издатель может подать иначе.
    # Смотрим в двух местах: папка приёма и сам архив. Первая работа (2609.90001) заводилась
    # руками, записи в папке приёма у неё нет — а повторить её было бы обиднее всего.
    def _clash(url, doi, title, where):
        same_url = url and url.rstrip("/") == src["url"].rstrip("/")
        same_doi = src.get("doi") and doi == src["doi"]
        if same_url or same_doi:
            print(f"⛔ эта работа у нас уже есть: {where}")
            print(f"   {(title or '')[:74]}")
            return True
        return False

    for p in sorted(WORKS.glob("*.json")):
        try:
            old = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if _clash(old.get("url"), old.get("doi"), old.get("title"), f"номер {old.get('id', p.stem)}"):
            return 1
    for p in sorted((ROOT / "lang" / "ru" / "archive").glob("*/*.900*/data.json")):
        try:
            old = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if _clash((old.get("sources") or {}).get("live"), (old.get("cited_dois") or [None])[0],
                  old.get("original_title"), f"номер {p.parent.name} в архиве"):
            return 1

    WORKS.mkdir(parents=True, exist_ok=True)
    aid = a.id or next_id(src["date"])

    # Текст: PDF, если дан; иначе снятый со страницы; иначе одна аннотация.
    text = (src.get("fulltext") or "").strip()
    origin = "заготовка"
    if src.get("pdf") and not text:
        try:
            text = text_from_pdf(src["pdf"]).strip()
            origin = "PDF источника"
        except Exception as e:
            print(f"⚠️  PDF не дался ({type(e).__name__}): {str(e)[:120]}")
    if not text:
        text = src["abstract"].strip()
        origin = "только аннотация"

    folder = ROOT / "lang" / "ru" / "archive" / src["date"] / aid
    print(f"номер          {aid}")
    print(f"название       {src['title'][:78]}")
    print(f"источник       {src.get('org') or '—'} · {src['url'][:70]}")
    print(f"дата           {src['date']}")
    print(f"авторов        {len(src.get('authors') or [])}")
    print(f"лицензия       {src['licence_url']} → класс {cls}")
    if cls == "analysis":
        print("               (пересказ наш; авторские рисунки и абстракт не показываем)")
    print(f"разделы        {', '.join(src['categories'])}")
    print(f"текст          {len(text)} знаков, источник: {origin}")
    if len(text) < THIN_TEXT:
        print(f"⚠️  текста меньше {THIN_TEXT} знаков — генератор такому файлу не поверит и")
        print("    пойдёт за PDF на arXiv, которого у этой работы нет. Дай fulltext или pdf.")
    print(f"папка          {folder.relative_to(ROOT)}")

    if not a.apply:
        print("\nэто показ. Завести: добавь --apply")
        return 0

    rec = dict(src)
    rec["id"] = aid
    rec["licence_class"] = cls
    (WORKS / f"{aid}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "fulltext.txt").write_text(text, encoding="utf-8")
    print(f"\n✅ заведено: tools/outside/works/{aid}.json + fulltext.txt")
    print(f"дальше: python run.py ids {aid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
