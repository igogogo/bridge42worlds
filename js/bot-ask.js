/* Бот-исследователь: вопрос → ответ по нашим статьям со ссылками.
 *
 * СТЫК. Контур `/api/ask` делает DevOps, промпт и параметры поиска — ML; формат ответа
 * на момент написания письменно не зафиксирован (у ML в задаче он «даётся DevOps»).
 * Чтобы интерфейс не пришлось переписывать из-за расхождения в именах полей, читаю
 * ответ через один разбор, понимающий очевидные варианты. Что ожидается:
 *
 *     POST /api/ask  { q, lang }
 *     → { answer: "текст",
 *         sources: [ { id, title, url, date } ],
 *         left: 7 }                            остаток нормы после этого вопроса
 *     → { error: "no_token" | "limit" | "not_found" | ... }
 *
 * Синонимы, которые тоже приму: answer|text|reply, sources|results|articles,
 * left|remaining|quota_left. Если DevOps назовёт поля иначе, чинить нужно ЗДЕСЬ, в одном
 * месте, а не по всей странице — ровно тот же приём, что со стыком поиска.
 *
 * Главное правило показа: ответ без источников — это НЕ ответ. Бот отвечает только по
 * нашим статьям, поэтому текст без ссылок означает, что в базе темы нет, и мы говорим
 * это прямо. Иначе бот превращается в генератор правдоподобного текста, а читатель
 * не может отличить наше знание от выдумки модели.
 */
