#!/usr/bin/env python3
"""Материалы авторской работы: PDF, картинки, полный архив — рядом со страницей.

Зачем отдельным модулем. У статьи с arXiv по ссылке лежит текст, и всё. У авторской
работы лежит текст И данные, на которых он построен, — этим мы от arXiv и отличаемся
(владелец 2026-08-08: «у нас же немного отличается, я все данные даю, а не как в arXiv»).
Значит на странице должны быть две видные кнопки, а не одна:

    [ читать работу PDF ]      полная работа автора, свёрстанная в PDF
    [ полные материалы ZIP ]   данные, код, графики — всё, чем работа проверяется

Что здесь делается КОДОМ, без модели: распознать корень пакета, свернуть index.html в PDF
системным браузером, скопировать картинки, собрать архив. Думать тут не над чем, а модель
на такой работе только ошибается и стоит денег.

Что делает МОДЕЛЬ — не здесь, а в submission.py: выбирает, какие картинки выносить в
пересказ, и пишет к ним подписи по-человечески. Имя файла comb_histogram.png читателю
не говорит ничего.
"""
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Куда кладём: рядом со страницей работы, в русской ветке. Языковые версии страницы
# ссылаются сюда же — файлы одни и те же, переводить нечего.
def out_dir(code):
    return ROOT / "lang" / "ru" / "community" / code


IMG_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
# Предел на картинку: авторские графики бывают в исходном разрешении по 15 МБ, а на
# странице всё равно показываются шириной в колонку.
MAX_IMG_MB = 12

# Видео эксперимента — самое ценное, что может прислать автор (владелец 2026-08-08:
# «там ещё видео в работе, его тоже надо публиковать, это круто, видео экспериментов
# прям первым после обложки»). Никакой пересказ не заменит десяти секунд, где видно,
# как установка на самом деле крутится.
VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".m4v"}
MAX_VIDEO_MB = 120


def find_root(box: Path) -> Path:
    """Корень пакета среди распакованного: там, где лежит заключение подготовки."""
    un = box / "unpacked"
    if not un.exists():
        return un
    if (un / "SELF-REVIEW.md").exists():
        return un
    dirs = [d for d in un.iterdir() if d.is_dir()]
    best = [d for d in dirs if (d / "SELF-REVIEW.md").exists()] or \
           [d for d in dirs if (d / "index.html").exists() or (d / "README.md").exists()]
    return best[0] if best else un


def _browser():
    """Путь к системному браузеру для печати в PDF.

    Ставить ничего не нужно: и Edge, и Chrome умеют --headless --print-to-pdf, и хотя бы
    один из них есть на любой машине с Windows. Возвращаем первый найденный."""
    cands = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for c in cands:
        if Path(c).exists():
            return c
    return ""


def make_pdf(code: str, box: Path) -> str:
    """index.html работы → PDF рядом со страницей. Возвращает публичный адрес или ''.

    Печатаем именно авторский html, а не наш пересказ: по этой кнопке человек должен
    получить работу такой, какой её написал автор, включая формулы и вёрстку.
    """
    root = find_root(box)
    src = root / "index.html"
    if not src.exists():
        print("  ⚠️ PDF: в пакете нет index.html")
        return ""
    exe = _browser()
    if not exe:
        print("  ⚠️ PDF: не нашёл системный браузер для печати")
        return ""

    d = out_dir(code)
    d.mkdir(parents=True, exist_ok=True)
    pdf = d / f"{code}.pdf"

    # ПЕЧАТАЕМ КОПИЮ с добавленным печатным стилем, а не оригинал.
    #
    # У работы оказались визуализации на canvas: на бумаге они пусты, но место занимают —
    # и после раздела 5.3 в PDF выходила чистая страница (нашёл владелец 2026-08-08).
    # Пустой холст в печати не нужен: он ничего не показывает. Заодно просим браузер не
    # рвать таблицы и заголовки посередине — в научной работе разорванная таблица хуже
    # лишнего переноса.
    #
    # Файл автора при этом остаётся нетронутым: его же мы отдаём «живой версией», где
    # холсты работают.
    print_css = (
        "<style media='print'>"
        "canvas{display:none!important}"
        # Контейнер холста без иного содержимого схлопываем целиком — иначе от него
        # остаётся отступ и рамка вокруг пустоты.
        ".viz:not(:has(img)),.chart:not(:has(img)),.interactive:not(:has(img)){display:none!important}"
        "table,figure,pre{break-inside:avoid;page-break-inside:avoid}"
        "h1,h2,h3,h4{break-after:avoid;page-break-after:avoid}"
        "</style></head>"
    )
    tmp = box / "_print.html"
    html = src.read_text(encoding="utf-8", errors="replace")
    tmp.write_text(html.replace("</head>", print_css, 1) if "</head>" in html
                   else print_css + html, encoding="utf-8")
    # Кладём копию РЯДОМ с оригиналом: относительные пути к figures/ и media/ должны
    # разрешаться, иначе в PDF не будет ни одной картинки автора.
    near = src.parent / "_print.html"
    shutil.copy2(tmp, near)

    # Профиль во временной папке: без него браузер цепляется к уже открытому окну
    # пользователя и печатает не то, а то и не печатает вовсе.
    prof = box / ".chrome-profile"
    cmd = [exe, "--headless=new", "--disable-gpu", "--no-sandbox",
           f"--user-data-dir={prof}",
           "--no-pdf-header-footer",
           f"--print-to-pdf={pdf}", near.resolve().as_uri()]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        print("  ⚠️ PDF: браузер не уложился в 5 минут")
        return ""
    finally:
        shutil.rmtree(prof, ignore_errors=True)
        near.unlink(missing_ok=True)
        tmp.unlink(missing_ok=True)

    if not pdf.exists() or pdf.stat().st_size < 2048:
        print(f"  ⚠️ PDF не получился: {(r.stderr or r.stdout or '')[:200]}")
        return ""
    print(f"  📄 PDF: {pdf.stat().st_size // 1024} КБ")
    return f"/lang/ru/community/{code}/{code}.pdf"


