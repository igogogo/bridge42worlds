"""Народная наука: приём статьи с почты → проверка → разбор → закрытая публикация.

Владелец 2026-08-04: «прогнать как будто прислали новую статью: анализ на вменяемость,
логичность, завершённость; похожие работы и как помочь — всё в ответном письме; если ок —
публикуем в закрытом виде со своим препринт-кодом, размечаем тегами как положено; главное —
наш уникальный ML-анализ на корректность и силу. Автор не указан — анонимно, но почту
фиксируем; в справочник авторов НЕ добавляем. Данные жмём в zip, лимит 10 МБ, полные —
по запросу. После публикации автору возвращается токен для связи: отзыв, апдейт».

Стадии — отдельными командами, потому что режим ПОЛУРУЧНОЙ: между стадиями смотрит человек.

    python tools/submission.py fetch              забрать письма с article@ → data/submissions/
    python tools/submission.py analyze b42p-...   анализатор + похожие + черновик ответа
    python tools/submission.py publish b42p-...   закрытая страница + токен автора
    python tools/submission.py list               что в работе

Безопасность: вложения прогоняются через Защитник Windows ДО распаковки; распаковка — с
запретом выхода из папки (zip-slip); html-вложения публикуются только после ручного
просмотра (стадия publish этого не обходит).
"""
import argparse
import email
import email.header
import hashlib
import imaplib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

ROOT = Path(__file__).resolve().parent.parent
# Скрипт лежит в tools/, а общие модули (common, community_pages) — в корне. Без этой
# строки корень попадал в путь только внутри cmd_analyze, и стадия publish падала
# на импорте common — поймано эмуляцией заявки, ровно тем, чем и должно ловиться.
sys.path.insert(0, str(ROOT))
SUBS = ROOT / "data" / "submissions"
SITE = "https://bridge42worlds.academy"
MAX_MB = 25          # вложение: практический предел почтовых серверов
MAX_LINK_MB = 100    # данные по ссылке из письма — скачиваем и храним у себя
DEFENDER = Path(r"C:\Program Files\Windows Defender\MpCmdRun.exe")


def env():
    out = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def hdr(s):
    parts = email.header.decode_header(s or "")
    return "".join(p.decode(enc or "utf-8", "replace") if isinstance(p, bytes) else p
                   for p, enc in parts)


def _peek_body(msg):
    """Текстовое тело письма — только чтобы поискать в нём наш код работы.

    Полный разбор частей идёт ниже и своим порядком; здесь нужен один быстрый взгляд
    до того, как решится, новая это заявка или продолжение старой."""
    for part in msg.walk():
        if part.get_content_type() == "text/plain" and not part.get_filename():
            raw = part.get_payload(decode=True) or b""
            return raw.decode(part.get_content_charset() or "utf-8", "replace")[:4000]
    return ""


def next_code():
    """Свой препринт-код: b42p-ГОД-NNN. Отдельная сущность, с arXiv не смешивается."""
    year = date.today().year
    existing = sorted(SUBS.glob(f"b42p-{year}-*")) if SUBS.exists() else []
    n = 1 + max((int(p.name.split("-")[-1]) for p in existing), default=0)
    return f"b42p-{year}-{n:03d}"


def defender_scan(path):
    """Проверка Защитником ДО распаковки. Коды MpCmdRun: 0 — чисто, 2 — НАЙДЕНА УГРОЗА,
    остальное — ошибка самой проверки (путь, служба, права).

    ПЕРВАЯ ВЕРСИЯ считала заражённым ЛЮБОЙ ненулевой код и УДАЛЯЛА файл — и удалила
    первую же настоящую заявку владельца (b42p-2026-001, 2026-08-04) на ошибке проверки.
    Два урока в одном: ошибка проверки — не вердикт; и вердикт — не приговор к удалению.
    Теперь: 'clean' / 'infected' / 'error', заражённое уходит в карантин переименованием,
    удаления нет вообще."""
    if not DEFENDER.exists():
        return "error"
    r = subprocess.run([str(DEFENDER), "-Scan", "-ScanType", "3", "-File", str(path)],
                       capture_output=True, text=True, timeout=300)
    if r.returncode == 0:
        return "clean"
    # Код 2 у MpCmdRun — И «найдена угроза», И «скан не удался» (на этой машине Защитник
    # отключён: «Product/Feature disabled», hr=0x80004005 — выяснено на b42p-2026-001).
    # Различаем по тексту: про угрозу он пишет прямо. Ошибка проверки — это «смотреть
    # руками», а не вердикт.
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode == 2 and ("Threat" in out or "found" in out.lower()):
        return "infected"
    return "error"


# Пределы распаковки. Нужны, когда антивирус недоступен и архив — единственное, что нас
# защищает от самого себя: zip-бомба весит мегабайт, а разворачивается в терабайт.
MAX_UNPACKED_GB = 3
MAX_UNPACKED_FILES = 30000
# Исполняемое из чужого архива на диск не кладём вовсе. Работе оно не нужно: код обработки
# автор присылает исходником, а не собранным бинарником.
BAD_SUFFIXES = {".exe", ".dll", ".scr", ".com", ".pif", ".msi", ".bat", ".cmd",
                ".ps1", ".vbs", ".vbe", ".wsf", ".jar", ".lnk", ".reg", ".hta"}


def safe_extract(zpath, dest):
    """Распаковка с защитой от zip-slip: имя с ../ выводит запись из папки — отклоняем.

    Плюс три предела, которые раньше держал за нас антивирус: суммарный объём, число
    файлов и расширения. Возвращает список пропущенного, чтобы это было видно, а не
    случилось молча."""
    skipped = []
    with zipfile.ZipFile(zpath) as z:
        infos = z.infolist()
        if len(infos) > MAX_UNPACKED_FILES:
            raise ValueError(f"в архиве {len(infos)} файлов — больше предела {MAX_UNPACKED_FILES}")
        total = sum(m.file_size for m in infos)
        if total > MAX_UNPACKED_GB * (1 << 30):
            raise ValueError(f"распакованный объём {total >> 30} ГБ — больше предела {MAX_UNPACKED_GB} ГБ")
        keep = []
        for m in infos:
            target = (dest / m.filename).resolve()
            if not str(target).startswith(str(dest.resolve())):
                raise ValueError(f"подозрительный путь в архиве: {m.filename}")
            if Path(m.filename).suffix.lower() in BAD_SUFFIXES:
                skipped.append(m.filename)
                continue
            keep.append(m)
        z.extractall(dest, members=keep)
    return skipped



