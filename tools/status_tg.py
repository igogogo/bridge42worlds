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


def why(log):
    """Из лога упавшего прогона — одна человеческая фраза, ПОЧЕМУ он упал.

    Владелец 13 августа: «пишет stats refresh fails — может, в канал надо, что за ошибка,
    иначе непонятно». Он прав: сообщение «код 1, лог в logs/…» полезно ровно одному
    человеку — тому, кто сидит за этой машиной. Все остальные (и владелец с телефона в
    первую очередь) видят только то, что что-то сломалось, и не могут решить, надо ли
    вмешиваться сейчас или это само пройдёт к следующему прогону.

    Разбор простой и намеренно тупой: последняя строка последнего Traceback — это и есть
    причина, питон кладёт её туда сам. Если трейсбека нет, берём последнюю строку с
    предупреждением. Частые случаи переводим на русский: «TimeoutExpired» ничего не
    объясняет тому, кто не писал этот код.
    """
    p = Path(log)
    if not log or not p.exists():
        return ""
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    lines = [l.rstrip() for l in text.splitlines() if l.strip()]

    raw = ""
    for i in range(len(lines) - 1, -1, -1):
        s = lines[i].strip()
        # Последняя строка трейсбека: «ИмяОшибки: подробности». Не путаем с телом
        # трейсбека — те строки начинаются с File/^^^ и с отступа.
        if s and not s.startswith(("File ", "Traceback", "~", "^")) and ":" in s[:60]:
            head = s.split(":", 1)[0]
            # Имя может быть с модулем — «subprocess.TimeoutExpired». Смотрим на последний
            # сегмент, иначе проверка на заглавную букву не срабатывает и причина теряется.
            tail_name = head.rsplit(".", 1)[-1]
            if tail_name and tail_name[:1].isupper() and " " not in head and tail_name.endswith(
                    ("Error", "Exception", "Expired", "Interrupt", "Exit")):
                raw = s
                break
    if not raw:
        # Трейсбека нет — значит скрипт сам решил, что дело плохо, и написал об этом.
        # Берём только строки-жалобы: последняя строка лога вполне может оказаться
        # бодрым «✅ статус отправлен», и выдавать её за причину сбоя — хуже, чем молчать.
        for s in reversed(lines):
            if s.strip().startswith(("⚠", "⛔", "❌", "СТОП", "Ошибка", "ошибка")):
                raw = s.strip().lstrip("⚠️⛔❌ ").strip()
                break

    human = {
        "TimeoutExpired": "шаг не уложился в отведённое время (обычно большая дельта выкладки)",
        "ConnectionError": "не достучались до сети",
        "ConnectTimeout": "сеть не ответила вовремя",
        "ReadTimeout": "сервис отвечал слишком долго",
        "MemoryError": "не хватило памяти",
        "PermissionError": "файл занят другой программой",
        "FileNotFoundError": "не нашёлся нужный файл",
        "JSONDecodeError": "испорченный json на входе",
        "KeyboardInterrupt": "прогон прервали вручную",
    }
    for k, v in human.items():
        if k in raw:
            return v
    return raw[:180]


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
        text = (f"⛔ <b>Ежедневный прогон не пополнил ленту</b> (код {rc})."
                + (f"\nПричина: {why(log)}" if why(log) else "")
                + f"\nЛог: <code>{log}</code>")
    elif len(sys.argv) >= 2 and sys.argv[1] == "--dump-failed":
        rc = sys.argv[2] if len(sys.argv) > 2 else "?"
        log = sys.argv[3] if len(sys.argv) > 3 else ""
        text = (f"⚠️ <b>Дамп arXiv не обновился</b> (код {rc})."
                + (f"\nПричина: {why(log)}" if why(log) else "")
                + "\nРетроспектива и поиск дыр будут работать по старым данным."
                + f"\nЛог: <code>{log}</code>")
    elif len(sys.argv) >= 2 and sys.argv[1] == "--run-failed":
        # Общий случай для задач планировщика, у которых нет своего текста. Имя задачи
        # приходит ЛАТИНИЦЕЙ (см. объяснение про кодировку выше), человеческие слова
        # добавляем здесь.
        name = sys.argv[2] if len(sys.argv) > 2 else "?"
        rc = sys.argv[3] if len(sys.argv) > 3 else "?"
        log = sys.argv[4] if len(sys.argv) > 4 else ""
        titles = {"overnight": "Ночная накачка архива",
                  "upkeep": "Разметка вектором и починка графа",
                  "factory": "Фабрика (плановая работа по бюджету)",
                  "stats": "Пересчёт витрины и отчёт по читателям"}
        # «Сбой: <что>», а не «<что> не отработала»: названия задач разного рода
        # («пересчёт» и «накачка»), и одна общая формулировка иначе выходит безграмотной.
        text = (f"⚠️ <b>Сбой: {titles.get(name, name)}</b> (код {rc})."
                + (f"\nПричина: {why(log)}" if why(log) else "")
                + f"\nЛог: <code>{log}</code>")
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
