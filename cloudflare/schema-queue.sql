-- Очередь заказов. Один каркас на троих потребителей (решение владельца 2026-07-30):
--   ask       — вопрос боту-исследователю (/api/ask)
--   article   — «хочу статью про это»
--   translate — «переведи эту статью на мой язык»
--
-- Почему одна таблица, а не три. Работа у них разная, а жизненный путь один: приняли заказ →
-- проверили право и остаток → положили в очередь → машина с данными взяла и исполнила →
-- читатель увидел готовое. Три таблицы означали бы три копии этого пути и три места, где
-- он разойдётся. Различия типов живут в поле payload, а не в отдельных схемах.
--
-- Почему D1, а не очередь Cloudflare. Заказ должен быть виден читателю («ваша статья готовится,
-- третья в очереди») и переживать перезапуск исполнителя. Это состояние, а не поток событий.

CREATE TABLE IF NOT EXISTS orders (
  id           TEXT PRIMARY KEY,           -- uuid, его же читатель видит в ссылке на статус
  kind         TEXT NOT NULL,              -- ask | article | translate
  status       TEXT NOT NULL DEFAULT 'queued',
                                           -- queued → running → done | failed | rejected
                                           -- rejected: не взяли (дубль, лимит, не прошло проверку)
  priority     INTEGER NOT NULL DEFAULT 100,
                                           -- меньше = раньше. Заведено сразу, потому что
                                           -- потом это не добавить безболезненно: ask нужен
                                           -- читателю сейчас, article может подождать ночь.

  user_id      TEXT NOT NULL,              -- кто заказал (сессия или id входа)
  lang         TEXT,                       -- язык читателя: на нём отвечаем и переводим

  payload      TEXT NOT NULL,              -- JSON, поля зависят от kind (см. ниже)
  result       TEXT,                       -- JSON с ответом/ссылкой на готовое
  error        TEXT,                       -- человеческая причина отказа, её показываем

  cost         INTEGER NOT NULL DEFAULT 1, -- сколько списано с нормы (ask=1, article дороже)
  attempts     INTEGER NOT NULL DEFAULT 0, -- чтобы вечно падающий заказ не крутился без конца

  created_at   INTEGER NOT NULL,           -- unix-время, миллисекунды
  started_at   INTEGER,
  finished_at  INTEGER,
  dedupe_key   TEXT                        -- см. индекс ниже
);

-- Главная выборка исполнителя: «дай следующий заказ». Сортировка ровно та же, что в индексе,
-- иначе на выросшей очереди это станет полным перебором.
CREATE INDEX IF NOT EXISTS idx_orders_next
  ON orders (status, priority, created_at);

-- Показать читателю его заказы.
CREATE INDEX IF NOT EXISTS idx_orders_user
  ON orders (user_id, created_at DESC);

-- Защита от дублей. Десять человек просят перевести одну и ту же статью на арабский — это
-- один заказ, а не десять оплаченных прогонов модели. Ключ собирает заказчик:
--   article   → 'article:' + нормализованная тема
--   translate → 'translate:' + arxiv_id + ':' + язык
--   ask       → NULL, вопросы не склеиваем: они у всех свои
-- Частичный индекс, потому что NULL нам нужно разрешать многократно.
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_dedupe
  ON orders (dedupe_key)
  WHERE dedupe_key IS NOT NULL AND status IN ('queued', 'running');

-- Что лежит в payload по типам (описание для разработчика и ML — схема одна, поля разные):
--
--   kind = 'ask'
--     { "question": "текст вопроса", "context": "необязательный кусок урока" }
--     result: { "answer": "...", "sources": [{ "id": "2607.13625", "title": "...", "url": "..." }] }
--     Правило проекта: ответ без хотя бы одной ссылки на наш материал не показываем.
--
--   kind = 'article'
--     { "topic": "о чём хочет статью", "hint_arxiv_id": "если читатель указал источник" }
--     result: { "arxiv_id": "...", "url": "..." }
--
--   kind = 'translate'
--     { "arxiv_id": "2607.13625", "to": "ar" }
--     result: { "url": "https://.../lang/ar/archive/..." }
