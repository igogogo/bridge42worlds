/* tutor.js — учебный слой поверх движка explorable.js:
   (1) проверочные вопросы КАЧЕСТВЕННОГО типа (объяснить, а не посчитать) — выбор варианта
       или свой ответ словами; всё решается в уме, без калькулятора;
   (2) итоговая оценка знаний + рекомендация, куда копать дальше;
   (3) бот-тьютор: спросить в контексте раздела/вопроса. При неверном ответе бот НЕ выдаёт
       правильный, а ведёт к идее (см. system prompt в cloudflare/worker.js, режим hint).

   Без ключа DeepSeek (локально) бот честно уходит в демо-режим и показывает заготовленную
   подсказку из JSON статьи — UX виден целиком, но подменять живой ответ мы не притворяемся. */
(function (global) {
    'use strict';

    var STYLE_ID = 'b42-tutor-style';
    var CSS = [
        '.tq{max-width:620px;margin:18px 0;padding:14px 16px;border:1px solid var(--border);border-radius:12px;background:var(--bg)}',
        '.tq-q{font-size:15px;line-height:1.6;color:var(--text);margin-bottom:10px}',
        '.tq-q b{font-weight:600}',
        '.tq-opts{display:flex;flex-direction:column;gap:6px}',
        '.tq-opt{text-align:left;font:inherit;font-size:14px;line-height:1.5;padding:8px 12px;border-radius:9px;cursor:pointer;',
        'background:none;border:1px solid var(--border);color:var(--text);transition:all .15s}',
        '.tq-opt:hover:not(:disabled){border-color:var(--link);color:var(--link)}',
        '.tq-opt:disabled{cursor:default}',
        '.tq-opt.right{border-color:#2e7d32;background:rgba(46,125,50,.10);color:var(--text)}',
        '.tq-opt.wrong{border-color:var(--red);background:rgba(179,27,27,.08);color:var(--text)}',
        '.tq-free{display:flex;gap:6px;margin-top:4px}',
        '.tq-free textarea{flex:1;min-height:56px;resize:vertical;font:inherit;font-size:14px;padding:8px 10px;',
        'border:1px solid var(--border);border-radius:9px;background:var(--bg);color:var(--text)}',
        '.tq-send{align-self:flex-end;font-size:13px;padding:7px 14px;border-radius:9px;cursor:pointer;',
        'background:var(--link);color:#fff;border:none}',
        '.tq-fb{margin-top:10px;font-size:13.5px;line-height:1.6;padding:10px 12px;border-radius:9px}',
        '.tq-fb.ok{background:rgba(46,125,50,.10);color:var(--text)}',
        '.tq-fb.no{background:rgba(179,27,27,.07);color:var(--text)}',
        /* Подсказка про формат ввода — это не вердикт: она не красит ответ ни в зелёный,
           ни в красный, потому что читатель ещё не ответил. */
        '.tq-tip{margin-top:8px;font-size:12.5px;line-height:1.7;color:var(--soft)}',
        '.tq-tip code{font-family:var(--mono,monospace);font-size:12px;background:var(--tag-bg);',
        'padding:1px 6px;border-radius:5px;margin:0 2px;white-space:nowrap}',
        '.tq-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}',
        '.tq-ask{font-size:12.5px;padding:5px 12px;border-radius:14px;cursor:pointer;background:none;',
        'border:1px solid var(--border);color:var(--soft)}',
        '.tq-ask:hover{border-color:var(--link);color:var(--link)}',
        '.tq-score{max-width:620px;margin:22px 0;padding:18px 20px;border-radius:14px;background:var(--tag-bg);border:1px solid var(--border)}',
        '.tq-score h3{font-size:18px;margin-bottom:8px;font-family:"Source Serif 4",Georgia,serif}',
        '.tq-score-bar{height:8px;border-radius:4px;background:var(--border);overflow:hidden;margin:10px 0}',
        '.tq-score-fill{height:100%;background:var(--link);transition:width .6s ease}',
        '.tq-score p{font-size:14px;line-height:1.65;color:var(--muted);margin:8px 0 0}',
        /* ── чат-бот ── */
        '.tb-fab{position:fixed;right:20px;bottom:20px;z-index:900;width:52px;height:52px;border-radius:50%;',
        'background:var(--link);color:#fff;border:none;cursor:pointer;font-size:22px;box-shadow:0 4px 16px rgba(0,0,0,.22)}',
        '.tb-panel{position:fixed;right:20px;bottom:20px;z-index:901;width:min(380px,calc(100vw - 32px));',
        'max-height:min(560px,calc(100vh - 40px));display:none;flex-direction:column;border-radius:16px;',
        'background:var(--bg);border:1px solid var(--border);box-shadow:0 8px 34px rgba(0,0,0,.24);overflow:hidden}',
        '.tb-panel.open{display:flex}',
        '.tb-head{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:11px 14px;border-bottom:1px solid var(--border)}',
        '.tb-title{font-size:13.5px;font-weight:600;color:var(--text)}',
        '.tb-ctx{font-size:11px;color:var(--soft);margin-top:1px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:250px}',
        '.tb-close{background:none;border:none;font-size:20px;line-height:1;cursor:pointer;color:var(--soft)}',
        '.tb-body{flex:1;overflow-y:auto;padding:12px 14px;display:flex;flex-direction:column;gap:10px}',
        '.tb-msg{font-size:13.5px;line-height:1.6;padding:9px 12px;border-radius:12px;max-width:88%;white-space:pre-wrap}',
        '.tb-msg.me{align-self:flex-end;background:var(--link);color:#fff;border-bottom-right-radius:4px}',
        '.tb-msg.bot{align-self:flex-start;background:var(--tag-bg);color:var(--text);border-bottom-left-radius:4px}',
        '.tb-msg.sys{align-self:center;font-size:11.5px;color:var(--soft);background:none;text-align:center}',
        '.tb-foot{display:flex;gap:6px;padding:10px 12px;border-top:1px solid var(--border)}',
        '.tb-foot textarea{flex:1;min-height:38px;max-height:110px;resize:none;font:inherit;font-size:13.5px;',
        'padding:8px 10px;border:1px solid var(--border);border-radius:10px;background:var(--bg);color:var(--text)}',
        '.tb-foot button{align-self:flex-end;background:var(--link);color:#fff;border:none;border-radius:10px;',
        'padding:9px 14px;font-size:13px;cursor:pointer}',
        '@media(max-width:640px){.tb-panel{right:8px;left:8px;width:auto;bottom:8px}.tb-fab{right:14px;bottom:14px}}',
        /* ── Доводка вида по мокапу задачи «диалог бота» (задачи/мокапы/бот-диалог.html) ── */
        /* Знак у реплик бота: чей это пузырь, раньше читалось только по цвету и стороне,
           а на тёмной теме форма различается надёжнее цвета. */
        '.tb-msg.bot{position:relative;margin-left:26px}',
        '.tb-msg.bot::before{content:"";position:absolute;left:-26px;top:2px;width:18px;height:18px;',
        'background-color:var(--link);opacity:.75;-webkit-mask:var(--tb-ic-chat) center/contain no-repeat;',
        'mask:var(--tb-ic-chat) center/contain no-repeat}',
        /* Остаток вопросов — тихой строкой в шапке. Системной репликой он уезжал вверх
           при первой же прокрутке, то есть исчезал именно тогда, когда становился важен. */
        '.tb-quota{font-family:var(--mono,monospace);font-size:10.5px;color:var(--soft);margin-top:3px}',
        '.tb-quota:empty{display:none}',
        /* «Думаю…» словом читалось как ещё одна реплика бота — три точки однозначнее. */
        '.tb-typing{align-self:flex-start;display:flex;gap:4px;padding:11px 14px;background:var(--tag-bg);',
        'border-radius:12px;border-bottom-left-radius:4px}',
        '.tb-typing i{width:6px;height:6px;border-radius:50%;background:var(--soft);display:block;',
        'animation:tbDot 1.2s infinite ease-in-out}',
        '.tb-typing i:nth-child(2){animation-delay:.15s}.tb-typing i:nth-child(3){animation-delay:.3s}',
        '@keyframes tbDot{0%,60%,100%{opacity:.25;transform:translateY(0)}30%{opacity:1;transform:translateY(-3px)}}',
        '@media(prefers-reduced-motion:reduce){.tb-typing i{animation:none;opacity:.5}}',
        /* Системная реплика — это состояние, а не слова тьютора: отделяем знаком. */
        '.tb-msg.sys{display:inline-flex;align-items:center;gap:6px}',
        '.tb-msg.sys .b42-ic{flex:none;color:var(--ochre)}',
        /* Ровный обрез списка не показывает, что выше есть ещё. */
        '.tb-body::before{content:"";position:sticky;top:-12px;display:block;height:14px;',
        'margin:-12px -14px 0;background:linear-gradient(var(--bg),transparent);pointer-events:none}',
        ':root{--tb-ic-chat:url("data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 24 24\' fill=\'none\' stroke=\'black\' stroke-width=\'1.6\' stroke-linecap=\'round\' stroke-linejoin=\'round\'%3E%3Cpath d=\'M20 15a2 2 0 0 1-2 2H8l-4 4V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2z\'/%3E%3Cpath d=\'M8 9h8\'/%3E%3Cpath d=\'M8 12.5h5\'/%3E%3C/svg%3E")}',
        /* ── Шкала касания внутри панели (QA, круг 2: .tb-close меряется 12×20) ──
           Панель живёт своей вёрсткой, поэтому общая шкала из css/style.css её не
           накрывала: крестик был ровно по глифу «×», а «Спросить» — 85×33. Закрыть
           диалог — единственный способ его убрать, и именно эта кнопка была самой
           мелкой на экране. Берём те же ступени, что и весь сайт. */
        '.tb-close{background:none;border:none;font-size:20px;line-height:1;cursor:pointer;color:var(--soft);',
        'min-width:var(--tap-md,44px);min-height:var(--tap-md,44px);display:inline-flex;',
        'align-items:center;justify-content:center;border-radius:10px;margin:-6px -6px -6px 0}',
        '.tb-close:hover{color:var(--text);background:var(--tag-bg)}',
        '.tb-foot button{min-height:var(--tap-md,44px);min-width:var(--tap-md,44px)}',
        '.tb-foot textarea{min-height:var(--tap-md,44px)}',
        '.tb-fab{min-width:var(--tap-md,44px);min-height:var(--tap-md,44px)}'
    ].join('');

    function injectStyle() {
        if (document.getElementById(STYLE_ID)) return;
        var s = document.createElement('style'); s.id = STYLE_ID; s.textContent = CSS;
        document.head.appendChild(s);
    }
    function el(tag, cls, html) {
        var e = document.createElement(tag);
        if (cls) e.className = cls;
        if (html != null) e.innerHTML = html;
        return e;
    }
    /* Знак из нашего набора (js/icons.js). Запасной вариант — типографский символ,
       он рисуется шрифтом и одинаков везде; эмодзи в запас не берём именно поэтому. */
    function tIcon(name, size, fallback) {
        return (global.B42Icons && B42Icons[name]) ? B42Icons[name](size || 16) : (fallback || '');
    }

    /* Подпись интерфейса — всегда отдельным узлом.
       Словарь курса (js/course-i18n.js) сверяет текст узла ЦЕЛИКОМ — так он не может случайно
       зацепить содержание урока. Значит, склейка «Как на самом деле: » + переведённый текст
       даёт узел, которого в словаре нет, и подпись остаётся русской на всех языках. Раньше так
       и было со всеми вердиктами разбора. Держим подписи в своих узлах, содержание — в своих. */
    function lab(text) {
        var s = document.createElement('span');
        s.textContent = text;                 // ровно ключ словаря, без разметки вокруг
        return s;
    }
    /* Примеры записи числа. В <code> словарь не заходит — и правильно: «5·10³²» переводить
       нечего, а сломать разметку примера легко. */
    function codeEl(text) {
        var c = document.createElement('code');
        c.textContent = text;
        return c;
    }
    /** Собирает содержимое из кусочков: строка — текстовым узлом, узел — как есть. */
    function fill(host, parts) {
        parts.forEach(function (p) {
            if (p == null || p === false) return;
            host.appendChild(typeof p === 'string' ? document.createTextNode(p) : p);
        });
        return host;
    }

    /* Число так, как оно написано в уроке. «5e+32» — запись из отладчика: в тексте то же
       число выглядит как 5·10³², и читателю не с чем сравнивать свой ответ. Обычные числа
       не трогаем — экспонента появляется ровно там, где её показал бы и сам JS. */
    var SUP = ['⁰', '¹', '²', '³', '⁴', '⁵', '⁶', '⁷', '⁸', '⁹'];
    function supText(n) {
        return String(n).split('').map(function (c) { return c === '-' ? '⁻' : SUP[+c]; }).join('');
    }
    function numText(v) {
        if (typeof v !== 'number' || !isFinite(v)) return String(v);
        var a = Math.abs(v), out;
        if (a !== 0 && (a >= 1e5 || a < 1e-4)) {
            var e = Math.floor(Math.log10(a));
            var m = Number((v / Math.pow(10, e)).toPrecision(3));
            out = (Math.abs(m) === 1 ? (m < 0 ? '-' : '') : m + '·') + '10' + supText(e);
        } else {
            out = String(Number(v.toPrecision(6)));
        }
        return out.replace(/^-/, '−');        // типографский минус, как в тексте уроков
    }

    /* Насколько промахнулись — словами, которые можно произнести вслух.
       Раньше здесь было res.off.toFixed(1) + '×', а грейдер честно отдаёт Infinity там, где
       «во столько-то раз» сказать нельзя: ответ нулём или с другим знаком. Читатель видел
       «вы промахнулись в Infinity×» — на десяти вопросах-прикидках из пятидесяти семи.
       Точность тоже приводим в чувство: «в 3.2×» человеку понятно, «в 1247.3×» — нет,
       это уже просто «очень далеко». */
    function missParts(res, L, unit) {
        if (res.kind === 'abs') {
            return [lab(L.estOffBy || 'вы промахнулись на'),
                    ' ' + numText(Number(res.off.toPrecision(2))) + unit];
        }
        if (res.reason === 'sign') return [lab(L.estOffSign || 'у ответа другой знак')];
        if (res.reason === 'zero') return [lab(L.estOffZero || 'ноль здесь не подходит')];
        if (!isFinite(res.off) || res.off >= 1000) {
            return [lab(L.estOffFar || 'вы промахнулись больше чем в тысячу раз')];
        }
        return [lab(L.estOff || 'вы промахнулись в'), ' ' + Number(res.off.toPrecision(2)) + '×'];
    }

    /* Формулы в разборе набираются так же, как в тексте урока. Страница прогоняет KaTeX один
       раз после отрисовки, а разбор появляется позже — по нажатию, — поэтому прогоняем сами;
       иначе читатель видит сырое «$\pi \cdot 0{,}1$». Разделители те же, что в course.html. */
    function renderMath(node) {
        if (!global.renderMathInElement) return;
        try {
            global.renderMathInElement(node, {
                delimiters: [{ left: '$$', right: '$$', display: true },
                             { left: '$', right: '$', display: false }],
                throwOnError: false
            });
        } catch (e) {}
    }

    // ═════════════ БОТ ═════════════
    function Bot(opts) {
        injectStyle();
        var lang = opts.lang || 'ru', L = opts.strings || {};
        var ctx = { title: '', text: '' };
        var busy = false;
        // Локальная разработка: wrangler dev поднимает Worker на 8787, а статику отдаёт другой
        // сервер — тогда в странице задают window.B42_TUTOR_API = 'http://localhost:8787/api/tutor'.
        var API = global.B42_TUTOR_API || '/api/tutor';
        // Тьютор отвечает через серверный эндпоинт /api/tutor. Пока сайт жил на GitHub Pages,
        // эндпоинта не было — кнопка висела бы и молчала, поэтому модуль был скрыт по умолчанию.
        // С 2026-07-30 включён: сайт на Cloudflare, /api/tutor живой, ключ модели в секретах
        // Worker'а, расход считается нормой (см. /api/quota). Выключается той же строкой —
        // window.B42_TUTOR_ENABLED = false в странице, если понадобится погасить без выкладки.
        var ENABLED = global.B42_TUTOR_ENABLED !== false;
        if (!ENABLED) return { hidden: true };
        var MAX_Q = opts.maxQuestions || 10;      // сколько вопросов/подсказок даётся за сессию
        var MAX_LEN = opts.maxLen || 600;         // ограничение на длину вопроса
        var asked = 0;

        // Иконка из общего набора (B42Icons), эмодзи — только как запасной вариант,
        // если набор не подключён: эмодзи выглядят по-разному в каждой системе.
        var fabIcon = (global.B42Icons && B42Icons.chat) ? B42Icons.chat(24) : '🎓';
        var fab = el('button', 'tb-fab', fabIcon); fab.type = 'button'; fab.title = L.botTitle || 'Спросить тьютора';
        var panel = el('div', 'tb-panel');
        var head = el('div', 'tb-head');
        var titleWrap = el('div');
        var title = el('div', 'tb-title', L.botTitle || 'Тьютор');
        var ctxLine = el('div', 'tb-ctx', '');
        // Остаток вопросов живёт здесь, а не репликой в потоке: в потоке он уезжал вверх
        // при первой прокрутке — исчезал тогда, когда как раз становился нужен.
        var quotaLine = el('div', 'tb-quota', '');
        titleWrap.appendChild(title); titleWrap.appendChild(ctxLine); titleWrap.appendChild(quotaLine);
        var close = el('button', 'tb-close', '×'); close.type = 'button';
        head.appendChild(titleWrap); head.appendChild(close);
        var body = el('div', 'tb-body');
        var foot = el('div', 'tb-foot');
        var input = el('textarea'); input.placeholder = L.botPlaceholder || 'Спросите о том, что не сходится…';
        var send = el('button', null, L.botSend || 'Спросить'); send.type = 'button';
        foot.appendChild(input); foot.appendChild(send);
        panel.appendChild(head); panel.appendChild(body); panel.appendChild(foot);
        document.body.appendChild(fab); document.body.appendChild(panel);

        /* icon — необязательный знак из набора перед текстом. Раньше он был вшит в саму
           строку («🔑 Нужен токен…»), из-за чего эмодзи ехал в файлы переводов и рисовался
           системой по-разному. Текст кладём через textContent: он приходит из локали и
           разметкой быть не должен.
           text может быть и списком кусочков — тогда подпись живёт в своём узле и остаётся
           переводимой (см. lab() выше): «лимит исчерпан» + « (10).» одной строкой словарь
           не находит. */
        function msg(text, who, icon) {
            var m = el('div', 'tb-msg ' + who);
            if (icon) m.innerHTML = tIcon(icon, 15, '');
            if (Array.isArray(text)) fill(m, icon ? [' '].concat(text) : text);
            else if (icon) m.appendChild(document.createTextNode(' ' + text));
            else m.textContent = text;
            body.appendChild(m); body.scrollTop = body.scrollHeight;
            return m;
        }
        function setCtx(c) {
            ctx = c || { title: '', text: '' };
            ctxLine.innerHTML = '';
            // Подпись и название раздела — разными узлами: склеенное «по разделу: Гамильтониан»
            // словарь курса не узнаёт и на английской странице подпись остаётся русской.
            if (ctx.title) fill(ctxLine, [lab(L.botCtx || 'по разделу'), ': ' + ctx.title]);
        }
        function open(c, seed) {
            if (c) setCtx(c);
            panel.classList.add('open'); fab.style.display = 'none';
            // Приветствие — это слова тьютора, а не состояние: пузырём бота, со знаком.
            // Раньше шло как системная реплика и читалось наравне с «демо-режим» и «нужен токен».
            if (!body.childNodes.length) msg(L.botHello || 'Спросите что угодно по этому разделу — объясню на пальцах.', 'bot');
            if (seed) { input.value = seed; }
            input.focus();
        }
        function hide() { panel.classList.remove('open'); fab.style.display = ''; }

        // ── токен доступа ──
        // Доступ к живому тьютору по токену (выдаётся на неделю с лимитом — чтобы расход на
        // DeepSeek был предсказуем). Токен берём из ?token=… (удобно раздавать ссылкой) либо
        // из localStorage; в URL не оставляем — сразу чистим адресную строку.
        var TOKEN_KEY = 'b42_tutor_token';
        function getToken() { try { return localStorage.getItem(TOKEN_KEY) || ''; } catch (e) { return ''; } }

        // ── Проверка «не робот» (Cloudflare Turnstile) ──
        // Подключаем библиотеку лениво — только когда человек впервые задаёт вопрос.
        // Грузить её на каждой странице курса ради кнопки, которую нажмут единицы, незачем.
        // Виджет невидимый: человек ничего не делает, скрипт получает одноразовый пропуск.
        var TURNSTILE_SITEKEY = global.B42_TURNSTILE_SITEKEY || '0x4AAAAAAEB-LevMvRwY5jR7';
        var tsReady = null;

        function loadTurnstile() {
            if (tsReady) return tsReady;
            tsReady = new Promise(function (resolve) {
                if (global.turnstile) return resolve(true);
                var s = document.createElement('script');
                s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
                s.async = true;
                s.onload = function () { resolve(true); };
                s.onerror = function () { resolve(false); };   // не роняем диалог из-за сети
                document.head.appendChild(s);
            });
            return tsReady;
        }

        // Пропуск одноразовый и живёт минуты — поэтому берём новый на каждый вопрос,
        // а не храним. Если проверка недоступна, возвращаем пустую строку: сервер откажет
        // сам и скажет об этом человеческим текстом, а мы не притворяемся, что всё хорошо.
        async function turnstilePass() {
            var ok = await loadTurnstile();
            if (!ok || !global.turnstile) return '';
            var host = document.createElement('div');
            host.style.display = 'none';
            document.body.appendChild(host);
            return new Promise(function (resolve) {
                var done = false;
                function finish(v) {
                    if (done) return;
                    done = true;
                    try { host.remove(); } catch (e) {}
                    resolve(v || '');
                }
                try {
                    global.turnstile.render(host, {
                        sitekey: TURNSTILE_SITEKEY, size: 'invisible',
                        callback: finish, 'error-callback': function () { finish(''); },
                    });
                } catch (e) { finish(''); }
                setTimeout(function () { finish(''); }, 8000);  // не ждём вечно
            });
        }
        function setToken(t) { try { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY); } catch (e) {} }
        (function pickTokenFromUrl() {
            try {
                var u = new URL(location.href), t = u.searchParams.get('token');
                if (t) {
                    setToken(t.trim());
                    u.searchParams.delete('token');
                    history.replaceState(null, '', u.toString());
                }
            } catch (e) {}
        })();
        function promptToken() {
            var t = prompt(L.tokenPrompt || 'Введите токен доступа к тьютору (выдаётся на неделю):', getToken() || '');
            if (t != null) { setToken(t.trim()); return t.trim(); }
            return '';
        }

        // Вопрос уходит на наш Worker (/api/tutor), ключ DeepSeek там в секрете.
        async function ask(question, mode, demoHint) {
            if (busy || !question.trim()) return;
            if (asked >= MAX_Q) {                                  // лимит на сессию: 10 вопросов/подсказок
                msg([lab(L.sessionLimit || 'На эту сессию лимит исчерпан'), ' (' + MAX_Q + ').'],
                    'sys', 'clock');
                return;
            }
            question = question.trim().slice(0, MAX_LEN);           // и на длину одного вопроса
            asked++;
            busy = true; msg(question, 'me');
            input.value = '';
            // Ожидание — тремя точками: слово «Думаю…» в потоке читалось как ещё одна
            // реплика бота. Подпись для скринридера остаётся словом.
            var pend = el('div', 'tb-typing', '<i></i><i></i><i></i>');
            pend.setAttribute('aria-label', L.botThinking || 'Думаю…');
            pend.setAttribute('role', 'status');
            body.appendChild(pend); body.scrollTop = body.scrollHeight;
            try {
                var headers = { 'content-type': 'application/json' };
                var tok = getToken();
                if (tok) headers['x-b42-token'] = tok;
                // Проверка «не робот». Для человека она обычно невидима: виджет решает
                // задачу сам и отдаёт одноразовый пропуск. Без него сервер откажет —
                // каждый вопрос стоит денег, и открытая ручка выгребается за ночь.
                var pass = await turnstilePass();
                var r = await fetch(API, {
                    method: 'POST', headers: headers,
                    body: JSON.stringify({
                        lang: lang, mode: mode || 'ask', question: question,
                        turnstile: pass,
                        context: (ctx.title ? ctx.title + '\n\n' : '') + (ctx.text || '')
                    })
                });
                var data = await r.json().catch(function () { return {}; });
                pend.remove();
                if (r.ok && data.answer) {
                    msg(data.answer, 'bot');
                    if (typeof data.left === 'number' && data.left <= 20) {
                        // подпись отдельным узлом — иначе словарь её не найдёт (см. lab())
                        quotaLine.innerHTML = '';
                        fill(quotaLine, [lab(L.tokenLeft || 'Осталось вопросов по токену'), ': ' + data.left]);
                    }
                } else if (data.error === 'token_required' || data.error === 'token_invalid') {
                    msg(L.tokenNeeded || 'Нужен токен доступа — он выдаётся на неделю и ограничен по числу вопросов.', 'sys', 'key');
                    var got = promptToken();
                    if (got) { busy = false; return ask(question, mode, demoHint); }
                } else if (data.error === 'token_expired') {
                    msg(L.tokenExpired || 'Срок действия токена истёк — попросите новый.', 'sys', 'key');
                } else if (data.error === 'limit_total' || data.error === 'limit_day') {
                    msg((data.error === 'limit_day'
                        ? (L.limitDay || 'На сегодня лимит вопросов исчерпан. Возвращайтесь завтра.')
                        : (L.limitTotal || 'Лимит вопросов по этому токену исчерпан.')), 'sys', 'clock');
                } else if (demoHint) {
                    msg(demoHint, 'bot');
                    msg(L.botDemo || 'Демо-режим: живой тьютор подключается на сервере (ключ DeepSeek). Это заготовленная подсказка из материала урока.', 'sys', 'warn');
                } else {
                    msg(L.botOffline || 'Тьютор сейчас недоступен (нет ключа DeepSeek на сервере). Подсказка к этому вопросу есть в материале раздела.', 'sys', 'warn');
                }
            } catch (e) {
                pend.remove();
                msg(demoHint || (L.botOffline || 'Тьютор недоступен.'), demoHint ? 'bot' : 'sys',
                    demoHint ? null : 'warn');
            }
            busy = false;
        }

        fab.addEventListener('click', function () { open(); });
        close.addEventListener('click', hide);
        send.addEventListener('click', function () { ask(input.value); });
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(input.value); }
        });

        return {
            open: open, setCtx: setCtx, ask: ask,
            left: function () { return Math.max(0, MAX_Q - asked); },
            askWithContext: function (c, question, mode, demoHint) { setCtx(c); open(c); ask(question, mode, demoHint); },
            setLang: function (l, strings) { lang = l; if (strings) L = strings; title.textContent = L.botTitle || 'Тьютор'; input.placeholder = L.botPlaceholder || ''; send.textContent = L.botSend || 'Спросить'; setCtx(ctx); }
        };
    }

    // ═════════════ ВОПРОСЫ И ОЦЕНКА ═════════════
    // q = { id, q, type:'mcq'|'free', options:[], answer:idx, keywords:[], why, hint, ctx }
    function Quiz(root, questions, strings, bot, opts) {
        injectStyle();
        var L = strings || {}, results = {}, o = opts || {};
        root.innerHTML = '';

        questions.forEach(function (q) {
            var card = el('div', 'tq');
            card.appendChild(el('div', 'tq-q', q.q));
            var fb = el('div', 'tq-fb'); fb.style.display = 'none';
            var actions = el('div', 'tq-actions'); actions.style.display = 'none';

            function settle(correct, userText) {
                results[q.id] = { correct: correct, answer: userText || '' };
                fb.className = 'tq-fb ' + (correct ? 'ok' : 'no');
                // Верно — галочка из набора, мимо — знак вопроса (paradox): он про «подумай ещё»,
                // а не про ошибку. Эмодзи здесь рисовала система, и «✅» на каждой ОС был своего
                // оттенка зелёного — рядом со штриховым набором это выбивалось.
                // Пояснение `why` написано под ВЕРНЫЙ ответ, поэтому после промаха его нельзя
                // приклеивать к вердикту встык: получалось «Не совсем. Именно так: …», будто
                // читатель ответил правильно. Отделяем строкой и подводкой.
                // Подпись вердикта и текст урока — разными узлами, иначе подпись непереводима
                // (см. lab() выше): словарь ищет узел целиком.
                fb.innerHTML = tIcon(correct ? 'check' : 'paradox', 16, correct ? '✓' : '?');
                fill(fb, [
                    ' ', lab(correct ? (L.right || 'Верно!') : (L.notQuite || 'Не совсем.')),
                    q.why && el('br'),
                    q.why && !correct && lab(L.howItIs || 'Как на самом деле:'),
                    q.why && !correct && ' ',
                    q.why && el('span', null, q.why)      // содержание урока — с его разметкой
                ]);
                fb.style.display = '';
                renderMath(fb);
                actions.innerHTML = ''; actions.style.display = '';
                // Кнопка «довести до идеи» — бот в режиме hint (правильный ответ не выдаёт)
                var askBtn = el('button', 'tq-ask', '');
                askBtn.innerHTML = tIcon(correct ? 'chat' : 'lamp', 16, '') + ' ' +
                    (correct ? (L.askMore || 'Спросить глубже') : (L.leadMe || 'Не понимаю — подведи к идее'));
                askBtn.type = 'button';
                askBtn.addEventListener('click', function () {
                    var question = correct
                        ? (L.seedDeeper || 'Объясни глубже, почему это так: ') + q.q
                        : (L.seedStuck || 'Я ответил так: ') + '«' + (userText || (L.noAnswer || 'не знаю')) + '». ' +
                          (L.seedStuck2 || 'Не понимаю, где ошибка. Вопрос: ') + q.q;
                    bot.askWithContext({ title: q.ctxTitle || (L.quizCtx || 'Проверка знаний'), text: (q.ctx || '') + '\n\n' + q.q },
                        question, correct ? 'ask' : 'hint', q.hint);
                });
                actions.appendChild(askBtn);
                if (o.onAnswer) o.onAnswer(results);
            }

            // Прикидка порядка (по-фейнмановски): важно не точное число, а верный масштаб.
            // Засчитываем, если ответ в пределах фактора tolerance (по умолчанию ×3) от эталона.
            if (q.type === 'estimate') {
                var ew = el('div', 'tq-free');
                var ei = el('input');
                ei.type = 'text'; ei.inputMode = 'decimal';
                ei.placeholder = L.estPlaceholder || 'Порядок величины, можно «в уме»…';
                ei.style.cssText = 'flex:1;font:inherit;font-size:14px;padding:8px 10px;border:1px solid var(--border);border-radius:9px;background:var(--bg);color:var(--text)';
                var eu = el('span', null, q.unit || '');
                eu.style.cssText = 'align-self:center;font-size:13px;color:var(--soft)';
                var eb = el('button', 'tq-send', L.check || 'Проверить'); eb.type = 'button';
                ew.appendChild(ei); ew.appendChild(eu); ew.appendChild(eb);
                card.appendChild(ew);
                // Подсказка про запись числа. Живёт под полем и появляется только тогда, когда
                // мы ввод не поняли: до этого читателю не о чем читать инструкцию.
                var etip = el('div', 'tq-tip'); etip.style.display = 'none';
                etip.setAttribute('role', 'status');
                card.appendChild(etip);
                function showTip(parts) {
                    etip.innerHTML = '';
                    fill(etip, parts);
                    etip.style.display = '';
                    ei.setAttribute('aria-invalid', 'true');
                    ei.focus();
                }
                function hideTip() {
                    etip.style.display = 'none';
                    ei.removeAttribute('aria-invalid');
                }
                // Начал править ввод — замечание убираем: оно про прошлую запись, а не про эту.
                ei.addEventListener('input', hideTip);
                eb.addEventListener('click', function () {
                    var raw = ei.value.trim();
                    // Правило проверки — одно на проект, js/quiz-grade.js: оно понимает и
                    // абсолютную погрешность, и множитель, и отрицательные ответы. Раньше
                    // правило жило прямо здесь, знало только множитель и потому не пропускало
                    // даже точный авторский ответ там, где автор писал ±0,1.
                    var G = (typeof B42Grade !== 'undefined') ? B42Grade : null;
                    if (!G) { console.warn('B42Grade не подключён — проверка прикидок не работает'); }
                    // Молчащая кнопка — худшее из возможного: читатель не понимает, сломалось
                    // у него или у нас, и жмёт ещё раз. Говорим, какая запись понимается,
                    // и попытку не засчитываем.
                    if (!raw) {
                        showTip([lab(L.estEmpty || 'Впишите число — хватит и порядка величины.')]);
                        return;
                    }
                    if (!G || !isFinite(G.parseValue(raw))) {
                        showTip([lab(L.estFormat || 'Не разобрал число. Можно так:'), ' ',
                            codeEl('5·10³²'), ' ', codeEl('10⁻³⁴'), ' ', codeEl('0,5'), ' ', codeEl('−10')]);
                        return;
                    }
                    hideTip();
                    var res = G.estimate(raw, q);
                    var ok = res.ok;
                    // Единица «—» означает «безразмерная»: подставлять её в текст нельзя,
                    // иначе получается «промахнулись на 0.65 —» и двойное тире рядом.
                    var unit = (q.unit && q.unit !== '—') ? ' ' + q.unit : '';
                    fb.className = 'tq-fb ' + (ok ? 'ok' : 'no');
                    fb.innerHTML = tIcon(ok ? 'check' : 'paradox', 16, ok ? '✓' : '?');
                    // Каждая подпись — своим узлом: иначе словарь курса её не найдёт и на
                    // английской странице останется русское «Точное значение».
                    fill(fb, [
                        ' ', lab(ok ? (L.estRight || 'Порядок верный!') : (L.estWrong || 'Мимо порядка.')),
                        ' ', lab(L.estAnswer || 'Точное значение'), ': ',
                        el('b', null, numText(q.answer) + unit)
                    ]);
                    if (!ok) fill(fb, [' — '].concat(missParts(res, L, unit)));
                    if (q.why) fill(fb, [el('br'), el('span', null, q.why)]);
                    fb.style.display = '';
                    renderMath(fb);
                    results[q.id] = { correct: ok, answer: raw };
                    ei.disabled = true; eb.disabled = true; eb.style.opacity = .5;
                    actions.innerHTML = ''; actions.style.display = '';
                    var ab = el('button', 'tq-ask', '');
                    ab.innerHTML = tIcon(ok ? 'chat' : 'lamp', 16, '') + ' ' +
                        (ok ? (L.askMore || 'Спросить глубже') : (L.leadMe || 'Как это прикинуть?'));
                    ab.type = 'button';
                    ab.addEventListener('click', function () {
                        bot.askWithContext({ title: q.ctxTitle || (L.quizCtx || 'Оценка'), text: (q.ctx || '') + '\n\n' + q.q },
                            (L.seedEstimate || 'Помоги прикинуть в уме, по шагам, не давая сразу число: ') + q.q,
                            ok ? 'ask' : 'hint', q.hint);
                    });
                    actions.appendChild(ab);
                    if (o.onAnswer) o.onAnswer(results);
                });
            } else if (q.type === 'free') {
                var wrap = el('div', 'tq-free');
                var ta = el('textarea'); ta.placeholder = L.freePlaceholder || 'Ответьте своими словами…';
                var btn = el('button', 'tq-send', L.check || 'Проверить'); btn.type = 'button';
                wrap.appendChild(ta); wrap.appendChild(btn);
                card.appendChild(wrap);
                btn.addEventListener('click', function () {
                    var val = ta.value.trim();
                    if (!val) return;
                    // Свободный ответ проверяем по ключевым идеям — грубо, зато мгновенно и без сети;
                    // спорные случаи ученик всегда может разобрать с тьютором кнопкой ниже.
                    var lower = val.toLowerCase();
                    var hits = (q.keywords || []).filter(function (k) { return lower.indexOf(k.toLowerCase()) >= 0; });
                    settle(hits.length >= (q.needed || 1), val);
                    ta.disabled = true; btn.disabled = true; btn.style.opacity = .5;
                });
            } else {
                var opts = el('div', 'tq-opts');
                // Порядок вариантов перемешиваем. В данных верный ответ стоит вторым в 64%
                // вопросов и ни разу — последним: стратегия «всегда жми второй» давала около
                // двух третей правильных, то есть проверка знаний проверяла привычку автора,
                // а не читателя. Перемешиваем один раз при отрисовке (не при каждом клике),
                // чтобы подсветка верного и неверного осталась на своих местах.
                var order = q.options.map(function (_, i) { return i; });
                for (var oi = order.length - 1; oi > 0; oi--) {
                    var oj = Math.floor(Math.random() * (oi + 1));
                    var tmp = order[oi]; order[oi] = order[oj]; order[oj] = tmp;
                }
                order.forEach(function (src, shown) {
                    var text = q.options[src];
                    var b = el('button', 'tq-opt', text); b.type = 'button';
                    b.addEventListener('click', function () {
                        var all = opts.querySelectorAll('.tq-opt');
                        all.forEach(function (x, xi) {
                            x.disabled = true;
                            if (order[xi] === q.answer) x.classList.add('right');
                            else if (xi === shown) x.classList.add('wrong');
                        });
                        settle(src === q.answer, text);
                    });
                    opts.appendChild(b);
                });
                card.appendChild(opts);
            }
            card.appendChild(fb); card.appendChild(actions);
            root.appendChild(card);
        });

        return {
            results: function () { return results; },
            score: function () {
                var done = Object.keys(results).length;
                var right = Object.keys(results).filter(function (k) { return results[k].correct; }).length;
                return { done: done, right: right, total: questions.length };
            }
        };
    }

    // Итоговая карточка: балл, полоса, вердикт и куда копать дальше.
    function renderScore(root, score, strings, levels) {
        injectStyle();
        var L = strings || {};
        var pct = score.total ? Math.round(100 * score.right / score.total) : 0;
        var lv = levels.slice().reverse().find(function (x) { return pct >= x.min; }) || levels[0];
        root.innerHTML = '';
        var card = el('div', 'tq-score');
        // Подпись — своим узлом, балл и вердикт — своими: склейку словарь не находит (см. lab()).
        var h3 = el('h3');
        fill(h3, [lab(L.yourResult || 'Ваш результат'),
                  ': ' + score.right + '/' + score.total + ' — ', lab(lv.title)]);
        card.appendChild(h3);
        var bar = el('div', 'tq-score-bar');
        var barFill = el('div', 'tq-score-fill'); barFill.style.width = pct + '%';
        bar.appendChild(barFill); card.appendChild(bar);
        card.appendChild(el('p', null, lv.text));
        if (lv.next) {
            var p = el('p');
            var b = el('b'); b.appendChild(lab(L.whereNext || 'Куда дальше')); b.appendChild(document.createTextNode(':'));
            fill(p, [b, ' ', el('span', null, lv.next)]);
            card.appendChild(p);
        }
        root.appendChild(card);
        return card;
    }

    global.B42Tutor = { Bot: Bot, Quiz: Quiz, renderScore: renderScore };
})(window);
