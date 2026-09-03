"""Delta-деплой сайта в Cloudflare R2 — заливает ТОЛЬКО изменённые файлы (по md5), а не весь
репозиторий. Заменяет 20-минутный git-push. (Подготовлено 2026-07-24, запускается после регенера.)

Что заливаем: собранный статический вывод — lang/, css/, js/, data/, favicon.*, sitemap*.xml,
feed*.xml, robots.txt. Внутренние файлы (см. .gitignore) не публикуются: data/arxiv-bulk,
data/bulk-select, папки api/, per-article data.json, arxiv-atom.xml/arxiv-oai.xml, *.pdf.
Список зеркалит .gitignore вручную (прямые проверки в Python) — `git check-ignore --stdin`
на 130k+ путях на Windows оказался неадекватно медленным/ненадёжным, отказались от него.

Как работает delta: держим локальный манифест cloudflare/.r2-manifest.json {путь: md5}. Заливаем
только файлы, чей md5 изменился (или которых нет в манифесте) → на 280k файлов это секунды, а не часы.
Удалённые файлы — опционально чистим (--prune).

Доступ — два пути, скрипт выбирает сам:
  1) S3 (boto3) — если в env есть R2_ACCESS_KEY_ID/R2_SECRET_ACCESS_KEY. Без лимита запросов,
     нужен для больших заливок (первичная заливка — 130k+ файлов).
  2) Нативный Cloudflare API v4 (Bearer CLOUDFLARE_API_TOKEN) — если S3-ключей нет. Проще (тот же
     токен, что для wrangler), но api.cloudflare.com лимитирован (~1200 запр/5мин) — годится только
     для мелких ежедневных дельт (десятки-сотни файлов), не для полной заливки.
Нужны env: CLOUDFLARE_ACCOUNT_ID (или R2_ACCOUNT_ID), R2_BUCKET=bridge42worlds-site,
  и либо (R2_ACCESS_KEY_ID + R2_SECRET_ACCESS_KEY), либо CLOUDFLARE_API_TOKEN.
"""
import os, sys, json, hashlib, mimetypes, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests
from dotenv import load_dotenv

# Windows: при выводе в файл/фон (не в консоль) Python откатывается на cp1252 и падает на кириллице.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
MANIFEST = ROOT / "cloudflare" / ".r2-manifest.json"
# ВНИМАНИЕ: data/ публикуется ЦЕЛИКОМ, за вычетом исключений ниже. Всё, что кладут
# в data/, оказывается по публичному адресу — рабочим файлам разработки там не место,
# им место рядом со своим скриптом (tools/ и подобные каталоги не публикуются вовсе).
INCLUDE_DIRS = ["lang", "css", "js", "data"]
# config.json обязателен: по нему строится строка выбора языков (search.js). Без него
# переключателя языков нет на всём сайте, а ошибка глушится пустым catch — молча.
INCLUDE_GLOBS = ["favicon.*", "sitemap*.xml", "feed*.xml", "robots.txt", "llms.txt", "*.html",
                 "config.json"]
# Зеркалит .gitignore для этих папок (см. docstring выше) — внутренние/рабочие файлы, не сайт.
# .pdf пропускаем везде, КРОМЕ страниц авторских работ: там PDF — это сама работа,
# первоисточник, на который ведёт главная кнопка страницы (см. исключение в
# publish-rules.json). В остальных местах .pdf — скачанный с arXiv исходник статьи.
SKIP_SUFFIX = {".pdf", ".jsonl"}
SKIP_SUFFIX_EXCEPT = ("/community/",)
# jpg исключаем ТОЛЬКО под lang/: там у каждой картинки статьи есть webp-двойник, страницы
# ссылаются на него, а jpg втрое тяжелее — из-за них сайт весил 11 ГБ вместо четырёх.
# Широкое правило «любой jpg» было ошибкой: картинки параграфов курса лежат в
# data/theory/courses/<тема>/img/<id>.jpg, двойников не имеют, и страница просит именно jpg —
# они бы просто пропали с сайта (поймано 2026-07-28 до публикации).
SKIP_JPG_UNDER = ("lang/",)
# fulltext.txt — разобранный текст чужой статьи, который мы храним ДЛЯ ВЕКТОРА,
# а не для читателя. На сайте ему делать нечего: это 179 МБ текста, права на
# который принадлежат авторам, и читателю мы даём наш пересказ и ссылку на arXiv.
# Ловится ровно тем же способом, что data.json и служебные xml.
SKIP_NAMES = {"data.json", "arxiv-atom.xml", "arxiv-oai.xml", "fulltext.txt",
              "references.txt",
              # Внутренние страницы для показа и обсуждения, живут в корне репозитория
              # рядом с настоящими страницами сайта. Публиковать их нельзя: INCLUDE_GLOBS
              # забирает из корня ВСЕ *.html, и после слияния ветки ML 12 августа портал
              # проекта, презентация и комплект докладчика уехали бы на публичный домен
              # вместе с обычной выкаткой — без единого решения кого-либо.
              "portal.html", "deck-en.html", "kit-index.html", "материалы.html"}
