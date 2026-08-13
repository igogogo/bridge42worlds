#!/usr/bin/env python3
"""Голоса ИИ-участников — в живую базу совета, до истечения срока.

Владелец 13 августа: «когда заседание прошло — наверное, чтобы ИИ-участники уже
проголосовали все и написали комментарии и предложения, потом, как только время истекло,
уже на почту: вот решения, вот план работ, вот вопросы к следующему голосованию».

Почему отдельный инструмент, а не council_vote.py. Тот писал голос модели в ФАЙЛ
заседания, а кабинет считает итоги по базе D1. Две правды об одном голосовании — верный
способ однажды разослать людям не тот итог. Здесь голос уходит той же ручкой /api/council/vote,
что и у человека: одна дверь, одни правила, один счётчик.

Два ограничения регламента соблюдаются буквально:
  • голос ИИ всегда с обоснованием — оно уходит в поле why и видно в итогах;
  • решающий голос ИИ вопрос не закрывает — это считает уже закрытие заседания.

    python tools/council_ai_vote.py                 проголосовать за всех ИИ-участников
    python tools/council_ai_vote.py --dry           показать, не записывая
    python tools/council_ai_vote.py --meeting 2026-08-16
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SITE = "https://bridge42worlds.academy"
API = f"{SITE}/api/council"

# Роль задаёт УГОЛ ЗРЕНИЯ, а не мнение. Два ИИ-участника с одинаковым промптом дали бы
# два одинаковых голоса — это не два участника, а один, посчитанный дважды.
ROLES = {
    "Архитектор": (
        "Ты архитектор проекта в наблюдательном совете. Смотришь на исполнимость: "
        "что мы реально сможем сделать и поддерживать, чего будет стоить обслуживание "
        "решения через полгода, какие решения загоняют нас в угол. Ты не оптимист и не "
        "пессимист — ты считаешь работу."
    ),
    "Стратег": (
        "Ты стратег и секретарь совета. Смотришь на смысл и последствия: кому решение "
        "помогает, кого отталкивает, как оно выглядит со стороны читателя и автора, "
        "что оно говорит о наших ценностях. Технику оставь архитектору."
    ),
}

SYSTEM = (
    "{role}\n\n"
    "Тебе дают вопросы повестки с вариантами. По каждому выбери РОВНО ОДИН вариант из "
    "предложенных (по его id) и объясни выбор в двух-трёх предложениях: не пересказывай "
    "вопрос, а скажи, почему именно этот вариант и чем плох ближайший конкурент.\n\n"
    "Правила, которые не обсуждаются:\n"
    "• Никогда не выдумывай вариант, которого нет в списке.\n"
    "• Если данных для выбора не хватает — это тоже позиция, выбирай вариант «отложить», "
    "если он есть, и объясни, чего именно не хватает.\n"
    "• Обоснование пишут для человека, который увидит его в кабинете совета. Без "
    "канцелярита, без «важно отметить», без перечисления очевидного.\n\n"
    "Ответ — только JSON: {{\"votes\": [{{\"id\": \"a1\", \"choice\": \"o2\", "
    "\"why\": \"…\"}}]}}"
)


def admin_head():
    """Наш собственный прогон представляется админ-секретом.

    Щит по адресу считает обращения с одного IP и рассчитан на человека, который жмёт
    кнопки. Плановый прогон шлёт шестнадцать голосов подряд с одной машины и упирается
    в дневной предел — не потому, что он бот, а потому, что он быстрый. Секрет отличает
    свою автоматику от чужой; правила голосования (членство, почта, заморозка) он не
    отменяет — они проверяются как для всех.
    """
    tok = os.environ.get("COUNCIL_ADMIN_TOKEN") or _from_env("COUNCIL_ADMIN_TOKEN")
    return {"x-b42-admin": tok or ""}


def members():
    import requests
    r = requests.get(f"{API}/members", headers=admin_head(), timeout=30)
    r.raise_for_status()
    return [m for m in r.json().get("members", []) if m.get("kind") == "ai"]


def _from_env(name):
    p = ROOT / ".env"
    if not p.exists():
        return None
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith(f"{name}="):
            return line.split("=", 1)[1].strip()
    return None


def agenda(meeting=None):
    import requests
    d = requests.get(f"{SITE}/data/council/upcoming.json", timeout=30).json()
    if meeting and str(d.get("date")) != meeting:
        d = requests.get(f"{SITE}/data/council/{meeting}.json", timeout=30).json()
    return d


def frozen(meeting):
    import requests
    try:
        return requests.get(f"{API}/frozen?meeting={meeting}", timeout=30).json().get("frozen", {})
    except Exception:
        return {}


def ask(role_name, items):
    """Один запрос на участника: вся повестка разом — так у модели есть контекст всего
    заседания, а не восьми отдельных вопросов без связи между собой."""
    from common import chat, clean_json
    payload = {"вопросы": [
        {"id": q["id"], "title": q.get("title"), "body": q.get("body"),
         "origin": q.get("origin"),
         "options": [{"id": o.get("id"), "label": o.get("label"), "note": o.get("note")}
                     for o in (q.get("options") or [])]}
        for q in items]}
    resp = chat("translate_flash", json.dumps(payload, ensure_ascii=False, indent=1),
                system=SYSTEM.format(role=ROLES.get(role_name, ROLES["Архитектор"])))
    text = (resp.choices[0].message.content or "").strip()
    return json.loads(clean_json(text)).get("votes") or []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meeting", help="дата заседания, по умолчанию ближайшее")
    ap.add_argument("--dry", action="store_true", help="показать голоса, не записывая")
    args = ap.parse_args()

    import requests
    d = agenda(args.meeting)
    meeting = str(d.get("date") or "")
    items = d.get("agenda") or []
    if not items:
        print("повестка пуста — голосовать не за что")
        return 1

    # Замороженные вопросы пропускаем: они сняты с голосования, и голос по ним сервер
    # всё равно не примет. Проверяем до обращения к модели — незачем платить за ответы,
    # которые будут выброшены.
    frz = frozen(meeting)
    live = [q for q in items if q.get("id") not in frz]
    if len(live) < len(items):
        print(f"заморожено и пропущено: {len(items) - len(live)} вопрос(ов) — {', '.join(frz)}")
    if not live:
        print("все вопросы заморожены — голосовать не за что")
        return 0

    ai = members()
    if not ai:
        print("ИИ-участников в совете нет")
        return 1

    total, bad = 0, 0
    for m in ai:
        name = m.get("name") or "участник"
        print(f"\n=== {name}")
        try:
            votes = ask(name, live)
        except Exception as e:
            print(f"  ❌ не проголосовал ({type(e).__name__}: {e})")
            bad += 1
            continue
        allowed = {q["id"]: {str(o.get("id")) for o in (q.get("options") or [])} for q in live}
        for v in votes:
            qid, choice, why = v.get("id"), str(v.get("choice", "")), (v.get("why") or "").strip()
            if qid not in allowed:
                print(f"  ⚠️ неизвестный вопрос {qid} — пропускаю")
                continue
            if choice not in allowed[qid]:
                # Выдуманный вариант — ошибка голосования, а не мелочь: подгонять нельзя.
                print(f"  ⚠️ {qid}: варианта «{choice}» нет в списке — голос не принят")
                bad += 1
                continue
            if not why:
                print(f"  ⚠️ {qid}: голос без обоснования — по регламенту не принимается")
                bad += 1
                continue
            title = next((q.get("title", "") for q in live if q["id"] == qid), qid)
            print(f"  · {title[:60]}\n    → {choice}: {why[:150]}")
            if args.dry:
                continue
            # Ручка голосования защищена от частых обращений — она рассчитана на человека,
            # который жмёт кнопки руками. ИИ-участник отправляет восемь голосов подряд и
            # упирается в этот же щит: первый прогон записал 10 из 16, остальные получили
            # «слишком часто». Щит правильный, поэтому меняем не его, а темп: пауза между
            # голосами и одна повторная попытка.
            ok = False
            for attempt in (0, 1):
                if attempt:
                    time.sleep(6)
                r = requests.post(f"{API}/vote", headers=admin_head(),
                                  json={"key": m["key"], "meeting": meeting,
                                        "question": qid, "vote": choice,
                                        "why": f"{name}: {why}"}, timeout=30)
                if r.ok and r.json().get("ok"):
                    ok = True
                    break
                if "too_fast" not in r.text:
                    break
            if ok:
                total += 1
            else:
                print(f"    ⚠️ не записан: {r.text[:100]}")
                bad += 1
            time.sleep(2)

    print(f"\nзаписано голосов: {total}" + (f", не принято: {bad}" if bad else ""))
    return 0 if total or args.dry else 1


if __name__ == "__main__":
    sys.exit(main())
