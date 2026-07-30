// bridge42worlds · движок вовлечения: реакции (Supabase) + избранное (localStorage) + обратная связь (Supabase)
const SUPABASE_URL = 'https://gyfdyfbuolnciaqxgybx.supabase.co';
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd5ZmR5ZmJ1b2xuY2lhcXhneWJ4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI3OTk0MzQsImV4cCI6MjA5ODM3NTQzNH0.rKsgWoj5ubRpkvElPfELOn-G9StW5RSOkxBbpvFyWc4';
const REACTIONS = ['like', 'dislike'];

let _sb = null, _lock = false;
async function getSupabase() {
    if (_sb) return _sb;
    const { createClient } = await import('https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm');
    _sb = createClient(SUPABASE_URL, SUPABASE_KEY);
    return _sb;
}

// Таблицы likes/feedback: колонок user_key/device в них НЕТ (есть только у views), а version/lang/
// base_id — GENERATED (БД вычисляет их из article_id сама, вставлять нельзя). Раньше react()/
// submitFeedback вставляли user_key/device → insert падал, лайки и комменты молча не сохранялись
// (баг найден 2026-07-24). Пишем ТОЛЬКО базовые колонки {article_id, reaction/options/comment,
// entity_type}; остальное БД проставит сама.

// ── Реакции: like / dislike / superlike ─────────────────────────────────────
function myReaction(id) { try { return localStorage.getItem('react_' + id) || ''; } catch { return ''; } }
function setMyReaction(id, v) { try { v ? localStorage.setItem('react_' + id, v) : localStorage.removeItem('react_' + id); } catch {} }

function highlightReactions(id) {
    const cur = myReaction(id);
    document.querySelectorAll(`[data-article-id="${id}"] [data-react]`).forEach(b =>
        b.classList.toggle('active', b.dataset.react === cur));
}

async function loadReactions(id) {
    if (!document.querySelector(`[data-article-id="${id}"] [data-react] .rc`)) return; // на карточках счётчиков нет — не дёргаем сеть
    const sb = await getSupabase();
    for (const type of REACTIONS) {
        const { count } = await sb.from('likes').select('*', { count: 'exact', head: true })
            .eq('article_id', id).eq('reaction', type);
        document.querySelectorAll(`[data-article-id="${id}"] [data-react="${type}"] .rc`)
            .forEach(el => el.textContent = count || 0);
    }
}

// Мгновенно двигаем видимый счётчик (оптимистично, до ответа сервера).
function bumpCount(id, type, delta) {
    document.querySelectorAll(`[data-article-id="${id}"] [data-react="${type}"] .rc`).forEach(el => {
        el.textContent = Math.max(0, (parseInt(el.textContent, 10) || 0) + delta);
    });
}

const _pending = new Set();   // id, по которым запись в фоне ещё не завершилась

async function react(id, type, entityType) {
    if (_lock) return;
    _lock = true;
    // Замок 350 мс защищал от дребезга, но НЕ от осмысленных повторных тапов: читатель
    // жал «нравится» много раз подряд и видел +1, −1, +2… (владелец, живой телефон
    // 2026-07-30). Сервер при этом получал по строке на каждый тап. Одна реакция на
    // статью с одного устройства — это и есть смысл кнопки: повторный тап по УЖЕ активной
    // снимает её, а дальнейшие быстрые тапы игнорируются до подтверждения записи.
    if (_pending.has(id)) { _lock = false; return; }
    _pending.add(id);
    // ОПТИМИСТИЧНО: отклик СРАЗУ, до сети (юзер 2026-07-25: «нажал — получил», а загрузка supabase
    // с CDN + insert + повторный запрос счётчика раньше давали заметную задержку). Сеть — в фоне.
    const wasActive = myReaction(id) === type;
    const prev = myReaction(id);
    if (wasActive) {
        setMyReaction(id, '');
        bumpCount(id, type, -1);
    } else {
        if (prev) bumpCount(id, prev, -1);       // визуально снимаем прошлую реакцию
        setMyReaction(id, type);
        bumpCount(id, type, +1);
    }
    highlightReactions(id);
    setTimeout(() => { _lock = false; }, 350);
    // фоновая запись + тихая ресинхронизация счётчиков с сервером (не блокирует UI)
    try {
        const sb = await getSupabase();
        if (!wasActive) {
            const { error } = await sb.from('likes').insert({
                article_id: id, reaction: type, entity_type: entityType || 'article',
            });
            if (error) console.error('like insert failed:', error.message);
        }
        loadReactions(id);   // подтянуть настоящий глобальный счётчик (без await — не тормозим клик)
    } catch (e) { console.error('react bg:', e); }
    finally { _pending.delete(id); }
}

