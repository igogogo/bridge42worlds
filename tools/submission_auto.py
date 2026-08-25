#!/usr/bin/env python3
"""Полный автомат приёма авторских работ: письмо → разбор → публикация → ответ автору.

Владелец 2026-08-06: «проверяем полный автомат, конечно ничего руками, по результатам
скажешь». До этого режим был полуручным по его же решению от 4 августа — между стадиями
смотрел человек. Пробуем без человека и смотрим, что выйдет.

Что делает один прогон:
    1. забирает новые письма с article@ (проверка на вирусы внутри)
    2. разбирает каждую работу моделью
    3. по вердикту разбора: публикует ЛИБО пишет автору просьбу доработать
    4. отправляет автору письмо и возвращает токен управления публикацией
    5. докладывает в Telegram

ГДЕ АВТОМАТ ОСТАНАВЛИВАЕТСЯ САМ (и это не осторожность, а отказ делать плохо):
  · вердикт decline — письмо НЕ уходит само. Отказ живому человеку пишется руками;
    автомат только готовит черновик и зовёт человека.
  · работа без следов промпта подготовки — тоже к человеку: возможно, автор просто
    не нашёл инструкцию, и шаблонный отлуп будет несправедлив.
  · разбор не сошёлся технически (модель не ответила) — молчим и зовём, а не шлём пустое.

    python tools/submission_auto.py            один проход
    python tools/submission_auto.py --dry      показать, что сделал бы, ничего не меняя
"""
import argparse
import json
import ssl
import smtplib
import subprocess
import sys
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

SUBS = ROOT / "data" / "submissions"
SITE = "https://bridge42worlds.academy"


def env():
    out = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def tg(text):
    # Общий выключатель канала (tools/tg_silence.py). Владелец 25 августа: «выруби
    # все сообщения в ленту, пока ждём ML». Дело при этом продолжается — молчит
    # только рапорт.
    try:
        import sys as _s
        from pathlib import Path as _P
        _r = str(_P(__file__).resolve().parent.parent)
        if _r not in _s.path:
            _s.path.insert(0, _r)
        from tools.tg_silence import guard as _guard
        if _guard(text):
            return False
    except ImportError:
        pass
    e = env()
    token, chat = e.get("TG_BOT_TOKEN"), e.get("TG_CHAT_ID")
    if not (token and chat):
        return False
    try:
        import requests
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", timeout=20,
                      json={"chat_id": chat, "text": text, "parse_mode": "HTML",
                            "disable_web_page_preview": True})
        return True
    except Exception:
        return False


def send_mail(to, subject, body):
    """Письмо автору с адреса article@ — с него он писал, туда и ответит."""
    e = env()
    host, pw = e.get("MAIL_HOST"), e.get("MAIL_PASS")
    user = "article@bridge42worlds.academy"
    if not (host and pw and to):
        print("  ⚠️ письмо не отправлено: нет доступов или адреса")
        return False
    msg = EmailMessage()
    msg["From"] = f"bridge42worlds <{user}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(host, int(e.get("MAIL_SMTP_PORT", 587)), timeout=30) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(user, pw)
            s.send_message(msg)
        return True
    except Exception as ex:
        print(f"  ❌ письмо {to}: {type(ex).__name__} {ex}")
        return False


def compose(kind, meta, review_text, url=""):
    """Текст письма автору: пишет модель по нашему промпту, а не шаблон с подстановками.

    Шаблон с дырками выдал бы одинаковое письмо всем, а работы разные: одному нужно
    объяснить, чего не хватает в методике, другому — просто сказать, что вышло хорошо.
    Промпт держит тон («помогаем, а не лечим») и правило про язык работы."""
    from common import chat, load_prompt
    name = {"publish": "submission-reply-publish",
            "revise": "submission-reply-revise",
            "needs-prompt": "submission-reply-needs-prompt"}[kind]
    p = load_prompt(name)
    for k, v in (("{code}", meta.get("code", "")),
                 ("{title}", meta.get("subject", "")),
                 ("{kind}", meta.get("kind", "")),
                 ("{author_name}", meta.get("author_name", "")),
                 ("{public_id}", meta.get("code", "")),
                 ("{work_language}", ""),
                 ("{review}", review_text),
                 ("{url}", url),
                 ("{token}", meta.get("author_token", "")),
                 # Этих трёх не передавали — и автор получал бы фигурные скобки в тексте.
                 ("{reply_to}", "article@bridge42worlds.academy"),
                 ("{prompt_url}", f"{SITE}/lang/ru/community/prepare/"),
                 ("{prepare_url}", f"{SITE}/lang/ru/community/prepare/"),
                 ("{token_url}", f"{SITE}/lang/ru/community/"),
                 ("{found}", meta.get("found", "")),
                 ("{problems}", meta.get("problems_text", "")),
                 ("{attempt_note}", meta.get("attempt_note", "")),
                 # Промпт вставляем в письмо ЦЕЛИКОМ (владелец 2026-08-07: «промт в письмо
                 # прямо вставить, чтобы продублировать»). Автору не придётся никуда идти:
                 # ссылка на страницу тоже есть, но письмо самодостаточно.
                 ("{prompt}", (ROOT / "data" / "prompts" / "author-self-check.txt")
                  .read_text(encoding="utf-8"))):
        p = p.replace(k, str(v))
    r = chat("article_popular", p, system="Ты пишешь письмо автору от лица bridge42worlds.")
    raw = (r.choices[0].message.content or "").strip()
    # Промпт просит JSON с темой и телом — тема должна зависеть от содержания письма,
    # а не быть одинаковой у всех. Разбираем; если модель ответила обычным текстом,
    # берём его как есть и ставим тему по умолчанию: письмо важнее формата ответа.
    try:
        from common import clean_json
        d = json.loads(clean_json(raw))
        subject = (d.get("тема") or d.get("subject") or "").strip()
        body = (d.get("письмо") or d.get("body") or "").strip()
        if body:
            return subject, body
    except Exception:
        pass
    return "", raw


