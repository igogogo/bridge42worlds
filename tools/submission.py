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

        # Антивирус до всякой распаковки
        verdicts = {}
        for fn in files:
            v = defender_scan(box / "incoming" / fn)
            verdicts[fn] = {"clean": "чисто", "infected": "УГРОЗА — в карантине",
                            "error": "проверка не удалась — смотреть руками"}[v]
            if v == "infected":
                src = box / "incoming" / fn
                src.rename(src.with_suffix(src.suffix + ".quarantine"))
        (box / "scan.json").write_text(json.dumps(verdicts, ensure_ascii=False, indent=1),
                                       encoding="utf-8")

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
            except Exception as ex:
                print(f"  ⚠️ ссылка {url[:50]}: {ex}")

        # zip распаковываем только чистые
        for fn in list(files):
            p = box / "incoming" / fn
            if p.suffix.lower() == ".zip" and p.exists() and verdicts.get(fn) != "УГРОЗА — в карантине":
                try:
                    safe_extract(p, box / "unpacked")
                    print(f"  📦 {fn} распакован")
                except Exception as ex:
                    print(f"  ⚠️ {fn}: {ex}")

        print(f"  ✅ {code} · от {meta['email'] or 'без адреса'} · файлов {len(files)}")
    m.logout()
    return 0


ANALYZE_PROMPT = """Ты — научный рецензент открытой площадки для работ от неаккредитованных
авторов. Твоя задача ПОМОЧЬ автору, а не отсеять его: разбор строгий, тон уважительный.

Разбери присланную работу по пунктам, каждый — коротко и по делу:

1. СУТЬ (2-3 предложения своими словами: что автор утверждает и на чём основывает).
2. ВМЕНЯЕМОСТЬ: есть ли внутренние противоречия, нарушения известной физики без оговорок.
3. ЛОГИЧНОСТЬ: следует ли вывод из данных; где логический разрыв, если есть.
4. ЗАВЕРШЁННОСТЬ: чего не хватает (контроль, статистика, описание методики, данные).
5. КОРРЕКТНОСТЬ И СИЛА: самое сильное место работы и самое слабое. Что нужно, чтобы
   слабое стало сильным.
6. ЧТО ПОПРАВИТЬ: нумерованный список конкретных правок — «сделать то-то».
7. ВОПРОСЫ АВТОРУ: нумерованные, на которые нужен ответ до публикации.
8. ВЕРДИКТ: publish / revise / decline — одним словом, затем одно предложение почему.

Пиши по-русски. Не выдумывай похвал и не смягчай проблем: автору полезна правда.

РАБОТА:
"""


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
    r = chat("article_advanced", ANALYZE_PROMPT + text[:120000] + ask_json,
             system="Ты научный рецензент открытой площадки. Пиши по-русски, конкретно.")
    import json as _j
    from common import clean_json
    d = _j.loads(clean_json(r.choices[0].message.content))
    parts = []
    NL = "\n"
    for k in ("суть", "вменяемость", "логичность", "завершённость", "корректность_и_сила"):
        if d.get(k):
            parts.append("## " + k.replace("_", " ").capitalize() + NL + NL + str(d[k]))
    if d.get("что_поправить"):
        parts.append("## Что поправить" + NL + NL +
                     NL.join(f"{i+1}. {x}" for i, x in enumerate(d["что_поправить"])))
    if d.get("вопросы_автору"):
        parts.append("## Вопросы автору" + NL + NL +
                     NL.join(f"{i+1}. {x}" for i, x in enumerate(d["вопросы_автору"])))
    parts.append("## Вердикт" + NL + NL +
                 f"**{d.get('вердикт', '?')}** — {d.get('почему', '')}")
    review = (NL + NL).join(parts)
    (box / "review.md").write_text(review, encoding="utf-8")

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


def cmd_publish(code):
    """Закрытая страница: неугадываемый адрес, noindex, вне карт сайта и индексов.
    Это «не на виду», а не «под замком» — для черновиков достаточно; постоянный раздел
    получит проверку ключом совета."""
    box = SUBS / code
    meta = json.loads((box / "meta.json").read_text(encoding="utf-8"))
    review = (box / "review.md").read_text(encoding="utf-8") if (box / "review.md").exists() else ""
    similar = json.loads((box / "similar.json").read_text(encoding="utf-8")) if (box / "similar.json").exists() else []
    letter = (box / "letter.txt").read_text(encoding="utf-8")

    slug = code + "-" + secrets.token_urlsafe(8)
    out_dir = ROOT / "lang" / "ru" / "community" / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    import html as H
    sim_html = "".join(
        f'<li><a href="/lang/ru/archive/">{H.escape(s["title"])}</a> <small>{s["score"]}</small></li>'
        for s in similar)
    rev_html = "".join(f"<p>{H.escape(x)}</p>" for x in review.split("\n\n") if x.strip())
    let_html = "".join(f"<p>{H.escape(x)}</p>" for x in letter.split("\n\n") if x.strip())
    page = f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<meta name="robots" content="noindex, nofollow">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{code} · закрытый просмотр — bridge42worlds</title>
<link rel="stylesheet" href="/css/style.css"></head>
<body style="max-width:680px;margin:0 auto;padding:20px">
<p style="font-family:monospace;font-size:12px;color:#888">{code} · народная наука ·
закрытый просмотр — не для распространения</p>
<h1>{H.escape(meta.get("subject") or code)}</h1>
<p><small>получено {meta["received"]} · автор: {"аноним" if not meta.get("author_name") else H.escape(meta["author_name"])}</small></p>
<h2>Текст</h2>{let_html}
<h2>Разбор (наш анализатор)</h2>{rev_html}
<h2>Похожие работы у нас</h2><ul>{sim_html or "<li>—</li>"}</ul>
</body></html>"""
    (out_dir / "index.html").write_text(page, encoding="utf-8")

    meta["status"] = "published-private"
    meta["url"] = f"{SITE}/lang/ru/community/{slug}/"
    (box / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ закрытая страница: {meta['url']}")
    print(f"   токен автора: {meta['author_token']} — вернуть в ответном письме")
    print("   на прод уедет ближайшей выкаткой (страница вне индексов и карт сайта)")
    return 0


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
