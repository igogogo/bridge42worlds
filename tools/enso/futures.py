# -*- coding: utf-8 -*-
"""Биржевые котировки продовольствия — недельные и дневные, между месячными таблицами.

Владелец 18.09: «по ценам всё замерло? нужна динамика… добавь недельные котировки по биржевым
товарам». FAO и Pink Sheet выходят раз в месяц; здесь — фьючерсы CBOT/ICE/Bursa по тем же
товарам, каждый день, и недельные закрытия за два года. Источник — открытый график Yahoo
Finance (без ключа и регистрации; непрерывный ближайший контракт). Это НЕ цена FAO и не
Pink Sheet: биржевая котировка ближайшего контракта в своих единицах (центы за бушель, центы
за фунт, доллары за тонну). Панель показывает единицу и не смешивает с месячными рядами.

Что считаем: последняя цена и дата, изменение за неделю и за месяц, процент от закрытия
месяца начала события (тот же onset, что у Pink Sheet), 52-недельные максимум и минимум.
Выход: data/enso/futures.json. Запуск ежедневный в лёгком прогоне.
"""
import json
import sys
import time
import urllib.request
from datetime import datetime, date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
import safeio   # noqa: E402
OUT = ROOT / "data" / "enso" / "futures.json"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UA = {"User-Agent": "Mozilla/5.0 (bridge42worlds-panel; research; bridge42worlds@gmail.com)"}
API = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range={rng}&interval={itv}"

# (ключ, символ, имя, единица, биржа, ключ товара Pink Sheet для связи)
CONTRACTS = [
    ("wheat", "ZW=F", "Wheat, Chicago SRW", "¢/bu", "CBOT", "wheat"),
    ("wheat_hrw", "KE=F", "Wheat, Kansas HRW", "¢/bu", "CBOT", "wheat"),
    ("corn", "ZC=F", "Corn", "¢/bu", "CBOT", "maize"),
    ("soybeans", "ZS=F", "Soybeans", "¢/bu", "CBOT", None),
    ("soybean_oil", "ZL=F", "Soybean oil", "¢/lb", "CBOT", "soybean_oil"),
    ("rice", "ZR=F", "Rough rice", "$/cwt", "CBOT", "rice"),
    ("palm_oil", "CPO=F", "Crude palm oil", "$/t", "Bursa Malaysia", "palm_oil"),
    ("sugar", "SB=F", "Sugar #11", "¢/lb", "ICE", "sugar"),
    ("coffee", "KC=F", "Coffee, Arabica", "¢/lb", "ICE", "coffee_arabica"),
    ("cocoa", "CC=F", "Cocoa", "$/t", "ICE", "cocoa"),
]


def get(url, tries=3):
    last = None
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:                                   # noqa: BLE001
            last = e
            time.sleep(3 + 3 * k)
    raise last


def series(sym, rng, itv):
    """[(дата, закрытие)] по графику Yahoo; пустые свечи пропускаем."""
    d = get(API.format(sym=sym, rng=rng, itv=itv))
    r = ((d.get("chart") or {}).get("result") or [None])[0]
    if not r:
        raise RuntimeError(str((d.get("chart") or {}).get("error"))[:120])
    ts = r.get("timestamp") or []
    closes = (((r.get("indicators") or {}).get("quote") or [{}])[0]).get("close") or []
    out = []
    for t, c in zip(ts, closes):
        if c is None:
            continue
        out.append((date.fromtimestamp(t).isoformat(), round(float(c), 2)))
    return out, r.get("meta") or {}


def onset_month():
    """Месяц начала события — тот же, что у Pink Sheet в latest.json, чтобы проценты были сравнимы."""
    try:
        D = json.loads((ROOT / "data" / "enso" / "latest.json").read_text(encoding="utf-8"))
        items = (((D.get("air") or {}).get("commodities") or {}).get("items") or [])
        return (items[0] or {}).get("onset") if items else None
    except Exception:                                            # noqa: BLE001
        return None


def main():
    t0 = time.time()
    onset = onset_month()
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "onset": onset, "items": [], "errors": [],
           "source": {"label": "Yahoo Finance chart, nearest continuous contract", "page": "https://finance.yahoo.com/commodities/"},
           "note": ("Exchange futures for the same goods as the monthly tables: the nearest contract, daily closes for the last "
                    "three months and weekly closes for two years. Not the FAO or World Bank price: a quote in the exchange's own "
                    "unit, and the contract rolls, so a jump on a roll date is the calendar, not the market.")}
    for key, sym, name, unit, exch, pink in CONTRACTS:
        try:
            wk, meta = series(sym, "2y", "1wk")
            dy, _ = series(sym, "3mo", "1d")
            if not dy:
                raise RuntimeError("no daily closes")
            last_d, last_v = dy[-1]
            def back(days):
                tgt = (datetime.fromisoformat(last_d) - __import__("datetime").timedelta(days=days)).date().isoformat()
                prior = [v for d0, v in dy if d0 <= tgt]
                return prior[-1] if prior else None
            w1, m1 = back(7), back(30)
            # закрытие месяца начала события: последняя недельная точка внутри того месяца
            on_v = None
            if onset:
                inside = [v for d0, v in wk if d0[:7] == onset]
                on_v = inside[-1] if inside else None
            wk_vals = [v for _, v in wk][-52:]
            doc["items"].append({
                "key": key, "symbol": sym, "name": name, "unit": unit, "exchange": exch, "pink_key": pink,
                "contract": (meta.get("shortName") or "").strip(),
                "last": {"date": last_d, "value": last_v},
                "chg_week_pct": round(100 * (last_v / w1 - 1), 1) if w1 else None,
                "chg_month_pct": round(100 * (last_v / m1 - 1), 1) if m1 else None,
                "since_onset_pct": round(100 * (last_v / on_v - 1), 1) if on_v else None,
                "onset_close": on_v,
                "hi_52w": max(wk_vals) if wk_vals else None, "lo_52w": min(wk_vals) if wk_vals else None,
                "weekly": {"dates": [d0 for d0, _ in wk], "values": [v for _, v in wk]},
                "daily": {"dates": [d0 for d0, _ in dy], "values": [v for _, v in dy]},
            })
            print(f"  {name:22s} {last_v:9.2f} {unit:6s} {last_d}  week {doc['items'][-1]['chg_week_pct']:+.1f} %"
                  f"  since onset {doc['items'][-1]['since_onset_pct'] if on_v else '·'}")
            time.sleep(0.6)
        except Exception as e:                                   # noqa: BLE001
            doc["errors"].append(f"{key} ({sym}): {str(e)[:120]}")
            print(f"  {name:22s} ERR {str(e)[:90]}")
    safeio.write_text(OUT, json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
    print(f"futures.json: {len(doc['items'])} contracts, {OUT.stat().st_size // 1024} KB, {time.time() - t0:.0f} s"
          + (f", errors: {len(doc['errors'])}" if doc["errors"] else ""))
    try:
        import ops as OPSLOG
        OPSLOG.record_run("futures", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                          "partial" if doc["errors"] else "ok",
                          note=f"{len(doc['items'])} contracts" + ("; " + "; ".join(doc["errors"]) if doc["errors"] else ""))
    except Exception:                                            # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