SKIP_DIR_NAMES = {"api"}
# .log, .pyc, __pycache__ здесь НЕ перечислены сознательно: их закрывает .gitignore, и с
# 2026-08-05 его правила применяются напрямую (см. _internal_by_gitignore). Дублировать
# их тут — ровно та ошибка, из-за которой в бакет уехали common.cpython-313.pyc и
# config_history.log из присланной автором работы. Исключения (авторский .log и .zip
# публикуются) живут в publish-rules.json, а не в этих константах.
# data/prompts — тексты запросов к модели, data/arxiv-index — рабочий индекс отбора статей
# (107 МБ). Ни то, ни другое браузер не запрашивает.
# data/submissions — РАБОЧАЯ папка присланных работ, и она приватная целиком. Найдено
# 2026-08-06 разведкой перед испытанием конвейера: её тут не было, и на прод уезжало всё
# содержимое заявки, включая meta.json с ПОЧТОЙ АВТОРА и его секретным токеном снятия
# публикации. Адрес при этом угадывается — код работы идёт подряд (b42p-ГОД-NNN), так что
# перебрать их мог кто угодно. Публиковать положено ТОЛЬКО собранные страницы под
# lang/*/community/, куда мы сами кладём то, что решили показать.
# Контакты авторов — ВТОРОЙ замок, поверх .gitignore. Один список, от которого
# зависит и git, и публикация, — это одна точка отказа: достаточно, чтобы кто-то
# завёл файл и не вспомнил про строку, и персональные данные уезжают в открытый
# доступ. Здесь тот же запрет записан отдельно и по существу.
SKIP_PATH_PREFIXES = ("data/authors-contacts", "data/authors-outreach",
                      "data/arxiv-bulk/", "data/arxiv-bulk", "data/bulk-select",
                      "data/prompts/", "data/arxiv-index", "data/submissions/",
                      "data/submissions",
                      # Эль-Ниньо: странице нужны latest.json, history.json и справочники;
                      # сырьё источников, снимки и саммари модели — рабочий архив, не сайт.
                      "data/enso/raw", "data/enso/last_good", "data/enso/snapshots",
                      "data/enso/summaries", "data/enso/iri")

mimetypes.add_type("application/json", ".json")
mimetypes.add_type("text/html; charset=utf-8", ".html")


_gitignore_spec = None


def _internal_by_gitignore(rel):
    """Правила .gitignore с вердиктом «внутреннее» — применяем их напрямую.

    Раньше этот список повторялся здесь константами; аудит справедливо назвал это путём
    к публикации приватного. Теперь источник один — .gitignore, а разметку «это не сайт,
    а внутреннее» держит cloudflare/publish-rules.json. Собственные правила ниже остаются:
    они про публикацию, а не про git (jpg под lang/, data/prompts/), и в .gitignore их нет."""
    global _gitignore_spec
    if _gitignore_spec is None:
        # Оба набора компилируются один раз: is_internal зовут на каждый из 100 000 файлов,
        # и сборка pathspec внутри неё превращала бы выкладку в минуты ожидания.
        import pathspec
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import publish_rules
        _gitignore_spec = (
            publish_rules.internal_spec(),
            pathspec.PathSpec.from_lines(
                "gitwildmatch", [e["шаблон"] for e in publish_rules.load_exceptions()]))
    spec, allow = _gitignore_spec
    return spec.match_file(rel) and not allow.match_file(rel)


