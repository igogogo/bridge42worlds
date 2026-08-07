"""Право автора снять свою работу: регистрация токенов и учёт снятых работ.

По ТЗ владельца (задачи/АВТОРСКИЕ-РАБОТЫ.md, п.6) автор снимает публикацию когда захочет
и без объяснений. Чтобы ручка /api/community/withdraw могла проверить его токен, Worker
должен знать ОТПЕЧАТОК этого токена. Сам токен живёт в data/submissions/<код>/meta.json
и на прод не уезжает (папка закрыта после находки 6 августа: вместе со страницами работы
на сайт уходила почта автора и этот самый токен).

Кладём в KV именно отпечаток (SHA-256), а не токен. Разница важна: утечка нашего
хранилища не должна давать возможность снимать чужие работы. Сравнение на стороне Worker
идёт постоянным по времени сравнением — код работы угадывается (b42p-ГОД-NNN идут подряд),
значит перебор реален.

    python cloudflare/submissions_sync.py            # зарегистрировать новые заявки
    python cloudflare/submissions_sync.py --list     # что зарегистрировано и что снято
    python cloudflare/submissions_sync.py --restore b42p-2026-001   # вернуть публикацию

Снятие НЕ удаляет материалы автора: он может передумать. Возврат — команда выше, и её
запускает человек, а не автоматика.
"""
import os, sys, json, hashlib, argparse
from pathlib import Path
import requests
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(os.environ.get("B42_DATA_ROOT") or Path(__file__).resolve().parent.parent)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
KV_NAMESPACE = os.environ.get("KV_TOKENS_ID", "bf89cc7963304948a6a7aeeb0a06e43d")
SUBMISSIONS = ROOT / "data" / "submissions"


def kv():
    acc = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or os.environ.get("R2_ACCOUNT_ID")
    tok = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not (acc and tok):
        raise SystemExit("нет CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN")
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {tok}"
    return s, (f"https://api.cloudflare.com/client/v4/accounts/{acc}"
               f"/storage/kv/namespaces/{KV_NAMESPACE}")


def keys_with_prefix(s, base, prefix):
    out, cursor = [], None
    while True:
        p = {"limit": 1000, "prefix": prefix}
        if cursor:
            p["cursor"] = cursor
        j = s.get(f"{base}/keys", params=p, timeout=60).json()
        out += [k["name"] for k in j.get("result", [])]
        cursor = (j.get("result_info") or {}).get("cursor")
        if not cursor:
            break
    return out


def withdrawn_codes(s=None, base=None):
    """Список снятых работ. Читается и выкладкой: опубликовать снятое заново нельзя."""
    if s is None:
        s, base = kv()
    return sorted(k.split(":", 1)[1] for k in keys_with_prefix(s, base, "wd:"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="что зарегистрировано и что снято")
    ap.add_argument("--restore", metavar="CODE", help="вернуть публикацию снятой работы")
    a = ap.parse_args()
    s, base = kv()

    if a.restore:
        r = s.delete(f"{base}/values/wd:{a.restore}", timeout=60).json()
        if not r.get("success"):
            print("не вышло:", json.dumps(r.get("errors"), ensure_ascii=False)[:200])
            return 1
        print(f"✅ {a.restore}: признак снятия убран. Страницы вернутся следующей выкладкой "
              f"(run.py publish) — сами по себе они в хранилище не появятся.")
        return 0

    if a.list:
        reg = keys_with_prefix(s, base, "sub:")
        wd = withdrawn_codes(s, base)
        fails = keys_with_prefix(s, base, "wdfail:")
        print(f"зарегистрировано работ: {len(reg)}")
        for k in reg:
            code = k.split(":", 1)[1]
            print(f"   {code}" + ("   ← СНЯТА автором" if code in wd else ""))
        if fails:
            # Неудачные попытки — не шум: код угадывается, и всплеск здесь означает подбор.
            print(f"\nнеудачных попыток снятия: {len(fails)}")
            for k in fails[-10:]:
                print("   ", k)
        return 0

    if not SUBMISSIONS.exists():
        print(f"папки {SUBMISSIONS} нет — регистрировать нечего.")
        return 0
    known = set(keys_with_prefix(s, base, "sub:"))
    added = 0
    for meta_path in sorted(SUBMISSIONS.glob("*/meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        code = meta.get("code") or meta_path.parent.name
        token = meta.get("author_token")
        if not token:
            print(f"⚠️  {code}: в meta.json нет author_token — автор не сможет снять работу")
            continue
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        r = s.put(f"{base}/values/sub:{code}", data=digest.encode(),
                  files=None, timeout=60,
                  headers={"Content-Type": "text/plain"})
        if r.status_code != 200 or not r.json().get("success"):
            print(f"⚠️  {code}: не записалось — {r.text[:160]}")
            continue
        added += 1
        print(f"✅ {code}: токен зарегистрирован" + ("" if f"sub:{code}" in known else " (новая)"))
    print(f"\nготово: {added} работ готовы к снятию автором.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
