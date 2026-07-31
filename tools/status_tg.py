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
    if len(sys.argv) >= 3 and sys.argv[1] == "--file":
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
