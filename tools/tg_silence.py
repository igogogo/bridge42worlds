# -*- coding: utf-8 -*-
"""Общий выключатель отправки в канал.

ЗАЧЕМ. Владелец 25 августа: «выруби все сообщения в ленту — там сторож почты и так
далее, пока ждём ML». Отправок в канал шесть штук, и все написаны по отдельности:

    tools/mail_watch.py        сторож почты
    tools/tg_digest.py         дайджест статей
    tools/status_tg.py         отчёт о состоянии
    tools/submission_auto.py   приём авторских работ
    cloudflare/queue_worker.py исполнитель очереди заказов
    cloudflare/deploy_r2.py    выкладка на прод

Шесть копий одного кода — это шесть мест, где выключатель придётся не забыть. Поэтому
он один и лежит здесь; каждая отправка спрашивает разрешения перед тем, как писать.

ПОЧЕМУ НЕ УБРАТЬ ПРОСТО ТОКЕН ИЗ .env. Он же нужен для входящих: бот читает команды и
почту, и без токена сторож перестанет РАБОТАТЬ, а не только молчать. Нам нужна тишина
в канале, а не остановка дела: письма собираются, заказы исполняются, совет считает
голоса — просто никто об этом не рапортует.

КАК ВКЛЮЧИТЬ ТИШИНУ
    python tools/tg_silence.py on          молчим
    python tools/tg_silence.py off         говорим снова
    python tools/tg_silence.py             показать состояние

Признак — файл data/tg-silence, а не переменная окружения: задачи планировщика
запускаются в своих окружениях, и переменная до них не дошла бы. Файл видят все.
Внутри — дата и причина, чтобы через неделю не гадать, почему в канале тихо.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FLAG = ROOT / "data" / "tg-silence"


def muted():
    """Молчим ли сейчас. Вызывается перед каждой отправкой."""
    return FLAG.exists()


def note():
    """Что записано в признаке — дата и причина."""
    try:
        return json.loads(FLAG.read_text(encoding="utf-8"))
    except Exception:
        return {}


def guard(text=""):
    """Единая проверка для всех отправок.

    Возвращает True, если писать НЕЛЬЗЯ. Сообщение печатается в консоль: тишина в
    канале не должна означать потерю сведений — прогон в планировщике пишет лог,
    и там всё видно.
    """
    if not muted():
        return False
    if text:
        print("🔇 канал заглушен (data/tg-silence) — сообщение только в лог:")
        print(text[:1200])
    return True


def main():
    arg = (sys.argv[1] if len(sys.argv) > 1 else "").lower()
    if arg in ("on", "мол", "silence"):
        FLAG.parent.mkdir(exist_ok=True)
        why = " ".join(sys.argv[2:]) or "по просьбе владельца"
        FLAG.write_text(json.dumps(
            {"since": datetime.now().isoformat(timespec="seconds"), "why": why},
            ensure_ascii=False), encoding="utf-8")
        print(f"🔇 канал заглушен: {why}")
    elif arg in ("off", "on-air", "speak"):
        if FLAG.exists():
            FLAG.unlink()
            print("🔊 канал снова говорит")
        else:
            print("канал и так не был заглушен")
    else:
        if muted():
            n = note()
            print(f"🔇 заглушен с {n.get('since', '?')} — {n.get('why', '')}")
        else:
            print("🔊 говорит")
    return 0


if __name__ == "__main__":
    sys.exit(main())
