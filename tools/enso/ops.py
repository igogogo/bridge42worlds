# -*- coding: utf-8 -*-
"""Служебный слой панели: журнал прогонов и состояние источников (вкладка Ops).

Владелец 06.09: «нужна страница, чтобы видел эти пайплайны: когда были запущены, какого типа,
время выполнения и статус на сейчас; по каждому источнику его диапазон дат и дата обновления,
если были ошибки; можно не в реальном времени, но по факту завершения каждого пайплайна».

Два файла в data/enso, оба уезжают на сайт вместе с данными:
  runs.json — журнал прогонов (последние 100): вид, начало, конец, секунды, статус, итог, ошибки.
  ops.json  — состояние на сейчас: каждый источник с диапазоном дат, датой обновления, свежестью и
              ошибкой; хвост журнала прогонов; свежий слой одной строкой.

Виды прогонов: full (правила + модель + снимок), light (только правила, свежий слой), links
(разметка нашими работами), records (рекорды буёв), publish, review (отметка проверки).
"""
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Своя запись файлов: повтор при осечке файловой системы и подмена целиком (17.09).
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
import safeio   # noqa: E402
ROOT = HERE.parents[1] / "data" / "enso"
RUNS = ROOT / "runs.json"
OPS = ROOT / "ops.json"
KEEP = 100

KIND_LABEL = {
    # подписи этого словаря видны на экране, во вкладке Ops, — значит по-английски
    "phase": "phase change watch: relations, memory of the long records, the way back",
    "zones_flow": "between the zones: which patch warms first, and how far the event leans",
    "full": "full update: rules, model verdict, snapshot",
    "light": "light run: rules only, fresh layer",
    "links": "links to our works",
    "futures": "exchange futures for food goods: daily and weekly closes",
    "records": "mooring records",
    "publish": "publish to the site",
    "publish-fresh": "publish the fresh layer only",
    "review": "review mark (Fable)",
    "planet": "long record (gases, ice, temperature, sea level)",
    "mentions": "mentions feed (GDELT, Wikipedia, official feeds)",
    "hovmoller": "Hovmöller diagram (GODAS)",
    "spectral": "spectral watch: a line at 2–7 days in the daily series",
    "regions-daily": "land regions on Dynamics (ERA5 boxes, like Niño 3.4)",
    "precip": "rain: ERA5 box sums and GPCP planet",
    "radiance": "raw satellite granules (external collector C:\\CL\\radiance), copied in",
    "stats": "statistics layer: regression, change-points, persistence, clusters, extremes, correlations",
    "layout": "layout walk: every scene in a headless browser at three widths",
}


