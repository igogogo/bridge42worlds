#!/usr/bin/env python3
"""Голос модели как члена совета.

Владелец 2026-07-31: «роль агента будет тоже голосовать, а не только давать предложения».
Значит у модели полноценное членство: свои предложения (council_collect.py) и свой голос.

ДВА ОГРАНИЧЕНИЯ, которые делают это безопасным. Оба не технические, а по существу.

1. Голос модели ВСЕГДА с обоснованием, и обоснование публикуется на странице заседания.
   Человек должен видеть, почему она так проголосовала, и иметь возможность возразить.
   Голос без объяснения от участника, который не устаёт и не спит, — это не участие,
   а давление числом.

2. Модель не может решить вопрос в одиночку. Если её голос оказывается решающим —
   то есть без него итог был бы другим, — вопрос помечается как «требует живого голоса»
   и переносится. Совет из людей и модели, где решает модель, — это уже не совет.

Скрипт голосует ТОЛЬКО за модель. Голоса людей приходят через доску (DevOps) или
вносятся секретарём.

Запуск:
    python council_vote.py 2026-08-04           # проголосовать за модель
    python council_vote.py 2026-08-04 --dry     # показать, не записывая
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent
DIR = ROOT / "data" / "council"
VOTER = "модель"

SYSTEM = """Ты — член наблюдательного совета проекта bridge42worlds. Не администратор
и не исполнитель: один голос из многих, наравне с людьми.

Проект: превращает свежие работы с arXiv в статьи, понятные любому, на пяти языках,
на четырёх глубинах. Некоммерческий, живёт на бюджет владельца. Ежедневно 20–25 коротких
разборов по аннотациям; полный разбор вчетверо дороже, делается по заказу читателя.

Тебе дана повестка заседания. По каждому вопросу выбери ОДИН вариант из предложенных
и объясни выбор.

Требования к обоснованию:
— два-три предложения, по существу, без общих слов;
— назови, чем ты пожертвовал: у любого выбора есть цена, и совет должен её видеть;
— если данных для решения не хватает — так и скажи и выбери «Отложить»;
— пиши по-русски, человеческим языком.

Помни: твой голос будет опубликован вместе с обоснованием, и люди будут с ним спорить.
Пиши так, чтобы возражать было по чему.

Ответ строго JSON:
{"votes": [{"id": "a1", "choice": "точная строка одного из вариантов",
            "why": "обоснование"}]}
Никакого текста вне JSON."""


def load(when):
    p = DIR / f"{when}.json"
    if not p.exists():
        print(f"нет заседания {when} — файл {p.relative_to(ROOT)} не найден")
        return None, None
    return p, json.loads(p.read_text(encoding="utf-8"))


def ask(agenda):
    from common import chat
    payload = {"повестка": [
        {"id": a.get("id"), "title": a.get("title"), "body": a.get("body"),
         "options": a.get("options") or ["За", "Против", "Отложить"]}
        for a in agenda]}
    resp = chat("translate_flash", json.dumps(payload, ensure_ascii=False, indent=1),
                system=SYSTEM)
    text = (resp.choices[0].message.content or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(text).get("votes") or []


def decisive(item, choice):
    """Был бы итог другим без голоса модели? Если да — решать должны живые."""
    votes = dict(item.get("votes") or {})
    without = dict(votes)
    with_model = dict(votes)
    with_model[choice] = with_model.get(choice, 0) + 1
    if not without:
        return True                       # кроме модели не голосовал никто
    top_without = max(without.values())
    winners_without = {k for k, v in without.items() if v == top_without}
    top_with = max(with_model.values())
    winners_with = {k for k, v in with_model.items() if v == top_with}
    return winners_without != winners_with


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    if not args:
        print("укажи дату заседания: python council_vote.py 2026-08-04")
        return 1
    path, data = load(args[0])
    if not data:
        return 1
    agenda = data.get("agenda") or []
    if not agenda:
        print("повестка пуста")
        return 1

    try:
        votes = ask(agenda)
    except Exception as e:
        print(f"❌ модель не проголосовала ({type(e).__name__}: {e})")
        return 1

    by_id = {a.get("id"): a for a in agenda}
    changed = 0
    for v in votes:
        item = by_id.get(v.get("id"))
        if not item:
            print(f"  ⚠️ голос по неизвестному вопросу {v.get('id')} — пропускаю")
            continue
        options = item.get("options") or ["За", "Против", "Отложить"]
        choice = v.get("choice", "")
        if choice not in options:
            # Не подгоняем: выдуманный вариант — это ошибка голосования, а не мелочь.
            print(f'  ⚠️ {item.get("title","")[:40]}: вариант «{choice}» не из списка — голос не принят')
            continue

        was_decisive = decisive(item, choice)
        print(f'\n· {item.get("title","")}')
        print(f'  голос модели: {choice}')
        print(f'  почему: {v.get("why","")[:200]}')
        if was_decisive:
            print("  ⚠️ этот голос РЕШАЮЩИЙ — вопрос помечен как требующий живого голоса")

        if dry:
            continue
        item.setdefault("votes", {})
        item["votes"][choice] = item["votes"].get(choice, 0) + 1
        item.setdefault("voices", []).append(
            {"by": VOTER, "choice": choice, "why": v.get("why", "")})
        if was_decisive:
            item["needs_human"] = True
        changed += 1

    if dry:
        print("\n[сухой прогон] ничего не записано")
        return 0
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nзаписано голосов: {changed} → {path.relative_to(ROOT)}")
    print("дальше: python council_build.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
