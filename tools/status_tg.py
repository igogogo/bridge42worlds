"""Статус команды в общий Telegram-канал: что сделано, что в работе.

Просьба владельца 2026-07-31: писать статус при каждом пуше/выкатке. Канал тот же,
что у уведомления «сайт обновлён» (deploy_r2.notify_telegram) — креды из .env.

    python tools/status_tg.py "текст"        одна строка
    python tools/status_tg.py --file f.txt   длинный текст из файла (HTML-разметка Telegram)

Не роняет вызвавшего: любые ошибки — предупреждение и код 0 (статус не критичен),
кроме явного отсутствия текста.
"""
import os
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent


def _load_env():
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def main():
    # Готовые сообщения СОБИРАЮТСЯ ЗДЕСЬ, а не передаются строкой из .cmd-файла.
    #
    # Владелец 2026-08-04: «в канал телеграма лезет какая-то сбитая кодировка, что-то там
    # log». Причина: русский текст жил внутри tools/daily.cmd, а консоль Windows отдаёт
    # аргументы в кодировке OEM (cp866) — до Python доезжали кракозябры, и они же уходили
    # в канал. Лечится не «ещё одним перекодированием», а тем, что русские тексты живут
    # только в UTF-8 файлах Python; .cmd передаёт короткий ЛАТИНСКИЙ код и числа.
    if len(sys.argv) >= 2 and sys.argv[1] == "--daily-failed":
        rc = sys.argv[2] if len(sys.argv) > 2 else "?"
        log = sys.argv[3] if len(sys.argv) > 3 else ""
        text = (f"⛔ <b>Ежедневный прогон не пополнил ленту</b> (код {rc}).\n"
                f"Причина — в логе: <code>{log}</code>")
    elif len(sys.argv) >= 2 and sys.argv[1] == "--dump-failed":
        rc = sys.argv[2] if len(sys.argv) > 2 else "?"
        log = sys.argv[3] if len(sys.argv) > 3 else ""
        text = (f"⚠️ <b>Дамп arXiv не обновился</b> (код {rc}).\n"
                f"Ретроспектива и поиск дыр будут работать по старым данным.\n"
                f"Лог: <code>{log}</code>")
    elif len(sys.argv) >= 3 and sys.argv[1] == "--file":
        text = Path(sys.argv[2]).read_text(encoding="utf-8")
    elif len(sys.argv) >= 2:
        text = sys.argv[1]
    else:
        print("нужен текст: status_tg.py \"...\" или --file путь")
        return 1
    _load_env()
    token, chat = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")
    if not (token and chat):
        print("⚠️ TG_BOT_TOKEN/TG_CHAT_ID не настроены — статус не отправлен")
        return 0
    try:
        import requests
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", timeout=20,
                          json={"chat_id": chat, "parse_mode": "HTML", "text": text[:4000],
                                "disable_web_page_preview": True})
        if r.status_code == 200:
            print("✅ статус отправлен")
        else:
            print(f"⚠️ Telegram ответил {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"⚠️ статус не ушёл: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
