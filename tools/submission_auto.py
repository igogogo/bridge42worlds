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
            "revise": "submission-reply-revise"}[kind]
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
                 ("{prompt_url}", f"{SITE}/lang/ru/community/"),
                 ("{token_url}", f"{SITE}/lang/ru/community/")):
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

    # ── куда автомат не идёт ──
    if verdict == "decline" or not meta.get("prepared", True):
        why = ("вердикт decline — отказ пишем руками"
               if verdict == "decline" else "нет следов промпта подготовки")
        meta["status"] = "held"
        meta["hold_reason"] = why
        if not dry:
            (box / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                           encoding="utf-8")
            tg(f"✋ <b>{code}</b> ждёт человека: {why}.\nРазбор готов, письмо не отправлено.")
        print(f"  ✋ {code}: {why}")
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