def process(code, dry=False):
    box = SUBS / code
    meta = json.loads((box / "meta.json").read_text(encoding="utf-8"))
    if meta.get("status") in ("published", "revise-sent", "held"):
        return None

    # ── разбор ──
    if not (box / "review.md").exists():
        if dry:
            print(f"  [сухой] {code}: запустил бы разбор")
            return None
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "submission.py"),
                            "analyze", code], cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=1800)
        if r.returncode != 0 or not (box / "review.md").exists():
            meta["status"] = "held"
            meta["hold_reason"] = "разбор не сошёлся технически"
            (box / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                           encoding="utf-8")
            tg(f"⚠️ <b>{code}</b>: разбор не сошёлся, работа ждёт человека.")
            return "held"

    review = (box / "review.md").read_text(encoding="utf-8")
    verdict = ""
    for line in review.splitlines():
        if "**" in line and any(v in line for v in ("publish", "revise", "decline")):
            for v in ("publish", "revise", "decline"):
                if v in line:
                    verdict = v
                    break
            break

    # ── работа без подготовки: отвечаем сами, это не отказ ──
    # Раньше такие работы ждали человека. Владелец 2026-08-07: «мою работу отклони, скажи
    # нужен промпт, и в письме укажи порядок проверки». Письмо не шаблонное: его пишет
    # модель, перечисляя то, что реально лежит в пакете, и вкладывая промпт целиком —
    # автору не нужно никуда идти.
    # Проверяем СООТВЕТСТВИЕ требованиям, а не наличие файла (владелец 2026-08-07):
    # пакет может содержать SELF-REVIEW.md и всё равно не годиться — если в нём стоит
    # «почти готово» или структура разошлась с нашей.
    import submission as _sub
    ok_pkg, problems, author_verdict = _sub.check_package(box)
    if not ok_pkg:
        if dry:
            print(f"  [сухой] {code}: вернул бы на подготовку ({len(problems)} замечаний)")
            return "needs-prompt"

        # Счёт попыток по отпечатку пакета: та же работа второй раз — та же попытка,
        # переделанная — новая. Три круга, дальше пауза: если пакет не собирается
        # с третьего раза, переписка по кругу не поможет ни нам, ни автору.
        digest = _sub.package_digest(box)
        n, hist, data = _sub.tries_count(box, digest)
        attempt = _sub.bump_try(hist, data, digest)
        meta["attempt"] = attempt
        meta["package_digest"] = digest
        meta["problems"] = problems

        if attempt > _sub.MAX_TRIES:
            # Три круга — и пауза на неделю (владелец 2026-08-08: «не больше трёх итераций,
            # потом скажи надо дорабатывать глубже, пока не готовы, можете попробовать
            # через неделю»). Молча ставить на паузу нельзя: автор ждёт ответа и вправе
            # знать, что дело не в очереди, а в работе, и когда можно вернуться.
            from datetime import date, timedelta
            until = (date.today() + timedelta(days=7)).isoformat()
            meta["status"] = "paused"
            meta["paused_until"] = until
            meta["attempt_note"] = (
                f"Это третий заход, и пакет всё ещё не собирается. Дело не в мелочах "
                f"оформления — работе нужна более глубокая доработка. Возвращайтесь к нам "
                f"после {until}, мы посмотрим её заново и с чистого листа."
            )
            subject, letter = compose("needs-prompt", meta, "")
            (box / "reply-paused.txt").write_text(letter, encoding="utf-8")
            ok = send_mail(meta.get("email", ""),
                           subject or f"{code}: нужна более глубокая доработка", letter)
            meta["reply_sent"] = bool(ok)
            (box / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                           encoding="utf-8")
            tg(f"⏸️ <b>{code}</b>: три попытки исчерпаны, пауза до {until}. "
               f"Письмо: {'ушло' if ok else 'НЕ УШЛО'}")
            print(f"  ⏸️ {code}: три попытки исчерпаны — пауза до {until}")
            return "paused"

        un = box / "unpacked"
        found = []
        if un.exists():
            root = next((d for d in un.iterdir() if d.is_dir()), un)
            for item in sorted(root.iterdir()):
                n2 = sum(1 for _ in item.rglob("*")) if item.is_dir() else 0
                found.append(f"{item.name}{' (' + str(n2) + ' файлов)' if n2 else ''}")
        meta["found"] = ", ".join(found) if found else "архив не распаковался"
        meta["problems_text"] = "\n".join(f"· {x}" for x in problems)
        meta["attempt_note"] = (f"Попытка {attempt} из {_sub.MAX_TRIES}." if attempt > 1 else "")
        subject, letter = compose("needs-prompt", meta, "")
        (box / "reply-sent.txt").write_text(letter, encoding="utf-8")
        ok = send_mail(meta.get("email", ""),
                       subject or f"{code}: нужна подготовка работы", letter)
        meta["status"] = "needs-prompt-sent" if ok else "received"
        meta["reply_sent"] = bool(ok)
        (box / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
        tg(f"📨 <b>{code}</b>: работа без подготовки, автору отправлен промпт и порядок. "
           f"Письмо: {'ушло' if ok else 'НЕ УШЛО'}")
        print(f"  📨 {code}: письмо о подготовке {'ушло' if ok else 'НЕ УШЛО'}")
        return "needs-prompt"

    # ── отказ по существу пишет человек ──
    if verdict == "decline":
        meta["status"] = "held"
        meta["hold_reason"] = "вердикт decline — отказ пишем руками"
        if not dry:
            (box / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                           encoding="utf-8")
            tg(f"✋ <b>{code}</b> ждёт человека: вердикт decline.\n"
               f"Разбор готов, письмо не отправлено.")
        print(f"  ✋ {code}: вердикт decline — письмо пишет человек")
        return "held"

    # ── публикация или просьба доработать ──
    if dry:
        print(f"  [сухой] {code}: вердикт {verdict or '?'} → "
              f"{'публикация и письмо' if verdict == 'publish' else 'письмо с просьбой доработать'}")
        return verdict

    url = ""
    if verdict == "publish":
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "submission.py"),
                            "publish", code], cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=3600)
        if r.returncode != 0:
            meta["status"] = "held"
            meta["hold_reason"] = "публикация не удалась"
            (box / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                           encoding="utf-8")
            tg(f"⚠️ <b>{code}</b>: публикация не удалась, работа ждёт человека.")
            return "held"
        meta = json.loads((box / "meta.json").read_text(encoding="utf-8"))
        url = meta.get("url", "")

    subject, letter = compose("publish" if verdict == "publish" else "revise",
                              meta, review, url)
    (box / "reply-sent.txt").write_text(letter, encoding="utf-8")
    ok = send_mail(meta.get("email", ""),
                   subject or f"Ваша работа {code} — разбор bridge42worlds", letter)
    # Письмо не ушло — работу НЕ закрываем. Иначе при лежащей почте (а такое уже было:
    # 6 августа кончилась подписка на хостинг и отвалились все ящики разом) автор просто
    # никогда не получит ответа, а у нас будет стоять «отправлено».
    if ok:
        meta["status"] = "published" if verdict == "publish" else "revise-sent"
    else:
        meta["status"] = "received"          # вернёмся к ней следующим прогоном
        meta["reply_pending"] = True
        tg(f"✉️ <b>{code}</b>: письмо автору НЕ ушло, работа осталась в очереди. "
           f"Проверьте почту — текст письма готов и лежит в reply-sent.txt.")
    meta["reply_sent"] = bool(ok)
    (box / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                   encoding="utf-8")

    tg(f"{'📗' if verdict == 'publish' else '📙'} <b>{code}</b> — "
       f"{'опубликована' if verdict == 'publish' else 'отправлена просьба доработать'}\n"
       f"{('Страница: ' + url) if url else ''}\n"
       f"Письмо автору: {'ушло' if ok else 'НЕ УШЛО, смотреть руками'}")
    print(f"  ✅ {code}: {verdict}, письмо {'ушло' if ok else 'не ушло'}")
    return verdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    before = {p.name for p in SUBS.iterdir()} if SUBS.exists() else set()
    if not args.dry:
        subprocess.run([sys.executable, str(ROOT / "tools" / "submission.py"), "fetch"],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800)
    after = {p.name for p in SUBS.iterdir()} if SUBS.exists() else set()
    new = sorted(after - before)
    if new:
        tg(f"📥 <b>Новых работ: {len(new)}</b>\n" + "\n".join(new))
        print(f"новых работ: {len(new)} — {', '.join(new)}")

    # Обрабатываем и новые, и всё, что осталось незакрытым с прошлых прогонов
    todo = []
    for d in sorted(SUBS.iterdir()) if SUBS.exists() else []:
        m = d / "meta.json"
        if not m.exists():
            continue
        try:
            st = json.loads(m.read_text(encoding="utf-8")).get("status", "")
        except Exception:
            continue
        if st in ("received", ""):
            todo.append(d.name)
    if not todo:
        print("нечего обрабатывать")
        return 0
    print(f"в работе: {len(todo)}")
    for code in todo:
        process(code, dry=args.dry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
