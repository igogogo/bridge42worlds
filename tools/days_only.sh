#!/bin/bash
# Точечный прогон: забрать дни, собрать изменившееся, выложить. Ничего больше.
# Владелец 28.08: «переводы, прочее — это всё потом; давай прогони, чтобы новые
# дни появились, и стоп».
#
# После КАЖДОГО дня отмечаемся в журнале схемы (/pipeline.html). Иначе она
# показывает последнее, что ей сообщили, и прогон выглядит зависшим — так и
# случилось 28.08: конвейер шёл, а схема час стояла на одном дне.
set -u
cd "$(dirname "$0")/.."
export B42_LEAD=1 PYTHONIOENCODING=utf-8
DAYS="${1:-2026-08-24,2026-08-25,2026-08-26,2026-08-27}"
IFS=',' read -ra LIST <<< "$DAYS"
for d in "${LIST[@]}"; do
  echo "═══ день $d ═══"
  python tools/days_state.py --days "$DAYS" --current "day-$d" >/dev/null 2>&1
  B42_LANGS=ru,en B42_NO_PUBLISH=1 python run.py daily --date "$d" --limit 20
  python tools/days_state.py --days "$DAYS" >/dev/null 2>&1
done
echo "═══ сборка изменившегося ═══"
python tools/days_state.py --days "$DAYS" --current html >/dev/null 2>&1
# B42_ONLY_NEW: правка генератора не тянет за собой сорок тысяч страниц. Полная
# пересборка — дело служебного прогона (tools/weekly_run.py), и она объявлена.
B42_LANGS=ru,en B42_NO_PUBLISH=1 B42_ONLY_NEW=1 python run.py html
# Карточки статей в облачную базу: страница статьи уезжает статикой в R2, а ЛЕНТА
# собирается из D1. Без этого шага статья открывается по прямой ссылке, но в ленте
# её нет — 28.08 так и вышло, и выглядело это как «динамика не работает».
echo "═══ карточки в облако ═══"
python cloudflare/cards_sync.py --apply

echo "═══ выкладка ═══"
python tools/days_state.py --days "$DAYS" --current publish >/dev/null 2>&1
python run.py publish
python tools/days_state.py --days "$DAYS" --finish >/dev/null 2>&1
echo "═══ готово ═══"
