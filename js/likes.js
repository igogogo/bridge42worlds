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

async function react(id, type, entityType) {
    if (_lock) return;
    _lock = true;
    try {
        const sb = await getSupabase();
        if (myReaction(id) === type) {
            setMyReaction(id, '');                       // снять выбор (строку в БД не удаляем — anon без RLS)
        } else {
            const { error } = await sb.from('likes').insert({
                article_id: id, reaction: type, entity_type: entityType || 'article',
                user_key: getUserKey(), device: deviceType(),
            });
            if (!error) setMyReaction(id, type);
        }
        highlightReactions(id);
        await loadReactions(id);
    } finally { setTimeout(() => { _lock = false; }, 700); }
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
        const ic = b.querySelector('.fav-ic'); if (ic) ic.textContent = on ? '★' : '☆';
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
        user_key: getUserKey(), device: deviceType(),
    });
    const status = box.querySelector('.fb-status');
    if (status) status.textContent = error ? '⚠️ не отправлено' : '✓ спасибо!';
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
        const wrap = ct.closest('.feedback');
        const ta = wrap?.querySelector('.fb-comment');
        const row = wrap?.querySelector('.fb-row');
        if (ta) {
            const show = ta.style.display === 'none';
            ta.style.display = show ? 'block' : 'none';
            if (row) row.hidden = !show;
            if (show) ta.focus();
        }
        return;
    }
    const send = e.target.closest('.fb-send');
    if (send) { const h = send.closest('[data-article-id]'); if (h) submitFeedback(h.dataset.articleId, send.closest('.feedback'), h.dataset.entityType); }
});

document.addEventListener('DOMContentLoaded', () => bindEngagement(document));
