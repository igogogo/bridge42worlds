# -*- coding: utf-8 -*-
"""Постоянная проверка раскладки панели: обход всех сцен в безоконном браузере.

Владелец 16.09: «сделай такой обход постоянной проверкой». До этого поломки находил он сам,
глазами, и находил поздно: столкновение имён классов 15.09 осыпало карточки пояснений на семи
сценах сразу и прожило сутки, а сцена «Data chain» при окне 1024 показывала четыре столбца по
девяносто пикселей — слова по одному в строку и рваные посередине.

ПОЧЕМУ БЕЗ БРАУЗЕРА ЭТОГО НЕ ПРОВЕРИТЬ. check_ui.py читает исходники и данные и ловит
рассогласования: термин без статьи, файл вне выкладки, вкладку без ветки отрисовки. Всё это —
свойства ТЕКСТА. А «не помещается» — свойство РАСКЛАДКИ: оно зависит от ширины сцены, от длины
соседнего текста (а он приходит с данными и меняется каждый день) и от того, какое правило
победило в каскаде. Ни одно из этих трёх не видно в файле.

ЧТО ДЕЛАЕТ. Поднимает свой файловый сервер на свободном порту, открывает панель в безоконном
Edge (или Chrome) через протокол отладки, вставляет обход layout_sweep.js и прогоняет его на
трёх ширинах: 375 (телефон), 1024 (узкое окно — там сцена между двумя рельсами уже телефонной!)
и 1440 (рабочий стол). На каждой ширине обходятся ВСЕ вкладки со всеми подвкладками. Заодно
собираются ошибки javascript: обход кликает по каждой сцене, и сцена, которая падает, выдаёт
себя здесь, а не у читателя.

РЕЗУЛЬТАТ: data/enso/layout-check.json (его показывает вкладка Ops) и код возврата 1, если
есть замечания. Признанные исключения лежат в layout-accepted.json — каждое с причиной и с
потолком: если таких мест вдруг стало больше потолка, проверка снова заговорит.

    python tools/enso/check_layout.py                          # локальные файлы, три ширины
    python tools/enso/check_layout.py --widths 375             # одна ширина
    python tools/enso/check_layout.py --base https://bridge42worlds.academy   # против прода
    python tools/enso/check_layout.py --keep --quiet           # браузер оставить открытым
"""
import argparse
import functools
import json
import os
import socket
import sys
import threading
import time
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
# Своя запись файлов: повтор при осечке файловой системы и подмена целиком (17.09).
import sys as _sys
import pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
import safeio   # noqa: E402
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))          # page_watch тянет common.py из корня репозитория
# ...а common.py читает свои файлы путями от текущей папки, и ночная обёртка зовёт нас из
# tools/enso. Становимся в корень репозитория: вся работа этого скрипта всё равно о нём.
# Относительный путь у --json после этого считается от корня, а не от места запуска.
os.chdir(ROOT)

OUT = ROOT / "data" / "enso" / "layout-check.json"
SWEEP = HERE / "layout_sweep.js"
ACCEPTED = HERE / "layout-accepted.json"
WIDTHS = (375, 1024, 1440)
PAGE = "/enso.html"


# ------------------------------------------------------------------ свой файловый сервер
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):                                   # без шума в лог проверки
        pass


