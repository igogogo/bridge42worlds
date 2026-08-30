"""Сторож живой страницы: открывает главную на всех языках и считает карточки.

Зачем именно браузер. 14 августа главная не показала ни одной статьи на пяти языках,
отдаваясь при этом с кодом 200. Ни один наш сторож этого не заметил: они смотрят
свежесть данных и доступность файлов, а лента рисуется javascript'ом уже в браузере.
Проверка без браузера тут бесполезна по устройству — HTML главной одинаков и когда
статей 3988, и когда их ноль.

Что проверяем на каждом языке:
  • страница открылась (код ответа);
  • в ленте есть карточки (article.article-card) — их считаем;
  • не было ошибок javascript. Это важнее счётчика: 14 августа лента рухнула на
    вызове функции esc(), которой в файле не было, и первая же карточка обрушила
    отрисовку целиком. Ошибка в консоли была ОДНА, и она объясняла всё.

Чем открываем. Microsoft Edge в безоконном режиме через его же протокол отладки —
он есть на машине по умолчанию, отдельный драйвер не нужен, лишних зависимостей ноль
(websocket-client уже стоит). Chrome, если он появится, подойдёт тем же кодом.

    python tools/page_watch.py                     # прод, все языки
    python tools/page_watch.py --base http://localhost:8420   # локальная сборка
    python tools/page_watch.py --lang ru --keep    # один язык, окно не закрывать
"""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
from common import ALL_LANGS  # noqa: E402
LANGS = ALL_LANGS   # список языков один на проект: config.json через common.ALL_LANGS
BASE = "https://bridge42worlds.academy"
CARD_SELECTOR = "article.article-card"
# Меньше этого числа карточек на главной — беда, а не «мало статей»: лента показывает
# первый экран из latest-индекса, там всегда десятки записей.
MIN_CARDS = 5
BROWSERS = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)


