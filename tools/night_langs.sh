#!/bin/bash
# Ночная догонялка языков: имена и карточки понятий на es/ar/fr, затем страницы,
# облако и выкладка. Владелец 28.08: «займись переводами, чтобы сформировать и
# доформировать всё целиком, а я спать».
#
# Порядок не случаен: сперва ИМЕНА (без них страница зовётся английским словом),
# потом карточки, и только затем сборка — иначе страницы соберутся с наполовину
# переведённым слоем и придётся собирать второй раз.
#
# Арабский первым: университет в Кувейте — целевая аудитория проекта.
set -u
cd "$(dirname "$0")/.."
export B42_LEAD=1 PYTHONIOENCODING=utf-8

for L in ar es fr; do
  echo "═══ $L: имена ═══"
  python tools/concept_names_translate.py --lang "$L"
  echo "═══ $L: карточки ═══"
  python tools/cards_translate_ru.py --concepts --lang "$L" --force-peak
done

echo "═══ страницы понятий (все языки) ═══"
python concepts_pages.py

echo "═══ формулы ═══"
python formulas_pages.py

echo "═══ облако ═══"
python cloudflare/concepts_sync.py

echo "═══ выкладка ═══"
python run.py publish

echo "═══ проверки ═══"
python cloudflare/checks/api_check.py --prod
python cloudflare/checks/pages_check.py
python tools/link_check.py --sample 25
echo "═══ НОЧНАЯ РАБОТА ЗАВЕРШЕНА ═══"
