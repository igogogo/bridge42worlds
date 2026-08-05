"""Сторож границы «что не публикуем»: не даёт .gitignore и deploy_r2.py разъехаться молча.

Находка аудита (2026-08-05): deploy_r2.py повторяет .gitignore руками, списком констант.
Списки живут в разных файлах и правятся разными людьми — рано или поздно кто-то закроет
от git новую приватную папку и не вспомнит про публикацию. Тогда приватное уедет в R2
и станет доступно по прямой ссылке.

Почему нельзя просто «читать .gitignore и не публиковать всё, что там»: это разные вопросы.
В .gitignore лежит `lang/**` — весь собранный сайт, ровно то, что публиковать НАДО (в git
его не держат, он тяжёлый). Списки обязаны различаться. Значит, задача не «слить в один»,
а «сделать расхождение громким».

Отсюда два замка, оба до заливки:

  1. Незнакомое правило. Каждый шаблон из .gitignore должен иметь вердикт в
     publish-rules.json: «внутреннее» (не публикуем) или «сборка» (публикуем, git его не
     держит по другой причине). Появилось новое правило без вердикта — заливка встаёт,
     пока человек не скажет, что это. Дешёвая бухгалтерия, но именно она ловит тот
     сценарий, ради которого всё затевалось.

  2. Реальная проверка путей. Первый замок сам по себе — обещание; второй его проверяет:
     весь список файлов, который deploy_r2 собрался залить, прогоняется через шаблоны
     с вердиктом «внутреннее». Хоть одно совпадение — стоп с поимённым перечнем.

Замок №1 ловит новое правило, замок №2 — старое правило, которое deploy_r2 перестал
покрывать (например, кто-то поправил SKIP_PATH_PREFIXES). Порознь каждый неполон.

Отдельно от них: PUBLISH_ONLY — те же проверки применимы и к резервной копии, но там
задача обратная (копируем всё невосстановимое), поэтому backup_r2.py этот модуль не зовёт.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GITIGNORE = ROOT / ".gitignore"
RULES = Path(__file__).resolve().parent / "publish-rules.json"

INTERNAL = "внутреннее"   # приватное/рабочее: в публикации быть не должно
BUILD = "сборка"          # собранный сайт: git его не держит, а публиковать надо


def read_gitignore():
    """Шаблоны .gitignore в порядке файла, без комментариев и пустых строк.

    Отрицания (`!lang/*/data/about.json`) оставляем как есть: pathspec понимает их
    в общем наборе, а для вердиктов это такие же строки, требующие решения."""
    out = []
    for line in GITIGNORE.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            out.append(s)
    return out


def load_rules():
    if not RULES.exists():
        return {}
    return json.loads(RULES.read_text(encoding="utf-8")).get("вердикты", {})


def load_exceptions():
    """Пути, которые публикуются вопреки вердикту «внутреннее», — с письменной причиной.

    Без этой лазейки сторож пришлось бы отключать целиком из-за одного файла: работа
    автора приходит архивом, а `*zip` в .gitignore закрыт (и правильно — своих архивов
    в репозитории быть не должно). Исключение поимённое и с причиной: если однажды
    оно окажется лишним, будет видно, кто и зачем его завёл."""
    if not RULES.exists():
        return []
    return json.loads(RULES.read_text(encoding="utf-8")).get("исключения", [])


def unreviewed(patterns=None, rules=None):
    """Шаблоны .gitignore без вердикта."""
    patterns = read_gitignore() if patterns is None else patterns
    rules = load_rules() if rules is None else rules
    return [p for p in patterns if p not in rules]


def stale(patterns=None, rules=None):
    """Вердикты для шаблонов, которых в .gitignore больше нет — чтобы список не пух."""
    patterns = set(read_gitignore() if patterns is None else patterns)
    rules = load_rules() if rules is None else rules
    return [p for p in rules if p not in patterns]


def internal_spec(rules=None):
    """pathspec по шаблонам с вердиктом «внутреннее»."""
    import pathspec
    rules = load_rules() if rules is None else rules
    pats = [p for p, v in rules.items() if v == INTERNAL]
    return pathspec.PathSpec.from_lines("gitwildmatch", pats)


def leaks(keys, rules=None):
    """Ключи из списка к заливке, попадающие под «внутреннее». Пусто — значит, чисто."""
    import pathspec
    spec = internal_spec(rules)
    allow = pathspec.PathSpec.from_lines(
        "gitwildmatch", [e["шаблон"] for e in load_exceptions()])
    return [k for k in keys if spec.match_file(k) and not allow.match_file(k)]


def check(keys):
    """Оба замка разом. Возвращает список причин отказа; пустой список — можно заливать."""
    patterns, rules = read_gitignore(), load_rules()
    problems = []

    new = unreviewed(patterns, rules)
    if new:
        problems.append(
            "В .gitignore есть правила без вердикта — непонятно, публиковать это или нет:\n"
            + "\n".join(f"     {p}" for p in new)
            + f"\n   Решите и допишите в {RULES.name}: «{INTERNAL}» или «{BUILD}».")

    bad = leaks(keys, rules)
    if bad:
        problems.append(
            f"К заливке подготовлено {len(bad)} файлов, закрытых как внутренние:\n"
            + "\n".join(f"     {k}" for k in bad[:20])
            + (f"\n     …и ещё {len(bad) - 20}" if len(bad) > 20 else "")
            + "\n   Либо чините фильтр в deploy_r2.py, либо меняйте вердикт правила.")

    return problems


def main():
    """Прогон вручную: показать состояние границы, ничего не заливая."""
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    patterns, rules = read_gitignore(), load_rules()
    print(f"правил в .gitignore: {len(patterns)} | вердиктов: {len(rules)}")
    n = unreviewed(patterns, rules)
    s = stale(patterns, rules)
    print("без вердикта: " + ("нет" if not n else "\n  " + "\n  ".join(n)))
    print("устаревших вердиктов: " + ("нет" if not s else "\n  " + "\n  ".join(s)))

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import deploy_r2
    keys = [p.relative_to(ROOT).as_posix() for p in deploy_r2.iter_files()]
    bad = leaks(keys, rules)
    print(f"файлов к публикации: {len(keys)} | из них закрытых как внутренние: {len(bad)}")
    for k in bad[:20]:
        print("  ", k)
    return 1 if (n or bad) else 0


if __name__ == "__main__":
    sys.exit(main())
