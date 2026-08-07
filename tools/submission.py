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


def safe_extract(zpath, dest):
    """Распаковка с защитой от zip-slip: имя с ../ выводит запись из папки — отклоняем."""
    with zipfile.ZipFile(zpath) as z:
        for m in z.infolist():
            target = (dest / m.filename).resolve()
            if not str(target).startswith(str(dest.resolve())):
                raise ValueError(f"подозрительный путь в архиве: {m.filename}")
        z.extractall(dest)


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
        (box / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
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
        for m2 in list(re.finditer(r"https?://[^\s<>\"']+", body))[:5]:
            url = m2.group(0).rstrip('.,)')
            if any(h in url for h in ("bridge42worlds", "mailto:")):
                continue
            try:
                with _rq.get(url, stream=True, timeout=120,
                             headers={"User-Agent": "bridge42worlds-intake"}) as resp:
                    if resp.status_code != 200:
                        continue
                    name = Path(url.split("?")[0]).name or "data.bin"
                    dest = box / "incoming" / ("link_" + name)
                    size = 0
                    with dest.open("wb") as f:
                        for chunk in resp.iter_content(1 << 20):
                            size += len(chunk)
                            if size > MAX_LINK_MB * 1024 * 1024:
                                raise ValueError("больше предела")
                            f.write(chunk)
                    files.append(dest.name)
                    print(f"  🔗 скачано по ссылке: {name} · {size // 1024 // 1024} МБ")
                    scan_one(dest.name)      # ровно та же проверка, что у вложений
            except Exception as ex:
                print(f"  ⚠️ ссылка {url[:50]}: {ex}")

        # Сводка проверки пишется ПОСЛЕ ссылок — иначе в неё не попадало скачанное.
        (box / "scan.json").write_text(json.dumps(verdicts, ensure_ascii=False, indent=1),
                                       encoding="utf-8")

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
            if p.suffix.lower() == ".zip" and p.exists() and verdicts.get(fn) == "чисто":
                try:
                    safe_extract(p, box / "unpacked")
                    print(f"  📦 {fn} распакован")
                except Exception as ex:
                    print(f"  ⚠️ {fn}: {ex}")

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
    prompt = load_prompt("submission-analyze").replace("{work}", text[:120000])
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

    # ПРИВАТНОЕ СЮДА НЕ ПОПАДАЕТ. publish.json уезжает на сайт, meta.json — нет.
    # Почта автора и токен остаются в meta.json; здесь только то, что можно показывать.
    pub = {
        "code": code,
        "received": meta.get("received", ""),
        "title": title,
        "kind": meta.get("kind", ""),
        "author_display": meta.get("author_name") or "",
        "ours": ours,
        "review": review_all,
        "similar": similar[:5],
        "source_url": f"/lang/ru/community/{code}/source.zip",
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