def is_internal(p):
    rel = p.relative_to(ROOT).as_posix()
    if _internal_by_gitignore(rel):
        return True
    if p.suffix.lower() in SKIP_SUFFIX and not any(x in rel for x in SKIP_SUFFIX_EXCEPT):
        return True
    if p.name in SKIP_NAMES:
        return True
    # jpg под lang/ пропускаем ради веса: у картинок статей есть webp-двойник. Но обложка
    # авторской работы и кадры из её media/ двойников не имеют — страница просит именно
    # jpg, и без этого исключения на ней зияли бы дыры.
    if (p.suffix.lower() in (".jpg", ".jpeg") and rel.startswith(SKIP_JPG_UNDER)
            and "/community/" not in rel):
        return True
    if rel.startswith(SKIP_PATH_PREFIXES):
        return True
    if SKIP_DIR_NAMES & set(p.relative_to(ROOT).parts[:-1]):
        return True
    return False


def iter_files():
    candidates = []
    for d in INCLUDE_DIRS:
        for p in (ROOT / d).rglob("*"):
            if p.is_file() and not is_internal(p):
                candidates.append(p)
    for g in INCLUDE_GLOBS:
        for p in ROOT.glob(g):
            # is_internal здесь не для симметрии: корневые файлы шли в бакет вообще без
            # проверок, и ни SKIP_NAMES, ни правила .gitignore на них не действовали.
            # Пока в корне лежали только страницы сайта, это не всплывало.
            if p.is_file() and not is_internal(p):
                candidates.append(p)
    return candidates


def md5(p):
    h = hashlib.md5()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


"""ОПИСЬ ПОМНИТ НЕ ТОЛЬКО ОТПЕЧАТОК, НО И РАЗМЕР СО ВРЕМЕНЕМ ПРАВКИ.

Дельта считалась так: обойти дерево и посчитать отпечаток КАЖДОГО файла заново.
В облаке 286 920 файлов, из них 92 тысячи картинок; чтобы узнать, изменился ли
файл, его надо прочитать целиком, — то есть каждая выкладка читала с диска
десятки гигабайт. Именно это, а не отправка в сеть, и загружало машину до
неработоспособности (владелец 30.08).

Размер и время правки файловая система знает БЕЗ чтения содержимого. Совпали оба
и отпечаток уже записан — значит файл тот же, читать нечего. Обложке, которую не
трогали с июля, теперь достаётся один запрос к файловой системе вместо чтения
двухсот килобайт.

Чего эта проверка не поймает: правку, которая сохранила и размер, и время до
наносекунды. Такое бывает только при намеренном возврате времени; наши сборщики
пишут обычной записью. На случай сомнений есть --rehash: он считает всё заново,
как раньше.

Опись читается в обоих видах. Старая запись — просто строка с отпечатком; новая —
тройка «отпечаток, размер, время». Первая выкладка после этой правки честно
прочитает всё (сравнивать не с чем) и запишет тройки; выигрыш начнётся со второй.
"""


def stat_of(p):
    st = p.stat()
    return st.st_size, st.st_mtime_ns


def hash_of(entry):
    """Отпечаток из записи описи, каким бы ни был её вид."""
    if isinstance(entry, str):
        return entry
    if isinstance(entry, (list, tuple)) and entry:
        return entry[0]
    return None


def same_file(entry, size, mtime):
    """Можно ли поверить описи без чтения файла."""
    return (isinstance(entry, (list, tuple)) and len(entry) >= 3
            and entry[1] == size and entry[2] == mtime)


def _api_call(method, session, url, **kw):
    """Запрос к api.cloudflare.com с ретраем на 429/5xx (лимит ~1200 запр/5мин на токен)."""
    for attempt in range(6):
        r = session.request(method, url, **kw)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(min(2 ** attempt, 30))
            continue
        r.raise_for_status()
        return r
    r.raise_for_status()
    return r


