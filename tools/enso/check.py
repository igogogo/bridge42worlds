# -*- coding: utf-8 -*-
"""Механическая часть проверки панели El Niño перед выкладкой.

Задание проверяющего — FABLE-ПРОВЕРКА-ПАНЕЛИ.md в корне репо. Здесь то, что можно сделать
без чтения глазами: сверить каждое число вердикта с дайджестом, который видела модель;
найти ложные строки ленты; TeX, кириллицу и слипшиеся тире в текстах; пересчитать независимо
максимум индекса FAO; проверить, что у цитируемых блоков есть источник и дата. Плюс печать
всех текстов рисков, тревог и вердикта одним списком — для чтения глазами.

    python check.py            # отчёт о подозрениях
    python check.py --dump     # плюс тексты рисков, тревог и вердикта
    python check.py --links    # плюс все ссылки на работы с пояснениями

Ничего не пишет. Подозрение — не приговор: каждое перечитать и решить.
"""
import glob
import json
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[1] / "data" / "enso"
CYR = re.compile(r"[Ѐ-ӿ]")
NUM = re.compile(r"[-+−]?\d+(?:\.\d+)?")
DASH = re.compile(r"[^ \n]—[^ \n]")          # длинное тире без пробелов
SUSP = []


def flag(where, what):
    SUSP.append((where, what))
    print(f"  ? {where}: {what}")


def load(name, default=None):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except Exception as e:                                       # noqa: BLE001
        print(f"  !! {name}: {e}")
        return default


