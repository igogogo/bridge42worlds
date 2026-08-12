/* «Перевести эту статью» на заглушке непереведённой статьи.
 *
 * Раньше заглушка только извинялась и предлагала сменить язык. Очередь заказов (D1, DevOps)
 * уже принимает kind=translate, поэтому читателю можно предложить получить перевод прямо
 * сейчас — минута ожидания вместо «приходите потом».
 *
 * Стык с очередью (cloudflare/worker.js, ORDER_KINDS/handleOrder):
 *     POST /api/order   { kind: "translate", payload: { arxiv_id, to } }
 *       → { id, status }                    заказ принят
 *       → { id, status, deduped: true }     кто-то уже просил то же самое — ждём вместе
 *       → { error, dayLeft, weekLeft }      норма исчерпана или вход не выполнен
 *     GET  /api/order/<id> → { status: queued|running|done|error, ahead }
 *
 * Заказы склеиваются по (arxiv_id, to) на стороне Worker, поэтому повторное нажатие никого
 * не наказывает: мы просто присоединяемся к уже идущему переводу. В интерфейсе держим то же
 * поведение — кнопка после нажатия превращается в ожидание, а не во вторую кнопку.
 */
(function () {
    'use strict';

    var box = document.querySelector('.translate-offer');
    if (!box) return;                       // страница переведена — предлагать нечего

    var LANG = document.documentElement.lang || 'ru';
    var T = {
        ru: { offer: 'Перевести эту статью сейчас', hint: 'Обычно занимает около минуты',
              queued: 'Заказ принят, ждём очереди', running: 'Переводим…',
              ahead: 'перед вами в очереди', done: 'Готово — обновите страницу',
              reload: 'Обновить', already: 'Эта статья уже переводится — подождите вместе со всеми',
              limit: 'На сегодня заказы закончились. Норма обновится завтра.',
              noAuth: 'Чтобы заказать перевод, нужно войти',
              captcha: 'Не прошла проверка «не робот». Обновите страницу и попробуйте ещё раз.',
              tooFast: 'Слишком много запросов подряд — подождите минуту.',
              offline: 'Очередь сейчас недоступна. Статья доступна на других языках.',
              failed: 'Перевести не получилось. Попробуйте позже.' },
        en: { offer: 'Translate this article now', hint: 'Usually takes about a minute',
              queued: 'Order accepted, waiting in queue', running: 'Translating…',
              ahead: 'ahead of you in the queue', done: 'Done — reload the page',
              reload: 'Reload', already: 'This article is already being translated — wait along with others',
              limit: 'No orders left today. The allowance resets tomorrow.',
              noAuth: 'Sign in to order a translation',
              captcha: 'The “not a robot” check failed. Reload the page and try again.',
              tooFast: 'Too many requests in a row — wait a minute.',
              offline: 'The queue is unavailable right now. The article is available in other languages.',
              failed: 'Translation failed. Please try later.' },
        es: { offer: 'Traducir este artículo ahora', hint: 'Suele tardar alrededor de un minuto',
              queued: 'Pedido aceptado, esperando turno', running: 'Traduciendo…',
              ahead: 'delante de usted en la cola', done: 'Listo: recargue la página',
              reload: 'Recargar', already: 'Este artículo ya se está traduciendo: espere junto a los demás',
              limit: 'No quedan pedidos hoy. El cupo se renueva mañana.',
              noAuth: 'Inicie sesión para pedir una traducción',
              captcha: 'La verificación «no soy un robot» falló. Recargue la página e inténtelo de nuevo.',
              tooFast: 'Demasiadas solicitudes seguidas: espere un minuto.',
              offline: 'La cola no está disponible ahora. El artículo está disponible en otros idiomas.',
              failed: 'No se pudo traducir. Inténtelo más tarde.' },
        ar: { offer: 'ترجم هذه المقالة الآن', hint: 'يستغرق عادة نحو دقيقة',
              queued: 'تم قبول الطلب، في انتظار الدور', running: 'جارٍ الترجمة…',
              ahead: 'أمامك في الطابور', done: 'تم — أعد تحميل الصفحة',
              reload: 'إعادة التحميل', already: 'هذه المقالة قيد الترجمة بالفعل — انتظر مع الآخرين',
              limit: 'لا طلبات متبقية اليوم. تتجدد الحصة غدًا.',
              noAuth: 'سجّل الدخول لطلب الترجمة',
              captcha: 'فشل التحقق من «لست روبوتًا». أعد تحميل الصفحة وحاول مجددًا.',
              tooFast: 'طلبات كثيرة متتالية — انتظر دقيقة.',
              offline: 'الطابور غير متاح الآن. المقالة متاحة بلغات أخرى.',
              failed: 'تعذّرت الترجمة. حاول لاحقًا.' },
        fr: { offer: 'Traduire cet article maintenant', hint: 'Prend en général une minute',
              queued: 'Commande acceptée, en file d’attente', running: 'Traduction en cours…',
              ahead: 'devant vous dans la file', done: 'Terminé — rechargez la page',
              reload: 'Recharger', already: 'Cet article est déjà en cours de traduction — patientez avec les autres',
              limit: 'Plus de commandes aujourd’hui. Le quota se renouvelle demain.',
              noAuth: 'Connectez-vous pour commander une traduction',
              captcha: 'La vérification « je ne suis pas un robot » a échoué. Rechargez la page et réessayez.',
              tooFast: 'Trop de requêtes d’affilée — patientez une minute.',
              offline: 'La file est indisponible. L’article existe dans d’autres langues.',
              failed: 'La traduction a échoué. Réessayez plus tard.' }
    };
    var L = T[LANG] || T.en;

    var arxivId = box.dataset.arxivId || '';
    var to = box.dataset.to || LANG;
    if (!arxivId) return;

    function say(text, withReload) {
        box.innerHTML = '';
        var p = document.createElement('div');
        p.className = 'translate-state';
        p.textContent = text;
        box.appendChild(p);
        if (withReload) {
            var b = document.createElement('button');
            b.type = 'button';
            b.className = 'translate-btn';
            b.textContent = L.reload;
            b.onclick = function () { location.reload(); };
            box.appendChild(b);
        }
    }

    var timer = null, tries = 0;

    function poll(id) {
        // Опрашиваем редко и не бесконечно: перевод статьи занимает около минуты, а вечный
        // таймер на брошенной вкладке — это запросы, за которые платим мы.
        if (++tries > 40) { say(L.queued); return; }
        fetch('/api/order/' + encodeURIComponent(id))
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (d) {
                if (!d) { say(L.offline); return; }
                if (d.status === 'done') { say(L.done, true); return; }
                // Очередь пишет 'failed' и 'rejected' (schema-queue.sql), а не 'error':
                // из-за расхождения провалившийся заказ показывался читателю как
                // «ждём очереди» до конца опроса — сорок раз по три секунды впустую.
                if (d.status === 'failed' || d.status === 'rejected' || d.status === 'error') {
                    say(L.failed); return;
                }
                if (d.status === 'running') say(L.running);
                else say(L.queued + (d.ahead ? ' · ' + d.ahead + ' ' + L.ahead : ''));
                timer = setTimeout(function () { poll(id); }, 3000);
            })
            .catch(function () { say(L.offline); });
    }

    // Помощник подключён в шаблоне статьи, но уже СОБРАННЫЕ страницы тега <script> не имеют —
    // догружаем сами, чтобы починка работала сразу после выкладки js, без пересборки 42к страниц.
    function loadHelper() {
        if (window.b42TurnstilePass) return Promise.resolve(true);
        return new Promise(function (resolve) {
            var s = document.createElement('script');
            s.src = '/js/b42-turnstile.js';
            s.onload = function () { resolve(true); };
            s.onerror = function () { resolve(false); };
            document.head.appendChild(s);
        });
    }

    async function order() {
        say(L.queued);
        // Пропуск «не робот» обязателен: handleOrder отказывает без него ВСЕГДА
        // (fail-closed). Кнопка без пропуска не могла сработать никогда — блокер QA
        // 2026-07-31. Помощник общий (js/b42-turnstile.js); нет его или пропуска —
        // шлём пусто, сервер откажет честным captcha_failed, и мы его покажем.
        await loadHelper();
        var pass = window.b42TurnstilePass ? await window.b42TurnstilePass() : '';
        fetch('/api/order', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ kind: 'translate', lang: to, turnstile: pass,
                                   payload: { arxiv_id: arxivId, to: to } })
        }).then(function (r) {
            return r.json().catch(function () { return null; });
        }).then(function (d) {
            if (!d) { say(L.offline); return; }
            // Коды сервера (worker.js): day_limit / week_limit / project_limit /
            // captcha_failed / too_fast. Раньше клиент ловил только свои выдуманные
            // (quota_exceeded, no_token…) — пересечение было пустым, и любой отказ
            // выглядел как «очередь недоступна». Старые коды оставлены на всякий случай.
            var e = d.error;
            if (e === 'day_limit' || e === 'week_limit' || e === 'project_limit' ||
                e === 'quota_exceeded' || e === 'limit') { say(L.limit); return; }
            if (e === 'captcha_failed') { say(L.captcha, true); return; }
            if (e === 'too_fast') { say(L.tooFast); return; }
            if (e === 'no_token' || e === 'unauthorized') { say(L.noAuth); return; }
            if (e) { say(L.offline); return; }
            if (d.deduped) say(L.already);
            if (d.id) poll(d.id);
        }).catch(function () { say(L.offline); });
    }

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'translate-btn';
    btn.textContent = L.offer;
    btn.onclick = order;
    var hint = document.createElement('div');
    hint.className = 'translate-hint';
    hint.textContent = L.hint;
    box.appendChild(btn);
    box.appendChild(hint);

    window.addEventListener('pagehide', function () { if (timer) clearTimeout(timer); });
})();