class S3Backend:
    """Быстрый путь: R2 S3 API, без лимита запросов. Для больших заливок."""

    def __init__(self, account, bucket):
        import boto3
        from boto3.s3.transfer import TransferConfig
        from botocore.config import Config
        self.bucket = bucket
        # ФИКС «IncompleteBody» на файлах в мегабайты (2026-08-04, второй раз наступаем):
        # R2 не принимает chunked-стриминг с неточной длиной — большие articles-index-*.json
        # рвались на PutObject трижды подряд, выкладка 1661 файла обрывалась на середине.
        # Два рычага: multipart с порога 8 МБ (крупный файл идёт частями, у каждой части
        # честный Content-Length) и ретраи адаптивным режимом на уровне botocore.
        self.s3 = boto3.client(
            "s3", endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto",
            config=Config(retries={"max_attempts": 5, "mode": "adaptive"},
                          s3={"addressing_style": "path"}))
        # Порог 8 МБ не спас: ar-индекс на ~6 МБ шёл одним куском и рвался так же.
        # 2 МБ — крупные файлы у нас только индексы и картинки, им multipart не вредит.
        self.tcfg = TransferConfig(multipart_threshold=2 * 1024 * 1024,
                                   multipart_chunksize=2 * 1024 * 1024,
                                   use_threads=False)

    def put(self, p, key, ct):
        self.s3.upload_file(str(p), self.bucket, key, ExtraArgs={"ContentType": ct},
                            Config=self.tcfg)

    def delete_many(self, keys):
        for i in range(0, len(keys), 1000):
            batch = keys[i:i + 1000]
            self.s3.delete_objects(Bucket=self.bucket, Delete={"Objects": [{"Key": k} for k in batch]})


class TokenBackend:
    """Медленный путь: нативный Cloudflare API v4, тем же Bearer-токеном, что wrangler.
    Лимит ~1200 запр/5мин — только для мелких дельт."""

    def __init__(self, account, bucket, token):
        self.base = f"https://api.cloudflare.com/client/v4/accounts/{account}/r2/buckets/{bucket}/objects"
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"

    def put(self, p, key, ct):
        with p.open("rb") as f:
            _api_call("PUT", self.session, f"{self.base}/{key}", data=f, headers={"Content-Type": ct})

    def delete_many(self, keys):
        def rm(key):
            _api_call("DELETE", self.session, f"{self.base}/{key}")
        with ThreadPoolExecutor(max_workers=16) as ex:
            for _ in ex.map(rm, keys):
                pass


def notify_telegram(uploaded, total):
    """Сообщает в общий канал, что сайт обновился. Тихо молчит, если канал не настроен,
    и НИКОГДА не роняет публикацию: не доставленное уведомление — не повод считать,
    что сайт не опубликован."""
    # Общий выключатель канала (tools/tg_silence.py). Владелец 25 августа: «выруби
    # все сообщения в ленту, пока ждём ML». Дело при этом продолжается — молчит
    # только рапорт.
    try:
        import sys as _s
        from pathlib import Path as _P
        _r = str(_P(__file__).resolve().parent.parent)
        if _r not in _s.path:
            _s.path.insert(0, _r)
        from tools.tg_silence import guard as _guard
        if _guard("выкладка на прод завершена"):
            return 
    except ImportError:
        pass
    token, chat = os.environ.get("TG_BOT_TOKEN"), os.environ.get("TG_CHAT_ID")
    if not (token and chat):
        return
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", timeout=20, json={
            "chat_id": chat, "parse_mode": "HTML",
            "text": f"🚀 <b>Сайт обновлён</b>\nСтраниц изменено: <b>{uploaded}</b> (всего {total})",
        })
    except Exception as e:
        print(f"(уведомление в Telegram не ушло: {e})")


