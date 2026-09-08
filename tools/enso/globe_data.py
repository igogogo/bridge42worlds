# -*- coding: utf-8 -*-
"""Данные для шара (пилот, владелец 08.09: «переключатель на каждое наше представление, чтобы на шаре
видеть, где уместно»). Один файл data/enso/globe.json, читается панелью по требованию:

  • sst: аномалия OISST v2.1 (NRT, против 1971–2000) на 1° сетке за последний день, 60°S–60°N;
  • boxes: зоны Niño с недельной аномалией NOAA, наши сухопутные боксы с 30-дневной аномалией
    воздуха и дождём в % от нормы, боксы спутника (Niño 3.4, тёплый бассейн) с конвекцией и G_clear;
  • moorings: буи TAO на экваторе с самой тёплой аномалией по глубине;
  • meta: даты и источники.
Всё берётся из уже посчитанных файлов, сеть нужна только для сетки OISST (~1 МБ). Запуск:
python globe_data.py (в обёртке после regions_daily/precip/radiance_take).
"""
import json
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oisst as OI                                              # noqa: E402
import spectral as SPX                                          # noqa: E402
import subsurface as SB                                         # noqa: E402

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"
OUT = ROOT / "globe.json"
STRIDE = 4                                                      # 0.25° × 4 = 1°


def sst_grid():
    """Аномалия OISST за последний день NRT, 1°, 60°S–60°N → {lat0, lon0, step, nlat, nlon, rows}."""
    import netCDF4
    q = (f"{OI.E}{OI.NRT}.nc?anom[(last):1:(last)][(0.0)][(-60):{STRIDE}:(60)][(-180):{STRIDE}:(179.875)]")
    req = urllib.request.Request(q, headers={"User-Agent": OI.UA})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = r.read()
    ds = netCDF4.Dataset("inmem.nc", memory=data)
    try:
        t = ds["time"]; day = netCDF4.num2date(t[:], t.units)[0].strftime("%Y-%m-%d")
        lats = np.array(ds["latitude"][:], float); lons = np.array(ds["longitude"][:], float)
        a = np.ma.filled(np.ma.masked_invalid(ds["anom"][:]), np.nan).astype(float)[0, 0]   # (lat, lon)
    finally:
        ds.close()
    rows = [[None if not np.isfinite(v) else round(float(v), 1) for v in row] for row in a]
    return {"date": day, "lat0": float(lats[0]), "lon0": float(lons[0]), "step": float(lats[1] - lats[0]) if len(lats) > 1 else 1.0,
            "nlat": len(lats), "nlon": len(lons), "rows": rows,
            "source": "NOAA OISST v2.1 NRT via ERDDAP, anomaly against 1971–2000, 1° subsample"}


