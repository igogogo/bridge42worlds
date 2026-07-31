/* Страница «изнутри»: опросы, ключ участника, заявка.
 *
 * Раньше этот код жил внутри council.html одной копией на один русский файл. Теперь
 * страница собирается на пять языков (council_page.py), и держать в каждой свою копию
 * скрипта — верный способ получить пять разных поведений через месяц. Подписи приходят
 * из разметки в window.B42_COUNCIL_T, логика одна.
 */
(function () {
    'use strict';
    var T = window.B42_COUNCIL_T || {};
    var LS_POLL = 'b42_council_polls', LS_TOKEN = 'b42_council_token';

    function read(key, dflt) {
        try { return JSON.parse(localStorage.getItem(key)) || dflt; } catch (e) { return dflt; }
    }
    function write(key, val) {
        try { localStorage.setItem(key, JSON.stringify(val)); } catch (e) { /* приватный режим */ }
    }

    /* Опросы. Голос остаётся в браузере и уезжает вместе с заявкой — так и написано
       на самой странице. Обещать «ваш голос учтён» без приёмника нельзя: это тот же
       молчаливый обман, который мы в своём коде считаем худшим классом ошибок. */
    var votes = read(LS_POLL, {});
    Array.prototype.forEach.call(document.querySelectorAll('.poll'), function (poll) {
        var id = poll.dataset.poll;
        var said = poll.querySelector('.said');
        function paint() {
            Array.prototype.forEach.call(poll.querySelectorAll('button'), function (b) {
                b.classList.toggle('on', votes[id] === b.dataset.v);
            });
            said.textContent = votes[id] ? (T.poll_saved || '') + ' ' + votes[id] : '';
        }
        poll.addEventListener('click', function (e) {
            var b = e.target.closest('button');
            if (!b) return;
            votes[id] = (votes[id] === b.dataset.v) ? null : b.dataset.v;
            if (!votes[id]) delete votes[id];
            write(LS_POLL, votes);
            paint();
        });
        paint();
    });

    /* Живое число статей. Если сводка не доехала — на странице остаются числа из
       разметки: они верны на момент сборки и врать не начнут. */
    fetch('/data/corpus-stats.json')
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) {
            if (!d || !d.generated_total || !d.generated_total.gen) return;
            var cell = document.querySelector('#live-num div b');
            if (cell) cell.textContent = d.generated_total.gen;
        })
        .catch(function () { /* остаёмся на числах из разметки */ });

    /* Ключ участника. Никакого аккаунта: случайный номер, который человек сохраняет.
       Пароля нет — значит нечему утечь. */
    function makeToken() {
        var raw = (window.crypto && crypto.randomUUID) ? crypto.randomUUID()
                : String(Date.now()) + Math.random().toString(36).slice(2);
        return 'B42-' + raw.replace(/-/g, '').slice(0, 12).toUpperCase();
    }

    var elName = document.getElementById('j-name'),
        elMail = document.getElementById('j-mail'),
        elNote = document.getElementById('j-note'),
        elTok = document.getElementById('j-token'),
        btnMake = document.getElementById('j-make'),
        btnMail = document.getElementById('j-mail-btn'),
        btnCopy = document.getElementById('j-copy');
    if (!btnMake) return;

    var saved = read(LS_TOKEN, null);

    function letter() {
        var lines = [
            T.letter_title || 'bridge42worlds', '',
            (T.letter_name || 'Name') + ': ' + (elName.value.trim() || '—'),
            (T.letter_mail || 'Mail') + ': ' + (elMail.value.trim() || '—'),
            (T.letter_key || 'Key') + ': ' + (saved && saved.token ? saved.token : '—'), ''
        ];
        var keys = Object.keys(votes);
        if (keys.length) {
            lines.push(T.letter_answers || '');
            keys.forEach(function (k) { lines.push('  · ' + k + ': ' + votes[k]); });
            lines.push('');
        }
        if (elNote.value.trim()) { lines.push(T.letter_msg || '', elNote.value.trim()); }
        return lines.join('\n');
    }

    function showToken() {
        elTok.hidden = false;
        elTok.textContent = '';
        var span = document.createElement('span');
        span.textContent = saved.token;
        var small = document.createElement('small');
        small.textContent = T.key_note || '';
        elTok.appendChild(span);
        elTok.appendChild(small);
        btnMail.hidden = false;
        btnCopy.hidden = false;
        btnMake.textContent = T.b_key_done || btnMake.textContent;
    }

    btnMake.addEventListener('click', function () {
        if (!saved || !saved.token) {
            saved = { token: makeToken(), at: new Date().toISOString().slice(0, 10) };
        }
        saved.name = elName.value.trim();
        saved.mail = elMail.value.trim();
        write(LS_TOKEN, saved);
        showToken();
    });

    btnMail.addEventListener('click', function () {
        window.location.href = 'mailto:admin@bridge42worlds.academy'
            + '?subject=' + encodeURIComponent(T.letter_subject || 'bridge42worlds')
            + '&body=' + encodeURIComponent(letter());
    });

    btnCopy.addEventListener('click', function () {
        function done(ok) { btnCopy.textContent = ok ? (T.b_copied || 'ok') : (T.b_copy_manual || ''); }
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(letter()).then(function () { done(true); },
                                                         function () { done(false); });
        } else { done(false); }
    });

    if (saved && saved.token) {
        if (saved.name) elName.value = saved.name;
        if (saved.mail) elMail.value = saved.mail;
        showToken();
    }
})();
