# -*- coding: utf-8 -*-
"""Имена-двойники в реестре: слить, если один предмет; развести, если разные.

Сорок шесть русских имён носят по два-три понятия. Читателю это видно прямо:
два одинаковых заголовка в облаке, «измеряет → эхо гравитационных волн» дважды
на странице LIGO, две ссылки под одним словом в разные места.

Причины разные, и лечение разное:
  · «gravitational_wave_echo» и «gravitational_wave_echoes» — одно и то же,
    единственное против множественного. Слить.
  · «optical_resonator» и «optical_cavity» — синонимы. Слить.
  · «phase_space» и «state_space» — РАЗНЫЕ предметы, у которых совпал перевод.
    Слить нельзя; нужно вернуть различие в русское имя.
Отличить одно от другого по написанию невозможно — нужен смысл, поэтому спрашиваем
модель, и спрашиваем строго: «один это предмет или два». При «два» она обязана
предложить русское имя, которое их разводит.

ЧТО ДЕЛАЕТ СЛИЯНИЕ. Победитель — запись с бо́льшим числом статей (при равенстве —
с более длинной карточкой). Ему достаются статьи, связи, формулы, учёные, области
и синонимы проигравшего; проигравший остаётся в реестре ПЕРЕАДРЕСАЦИЕЙ
(merged_into), чтобы старые ссылки и разметка статей не превратились в 404.
Ничего не выбрасывается — это правило слияний с 18 августа.

    python tools/concept_twins.py                 показать, что решит модель
    python tools/concept_twins.py --apply         применить
    python tools/concept_twins.py --limit 10      только первые N имён
"""
import argparse
import json
import os
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from common import write_json_atomic  # noqa: E402

LIVE = ROOT / "data" / "concepts-live.json"
KNOW = ROOT / "data" / "concept-links-knowledge.json"
# По восемь групп в запросе модель отвечала на четыре и молча теряла остальные —
# ответ обрывался, а не ошибался. Четыре умещаются целиком.
PER_CALL = 4

SYS = """You decide whether concepts that share one Russian name are the SAME thing.

For each numbered group you get 2-3 concepts: id, English name, card.
Answer for each group:
  same  — one and the same subject under different ids (singular vs plural,
          word order, synonyms: "optical resonator" / "optical cavity")
  diff  — genuinely different subjects whose Russian translation collided
          ("phase space" vs "state space" — different notions in physics)

For "diff" you MUST give a distinct Russian name for EACH id, so a reader can
tell them apart. Keep the accepted term; do not invent.
For "same" give nothing but the group verdict.

Be strict: "same" only when merging them would lose nothing. If one is broader
than the other (gamma radiation vs gamma ray), that is "diff".

Return JSON: [{"n": 1, "verdict": "same"},
              {"n": 2, "verdict": "diff", "names": {"<id>": "<русское имя>"}}]
Nothing else."""


def env(k):
    if os.environ.get(k):
        return os.environ[k]
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(k + "="):
            return line.split("=", 1)[1].strip()
    raise SystemExit(f"нет {k}")


def ask(groups, key):
    lines = []
    for i, (nm, ids, live) in enumerate(groups, 1):
        lines.append(f'{i}. Russian name "{nm}":')
        for cid in ids:
            v = live[cid]
            en = (v.get("names") or {}).get("en") or cid.replace("_", " ")
            lines.append(f'   - {cid} ("{en}"): {(v.get("card_en") or "")[:160]}')
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": SYS},
                     {"role": "user", "content": "\n".join(lines)}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        raw = json.loads(r.read().decode("utf-8"))["choices"][0]["message"]["content"]
    # Модель отвечает не массивом, а НЕСКОЛЬКИМИ объектами подряд, по одному на
    # группу: {"n":1,…}\n{"n":2,…}. Первый разбор брал только первый объект — и
    # из двенадцати имён разбирались четыре, а остальные значились «ответа нет».
    # Читаем весь поток, сколько бы объектов в нём ни было.
    dec = json.JSONDecoder()
    s, got = raw.strip(), []
    if s.startswith("```"):
        s = s.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    i = 0
    while i < len(s):
        try:
            obj, end = dec.raw_decode(s, i)
        except ValueError:
            nxt = s.find("{", i + 1)
            if nxt < 0:
                break
            i = nxt
            continue
        got.append(obj)
        i = end
        while i < len(s) and s[i] in " \r\n\t,":
            i += 1
    # Ответ мог прийти и одним объектом-обёрткой со списком внутри.
    if len(got) == 1 and isinstance(got[0], dict) and "n" not in got[0]:
        for v in got[0].values():
            if isinstance(v, list):
                got = v
                break
    out = {}
    for it in (got if isinstance(got, list) else []):
        try:
            n = int(it["n"])
            if 1 <= n <= len(groups):
                out[groups[n - 1][0]] = it
        except (KeyError, TypeError, ValueError):
            continue
    return out