// ── Избранное: только localStorage, без сервера ─────────────────────────────
function getFavorites() { try { return JSON.parse(localStorage.getItem('favorites') || '[]'); } catch { return []; } }
function isFavorite(aid) { return getFavorites().indexOf(aid) !== -1; }
function toggleFavorite(aid) {
    let f = getFavorites();
    const i = f.indexOf(aid);
    if (i === -1) f.push(aid); else f.splice(i, 1);
    try { localStorage.setItem('favorites', JSON.stringify(f)); } catch {}
    updateFavoriteUI(aid);
}
function updateFavoriteUI(aid) {
    const on = isFavorite(aid);
    document.querySelectorAll(`[data-fav="${aid}"]`).forEach(b => {
        b.classList.toggle('active', on);
        const ic = b.querySelector('.fav-ic'); if (ic) ic.innerHTML = on ? '<svg class="ico-svg" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" aria-hidden="true"><path d="M12 3.6l2.45 5 5.5.7-4 3.85 1 5.45-4.95-2.65-4.95 2.65 1-5.45-4-3.85 5.5-.7Z"/></svg>' : '<svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3.6l2.45 5 5.5.7-4 3.85 1 5.45-4.95-2.65-4.95 2.65 1-5.45-4-3.85 5.5-.7Z"/></svg>';
    });
}

// ── Обратная связь: чипы + опциональный комментарий ─────────────────────────
async function submitFeedback(id, wrap, entityType) {
    const box = wrap || document.querySelector(`.feedback[data-article-id="${id}"]`);
    if (!box) return;
    const opts = [...box.querySelectorAll('.fb-chip.active')].map(c => c.dataset.opt);
    const comment = (box.querySelector('.fb-comment')?.value || '').trim();
    if (!opts.length && !comment) return;
    const sb = await getSupabase();
    const { error } = await sb.from('feedback').insert({
        article_id: id, options: opts, comment: comment || null, entity_type: entityType || 'article',
    });
    if (error) console.error('feedback insert failed:', error.message);
    const status = box.querySelector('.fb-status');
    // Статус отклика — ЛОКАЛИЗОВАН (был русский хардкод на всех языках, юзер 2026-07-25).
    const FB_MSG = {
        ru: { ok: '✓ спасибо!', err: '⚠ не отправлено' },
        en: { ok: '✓ thank you!', err: '⚠ not sent' },
        es: { ok: '✓ ¡gracias!', err: '⚠ no enviado' },
        ar: { ok: '✓ شكرًا لك!', err: '⚠ لم يُرسل' }
    };
    const _m = FB_MSG[window.lang] || FB_MSG.en;
    if (status) status.textContent = error ? _m.err : _m.ok;
    if (!error) box.querySelectorAll('.fb-chip.active').forEach(c => c.classList.remove('active'));
    if (!error && box.querySelector('.fb-comment')) box.querySelector('.fb-comment').value = '';
}

// ── Тумблер «сырое ⇄ шлифованное» (видимый чекбокс) ─────────────────────────
let _rawCache = {};
async function toggleRaw(cb) {
    const main = document.querySelector('.article-main, .ref-body');
    if (!main) return;
    if (cb.checked) {
        const url = cb.dataset.rawUrl;
        if (url && !_rawCache[url]) {
            try { _rawCache[url] = await (await fetch(url)).json(); } catch { cb.checked = false; return; }
        }
        const raw = _rawCache[url] || {};
        let box = main.querySelector('.refine-raw');
        if (!box) {
            box = document.createElement('div');
            box.className = 'refine-raw';
            const anchor = main.querySelector('h1') || main.firstElementChild;
            anchor ? anchor.insertAdjacentElement('afterend', box) : main.prepend(box);
        }
        box.textContent = raw.text || raw.description || raw.description_popular || '(нет сырого текста)';
        box.style.display = 'block';
    } else {
        const box = main.querySelector('.refine-raw');
        if (box) box.style.display = 'none';
    }
}

// Сравнение сырое⇄шлифованное для описаний тегов/законов (Unit 4)
function toggleRawDesc(cb) {
    document.querySelectorAll('.desc[data-raw]').forEach(function(el) {
        if (cb.checked) {
            if (el.dataset.refinedText === undefined) el.dataset.refinedText = el.textContent;
            if (el.dataset.raw) el.textContent = el.dataset.raw;
        } else if (el.dataset.refinedText !== undefined) {
            el.textContent = el.dataset.refinedText;
        }
    });
}
window.toggleRawDesc = toggleRawDesc;

