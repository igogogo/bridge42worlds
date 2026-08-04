/* Совет живьём: вступление, предложения и голосование ВНУТРИ САЙТА, без почты.
 *
 * Решение владельца 2026-08-01: «регистрация без отправки по почте, внутри сайта,
 * ведение заседаний там же; нужен уже реализованный рабочий инструмент».
 *
 * Как это устроено и почему так:
 *
 * • ЧЛЕНСТВО — КЛЮЧ, А НЕ УЧЁТНАЯ ЗАПИСЬ. Сервер выдаёт ключ вида B42-XXXX-XXXX-XXXX,
 *   браузер его хранит, человек может переписать на бумажку и перенести на другое
 *   устройство. Ни почты, ни пароля, ни персональных данных — восстанавливать нечего,
 *   терять нечего, утечь нечему.
 * • ПРАВО ВХОДА ДОКАЗЫВАЕТСЯ ЧТЕНИЕМ, а не адресом почты: наш счётчик знает, сколько
 *   разных статей открыл этот браузер. Прочитал достаточно — можешь вступить. Это
 *   честнее подтверждения почты: почту подтвердит и робот, а сорок статей — нет.
 * • ГОЛОСОВАТЬ МОЖНО ПЕРЕДУМАВ: голос переписывается до закрытия заседания. Мнение
 *   меняется, когда читаешь чужие доводы, — это и есть смысл обсуждения.
 * • ИТОГИ ОТКРЫТЫ ВСЕМ, без ключа: решения совета публичны по определению.
 */
