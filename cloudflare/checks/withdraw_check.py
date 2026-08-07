"""Проверка права автора снять работу — концом-в-конец, на испытательном Worker'е.

Регистрирует вымышленную работу (кода b42p-2026-999 не существует, страниц у неё нет),
проверяет отказ на чужом токене, снятие на своём, повторное снятие, и убирает следы.
"""
import hashlib, json, os, sys, urllib.request
import requests
from dotenv import load_dotenv

BASE = sys.argv[1] if len(sys.argv) > 1 else \
    "https://bridge42worlds-dev.bridge42worlds-dev.workers.dev"
CODE = "b42p-2026-999"
GOOD = "b42a-proverka-prava-avtora"
BAD = "b42a-podobrannyj-token--"
UA = {"User-Agent": "Mozilla/5.0 b42-selfcheck", "content-type": "application/json"}

load_dotenv(r"C:\Users\nadez\PycharmProjects\b42-devops\.env")
ACC = os.environ["CLOUDFLARE_ACCOUNT_ID"]
NS = os.environ.get("KV_TOKENS_ID", "bf89cc7963304948a6a7aeeb0a06e43d")
S = requests.Session()
S.headers["Authorization"] = f"Bearer {os.environ['CLOUDFLARE_API_TOKEN']}"
KV = f"https://api.cloudflare.com/client/v4/accounts/{ACC}/storage/kv/namespaces/{NS}"


def post(payload):
    req = urllib.request.Request(f"{BASE}/api/community/withdraw", headers=UA,
                                 data=json.dumps(payload).encode())
    def parse(raw):
        # Не всякий ответ — JSON: край Cloudflare умеет вернуть свою HTML-страницу,
        # и проверка не должна падать вместо того, чтобы показать, что пришло.
        try:
            return json.loads(raw or "{}")
        except ValueError:
            return {"не_json": (raw or "")[:80]}
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, parse(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, parse(e.read().decode())


def main():
    digest = hashlib.sha256(GOOD.encode()).hexdigest()
    S.put(f"{KV}/values/sub:{CODE}", data=digest.encode(),
          headers={"Content-Type": "text/plain"}, timeout=60)
    S.delete(f"{KV}/values/wd:{CODE}", timeout=60)
    print(f"работа {CODE} зарегистрирована для проверки\n")

    checks, bad = [], 0
    code, d = post({"code": CODE, "token": BAD})
    checks.append(("чужой токен отклонён", code == 403 and d.get("error") == "forbidden", f"{code} {d}"))
    code, d = post({"code": CODE})
    checks.append(("без токена — отказ", code == 400, f"{code} {d}"))
    code, d = post({"code": "не-код", "token": GOOD})
    checks.append(("мусорный код — отказ", code == 400, f"{code} {d}"))
    code, d = post({"code": CODE, "token": GOOD})
    ok = code == 200 and d.get("ok") and "снят" in (d.get("message") or "")
    checks.append(("свой токен снимает работу", ok, f"{code} {str(d)[:70]}"))
    code, d = post({"code": CODE, "token": GOOD})
    checks.append(("повторное снятие не ломается", code == 200 and d.get("ok"), f"{code}"))

    flag = S.get(f"{KV}/values/wd:{CODE}", timeout=60)
    checks.append(("признак снятия записан", flag.status_code == 200, flag.text[:30]))

    for name, good, info in checks:
        print(("✅ " if good else "❌ ") + name + ("" if good else f"  ← {info}"))
        bad += not good

    S.delete(f"{KV}/values/sub:{CODE}", timeout=60)
    S.delete(f"{KV}/values/wd:{CODE}", timeout=60)
    print(f"\nследы проверки убраны | итог: {len(checks) - bad} из {len(checks)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