def find_browser():
    for p in BROWSERS:
        if Path(p).exists():
            return p
    return shutil.which("msedge") or shutil.which("chrome")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Browser:
    """Безоконный браузер + протокол отладки. Своя папка профиля на каждый запуск:
    общий профиль занят живым браузером владельца, и вторая копия просто не стартует."""

    def __init__(self, exe, keep=False):
        self.port = free_port()
        self.profile = tempfile.mkdtemp(prefix="b42-watch-")
        self.keep = keep
        self.proc = subprocess.Popen(
            [exe, "--headless=new", f"--remote-debugging-port={self.port}",
             f"--user-data-dir={self.profile}", "--no-first-run", "--no-default-browser-check",
             "--disable-gpu", "--disable-extensions", "--window-size=1280,900", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.base = f"http://127.0.0.1:{self.port}"
        self._wait_ready()

    def _wait_ready(self, timeout=30):
        end = time.time() + timeout
        while time.time() < end:
            try:
                with urllib.request.urlopen(f"{self.base}/json/version", timeout=2):
                    return
            except Exception:
                time.sleep(0.3)
        raise RuntimeError("браузер не поднял протокол отладки за 30 секунд")

    def open_tab(self, url):
        req = urllib.request.Request(f"{self.base}/json/new?{url}", method="PUT")
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())

    def close(self):
        if self.keep:
            print(f"браузер оставлен: {self.base}")
            return
        try:
            self.proc.terminate()
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()
        shutil.rmtree(self.profile, ignore_errors=True)


def look(browser, url, wait=12):
    """Открывает адрес, ждёт отрисовки, возвращает (карточек, ошибки, код ответа)."""
    import websocket

    tab = browser.open_tab(url)
    # suppress_origin обязателен: библиотека по умолчанию шлёт заголовок Origin, а протокол
    # отладки браузера отвергает такое соединение с 403 — это его защита от того, чтобы
    # страница из интернета не управляла браузером через случайно открытый порт.
    ws = websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=wait + 20,
                                     suppress_origin=True)
    errors, status = [], None
    n = 0
    try:
        def send(method, params=None, _id=[0]):
            _id[0] += 1
            ws.send(json.dumps({"id": _id[0], "method": method, "params": params or {}}))
            return _id[0]

        send("Runtime.enable")
        send("Page.enable")
        send("Network.enable")
        nav_id = send("Page.navigate", {"url": url})

        # Слушаем до тех пор, пока страница не догрузится: ошибки javascript приходят
        # событиями, и ловить их надо ЗДЕСЬ, а не спрашивать потом — к моменту опроса
        # консоль уже пуста.
        end = time.time() + wait
        loaded = False
        while time.time() < end:
            ws.settimeout(max(0.5, end - time.time()))
            try:
                msg = json.loads(ws.recv())
            except Exception:
                break
            m = msg.get("method")
            if m == "Runtime.exceptionThrown":
                d = msg["params"]["exceptionDetails"]
                text = (d.get("exception", {}).get("description")
                        or d.get("text") or "ошибка без текста")
                errors.append(text.split("\n")[0][:200])
            elif m == "Runtime.consoleAPICalled" and msg["params"].get("type") == "error":
                parts = [str(a.get("value", a.get("description", "")))
                         for a in msg["params"].get("args", [])]
                errors.append(" ".join(parts)[:200])
            elif m == "Network.responseReceived":
                r = msg["params"]["response"]
                if status is None and r.get("url", "").rstrip("/") == url.rstrip("/"):
                    status = r.get("status")
            elif m == "Page.loadEventFired":
                loaded = True
                # Лента рисуется ПОСЛЕ загрузки: latest-индекс тянется отдельным запросом.
                # Даём ему секунду и идём считать — если не успел, посчитаем ещё раз ниже.
                end = min(end, time.time() + 3)
            elif msg.get("id") == nav_id and msg.get("result", {}).get("errorText"):
                errors.append(f"навигация не удалась: {msg['result']['errorText']}")

        # Считаем карточки, повторяя попытку: медленная сеть — не повод объявлять тревогу.
        for _ in range(6):
            cid = send("Runtime.evaluate", {
                "expression": f"document.querySelectorAll('{CARD_SELECTOR}').length",
                "returnByValue": True})
            ws.settimeout(10)
            while True:
                msg = json.loads(ws.recv())
                if msg.get("id") == cid:
                    n = int((msg.get("result", {}).get("result", {}) or {}).get("value") or 0)
                    break
            if n >= MIN_CARDS:
                break
            time.sleep(1)
        _ = loaded
    finally:
        try:
            ws.close()
        except Exception:
            pass
    return n, errors, status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=os.environ.get("B42_WATCH_BASE", BASE))
    ap.add_argument("--lang", help="проверить только один язык")
    ap.add_argument("--keep", action="store_true", help="не закрывать браузер (для разбора)")
    ap.add_argument("--quiet", action="store_true", help="молчать, если всё хорошо")
    # Проверка сторожа не должна будить команду. Своя же тревога, отправленная при отладке,
    # учит не верить каналу — а канал у нас единственный способ узнать о настоящей беде.
    ap.add_argument("--no-alert", action="store_true", help="не писать в канал (для проверок)")
    a = ap.parse_args()

    exe = find_browser()
    if not exe:
        print("⛔ не нашёл ни Edge, ни Chrome — проверять нечем.")
        return 2

    langs = [a.lang] if a.lang else list(LANGS)
    br = Browser(exe, keep=a.keep)
    bad = []
    try:
        for lang in langs:
            url = f"{a.base}/lang/{lang}/index.html"
            try:
                n, errors, status = look(br, url)
            except Exception as e:                    # noqa: BLE001
                bad.append(f"{lang}: проверка сорвалась — {type(e).__name__}: {str(e)[:120]}")
                print(f"❌ {lang}: {type(e).__name__} {str(e)[:120]}")
                continue
            ok = n >= MIN_CARDS and not errors
            mark = "✅" if ok else "❌"
            print(f"{mark} {lang}: карточек {n}" + (f", код {status}" if status else "")
                  + (f", ошибок js {len(errors)}" if errors else ""))
            for e in errors[:3]:
                print(f"     {e}")
            if n < MIN_CARDS:
                bad.append(f"{lang}: карточек {n} (код {status or '?'})")
            if errors:
                bad.append(f"{lang}: ошибка js — {errors[0]}")
    finally:
        br.close()

    if bad:
        # В канал уходит ПРИЧИНА, а не «страница сломалась»: 14 августа причина была одна
        # строка в консоли, и по ней чинилось за минуту.
        text = "🚨 <b>Главная не показывает статьи</b>\n" + "\n".join(f"· {b}" for b in bad)
        if a.no_alert:
            print("\n(в канал не пишу: --no-alert)")
            return 1
        try:
            sys.path.insert(0, str(ROOT / "tools"))
            subprocess.run([sys.executable, str(ROOT / "tools" / "status_tg.py"), text],
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=60)
        except Exception as e:                        # noqa: BLE001
            print(f"(в канал не ушло: {e})")
        return 1
    if not a.quiet:
        print(f"\nвсе {len(langs)} языков показывают ленту.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
