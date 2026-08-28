#!/bin/bash
# Точечный прогон: забрать дни, собрать изменившееся, выложить. Ничего больше.
# Владелец 28.08: «переводы, прочее — это всё потом; давай прогони, чтобы новые
# дни появились, и стоп».
set -u
cd "$(dirname "$0")/.."
export B42_LEAD=1 PYTHONIOENCODING=utf-8
for d in 2026-08-24 2026-08-25 2026-08-26 2026-08-27; do
  echo "═══ день $d ═══"
  B42_LANGS=ru,en B42_NO_PUBLISH=1 python run.py daily --date "$d" --limit 20
done
echo "═══ сборка изменившегося ═══"
B42_LANGS=ru,en B42_NO_PUBLISH=1 python run.py html
echo "═══ выкладка ═══"
python run.py publish
echo "═══ готово ═══"