def direct_link(url):
    """Ссылка из адресной строки облака → ссылка, по которой отдаётся сам файл.

    Автор присылает то, что видит в браузере. Для Google Drive это .../file/d/ID/view —
    страница просмотра; скачав её, мы получим html вместо архива и не заметим этого,
    пока не попробуем распаковать. Возвращаем ссылку на скачивание там, где знаем правило,
    и исходную там, где не знаем.
    """
    m = re.search(r"drive\.google\.com/file/d/([\w-]{10,})", url)
    if m:
        return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    m = re.search(r"drive\.google\.com/open\?id=([\w-]{10,})", url)
    if m:
        return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    # Яндекс.Диск: публичная ссылка отдаётся через их API, прямой нет вовсе
    if "disk.yandex" in url:
        return ("https://cloudapi.yandex.net/v1/disk/public/resources/download"
                f"?public_key={url}")
    if "dropbox.com" in url and "dl=0" in url:
        return url.replace("dl=0", "dl=1")
    return url


def looks_like_page(head):
    """Пришёл html вместо файла? Признак того, что ссылка вела на страницу, а не на данные.

    Проверяем НАЧАЛО содержимого, а не заголовок ответа: облака часто отдают
    content-type: text/html и при отдаче файла тоже, а вот сигнатура не врёт."""
    h = head[:400].lstrip().lower()
    return h.startswith(b"<!doctype html") or h.startswith(b"<html") or b"<head" in h[:200]


def fetch_link(url, dest, max_mb, session=None):
    """Скачать файл по ссылке из письма. Возвращает (имя, размер) или (None, причина).

    Отдельной функцией, потому что путей отказа тут больше, чем кода: ссылка может вести
    на страницу просмотра, на форму подтверждения, на «запросите доступ» — и каждый из этих
    ответов приходит с кодом 200 и типом text/html. Единственный надёжный признак файла —
    его первые байты.
    """
    import requests as _rq
    s = session or _rq.Session()
    H = {"User-Agent": "Mozilla/5.0 bridge42worlds-intake"}
    dl = direct_link(url)

    r = s.get(dl, stream=True, timeout=300, allow_redirects=True, headers=H)
    if r.status_code != 200:
        return None, f"ответ {r.status_code}"
    head = next(r.iter_content(4096), b"")

    # Google Drive: страница «Virus scan warning» с формой подтверждения. Разбираем форму
    # и повторяем запрос её полями — то же самое делает браузер по нажатию «скачать».
    if looks_like_page(head) and "drive.google" in dl:
        page = head + r.content if hasattr(r, "content") else head
        try:
            page = (head + b"".join(r.iter_content(1 << 16))).decode("utf-8", "replace")
        except Exception:
            page = head.decode("utf-8", "replace")
        m = re.search(r'action="([^"]+)"', page)
        if m:
            action = m.group(1).replace("&amp;", "&")
            fields = dict(re.findall(r'name="([^"]+)"\s+value="([^"]*)"', page))
            r = s.get(action, params=fields, stream=True, timeout=300, headers=H)
            head = next(r.iter_content(4096), b"")

    if looks_like_page(head):
        return None, "по ссылке отдаётся веб-страница, а не файл (нет общего доступа?)"

    cd = r.headers.get("content-disposition", "")
    mfn = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', cd)
    name = Path((mfn.group(1) if mfn else url.split("?")[0])).name or "data.bin"

    size = len(head)
    with dest_path_for(dest, name).open("wb") as f:
        f.write(head)
        for chunk in r.iter_content(1 << 20):
            size += len(chunk)
            if size > max_mb * 1024 * 1024:
                f.close()
                dest_path_for(dest, name).unlink(missing_ok=True)
                return None, f"файл больше {max_mb} МБ"
            f.write(chunk)
    return name, size


def dest_path_for(folder, name):
    return folder / ("link_" + Path(name).name)



# Сколько раз работа может вернуться на подготовку. Владелец 2026-08-07: «три попытки
# и хватит». Это не наказание, а признание: если после трёх заходов пакет не собирается,
# дело не в невнимательности, и переписка по кругу не поможет ни нам, ни автору.
MAX_TRIES = 3

# Что должно быть в пакете. Ключ — что ищем, значение — как объяснить автору, зачем.
REQUIRED = [
    (("README.md", "index.html"), "текст работы"),
    (("SELF-REVIEW.md",), "заключение подготовки со строкой «ВЕРДИКТ:»"),
]
EXPECTED_DIRS = [("data", "данные"), ("scripts", "код обработки"), ("figures", "графики")]


def check_package(box):
    """Соответствует ли пакет требованиям. Возвращает (готов, [замечания], вердикт_автора).

    Проверяем СОДЕРЖАНИЕ, а не галочки: файл самопроверки с вердиктом «почти готово»
    означает, что автор сам знает о недоделках — принимать такую работу и потом писать
    о тех же недоделках было бы странно."""
    un = box / "unpacked"
    if not un.exists() or not any(un.rglob("*")):
        return False, ["архив не распаковался или пуст"], ""

    # Корень пакета ищем ПО СОДЕРЖИМОМУ, а не по тому, что папка одна.
    #
    # Автор вправе прислать несколько архивов — например, работу и полный комплект данных
    # отдельно, — и тогда наверху лежит два каталога. Прежнее правило «корень, если папка
    # единственная» в этом случае откатывалось к самой unpacked, где нет ничего, и приёмник
    # честно сообщал «нет README, нет data, нет scripts» при том, что всё это лежало
    # каталогом ниже (поймано на живой заявке 2026-08-08).
    #
    # Признак настоящего корня простой: там лежит SELF-REVIEW.md либо текст работы.
    def _looks_like_root(d):
        n = {p.name for p in d.iterdir()}
        return "SELF-REVIEW.md" in n or bool(n & {"README.md", "index.html"})

    dirs = [d for d in un.iterdir() if d.is_dir()]
    root = un
    if not _looks_like_root(un):
        # Каталог с заключением подготовки главнее: полный комплект данных его не содержит.
        best = [d for d in dirs if (d / "SELF-REVIEW.md").exists()] or \
               [d for d in dirs if _looks_like_root(d)]
        if best:
            root = best[0]

    problems = []
    names = {p.name for p in root.iterdir()}

    for variants, what in REQUIRED:
        if not (names & set(variants)):
            problems.append(f"нет файла {' или '.join(variants)} — {what}")

    for d, what in EXPECTED_DIRS:
        if d not in names:
            # Не всякая работа имеет код или данные — говорим мягко, но говорим
            problems.append(f"нет папки {d}/ — {what}; если их нет по существу работы, "
                            f"так и напишите в SELF-REVIEW.md")

    verdict = ""
    sr = root / "SELF-REVIEW.md"
    if sr.exists():
        head = sr.read_text(encoding="utf-8", errors="replace").strip().splitlines()
        first = next((l for l in head if l.strip()), "")
        if not first.upper().startswith("ВЕРДИКТ"):
            problems.append("SELF-REVIEW.md не начинается со строки «ВЕРДИКТ:» — "
                            "именно её читает приёмник")
        else:
            verdict = first.strip()
            if "ГОТОВО К ОТПРАВКЕ" not in first.upper():
                # Автор сам отметил недоделки — принимать нельзя, но и придираться не за что
                problems.append(f"в заключении стоит «{first.strip()}» — "
                                f"работа помечена как незавершённая самим автором")

    return (not problems), problems, verdict