(function () {
    'use strict';

    var LANG = window.B42_LANG || 'ru';
    var API = window.B42_ASK_API || '/api/ask';

    var T = {
        ru: { title: 'Спросить', send: 'Спросить', asking: 'Ищу в наших статьях…',
              lead: 'Вопрос по науке — отвечаю только по статьям этого сайта и показываю, откуда взят ответ.',
              placeholder: 'Например: почему чёрные дыры испаряются?',
              sources: 'Источники', left: 'Осталось вопросов сегодня',
              unlimited: 'Норма не ограничена', noToken: 'Чтобы спрашивать, нужно войти',
              limit: 'На сегодня вопросы закончились. Возвращайтесь завтра — норма обновится.',
              nothing: 'В наших статьях этого пока нет.',
              nothingHint: 'Бот отвечает только по нашему архиву, чтобы не выдумывать. Попробуйте поиск по сайту — он ищет и по понятиям.',
              search: 'поиск по сайту', offline: 'Сервис ответов сейчас недоступен. Поиск по сайту работает.',
              empty: 'Напишите вопрос' },
        en: { title: 'Ask', send: 'Ask', asking: 'Searching our articles…',
              lead: 'A science question — I answer only from articles on this site and show where the answer comes from.',
              placeholder: 'For example: why do black holes evaporate?',
              sources: 'Sources', left: 'Questions left today',
              unlimited: 'No limit', noToken: 'Sign in to ask questions',
              limit: 'No questions left today. Come back tomorrow — the allowance resets.',
              nothing: 'Our articles do not cover this yet.',
              nothingHint: 'The bot answers only from our archive, so it does not invent. Try the site search — it also searches concepts.',
              search: 'site search', offline: 'The answer service is unavailable right now. Site search works.',
              empty: 'Type a question' },
        es: { title: 'Preguntar', send: 'Preguntar', asking: 'Buscando en nuestros artículos…',
              lead: 'Una pregunta de ciencia: respondo solo con artículos de este sitio y muestro de dónde sale la respuesta.',
              placeholder: 'Por ejemplo: ¿por qué se evaporan los agujeros negros?',
              sources: 'Fuentes', left: 'Preguntas restantes hoy',
              unlimited: 'Sin límite', noToken: 'Inicie sesión para preguntar',
              limit: 'No quedan preguntas hoy. Vuelva mañana: el cupo se renueva.',
              nothing: 'Nuestros artículos aún no cubren esto.',
              nothingHint: 'El bot responde solo desde nuestro archivo, para no inventar. Pruebe la búsqueda del sitio: también busca conceptos.',
              search: 'búsqueda del sitio', offline: 'El servicio de respuestas no está disponible ahora. La búsqueda funciona.',
              empty: 'Escriba una pregunta' },
        ar: { title: 'اسأل', send: 'اسأل', asking: 'أبحث في مقالاتنا…',
              lead: 'سؤال علمي — أجيب فقط من مقالات هذا الموقع وأبيّن مصدر الإجابة.',
              placeholder: 'مثلاً: لماذا تتبخر الثقوب السوداء؟',
              sources: 'المصادر', left: 'الأسئلة المتبقية اليوم',
              unlimited: 'بلا حد', noToken: 'سجّل الدخول لطرح الأسئلة',
              limit: 'لا أسئلة متبقية اليوم. عُد غدًا — تتجدد الحصة.',
              nothing: 'مقالاتنا لا تغطي هذا بعد.',
              nothingHint: 'يجيب البوت من أرشيفنا فقط كي لا يختلق. جرّب البحث في الموقع — فهو يبحث في المفاهيم أيضًا.',
              search: 'البحث في الموقع', offline: 'خدمة الإجابات غير متاحة الآن. البحث في الموقع يعمل.',
              empty: 'اكتب سؤالاً' },
        fr: { title: 'Demander', send: 'Demander', asking: 'Je cherche dans nos articles…',
              lead: 'Une question scientifique : je réponds uniquement à partir des articles de ce site et je montre la source.',
              placeholder: 'Par exemple : pourquoi les trous noirs s’évaporent-ils ?',
              sources: 'Sources', left: 'Questions restantes aujourd’hui',
              unlimited: 'Sans limite', noToken: 'Connectez-vous pour poser des questions',
              limit: 'Plus de questions aujourd’hui. Revenez demain, le quota se renouvelle.',
              nothing: 'Nos articles ne couvrent pas encore ce sujet.',
              nothingHint: 'Le bot répond uniquement depuis notre archive, pour ne rien inventer. Essayez la recherche du site : elle couvre aussi les notions.',
              search: 'recherche du site', offline: 'Le service de réponses est indisponible. La recherche fonctionne.',
              empty: 'Écrivez une question' }
    };
    var L = T[LANG] || T.en;

    var form = document.getElementById('ask-form');
    var input = document.getElementById('ask-input');
    var send = document.getElementById('ask-send');
    var log = document.getElementById('ask-log');
    var quotaLine = document.getElementById('ask-quota');
    if (!form) return;

    document.getElementById('ask-title').textContent = L.title;
    document.getElementById('ask-lead').textContent = L.lead;
    document.title = L.title + ' — bridge42worlds';
    input.placeholder = L.placeholder;
    send.textContent = L.send;

    function esc(s) {
        return (s == null ? '' : String(s))
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function el(tag, cls, html) {
        var e = document.createElement(tag);
        if (cls) e.className = cls;
        if (html != null) e.innerHTML = html;
        return e;
    }

    /* Разбор ответа — единственное место, знающее имена полей сервера. */
    function parse(data) {
        if (!data || typeof data !== 'object') return null;
        var answer = data.answer || data.text || data.reply || '';
        var src = data.sources || data.results || data.articles || [];
        if (!Array.isArray(src)) src = [];
        var left = data.left;
        if (left == null) left = data.remaining;
        if (left == null) left = data.quota_left;
        return {
            error: data.error || '',
            answer: String(answer || ''),
            left: (typeof left === 'number') ? left : null,
            sources: src.map(function (s) {
                return {
                    id: s.id || '',
                    title: s.title || s.n || s.id || '',
                    url: s.url || '',
                    date: s.date || s.d || ''
                };
            }).filter(function (s) { return s.url || s.id; })
        };
    }

    function showQuota(left) {
        if (left == null) { quotaLine.textContent = ''; return; }
        quotaLine.textContent = L.left + ': ' + left;
        quotaLine.classList.toggle('low', left <= 2);
    }

    function nothingBlock() {
        var searchUrl = '/lang/' + (LANG === 'fr' ? 'en' : LANG) + '/index.html';
        return '<div class="ask-empty"><b>' + esc(L.nothing) + '</b><br>' + esc(L.nothingHint) +
               ' — <a href="' + searchUrl + '">' + esc(L.search) + '</a></div>';
    }

    function addAnswer(res) {
        var box = el('div', 'ask-msg');
        if (res.error === 'no_token' || res.error === 'unauthorized') {
            box.appendChild(el('div', 'ask-state', esc(L.noToken)));
        } else if (res.error === 'limit' || res.error === 'quota_exceeded') {
            box.appendChild(el('div', 'ask-state', esc(L.limit)));
        } else if (!res.sources.length) {
            // Текст без источников не показываем как ответ — см. шапку файла.
            box.innerHTML = nothingBlock();
        } else {
            box.appendChild(el('div', 'ask-a', esc(res.answer)));
            var srcBox = el('div', 'ask-sources');
            srcBox.appendChild(el('div', 'ask-state', esc(L.sources)));
            res.sources.forEach(function (s) {
                var a = el('a', 'ask-src', '<b>' + esc(s.title) + '</b>' +
                          (s.date ? '<i>' + esc(s.date) + '</i>' : ''));
                a.href = s.url || '#';
                srcBox.appendChild(a);
            });
            box.appendChild(srcBox);
        }
        log.appendChild(box);
    }

    var busy = false;

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        var q = (input.value || '').trim();
        if (busy) return;
        if (!q) { input.placeholder = L.empty; return; }

        log.appendChild(el('div', 'ask-msg ask-q', esc(q)));
        var pending = el('div', 'ask-msg ask-state', esc(L.asking));
        log.appendChild(pending);
        busy = true; send.disabled = true;
        input.value = '';

        fetch(API, {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ q: q, lang: LANG })
        }).then(function (r) {
            return r.json().catch(function () { return null; });
        }).then(function (data) {
            pending.remove();
            var res = parse(data);
            if (!res) { log.appendChild(el('div', 'ask-msg ask-state', esc(L.offline))); return; }
            addAnswer(res);
            showQuota(res.left);
        }).catch(function () {
            pending.remove();
            // Сеть или Worker недоступны — говорим прямо и не делаем вид, что ответа нет
            // по существу: это разные вещи для читателя.
            log.appendChild(el('div', 'ask-msg ask-state', esc(L.offline)));
        }).then(function () {
            busy = false; send.disabled = false;
            input.focus();
        });
    });

    /* Остаток нормы показываем ДО первого вопроса — отдельным лёгким запросом, если он есть.
       Молчим, если эндпоинта нет: пустая строка честнее, чем выдуманное число. */
    fetch('/api/quota', { method: 'GET' })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) {
            var res = parse(d);
            if (res) showQuota(res.left);
        })
        .catch(function () { /* нет так нет */ });
})();