def _refuse_if_build_running():
    """Заливать во время регенера нельзя: в R2 попадёт смесь старых и новых страниц.

    Смотрим на файл-замок, который ставит генератор (см. run.py). Опрос процессов через wmic
    на этой машине молча возвращает пустоту — защита на нём не срабатывала (2026-07-28)."""
    lock = ROOT / ".build.lock"
    if not lock.exists():
        return
    try:
        info = lock.read_text(encoding="utf-8").strip()
    except Exception:
        info = ""
    print("⚠️  Идёт пересборка сайта" + (f" ({info})" if info else "") + ".")
    print("   Заливать сейчас нельзя: в R2 попадёт смесь старых и новых страниц.")
    print("   Дождитесь конца сборки и запустите заново.")
    print("   Если сборка оборвалась и замок остался — удалите .build.lock")
    raise SystemExit(1)


def _refuse_if_rules_unclear(keys):
    """Второй замок перед заливкой: граница «что не публикуем» должна быть внятной.

    Отказ, а не предупреждение. Предупреждение в конвейере, который ходит сам по
    расписанию, никто не прочтёт — а цена ошибки здесь односторонняя: опубликованное
    уже скачано и, возможно, проиндексировано. Пропущенная выкладка стоит одного прогона."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import publish_rules
    problems = publish_rules.check(keys)
    if not problems:
        return
    print("⛔ Выкладка остановлена: непонятна граница публикуемого.")
    for i, t in enumerate(problems, 1):
        print(f"   {i}. {t}")
    raise SystemExit(1)


def main():
    # Общий замок (tools/freeze.py): пока стоит, прогоны не начинаются.
    try:
        import sys as _s
        from pathlib import Path as _P
        _r = str(_P(__file__).resolve().parent.parent)
        if _r not in _s.path:
            _s.path.insert(0, _r)
        from tools.freeze import guard as _frozen
        _frozen("публикация на прод")
    except ImportError:
        pass
    # --only <путь> — выложить ТОЛЬКО то, что начинается с этого пути.
    #
    # Зачем. Правка интерфейса — это один файл css или js, и страницы подключают их
    # без версии в адресе, то есть доезжает она сама за пять минут жизни кэша, без
    # всякой пересборки (так и задумано, см. заголовки в worker.js). А выкладка при
    # этом всё равно считала дельту по всему дереву в 286 тысяч файлов и отказывалась
    # работать, пока идёт сборка. Получалось, что почтовую марку нельзя отправить,
    # пока не достроен дом.
    #
    # С точечной выкладкой манифест НЕ переписывается целиком: обновляются только
    # тронутые ключи, остальные переносятся как были. Иначе следующая полная выкладка
    # решила бы, что всего прочего в облаке нет, и залила бы весь сайт заново.
    only = []
    if "--only" in sys.argv:
        # НЕСКОЛЬКО ПУТЕЙ, а не один. Раньше бралось ровно sys.argv[i+1], и вызов
        # с двумя путями молча выкладывал первый: команда отрабатывала, отчитывалась
        # успехом, а половина того, ради чего её звали, оставалась дома. Берём всё
        # до следующего ключа.
        i = sys.argv.index("--only")
        rest = []
        for x in sys.argv[i + 1:]:
            if x.startswith("--"):
                break
            rest.append(x.replace("\\", "/").strip("/"))
        only = [x for x in rest if x]
        if not only:
            print("--only без пути. Стоп.")
            return
        print("точечная выкладка: только " + ", ".join(only))
    # ВЫКЛАДКА МИМО ОПИСИ. Опись читается в начале и пишется в конце; две выкладки
    # разом затрут друг другу её. Для одного маленького файла — журнала прогона,
    # который надо уронить на сайт посреди работы, — опись не нужна вовсе: файл
    # меняется каждую минуту, и запоминать его отпечаток бессмысленно.
    no_manifest = "--no-manifest" in sys.argv
    if not only:
        _refuse_if_build_running()
    prune = "--prune" in sys.argv
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or os.environ.get("R2_ACCOUNT_ID")
    bucket = os.environ.get("R2_BUCKET", "bridge42worlds-site")
    if not account:
        print("нет env CLOUDFLARE_ACCOUNT_ID / R2_ACCOUNT_ID. Стоп.")
        return

    if os.environ.get("R2_ACCESS_KEY_ID") and os.environ.get("R2_SECRET_ACCESS_KEY"):
        backend = S3Backend(account, bucket)
        print("бэкенд: S3 (быстрый, без лимита запросов)")
    elif os.environ.get("CLOUDFLARE_API_TOKEN"):
        backend = TokenBackend(account, bucket, os.environ["CLOUDFLARE_API_TOKEN"])
        print("бэкенд: нативный API по токену (медленнее, лимит ~4 запр/сек)")
    else:
        print("нет ни R2_ACCESS_KEY_ID/R2_SECRET_ACCESS_KEY, ни CLOUDFLARE_API_TOKEN. Стоп.")
        return

    # Работы, снятые авторами, не публикуем — даже если страницы всё ещё лежат в дереве.
    # Без этой проверки первая же выкладка вернула бы на сайт то, что автор снял час назад,
    # и он узнал бы об этом сам. Право снять публикацию стоит ровно столько, сколько живёт
    # между двумя выкладками.
    withdrawn = ()
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import submissions_sync
        withdrawn = tuple(submissions_sync.withdrawn_codes())
        if withdrawn:
            print(f"снято авторами (не публикуем): {', '.join(withdrawn)}")
    except Exception as e:
        # Молча продолжать нельзя: это тот случай, когда «не смогли проверить» означает
        # «можем опубликовать снятое». Останавливаемся и говорим почему.
        print(f"⛔ не удалось узнать список снятых работ: {str(e)[:160]}")
        print("   Публикация остановлена: иначе рискуем вернуть на сайт снятую работу.")
        raise SystemExit(1)

    old = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    # При точечной выкладке начинаем не с пустого манифеста, а со старого: иначе
    # всё, что не попало под фильтр, исчезнет из него и уедет заново следующим разом.
    if no_manifest:
        old = {}
    new, to_upload, skipped = (dict(old) if (only and not no_manifest) else {}), [], 0
    pending = {}          # отпечатки файлов, которые ещё предстоит отправить
    rehash = "--rehash" in sys.argv
    quick = 0
    for p in iter_files():
        key = p.relative_to(ROOT).as_posix()
        if only and not any(key.startswith(o) for o in only):
            continue
        if withdrawn and any(code in key for code in withdrawn):
            continue
        try:
            size, mtime = stat_of(p)
            prev = old.get(key)
            if not rehash and same_file(prev, size, mtime):
                # Размер и время те же — содержимое то же. Файл не читаем.
                new[key] = prev
                quick += 1
                continue
            h = md5(p)
        except FileNotFoundError:
            # другой процесс/сессия может параллельно писать в то же дерево (см. ПРАВИЛА-РАБОТЫ.md) —
            # файл, который был в листинге, успел исчезнуть; не роняем весь прогон из-за одного.
            skipped += 1
            continue
        if hash_of(old.get(key)) != h:
            # В опись попадёт после удачной отправки, не раньше.
            pending[key] = [h, size, mtime]
            to_upload.append((p, key))
        else:
            new[key] = [h, size, mtime]
    print(f"всего файлов: {len(new)} | изменённых к заливке: {len(to_upload)}" +
          (f" | без чтения (размер и время те же): {quick}" if quick else "") +
          (f" | пропущено (исчезли на лету): {skipped}" if skipped else ""))
    _refuse_if_rules_unclear(list(new))

    # Файл читается ДВАЖДЫ: сначала для md5 (выше), потом для отправки (ниже), и между
    # этими чтениями проходят минуты. Если между ними файл переписали, в бакет уедет одно
    # содержимое, а в манифест запишется отпечаток ДРУГОГО — и дельта больше никогда его
    # не тронет: локальный md5 совпадает с манифестом, значит «уже залито».
    #
    # Так 14 августа обрезанный индекс закрепился в облаке намертво: сам бы он не починился
    # никогда, его перезаливали руками на всех языках. Поэтому перед отправкой сверяем
    # отпечаток заново и, если файл изменился, отправляем НОВЫЙ и запоминаем НОВЫЙ.
    changed_under_us = []
    failed = []

    """ОБРЫВ СЕТИ НЕ ДОЛЖЕН ОБЕСЦЕНИВАТЬ ВЫКЛАДКУ.

    30 августа заливка 128 399 файлов упала на таймауте рукопожатия к R2 — обычная
    сетевая икота на большом прогоне. Упала целиком: одно исключение из потока
    выносило весь ex.map, опись не записывалась вовсе, и следующий запуск считал
    заново ВСЁ, включая сотню тысяч уже уехавших файлов.

    Две правки. Первая: файл попадает в опись ТОЛЬКО после удачной отправки —
    раньше отпечатки всех файлов проставлялись до заливки, и оборвись прогон в
    середине, опись соврала бы, что залито всё. Вторая: опись сохраняется по ходу,
    каждые две тысячи файлов. Оборвалось — потеряли последние две тысячи, а не сто
    двадцать восемь.

    Неудачные файлы в опись не попадают, поэтому следующий прогон возьмётся ровно
    за них.
    """
    RETRY = 3

    def put(item):
        p, key = item
        ct = mimetypes.guess_type(key)[0] or "application/octet-stream"
        try:
            fresh = md5(p)
            size, mtime = stat_of(p)
        except FileNotFoundError:
            return key, None
        if fresh != hash_of(pending.get(key)):
            changed_under_us.append(key)
        for attempt in range(RETRY):
            try:
                backend.put(p, key, ct)
                return key, [fresh, size, mtime]
            except Exception as e:
                if attempt == RETRY - 1:
                    failed.append((key, f"{type(e).__name__}: {str(e)[:60]}"))
                    return key, None
                time.sleep(1.5 * (attempt + 1))
        return key, None

    if to_upload:
        done_since_save = 0
        with ThreadPoolExecutor(max_workers=24) as ex:
            for i, (key, rec) in enumerate(ex.map(put, to_upload), 1):
                if rec:
                    new[key] = rec
                    done_since_save += 1
                if i % 500 == 0:
                    print(f"  залито {i}/{len(to_upload)}" +
                          (f" · не удалось {len(failed)}" if failed else ""))
                if done_since_save >= 2000 and not no_manifest:
                    MANIFEST.write_text(json.dumps(new, ensure_ascii=False),
                                        encoding="utf-8")
                    done_since_save = 0
    if failed:
        print(f"⚠️  не удалось залить {len(failed)} файлов — они НЕ записаны в опись, "
              f"следующий прогон возьмётся за них. Первые:")
        for k, why in failed[:5]:
            print(f"   {k}  ({why})")
    if changed_under_us:
        # Не тревога, а факт: дерево меняли во время выкладки. Печатаем, потому что это
        # первый признак двух прогонов на одном дереве — и потому что молчание здесь
        # означало бы, что мы опять не знаем, какая версия уехала.
        print(f"⚠️  во время заливки успели измениться {len(changed_under_us)} файлов — "
              f"залита свежая версия, манифест обновлён. Первые: "
              f"{', '.join(changed_under_us[:5])}")
    if prune:
        removed = [k for k in old if k not in new]
        # Чистка бакета сайта — не то же самое, что чистка кэша. С 2026-08-05 известно,
        # что переводы на четыре языка существуют только собранными страницами: бакет
        # для них не витрина, а экземпляр. Копия переводов теперь есть (backup_pages.py),
        # но удалять сотни страниц по расхождению манифеста всё равно нельзя молча —
        # манифест ведёт локальная машина, а ошибается обычно она.
        if len(removed) > 200 and "--yes-prune" not in sys.argv:
            print(f"⛔ к удалению {len(removed)} объектов — это много. Первые десять:")
            for k in removed[:10]:
                print("   ", k)
            print("   Если это действительно так задумано — добавьте --yes-prune.")
            raise SystemExit(1)
        backend.delete_many(removed)
        print(f"удалено устаревших: {len(removed)}")

    if not no_manifest:
        MANIFEST.write_text(json.dumps(new, ensure_ascii=False), encoding="utf-8")
    print(f"✅ delta-деплой готов: +{len(to_upload)} обновлено"
          + (", опись не тронута." if no_manifest else ", манифест сохранён."))
    if to_upload:
        notify_telegram(len(to_upload), len(new))


if __name__ == "__main__":
    main()