def _load(p, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:                                            # noqa: BLE001
        return default


def _save(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    safeio.write_text(p, json.dumps(obj, ensure_ascii=False, indent=1))


# ------------------------------------------------------------------ журнал прогонов
class Run:
    """Один прогон: завести в начале, закрыть в конце. Ошибки копятся по дороге."""

    def __init__(self, kind, note=""):
        self.kind, self.note = kind, note
        self.t0 = time.time()
        self.started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.errors = []

    def error(self, text):
        self.errors.append(str(text)[:200])

    def finish(self, status="ok", **info):
        rec = {"kind": self.kind, "label": KIND_LABEL.get(self.kind, self.kind),
               "started": self.started, "finished": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
               "secs": int(round(time.time() - self.t0)), "status": status, "note": self.note,
               "errors": self.errors}
        rec.update({k: v for k, v in info.items() if v is not None})
        record(rec)
        return rec


def record(rec):
    runs = _load(RUNS, [])
    runs.append(rec)
    runs = runs[-KEEP:]
    _save(RUNS, runs)
    # ops.json держит хвост журнала: обновляем его, не трогая остального
    ops = _load(OPS, None)
    if isinstance(ops, dict):
        ops["runs"] = runs[-60:]
        ops["runs_built"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        _save(OPS, ops)
    return runs


def record_run(kind, started, finished, status="ok", note="", **info):
    """Запись задним числом (по логам): для прогонов, которые шли до появления журнала."""
    try:
        t0 = datetime.strptime(started, "%Y-%m-%d %H:%M:%S")
        t1 = datetime.strptime(finished, "%Y-%m-%d %H:%M:%S")
        secs = int((t1 - t0).total_seconds())
    except ValueError:
        secs = None
    rec = {"kind": kind, "label": KIND_LABEL.get(kind, kind), "started": started, "finished": finished,
           "secs": secs, "status": status, "note": note, "errors": []}
    rec.update({k: v for k, v in info.items() if v is not None})
    return record(rec)


# ------------------------------------------------------------------ источники
def _q(yf):
    """2026.125 → «2026 Q1» (дробный год NCEI — середина квартала)."""
    iy = int(yf)
    q = int(round((yf - iy - 0.125) / 0.25)) + 1
    return f"{iy} Q{max(1, min(4, q))}"


def _range(kind, key, path):
    """(с, по, точек) по сырому файлу через ту же читалку, что и панель."""
    import sources as S
    if kind == "cr_json":
        d = S.read_cr_json(path)
        ys = sorted(d["years"])
        return (f"{ys[0]}-01-01", str(d["last_date"]), len(ys))
    if kind == "noaa_weekly":
        rows = S.read_noaa_weekly(path)
        return (str(rows[0]["date"]), str(rows[-1]["date"]), len(rows))
    if kind in ("oni_txt", "roni_txt"):
        rows = S.read_oni(path) if kind == "oni_txt" else S.read_roni(path)
        return (f"{rows[0][0]} {rows[0][1]}", f"{rows[-1][0]} {rows[-1][1]}", len(rows))
    if kind == "psl_monthly":
        d = S.read_psl_monthly(path)
        ks = [f"{y}-{m:02d}" for y, vals in sorted(d.items()) for m, v in enumerate(vals, 1) if v == v]
        return (ks[0], ks[-1], len(ks))
    if kind == "fao_csv":
        d = S.read_fao(path)
        return (d["months"][0], d["months"][-1], len(d["months"]))
    if kind in ("cpc_table", "pmel"):
        d = S.read_cpc_table(path) if kind == "cpc_table" else S.read_pmel(path)
        ks = sorted(d)
        return (ks[0], ks[-1], len(ks))
    if kind == "uah":
        ks = sorted(S.read_uah(path)["globe"])
        return (ks[0], ks[-1], len(ks))
    if kind == "xlsx":
        d = S.read_pink(path)
        ks = sorted({k for rec in d.values() for k in (rec.get("series") or {})})
        return (ks[0], ks[-1], len(ks))
    if kind == "omi_txt":
        ks = sorted(S.read_omi(path))
        return (ks[0], ks[-1], len(ks))
    if kind == "ncei_ohc":
        rows = S.read_ohc(path)
        return (_q(rows[0][0]), _q(rows[-1][0]), len(rows))
    if kind == "json":
        t = (S.read_json(path).get("daily") or {}).get("time") or []
        return (t[0], t[-1], len(t)) if t else (None, None, 0)
    return (None, None, None)


def _behind(to):
    """Сколько дней назад кончаются данные, если дата суточная."""
    try:
        return (date.today() - date.fromisoformat(str(to)[:10])).days if to and len(str(to)) >= 10 else None
    except ValueError:
        return None


def _chain_map():
    """Каденция и адрес источника из chain-ref.json: по ключу источника и по id узла."""
    ref = _load(ROOT / "chain-ref.json", {}) or {}
    by_key, by_id = {}, {}
    for n in ref.get("nodes") or []:
        if n.get("layer") != "src":
            continue
        by_id[n.get("id")] = n
        for k in n.get("src_keys") or []:
            by_key[k] = n
    return by_key, by_id


def sources_status(cur):
    """Каждый источник панели: подпись, каденция, адрес, диапазон данных, когда обновлён, ответил ли, ошибка."""
    import sources as S
    by_key, by_id = _chain_map()
    st = cur.get("sources") or {}
    out = []

    def push(key, label, node, data_from, data_to, n, fetched, fresh, error, group=""):
        out.append({"key": key, "label": label, "group": group,
                    "cadence": (node or {}).get("cadence"), "url": (node or {}).get("url"),
                    "data_from": data_from, "data_to": data_to, "n": n, "behind_days": _behind(data_to),
                    "fetched": fetched, "fresh": bool(fresh), "error": error or ""})

    # 1. классические источники: файл в last_good, читалка, диапазон
    ohc = {}
    for key, (url, kind) in S.SOURCES.items():
        p = S.LAST / (key + S.ext_of(kind))
        fetched = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M") if p.exists() else None
        s = st.get(key) or {}
        try:
            fr, to, n = _range(kind, key, p) if p.exists() else (None, None, None)
            rerr = ""
        except Exception as e:                                   # noqa: BLE001
            fr, to, n, rerr = None, None, None, f"reader: {str(e)[:80]}"
        err = s.get("error") or rerr
        if key.startswith("ohc_"):                               # восемь квартальных файлов → две строки
            depth = key.split("_")[1]
            g = ohc.setdefault(depth, {"from": [], "to": [], "n": 0, "fresh": True, "errors": [], "fetched": fetched})
            if fr: g["from"].append(fr)
            if to: g["to"].append(to)
            g["n"] += n or 0
            g["fresh"] = g["fresh"] and bool(s.get("fresh"))
            if err: g["errors"].append(f"{key}: {err}")
            continue
        node = by_key.get(key)
        push(key, S.LABELS.get(key, key), node, fr, to, n, fetched, s.get("fresh"), err, "files")
    for depth, g in ohc.items():
        push(f"ohc_{depth}", f"Ocean heat content 0–{depth} m, four quarterly files (NCEI)", by_id.get("s_ohc"),
             min(g["from"]) if g["from"] else None, max(g["to"]) if g["to"] else None, g["n"], g["fetched"],
             g["fresh"], "; ".join(g["errors"]), "files")

    # 2. источники модулей: их состояние живёт в самих блоках
    stamp = cur.get("stamp")
    ob = (cur.get("oisst") or {}).get("boxes") or {}
    # запад → восток: в этом порядке строки лягут в таблицу источников на вкладке Ops
    for bk, bl in (("nino4", "Niño 4"), ("nino34", "Niño 3.4"), ("nino3", "Niño 3"), ("nino12", "Niño 1+2"), ("gulf", "Persian Gulf"), ("world", "World ocean")):
        b = ob.get(bk) or {}
        if not b:
            continue
        ds = b.get("dates") or []
        push(f"nrt_{bk}", f"OISST NRT daily box, {bl}", by_id.get("s_nrt"), ds[0] if ds else None, b.get("last_date"), len(ds),
             stamp, not b.get("error"), b.get("error") or "", "modules")
    tao = (cur.get("subsurface") or {}).get("tao") or {}
    for s_ in tao.get("stations") or []:
        ds = ((s_.get("d20_series") or {}).get("dates") or [])
        rc = s_.get("record") or {}
        push(f"tao_{s_.get('name')}", f"TAO mooring {s_.get('label')}, daily temperature by depth", by_id.get("s_tao"),
             (rc.get("from") or (ds[0] if ds else None)), s_.get("last_date"), len(ds), stamp, not s_.get("error"), s_.get("error") or "", "modules")
    gd = (cur.get("subsurface") or {}).get("godas") or {}
    if gd:
        hm = (gd.get("heat_content") or {}).get("months") or []
        push("godas", "GODAS reanalysis section and heat content", by_id.get("s_godas"), hm[0] if hm else None, gd.get("month"), len(hm),
             stamp, not gd.get("error"), gd.get("error") or "", "modules")
    er = (cur.get("wind") or {}).get("era5") or {}
    if er:
        ds = er.get("dates") or []
        push("era5_wind", "ERA5 10 m wind, six equatorial points", by_id.get("s_era5"), ds[0] if ds else None, er.get("last_date"), len(ds),
             stamp, not er.get("error"), er.get("error") or "", "modules")
    ir = cur.get("iri") if isinstance(cur.get("iri"), dict) else {}
    if ir:
        iss = [h.get("issued") for h in (ir.get("history") or []) if h.get("issued")]
        push("iri", "IRI model plume, monthly issues", by_id.get("s_iri"), iss[-1] if iss else None, ir.get("issued"), len(iss),
             stamp, "error" not in ir, ir.get("error") or "", "modules")
    return out


HIST = ROOT / "ops-history.json"
HIST_KEEP = 40                     # сколько приходов держим на источник


def _history(srcs):
    """Когда у источника появлялся новый день данных — и что из этого следует.

    Владелец 16.09: «можно там видеть history тоже, кнопочку — когда обновлялся, то есть
    появлялись данные за когда, и когда следующие».

    ЗАПИСЫВАЕМ НЕ КАЖДЫЙ ПРОГОН, А КАЖДОЕ ИЗМЕНЕНИЕ. Прогонов в сутки несколько, и если писать
    все, файл распухнет, а читать его будет нечего: строка «источник ответил то же самое» —
    не событие. Событие — это НОВЫЙ последний день данных. Его и кладём, вместе с датой, когда
    мы его увидели: разница между ними и есть настоящее отставание источника.

    КАДЕНЦИЯ ИЗМЕРЯЕТСЯ, А НЕ ОБЪЯВЛЯЕТСЯ. В таблице у источников стоит текстовое поле вроде
    «daily, 1–3 weeks behind» — это то, что мы сами про них написали. Здесь считается медиана
    фактических промежутков между приходами, и «ждать следующего» строится по ней. Пока
    приходов меньше трёх, ничего не обещаем и так и пишем.
    """
    prev = _load(HIST, {})
    store = prev.get("sources") if isinstance(prev, dict) else {}
    store = store if isinstance(store, dict) else {}
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    for s0 in srcs:
        k = s0.get("key")
        if not k:
            continue
        rec = store.setdefault(k, {"arrivals": []})
        arr = rec["arrivals"]
        to = s0.get("data_to")
        if to and (not arr or arr[-1].get("data_to") != to):
            arr.append({"data_to": to, "seen": now,
                        "behind_days": s0.get("behind_days"),
                        "error": (s0.get("error") or "")[:60] or None})
            del arr[:-HIST_KEEP]
        # сколько суток подряд источник не приносит нового дня
        rec["last_change_seen"] = arr[-1]["seen"] if arr else None
        rec["n_arrivals"] = len(arr)
        gaps = []
        for a, b in zip(arr, arr[1:]):
            try:
                d0 = datetime.strptime(a["seen"][:10], "%Y-%m-%d")
                d1 = datetime.strptime(b["seen"][:10], "%Y-%m-%d")
                g = (d1 - d0).days
                if g > 0:
                    gaps.append(g)
            except Exception:                                    # noqa: BLE001
                pass
        if len(gaps) >= 2:
            gaps_sorted = sorted(gaps)
            med = gaps_sorted[len(gaps_sorted) // 2]
            rec["cadence_measured_days"] = med
            rec["cadence_spread_days"] = [gaps_sorted[0], gaps_sorted[-1]]
            try:
                last = datetime.strptime(arr[-1]["seen"][:10], "%Y-%m-%d")
                rec["next_expected"] = (last + timedelta(days=med)).strftime("%Y-%m-%d")
                rec["overdue_days"] = max(0, (datetime.now() - (last + timedelta(days=med))).days)
            except Exception:                                    # noqa: BLE001
                pass
        else:
            rec["cadence_measured_days"] = None
            rec["next_expected"] = None
            rec["overdue_days"] = None
    doc = {"built": now, "keep": HIST_KEEP, "sources": store,
           "note": ("One line per ARRIVAL, not per run: a row appears when a source first hands us a new last "
                    "day of data. The gap between that day and the moment we saw it is the source's real lag. "
                    "The cadence here is measured from those gaps, not taken from what we wrote about the source; "
                    "until three arrivals are on record nothing is promised.")}
    _save(HIST, doc)
    return store


def build(cur, fresh=None):
    """ops.json: источники, хвост журнала прогонов, свежий слой одной строкой, календарь."""
    try:
        srcs = sources_status(cur)
    except Exception as e:                                       # noqa: BLE001
        srcs = [{"key": "ops", "label": "sources status failed", "error": str(e)[:160], "fresh": False}]
    try:
        hist = _history(srcs)
    except Exception as e:                                       # noqa: BLE001
        hist = {}
        print("история источников не записана:", str(e)[:100])
    for s0 in srcs:
        h = hist.get(s0.get("key")) or {}
        # в саму таблицу кладём только итог: сам список приходов живёт в ops-history.json
        s0["n_arrivals"] = h.get("n_arrivals")
        s0["cadence_measured_days"] = h.get("cadence_measured_days")
        s0["next_expected"] = h.get("next_expected")
        s0["overdue_days"] = h.get("overdue_days")
        s0["last_change_seen"] = h.get("last_change_seen")
        s0["arrivals"] = (h.get("arrivals") or [])[-8:]
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "assessed_stamp": cur.get("stamp"),
           "assessed_generated": cur.get("generated"),
           "sources": srcs,
           "stale": [s["key"] for s in srcs if not s.get("fresh")],
           "runs": _load(RUNS, [])[-60:],
           "fresh": ({"stamp": fresh.get("stamp"), "assessed_stamp": fresh.get("assessed_stamp"),
                      "summary": fresh.get("summary"), "needs_assessment": fresh.get("needs_assessment"),
                      "n_triggers": len(fresh.get("triggers") or [])} if fresh else None),
           "note": ("Written at the end of every run by tools/enso/ops.py, not live. Data range and last update "
                    "are read from the raw copies with the same readers the panel uses; a source that did not answer "
                    "keeps its last good copy and is marked stale.")}
    _save(OPS, doc)
    return doc


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.path.insert(0, str(HERE))
    cur = _load(ROOT / "latest.json", {})
    fr = _load(ROOT / "fresh.json", None)
    d = build(cur, fr)
    for s in d["sources"]:
        print(f"{'ok ' if s.get('fresh') else 'OLD'} {s['key']:22} {str(s.get('data_from')):12} → {str(s.get('data_to')):12} "
              f"{str(s.get('behind_days') if s.get('behind_days') is not None else ''):>4} {s.get('fetched') or ''} {s.get('error') or ''}")
    print("прогонов в журнале:", len(d["runs"]))
