"""Проверка облачного поиска концом-в-конец: через настоящую ручку, а не через базу.

Запросы лежат в отдельном JSON и читаются файлом. Так сделано намеренно: арабские
диапазоны и слова, переданные скрипту через оболочку, переставляются, и проверка
начинает врать (2026-08-06 показала ровный ноль по арабскому — сломан был тест, а не
поиск). Правило оттуда же: файл, а не командная строка; импорт, а не копия функции.
"""
import json, sys, time, urllib.parse, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = sys.argv[1] if len(sys.argv) > 1 else \
    "https://bridge42worlds-dev.bridge42worlds-dev.workers.dev"
# Cloudflare режет User-Agent «Python-urllib» на краю (ошибка 1010) — это защита
# площадки, а не наш код.
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) b42-selfcheck"}
BUST = sys.argv[2] if len(sys.argv) > 2 else ""


def ask(path, params):
    # Лишний параметр меняет АДРЕС запроса и уводит от кэша края. Он нужен именно проверке:
    # ответ, посчитанный до починки, живёт в кэше час и переживает выкладку, поэтому без
    # этого проверка показывает не сегодняшний код, а вчерашний. Ручка параметр игнорирует.
    if BUST:
        params = dict(params, _=BUST)
    url = f"{BASE}{path}?" + urllib.parse.urlencode(params)
    t = time.time()
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
        return json.loads(r.read().decode()), (time.time() - t) * 1000


def main():
    cases = json.loads((HERE / "search_cases.json").read_text(encoding="utf-8"))
    bad = 0
    for c in cases:
        try:
            d, ms = ask("/api/search", {"q": c["q"], "lang": c["lang"],
                                        "version": c.get("version", "advanced")})
        except Exception as e:
            print(f"❌ {c['lang']} «{c['q']}» — {type(e).__name__}: {str(e)[:70]}")
            bad += 1
            continue
        res = d.get("results", [])
        ok = len(res) >= c.get("min", 1)
        # Проверяем не «ответило», а что нашлось ожидаемое: иначе зелёный прогон
        # означал бы только, что ручка жива.
        want = c.get("expect")
        hit = (not want) or any(want.lower() in (r.get("title") or "").lower() for r in res)
        mark = "✅" if (ok and hit) else "❌"
        if not (ok and hit):
            bad += 1
        print(f"{mark} {c['lang']} «{c['q'][:24]:24}» слов={d.get('words')} "
              f"смысл={d.get('semantic')} всего={len(res):2} {ms:5.0f} мс"
              + (f" | ждали «{want}»" if want and not hit else "")
              + (f" | {res[0]['title'][:44]}" if res else ""))
    print(f"\nитог: {len(cases) - bad} из {len(cases)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
