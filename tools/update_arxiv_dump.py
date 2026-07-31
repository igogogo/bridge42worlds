"""Обновление Kaggle-дампа arXiv + прогон чанков. Решение владельца 2026-07-31.

    python tools/update_arxiv_dump.py --check      только дата снапшота (бесплатно, секунда)
    python tools/update_arxiv_dump.py              скачать, если снапшот новее локального,
                                                   распаковать и прогнать arxiv_bulk_chunk.py
    python tools/update_arxiv_dump.py --force      скачать в любом случае

Токен — KAGGLE_API_TOKEN из .env или ~/.kaggle/access_token (новый формат KGAT_…,
Bearer-авторизация; проверено на живом API 2026-07-31). Дамп ~5,4 ГБ распакованный,
скачивается zip'ом в Downloads рядом с прежним. После обновления дата снапшота попадает
на дашборд через data/corpus-stats.json (corpus_stats.py --dump) — прогоняется здесь же.
"""
import argparse
import json
import os
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests

ROOT = Path(__file__).resolve().parent.parent
DUMP = Path(r"C:/Users/nadez/Downloads/arxiv-metadata-oai-snapshot.json")
ZIP = DUMP.with_name("arxiv-dump.zip")
API = "https://www.kaggle.com/api/v1/datasets"
DATASET = "Cornell-University/arxiv"


def token():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("KAGGLE_API_TOKEN="):
                return line.split("=", 1)[1].strip()
    t = Path.home() / ".kaggle" / "access_token"
    if t.exists():
        return t.read_text(encoding="ascii").strip()
    print("❌ токена нет: KAGGLE_API_TOKEN в .env или ~/.kaggle/access_token")
    sys.exit(1)


def remote_updated(tok):
    r = requests.get(f"{API}/view/{DATASET}", headers={"Authorization": f"Bearer {tok}"}, timeout=30)
    r.raise_for_status()
    j = r.json()
    return j["lastUpdated"][:10], j.get("totalBytes", 0)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true", help="только сравнить даты, ничего не качать")
    p.add_argument("--force", action="store_true", help="качать, даже если не новее")
    args = p.parse_args()

    tok = token()
    remote_date, total = remote_updated(tok)
    local_date = (datetime.fromtimestamp(DUMP.stat().st_mtime).strftime("%Y-%m-%d")
                  if DUMP.exists() else "нет файла")
    print(f"снапшот Kaggle: {remote_date} ({total/1e9:.2f} ГБ распакованный) | локальный файл: {local_date}")
    if args.check:
        return 0
    if DUMP.exists() and remote_date <= local_date and not args.force:
        print("локальный дамп не старее снапшота — качать нечего (--force, чтобы всё равно)")
        return 0

    print("качаю zip (это гигабайты — минуты)…", flush=True)
    with requests.get(f"{API}/download/{DATASET}", headers={"Authorization": f"Bearer {tok}"},
                      stream=True, timeout=60) as r:
        r.raise_for_status()
        done = 0
        with open(ZIP, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
                done += len(chunk)
                if done % (200 << 20) < (1 << 20):
                    print(f"  …{done / 1e9:.1f} ГБ", flush=True)
    print(f"скачано {ZIP.stat().st_size/1e9:.2f} ГБ, распаковываю…", flush=True)
    with zipfile.ZipFile(ZIP) as z:
        z.extract("arxiv-metadata-oai-snapshot.json", DUMP.parent)
    ZIP.unlink()
    print("✅ дамп обновлён, гоню чанки и статистику…", flush=True)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    for cmd in (["arxiv_bulk_chunk.py"], ["corpus_stats.py", "--dump"]):
        code = subprocess.run([sys.executable, *cmd], cwd=ROOT, env=env).returncode
        if code != 0:
            print(f"❌ {cmd[0]} завершился с кодом {code}")
            return code
    print("🎉 дамп, чанки и статистика покрытия обновлены")
    return 0


if __name__ == "__main__":
    sys.exit(main())
