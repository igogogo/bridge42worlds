-- Карточки статей на сервере: хранилище для ОБОИХ видов поиска и для будущей ленты.
--
-- Почему таблица, а не «просто добавим FTS». Vectorize отдаёт только идентификаторы
-- с крохой метаданных — нарисовать по ним карточку нельзя. Значит, данные карточки
-- всё равно должны лежать на сервере, и держать их дважды (для смыслового и для
-- словесного поиска) бессмысленно. Отсюда: одна таблица карточек, два движка поверх,
-- оба возвращают id, карточки достаются одним запросом.
--
-- Побочная выгода, ради которой это и затевалось: постраничная лента и календарь
-- становятся обычными запросами к этой же таблице, и рост архива перестаёт влиять
-- на вес страницы у читателя.

CREATE TABLE IF NOT EXISTS cards (
  id               TEXT NOT NULL,        -- arXiv id, он же ключ статьи
  lang             TEXT NOT NULL,        -- ru/en/es/ar/fr
  version          TEXT NOT NULL,        -- уровень: mini/simple/advanced
  title            TEXT,
  oneliner         TEXT,
  description      TEXT,
  authors          TEXT,                 -- JSON-массив строкой: D1 отдаёт его клиенту как есть
  tags             TEXT,                 -- JSON-массив
  laws             TEXT,                 -- JSON-массив
  scientists       TEXT,                 -- JSON-массив
  categories       TEXT,                 -- JSON-массив
  primary_category TEXT,
  date             TEXT,                 -- YYYY-MM-DD, по нему же курсор ленты
  url              TEXT,
  image            TEXT,
  reading          INTEGER,              -- минут чтения
  express          INTEGER DEFAULT 0,    -- 1 — экспресс (пересказ по аннотации автора)
  PRIMARY KEY (id, lang, version)
);

-- Лента и календарь: выборка по языку и уровню, свежие сверху.
CREATE INDEX IF NOT EXISTS cards_feed ON cards(lang, version, date DESC);
-- Фильтр по разделу arXiv — второй по частоте после ленты.
CREATE INDEX IF NOT EXISTS cards_cat ON cards(lang, version, primary_category);

-- Поиск по словам. Отдельная таблица, а не content='cards': тело поиска — это НЕ то,
-- что лежит в карточке. Туда идут ещё и abstract с threads, которых на карточке нет
-- и которые ради этого поиска сейчас едут читателю в браузер (30% и 12% веса индекса).
--
-- Токенизатор unicode61, потому что ICU в D1 не существует — вариантов ровно четыре:
-- unicode61, ascii, porter, trigram. remove_diacritics 2 снимает комбинируемые знаки
-- (важно для арабских огласовок и французских акцентов).
--
-- В body кладём НОРМАЛИЗОВАННЫЙ текст (см. cards_build.py: norm_text). Для арабского
-- это не украшение, а условие работоспособности: артикль «ال» и клитики пишутся слитно,
-- и без нормализации читатель, набравший «فيزياء», не найдёт «الفيزياء» — поиск был бы
-- формально исправен и фактически бесполезен. Запрос в Worker нормализуется ТЕМ ЖЕ
-- преобразованием; если поменять одно и забыть второе, поиск замолчит без ошибки.
CREATE VIRTUAL TABLE IF NOT EXISTS cards_fts USING fts5(
  body,
  id       UNINDEXED,
  lang     UNINDEXED,
  version  UNINDEXED,
  tokenize = "unicode61 remove_diacritics 2"
);

-- Чем наполнено и когда — чтобы сборка видела, что уже залито, и не гоняла 32 тысячи
-- строк каждый раз.
CREATE TABLE IF NOT EXISTS cards_state (
  key     TEXT PRIMARY KEY,   -- lang/version
  hash    TEXT,               -- md5 содержимого, по нему решаем, нужно ли перезаливать
  rows    INTEGER,
  updated TEXT
);
