"""Не дать ключу уехать в коммит. Смотрит ТОЛЬКО добавляемые строки.

Зачем. 5 июля 2026 файл .env попал в публичную историю и пролежал там девять дней.
Ключи с тех пор мертвы, но история публична, и вычистить её — операция, которая
переписывает все SHA и ломает рабочие папки всей команды. Урок отсюда не «чистить
быстрее», а «не пускать»: след стоит дорого, а вход бесплатен.

Что ищем — ПОЛНЫЕ образцы наших ключей, а не приметы вроде «строка со словом key».
Это принципиально: отчёты и заметки постоянно упоминают ключи обрезанными
(«sk-5dd1ac6a7…», «b42svc_f58…»), и проверка, срабатывающая на них, будет мешать
каждый день — а мешающую проверку отключают.

    python tools/secret_scan.py           # проверить, что подготовлено к коммиту
    python tools/secret_scan.py --all     # проверить всё дерево (медленнее)
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# Каждый образец — полной длины, с якорями по краям слова.
PATTERNS = [
    ("ключ DeepSeek/OpenAI", re.compile(r"\bsk-[a-zA-Z0-9]{32,}\b")),
    ("токен Cloudflare (API)", re.compile(r"\bcfat_[A-Za-z0-9_-]{30,}\b")),
    ("токен Cloudflare (DNS)", re.compile(r"\bcfut_[A-Za-z0-9_-]{30,}\b")),
    ("токен бота Telegram", re.compile(r"\b\d{8,12}:AA[A-Za-z0-9_-]{30,}\b")),
    ("токен Kaggle", re.compile(r"\bKGAT_[a-f0-9]{32,}\b")),
    ("служебный ключ b42", re.compile(r"\bb42svc_[a-f0-9]{40,}\b")),
    ("секрет R2 (64 шестнадцатеричных)", re.compile(r"\b[a-f0-9]{64}\b")),
]
# Файлы, которым в git не место вовсе, как бы ни выглядело их содержимое.
FORBIDDEN_NAMES = {".env", ".dev.vars"}
FORBIDDEN_SUFFIX = {".key", ".pem"}
# Где 64 шестнадцатеричных знака — норма, а не секрет: отпечатки файлов и коммитов.
HEX_OK_FILES = re.compile(r"(manifest|\.lock|package-lock|\.sha256|hashes?)", re.I)


def staged_additions():
    """Добавляемые строки из подготовленного к коммиту. Только «+», без контекста."""
    out = subprocess.run(["git", "diff", "--cached", "-U0"],
                         capture_output=True, text=True, errors="replace").stdout
    cur = ""
    for line in out.splitlines():
        if line.startswith("+++ b/"):
            cur = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            yield cur, line[1:]


def staged_names():
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                         capture_output=True, text=True, errors="replace").stdout
    return [x for x in out.splitlines() if x.strip()]


def scan_lines(pairs):
    hits = []
    for path, line in pairs:
        if HEX_OK_FILES.search(path or ""):
            continue
        for title, rx in PATTERNS:
            m = rx.search(line)
            if m:
                shown = m.group(0)
                hits.append((path, title, shown[:12] + "…"))
                break
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="всё дерево, а не подготовленное")
    a = ap.parse_args()

    problems = []
    for name in staged_names():
        p = Path(name)
        if p.name in FORBIDDEN_NAMES or p.suffix in FORBIDDEN_SUFFIX:
            problems.append((name, "файл с доступами", "коммитить нельзя вовсе"))

    if a.all:
        pairs = []
        for p in Path(".").rglob("*"):
            if not p.is_file() or ".git" in p.parts or ".venv" in p.parts:
                continue
            if p.suffix.lower() not in (".py", ".js", ".json", ".md", ".txt", ".toml",
                                        ".yml", ".yaml", ".cmd", ".sh", ".html"):
                continue
            try:
                for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                    pairs.append((p.as_posix(), line))
            except OSError:
                continue
        problems += scan_lines(pairs)
    else:
        problems += scan_lines(staged_additions())

    if problems:
        print("==> СТОП: похоже на ключ в коммите.")
        for path, title, shown in problems[:20]:
            print(f"    {path}: {title} — {shown}")
        print("\n    Ключам место в .env (он в .gitignore). Если это ЛОЖНАЯ тревога —")
        print("    правьте образец в tools/secret_scan.py, а не обходите проверку:")
        print("    обойдённая один раз, она обходится всегда.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
