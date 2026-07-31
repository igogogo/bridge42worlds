/* Общий пропуск «не робот» (Cloudflare Turnstile) — один помощник на все платные кнопки.
 *
 * Появился из блокера QA 2026-07-31: кнопка «перевести статью» слала /api/order БЕЗ
 * пропуска, а воркер без него отказывает всегда (fail-closed) — кнопка не могла сработать
 * никогда. Логика один в один повторяла бы тьютора (js/tutor.js), а «правило в двух местах
 * обязательно разойдётся» — поэтому вынос сюда. Тьютор пока живёт со своей копией
 * (работает на проде, трогать без нужды не стали) — при следующей правке tutor.js
 * перевести на этот помощник и копию удалить.
 *
 * Использование:  var pass = await window.b42TurnstilePass();
 * Пустая строка = проверка недоступна; шлём как есть — сервер откажет сам и скажет
 * человеческим текстом, а мы не притворяемся, что всё хорошо.
 */
(function (global) {
    'use strict';
    var SITEKEY = global.B42_TURNSTILE_SITEKEY || '0x4AAAAAAEB-LevMvRwY5jR7';
    var tsReady = null;

    function load() {
        if (tsReady) return tsReady;
        tsReady = new Promise(function (resolve) {
            if (global.turnstile) return resolve(true);
            var s = document.createElement('script');
            s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
            s.async = true;
            s.onload = function () { resolve(true); };
            s.onerror = function () { resolve(false); };   // сеть упала — не роняем кнопку
            document.head.appendChild(s);
        });
        return tsReady;
    }

    // Пропуск одноразовый и живёт минуты — берём новый на каждое действие, не храним.
    global.b42TurnstilePass = async function () {
        var ok = await load();
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
                    sitekey: SITEKEY, size: 'invisible',
                    callback: finish, 'error-callback': function () { finish(''); },
                });
            } catch (e) { finish(''); }
            setTimeout(function () { finish(''); }, 8000);  // не ждём вечно
        });
    };
})(window);
