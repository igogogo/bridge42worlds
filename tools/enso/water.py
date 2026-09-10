# -*- coding: utf-8 -*-
"""Запасы воды в водохранилищах: Бразилия и Калифорния, суточно, 2025–2026.

Владелец 10.09: «по объёмам запасов воды в водохранилищах что может подтянуть» и «подробные —
за 25–26 годы». Оба берега Тихого океана держат воду по-своему, и Эль-Ниньо виден в ней
раньше, чем в урожае:

  · БРАЗИЛИЯ — ONS, открытые данные оператора энергосистемы: «запасённая энергия» (EAR)
    по четырём подсистемам и по каждому водохранилищу, суточно, с 2000 года. Единица не
    кубометры, а мегаватт-месяцы: сколько электричества можно выработать запасённой водой.
    Для нас это прямой измеритель запаса — и он же экономика: юг Бразилии при Эль-Ниньо
    заливает, север и северо-восток сушит.
  · КАЛИФОРНИЯ — CDEC, суточный объём десяти крупнейших водохранилищ штата в акрофутах.
    Восточный берег Тихого океана: при сильном событии зима обычно мокрее нормы, и это
    видно по наполнению следующей весной.

Ловушки:
  · EAR это энергия, а не объём воды: у глубокого водохранилища с большой ГЭС тот же
    кубометр «стоит» больше. Сравнивать надо проценты от максимума, они в файле есть;
  · CDEC отдаёт «---» вместо пропуска и держит несколько станций в одном CSV;
  · сезон у обоих полушарий свой: сравниваем день с тем же днём прошлых лет, а не с летом.

    python tools/enso/water.py            обновить 2025–2026
    python tools/enso/water.py --years 2023 2024 2025 2026
"""
import argparse
import csv
import io
import json
import sys
import time
import urllib.request
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "enso" / "water.json"
CACHE = ROOT / "data" / "enso" / "raw" / "water"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UA = {"User-Agent": "bridge42worlds-panel/1.0 (research; bridge42worlds@gmail.com)"}
ONS_SUB = "https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/ear_subsistema_di/EAR_DIARIO_SUBSISTEMA_{y}.csv"
ONS_RES = "https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/ear_reservatorio_di/EAR_DIARIO_RESERVATORIOS_{y}.csv"
CDEC = ("https://cdec.water.ca.gov/dynamicapp/req/CSVDataServlet?Stations={st}&SensorNums=15"
        "&dur_code=D&Start={a}&End={b}")
# Крупнейшие водохранилища Калифорнии и их полная ёмкость, акрофуты (CDEC, «capacity»).
CA = [("SHA", "Shasta", 4552000), ("ORO", "Oroville", 3537577), ("CLE", "Trinity", 2447650),
      ("NML", "New Melones", 2400000), ("SNL", "San Luis", 2041000), ("DNP", "Don Pedro", 2030000),
      ("BER", "Berryessa", 1602000), ("BUL", "New Bullards Bar", 966103), ("FOL", "Folsom", 977000),
      ("PNF", "Pine Flat", 1000000)]
SUBS = {"N": "North", "NE": "Northeast", "S": "South", "SE": "Southeast and Centre-West"}


