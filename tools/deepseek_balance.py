"""Настоящий остаток на счёте DeepSeek — из личного кабинета, а не из нашей оценки.

Зачем. Наш журнал (data/usage-log.jsonl) считает расход по прайсу: токены × цена. Это
оценка СВЕРХУ, и 9 августа выяснилось, что она завышает примерно вдвое — журнал показывал
$12.53 за месяц при реальном остатке около $6. Дублей в журнале нет, цены сверены; похоже
на скидку или грант, применяемые при списании. Гадать бессмысленно: у DeepSeek есть ручка,
которая отдаёт остаток, и правду знает только она.

Что это меняет. Оценка сверху годится, чтобы НЕ ДАТЬ потратить лишнее (в этом качестве
budget_guard остаётся как есть — он должен ошибаться в безопасную сторону). Но отвечать
владельцу на вопрос «сколько осталось» оценкой сверху нельзя: он примет решение по числу,
которое вдвое меньше правды, и не запустит то, что мог бы.

    python tools/deepseek_balance.py            # человеку
    python tools/deepseek_balance.py --json     # машине (для сводки)
"""
import os, sys, json, argparse
from pathlib import Path
import requests
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
URL = "https://api.deepseek.com/user/balance"


def balance():
    """Остаток в долларах и признак «счёт ещё жив». None, если спросить не вышло."""
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return None, None, "нет DEEPSEEK_API_KEY"
    try:
        r = requests.get(URL, headers={"Authorization": f"Bearer {key}"}, timeout=30)
    except Exception as e:                       # noqa: BLE001 — причину показываем целиком
        return None, None, f"{type(e).__name__}: {str(e)[:120]}"
    if r.status_code != 200:
        return None, None, f"ответ {r.status_code}: {r.text[:120]}"
    d = r.json()
    usd = None
    for info in d.get("balance_infos", []):
        if info.get("currency") == "USD":
            usd = float(info.get("total_balance", 0))
    return usd, bool(d.get("is_available")), ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="машиночитаемо")
    a = ap.parse_args()
    usd, alive, err = balance()
    if a.json:
        print(json.dumps({"usd": usd, "available": alive, "error": err}, ensure_ascii=False))
        return 0 if usd is not None else 1
    if usd is None:
        print(f"остаток узнать не удалось — {err}")
        return 1
    print(f"на счёте DeepSeek: ${usd:.2f}" + ("" if alive else "  ⚠️ счёт помечен недоступным"))
    # Сравниваем с нашей оценкой: расхождение — не ошибка, а известное свойство (см.
    # заголовок файла). Печатаем оба числа, чтобы никто не считал одно из них враньём.
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        import budget_guard
        spent, today, _ = budget_guard.spend()
        print(f"наш журнал насчитал за период: ${spent:.2f} (сегодня ${today:.2f})")
        print("Журнал — оценка сверху по прайсу; на списание влияют скидки, поэтому "
              "решения о запуске принимаем по остатку выше, а запреты — по журналу.")
    except Exception as e:                       # noqa: BLE001
        # Не глотаем молча: «сравнить не с чем» — это тоже новость, а тихий пропуск
        # выглядел бы так, будто расхождения нет.
        print(f"(сравнить с журналом не вышло: {type(e).__name__} — {str(e)[:80]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