def boxes(D, RD, PR, RA):
    out = []
    nw = (D.get("noaa") or {}).get("latest") or {}
    for key, b, kk in (("nino4", OI.BOXES["nino4"], "n4a"), ("nino34", OI.BOXES["nino34"], "n34a"),
                       ("nino3", OI.BOXES["nino3"], "n3a"), ("nino12", OI.BOXES["nino12"], "n12a")):
        lat = b["lat"]; lons = b["lon"]
        lon0 = lons[0][0]; lon1 = lons[-1][1]
        if len(lons) > 1:                                        # Niño 4 через антимеридиан: в 0..360
            lon0, lon1 = 160.0, 210.0
        out.append({"id": key, "kind": "nino", "label": b["title"], "lat": [lat[0], lat[1]], "lon": [lon0, lon1],
                    "value": nw.get(kk), "unit": "°C", "text": f"weekly anomaly {nw.get(kk):+.1f} °C" if nw.get(kk) is not None else "", "date": (D.get("noaa") or {}).get("date")})
    for key, label, box, rid in SPX.REGIONS:
        w = (RD.get("series") or {}).get("land_" + key) or {}
        p = (PR.get("regions") or {}).get("land_" + key) or {}
        lv = (w.get("level30") or {}).get("anom"); rp = ((p.get("sum30") or {}).get("pct_of_normal"))
        out.append({"id": "land_" + key, "kind": "land", "label": label.split(",")[0], "lat": [box[0], box[1]], "lon": [box[2], box[3]],
                    "value": lv, "unit": "°C", "rain_pct": rp,
                    "text": (f"air {lv:+.1f} °C over 30 days" if lv is not None else "") + (f"; rain {rp} % of normal" if rp is not None else ""),
                    "date": w.get("last_date")})
    cr = ((RA.get("sources") or {}).get("n21_cris") or {})
    cur = str(((RA.get("window") or {}).get("current")) or 2026)
    def last14(d):
        ks = sorted(int(k) for k in (d or {}).keys())[-14:]
        v = [d[str(k)] for k in ks if d.get(str(k)) is not None]
        return float(np.mean(v)) if v else None
    for key, label, lat, lon in (("nino34", "Satellite: Niño 3.4 box", (-5, 5), (-170, -120)), ("warmpool", "Satellite: warm pool", (-5, 5), (130, 170))):
        conv = last14(((cr.get("series") or {}).get(key + "_A") or {}).get("conv_frac", {}).get(cur))
        gcl = last14(((cr.get("greenhouse_clear") or {}).get(key + "_A") or {}).get(cur))
        out.append({"id": "rad_" + key, "kind": "radiance", "label": label, "lat": list(lat), "lon": list(lon),
                    "value": conv * 100 if conv is not None else None, "unit": "% deep convection",
                    "text": (f"deep convection {conv*100:.1f} % of footprints" if conv is not None else "") + (f"; G_clear {gcl:.1f} K" if gcl is not None else "") + " (last 14 days, day node)",
                    "date": str(RA.get("updated") or "")[:10]})
    return out


def moorings(D):
    out = []
    for st in ((D.get("subsurface") or {}).get("tao") or {}).get("stations") or []:
        lon = st.get("lon"); w = st.get("warmest_anom") or {}
        if lon is None:
            continue
        lon180 = lon - 360 if lon > 180 else lon
        out.append({"id": st.get("name"), "lat": 0.0, "lon": lon180, "label": st.get("label") or st.get("name"),
                    "value": w.get("value"), "depth": w.get("depth"), "date": st.get("last_date"),
                    "text": f"warmest layer {w.get('value'):+.1f} °C at {w.get('depth')} m" if w.get("value") is not None else "no live profile"})
    return out


def build(verbose=True):
    t0 = time.time()
    D = json.load(open(ROOT / "latest.json", encoding="utf-8"))
    RD = json.load(open(ROOT / "regions-daily.json", encoding="utf-8")) if (ROOT / "regions-daily.json").exists() else {}
    PR = json.load(open(ROOT / "precip.json", encoding="utf-8")) if (ROOT / "precip.json").exists() else {}
    RA = json.load(open(ROOT / "radiance.json", encoding="utf-8")) if (ROOT / "radiance.json").exists() else {}
    err = None
    try:
        grid = sst_grid()
    except Exception as e:                                       # noqa: BLE001
        err = f"sst grid: {str(e)[:120]}"
        grid = json.load(open(OUT, encoding="utf-8")).get("sst") if OUT.exists() else None
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "sst": grid, "boxes": boxes(D, RD, PR, RA), "moorings": moorings(D),
           "coast": "data/enso/coast.json",
           "note": ("Pilot globe: the latest day of OISST anomaly on a 1° grid (against 1971–2000, the dataset's own baseline, "
                    "not our 1991–2020), the Niño boxes with the NOAA weekly anomaly, our land boxes with the 30-day air anomaly "
                    "and rain against normal, the satellite boxes with deep convection, and the TAO moorings with the warmest layer. "
                    "Everything shown is already on the panel; the globe only puts it in one place."),
           "errors": [err] if err else [], "secs": int(time.time() - t0)}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    if verbose:
        print(f"globe.json: sst {'ok ' + grid['date'] if grid else 'none'}, boxes {len(doc['boxes'])}, moorings {len(doc['moorings'])}, {OUT.stat().st_size // 1024} KB, {doc['secs']} s" + (f"; {err}" if err else ""))
    try:
        import ops as OPSLOG
        OPSLOG.record_run("globe", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ok" if not err else "partial", note=err or f"sst {grid['date'] if grid else '-'}")
    except Exception:                                            # noqa: BLE001
        pass
    return doc


if __name__ == "__main__":
    build()
