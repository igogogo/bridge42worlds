#!/usr/bin/env bash
# Ночной уход за архивом — то же, что tools/upkeep.cmd на Windows, слово в слово по шагам.
#
# Почему отдельный файл, а не «запустить upkeep.py». Такого файла нет: на Windows это
# .cmd-цепочка из семи команд, и при переезде она не переносится сама. Это и есть главный
# ответ на вопрос «что завязано на Windows»: не код, а ЗАПУСКАЛКИ. Порядок шагов здесь
# повторяет .cmd намеренно — он не случаен, объяснения к каждому шагу живут там.
#
# Пока обе машины живы, этот файл должен работать РОВНО НА ОДНОЙ. Два конвейера на одном
# репозитории и одном бакете — гонка записи, которую мы уже проходили.
set -uo pipefail

REPO="${REPO:-/home/b42/bridge42worlds}"
PY="${PY:-/home/b42/venv/bin/python}"
STAMP="$(date +%Y%m%d_%H%M)"
LOG="${REPO}/logs/upkeep_${STAMP}.log"
mkdir -p "${REPO}/logs"
cd "${REPO}"

export PYTHONIOENCODING=utf-8
export PYTHONUNBUFFERED=1
RC=0

# Шаг падает — запоминаем код, но идём дальше: следующие шаги чинят то, что уже есть,
# и от неудачи предыдущего хуже не станет. А вот молча отчитаться успехом нельзя.
step() {
  echo "=== $* ===" >> "${LOG}"
  "$@" >> "${LOG}" 2>&1 || RC=$?
}

step "${PY}" tools/tag_by_vector.py --apply
step "${PY}" tools/graph_repair.py
step "${PY}" embeddings_export.py
step "${PY}" cloudflare/vector_build.py
step "${PY}" tools/abstract_orig.py
step "${PY}" tools/recommend.py --all-full --limit 60
step "${PY}" tools/recommend.py --fix-links

# Пересборка и выкладка — хвостом самой команды (см. run.py, _publish_to_r2).
# B42_LEAD=1: страж пересборки пропускает только ведущую, ночная задача и есть она.
B42_LEAD=1 step "${PY}" run.py html

echo "[$(date '+%F %T')] upkeep rc=${RC}" >> "${REPO}/logs/upkeep-history.log"
if [ "${RC}" != "0" ]; then
  "${PY}" tools/status_tg.py --run-failed upkeep "${RC}" "logs/upkeep_${STAMP}.log" || true
fi
exit "${RC}"