class Srv(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        """Браузер бросает недокачанные запросы — это норма, а не беда.

        Меняя ширину и переключая сцены, он обрывает уже начатые ответы, и сервер честно
        печатает на каждый такой обрыв полную трассировку. В логе ночного прогона это
        десятки экранов шума вокруг одной строки результата.
        """
        if sys.exc_info()[0] in (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            return
        super().handle_error(request, client_address)


def serve(root):
    """Отдаёт репозиторий с потоками на свободном порту.

    ПОТОКИ ОБЯЗАТЕЛЬНЫ. Панель тянет три десятка json одним Promise.all; однопоточный
    http.server выстраивает их в очередь, и на узкой ширине страница не успевает собраться
    за отпущенное время — проверка объявляет пустую сцену там, где сцена просто ждала файл.
    Это уже ловили на проверке сайта (см. память про замер на 375 px).

    Свой сервер, а не tools/dev_server.py: тому нужен индекс статей и фиксированный порт 8420,
    который обычно занят живой отладкой. Панели ручки облака не нужны — только файлы.
    """
    h = functools.partial(Quiet, directory=str(root))
    srv = Srv(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ------------------------------------------------------------------ протокол отладки
class Session:
    """Одна вкладка браузера. Ошибки javascript копятся по дороге, пока ждём ответы."""

    def __init__(self, tab, timeout=180):
        import websocket
        # suppress_origin обязателен: протокол отладки отвергает соединение с заголовком Origin
        self.ws = websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=timeout,
                                              suppress_origin=True)
        self._id = 0
        self.errors = []

    def _note(self, msg):
        m = msg.get("method")
        if m == "Runtime.exceptionThrown":
            d = msg["params"]["exceptionDetails"]
            t = (d.get("exception", {}).get("description") or d.get("text") or "ошибка без текста")
            self.errors.append(t.split("\n")[0][:200])
        elif m == "Runtime.consoleAPICalled" and msg["params"].get("type") == "error":
            parts = [str(a.get("value", a.get("description", ""))) for a in msg["params"].get("args", [])]
            self.errors.append(" ".join(parts)[:200])

    def call(self, method, params=None, timeout=180):
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        end = time.time() + timeout
        while True:
            left = end - time.time()
            if left <= 0:
                raise TimeoutError("нет ответа на " + method)
            self.ws.settimeout(max(0.5, left))
            msg = json.loads(self.ws.recv())
            self._note(msg)
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError("%s: %s" % (method, str(msg["error"])[:200]))
                return msg.get("result", {})

    def eval(self, expr, await_promise=False, timeout=180):
        r = self.call("Runtime.evaluate",
                      {"expression": expr, "returnByValue": True, "awaitPromise": await_promise},
                      timeout=timeout)
        ex = r.get("exceptionDetails")
        if ex:
            t = (ex.get("exception", {}) or {}).get("description") or ex.get("text") or "?"
            raise RuntimeError(str(t).split("\n")[0][:200])
        return (r.get("result", {}) or {}).get("value")

    def close(self):
        try:
            self.ws.close()
        except Exception:                                        # noqa: BLE001
            pass


def wait_panel(s, seconds=40):
    """Панель готова, когда есть вкладки и сцена. Раньше мерить нечего."""
    end = time.time() + seconds
    while time.time() < end:
        try:
            n = s.eval("document.querySelectorAll('.tab').length", timeout=20)
            body = s.eval("!!document.querySelector('.stage-body')", timeout=20)
            if (n or 0) >= 8 and body:
                return True
        except Exception:                                        # noqa: BLE001
            pass
        time.sleep(0.5)
    return False


# ------------------------------------------------------------------ признанные исключения
def load_accepted():
    try:
        d = json.loads(ACCEPTED.read_text(encoding="utf-8"))
        return d.get("rules") or []
    except Exception:                                            # noqa: BLE001
        return []


def split_accepted(findings, rules):
    """Делит находки на «признанные» и «новые».

    Правило узнаёт находку по роду, месту и (необязательно) куску текста и названию сцены.
    У каждого правила есть ПОТОЛОК: сколько таких мест мы согласились терпеть. Всё сверх
    потолка идёт в новые — иначе одно признанное исключение однажды прикроет собой десяток
    настоящих поломок в том же месте.
    """
    left, taken = [], []
    used = {}
    for f in findings:
        hit = None
        for i, r in enumerate(rules):
            if r.get("t") and r["t"] != f.get("t"):
                continue
            if r.get("p") and not str(f.get("p", "")).startswith(r["p"]):
                continue
            if r.get("scene") and not str(f.get("scene", "")).startswith(r["scene"]):
                continue
            if r.get("x") and r["x"] not in str(f.get("x", "")):
                continue
            hit = i
            break
        if hit is None:
            left.append(f)
            continue
        used[hit] = used.get(hit, 0) + 1
        if used[hit] > int(rules[hit].get("max", 1)):
            g = dict(f)
            g["over_accepted"] = rules[hit].get("why", "")
            left.append(g)
        else:
            taken.append(f)
    return left, taken


# ------------------------------------------------------------------ сам обход
def kpi_report(seen):
    """Сводка по реестру показателей: где расходятся числа и чего не видно вовсе.

    ОДИН КЛЮЧ — ОДНО ЧИСЛО. Панель показывает журнальный ряд в нескольких местах, и каждое
    берёт значение само: лента KPI из журнала, карточка сцены из своего поля, обзор из третьего.
    Разойтись они могут тихо — как 15.09 разошлись два суточных Niño 3.4 (2.71 и 2.90, разные
    климатологии) и как 2.715 печаталось то 2.71, то 2.72. Расхождение не всегда ошибка, но
    всегда вопрос, на который должен быть ответ.

    ЧЕГО НЕ ВИДНО. Ряд, который считается каждый прогон и нигде не показан, — это либо забытая
    работа, либо мёртвый код. Сегодня таких нашлось семнадцать из пятидесяти шести.
    """
    reg = {}
    try:
        j = json.loads((ROOT / "data" / "enso" / "journal.json").read_text(encoding="utf-8"))
        for k, v in (j.get("metrics") or {}).items():
            reg[k] = {"title": v.get("title") or k, "digits": v.get("digits"),
                      "last": ((v.get("entries") or [{}])[-1] or {}).get("v")}
    except Exception:                                            # noqa: BLE001
        pass
    by = {}
    for x in seen:
        by.setdefault(x.get("k"), []).append(x)
    out_of_sync, rounding, shown = [], [], sorted(by.keys())
    for k, rows in sorted(by.items()):
        vals = {}
        for r in rows:
            if r.get("n") is None:
                continue
            vals.setdefault(round(float(r["n"]), 4), []).append(r.get("scene"))
        if len(vals) > 1:
            items = sorted(vals.items())
            spread = max(v for v, _ in items) - min(v for v, _ in items)
            # ОКРУГЛЕНИЕ — НЕ РАСХОЖДЕНИЕ. Одно и то же число можно честно показать с разной
            # точностью: 33.25 в ленте и 33.2 на своей сцене — это одно значение, а не два.
            # Судим по САМОЙ ГРУБОЙ из показанных точностей: округляем к ней все значения
            # ключа, и если они сошлись в одно — спор был о последнем знаке, а не о числе.
            def _dec(r):
                s = str(r.get("raw") or "")
                return len(s.split(".")[1]) if "." in s else 0
            nd = min((_dec(r) for r in rows if r.get("n") is not None), default=0)
            same = {round(float(r["n"]), nd) for r in rows if r.get("n") is not None}
            eps = spread + 1.0 if len(same) == 1 else 0.0
            rec = {"key": k, "title": (reg.get(k) or {}).get("title", k),
                   "spread": round(spread, 4),
                   "values": [{"v": v, "scenes": sorted(set(sc))[:4], "n": len(sc)} for v, sc in items][:6]}
            if eps and spread <= eps:
                rec["rounding"] = True
                rounding.append(rec)
            else:
                out_of_sync.append(rec)
    # Ряды риска — не «потерянные показатели»: их заводит сам риск, и виден такой ряд ровно
    # тогда, когда его риск стоит на доске. Снялся риск — ряд остаётся в журнале историей.
    not_shown = [{"key": k, "title": reg[k]["title"]} for k in sorted(reg)
                 if k not in by and not k.startswith("risk:")]
    ghost = [k for k in shown if reg and k not in reg]
    return {"registry": len(reg), "shown": len(shown), "out_of_sync": out_of_sync,
            "rounding": rounding,
            "not_shown": not_shown, "not_in_registry": sorted(ghost),
            "note": ("Реестр показателей — журнал значений. Здесь сведено то, что панель реально "
                     "показала на всех обойдённых сценах: один ключ должен давать одно число везде.")}


def run(base, widths, keep, quiet):
    import page_watch                                            # оснастка браузера уже написана

    exe = page_watch.find_browser()
    if not exe:
        return {"status": "skipped", "why": "на машине нет ни Edge, ни Chrome"}, 2

    sweep_js = SWEEP.read_text(encoding="utf-8")
    br = page_watch.Browser(exe, keep=keep)
    findings, scenes, js_errors, kpis = [], 0, [], []
    try:
        tab = br.open_tab(base + PAGE)
        s = Session(tab)
        s.call("Runtime.enable")
        s.call("Page.enable")
        s.call("Page.navigate", {"url": base + PAGE})
        if not wait_panel(s):
            return {"status": "failed", "why": "панель не собралась за 40 секунд"}, 2
        for w in widths:
            s.call("Emulation.setDeviceMetricsOverride",
                   {"width": w, "height": 900, "deviceScaleFactor": 1, "mobile": w < 768})
            # панель перерисовывается по событию размера с задержкой 150 мс; ждём с запасом
            time.sleep(1.2)
            s.eval(sweep_js)                                     # обход вставляем заново на каждую ширину
            r = s.eval("B42Layout.sweep()", await_promise=True, timeout=600) or {}
            got = r.get("findings") or []
            scenes += int(r.get("scenes") or 0)
            for f in got:
                f["width"] = w
                findings.append(f)
            for x in (r.get("kpis") or []):
                x["width"] = w
                kpis.append(x)
            if not quiet:
                print("  ширина %d: сцен %d, замечаний %d" % (w, r.get("scenes") or 0, len(got)))
        js_errors = sorted(set(s.errors))
        s.close()
    finally:
        br.close()

    for e in js_errors:
        findings.append({"t": "js", "p": "console", "x": e, "scene": "любая", "width": 0})

    return {"status": "ok", "scenes": scenes, "findings": findings, "kpi": kpi_report(kpis)}, 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", help="адрес панели; по умолчанию свой сервер по локальным файлам")
    ap.add_argument("--widths", default=",".join(str(w) for w in WIDTHS))
    ap.add_argument("--keep", action="store_true", help="не закрывать браузер (для разбора)")
    ap.add_argument("--quiet", action="store_true", help="молчать, если всё хорошо")
    ap.add_argument("--json", default=str(OUT), help="куда писать отчёт")
    a = ap.parse_args()

    widths = [int(x) for x in str(a.widths).split(",") if x.strip()]
    srv = None
    base = a.base
    if not base:
        srv, base = serve(ROOT)
    t0 = time.time()
    try:
        res, code = run(base.rstrip("/"), widths, a.keep, a.quiet)
    except Exception as e:                                       # noqa: BLE001
        res, code = {"status": "failed", "why": "%s: %s" % (type(e).__name__, str(e)[:200])}, 2
    finally:
        if srv:
            srv.shutdown()

    rules = load_accepted()
    raw = res.get("findings") or []
    new, taken = split_accepted(raw, rules)
    doc = {
        "built": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "secs": int(round(time.time() - t0)),
        "base": "local files" if not a.base else a.base,
        "widths": widths,
        "scenes_checked": res.get("scenes", 0),
        "status": res.get("status"),
        "why": res.get("why"),
        "n_findings": len(new),
        "n_accepted": len(taken),
        "findings": new[:80],
        "kpi": res.get("kpi") or {},
        "note": ("Обход всех сцен панели в безоконном браузере на каждой ширине: где текст не "
                 "помещается, где обрезан без многоточия, где налезает на соседа, где сцена "
                 "отрисовалась пустой и где упал javascript. Признанные исключения перечислены "
                 "в tools/enso/layout-accepted.json, каждое с причиной и потолком. "
                 "Запуск: python tools/enso/check_layout.py"),
    }
    try:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        safeio.write_text(Path(a.json), json.dumps(doc, ensure_ascii=False, indent=1))
    except OSError as e:
        print("отчёт не записан: %s" % e)

    # строка в журнал прогонов — чтобы проверка была видна на вкладке Ops, как всё остальное
    try:
        import ops
        st = "ok" if (res.get("status") == "ok" and not new) else (
            "failed" if res.get("status") != "ok" else "findings")
        r = ops.Run("layout", note="%d scenes on %s" % (doc["scenes_checked"],
                                                        ", ".join(str(w) for w in widths)))
        r.t0 = time.time() - doc["secs"]
        if res.get("why"):
            r.error(res["why"])
        for f in new[:5]:
            r.error("%s · %s · %s" % (f.get("t"), f.get("scene"), str(f.get("x"))[:60]))
        r.finish(st, findings=len(new), accepted=len(taken))
    except Exception as e:                                       # noqa: BLE001
        print("журнал прогонов не записан: %s" % str(e)[:120])

    if res.get("status") != "ok":
        print("⛔ обход не состоялся: %s" % res.get("why"))
        return 2
    if not a.quiet or new:
        print("check_layout: %d замечаний, %d признанных, сцен %d, %d с"
              % (len(new), len(taken), doc["scenes_checked"], doc["secs"]))
    kp = doc.get("kpi") or {}
    if kp and not a.quiet:
        print("реестр показателей: %d рядов, показано %d, расходятся %d (плюс %d на округлении), не показаны %d"
              % (kp.get("registry", 0), kp.get("shown", 0), len(kp.get("out_of_sync") or []),
                 len(kp.get("rounding") or []), len(kp.get("not_shown") or [])))
        for x in (kp.get("out_of_sync") or [])[:10]:
            print("  ~~ %-18s %s: %s" % (x["key"], x["title"][:30],
                                         " | ".join("%s на %s" % (v["v"], ", ".join(v["scenes"])[:40]) for v in x["values"])))
    for f in new[:40]:
        print("  !! %-9s %4s  %-28s  %s" % (f.get("t"), f.get("width"), str(f.get("scene"))[:28],
                                            str(f.get("x"))[:70]))
        print("       %s" % f.get("p"))
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main())