def copy_images(code: str, box: Path):
    """Картинки автора → рядом со страницей. Возвращает список записей о каждой.

    Берём из figures/ и media/: это то, что автор считает иллюстрациями к работе. Папки
    data/, code/ и scripts/ не трогаем — там картинки бывают промежуточные, и вываливать
    их читателю незачем; они и так уедут в полный архив.
    """
    root = find_root(box)
    d = out_dir(code) / "figures"
    d.mkdir(parents=True, exist_ok=True)
    out = []
    for sub in ("figures", "media"):
        p = root / sub
        if not p.exists():
            continue
        for f in sorted(p.rglob("*")):
            if not f.is_file() or f.suffix.lower() not in IMG_SUFFIXES:
                continue
            if f.stat().st_size > MAX_IMG_MB * 1024 * 1024:
                print(f"  ⚠️ картинка {f.name} — {f.stat().st_size // 1024 // 1024} МБ, пропущена")
                continue
            # Имя разворачиваем в плоское: figures/a/b.png и media/b.png не должны
            # затирать друг друга.
            flat = f"{sub}-{f.relative_to(p).as_posix().replace('/', '-')}"
            shutil.copy2(f, d / flat)
            out.append({"file": flat, "src": f"{sub}/{f.relative_to(p).as_posix()}",
                        "url": f"/lang/ru/community/{code}/figures/{flat}"})
    print(f"  🖼️ картинок перенесено: {len(out)}")
    return out


def copy_interactive(code: str, box: Path) -> str:
    """Авторский index.html как есть — «живая версия». Возвращает адрес или ''.

    В работе оказались интерактивные визуализации на canvas: в PDF от них остаётся пустое
    место (владелец 2026-08-08: «в работе были динамические скрипты визуализации, их нет
    в PDF»). PDF этого и не может — он статичен по природе. Зато мы можем выложить сам
    html автора: скрипты в нём внутренние, картинки рядом, и всё оживает.

    Копируем ТОЛЬКО текст и изображения: код, данные и скрипты обработки уезжают в архив
    и на сайте как исполняемое не публикуются.
    """
    root = find_root(box)
    src = root / "index.html"
    if not src.exists():
        return ""
    d = out_dir(code) / "live"
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, d / "index.html")
    n = 0
    for sub in ("figures", "media"):
        p = root / sub
        if not p.exists():
            continue
        for f in p.rglob("*"):
            if not f.is_file() or f.suffix.lower() not in (IMG_SUFFIXES | VIDEO_SUFFIXES):
                continue
            dst = d / sub / f.relative_to(p)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
            n += 1
    print(f"  🔬 живая версия: index.html + {n} файлов")
    return f"/lang/ru/community/{code}/live/index.html"


