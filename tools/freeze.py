# -*- coding: utf-8 -*-
"""Общий замок: пока он стоит, никакие прогоны не начинаются.

ЗАЧЕМ. Владелец 25 августа: «пока не закончил — отмени все прогоны, замок на все».
ML перестраивает слой понятий и вектор; всё, что сейчас сгенерируется, разметится или
зальётся, придётся делать заново после его правки. Дешевле не делать.

ПОЧЕМУ НЕ ХВАТИЛО ПЛАНИРОВЩИКА. Задачи выключены — кроме двух: b42_mail_temp и
b42_queue заведены из-под повышенного процесса, и наша учётная запись их выключить не
может («Access is denied»). Значит расписание вообще ненадёжное место для запрета:
оно не покрывает ни эти две задачи, ни запуск руками, ни чужую сессию на том же дереве.
Замок в коде покрывает всё сразу.

ЧТО ОСТАНАВЛИВАЕТСЯ
    run.py            все команды — генерация, пересборка, индексы, графы, публикация
    сторож почты      письма не читаются
    очередь заказов   заказы не исполняются
    заливка в облако   cards_sync, frame_sync, deploy_r2

ЧТО ПРОДОЛЖАЕТ РАБОТАТЬ
    сайт на проде     он статический, его никто не трогает
    воркер            отвечает на запросы читателей
    локальная разработка — правки css/js/шаблонов и tools/dev_server.py

ЗАМОК И ТИШИНА — РАЗНЫЕ ВЕЩИ. tg_silence затыкает рапорт, дело при этом идёт.
freeze останавливает само дело. Стоять они могут по отдельности.

    python tools/freeze.py on "причина"    замок
    python tools/freeze.py off             снять
    python tools/freeze.py                 состояние
"""
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FLAG = ROOT / "data" / "freeze"


def frozen():
    return FLAG.exists()


def note():
    try:
        return json.loads(FLAG.read_text(encoding="utf-8"))
    except Exception:
        return {}


def guard(what="прогон", exit_code=0):
    """Остановиться, если стоит замок.

    Выходим с НУЛЁМ, а не с ошибкой: планировщик считает ненулевой код сбоем и начинает
    писать о нём в отчёт, а здесь ничего не сломалось — мы просто сознательно не работаем.
    Отличать «замок» от «упало» важно, иначе замок сам станет источником тревог.
    """
    if not frozen():
        return False
    n = note()
    print(f"🔒 ЗАМОК: {what} не запускается.")
    print(f"   поставлен {n.get('since', '?')} — {n.get('why', '')}")
    print("   снять: python tools/freeze.py off")
    if exit_code is not None:
        sys.exit(exit_code)
    return True


def main():
    arg = (sys.argv[1] if len(sys.argv) > 1 else "").lower()
    if arg in ("on", "lock", "замок"):
        FLAG.parent.mkdir(exist_ok=True)
        why = " ".join(sys.argv[2:]) or "по просьбе владельца"
        FLAG.write_text(json.dumps(
            {"since": datetime.now().isoformat(timespec="seconds"), "why": why},
            ensure_ascii=False), encoding="utf-8")
        print(f"🔒 замок поставлен: {why}")
    elif arg in ("off", "unlock", "снять"):
        if FLAG.exists():
            FLAG.unlink()
            print("🔓 замок снят — прогоны разрешены")
        else:
            print("замка и не было")
    else:
        if frozen():
            n = note()
            print(f"🔒 замок с {n.get('since', '?')} — {n.get('why', '')}")
        else:
            print("🔓 открыто")
    return 0


if __name__ == "__main__":
    sys.exit(main())
