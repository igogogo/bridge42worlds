-- Реакции читателей и отклики по статьям. Переезд с Supabase (решение владельца).
--
-- Зачем переезжаем: ключ Supabase лежал открытым в js/likes.js — то есть любой, кто открыл
-- исходник страницы, мог писать в нашу базу напрямую. Плюс теперь у нас есть своя база
-- и свой счётчик, и держать ради одиннадцати строк чужой сервис незачем.
--
-- Почему отдельные таблицы, а не в events: события счётчика живут 90 дней и чистятся,
-- а лайк читателя — не событие, а его след. Смешивать их значило бы однажды удалить
-- реакции вместе с посещаемостью.

CREATE TABLE IF NOT EXISTS reactions (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  article_id  TEXT NOT NULL,
  reaction    TEXT NOT NULL,              -- like | mind | heart… (набор задаёт клиент)
  entity_type TEXT NOT NULL DEFAULT 'article',
  uid         TEXT NOT NULL DEFAULT '',   -- обезличенный номер устройства
  ts          INTEGER NOT NULL
);

-- Главная выборка: сколько каких реакций у статьи.
CREATE INDEX IF NOT EXISTS idx_reactions_article ON reactions (article_id, reaction);

-- Один человек — одна реакция данного вида. В Supabase этого не было, и накрутить счётчик
-- можно было простым повторным нажатием. Пустой uid под правило не попадает: старые записи
-- переехали без него, и терять их из-за отсутствия номера неправильно.
CREATE UNIQUE INDEX IF NOT EXISTS idx_reactions_one
  ON reactions (article_id, reaction, uid) WHERE uid <> '';

-- Отклик по статье («что понравилось / что не так» + комментарий). Отдельно от таблицы
-- feedback: та собирает отзывы с плашки предзапуска, это разные вещи с разными полями.
CREATE TABLE IF NOT EXISTS article_feedback (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  article_id  TEXT NOT NULL,
  options     TEXT,                       -- JSON-массив выбранных вариантов
  comment     TEXT,
  entity_type TEXT NOT NULL DEFAULT 'article',
  lang        TEXT NOT NULL DEFAULT '',
  ts          INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_article_feedback ON article_feedback (article_id, ts DESC);