def winner(ids, live):
    """Кто поглощает: у кого больше статей, при равенстве — чья карточка полнее."""
    return sorted(ids, key=lambda c: (-len(live[c].get("articles") or []),
                                      -len(live[c].get("card_en") or "")))[0]


def key_of(x):
    """Чем элемент списка отличается от прочих.

    В реестре один и тот же список бывает двух форм: просто строки и записи вроде
    {"name": …, "line": …} или {"id": …, "w": …}. Обе живые — приводить одну к
    другой нельзя, потеряется пояснение или вес. Поэтому сравниваем по имени, а
    хранить продолжаем как есть.
    """
    if isinstance(x, dict):
        return x.get("id") or x.get("name")
    return x


def join(xs, ys, skip=()):
    """Сложить два списка без повторов, сохранив форму элементов."""
    out, seen = [], set()
    for x in list(xs or []) + list(ys or []):
        k = key_of(x)
        if k is None or k in seen or k in skip:
            continue
        out.append(x)
        seen.add(k)
    return out


def retarget(live):
    """Перевести все связи со слитых понятий на победителей.

    Слияние оставляет проигравшего указателем, и связи, которые вели на него,
    формально работают — через переадресацию. Но это ложная целость: в графе
    появляется узел-пустышка без статей, в облаке D1 — строка, ведущая в никуда,
    а читатель на странице проходит лишний прыжок. Поэтому после слияний
    проходим по соседям и по связям знания и заменяем адрес на победителя,
    выбрасывая ставшие самоссылками и дубли.
    """
    m = {c: v["merged_into"] for c, v in live.items() if v.get("merged_into")}
    if not m:
        return 0, 0
    n_rel = 0
    for cid, v in live.items():
        if v.get("merged_into"):
            continue
        rel, seen = [], set()
        for r in (v.get("related") or []):
            tgt = m.get(r.get("id"), r.get("id"))
            if tgt == cid or tgt in seen:
                n_rel += 1
                continue
            if tgt != r.get("id"):
                r = dict(r, id=tgt)
                n_rel += 1
            rel.append(r)
            seen.add(tgt)
        v["related"] = rel

    n_kn = 0
    if KNOW.exists():
        try:
            kn = json.loads(KNOW.read_text(encoding="utf-8"))
        except Exception:
            kn = {}
        out = {}
        for cid, links in kn.items():
            src = m.get(cid, cid)
            if live.get(src, {}).get("merged_into"):
                continue
            keep_l, seen_l = out.setdefault(src, []), set()
            for lk in links:
                tgt = m.get(lk.get("to"), lk.get("to"))
                if tgt == src or (tgt, lk.get("rel")) in seen_l:
                    n_kn += 1
                    continue
                if tgt != lk.get("to") or src != cid:
                    n_kn += 1
                keep_l.append(dict(lk, to=tgt))
                seen_l.add((tgt, lk.get("rel")))
        KNOW.write_text(json.dumps({k: v for k, v in out.items() if v},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
    return n_rel, n_kn


def merge(keep, drop, live):
    """Перенести всё из drop в keep; drop оставить переадресацией."""
    a, b = live[keep], live[drop]
    for field in ("articles", "scientists", "supers", "formulas"):
        a[field] = join(a.get(field), b.get(field))
    # Соседи: сам победитель себе не сосед.
    a["related"] = join(a.get("related"), b.get("related"), skip={keep})
    # Синонимом победителя становится и сам проигравший id, и его английское имя:
    # разметка статей ссылается на id, поиск — на имя.
    extra = [{"name": e, "line": (b.get("card_en") or "")[:200]}
             for e in (drop, (b.get("names") or {}).get("en")) if e]
    a["aliases"] = join(join(a.get("aliases"), b.get("aliases")), extra)
    # Проигравший не удаляется: на него ссылается разметка тысяч статей и внешние
    # ссылки. Остаётся записью-указателем — страница отдаст переадресацию.
    live[drop] = {"merged_into": keep, "names": b.get("names") or {},
                  "kind": b.get("kind"), "articles": [], "related": [],
                  "formulas": [], "scientists": [], "supers": []}


def main():
    ap = argparse.ArgumentParser(description="Имена-двойники: слить или развести")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    doc = json.loads(LIVE.read_text(encoding="utf-8"))
    live = doc["concepts"]
    by = defaultdict(list)
    for cid, v in live.items():
        if v.get("merged_into"):
            continue
        nm = (v.get("names") or {}).get("ru")
        if nm:
            by[nm].append(cid)
    twins = [(nm, ids) for nm, ids in by.items() if len(ids) > 1]
    twins.sort(key=lambda t: -sum(len(live[c].get("articles") or []) for c in t[1]))
    if a.limit:
        twins = twins[:a.limit]
    if not twins:
        print("имён-двойников нет")
        return 0
    print(f"имён-двойников: {len(twins)}")

    key = env("DEEPSEEK_API_KEY")
    groups = [(nm, ids, live) for nm, ids in twins]
    verdicts = {}

    def sweep(gs):
        for i in range(0, len(gs), PER_CALL):
            try:
                verdicts.update(ask(gs[i:i + PER_CALL], key))
            except Exception as e:
                print(f"  пачка пропущена: {type(e).__name__}: {str(e)[:70]}")

    # Переспрашиваем, пока отвечают: ответ обрывается непредсказуемо, и пропущенное
    # имя — это двойник, оставшийся на витрине. Дешевле спросить трижды, чем потом
    # разбирать руками. Круг без единого нового ответа заканчивает попытки — иначе
    # на упрямом имени можно ходить вечно.
    sweep(groups)
    for _ in range(3):
        left = [g for g in groups if g[0] not in verdicts]
        if not left:
            break
        print(f"переспрашиваем про {len(left)}")
        before = len(verdicts)
        sweep(left)
        if len(verdicts) == before:
            break

    merged = renamed = 0
    silent = []          # вердикт есть, а делать нечего — тоже результат
    for nm, ids in twins:
        v = verdicts.get(nm)
        if not v:
            silent.append((nm, "ответа нет"))
            continue
        if v.get("verdict") == "diff" and not (v.get("names") or {}):
            # модель сочла разными, но различающих имён не дала — значит
            # двойник остаётся на витрине, и молчать об этом нельзя
            silent.append((nm, "разные, но имён не предложено"))
            continue
        if v.get("verdict") == "same":
            keep = winner(ids, live)
            for other in ids:
                if other != keep:
                    print(f"  слить: {other} → {keep}  («{nm}»)")
                    if a.apply:
                        merge(keep, other, live)
                    merged += 1
        elif v.get("verdict") == "diff":
            names = v.get("names") or {}
            for cid, new in names.items():
                if cid in live and new and new != nm:
                    print(f"  развести: {cid} → «{new}»  (было «{nm}»)")
                    if a.apply:
                        live[cid].setdefault("names", {})["ru"] = new
                    renamed += 1

    if silent:
        print(f"\nбез решения — {len(silent)}:")
        for nm, why in silent[:20]:
            print(f"  «{nm}» — {why}")
    print(f"\nслито {merged} · переименовано {renamed}")
    if not a.apply:
        print("проба. применить: --apply")
        return 0

    n_rel, n_kn = retarget(live)
    if n_rel or n_kn:
        print(f"связей переведено на победителей: {n_rel} у соседей, {n_kn} по знанию")
    write_json_atomic(LIVE, doc, indent=None)
    print(f"→ {LIVE.name} обновлён")
    return 0


if __name__ == "__main__":
    sys.exit(main())