def copy_videos(code: str, box: Path):
    """Видео эксперимента → рядом со страницей. Возвращает список записей.

    Показываем без автозапуска и без звука по умолчанию: страница не должна начинать
    говорить сама. Постер берём первым кадром — иначе до нажатия видно чёрный
    прямоугольник, и читатель принимает его за поломку.
    """
    root = find_root(box)
    d = out_dir(code)
    d.mkdir(parents=True, exist_ok=True)
    out = []
    for sub in ("media", "video", "figures"):
        p = root / sub
        if not p.exists():
            continue
        for f in sorted(p.rglob("*")):
            if not f.is_file() or f.suffix.lower() not in VIDEO_SUFFIXES:
                continue
            mb = f.stat().st_size / 1024 / 1024
            if mb > MAX_VIDEO_MB:
                print(f"  ⚠️ видео {f.name} — {mb:.0f} МБ, больше предела {MAX_VIDEO_MB}")
                continue
            flat = f"{sub}-{f.relative_to(p).as_posix().replace('/', '-')}"
            shutil.copy2(f, d / flat)
            rec = {"file": flat, "src": f"{sub}/{f.relative_to(p).as_posix()}",
                   "url": f"/lang/ru/community/{code}/{flat}", "mb": round(mb),
                   "type": "video/mp4" if f.suffix.lower() in (".mp4", ".m4v") else
                           ("video/webm" if f.suffix.lower() == ".webm" else "video/quicktime")}
            poster = _poster(d / flat, d, flat)
            if poster:
                rec["poster"] = f"/lang/ru/community/{code}/{poster}"
            out.append(rec)
    if out:
        print(f"  🎬 видео перенесено: {len(out)} ({sum(v['mb'] for v in out)} МБ)")
    return out


def _poster(video: Path, dest: Path, flat: str) -> str:
    """Кадр из видео для превью. Без ffmpeg просто обходимся без постера."""
    ff = shutil.which("ffmpeg")
    if not ff:
        return ""
    name = Path(flat).stem + "-poster.jpg"
    try:
        subprocess.run([ff, "-y", "-ss", "1", "-i", str(video), "-frames:v", "1",
                        "-q:v", "3", str(dest / name)],
                       capture_output=True, timeout=120)
    except Exception:
        return ""
    return name if (dest / name).exists() else ""


def make_archive(code: str, box: Path) -> tuple:
    """Полный комплект автора → один zip рядом со страницей. Возвращает (адрес, МБ).

    Пересобираем из распакованного, а не копируем присланный: автор мог прислать два
    архива (работу и данные отдельно), и читателю нужна одна кнопка, а не выбор из двух.
    Заодно в архив не попадёт то, что мы при распаковке отсеяли, — исполняемых файлов
    в комплекте быть не должно.
    """
    root = find_root(box)
    un = box / "unpacked"
    d = out_dir(code)
    d.mkdir(parents=True, exist_ok=True)
    z = d / f"{code}-full.zip"

    # Берём КОРЕНЬ ПАКЕТА, а не всё распакованное. На повторном заходе рядом лежит и
    # прежняя версия работы: сложив обе, мы получили бы 138 МБ вместо 69 — те же данные
    # дважды — и читатель гадал бы, какая из двух папок настоящая. Корень пакета автор
    # собрал по нашему промпту, он самодостаточен.
    base = root if root != un else un
    files = [f for f in base.rglob("*") if f.is_file()]
    if not files:
        return "", 0
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for f in files:
            zf.write(f, f.relative_to(base).as_posix())
    mb = z.stat().st_size // 1024 // 1024
    print(f"  📦 полный комплект: {len(files)} файлов, {mb} МБ")
    return f"/lang/ru/community/{code}/{code}-full.zip", mb


def build(code: str) -> dict:
    """Все материалы разом. Результат кладётся в publish.json стадией publish."""
    box = ROOT / "data" / "submissions" / code
    if not box.exists():
        print(f"нет заявки {code}")
        return {}
    res = {
        "pdf_url": make_pdf(code, box),
        # Живая версия — html автора как есть, с работающими визуализациями. Функция была
        # написана, но к сборке НЕ ПОДКЛЮЧЕНА: я звал её руками и потому не заметил.
        # На второй редакции это вылезло — прежняя версия уехала в v1, новая не создалась,
        # и ссылка «работа автора: HTML» осталась без файла.
        "live_url": copy_interactive(code, box),
        "images": copy_images(code, box),
        "videos": copy_videos(code, box),
    }
    res["archive_url"], res["archive_mb"] = make_archive(code, box)
    return res


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("нужен код работы: python tools/submission_assets.py b42p-2026-001")
        sys.exit(2)
    print(json.dumps(build(sys.argv[1]), ensure_ascii=False, indent=1)[:800])
