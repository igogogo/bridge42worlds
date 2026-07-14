"""Офлайн-проверка внутренних ссылок сайта на 404 — без API, чистый обход файловой системы.
Разбирает href/src во всех *.html под lang/ + корневых *.html, резолвит корне-относительные
пути ("/lang/..") к файлам на диске, для "директорных" ссылок ("/lang/ru/tags/") проверяет
index.html внутри. Внешние ссылки (http/https/mailto/tel/javascript/data) и якоря — пропускает."""
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).parent
LINK_RE = re.compile(r'(?:href|src)="([^"]+)"')
SKIP_PREFIXES = ("http://", "https://", "mailto:", "tel:", "javascript:", "data:", "//")


def _html_files():
    files = list(ROOT.glob("*.html"))
    lang_dir = ROOT / "lang"
    if lang_dir.exists():
        files += list(lang_dir.rglob("*.html"))
    return files


def _resolve(url, from_file):
    path = urlsplit(url).path
    if not path:
        return None
    return (ROOT / path.lstrip("/")) if path.startswith("/") else (from_file.parent / path).resolve()


def _target_ok(target):
    if target.is_dir():
        return (target / "index.html").exists()
    if target.exists():
        return True
    return (target / "index.html").exists()  # путь без слэша, но фактически директория


def check_links(verbose=True):
    html_files = _html_files()
    cache = {}
    broken = {}  # url -> [referrer, ...]
    for f in html_files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in LINK_RE.finditer(text):
            url = m.group(1)
            if not url or url.startswith("#") or url.startswith(SKIP_PREFIXES):
                continue
            if "' +" in url or "+ '" in url:
                continue  # JS-конкатенация URL внутри инлайн <script> — не настоящий href/src
            target = _resolve(url, f)
            if target is None:
                continue
            key = str(target)
            if key not in cache:
                cache[key] = _target_ok(target)
            if not cache[key]:
                broken.setdefault(url, []).append(str(f.relative_to(ROOT)))

    if verbose:
        if not broken:
            print(f"  ✅ Ссылки целы: проверено {len(html_files)} HTML-файлов, битых не найдено")
        else:
            print(f"  ⚠️ Битых ссылок: {len(broken)} (уникальных целей) в {len(html_files)} проверенных файлах")
            for url, referrers in sorted(broken.items(), key=lambda kv: -len(kv[1])):
                head = ", ".join(referrers[:3])
                more = f" и ещё {len(referrers) - 3}" if len(referrers) > 3 else ""
                print(f"      {url}  ← {head}{more}")
    return broken


if __name__ == "__main__":
    broken = check_links()
    sys.exit(1 if broken else 0)