def strings(o, path=""):
    """Все строки JSON с путём до них."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield from strings(v, f"{path}.{k}" if path else k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from strings(v, f"{path}[{i}]")
    elif isinstance(o, str):
        yield path, o


def numbers(o):
    """Все числа JSON, включая числа внутри строк."""
    out = set()
    if isinstance(o, dict):
        for k, v in o.items():
            out |= numbers(str(k))                               # годы-ключи («2015») и «forecast_14d»
            out |= numbers(v)
    elif isinstance(o, list):
        for v in o:
            out |= numbers(v)
    elif isinstance(o, bool):
        pass
    elif isinstance(o, (int, float)):
        out.add(float(o))
    elif isinstance(o, str):
        for t in NUM.findall(re.sub(r"\d{4}-\d{2}(?:-\d{2})?", " ", o)):
            try:
                out.add(float(t.replace("−", "-")))
            except ValueError:
                pass
    return out


def _aslist(v):
    return v if isinstance(v, list) else ([v] if v else [])


def text_nums(text):
    t = re.sub(r"\d{4}-\d{2}(?:-\d{2})?", " ", str(text or ""))       # даты — не числа
    return [x.replace("−", "-").lstrip("+") for x in NUM.findall(t)]


# ---------------------------------------------------------------- A. вердикт против дайджеста
def check_verdict(D):
    print("\nA. Вердикт против дайджеста модели")
    sm = D.get("summary") or {}
    files = sorted(glob.glob(str(DATA / "summaries" / "*.json")))
    facts = None
    for f in reversed(files):
        try:
            j = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception:                                        # noqa: BLE001
            continue
        if (j.get("facts") or {}).get("stamp") == D.get("stamp"):
            facts = j["facts"]
            print(f"  дайджест: {Path(f).name} (штамп совпал)")
            break
    if facts is None and files:
        facts = json.loads(Path(files[-1]).read_text(encoding="utf-8")).get("facts")
        print(f"  дайджест: {Path(files[-1]).name} (ШТАМП НЕ СОВПАЛ: сверка приблизительная)")
    if not facts:
        flag("summaries/", "дайджеста нет, числа вердикта сверить не с чем")
        return
    pool = numbers(facts)
    texts = {"verdict": sm.get("verdict"), "turning_point.why": (sm.get("turning_point") or {}).get("why"),
             "changed": sm.get("changed"), "outlook_2_3w": sm.get("outlook_2_3w"), "confidence": sm.get("confidence")}
    for i, w in enumerate(_aslist(sm.get("watch"))):
        texts[f"watch[{i}]"] = w
    for i, c in enumerate(_aslist(sm.get("caveats"))):
        texts[f"caveats[{i}]"] = c
    for k in ("watch", "caveats"):
        if isinstance(sm.get(k), str):
            flag(f"summary.{k}", "строка вместо списка: модель не соблюла формат ответа")
    for k, v in (sm.get("blocks") or {}).items():
        texts[f"blocks.{k}"] = v
    for where, t in texts.items():
        if not t:
            continue
        for x in text_nums(t):
            try:
                v = float(x)
            except ValueError:
                continue
            ok = any(abs(v - p) < 0.0051 for p in pool) or any(abs(v - round(p, 1)) < 1e-9 for p in pool) \
                or any(abs(v - round(p)) < 1e-9 for p in pool)
            if not ok:
                flag(f"summary.{where}", f"число {x} не найдено в дайджесте")
        low = t.lower()
        for pat, why in ((r"per day", "«per day»: 14-дневное изменение считается за 14 дней, не в сутки"),
                         (r"highest in \d+ years", "«highest in N years»: проверить окно правила"),
                         (r"\bper week\b", "«per week»: единица не из дайджеста")):
            if re.search(pat, low):
                flag(f"summary.{where}", why)
        if DASH.search(t):
            flag(f"summary.{where}", "длинное тире без пробелов")
    rv = sm.get("review")
    if rv:
        st = "совпадает" if rv.get("stamp") == D.get("stamp") else "НЕ СОВПАДАЕТ: данные пересчитаны после проверки"
        print(f"  отметка проверки: {rv.get('model')} {rv.get('at')}, штамп {st}, blocking={rv.get('blocking')}")
    else:
        print("  отметки проверки нет")


# ---------------------------------------------------------------- B. риски
def check_risks(D):
    print("\nB. Риски")
    seen = {}
    for r in D.get("risks") or []:
        rid, t = r.get("id") or "", r.get("title") or ""
        if not rid or len(rid) >= 48 or "__" in rid or re.search(r"\d+_\d", rid):
            flag(f"risk {rid or t[:40]}", "id похож на обрезанный заголовок: история риска оборвётся при смене текста")
        if re.search(r"\d+\.\d", t) and rid:
            print(f"  · {rid}: в заголовке число с дробью ({t[:60]}), меняется с данными; id устойчив")
        for f in ("evidence", "plain", "watch", "horizon"):
            if not r.get(f):
                flag(f"risk {rid}", f"пустое поле {f}")
        for f in ("evidence", "plain", "watch", "title"):
            s = r.get(f) or ""
            if "per day" in s:
                flag(f"risk {rid}.{f}", "«per day»")
            if DASH.search(s):
                flag(f"risk {rid}.{f}", "длинное тире без пробелов")
            if "…." in s:
                flag(f"risk {rid}.{f}", "многоточие с точкой")
        if t in seen:
            flag(f"risk {rid}", f"заголовок повторяет {seen[t]}")
        seen[t] = rid
    print(f"  рисков {len(D.get('risks') or [])}, индекс {D.get('risk_index')}")


# ---------------------------------------------------------------- C. тревоги
def check_alerts(D):
    print("\nC. Тревоги")
    for a in D.get("alerts") or []:
        lvl, t, aid = a.get("level"), a.get("title") or "", a.get("id") or ""
        mark = "!!" if lvl == "SHOUT" else "  "
        print(f"  {mark} {lvl:5} {t}  [{aid}]")
        if re.search(r"\d", aid):
            flag(f"alert {aid}", "id с цифрой: лента объявит «новую» при смене числа")
        d = (a.get("detail") or "")
        if lvl == "SHOUT" and not re.search(r"record|maximum|anything measured|threshold|every model|since", d + t, re.I):
            flag(f"alert {aid}", "SHOUT без слов о рекорде или пороге в тексте: чем оправдан уровень?")
        for s in (t, d):
            if DASH.search(s):
                flag(f"alert {aid}", "длинное тире без пробелов")
            if re.search(r"\d \(\$", s):
                flag(f"alert {aid}", "единица в скобках после числа")


# ---------------------------------------------------------------- D. лента
def check_news(D):
    print("\nD. Лента")
    N = load("news.json", {}) or {}
    seen_r = load("risk-seen.json", {}) or {}
    for it in N.get("this_week") or []:
        t, d = it.get("title") or "", it.get("detail") or ""
        if it.get("kind") == "value":
            m = re.search(r"\(was (.+?) on ", d)
            head = t.split(": ", 1)[-1]
            if m and m.group(1).strip() == head.strip():
                flag(f"news {t}", "значение не изменилось, а строка есть")
            mv = re.match(r"[+](\d+\.\d+) °C", head)
            if mv and float(mv.group(1)) > 20:
                flag(f"news {t}", "знак «+» у абсолютной температуры")
        if t.startswith("New risk:"):
            rid = (it.get("go") or ["", ""])[1]
            s = seen_r.get(rid) or {}
            print(f"  · {t[:70]}: впервые увидели {s.get('first')}, quiet={s.get('quiet')}")
        if t.startswith("Alert cleared:") or (it.get("kind") == "alert" and t.split(":")[0] in ("SHOUT", "WATCH")):
            print(f"  · {t[:80]}")
    vd = [it for it in N.get("this_week") or [] if it.get("kind") == "verdict"]
    if len(vd) > 2:
        print(f"  · строк про вердикт за неделю: {len(vd)}; перечитать, действительно ли менялся смысл")
    for w in N.get("watch") or []:
        if "per day" in w:
            flag("news.watch", "«per day»")
    print(f"  строк {len(N.get('this_week') or [])}, впереди {len(N.get('next_week') or [])}")


# ---------------------------------------------------------------- E. ссылки на работы
def check_links(D, show):
    print("\nE. Ссылки на работы")
    L = load("links.json", {}) or {}
    G = (load("glossary.json", {}) or {}).get("en") or {}
    anchors = L.get("anchors") or {}
    valid = {"risk:" + (r.get("id") or "") for r in D.get("risks") or []}
    valid |= {"alert:" + (a.get("id") or "") for a in D.get("alerts") or []}
    valid |= {"region:" + (r.get("id") or "") for r in ((D.get("regions") or {}).get("items") or [])}
    valid |= {"term:" + k for k in G}
    valid |= {"block:models", "block:peak", "block:food", "block:type"}
    per_work = {}
    n = 0
    for a, ls in anchors.items():
        if a not in valid and not a.startswith("alert:"):
            flag(f"links {a}", "якоря больше нет на панели")
        for l in ls:
            n += 1
            per_work.setdefault(l["id"], []).append(a)
            for f in ("title", "why", "our_title"):
                s = str(l.get(f) or "")
                if "\\~" in s or "\\'" in s:
                    flag(f"links {a} {l['id']}", f"TeX в {f}")
                if DASH.search(s):
                    flag(f"links {a} {l['id']}", f"длинное тире без пробелов в {f}")
                if CYR.search(s):
                    flag(f"links {a} {l['id']}", f"кириллица в {f}")
            if len(l.get("why") or "") < 40:
                flag(f"links {a} {l['id']}", "пояснение why слишком короткое или пустое")
            if show:
                print(f"  {a} <- {l['id']} | {(l.get('our_title') or l.get('title') or '')[:70]}\n      {l.get('why')}")
    for w, ancs in per_work.items():
        if len(ancs) >= 5:
            print(f"  · работа {w} стоит у {len(ancs)} якорей: {', '.join(ancs[:6])}; не слишком ли общая?")
    deny = load("links-deny.json", {}) or {}
    denied = sum(len(v) for k, v in deny.items() if not k.startswith("_"))
    print(f"  ссылок {n} у {len(anchors)} якорей; снятых по deny-списку: {denied}")


# ---------------------------------------------------------------- F. язык
def check_language(D):
    print("\nF. Язык")
    files = {"latest.json": D, "news.json": load("news.json", {}), "glossary.json": load("glossary.json", {}),
             "chain-ref.json": load("chain-ref.json", {}), "models-ref.json": load("models-ref.json", {})}
    for name, obj in files.items():
        cnt = 0
        for path, s in strings(obj or {}):
            if path == "_" or path.endswith("._"):
                continue                                         # служебные русские пометки справочников
            if CYR.search(s):
                cnt += 1
                if cnt <= 5:
                    flag(f"{name} {path}", f"кириллица: {s[:60]}")
            if DASH.search(s):
                flag(f"{name} {path}", f"длинное тире без пробелов: {s[:60]}")
            if re.search(r"\d°C", s):
                flag(f"{name} {path}", f"°C без пробела: {s[:60]}")
        if cnt > 5:
            print(f"  · {name}: кириллица ещё в {cnt - 5} строках")


# ---------------------------------------------------------------- G. цитируемое против измеренного
def check_quoted(D):
    print("\nG. Цитируемое, не измеренное")
    E = (D.get("background") or {}).get("eei") or {}
    if E and not (E.get("src") and E.get("year")):
        flag("background.eei", "нет источника или года")
    G = D.get("gulf") or {}
    I = G.get("imports") or {}
    if I and not I.get("as_of"):
        flag("gulf.imports", "нет даты as_of")
    for r in I.get("rows") or []:
        if not r.get("src"):
            flag(f"gulf.imports {r.get('item')}", "нет источника")
    for r in (G.get("winter") or {}).get("refs") or []:
        u = r.get("url") or ""
        if len(u.rstrip("/").split("/")) <= 3:
            flag(f"gulf.winter.refs «{(r.get('src') or '')[:40]}»", f"ссылка на главную страницу, не на работу: {u}")
    R = D.get("regions") or {}
    if R and not R.get("as_of"):
        flag("regions", "нет даты as_of")
    print("  проверено: eei, gulf.imports, gulf.winter.refs, regions.as_of")


# ---------------------------------------------------------------- H. независимые пересчёты
def check_independent(D):
    print("\nH. Независимые пересчёты и свежесть")
    try:
        sys.path.insert(0, str(HERE))
        import sources as S
        fao = S.read_fao(DATA / "last_good" / "fao_fpi.csv")
        m, i = fao["months"], fao["index"]
        last = i[-1]
        hi60 = max(i[-60:]); hi12 = max(i[-12:])
        above = [mm for mm, v in zip(m, i) if v > last]
        lvl = "SHOUT five-year high" if last >= hi60 else ("WATCH twelve-month high" if last >= hi12 else "no price-high alert")
        print(f"  FAO {m[-1]}: {last}; max 60 мес {hi60}, max 12 мес {hi12}, выше в последний раз "
              f"{above[-1] if above else 'никогда'}; ожидается: {lvl}")
        for a in D.get("alerts") or []:
            t = a.get("title") or ""
            if "food prices" in t.lower():
                want = "five years" if last >= hi60 else ("twelve-month" if last >= hi12 else None)
                if want and want not in t:
                    flag(f"alert {a.get('id')}", f"«{t}» не согласуется с пересчётом ({lvl})")
    except Exception as e:                                       # noqa: BLE001
        print(f"  FAO: пересчёт не удался ({str(e)[:80]})")
    # тревога по глубине: SHOUT только выше рекорда буя до события (subsurface.build_record_tao)
    wm = ((D.get("subsurface") or {}).get("tao") or {}).get("warmest") or {}
    if wm:
        pm = wm.get("prev_max") or {}
        print(f"  буй {wm.get('station')}: {wm.get('value')} °C на {wm.get('depth')} м; рекорд до 2026: "
              f"{pm.get('value', 'нет')} °C {pm.get('depth', '')} м {pm.get('date', '')}; above_record={wm.get('above_record')}")
        for a in D.get("alerts") or []:
            if (a.get("id") or "").startswith("water_above_normal"):
                if a.get("level") == "SHOUT" and not wm.get("above_record"):
                    flag(f"alert {a.get('id')}", "SHOUT, а аномалия не выше рекорда буя")
                if a.get("level") == "WATCH" and wm.get("above_record"):
                    flag(f"alert {a.get('id')}", "выше рекорда буя, а уровень WATCH")
    # цены: у товара с весом ≥ 3 и годовым ходом ±30 % обязана быть тревога (air.alerts)
    aids = {a.get("id") for a in D.get("alerts") or []}
    for c in ((D.get("air") or {}).get("commodities") or {}).get("items") or []:
        w, yoy = c.get("weight") or 1, c.get("yoy_pct")
        if w >= 3 and yoy is not None and abs(yoy) >= 30 and f"price_{c.get('key')}" not in aids:
            flag(f"commodity {c.get('key')}", f"вес {w}, за год {yoy:+.0f} %, а тревоги price_{c.get('key')} нет")
        if c.get("mom_z") is not None and abs(c["mom_z"]) >= 2 and w >= 2 and f"price_{c.get('key')}" not in aids:
            flag(f"commodity {c.get('key')}", f"месячный скачок z={c['mom_z']} необычен, а тревоги нет")
    W = D.get("watch") or {}
    for k in ("sst_nino34", "sst_world", "t2_world"):
        w = W.get(k) or {}
        print(f"  {k}: данные до {w.get('last_date')} ({w.get('days_stale')} дн.), последний день {w.get('last_value')}, "
              f"изменение за 14 дней {((w.get('slope14') or {}).get('now'))} °C")
    stale = [k for k, v in (D.get("sources") or {}).items() if not v.get("fresh")]
    if stale:
        flag("sources", f"не ответили: {', '.join(stale)}")


# ---------------------------------------------------------------- дамп текстов
def dump(D):
    sm = D.get("summary") or {}
    print("\n==== ВЕРДИКТ ====")
    for k in ("verdict", "changed", "outlook_2_3w", "confidence"):
        print(f"{k}: {sm.get(k)}")
    print("turning_point:", sm.get("turning_point"))
    for k, v in (sm.get("blocks") or {}).items():
        print(f"blocks.{k}: {v}")
    for i, w in enumerate(_aslist(sm.get("watch"))):
        print(f"watch[{i}]: {w}")
    for i, c in enumerate(_aslist(sm.get("caveats"))):
        print(f"caveats[{i}]: {c}")
    print("\n==== ТРЕВОГИ ====")
    for a in D.get("alerts") or []:
        print(f"{a.get('level')} | {a.get('title')} | {a.get('detail')}")
    print("\n==== РИСКИ ====")
    for r in D.get("risks") or []:
        m = r.get("metric") or {}
        vs = m.get("values") or []
        ds = m.get("dates") or []
        print(f"\n[{r.get('level')}] {r.get('id')} · {r.get('horizon')}\nT: {r.get('title')}\nE: {r.get('evidence')}\n"
              f"P: {r.get('plain')}\nW: {r.get('watch')}\nM: {m.get('name')} {m.get('unit') or ''} "
              f"last={vs[-1] if vs else None} on {ds[-1] if ds else None}")


def main():
    D = load("latest.json", {})
    if not D:
        sys.exit("latest.json не прочитан")
    print(f"latest.json: штамп {D.get('stamp')}, данные {D.get('generated')}, индекс {D.get('risk_index')}, "
          f"рисков {len(D.get('risks') or [])}, тревог {len(D.get('alerts') or [])}, SHOUT={D.get('shout')}")
    check_verdict(D)
    check_risks(D)
    check_alerts(D)
    check_news(D)
    check_links(D, "--links" in sys.argv)
    check_language(D)
    check_quoted(D)
    check_independent(D)
    if "--dump" in sys.argv:
        dump(D)
    print(f"\nИТОГО подозрений: {len(SUSP)} (каждое перечитать; это не приговор)")


if __name__ == "__main__":
    main()
