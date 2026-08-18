#!/usr/bin/env bash
# Подготовка чистого VPS (Debian 12 / Ubuntu 24.04) под фабрику bridge42worlds.
#
# Что этот скрипт делает и чего НЕ делает. Он ставит окружение и раскладывает расписание.
# Он НЕ переносит ключи и НЕ переключает боевой режим: ключи едут руками (см. КЛЮЧИ ниже),
# переключение — отдельное решение владельца. Разделение намеренное: скрипт, который умеет
# и поднять машину, и увести на неё прод, однажды сделает второе, когда просили первое.
#
#     scp deploy/vps_setup.sh root@СЕРВЕР:/tmp/ && ssh root@СЕРВЕР bash /tmp/vps_setup.sh
#
# Идемпотентен: повторный запуск ничего не ломает и доводит недоделанное.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/igogogo/bridge42worlds.git}"
APP_USER="${APP_USER:-b42}"
APP_HOME="/home/${APP_USER}"
APP_DIR="${APP_HOME}/bridge42worlds"

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

say "Система и пакеты"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
# python3-venv — отдельным пакетом на Debian, без него venv молча не создаётся.
# git-lfs не нужен: тяжёлое живёт в R2, а не в git.
apt-get install -y -qq python3 python3-venv python3-pip git curl ca-certificates tzdata \
                       chromium unzip >/dev/null
# Часовой пояс машины владельца: расписания и логи считаются по нему, и расхождение
# в три часа проще всего не заводить вовсе.
timedatectl set-timezone Europe/Moscow || true

say "Пользователь ${APP_USER} (работать из-под root нельзя)"
id -u "${APP_USER}" >/dev/null 2>&1 || adduser --disabled-password --gecos "" "${APP_USER}"

say "Репозиторий"
if [ ! -d "${APP_DIR}/.git" ]; then
  sudo -u "${APP_USER}" git clone --depth 50 "${REPO_URL}" "${APP_DIR}"
else
  sudo -u "${APP_USER}" git -C "${APP_DIR}" fetch --depth 50 origin
fi

say "Окружение Python"
sudo -u "${APP_USER}" python3 -m venv "${APP_HOME}/venv"
sudo -u "${APP_USER}" "${APP_HOME}/venv/bin/pip" install -q --upgrade pip
sudo -u "${APP_USER}" "${APP_HOME}/venv/bin/pip" install -q -r "${APP_DIR}/requirements.txt"

say "Место под данные"
# ВНИМАНИЕ, замер 17 августа на рабочей машине — требование к диску выше, чем в задании:
#   lang/ (собранные страницы)  60,8 ГБ  ← нужны локально: генератор пишет их на диск,
#                                          а выкладка сравнивает с ними дельту по md5
#   data/ (дампы, кэши, исходники) 8,0 ГБ
#   .git полный                 10,9 ГБ  ← поэтому клон здесь МЕЛКИЙ (--depth 50)
# Итого около 70 ГБ сразу и рост вместе с архивом. Плюс требование владельца 18.08:
# держать ВСЕ PDF статей (сейчас ~12 ГБ и растут) — они корм для дообучения. Диска
# в 60 ГБ не хватит: брать от 100.
#
# ВАЖНО ПРО HETZNER (выбран владельцем 18.08): у CX33 всего 80 ГБ, этого мало уже сегодня.
# Два честных варианта: тариф CX43 (160 ГБ) либо CX33 + том Volume на 100 ГБ (~€4.4/мес,
# монтируется отдельно и переживает пересоздание сервера). Второй вариант дешевле и лучше
# по существу: данные отделены от системы, и машину можно пересоздать, не трогая архив.
sudo -u "${APP_USER}" mkdir -p "${APP_DIR}/data" "${APP_DIR}/logs"
df -h "${APP_HOME}" | tail -1

say "Расписание вместо планировщика Windows"
# На Windows задачи ставит schtasks, здесь — cron. Соответствие один в один, чтобы
# при сравнении двух машин не гадать, что где запущено. Времена — местные (см. timedatectl).
CRON_FILE=/etc/cron.d/b42
cat > "${CRON_FILE}" <<CRON
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
MAILTO=""
# минута час день месяц день_недели пользователь команда
30  3 * * * ${APP_USER} cd ${APP_DIR} && ${APP_HOME}/venv/bin/python run.py daily      >> logs/cron-daily.log 2>&1
0  19 * * * ${APP_USER} cd ${APP_DIR} && ${APP_HOME}/venv/bin/python tools/overnight.py >> logs/cron-overnight.log 2>&1
30  7 * * * ${APP_USER} REPO=${APP_DIR} PY=${APP_HOME}/venv/bin/python bash ${APP_DIR}/deploy/upkeep.sh
0   5 * * * ${APP_USER} cd ${APP_DIR} && ${APP_HOME}/venv/bin/python tools/update_arxiv_dump.py >> logs/cron-dump.log 2>&1
0   * * * * ${APP_USER} cd ${APP_DIR} && ${APP_HOME}/venv/bin/python tools/page_watch.py --quiet >> logs/cron-pagewatch.log 2>&1
CRON
chmod 0644 "${CRON_FILE}"
echo "расписание: ${CRON_FILE}"

say "Готово. Осталось ДВА шага руками"
cat <<'NEXT'
1. КЛЮЧИ. Через git они не едут и ехать не должны. Скопируйте .env с рабочей машины:
      scp .env b42@СЕРВЕР:/home/b42/bridge42worlds/.env
      ssh b42@СЕРВЕР chmod 600 /home/b42/bridge42worlds/.env
   Какие поля обязательны — cloudflare/.env.example.

2. ДАННЫЕ. Их тоже нет в git, они приезжают из резервной копии:
      cd /home/b42/bridge42worlds
      ~/venv/bin/python cloudflare/restore_r2.py --to .

Проверка вхолостую, ничего не тратя и ничего не публикуя:
      ~/venv/bin/python tools/factory.py --plan
      ~/venv/bin/python run.py stats

ПЕРЕКЛЮЧАТЬ БОЕВОЙ РЕЖИМ ЭТОТ СКРИПТ НЕ УМЕЕТ — и не должен. Пока обе машины живы,
расписание должно работать РОВНО НА ОДНОЙ: два конвейера на одном репозитории и одном
бакете — это гонка записи, которую мы уже проходили на одном дереве.
NEXT
