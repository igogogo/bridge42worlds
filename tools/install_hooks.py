"""Поставить git-хуки из репозитория в .git/hooks.

Зачем отдельная команда. Хуки не ездят вместе с кодом: git их не версионирует, и до
17 августа наш pre-commit существовал ровно в одном экземпляре — в .git/hooks на машине
владельца. Ни истории, ни возможности поправить его веткой, ни способа узнать, что у
соседа стоит другая версия. Теперь канонический текст лежит в tools/hooks/, а эта
команда раскладывает его по местам.

Про рабочие папки ролей: связанные worktree пользуются хуками ГЛАВНОГО репозитория,
поэтому установка нужна одна на всех. Скрипт находит настоящую папку .git сам и говорит,
куда именно поставил, — чтобы не гадать, подействовало ли.

    python tools/install_hooks.py            # поставить
    python tools/install_hooks.py --check    # только сравнить, ничего не менять
"""
import argparse
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "tools" / "hooks"


def hooks_dir():
    """Настоящая папка хуков. В worktree .git — это файл-указатель, и класть хук рядом
    с ним бесполезно: git смотрит в общий каталог основного репозитория."""
    out = subprocess.run(["git", "rev-parse", "--git-common-dir"],
                         capture_output=True, text=True, cwd=ROOT)
    common = (out.stdout or "").strip() or ".git"
    p = Path(common)
    if not p.is_absolute():
        p = (ROOT / p).resolve()
    return p / "hooks"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="сравнить и не менять")
    a = ap.parse_args()

    dest_dir = hooks_dir()
    if not dest_dir.exists():
        print(f"нет папки хуков: {dest_dir}")
        return 1
    if not SOURCE.exists():
        print(f"нет исходников хуков: {SOURCE}")
        return 1

    diffs, installed = [], 0
    for src in sorted(SOURCE.iterdir()):
        if not src.is_file():
            continue
        dst = dest_dir / src.name
        same = dst.exists() and dst.read_bytes() == src.read_bytes()
        if same:
            print(f"  {src.name}: совпадает")
            continue
        diffs.append(src.name)
        if a.check:
            print(f"  {src.name}: ОТЛИЧАЕТСЯ от репозитория"
                  + ("" if dst.exists() else " (не установлен вовсе)"))
            continue
        dst.write_bytes(src.read_bytes())
        # Права на исполнение нужны там, где они вообще есть; на Windows git запускает
        # хук через оболочку и на бит не смотрит.
        try:
            dst.chmod(0o755)
        except OSError:
            pass
        installed += 1
        print(f"  {src.name}: установлен → {dst}")

    if a.check:
        print(f"\nрасхождений: {len(diffs)}")
        return 1 if diffs else 0
    print(f"\nустановлено: {installed}, папка хуков — {dest_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
