// bridge42worlds · движок вовлечения: реакции + избранное (localStorage) + обратная связь.
//
// Реакции и отклики живут в НАШЕЙ базе, через наши ручки /api/react и /api/article-feedback
// (переезд с Supabase, 2026-08-01). Раньше здесь лежал ключ доступа к чужой базе — открытым
// текстом, на виду у всякого, кто откроет исходник страницы: писать в неё мог кто угодно
// и сколько угодно, а счётчик накручивался повторным нажатием. Теперь браузер не знает
// никаких ключей вообще, запись идёт через сервер, и там же стоит правило «один человек —
// одна реакция».
//
// Просмотры отсюда ушли совсем: их считает js/metrics.js своим счётчиком.
const REACTIONS = ['like', 'dislike', 'superlike']   // superlike рисуется в ленте — без него его счётчик был локальной фикцией;

const _lock = new Set();   // замок ПО ID: глобальный терял тап по соседней карточке

// Одна дверь наружу на весь модуль. Сеть может не ответить — тогда молчим и не ломаем
// страницу: реакция уже показана оптимистично, а счётчик подтянется при следующем заходе.
async function api(path, opts) {
    try {
        const r = await fetch(path, Object.assign({ headers: { 'content-type': 'application/json' } }, opts || {}));
        return r.ok ? await r.json() : null;
    } catch (e) { return null; }
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
    // Один запрос на все три реакции вместо трёх: раньше открытие страницы стоило
    // три обращения к чужой базе, теперь одно к своей — и оно кэшируется на минуту.
    const d = await api(`/api/react?id=${encodeURIComponent(id)}`);
    if (!d) return;
    for (const type of REACTIONS) {
        document.querySelectorAll(`[data-article-id="${id}"] [data-react="${type}"] .rc`)
            .forEach(el => el.textContent = (d.counts && d.counts[type]) || 0);
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
    if (_lock.has(id)) return;
    _lock.add(id);
    // Замок 350 мс защищал от дребезга, но НЕ от осмысленных повторных тапов: читатель
    // жал «нравится» много раз подряд и видел +1, −1, +2… (владелец, живой телефон
    // 2026-07-30). Сервер при этом получал по строке на каждый тап. Одна реакция на
    // статью с одного устройства — это и есть смысл кнопки: повторный тап по УЖЕ активной
    // снимает её, а дальнейшие быстрые тапы игнорируются до подтверждения записи.
    /* Ждать сеть можно, а мешать читателю — нет. Замок стоял на СТАТЬЕ целиком,
       поэтому пока уходил «дизлайк», нажатие «нравится» молча терялось: кнопка
       выглядела сломанной (владелец 30.08: «дизлайк должен снимать лайк… нажимаешь
       лайк — опять идёт дизлайк»). Состояние у нас местное и мгновенное, сеть
       догоняет; блокируем только ПОВТОР ТОЙ ЖЕ реакции, а смену — никогда. */
    if (_pending.has(id) && myReaction(id) === type) { _lock.delete(id); return; }
    _pending.add(id);
    // ОПТИМИСТИЧНО: отклик СРАЗУ, до сети (юзер 2026-07-25: «нажал — получил», а поход
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
    setTimeout(() => { _lock.delete(id); }, 350);
    // фоновая запись + тихая ресинхронизация счётчиков с сервером (не блокирует UI)
    try {
        if (!wasActive) {
            const d = await api('/api/react', {
                method: 'POST',
                body: JSON.stringify({ id, reaction: type, entityType: entityType || 'article' }),
            });
            if (!d) {
                // Не сохранилось — откатываем то, что показали оптимистично. Счётчик,
                // который вырос только в глазах читателя, врёт ему и нам.
                setMyReaction(id, prev || '');
                bumpCount(id, type, -1);
                if (prev) bumpCount(id, prev, +1);
                highlightReactions(id);
            }
        }
        // После СНЯТИЯ не перечитываем: удаления на сервере нет, он вернёт прежнее число
        // и счётчик отскочит вверх — тот самый «прыгающий счётчик».
        if (!wasActive) loadReactions(id);
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
    const sent = await api('/api/article-feedback', {
        method: 'POST',
        body: JSON.stringify({
            id, options: opts, comment: comment || null,
            entityType: entityType || 'article',
            lang: document.documentElement.lang || '',
        }),
    });
    const error = sent ? null : true;
    const status = box.querySelector('.fb-status');
    // Статус отклика — ЛОКАЛИЗОВАН (был русский хардкод на всех языках, юзер 2026-07-25).
    const FB_MSG = {
        ru: { ok: '✓ спасибо!', err: '⚠ не отправлено' },
        en: { ok: '✓ thank you!', err: '⚠ not sent' },
        es: { ok: '✓ ¡gracias!', err: '⚠ no enviado' },
        ar: { ok: '✓ شكرًا لك!', err: '⚠ لم يُرسل' },
        zh: { ok: '✓ 谢谢！', err: '⚠ 未发送' }
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

// Просмотры считает js/metrics.js (событие view в нашу базу), поэтому здесь их больше нет.
// Функцию оставляем пустой заглушкой, а не удаляем: её зовут из шаблонов страниц, и молча
// исчезнувшее имя уронило бы страницу целиком ради того, чего мы и так больше не пишем.
function logPageView() { /* просмотры ушли в js/metrics.js */ }
window.logPageView = logPageView;

// Клик на «заблокированную» вкладку экспресс-статьи (advanced/popular ещё не сгенерены) —
// сигнал интереса, чтобы приоритизировать апгрейд до полной версии (run.py regen <id>).
// Этот сигнал НЕ выбрасываем вместе с просмотрами: он не про посещаемость, а про спрос —
// по нему решают, какую экспресс-статью поднять до полной. Шлём его нашим же счётчиком
// событием click, чтобы он попал в общую статистику и был виден на дашборде.
function logExpressInterest(entityId, lang) {
    try {
        if (window.b42Metrics && window.b42Metrics.send) {
            window.b42Metrics.send('click', 'express_locked:' + entityId);
        }
    } catch (e) {}
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
