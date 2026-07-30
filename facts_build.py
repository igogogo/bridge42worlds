#!/usr/bin/env python3
"""Каталог интересных фактов и мини-опросов — из того, что уже оплачено.

Идея владельца (ночь 2026-07-30): пока читатель ждёт перевода или генерации статьи,
показывать не спиннер, а интересное: факт, мини-опрос с неожиданным ответом, баллы.

Ничего не генерируем заново: у КАЖДОЙ статьи уже есть поля `fun_fact` (занятный факт),
`scifi` (отсылка к фантастике) и `key_numbers` (числа результата) на всех языках —
они писались моделью и оплачены, но живут только внутри своей страницы. Собираем их
в один каталог и заодно делаем из чисел вопросы «как думаешь?».

Выход: data/facts-<lang>.json (лёгкие, до ~200 КБ) — читаются экраном ожидания
и страницей каталога.

Запуск: python facts_build.py
"""
import json
import random
import re
from pathlib import Path

from common import CONFIG, LANG_DIR, DEFAULT_LANG

LANGS = CONFIG.get("languages", ["ru"])
OUT = Path("data")
MIN_FACT = 40          # короче — это обрывок, не факт
MAX_FACT = 400
NUM_RE = re.compile(r"^-?\d[\d\s.,]*$")


def tier_of(article, lang):
    """Поле берём из popular (он у всех), с откатом на simple/advanced."""
    for t in ("popular", "simple", "advanced"):
        v = (article.get(t) or {}).get(lang)
        if isinstance(v, dict) and v:
            return v
    return {}


def quiz_from_numbers(scipop, title, aid, lang):
    """Мини-опрос из key_numbers: берём число результата и строим три варианта —
    верный, вдесятеро больше, вдесятеро меньше. Порядок величины — то, на чём
    интуиция ошибается чаще всего, и именно это делает ответ «неожиданным»."""
    kn = scipop.get("key_numbers") or {}
    if not isinstance(kn, dict):
        return None
    for label, value in kn.items():
        sval = str(value).strip()
        m = re.match(r"^~?\s*([\d.,]+)\s*(.*)$", sval)
        if not m:
            continue
        try:
            num = float(m.group(1).replace(",", ".").replace(" ", ""))
        except ValueError:
            continue
        if num <= 0:
            continue
        unit = m.group(2).strip()

        def fmt(x):
            if x >= 100:
                return f"{x:,.0f}".replace(",", " ")
            if x >= 1:
                return f"{x:.1f}".rstrip("0").rstrip(".")
            return f"{x:.3g}"

        options = [f"{fmt(num)} {unit}".strip(),
                   f"{fmt(num * 10)} {unit}".strip(),
                   f"{fmt(num / 10)} {unit}".strip()]
        if len(set(options)) < 3:
            continue
        random.shuffle(options)
        return {"q": str(label).strip(), "options": options,
                "answer": f"{fmt(num)} {unit}".strip(),
                "title": title, "id": aid}
    return None


def main():
    for lang in LANGS:
        facts, quizzes, seen = [], [], set()
        root = Path(LANG_DIR) / DEFAULT_LANG / "archive"
        for dj in root.glob("*/*/data.json"):
            try:
                d = json.loads(dj.read_text(encoding="utf-8"))
            except Exception:
                continue
            sp = tier_of(d, lang)
            if not sp:
                continue
            aid, date = d.get("id", ""), d.get("date", "")
            title = (sp.get("title") or "").strip()
            url = f"/{LANG_DIR}/{lang}/archive/{date}/{aid}/"

            for field, kind in (("fun_fact", "fact"), ("scifi", "scifi")):
                txt = (sp.get(field) or "").strip()
                if not (MIN_FACT <= len(txt) <= MAX_FACT):
                    continue
                key = txt[:60].lower()
                if key in seen:
                    continue
                seen.add(key)
                facts.append({"t": txt, "k": kind, "title": title, "url": url, "date": date})

            q = quiz_from_numbers(sp, title, aid, lang)
            if q:
                q["url"] = url
                quizzes.append(q)

        facts.sort(key=lambda f: f["date"], reverse=True)
        quizzes.sort(key=lambda q: q.get("id", ""), reverse=True)
        payload = {"facts": facts[:1200], "quizzes": quizzes[:600]}
        p = OUT / f"facts-{lang}.json"
        p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        size = p.stat().st_size // 1024
        print(f"{lang}: фактов {len(payload['facts'])}, опросов {len(payload['quizzes'])} → {p} ({size} КБ)")


if __name__ == "__main__":
    main()