// ── Аналитика посещений (этап апробации): анонимный user_key + грубый device ─
function getUserKey() {
    try {
        let k = localStorage.getItem('b42_uid');
        if (!k) {
            k = (crypto.randomUUID ? crypto.randomUUID() : (Date.now() + '-' + Math.random().toString(36).slice(2)));
            localStorage.setItem('b42_uid', k);
        }
        return k;
    } catch { return ''; }
}
function deviceType() { return /Mobi|Android/i.test(navigator.userAgent) ? 'mobile' : 'desktop'; }

// Логируем ТОЛЬКО переходы на страницу сущности (не каждый клик) — вызывается один раз со страницы.
async function logPageView(entityId, entityType, lang) {
    try {
        const sb = await getSupabase();
        await sb.from('views').insert({
            entity_id: entityId, entity_type: entityType || 'article', lang: lang || '',
            source: 'page', user_key: getUserKey(), device: deviceType(),
        });
    } catch {}
}
window.logPageView = logPageView;

// Клик на «заблокированную» вкладку экспресс-статьи (advanced/popular ещё не сгенерены) —
// сигнал интереса, чтобы приоритизировать апгрейд до полной версии (run.py regen <id>).
async function logExpressInterest(entityId, lang) {
    try {
        const sb = await getSupabase();
        await sb.from('views').insert({
            entity_id: entityId, entity_type: 'article', lang: lang || '',
            source: 'express_locked', user_key: getUserKey(), device: deviceType(),
        });
    } catch {}
}
window.logExpressInterest = logExpressInterest;

function shareArticle(title, url) {
    if (navigator.share) navigator.share({ title, url });
    else navigator.clipboard.writeText(url).then(() => alert('Link copied!'));
}

// ── Инициализация + делегирование (работает и для динамических карточек) ─────
function bindEngagement(root) {
    (root || document).querySelectorAll('[data-article-id]').forEach(el => {
        const id = el.dataset.articleId;
        loadReactions(id); highlightReactions(id);
    });
    (root || document).querySelectorAll('[data-fav]').forEach(b => updateFavoriteUI(b.dataset.fav));
}
window.bindEngagement = bindEngagement;

document.addEventListener('click', e => {
    const rb = e.target.closest('[data-react]');
    if (rb) { const h = rb.closest('[data-article-id]'); if (h) { e.preventDefault(); react(h.dataset.articleId, rb.dataset.react, h.dataset.entityType); } return; }
    const fb = e.target.closest('[data-fav]');
    if (fb) { e.preventDefault(); toggleFavorite(fb.dataset.fav); return; }
    const chip = e.target.closest('.fb-chip');
    if (chip) {
        // Клик по варианту отклика шлётся сразу, без отдельной кнопки "отправить" —
        // та нужна только для комментария (юзер-фидбек 2026-07-15: "щёлкнул вариант
        // отзыва — сразу отправляется").
        chip.classList.toggle('active');
        const box = chip.closest('[data-article-id]');
        const wrap = chip.closest('.feedback');
        if (box) submitFeedback(box.dataset.articleId, wrap, box.dataset.entityType);
        return;
    }
    const ct = e.target.closest('.fb-comment-toggle');
    if (ct) {
        // Раскрывает .fb-expand (чипы + поле комментария + отправка) — в покое всё это скрыто,
        // видна только кнопка «+ комментарий» (юзер-фидбек 2026-07-21: убрать перегруз с карточки).
        // Кнопка «+ комментарий» на статье переехала в строку лайков (вне .feedback) — closest
        // там вернёт null, поэтому откатываемся на единственный .feedback страницы.
        const wrap = ct.closest('.feedback') || document.querySelector('.feedback');
        const exp = wrap?.querySelector('.fb-expand');
        if (exp) {
            const show = exp.hidden;
            exp.hidden = !show;
            ct.classList.toggle('open', show);
            if (show) wrap.querySelector('.fb-comment')?.focus();
        }
        return;
    }
    const send = e.target.closest('.fb-send');
    if (send) { const h = send.closest('[data-article-id]'); if (h) submitFeedback(h.dataset.articleId, send.closest('.feedback'), h.dataset.entityType); }
});

document.addEventListener('DOMContentLoaded', () => bindEngagement(document));
