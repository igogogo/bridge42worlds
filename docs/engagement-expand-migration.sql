-- bridge42worlds · расширение вовлечения на теги/законы/учёных + аналитика посещений
-- ─────────────────────────────────────────────────────────────────────────────
-- Сервис: Supabase (Postgres 15+), проект gyfdyfbuolnciaqxgybx. НЕ деструктивно
-- (только ADD COLUMN IF NOT EXISTS / CREATE TABLE IF NOT EXISTS) — старые данные не трогает.
-- Запусти целиком в Supabase → SQL Editor. Идемпотентно (можно гонять повторно).
--
-- Что меняется:
--   1) likes/feedback получают entity_type (article|tag|law|scientist), default 'article'
--      — старые строки (все статьи) остаются валидными без миграции данных.
--   2) article_id остаётся общим полем-ключом (composite id) для ЛЮБОЙ сущности:
--      статьи — "{arxiv_id}_{lang}_{version}" (как было),
--      теги/законы/учёные — "{entity_id}_{lang}_page" (page — заглушка вместо версии,
--      т.к. у справочных страниц нет уровней simple/popular/advanced как у статей).
--      Автовычисляемые base_id/lang/version продолжают работать без изменений (просто
--      "version" для справочников всегда будет = 'page').
--   3) likes/feedback ТАКЖЕ получают user_key/device (как views) — чтобы на этапе апробации
--      видеть КТО поставил конкретную реакцию/оставил конкретный комментарий, не только
--      факт посещения. Старые строки — user_key/device = null (до миграции их не было).
--   4) Новая таблица views — лёгкая аналитика посещений (не каждое действие, только переходы):
--      entity_id/entity_type/lang/source, анонимный user_key (UUID в localStorage),
--      грубый device (mobile/desktop по user-agent). Для этапа апробации — разделять тестировщиков.
-- ─────────────────────────────────────────────────────────────────────────────

-- 1) entity_type + user_key/device на существующих таблицах ────────────────────
alter table public.likes
  add column if not exists entity_type text not null default 'article';
alter table public.likes drop constraint if exists likes_entity_type_chk;
alter table public.likes
  add constraint likes_entity_type_chk check (entity_type in ('article', 'tag', 'law', 'scientist'));
alter table public.likes
  add column if not exists user_key text,
  add column if not exists device   text;
create index if not exists likes_entity_type_idx on public.likes (entity_type);
create index if not exists likes_user_idx        on public.likes (user_key);

alter table public.feedback
  add column if not exists entity_type text not null default 'article';
alter table public.feedback drop constraint if exists feedback_entity_type_chk;
alter table public.feedback
  add constraint feedback_entity_type_chk check (entity_type in ('article', 'tag', 'law', 'scientist'));
alter table public.feedback
  add column if not exists user_key text,
  add column if not exists device   text;
create index if not exists feedback_entity_type_idx on public.feedback (entity_type);
create index if not exists feedback_user_idx        on public.feedback (user_key);

-- 2) Таблица просмотров (аналитика, апробация) ─────────────────────────────────
create table if not exists public.views (
  id          bigint generated always as identity primary key,
  entity_id   text not null,
  entity_type text not null default 'article' check (entity_type in ('article', 'tag', 'law', 'scientist')),
  lang        text,
  source      text,                 -- 'page' (открыл страницу) | 'card' (карточка в ленте) | 'list' (список)
  user_key    text,                 -- анонимный UUID из localStorage (b42_uid) — различать тестировщиков
  device      text,                 -- 'mobile' | 'desktop' (грубо, по user-agent)
  created_at  timestamptz not null default now()
);
create index if not exists views_entity_idx  on public.views (entity_type, entity_id);
create index if not exists views_user_idx    on public.views (user_key);
create index if not exists views_created_idx on public.views (created_at);

alter table public.views enable row level security;
drop policy if exists views_insert_anon on public.views;
create policy views_insert_anon on public.views for insert to anon with check (true);
drop policy if exists views_select_anon on public.views;
create policy views_select_anon on public.views for select to anon using (true);

-- 4) Проверка/аналитика ─────────────────────────────────────────────────────────
--   -- реакции по типу сущности:
--   select entity_type, reaction, count(*) from public.likes group by entity_type, reaction order by 1,2;
--   -- фидбэк по типу сущности:
--   select entity_type, unnest(options) opt, count(*) n from public.feedback group by entity_type, opt order by n desc;
--   -- просмотры по дням/устройству:
--   select date_trunc('day', created_at) d, device, count(*) from public.views group by 1,2 order by 1 desc;
--   -- уникальные тестировщики (по user_key) и сколько страниц каждый посмотрел:
--   select user_key, count(*) n, count(distinct entity_id) entities from public.views
--     where user_key is not null group by user_key order by n desc limit 50;
--   -- КТО конкретно поставил реакции (по тестировщику):
--   select user_key, device, article_id, reaction, created_at from public.likes
--     where user_key is not null order by created_at desc limit 100;
--   -- КТО оставил комментарии (по тестировщику):
--   select user_key, device, article_id, options, comment, created_at from public.feedback
--     where comment is not null and comment <> '' order by created_at desc limit 100;
--   -- Профиль одного тестировщика (все его действия): замени 'XXX' на user_key
--   --   select 'view' kind, entity_type, entity_id, created_at from public.views where user_key='XXX'
--   --   union all select 'like', entity_type, article_id, created_at from public.likes where user_key='XXX'
--   --   union all select 'feedback', entity_type, article_id, created_at from public.feedback where user_key='XXX'
--   --   order by created_at;
-- ─────────────────────────────────────────────────────────────────────────────