def tries_count(box, digest):
    """Сколько раз ЭТА работа уже возвращалась. Считаем по отпечатку архива.

    Отпечаток, а не имя файла и не тема письма: автор может переименовать архив или
    сменить тему, но если содержимое то же самое — это та же попытка. А если он
    действительно переделал работу, отпечаток изменится, и счёт начнётся заново —
    что справедливо, ведь это уже другая работа."""
    hist = box.parent / "_tries.json"
    try:
        data = json.loads(hist.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    return data.get(digest, 0), hist, data


def bump_try(hist, data, digest):
    data[digest] = data.get(digest, 0) + 1
    hist.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data[digest]


def package_digest(box):
    """Отпечаток содержимого пакета: имена и размеры файлов, без чтения гигабайтов."""
    un = box / "unpacked"
    if not un.exists():
        return ""
    parts = sorted(f"{p.relative_to(un).as_posix()}:{p.stat().st_size}"
                   for p in un.rglob("*") if p.is_file())
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:16]


def cmd_fetch():
    e = env()
    host = e.get("MAIL_HOST")
    user = "article@bridge42worlds.academy"
    pw = e.get("MAIL_PASS")
    m = imaplib.IMAP4_SSL(host, int(e.get("MAIL_IMAP_PORT", 993)))
    m.login(user, pw)
    m.select("INBOX")
    _, data = m.search(None, "UNSEEN")
    ids = data[0].split()
    print(f"новых писем: {len(ids)}")
    for num in ids:
        _, d = m.fetch(num, "(RFC822)")
        msg = email.message_from_bytes(d[0][1])
        frm = hdr(msg.get("From"))
        subj = hdr(msg.get("Subject"))
        mail_addr = re.search(r"[\w.+-]+@[\w.-]+", frm)

        # СЛУЖЕБНЫЕ ПИСЬМА — не заявки. Отчёт о недоставке, автоответ «я в отпуске»,
        # уведомление рассылки: всё это приходит в тот же ящик и выглядит как письмо
        # от человека. 8 августа автомат завёл заявку b42p-2026-002 на отчёт Mailer-Daemon
        # о том, что наше же письмо не дошло, — и вежливо ответил почтовому роботу
        # с просьбой прогнать промпт подготовки.
        addr = (mail_addr.group(0) if mail_addr else "").lower()
        auto = (msg.get("Auto-Submitted", "").lower().startswith("auto")
                or msg.get("X-Autoreply")
                or msg.get("X-Failed-Recipients")
                or any(x in addr for x in ("mailer-daemon", "postmaster", "no-reply",
                                           "noreply", "bounce", "notification"))
                or any(x in (subj or "").lower() for x in
                       ("mail delivery failed", "undelivered mail", "delivery status",
                        "returning message to sender", "автоответ", "out of office")))
        if auto:
            print(f"  ↩️ служебное письмо, не заявка: {subj[:60]}")
            # Помечаем прочитанным и идём дальше: заявку не заводим, но и не теряем —
            # письмо остаётся в ящике, человек его увидит.
            continue

        # ПОВТОРНЫЙ ЗАХОД ПО ТОЙ ЖЕ РАБОТЕ, а не новая заявка.
        #
        # Автор отвечает на наше письмо, и в теме остаётся «Re: b42p-2026-001: …». Раньше
        # такое письмо заводило ВТОРУЮ заявку с новым кодом — и вместе с кодом обнулялось
        # всё: счёт попыток (три круга не срабатывали никогда), прошлый разбор (правило
        # «посмотри, ответил ли автор на вопросы» проверять было не с чем), ключ управления
        # публикацией. У человека на руках оказывалось два кода на одну работу.
        #
        # Ищем свой код в теме и в теле. Нашли живую заявку — продолжаем её.
        prev_code = ""
        for m_code in re.finditer(r"b42p-\d{4}-\d{3}", f"{subj}\n{_peek_body(msg)}"):
            if (SUBS / m_code.group(0)).is_dir():
                prev_code = m_code.group(0)
                break

        if prev_code:
            code = prev_code
            box = SUBS / code
            # Прошлый разбор сохраняем ДО того, как новый прогон его перезапишет: он нужен
            # рецензенту, чтобы проверить, ответил ли автор на наши вопросы.
            rv, rp = box / "review.md", box / "review-prev.md"
            if rv.exists() and not rp.exists():
                rp.write_text(rv.read_text(encoding="utf-8"), encoding="utf-8")
            # Прошлые файлы не затираем и не мешаем с новыми: сдвигаем в incoming-N.
            inc = box / "incoming"
            if inc.exists() and any(inc.iterdir()):
                n_old = 1
                while (box / f"incoming-{n_old}").exists():
                    n_old += 1
                inc.rename(box / f"incoming-{n_old}")
            # Распакованное — от прошлой версии; оставить значит разобрать старую работу.
            if (box / "unpacked").exists():
                shutil.rmtree(box / "unpacked", ignore_errors=True)

            # ОПУБЛИКОВАННУЮ версию сохраняем, а не затираем.
            #
            # Автор переписал работу и шлёт новую — прежняя при этом перестаёт быть черновиком
            # и становится ИСТОРИЕЙ: на неё могли сослаться, её могли скачать. У arXiv для
            # этого есть v1, v2, и причина та же. Кладём прежние PDF, архив и живую версию
            # рядом, в подпапку версии; адрес самой статьи не меняется.
            try:
                was_meta = json.loads((box / "meta.json").read_text(encoding="utf-8"))
            except Exception:
                was_meta = {}
            if was_meta.get("status") == "published":
                pub_dir = ROOT / "lang" / "ru" / "community" / code
                if pub_dir.exists():
                    ver = 1
                    while (pub_dir / f"v{ver}").exists():
                        ver += 1
                    keep = pub_dir / f"v{ver}"
                    keep.mkdir(parents=True, exist_ok=True)
                    # Обложку КОПИРУЕМ, остальное переносим.
                    #
                    # Владелец 2026-08-09: «только ссылки не меняй». Главные адреса и должны
                    # вести на свежую версию — так же, как /abs/2310.15936 на arXiv всегда
                    # показывает последнюю. Но обложка у нас НАША, а не авторская, и при
                    # обновлении версии заново не рисуется: сдвинь её в v1 — и страница
                    # останется без картинки, хотя ссылка формально цела.
                    KEEP_IN_PLACE = ("cover.jpg", "cover.webp")
                    for item in list(pub_dir.iterdir()):
                        if item.name.startswith("v") and item.name[1:].isdigit():
                            continue
                        try:
                            if item.name in KEEP_IN_PLACE:
                                shutil.copy2(str(item), str(keep / item.name))
                            else:
                                shutil.move(str(item), str(keep / item.name))
                        except Exception as ex:
                            print(f"     ⚠️ {item.name}: {ex}")
                    print(f"  🗄️ прежняя версия сохранена как v{ver}")
                    meta_ver = ver + 1
                else:
                    meta_ver = 2
            else:
                meta_ver = was_meta.get("version", 1)
            print(f"  🔁 повторный заход по {code}")
        else:
            code = next_code()
            box = SUBS / code
        (box / "incoming").mkdir(parents=True, exist_ok=True)

        body = ""
        files = []
        for part in msg.walk():
            fn = part.get_filename()
            if fn:
                fn = hdr(fn)
                payload = part.get_payload(decode=True) or b""
                if len(payload) > MAX_MB * 1024 * 1024:
                    print(f"  ⚠️ {fn}: больше {MAX_MB} МБ — пропущен, попросим ссылкой")
                    continue
                p = box / "incoming" / Path(fn).name
                p.write_bytes(payload)
                files.append(p.name)
            elif part.get_content_type() == "text/plain" and not body:
                body = (part.get_payload(decode=True) or b"").decode(
                    part.get_content_charset() or "utf-8", "replace")

        # Автор: почту фиксируем ВСЕГДА (канал связи), имя — только если он сам подписался.
        # В справочник авторов сайта НЕ добавляем (решение владельца): это отдельный мир.
        meta = {
            "code": code, "received": date.today().isoformat(),
            "email": mail_addr.group(0) if mail_addr else "",
            "subject": subj, "files": files, "status": "received",
            "author_token": "b42a-" + secrets.token_urlsafe(9),
        }
        # На повторном заходе часть прежнего переносим: ключ управления публикацией автор
        # уже держит на руках (менять его — значит сломать ему доступ), дата первого
        # обращения — его, а не сегодняшняя, и счёт попыток продолжается, а не начинается.
        if prev_code and (box / "meta.json").exists():
            try:
                was = json.loads((box / "meta.json").read_text(encoding="utf-8"))
            except Exception:
                was = {}
            for k in ("author_token", "received", "author_name", "kind",
                      "author_comment", "attempt", "package_digest"):
                if was.get(k):
                    meta[k] = was[k]
            meta["subject"] = was.get("subject") or subj   # тема «Re: …» хуже исходной
            meta["version"] = meta_ver
            meta["repeat_of"] = was.get("attempt", 1)
        (box / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
        # Письмо повторного захода дописываем к прежнему, а не затираем: в теле бывают
        # ответы на наши вопросы, и потерять их значит спросить то же самое второй раз.
        if prev_code and (box / "letter.txt").exists():
            was_letter = (box / "letter.txt").read_text(encoding="utf-8")
            body = f"{was_letter}\n\n─── повторный заход, {date.today().isoformat()} ───\n\n{body}"
        (box / "letter.txt").write_text(body, encoding="utf-8")

        # Антивирус до всякой распаковки.
        #
        # Проверка ОДНОГО файла вынесена в функцию не для красоты: раньше скан шёл одним
        # циклом ДО скачивания по ссылкам, а скачанное добавлялось в files уже после него.
        # Вердикта для link_* не появлялось вовсе, и распаковка ниже пропускала такой архив:
        # verdicts.get(fn) возвращал None, а условие сравнивало с «УГРОЗА». То есть архив
        # с чужого сервера распаковывался НЕПРОВЕРЕННЫМ, при том что комментарий рядом
        # обещал обратное (найдено разведкой 2026-08-06). Теперь проверяется каждый файл
        # в момент появления, чем бы он ни пришёл.
        verdicts = {}

        def scan_one(fn):
            v = defender_scan(box / "incoming" / fn)
            verdicts[fn] = {"clean": "чисто", "infected": "УГРОЗА — в карантине",
                            "error": "проверка не удалась — смотреть руками"}[v]
            if v == "infected":
                src = box / "incoming" / fn
                src.rename(src.with_suffix(src.suffix + ".quarantine"))
                print(f"  🛑 {fn}: угроза, файл в карантине")
            return v

        for fn in files:
            scan_one(fn)

        # ССЫЛКИ НА ДАННЫЕ в теле письма (решение владельца 2026-08-05: «данных может
        # быть много — пусть присылают всё, до 100 МБ; хранить дёшево»). Почта режет
        # вложения ~25 МБ, поэтому большие данные — ссылкой: мы скачиваем и размещаем
        # у себя (R2: полтора цента в месяц за 100 МБ, отдача читателям бесплатная).
        # Безопасность: только http(s), потолок размера продавлен потоком (не верим
        # Content-Length), скачанное проходит тот же скан, что вложения.
        import requests as _rq
        _sess = _rq.Session()
        for m2 in list(re.finditer(r"https?://[^\s<>\"']+", body))[:5]:
            url = m2.group(0).rstrip('.,)')
            if any(h in url for h in ("bridge42worlds", "mailto:")):
                continue
            name, res = fetch_link(url, box / "incoming", MAX_LINK_MB, _sess)
            if not name:
                # Причину показываем и себе, и потом автору: «не смогли скачать» без
                # объяснения выглядит как «ваша работа нам не нужна».
                print(f"  ⚠️ ссылка {url[:55]}: {res}")
                continue
            fn = "link_" + Path(name).name
            files.append(fn)
            print(f"  🔗 скачано по ссылке: {name} · {res // 1024 // 1024} МБ")
            scan_one(fn)

        # ПРОВЕРКА СЛЕДОВ ПРОМПТА ПОДГОТОВКИ (правило владельца 2026-08-05: «если видно,
        # что промпт не обрабатывался — по форматам, структуре хранения, первичному
        # заключению — не принимаем; архив должен быть сделан по промпту»). Робот ищет
        # SELF-REVIEW.md со строкой «ВЕРДИКТ:». Нет следов — статус needs-prompt и
        # заготовка вежливого ответа: это не отказ, а единственный вход.
        meta["prepared"] = False

        # zip распаковываем только чистые
        for fn in list(files):
            p = box / "incoming" / fn
            # Распаковываем только то, что ЯВНО признано чистым. Прежнее условие
            # «не равно УГРОЗА» пропускало файл без вердикта — то есть любую дыру
            # в учёте оно превращало в распаковку непроверенного архива.
            # «Чисто» — распаковываем. «Проверка не удалась» — тоже распаковываем, но
            # осознанно и с пометкой: на этой машине Защитник отключён, вердикт всегда
            # «error», и прежнее условие означало, что не распакуется НИ ОДНА работа —
            # автомат молча возвращал каждому автору «нет следов подготовки» (найдено на
            # живой заявке 2026-08-08). Отсутствие антивируса не повод остановить приём;
            # повод — заменить его пределами распаковки и сказать об этом вслух.
            # «УГРОЗА» не распаковывается ни при каких условиях.
            v = verdicts.get(fn)
            if p.suffix.lower() == ".zip" and p.exists() and v in ("чисто", "проверка не удалась — смотреть руками"):
                try:
                    skipped = safe_extract(p, box / "unpacked")
                    note = "" if v == "чисто" else " (антивирус недоступен — распакован под пределами)"
                    print(f"  📦 {fn} распакован{note}")
                    if skipped:
                        print(f"     ⚠️ не распакованы исполняемые: {', '.join(skipped[:5])}"
                              + (f" и ещё {len(skipped) - 5}" if len(skipped) > 5 else ""))
                        meta["skipped_executables"] = skipped[:50]
                except Exception as ex:
                    print(f"  ⚠️ {fn}: {ex}")
                    meta["unpack_error"] = str(ex)

        un = box / "unpacked"
        sr = list(un.rglob("SELF-REVIEW.md")) if un.exists() else []
        if sr and "ВЕРДИКТ:" in sr[0].read_text(encoding="utf-8", errors="replace")[:200]:
            meta["prepared"] = True
        (box / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
        if not meta["prepared"]:
            NL2 = chr(10) + chr(10)
            (box / "reply-needs-prompt.txt").write_text(
                "Здравствуйте!" + NL2 +
                "Спасибо за работу. Чтобы мы могли её разобрать, пропустите материалы через "
                "наш промпт подготовки — он проверит логику, соберёт пакет в нужной структуре "
                "и напишет первичное заключение. Это займёт минут пять с любым сильным "
                "ИИ-ассистентом." + NL2 +
                "Промпт: https://bridge42worlds.academy/data/prompts/author-self-check.txt" + chr(10) +
                "Инструкция: https://bridge42worlds.academy/lang/ru/community/" + NL2 +
                "Это не отказ — это единственный вход: подготовленная работа проходит наш "
                "разбор с первого раза." + NL2 + "bridge42worlds", encoding="utf-8")
            print(f"  ⚠️ {code}: следов промпта подготовки нет — заготовлен ответ needs-prompt")
        print(f"  ✅ {code} · от {meta['email'] or 'без адреса'} · файлов {len(files)} · "
              f"подготовлен: {'да' if meta['prepared'] else 'НЕТ'}")
    m.logout()
    return 0


# Промпт разбора живёт файлом (data/prompts/submission-analyze.txt), как все остальные:
# он был единственным вшитым в исходник, и правка тона требовала правки кода. А тон здесь
# менялся решением владельца дважды — «помогаем, а не лечим» и «если целостно, не копай».



def cmd_analyze(code):
    box = SUBS / code
    meta = json.loads((box / "meta.json").read_text(encoding="utf-8"))
    text = (box / "letter.txt").read_text(encoding="utf-8")

    def readable(p):
        """HTML — В ТЕКСТ до подачи рецензенту. Первый прогон скормил модели сырой html:
        40 КБ стилей и скриптов съели лимит, до анализа автора модель не дошла — и честно
        отрецензировала работу как «без выводов», хотя выводы там есть. Рецензия по
        обёртке вместо содержания хуже отсутствия рецензии (b42p-2026-001)."""
        raw = p.read_text(encoding="utf-8", errors="replace")
        if p.suffix.lower() in (".html", ".htm"):
            import re as _re
            import html as _h
            raw = _re.sub(r"<script.*?</script>|<style.*?</style>", "", raw, flags=_re.S)
            raw = _re.sub(r"<[^>]+>", " ", raw)
            raw = _h.unescape(_re.sub(r"[ \t]+", " ", raw))
        return raw

    csv_seen = 0
    for p in sorted(box.rglob("*")):
        if not p.is_file():
            continue
        suf = p.suffix.lower()
        if suf in (".txt", ".md", ".html", ".htm"):
            text += f"\n\n=== файл {p.name} ===\n" + readable(p)[:40000]
        elif suf == ".csv" and csv_seen < 2:   # пара образцов данных, не все двести
            csv_seen += 1
            text += f"\n\n=== образец данных {p.name} ===\n" + p.read_text(encoding="utf-8", errors="replace")[:3000]
    figs = [f.name for f in box.rglob("*.png")]
    if figs:
        text += "\n\n=== приложенные графики ===\n" + ", ".join(figs)
    sys.path.insert(0, str(ROOT))
    from common import chat
    # common.chat всегда требует JSON-ответ (response_format) — просим разбор объектом
    # и собираем в читаемый вид сами.
    ask_json = ('\n\nОтветь JSON: {"суть":"...","вменяемость":"...","логичность":"...",'
                '"завершённость":"...","корректность_и_сила":"...",'
                '"что_поправить":["..."],"вопросы_автору":["..."],'
                '"вердикт":"publish|revise|decline","почему":"..."}')
    from common import load_prompt
    # ПОВТОРНЫЙ ЗАХОД разбирается иначе, чем первый (правило владельца 2026-08-08).
    # Если работа приходит второй раз, рецензент обязан сперва посмотреть, что мы у автора
    # спрашивали, и ответил ли он. Без этого второй разбор пишется с чистого листа и может
    # задать те же вопросы заново — автор справедливо решит, что его не читали.
    #
    # Порог возврата тут намеренно высокий: «если условно ничего сильно неправильного —
    # пропускай». Работа между заходами всегда немного меняется, и гонять её по кругу за
    # мелкие расхождения — это не строгость, а неспособность остановиться.
    prev = ""
    old = box / "review-prev.md"
    cur = box / "review.md"
    if cur.exists() and not old.exists():
        # Прошлый разбор сохраняем ДО того, как перезапишем его новым.
        old.write_text(cur.read_text(encoding="utf-8"), encoding="utf-8")
    if old.exists():
        prev = old.read_text(encoding="utf-8")

    prompt = load_prompt("submission-analyze").replace("{work}", text[:120000])
    prompt = prompt.replace("{previous_review}", prev or "— работа пришла впервые —")
    r = chat("article_advanced", prompt,
             system="Ты научный рецензент открытой площадки. Отвечай на языке работы автора.")
    import json as _j
    from common import clean_json
    d = _j.loads(clean_json(r.choices[0].message.content))
    parts = []
    NL = "\n"
    if d.get("суть"):
        parts.append("## Суть работы" + NL + NL + str(d["суть"]))
    if d.get("вид"):
        parts.append("## Вид" + NL + NL + str(d["вид"]).capitalize())
    if d.get("сильная_сторона"):
        parts.append("## Сильная сторона" + NL + NL + str(d["сильная_сторона"]))
    if d.get("рекомендации"):
        parts.append("## Рекомендации по методике" + NL + NL +
                     NL.join(f"{i+1}. {x}" for i, x in enumerate(d["рекомендации"])))
    # Пустой список вопросов — нормальный исход, а не пропуск: владелец просил не
    # спрашивать ради формы. Пишем об этом прямо, чтобы автор не ждал вопросов.
    if d.get("вопросы"):
        parts.append("## Вопросы автору" + NL + NL +
                     NL.join(f"{i+1}. {x}" for i, x in enumerate(d["вопросы"])))
    else:
        parts.append("## Вопросы автору" + NL + NL + "Вопросов нет — работа понятна как есть.")
    parts.append("## Вердикт" + NL + NL +
                 f"**{d.get('вердикт', '?')}** — {d.get('почему', '')}")
    review = (NL + NL).join(parts)
    (box / "review.md").write_text(review, encoding="utf-8")
    # Вид работы нужен дальше: по нему ставится плашка на странице и
    # выбирается, о чём спрашивать автора при доработке.
    meta["kind"] = d.get("вид", "")
    (box / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                   encoding="utf-8")

    # Похожие работы — локальным вектором по нашему корпусу (тот же приём, что related-vec)
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import linear_kernel
        ids, texts, titles = [], [], {}
        for p in sorted((ROOT / "lang/ru/archive").glob("*/*/data.json")):
            d = json.loads(p.read_text(encoding="utf-8"))
            v = (d.get("popular", {}) or {}).get("ru") or {}
            if isinstance(v, dict) and v.get("title"):
                ids.append(p.parent.name)
                texts.append(v.get("title", "") + " " + v.get("description", "") + " " + v.get("text", "")[:4000])
                titles[p.parent.name] = v["title"]
        vec = TfidfVectorizer(min_df=3, max_df=0.4, sublinear_tf=True)
        X = vec.fit_transform(texts + [text[:20000]])
        sim = linear_kernel(X[-1], X[:-1])[0]
        import numpy as np
        best = np.argsort(sim)[::-1][:5]
        similar = [{"id": ids[i], "title": titles[ids[i]], "score": round(float(sim[i]), 3)}
                   for i in best if sim[i] > 0.05]
    except Exception as ex:
        similar = []
        print(f"  ⚠️ похожие не посчитались: {ex}")
    (box / "similar.json").write_text(json.dumps(similar, ensure_ascii=False, indent=1),
                                      encoding="utf-8")

    meta["status"] = "analyzed"
    (box / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ разбор: {box / 'review.md'}")
    print(f"   похожих: {len(similar)}")
    for s in similar:
        print(f"     {s['score']}  {s['title'][:60]}")
    print("\nДальше: посмотреть review.md глазами → publish")
    return 0


def _captions(work_text, images, lang="ru"):
    """Подписи к иллюстрациям автора: {имя_файла: подпись}. Пишет модель по тексту работы.

    Почему не берём подписи из html автора: они там не всегда есть, а где есть — часто
    служебные («Рис. 4»). Читателю нужно знать, ЧТО на графике и почему он важен, а это
    видно только из текста работы.

    Дальше подписи переводятся на остальные языки вместе с пересказом: картинка одна и
    та же на всех страницах, а объяснять её арабскому читателю по-русски — не объяснять.
    """
    from common import chat, clean_json
    names = [im.get("src") or im.get("file") for im in images]
    NL = "\n"
    prompt = (
        "Ниже текст научной работы и список файлов иллюстраций к ней." + NL +
        "Для КАЖДОГО файла напиши короткую подпись: что на изображении и что по нему видно." + NL +
        "Одно-два предложения, живым языком, без «Рис. N» и без пересказа всей работы." + NL +
        "Если по тексту непонятно, что на изображении, дай пустую строку — выдумывать нельзя." +
        NL + NL + "ФАЙЛЫ:" + NL + NL.join(f"- {n}" for n in names) +
        NL + NL + "ТЕКСТ РАБОТЫ:" + NL + work_text[:60000] + NL + NL +
        'Ответь JSON: {"подписи": {"имя файла": "подпись", ...}}'
    )
    try:
        r = chat("article_popular", prompt,
                 system="Ты подписываешь иллюстрации к научной работе для широкого читателя.")
        d = json.loads(clean_json(r.choices[0].message.content))
        got = d.get("подписи") or d.get("captions") or {}
    except Exception as ex:
        print(f"  ⚠️ подписи к картинкам не сошлись: {type(ex).__name__}")
        return {}
    # Ключи возвращаем в терминах файлов на сайте: модель отвечает по исходным путям.
    by_src = {(im.get("src") or im.get("file")): im["file"] for im in images}
    out = {}
    for k, v in got.items():
        f = by_src.get(k) or by_src.get(Path(k).name) or k
        if str(v).strip():
            out[f] = str(v).strip()
    print(f"  ✍️ подписей к картинкам: {len(out)} из {len(images)}")

    # Подписи переводятся, как и всё остальное на странице. Иначе арабский читатель
    # получает арабский интерфейс, арабский пересказ — и русские подписи под картинками.
    # На этих же граблях мы уже стояли с разбором: страница выходила на треть по-русски.
    res = {"ru": out}
    if out:
        keys = list(out)
        for lang in ("en", "es", "ar", "fr"):
            try:
                rr = chat("translate_flash",
                          "Переведи подписи к иллюстрациям научной работы. Верни JSON с теми же "
                          "ключами и переведёнными значениями, ничего не добавляя и не убирая." + NL +
                          f"Целевой язык (код): {lang}" + NL + NL +
                          json.dumps(out, ensure_ascii=False),
                          system=f"Ты переводчик. Отвечай только на языке с кодом {lang}.")
                got = json.loads(clean_json(rr.choices[0].message.content))
                # Ключи модель иногда переводит вместе со значениями — сопоставляем по порядку.
                if set(got) != set(keys) and len(got) == len(keys):
                    got = dict(zip(keys, list(got.values())))
                res[lang] = {k: str(v).strip() for k, v in got.items() if str(v).strip()}
                print(f"  🌐 {lang}: подписи переведены ({len(res[lang])})")
            except Exception:
                # Молчать нельзя: без подписи картинка на этом языке останется голой.
                print(f"  ⚠️ {lang}: подписи не перевелись — картинки выйдут без них")
    return res


def _pick_tags(work_text, title, limit=8):
    """Теги работы из нашего ЗАКРЫТОГО словаря. Придумывать новые нельзя.

    Придуманный тег ведёт на несуществующую страницу и портит облако; на этом мы уже
    стояли, когда физический словарь применяли к биологии. Поэтому модель выбирает из
    списка, а всё, чего в списке нет, отбрасывается кодом.
    """
    from common import chat, clean_json
    p = ROOT / "lang" / "ru" / "data" / "tags-list.json"
    if not p.exists():
        return []
    known = json.loads(p.read_text(encoding="utf-8"))
    # Список тегов — это список записей вида {"ru": …, "en": …, "type": …, "domain": …},
    # а идентификатор тега (и имя его страницы) — английское поле.
    if isinstance(known, dict):
        known = list(known.keys())
    else:
        known = [t.get("en") or t.get("ru") for t in known if isinstance(t, dict)] or \
                [t for t in known if isinstance(t, str)]
    known = [k for k in known if k]
    NL = chr(10)
    ask = ("Выбери из списка теги, которые ТОЧНО подходят этой научной работе." + NL +
           f"Не больше {limit}. Только из списка, ничего своего не добавляй." + NL +
           "Если подходит меньше — верни меньше, пустой список тоже нормальный ответ." + NL + NL +
           "СПИСОК ТЕГОВ:" + NL + ", ".join(known) + NL + NL +
           f"РАБОТА: {title}" + NL + work_text[:24000] + NL + NL +
           'Ответь JSON: {"tags": ["...", "..."]}')
    try:
        r = chat("article_kind", ask, system="Ты размечаешь научные работы тегами из закрытого словаря.")
        got = json.loads(clean_json(r.choices[0].message.content)).get("tags", [])
    except Exception as ex:
        print(f"  ⚠️ теги не выбрались: {type(ex).__name__}")
        return []
    ks = set(known)
    out = [t for t in got if t in ks][:limit]
    print(f"  🏷️ тегов: {len(out)} — {', '.join(out[:6])}")
    return out


def _laws_for_tags(tags, limit=6):
    """Законы природы, связанные с тегами работы. Тот же принцип связи, что на статье."""
    p = ROOT / "lang" / "ru" / "data" / "laws.json"
    if not p.exists() or not tags:
        return []
    try:
        laws = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    ts = set(tags)
    out = [lid for lid, L in laws.items() if ts & set((L or {}).get("tags", []))][:limit]
    if out:
        print(f"  ⚖️ законов: {len(out)}")
    return out


def _our_take(text, title, lang="ru"):
    """Наша обработка: пересказ работы на трёх уровнях глубины.

    Витрина раздела по ТЗ — именно наш пересказ, а не текст автора: читатель приходит
    к нам за понятным изложением, а точный текст остаётся под кнопкой «исходный вариант».
    Уровни те же, что у обычных статей, чтобы читателю не пришлось учиться заново."""
    from common import chat, clean_json, load_prompt
    import json as _j
    prompt = load_prompt("submission-retell").replace("{title}", title or "").replace(
        "{work}", (text or "")[:60000])
    try:
        r = chat("article_popular", prompt,
                 system="Ты научный журналист. Отвечай JSON-объектом, на русском языке.")
        d = _j.loads(clean_json(r.choices[0].message.content))
        return {k: d.get(k, "") for k in ("title", "oneliner", "mini", "simple", "advanced")}
    except Exception as ex:
        print(f"  ⚠️ пересказ не вышел: {type(ex).__name__} — страница выйдет без нашей обработки")
        return {}


def cmd_publish(code, langs=None):
    """Публикация работы: постоянный адрес /lang/{lang}/community/{code}/ на пяти языках.

    Адрес постоянный и предсказуемый — так и задумано: работа участвует в поиске и в срезах,
    как обычная статья. Защита живёт не в адресе, а в токене снятия: автор в любой момент
    убирает публикацию, и Worker начинает отдавать 410 вместо страницы.
    """
    box = SUBS / code
    meta = json.loads((box / "meta.json").read_text(encoding="utf-8"))
    letter = (box / "letter.txt").read_text(encoding="utf-8") if (box / "letter.txt").exists() else ""
    similar = json.loads((box / "similar.json").read_text(encoding="utf-8")) if (box / "similar.json").exists() else []

    # Текст работы: распакованное содержимое, если есть, иначе тело письма
    text = letter
    un = box / "unpacked"
    if un.exists():
        chunks = []
        for f in sorted(un.rglob("*")):
            if f.suffix.lower() in (".md", ".txt") and f.stat().st_size < 400000:
                chunks.append(f.read_text(encoding="utf-8", errors="replace"))
        if chunks:
            text = "\n\n".join(chunks)[:200000]

    title = meta.get("subject") or code
    ours_ru = _our_take(text, title)

    # Пересказ переводится на остальные языки, как обычная статья (решение владельца
    # 2026-08-06). Витрина раздела — наша обработка, и разделять читателей по языку там,
    # где мы уже взялись обрабатывать, странно: арабский читатель получал бы страницу
    # с арабским интерфейсом и русским текстом внутри. Порядка четырёх центов на работу.
    ours = {"ru": ours_ru} if ours_ru else {}
    if ours_ru:
        from gen_llm import translate_scipop
        for lang in ("en", "es", "ar", "fr"):
            got = translate_scipop(ours_ru, lang)
            if got:
                ours[lang] = got
                print(f"  🌐 {lang}: пересказ переведён")
            else:
                # Молчать нельзя: страница на этом языке выйдет с русским текстом,
                # и заметит это только читатель.
                print(f"  ⚠️ {lang}: перевод не сошёлся — страница выйдет на языке-источнике")

    # РАЗБОР ТОЖЕ ПЕРЕВОДИТСЯ. Эмуляция показала: интерфейс и пересказ переведены,
    # а разбор оставался русским — и арабская страница выходила на треть по-русски.
    # Читателю всё равно, какой у текста источник: он видит одну страницу, и она обязана
    # быть на его языке целиком.
    review_ru = _review_parts(box)
    review_all = {"ru": review_ru}
    if review_ru:
        from gen_llm import translate_scipop
        for lang in ("en", "es", "ar", "fr"):
            got = translate_scipop(review_ru, lang)
            review_all[lang] = got or review_ru
            if not got:
                print(f"  ⚠️ {lang}: разбор не перевёлся — выйдет на языке-источнике")

    # МАТЕРИАЛЫ РАБОТЫ — кодом, без модели: PDF, картинки, полный комплект.
    import submission_assets
    assets = submission_assets.build(code)

    # ПОДПИСИ К КАРТИНКАМ — а вот это модель. Имя файла comb_histogram.png читателю не
    # говорит ничего, и картинка без подписи в научной работе бесполезна: непонятно,
    # на что смотреть. Модель читает работу, находит, где график упоминается, и пишет
    # подпись по-человечески. Переводится, как и всё остальное на странице.
    captions = {}
    if assets.get("images"):
        captions = _captions(text, assets["images"])

    # ТЕГИ И ЗАКОНЫ — из нашего же словаря, как у обычной статьи.
    #
    # Владелец 2026-08-08: «не вижу наших обычных тегов, законов и так далее — немного не
    # по уставу всё… причеши по рядовому подходу». Он прав: авторскую работу должна
    # выделять плашка и обложка, а не отсутствие обычной разметки. Без тегов работа
    # выпадает из графа знаний и из всех перекрёстных связей сайта.
    #
    # Словарь ЗАКРЫТЫЙ: модель выбирает из существующих тегов, а не придумывает свои —
    # придуманный тег ведёт на несуществующую страницу и ломает облако.
    tags = _pick_tags(text, title)
    laws = _laws_for_tags(tags)

    # ПРИВАТНОЕ СЮДА НЕ ПОПАДАЕТ. publish.json уезжает на сайт, meta.json — нет.
    # Почта автора и токен остаются в meta.json; здесь только то, что можно показывать.
    # ДАТА ПУБЛИКАЦИИ НЕ ЕЗДИТ.
    #
    # `received` — дата первого письма автора, и она своя (7 августа). Дата публикации —
    # другая (8 августа). Подставив первую, вторая редакция уехала в архив на день назад
    # и задвоила статью: папки 2026-08-07 и 2026-08-08 с одним и тем же кодом.
    # Публикуемся один раз; при обновлении версии дата остаётся той, что была.
    from datetime import date as _date
    prev_pub = {}
    if (box / "publish.json").exists():
        try:
            prev_pub = json.loads((box / "publish.json").read_text(encoding="utf-8"))
        except Exception:
            prev_pub = {}
    pub_date = prev_pub.get("received") or meta.get("published_date") or _date.today().isoformat()

    pub = {
        "code": code,
        "received": pub_date,
        "title": title,
        "kind": meta.get("kind", ""),
        "author_display": meta.get("author_name") or "",
        "ours": ours,
        "review": review_all,
        "similar": similar[:5],
        # Материалы работы: PDF, картинки, полный комплект. Собираются кодом (см.
        # tools/submission_assets.py) — распаковать, свернуть в PDF, скопировать, сжать.
        # Адрес source.zip раньше стоял здесь жёстко, а файл туда никто не клал: кнопка
        # на странице вела в 404 всё время, пока раздел существовал.
        "pdf_url": assets.get("pdf_url", ""),
        "archive_url": assets.get("archive_url", ""),
        "archive_mb": assets.get("archive_mb", 0),
        "images": assets.get("images", []),
        "captions": captions,
        "source_url": assets.get("pdf_url", "") or assets.get("archive_url", ""),
        "source_meta": meta.get("source_meta", ""),
        "author_comment": meta.get("author_comment", ""),
        "withdrawn": False,
    }
    (box / "publish.json").write_text(json.dumps(pub, ensure_ascii=False, indent=1),
                                      encoding="utf-8")

    import community_pages
    made = community_pages.build_work(code, langs=langs)
    for lang in (langs or community_pages.LANGS):
        community_pages.build_index(lang)

    meta["status"] = "published"
    meta["url"] = f"{SITE}/lang/ru/community/{code}/"
    (box / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ опубликовано: {meta['url']}")
    print(f"   страниц собрано: {len(made)}")
    print(f"   токен автора: {meta['author_token']} — вернуть ему в письме")
    print("   зарегистрировать токен для снятия: python cloudflare/submissions_sync.py")
    return 0


def _review_parts(box):
    """Разбор в частях, как его ждёт страница: сильная сторона, советы, вопросы.

    Читаем из review.md по заголовкам, а не храним отдельно: файл разбора остаётся
    единственным источником, и правка руками в нём сразу видна на странице."""
    p = box / "review.md"
    if not p.exists():
        return {}
    t = p.read_text(encoding="utf-8")

    def section(name):
        m = re.search(rf"##\s*{name}\s*\n(.*?)(?=\n##|\Z)", t, re.S | re.I)
        return m.group(1).strip() if m else ""

    def items(name):
        body = section(name)
        return [re.sub(r"^\d+\.\s*", "", x).strip()
                for x in body.split("\n") if x.strip()] if body else []

    return {
        "strength": section("Сильная сторона"),
        "advice": items("Рекомендации по методике"),
        "questions": [x for x in items("Вопросы автору") if "Вопросов нет" not in x],
    }


def cmd_list():
    if not SUBS.exists():
        print("заявок нет")
        return 0
    for p in sorted(SUBS.glob("b42p-*")):
        m = json.loads((p / "meta.json").read_text(encoding="utf-8"))
        print(f"  {m['code']} · {m['status']} · {m.get('email', '')} · {m.get('subject', '')[:50]}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch", "analyze", "publish", "list"])
    ap.add_argument("code", nargs="?")
    a = ap.parse_args()
    if a.cmd == "fetch":
        return cmd_fetch()
    if a.cmd == "list":
        return cmd_list()
    if not a.code:
        print("нужен код заявки"); return 1
    return cmd_analyze(a.code) if a.cmd == "analyze" else cmd_publish(a.code)


if __name__ == "__main__":
    sys.exit(main())