def get_cached(url, name, timeout=240, max_age_h=20):
    """Тяжёлые годовые файлы качаем не чаще раза в сутки.

    Список водохранилищ Бразилии за год — 4,3 МБ, и он обновляется раз в сутки одной строкой
    на объект. Качать его при каждом запуске значит возить мегабайты ради нескольких новых
    строк (владелец 10.09: «там большой объём скачивается?»). Держим копию в raw/water и
    берём заново, только если она старше max_age_h часов.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / name
    if f.exists() and (time.time() - f.stat().st_mtime) < max_age_h * 3600:
        return f.read_bytes()
    body = get(url, timeout=timeout)
    f.write_bytes(body)
    return body


def get(url, timeout=180, tries=3):
    last = None
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception as e:                                   # noqa: BLE001
            last = e
            time.sleep(4 + 4 * k)
    raise last


def brazil(years):
    """EAR по подсистемам: суточный процент от максимума и абсолют в МВт-мес."""
    out = {k: {"name": v, "dates": [], "pct": [], "mwmonth": []} for k, v in SUBS.items()}
    rows = []
    for y in years:
        try:
            # прошлые годы не меняются — их держим месяц, текущий обновляем раз в сутки
            body = get_cached(ONS_SUB.format(y=y), f"ear_subsistema_{y}.csv", timeout=120,
                              max_age_h=20 if y >= date.today().year else 24 * 30).decode("utf-8", "replace")
        except Exception as e:                                   # noqa: BLE001
            print(f"  brazil {y}: ERR {str(e)[:70]}")
            continue
        rd = csv.DictReader(io.StringIO(body), delimiter=";")
        for r in rd:
            sid = (r.get("id_subsistema") or "").strip()
            if sid not in out:
                continue
            try:
                rows.append((sid, r["ear_data"][:10], float(r["ear_verif_subsistema_percentual"]),
                             float(r["ear_verif_subsistema_mwmes"])))
            except (TypeError, ValueError, KeyError):
                continue
    rows.sort(key=lambda x: (x[0], x[1]))
    for sid, d, pct, mw in rows:
        b = out[sid]
        b["dates"].append(d); b["pct"].append(round(pct, 2)); b["mwmonth"].append(round(mw, 1))
    for sid, b in out.items():
        if b["dates"]:
            b["last"] = {"date": b["dates"][-1], "pct": b["pct"][-1], "mwmonth": b["mwmonth"][-1]}
            same = [(p, dt) for dt, p in zip(b["dates"], b["pct"]) if dt[5:] == b["dates"][-1][5:]]
            if len(same) > 1:
                srt = sorted(same, reverse=True)
                b["last"]["rank_high"] = [dt for _, dt in srt].index(b["dates"][-1]) + 1
                b["last"]["of"] = len(same)
    return out


def brazil_reservoirs(year):
    """Последний доступный день по каждому водохранилищу: процент, бассейн, подсистема."""
    try:
        body = get_cached(ONS_RES.format(y=year), f"ear_reservatorios_{year}.csv").decode("utf-8", "replace")
    except Exception as e:                                       # noqa: BLE001
        print(f"  brazil reservoirs {year}: ERR {str(e)[:70]}")
        return []
    last_by_name, last_day = {}, ""
    for r in csv.DictReader(io.StringIO(body), delimiter=";"):
        d = (r.get("ear_data") or "")[:10]
        if not d:
            continue
        last_day = max(last_day, d)
    for r in csv.DictReader(io.StringIO(body), delimiter=";"):
        if (r.get("ear_data") or "")[:10] != last_day:
            continue
        try:
            pct = float(r["ear_reservatorio_percentual"])
        except (TypeError, ValueError, KeyError):
            continue
        last_by_name[r.get("nom_reservatorio", "").strip()] = {
            "name": r.get("nom_reservatorio", "").strip().title(),
            "basin": (r.get("nom_bacia") or "").strip().title(),
            "subsystem": SUBS.get((r.get("id_subsistema") or "").strip(), (r.get("nom_subsistema") or "").strip()),
            "pct": round(pct, 1),
        }
    items = sorted(last_by_name.values(), key=lambda x: x["pct"])
    return {"date": last_day, "items": items}


def california(a, b):
    """Суточный объём десяти водохранилищ и доля от полной ёмкости."""
    st = ",".join(x[0] for x in CA)
    body = get(CDEC.format(st=st, a=a, b=b), timeout=180).decode("utf-8", "replace")
    cap = {x[0]: x[2] for x in CA}
    names = {x[0]: x[1] for x in CA}
    out = {k: {"name": names[k], "capacity_af": cap[k], "dates": [], "af": [], "pct": []} for k in cap}
    seen_rows = set()
    for r in csv.DictReader(io.StringIO(body)):
        sid = (r.get("STATION_ID") or "").strip()
        if sid not in out:
            continue
        # CDEC отдаёт по створу иногда две строки за сутки (пересчёт): вторую отбрасываем,
        # иначе сумма по десяти водохранилищам подскакивает — 85 % вместо 56 % (10.09)
        key = (sid, (r.get("OBS DATE") or r.get("DATE TIME") or "")[:8])
        if key in seen_rows:
            continue
        seen_rows.add(key)
        v = (r.get("VALUE") or "").strip()
        if not v or v.startswith("-"):
            continue
        try:
            af = float(v)
        except ValueError:
            continue
        d = (r.get("OBS DATE") or r.get("DATE TIME") or "")[:8]
        if len(d) != 8:
            continue
        iso = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        b2 = out[sid]
        b2["dates"].append(iso); b2["af"].append(round(af)); b2["pct"].append(round(100 * af / cap[sid], 1))
    total, seen = {}, {}
    for sid, b2 in out.items():
        if b2["dates"]:
            b2["last"] = {"date": b2["dates"][-1], "af": b2["af"][-1], "pct": b2["pct"][-1]}
        for d, af in zip(b2["dates"], b2["af"]):
            total[d] = total.get(d, 0) + af
            seen[d] = seen.get(d, 0) + 1
    # ИТОГ СЧИТАЕМ ТОЛЬКО ЗА ПОЛНЫЕ ДНИ. За сегодняшнее число отчитываются не все створы, и
    # за сегодняшнее число отчитываются не все створы, и сумма по двум из десяти дала
    # «0,7 % ёмкости» — падение, которого не было (10.09).
    full = [d for d in sorted(total) if seen[d] >= len(cap) - 1]
    cap_all = sum(cap.values())
    tot = {"name": "Ten largest reservoirs together", "capacity_af": cap_all,
           "dates": full, "af": [total[d] for d in full], "partial_days": len(total) - len(full)}
    tot["pct"] = [round(100 * v / cap_all, 1) for v in tot["af"]]
    if tot["dates"]:
        tot["last"] = {"date": tot["dates"][-1], "af": tot["af"][-1], "pct": tot["pct"][-1]}
    return out, tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="*", type=int, default=[date.today().year - 1, date.today().year])
    a = ap.parse_args()
    t0 = time.time()
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "errors": [],
           "sources": [
               {"key": "ons", "label": "ONS Brazil, stored energy (EAR) by subsystem and reservoir, daily",
                "url": ONS_SUB.format(y=a.years[-1]), "page": "https://dados.ons.org.br/dataset/ear-diario-por-subsistema"},
               {"key": "cdec", "label": "California CDEC, daily storage of the ten largest reservoirs",
                "url": CDEC.format(st="SHA", a=f"{a.years[0]}-01-01", b=date.today().isoformat()),
                "page": "https://cdec.water.ca.gov/reportapp/javareports?name=RES"},
           ],
           "note": ("Brazil: stored energy in megawatt-months, the operator's own measure of what the water in the "
                    "reservoirs can generate; percentages are of each subsystem's maximum. California: storage in "
                    "acre-feet against full capacity. Compare a day with the same day of other years, not with "
                    "summer: both sides have their own season.")}
    try:
        doc["brazil"] = brazil(a.years)
        for sid, b in doc["brazil"].items():
            if b.get("last"):
                print(f"  brazil {b['name']:26s} {b['last']['pct']:>6.1f} % of max on {b['last']['date']}"
                      + (f" · rank {b['last'].get('rank_high')} of {b['last'].get('of')} for the date" if b['last'].get('rank_high') else ""))
    except Exception as e:                                       # noqa: BLE001
        doc["errors"].append(f"brazil: {str(e)[:100]}")
    try:
        doc["brazil_reservoirs"] = brazil_reservoirs(a.years[-1])
        it = doc["brazil_reservoirs"].get("items") or []
        if it:
            print(f"  brazil reservoirs {len(it)} on {doc['brazil_reservoirs']['date']}: "
                  f"lowest {it[0]['name']} {it[0]['pct']} %, highest {it[-1]['name']} {it[-1]['pct']} %")
    except Exception as e:                                       # noqa: BLE001
        doc["errors"].append(f"brazil reservoirs: {str(e)[:100]}")
    try:
        res, tot = california(f"{a.years[0]}-01-01", date.today().isoformat())
        doc["california"] = res
        doc["california_total"] = tot
        if tot.get("last"):
            print(f"  california total          {tot['last']['pct']:>6.1f} % of capacity on {tot['last']['date']}")
    except Exception as e:                                       # noqa: BLE001
        doc["errors"].append(f"california: {str(e)[:100]}")
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"water.json: {OUT.stat().st_size // 1024} KB, {time.time() - t0:.0f} s"
          + (f", errors: {len(doc['errors'])}" if doc["errors"] else ""))
    try:
        import ops as OPSLOG
        OPSLOG.record_run("water", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                          "partial" if doc["errors"] else "ok",
                          note=f"brazil {len(doc.get('brazil', {}))} subsystems, california {len(doc.get('california', {}))} reservoirs")
    except Exception:                                            # noqa: BLE001
        pass


if __name__ == "__main__":
    main()
