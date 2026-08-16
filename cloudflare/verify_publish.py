"""Проверка после выкладки: то ли лежит в облаке, что мы туда положили.

Зачем. 14 августа обрезанный индекс отдавался с кодом 200 и молчал: ни выкладка, ни
сторож, ни браузер не сказали ни слова — просто лента была пустой. Проверять «ответил ли
сервер» бессмысленно, он отвечал. Проверять надо СОДЕРЖИМОЕ: разбирается ли файл и
столько ли в нём записей, сколько у нас локально.

Отдельно важно: у обрезанного файла в манифесте остаётся отпечаток ЦЕЛОГО файла (md5
снимали до заливки, а уехал он уже переписанным). Из-за этого дельта считает его залитым
и не трогает — сам бы он не починился никогда, 14 августа индексы перезаливали руками.
Поэтому есть --fix: он вычёркивает расхождения из манифеста, и следующая выкладка
заливает их заново. По умолчанию проверка НИЧЕГО не меняет.

Два исхода различаются намеренно:
  • «не разбирается» или «пусто» — авария, тревога в канал;
  • «в облаке меньше, чем локально» — норма между генерацией и выкладкой. Тревожить
    этим канал значит приучить его не читать, а это дороже любой поломки.

    python cloudflare/verify_publish.py             # после выкладки, все языки
    python cloudflare/verify_publish.py --quiet     # молчать, когда всё сходится
    python cloudflare/verify_publish.py --fix       # + вычеркнуть расхождения из манифеста
"""
import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(os.environ.get("B42_DATA_ROOT") or Path(__file__).resolve().parent.parent)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
MANIFEST = Path(__file__).resolve().parent / ".r2-manifest.json"
SITE = os.environ.get("B42_SITE_URL", "https://bridge42worlds.academy")
LANGS = ("ru", "en", "es", "ar", "fr")
# Что именно сверяем. Не «все файлы» — их сто тридцать тысяч, и большинство из них
# страницы, чья поломка видна сторожем главной. Здесь — файлы, от которых зависит
# ЛЕНТА и поиск: если рвётся любой из них, сайт выглядит пустым.
FILES = ([f"lang/{l}/{n}" for l in LANGS
          for n in ("articles-index.json", "articles-index-simple.json",
                    "articles-index-advanced.json", "articles-latest.json")]
         + ["data/knowledge-graph.json"])
UA = {"User-Agent": "b42-verify-publish"}


def count_of(obj):
    """Сколько записей в файле. Индексы — список, граф — словарь с узлами."""
    if isinstance(obj, list):
        return len(obj)
    if isinstance(obj, dict):
        for k in ("nodes", "articles", "items"):
            if isinstance(obj.get(k), list):
                return len(obj[k])
        return len(obj)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="молчать, когда всё сходится")
    ap.add_argument("--no-alert", action="store_true", help="не писать в канал (для проверок)")
    # Проверка по умолчанию НИЧЕГО не меняет. Вычёркивание из манифеста — уже действие,
    # и делать его молча внутри «проверки» значит завести инструмент, которому нельзя
    # доверять на живом дереве.
    ap.add_argument("--fix", action="store_true",
                    help="вычеркнуть расхождения из манифеста, чтобы следующая выкладка их залила")
    a = ap.parse_args()

    # Два разных исхода, и путать их нельзя.
    #   broken — файл в облаке не разбирается или пуст. Это авария, тревога в канал.
    #   behind — в облаке записей меньше, чем локально. Это НОРМА между генерацией и
    #            выкладкой: статьи уже сделаны, но ещё не опубликованы. Тревожить этим
    #            канал — верный способ приучить не читать канал.
    broken, behind, checked = [], [], 0
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    dirty = []

    for rel in FILES:
        local = ROOT / rel
        if not local.exists():
            continue
        try:
            mine = count_of(json.loads(local.read_text(encoding="utf-8")))
        except Exception as e:                        # noqa: BLE001
            # Локальный файл битый — в облако он ещё не уехал, но уедет. Это тревога.
            broken.append(f"{rel}: ЛОКАЛЬНЫЙ файл не разбирается — {type(e).__name__}")
            continue
        try:
            r = requests.get(f"{SITE}/{rel}", headers=UA, timeout=60)
        except Exception as e:                        # noqa: BLE001
            broken.append(f"{rel}: не скачался — {type(e).__name__}: {str(e)[:80]}")
            continue
        checked += 1
        if r.status_code != 200:
            broken.append(f"{rel}: код {r.status_code}")
            continue
        try:
            theirs = count_of(r.json())
        except Exception:
            broken.append(f"{rel}: в облаке НЕ РАЗБИРАЕТСЯ как JSON "
                            f"({len(r.content) / 2 ** 20:.1f} МБ против "
                            f"{local.stat().st_size / 2 ** 20:.1f} МБ локально)")
            dirty.append(rel)
            continue
        if theirs == 0 and mine > 0:
            broken.append(f"{rel}: в облаке ПУСТО, локально {mine}")
            dirty.append(rel)
        elif theirs != mine:
            behind.append(f"{rel}: в облаке {theirs}, локально {mine} "
                          f"({'отстаёт' if theirs < mine else 'ОПЕРЕЖАЕТ'} на {abs(mine - theirs)})")
            dirty.append(rel)
        elif not a.quiet:
            print(f"✅ {rel}: {theirs}")

    # Вычёркиваем расхождения из манифеста — иначе дельта считает их залитыми и не тронет.
    if dirty and manifest and a.fix:
        for rel in dirty:
            manifest.pop(rel, None)
        tmp = MANIFEST.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, MANIFEST)
        print(f"\n♻️  вычеркнул из манифеста {len(dirty)} файлов — следующая выкладка "
              f"зальёт их заново.")

    if behind:
        print("\n".join("⏳ " + b for b in behind))
        print("   Это не поломка: свежие статьи есть локально и ждут выкладки. "
              "Станет поломкой, если не уйдёт после следующей публикации.")
        if not a.fix and dirty:
            print("   Заставить выкладку перезалить их: добавьте --fix.")

    if broken:
        print("\n".join("❌ " + p for p in broken))
        text = ("🚨 <b>В облаке лежит не то, что мы положили</b>\n"
                + "\n".join(f"· {p}" for p in broken[:10]))
        if a.no_alert:
            print("(в канал не пишу: --no-alert)")
            return 1
        try:
            import subprocess
            subprocess.run([sys.executable, str(ROOT / "tools" / "status_tg.py"), text],
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=60)
        except Exception as e:                        # noqa: BLE001
            print(f"(в канал не ушло: {e})")
        return 1
    if not a.quiet and not behind:
        print(f"\nсверено {checked} файлов, расхождений нет.")
    # Отставание — не тревога, но и не «всё хорошо»: отдельный код, чтобы запускалка
    # могла отличить одно от другого и не будила команду по пустякам.
    return 2 if behind else 0


if __name__ == "__main__":
    sys.exit(main())
