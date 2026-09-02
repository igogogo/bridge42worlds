#!/usr/bin/env python3
"""Реестр контактов авторов: почты из PDF наших же статей.

Владелец 2026-08-19: целевая аудитория — авторы; «как бы мы ни старались, пока о нас
они не узнают — мы вне игры»; и отдельно — «как следует подготовься, чтобы получить
почты». Официального реестра почт авторов arXiv не существует: API отдаёт имена без
адресов, и это сознательная политика arXiv. Но адрес контактного автора напечатан
на первой странице самого PDF — а PDF каждой нашей статьи уже лежит у нас на диске
(original.pdf, скачан конвейером). Стратегия начинается не с роботов по интернету,
а с чтения того, что авторы сами опубликовали в работе, которую мы разобрали.

ЧТО ИЗВЛЕКАЕМ. Адреса с первых двух и последней страницы (в письмах-препринтах адрес
живёт в сноске первой страницы или после заключения). Разворачиваем скобочную запись
{ivanov,petrov}@dom — она в физике обычна. Каждый адрес пытаемся ПРИВЯЗАТЬ к автору
статьи: фамилия из data.json ищется в локальной части адреса; привязка пишется только
при единственном кандидате, иначе адрес остаётся «на статью», без имени. Не угадываем.

ГДЕ ЖИВЁТ РЕЗУЛЬТАТ И ПОЧЕМУ ИМЕННО ТАМ. data/authors-contacts.jsonl — В GIT НЕ ИДЁТ
(закрыт в .gitignore этим же коммитом): почты — персональные данные живых людей,
репозиторий переживёт и человека, и его согласие; тот же принцип, что у входящих
совета. В data/ публикующийся конвейер его тоже не подхватит: публикация идёт
белым списком deploy_r2, а не «всё из data/».

РЯДОМ — ЖУРНАЛ ОТПРАВОК (authors-outreach.jsonl, тоже вне git): владелец просил
видеть, кому что ушло. Каждая строка: почта, ключ автора, статья, тема письма, когда,
чем кончилось. Журнал заполняет БУДУЩИЙ инструмент рассылки; здесь только формат,
чтобы реестр и журнал родились согласованными. Правило рассылки уже решено: одно
письмо — и тишина, никаких цепочек.

Запуск ИЗ ГЛАВНОЙ ПАПКИ:
    python tools/author_contacts.py --full-only     сначала разобранные (654 статьи)
    python tools/author_contacts.py                 весь корпус (~6 900 PDF)
    python tools/author_contacts.py --stats         сводка по готовому реестру
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tools"))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from pypdf import PdfReader                  # noqa: E402
from author_record import key_from_display   # noqa: E402

OUT = ROOT / "data" / "authors-contacts.jsonl"

# Адрес: локальная часть либо простая, либо скобочная {a,b,c}. Точка на конце домена
# отрезается отдельно — в PDF адрес часто стоит в конце предложения.
RE_MAIL = re.compile(
    r"(\{[\w.\-+,;\s]{1,120}\}|[\w.\-+]{1,64})\s*@\s*([\w\-]+(?:\.[\w\-]+)+)")

# Мусорные адреса: служебные ящики издательств и самого arXiv авторами не являются.
BAD_LOCAL = {"info", "admin", "support", "help", "webmaster", "contact", "office",
             "editor", "editors", "submissions", "noreply", "no-reply"}
BAD_DOM = ("arxiv.org", "example.", "elsevier.", "springer.", "wiley.", "iop.org",
           "aps.org", "overleaf.")


def emails_from_text(text):
    """Адреса из готового текста. Вынесено из emails_from_pdf: разбор один и тот же,
    источников теперь два — сохранённый текст работы и (для пятнадцати старых работ) PDF."""
    return _harvest(text)


def emails_from_pdf(path):
    """Адреса с первых двух и последней страницы. Ошибка чтения PDF — это «адресов
    не нашли», а не падение прогона: битый файл не должен останавливать 6 900 других."""
    try:
        rd = PdfReader(str(path))
        pages = rd.pages
        idx = list(range(min(2, len(pages)))) + ([len(pages) - 1] if len(pages) > 2 else [])
        text = ""
        for i in idx:
            try:
                text += (pages[i].extract_text() or "") + "\n"
            except Exception:
                continue
    except Exception:
        return []
    return _harvest(text)


def _harvest(text):
    """Единственный разбор адресов: раскрытие скобочной записи
    {ivanov,petrov}@dom, отсев служебных ящиков и издательских доменов."""
    found = []
    for m in RE_MAIL.finditer(text):
        local, dom = m.group(1), m.group(2).rstrip(".").lower()
        if any(b in dom for b in BAD_DOM):
            continue
        locals_ = ([p.strip() for p in local.strip("{}").replace(";", ",").split(",")]
                   if local.startswith("{") else [local])
        for lp in locals_:
            lp = lp.strip().strip(".")
            if not lp or lp.lower() in BAD_LOCAL or len(lp) > 64:
                continue
            e = f"{lp}@{dom}"
            if e.lower() not in {x.lower() for x in found}:
                found.append(e)
    return found


def bind(emails, authors):
    """Привязка адреса к автору по фамилии в локальной части. Только при ЕДИНСТВЕННОМ
    кандидате: угадать неправильно хуже, чем оставить адрес обезличенным."""
    keys = {}
    for name in authors:
        k = key_from_display(name)
        if k:
            keys[k] = name
    out = []
    for e in emails:
        lp = e.split("@")[0].lower()
        cands = [(k, n) for k, n in keys.items()
                 if len(k.split("|")[0]) >= 4 and k.split("|")[0] in lp]
        rec = {"email": e}
        if len(cands) == 1:
            rec["akey"], rec["name"] = cands[0]
        out.append(rec)
    return out


def load_existing():
    if not OUT.exists():
        return {}
    rows = {}
    for line in OUT.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
            rows[r["id"]] = r
        except Exception:
            continue
    return rows


def stats():
    rows = load_existing()
    n_mail = sum(len(r.get("emails") or []) for r in rows.values())
    bound = sum(1 for r in rows.values() for e in r.get("emails") or [] if e.get("akey"))
    with_any = sum(1 for r in rows.values() if r.get("emails"))
    uniq = {e["email"].lower() for r in rows.values() for e in r.get("emails") or []}
    print(f"статей в реестре: {len(rows)} · с адресами: {with_any} "
          f"({with_any * 100 // max(len(rows), 1)}%)")
    print(f"адресов: {n_mail} · уникальных: {len(uniq)} · привязано к автору: {bound}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full-only", action="store_true")
    ap.add_argument("--stats", action="store_true")
    a = ap.parse_args()
    if a.stats:
        stats()
        return 0

    done = load_existing()
    new = 0
    scanned = 0
    with OUT.open("a", encoding="utf-8") as fh:
        for f in sorted(Path("lang/ru/archive").glob("*/*/data.json"), reverse=True):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if a.full_only and d.get("express"):
                continue
            aid = d.get("id") or f.parent.name
            if aid in done:
                continue
            # ТЕКСТ РАБОТЫ, А НЕ PDF. Исходные PDF удалены 2026-09-01 (29.6 ГБ, на сайт
            # они не выкладывались), но разобранный текст лежит рядом — им и пользуемся.
            # Адрес для переписки печатают в шапке и в конце, поэтому берём начало и хвост.
            txt = f.parent / "fulltext.txt"
            pdf = f.parent / "original.pdf"
            if txt.exists() and txt.stat().st_size > 2000:
                whole = txt.read_text(encoding="utf-8", errors="ignore")
                emails = emails_from_text(whole[:6000] + chr(10) + whole[-3000:])
            elif pdf.exists():
                emails = emails_from_pdf(pdf)
            else:
                continue
            scanned += 1
            rec = {"id": aid, "date": f.parent.parent.name,
                   "full": not d.get("express"),
                   "title": (d.get("original_title") or "")[:120],
                   "emails": bind(emails, d.get("authors") or [])}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            new += 1
            if scanned % 200 == 0:
                print(f"  просмотрено {scanned}, добавлено {new}")
    print(f"готово: просмотрено {scanned}, добавлено {new}")
    stats()
    return 0


if __name__ == "__main__":
    sys.exit(main())