(function () {
    'use strict';
    var API = '/api/council';
    var LS_KEY = 'b42_council_key';
    var LANG = (document.documentElement.lang || 'ru').slice(0, 2);

    var T = {
        ru: { need: 'Чтобы вступить, откройте ещё {n} статей — сейчас прочитано {seen}.',
              can: 'Вы прочитали {seen} статей. Этого достаточно, чтобы войти в совет.',
              join: 'Войти в совет', joined: 'Вы участник совета', key: 'Ваш ключ',
              keyNote: 'Запишите его. Он заменяет логин и пароль: с ним вы войдёте с любого устройства.',
              propose: 'Предложить совету', placeholder: 'Что стоит изменить, добавить или прекратить',
              send: 'Отправить', sent: 'Предложение записано — оно попадёт в ближайшую повестку.',
              voteTitle: 'Голосование', yes: 'за', no: 'против', abstain: 'воздержаться',
              why: 'Коротко почему (необязательно)', voted: 'Голос учтён. Можно передумать до закрытия заседания.',
              results: 'Итоги', members: 'участников совета', err: 'Не получилось. Попробуйте ещё раз.',
              cabinet: 'Ваше участие', cabRead: ' статей прочитано', cabProps: ' предложений',
              cabVotes: ' голосов', cabSince: ' в совете с', cabMembers: ' участников всего',
              onAgenda: 'в повестке',
              fName: 'Как к вам обращаться (необязательно)',
              fMail: 'Почта для отчётов (необязательно)',
              fHint: 'Оба поля можно пропустить — ключ выдадим всё равно. Почта нужна только для писем о заседаниях.',
              getKey: 'Получить ключ',
              haveKey: 'У меня есть ключ', enter: 'Войти', badKey: 'ключ не найден — проверьте',
              invited: 'Вас пригласили в наблюдательный совет. Нажмите — и вы внутри: повестка, голосование, предложения.' },
        en: { need: 'To join, open {n} more articles — you have read {seen}.',
              can: 'You have read {seen} articles. That is enough to join the council.',
              join: 'Join the council', joined: 'You are a council member', key: 'Your key',
              keyNote: 'Write it down. It replaces login and password: use it on any device.',
              propose: 'Propose to the council', placeholder: 'What to change, add or stop doing',
              send: 'Send', sent: 'Proposal recorded — it will reach the next agenda.',
              voteTitle: 'Vote', yes: 'for', no: 'against', abstain: 'abstain',
              why: 'Briefly why (optional)', voted: 'Vote counted. You may change it until the meeting closes.',
              results: 'Results', members: 'council members', err: 'Did not work. Please try again.',
              cabinet: 'Your participation', cabRead: ' articles read', cabProps: ' proposals',
              cabVotes: ' votes', cabSince: ' member since', cabMembers: ' members total',
              onAgenda: 'on agenda',
              fName: 'How to address you (optional)',
              fMail: 'Email for reports (optional)',
              fHint: 'Both can be skipped — you get the key anyway. Email is only for meeting notices.',
              getKey: 'Get the key',
              haveKey: 'I have a key', enter: 'Enter', badKey: 'key not found — check it',
              invited: 'You have been invited to the council. One click and you are in: agenda, voting, proposals.' }
    };
    var L = T[LANG] || T.en;
    /* ar/es/fr — из файлов стратега (data/council/live-strings.<lang>.json): формулировки
       его, каркас мой, в js он не лезет. Пока файл едет, работает английский; приехал —
       надписи меняются на месте. Ключи сверяются: перевод с дырами хуже честного
       английского, потому что читается как недоделка. */
    if (!T[LANG] && ['ar', 'es', 'fr'].indexOf(LANG) >= 0) {
        fetch('/data/council/live-strings.' + LANG + '.json')
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (d) {
                if (!d) return;
                for (var k in T.ru) { if (!(k in d)) return; }   // дырявый перевод не берём
                L = d;
                if (window.__clRerender) window.__clRerender();
            }).catch(function () {});
    }

    function get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
    function set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
    function uid() { return get('b42_uid') || ''; }
    function esc(s) { var d = document.createElement('i'); d.textContent = s; return d.innerHTML; }

    function api(path, body) {
        return fetch(API + path, { method: 'POST', headers: { 'content-type': 'application/json' },
                                   body: JSON.stringify(body) }).then(function (r) { return r.json(); });
    }

    var host = document.getElementById('council-live') || (function () {
        // Своего места на странице может не быть — вешаемся перед формой заявки,
        // чтобы живой механизм стоял выше бумажного.
        var anchor = document.getElementById('j-make');
        if (!anchor) return null;
        var box = document.createElement('div');
        box.id = 'council-live';
        anchor.closest('form, section, div').insertAdjacentElement('beforebegin', box);
        return box;
    })();
    if (!host) return;

    function block(html) { var d = document.createElement('div'); d.className = 'cl-box'; d.innerHTML = html; return d; }

    function showMember(key) {
        window.__clRerender = function () { showMember(key); };
        host.innerHTML = '';
        host.appendChild(block(
            '<div class="cl-ok">🏛 ' + esc(L.joined) + '</div>' +
            '<div class="cl-key"><b>' + esc(L.key) + ':</b> <code>' + esc(key) + '</code>' +
            '<small>' + esc(L.keyNote) + '</small></div>' +
            '<div class="cl-cab"></div>' +
            '<div class="cl-prop"><h4>' + esc(L.propose) + '</h4>' +
            '<textarea class="cl-text" rows="3" placeholder="' + esc(L.placeholder) + '"></textarea>' +
            '<button type="button" class="cl-send">' + esc(L.send) + '</button>' +
            '<div class="cl-msg"></div></div>'));
        cabinet(key);
        host.querySelector('.cl-send').onclick = function () {
            var t = host.querySelector('.cl-text').value.trim();
            if (!t) return;
            var btn = this; btn.disabled = true;
            api('/propose', { key: key, text: t, lang: LANG }).then(function (r) {
                btn.disabled = false;
                host.querySelector('.cl-msg').textContent = r && r.ok ? L.sent : L.err;
                if (r && r.ok) host.querySelector('.cl-text').value = '';
            }).catch(function () { btn.disabled = false; host.querySelector('.cl-msg').textContent = L.err; });
        };
        mountVoting(key);
    }

    /* Кабинет участника: что он сделал и что из этого вышло. Не «профиль» с аватаркой,
       а короткая сводка участия — прочитано, предложено, как голосовал. Владелец
       2026-08-01: «небольшой личный кабинет участника». */
    function cabinet(key) {
        fetch(API + '/me?key=' + encodeURIComponent(key))
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (d) {
                var box = host.querySelector('.cl-cab');
                if (!d || !d.member || !box) return;
                var m = d.member;
                var rows = [
                    [L.cabRead, m.views],
                    [L.cabProps, (d.proposals || []).length],
                    [L.cabVotes, (d.votes || []).length],
                    [L.cabSince, (m.joined || '').slice(0, 10)],
                    [L.cabMembers, d.members]
                ];
                box.innerHTML = '<h4>' + esc(L.cabinet) + '</h4><div class="cl-stats">' +
                    rows.map(function (r) {
                        return '<span><b>' + esc(String(r[1])) + '</b>' + esc(r[0]) + '</span>';
                    }).join('') + '</div>' +
                    ((d.proposals || []).length
                        ? '<ul class="cl-list">' + d.proposals.slice(0, 5).map(function (p) {
                            return '<li>' + esc((p.text || '').slice(0, 140)) +
                                   (p.meeting ? ' <em>' + esc(L.onAgenda) + '</em>' : '') + '</li>';
                          }).join('') + '</ul>'
                        : '');
            }).catch(function () {});
    }

    function showJoin(st) {
        window.__clRerender = function () { showJoin(st); };
        host.innerHTML = '';
        // По личному приглашению порог чтения не нужен: человека позвали лично,
        // и это доказательство участия сильнее счётчика страниц.
        var can = st.eligible || !!get('b42_council_invite');
        var line = get('b42_council_invite') ? L.invited
                 : (can ? L.can : L.need).replace('{seen}', st.views).replace('{n}', Math.max(0, st.need - st.views));
        var b = block('<div class="cl-standing">' + esc(line) + '</div>' +
            (can ? '<button type="button" class="cl-join">' + esc(L.join) + '</button>' : '') +
            '<button type="button" class="cl-havekey">' + esc(L.haveKey) + '</button>' +
            '<div class="cl-msg"></div>');
        host.appendChild(b);
        /* «У меня есть ключ» — вход с ДРУГОГО устройства. Ключ живёт в браузере, и member
           в базе не означает, что этот браузер его знает: владелец вступил на телефоне,
           открыл с компьютера — и снова увидел «Войти в совет» (находка стратега
           2026-08-04, отсюда же его «токен забыл»). Форма вступления не должна быть
           единственной дверью. */
        var haveKey = host.querySelector('.cl-havekey');
        if (haveKey) haveKey.onclick = function () {
            var inp = host.querySelector('.cl-key-inp');
            if (!inp) {
                var f = document.createElement('div');
                f.className = 'cl-form';
                f.innerHTML = '<input class="cl-key-inp" type="text" placeholder="B42-XXXX-XXXX-XXXX" autocomplete="off">';
                haveKey.insertAdjacentElement('beforebegin', f);
                haveKey.textContent = L.enter;
                return;
            }
            var k = (inp.value || '').trim().toUpperCase();
            if (!/^B42-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$/.test(k)) { inp.focus(); return; }
            // Проверяем ключ КАБИНЕТОМ, а не верой: чужая строка не должна включать участника.
            fetch(API + '/me?key=' + encodeURIComponent(k))
                .then(function (r) { return r.ok; })
                .then(function (ok) {
                    if (ok) { set(LS_KEY, k); showMember(k); }
                    else { inp.value = ''; inp.placeholder = L.badKey; }
                }).catch(function () {});
        };

        var btn = host.querySelector('.cl-join');
        if (btn) btn.onclick = async function () {
            /* Минимальная форма (владелец 2026-08-01: «регистрацию упрости, форма
               минимальная, окошко»). Спрашиваем ровно два необязательных поля — как
               обращаться и куда прислать отчёт. Пропустить можно оба: членство от
               этого не зависит, а лишний вопрос на входе стоит нам участника. */
            var pane = host.querySelector('.cl-form');
            if (!pane) {
                var f = document.createElement('div');
                f.className = 'cl-form';
                f.innerHTML =
                    '<input class="cl-name" type="text" placeholder="' + esc(L.fName) + '">' +
                    '<input class="cl-mail" type="email" placeholder="' + esc(L.fMail) + '">' +
                    '<div class="cl-hint">' + esc(L.fHint) + '</div>';
                btn.insertAdjacentElement('beforebegin', f);
                btn.textContent = L.getKey;
                return;                       // первый клик открывает окошко, второй отправляет
            }
            btn.disabled = true;
            var pass = '';
            try {
                if (!window.b42TurnstilePass) await new Promise(function (res) {
                    var s = document.createElement('script'); s.src = '/js/b42-turnstile.js';
                    s.onload = res; s.onerror = res; document.head.appendChild(s);
                });
                if (window.b42TurnstilePass) pass = await window.b42TurnstilePass();
            } catch (e) {}
            var nm = host.querySelector('.cl-name'), ml = host.querySelector('.cl-mail');
            api('/join', { uid: uid(), turnstile: pass, invite: get('b42_council_invite') || '',
                           name: nm ? nm.value.trim() : '', email: ml ? ml.value.trim() : '' }).then(function (r) {
                if (r && r.ok && r.key) { set(LS_KEY, r.key); showMember(r.key); return; }
                btn.disabled = false;
                host.querySelector('.cl-msg').textContent = L.err;
            }).catch(function () { btn.disabled = false; host.querySelector('.cl-msg').textContent = L.err; });
        };
        mountVoting(null);
    }

    /* Голосование по ближайшему заседанию. Вопросы берём из того же файла, по которому
       строится страница заседания, — один источник, иначе списки разойдутся. */
    function mountVoting(key) {
        fetch('/data/council/upcoming.json').then(function (r) { return r.ok ? r.json() : null; })
            .then(function (m) {
                if (!m || !m.agenda || !m.agenda.length) return;
                var box = document.createElement('div');
                box.className = 'cl-box cl-vote';
                box.innerHTML = '<h4>' + esc(L.voteTitle) + ' · ' + esc(m.date || '') + '</h4>';
                m.agenda.forEach(function (q) {
                    var row = document.createElement('div');
                    row.className = 'cl-q';
                    row.innerHTML = '<div class="cl-qt">' + esc(q.title || q.id) + '</div>' +
                        (key ? '<div class="cl-btns">' +
                            ['yes', 'no', 'abstain'].map(function (v) {
                                return '<button type="button" data-v="' + v + '">' + esc(L[v]) + '</button>';
                            }).join('') + '</div><div class="cl-res"></div>'
                             : '<div class="cl-res"></div>');
                    box.appendChild(row);
                    if (key) row.querySelectorAll('button').forEach(function (b) {
                        b.onclick = function () {
                            api('/vote', { key: key, meeting: m.date, question: q.id, vote: b.dataset.v })
                                .then(function (r) {
                                    row.querySelector('.cl-res').textContent = r && r.ok ? L.voted : L.err;
                                    row.querySelectorAll('button').forEach(function (x) { x.classList.remove('on'); });
                                    if (r && r.ok) b.classList.add('on');
                                    loadResults(m.date, box);
                                });
                        };
                    });
                });
                host.appendChild(box);
                loadResults(m.date, box);
            }).catch(function () {});
    }

    function loadResults(meeting, box) {
        fetch(API + '/results?meeting=' + encodeURIComponent(meeting))
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (d) {
                if (!d || !d.results) return;
                box.querySelectorAll('.cl-q').forEach(function (row, i) {
                    var qid = (box.__ids || [])[i];
                });
                var head = box.querySelector('h4');
                if (head && d.members) head.innerHTML += ' <small>' + d.members + ' ' + esc(L.members) + '</small>';
            }).catch(function () {});
    }

    /* Вход по ссылке: /council.html?key=B42-… — владелец рассылает такую ссылку, человек
       переходит и сразу оказывается в кабинете. Ключ из адреса убираем немедленно:
       иначе он останется в истории браузера и в реферере при переходе по любой ссылке. */
    (function keyFromUrl() {
        try {
            var u = new URL(location.href), k = u.searchParams.get('key');
            var inv = u.searchParams.get('invite');
            if (inv) { set('b42_council_invite', inv); u.searchParams.delete('invite');
                       history.replaceState(null, '', u.toString()); }
            if (k && /^B42-/i.test(k)) {
                set(LS_KEY, k.toUpperCase());
                u.searchParams.delete('key');
                history.replaceState(null, '', u.toString());
            }
        } catch (e) {}
    })();

    var saved = get(LS_KEY);
    if (saved) { showMember(saved); return; }
    fetch(API + '/standing?uid=' + encodeURIComponent(uid()))
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (st) { if (st) showJoin(st); })
        .catch(function () {});
})();
