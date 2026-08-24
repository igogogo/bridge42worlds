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
              sending: 'Отправляю…',
              myVotes: 'Как я голосовал',
              edit: 'изменить', del: 'удалить', myProps: 'Мои предложения',
              delAsk: 'Удалить это предложение? Его ещё не видел совет.',
              voteTitle: 'Голосование', yes: 'за', no: 'против', abstain: 'воздержаться',
              why: 'Коротко почему (необязательно)', voted: 'Голос учтён. Можно передумать до закрытия заседания.',
              results: 'Итоги', members: 'участников совета', err: 'Не получилось. Попробуйте ещё раз.',
              cabinet: 'Ваше участие', cabRead: ' статей прочитано', cabProps: ' предложений',
              cabVotes: ' голосов', cabSince: ' в совете с', cabMembers: ' участников всего',
              onAgenda: 'в повестке',
              confirmTitle: 'Вы голосуете по этим пунктам',
              confirmNote: 'Проверьте выбор. После подтверждения голос будет записан — изменить его можно до закрытия заседания.',
              confirmYes: 'Проголосовать', cancel: 'Вернуться к выбору',
              yourProposal: 'Ваше предложение совету:',
              needMail: 'Сначала оставьте почту — без неё голос не принимается.',
              firstAsk: 'Представьтесь совету',
              nickPh: 'Ник — под ним вас увидят остальные',
              inMeetings: 'заседаний',
              mailAsk: 'Куда присылать повестку и итоги',
              mailNote: 'Уведомления о заседаниях приходят почтой — иначе о решениях можно узнать, только зайдя сюда. Оставьте поле пустым, если писем не нужно.',
              mailSave: 'Сохранить', mailOk: 'Записали. Повестка и итоги придут на этот адрес.',
              mailOff: 'Хорошо, писем не будет.',
              submitAll: 'Отправить мои решения', submitted: 'Ваши решения отправлены.',
              pickAll: 'Ответьте на вопросы выше — отмеченное отправится одной кнопкой.',
              chosen: 'выбрано', ofQ: 'из',
              hidden: 'Итоги откроются после закрытия заседания',
              votedN: 'уже проголосовали', nextMeet: 'следующее заседание',
              history: 'Заседания', closedM: 'закрыто', openM: 'идёт',
              decidedN: 'решений', questionsN: 'вопросов',
              roles: 'Состав совета', roleHuman: 'люди', roleAi: 'ИИ-участники',
              memo: 'Как устроен совет',
              fName: 'Как к вам обращаться (необязательно)',
              fMail: 'Почта для отчётов (необязательно)',
              fHint: 'Оба поля можно пропустить — ключ выдадим всё равно. Почта нужна только для писем о заседаниях.',
              getKey: 'Получить ключ',
              haveKey: 'У меня есть ключ', enter: 'Войти', badKey: 'ключ не найден — проверьте',
              invited: 'Вас пригласили в наблюдательный совет. Нажмите — и вы внутри: повестка, голосование, предложения.',
              whyBtn: 'откуда этот вопрос',
              whyTitle: 'Откуда взялся этот вопрос',
              whyAbout: 'О чём речь',
              whyOptions: 'Что означает каждый вариант',
              close: 'Закрыть',
              freeze: '❄ Заморозить вопрос',
              freezeTitle: 'Заморозить вопрос',
              freezeNote: 'Заморозка снимает вопрос с голосования: сегодня решения по нему не будет. К следующему заседанию мы переформулируем его с учётом вашего объяснения. Вашего имени не увидит никто — только причину.',
              freezePh: 'Почему сейчас не время? Что должно измениться, чтобы вопрос можно было решать',
              freezeShort: 'Объясните хотя бы одним предложением — иначе следующему заседанию не с чем работать.',
              freezeYes: 'Заморозить',
              frozenLabel: '❄ Снят с голосования',
              frozenAnon: 'Вопрос заморозил участник совета. Кто именно — не раскрывается.',
              frozenWhy: 'Причина',
              frozenNext: 'Вопрос вернётся на следующее заседание в переформулированном виде.',
              frozenQuorum: 'Замораживается второй раз — по регламенту решение примет кворум ИИ-участников.',
              unfreeze: 'Снять мою заморозку',
              oneAtATime: 'У вас уже заморожен другой вопрос. По регламенту — один вопрос на участника за заседание: сначала снимите ту заморозку.' },
        en: { need: 'To join, open {n} more articles — you have read {seen}.',
              can: 'You have read {seen} articles. That is enough to join the council.',
              join: 'Join the council', joined: 'You are a council member', key: 'Your key',
              keyNote: 'Write it down. It replaces login and password: use it on any device.',
              propose: 'Propose to the council', placeholder: 'What to change, add or stop doing',
              send: 'Send', sent: 'Proposal recorded — it will reach the next agenda.',
              sending: 'Sending…',
              myVotes: 'How I voted',
              edit: 'edit', del: 'delete', myProps: 'My proposals',
              anyLang: 'The council works in English, but write in any language you think in: Russian, Arabic, French. The secretary translates proposals when the agenda is assembled.',
              delAsk: 'Delete this proposal? The council has not seen it yet.',
              voteTitle: 'Vote', yes: 'for', no: 'against', abstain: 'abstain',
              why: 'Briefly why (optional)', voted: 'Vote counted. You may change it until the meeting closes.',
              results: 'Results', members: 'council members', err: 'Did not work. Please try again.',
              draftWarn: '⚠ Your choices are saved only in this browser — press the button below, otherwise they will NOT be counted.',
              sentMark: '✓ counted by the server',
              cabinet: 'Your participation', cabRead: ' articles read', cabProps: ' proposals',
              cabVotes: ' votes', cabSince: ' member since', cabMembers: ' members total',
              onAgenda: 'on agenda',
              fName: 'How to address you (optional)',
              fMail: 'Email for reports (optional)',
              fHint: 'Both can be skipped — you get the key anyway. Email is only for meeting notices.',
              getKey: 'Get the key',
              haveKey: 'I have a key', enter: 'Enter', badKey: 'key not found — check it',
              invited: 'You have been invited to the council. One click and you are in: agenda, voting, proposals.',
              whyBtn: 'where this question came from',
              whyTitle: 'Where this question came from',
              whyAbout: 'What it is about',
              whyOptions: 'What each option means',
              close: 'Close',
              freeze: '❄ Freeze this question',
              freezeTitle: 'Freeze this question',
              freezeNote: 'Freezing takes the question off the vote: no decision on it today. For the next meeting we will rephrase it taking your explanation into account. Nobody sees your name — only the reason.',
              freezePh: 'Why is now not the time? What has to change before this can be decided',
              freezeShort: 'Explain in at least one sentence — otherwise the next meeting has nothing to work with.',
              freezeYes: 'Freeze',
              frozenLabel: '❄ Off the vote',
              frozenAnon: 'A council member froze this question. Who exactly is not disclosed.',
              frozenWhy: 'Reason',
              frozenNext: 'The question returns to the next meeting, rephrased.',
              frozenQuorum: 'Frozen for the second time — by the rules the AI members decide it by their own quorum.',
              unfreeze: 'Remove my freeze',
              oneAtATime: 'You already froze another question. One question per member per meeting — remove that freeze first.' }
    };
    /* Совет ведётся НА ОДНОМ ЯЗЫКЕ — английском. Решение владельца 15 августа.
       До этого интерфейс кабинета был переведён на пять языков, а содержание — повестка,
       вопросы, варианты, решения — существовало только по-русски: араб видел арабские
       кнопки и русский текст вопроса. Обещание языком оболочки, которого не давали по
       существу, хуже честного одноязычия. Продукт (статьи) остаётся на пяти языках —
       там многоязычность и есть ценность; совет это управление, ему нужен один рабочий
       язык, понятный будущим участникам: авторам разобранных работ и университетам. */
    var L = T.en;
    /* ar/es/fr — из файлов стратега (data/council/live-strings.<lang>.json): формулировки
       его, каркас мой, в js он не лезет. Пока файл едет, работает английский; приехал —
       надписи меняются на месте. Ключи сверяются: перевод с дырами хуже честного
       английского, потому что читается как недоделка. */
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
            '<div class="cl-cab"></div>'));
        // Места под блоки размечаем СРАЗУ и в нужном порядке: голосование, почта, состав,
        // история, предложения. Иначе порядок задаёт то, чей запрос вернулся первым, —
        // и предложения (без запроса) обгоняли голосование (с запросом).
        ['slot-vote', 'slot-mail', 'slot-people', 'slot-hist', 'slot-prop'].forEach(function (c) {
            var s = document.createElement('div');
            s.className = 'cl-slot ' + c;
            host.appendChild(s);
        });
        cabinet(key);
        mountVoting(key);          // ради него и пришли — сразу за кабинетом
        mountEmail(key);           // связь: без почты участник не узнает об итогах
        mountPeople();             // кто ещё в совете и насколько он живой
        mountHistory(key);         // что уже было решено, как голосовал я, когда следующее
        // Предложения — ПОСЛЕ голосования: сначала ответь на поставленные вопросы,
        // потом ставь свои (владелец 13 августа).
        // ВАЖНО: искать элементы ВНУТРИ этого блока, а не по всей странице.
        // Владелец 15 августа: «нажал кнопку несколько раз, нет реакции, а потом поле
        // очистилось». Предложение уходило с первого раза, но ответ печатался в чужой
        // элемент: host.querySelector('.cl-msg') находит ПЕРВЫЙ .cl-msg в кабинете, а это
        // строка голосования — она стоит выше по порядку слотов. Человек смотрел на
        // кнопку и не видел ничего, а «записано» появлялось в двух экранах над ней.
        var propBox = block(
            '<div class="cl-prop"><h4>' + esc(L.propose) + '</h4>' +
            '<p class="cl-note">' + esc(L.anyLang) + '</p>' +
            '<textarea class="cl-text" rows="3" placeholder="' + esc(L.placeholder) + '"></textarea>' +
            '<button type="button" class="cl-send">' + esc(L.send) + '</button>' +
            '<div class="cl-msg cl-prop-msg"></div></div>');
        host.querySelector('.slot-prop').appendChild(propBox);
        var propText = propBox.querySelector('.cl-text');
        var propMsg = propBox.querySelector('.cl-prop-msg');
        propBox.querySelector('.cl-send').onclick = function () {
            var t = propText.value.trim();
            if (!t) { propMsg.textContent = L.placeholder; return; }
            var btn = this;
            btn.disabled = true;
            // Отклик СРАЗУ, а не после ответа сервера: иначе секунда молчания читается
            // как «кнопка не работает», и человек жмёт ещё раз.
            propMsg.textContent = L.sending || '…';
            api('/propose', { key: key, text: t, lang: LANG }).then(function (r) {
                btn.disabled = false;
                propMsg.textContent = r && r.ok ? L.sent : L.err;
                if (r && r.ok) { propText.value = ''; myProposals(propBox, key); }
            }).catch(function () { btn.disabled = false; propMsg.textContent = L.err; });
        };
        myProposals(propBox, key);
    }

    /* Свои предложения — СРАЗУ ПОД ФОРМОЙ, где человек их и пишет.
       Владелец 15 августа: «не вижу своих предложений на странице, как их изменить и
       удалить». Список был — но в блоке «Ваше участие» наверху страницы, в двух экранах
       от формы. Место, где вещь создают, и место, где ей управляют, должны совпадать. */
    function myProposals(box, key) {
        var wrap = box.querySelector('.cl-mine');
        if (!wrap) {
            wrap = document.createElement('div');
            wrap.className = 'cl-mine';
            box.querySelector('.cl-prop').appendChild(wrap);
        }
        fetch(API + '/me?key=' + encodeURIComponent(key))
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (d) {
                var list = (d && d.proposals) || [];
                if (!list.length) { wrap.innerHTML = ''; return; }
                wrap.innerHTML = '<div class="cl-myv-head">' + esc(L.myProps) + '</div>' +
                    '<ul class="cl-list cl-props">' + list.map(function (p) {
                        return '<li data-pid="' + esc(String(p.id)) + '">' +
                               '<span class="cl-p-text">' + esc(p.text || '') + '</span>' +
                               (p.meeting
                                 ? ' <em>' + esc(L.onAgenda) + '</em>'
                                 : '<span class="cl-p-act">' +
                                   '<button type="button" class="cl-p-edit">' + esc(L.edit) + '</button>' +
                                   '<button type="button" class="cl-p-del">' + esc(L.del) + '</button>' +
                                   '</span>') + '</li>';
                    }).join('') + '</ul>';
                bindProposalActions(wrap, key);
            }).catch(function () {});
    }

    /* Правка и удаление своего предложения прямо в списке. Владелец 15 августа:
       «предложения пусть накапливаются, чтобы я мог и изменить, и удалить каждое».
       Редактирование на месте, без отдельной формы: список и есть рабочее место. */
    function bindProposalActions(box, key) {
        box.querySelectorAll('.cl-props li').forEach(function (li) {
            var pid = li.dataset.pid;
            var span = li.querySelector('.cl-p-text');
            var edit = li.querySelector('.cl-p-edit');
            var del = li.querySelector('.cl-p-del');
            if (edit) edit.onclick = function () {
                if (li.querySelector('textarea')) return;
                var ta = document.createElement('textarea');
                ta.className = 'cl-p-in'; ta.rows = 3; ta.value = span.textContent;
                var save = document.createElement('button');
                save.type = 'button'; save.className = 'cl-p-save'; save.textContent = L.mailSave;
                span.style.display = 'none';
                li.insertBefore(ta, li.firstChild.nextSibling);
                li.querySelector('.cl-p-act').appendChild(save);
                ta.focus();
                save.onclick = function () {
                    var v = ta.value.trim();
                    if (!v) return;
                    save.disabled = true;
                    api('/propose', { key: key, id: Number(pid), text: v, lang: LANG })
                        .then(function (r) {
                            if (r && r.ok) { span.textContent = v; ta.remove(); save.remove(); span.style.display = ''; }
                            else { save.disabled = false; }
                        }).catch(function () { save.disabled = false; });
                };
            };
            if (del) del.onclick = function () {
                if (!confirm(L.delAsk)) return;
                del.disabled = true;
                api('/unpropose', { key: key, id: Number(pid) })
                    .then(function (r) { if (r && r.ok) li.remove(); else del.disabled = false; })
                    .catch(function () { del.disabled = false; });
            };
        });
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
                    '';
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

    /* Окно подтверждения перед отправкой голосов. Показывает ровно то, за что человек
       расписывается: каждый вопрос с выбранным вариантом словами (а не «o2») и своё
       предложение, если он его написал. Отменить можно на этом же шаге. */
    function confirmVotes(m, picked, proposal, go) {
        var rows = (m.agenda || []).filter(function (q) { return picked[q.id]; })
            .map(function (q) {
                var label = picked[q.id];
                (q.options || []).forEach(function (o, i) {
                    var id = (o && typeof o === 'object') ? String(o.id || (i + 1)) : String(i + 1);
                    if (id === picked[q.id]) label = (o && o.label) || String(o);
                });
                if (!q.options || !q.options.length) label = L[picked[q.id]] || picked[q.id];
                return '<li><span class="cd-q">' + esc(q.title || q.id) + '</span>' +
                       '<span class="cd-a">' + esc(label) + '</span></li>';
            }).join('');
        var wrap = modal(
            '<h4>' + esc(L.confirmTitle) + '</h4>' +
            '<p class="cl-note">' + esc(L.confirmNote) + '</p>' +
            '<ul class="cl-confirm">' + rows + '</ul>' +
            (proposal ? '<div class="cl-confirm-prop"><b>' + esc(L.yourProposal) + '</b>' +
                        '<p>' + esc(proposal.slice(0, 400)) + '</p></div>' : '') +
            '<div class="cl-modal-btns">' +
            '<button type="button" class="cl-cancel">' + esc(L.cancel) + '</button>' +
            '<button type="button" class="cl-yes">' + esc(L.confirmYes) + '</button>' +
            '</div>');
        wrap.querySelector('.cl-yes').onclick = function () { wrap.remove(); go(); };
    }

    /* Почта к ключу. Ключ — вход, почта — связь. Владелец 13 августа: «надо обязательно
       где-то почту попросить к ключу, потому что уведомления всё-таки почта; после входа
       это канал коммуникации». Спрашиваем ПОСЛЕ входа: сначала человек видит, во что
       вступил, и только потом решает, впускать ли нас в свой ящик. */
    function mountEmail(key) {
        fetch(API + '/me?key=' + encodeURIComponent(key))
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (d) {
                var m = (d && d.member) || {};
                // Первый вход — это когда ни ника, ни почты. Тогда форма стоит ВВЕРХУ и
                // просит оба поля разом: ник, под которым участника увидят остальные, и
                // адрес для повестки. Дальше она же служит настройками.
                var first = !m.name && !m.email;
                var b = block('<div class="cl-mail' + (first ? ' cl-first' : '') + '">' +
                    '<h4>' + esc(first ? L.firstAsk : L.mailAsk) + '</h4>' +
                    '<p class="cl-note">' + esc(L.mailNote) + '</p>' +
                    '<input type="text" class="cl-nick-in" value="' + esc(m.name || '') + '" placeholder="' + esc(L.nickPh) + '">' +
                    '<input type="email" class="cl-mail-in" value="' + esc(m.email || '') + '" placeholder="name@mail.com">' +
                    '<button type="button" class="cl-mail-save">' + esc(L.mailSave) + '</button>' +
                    '<div class="cl-msg cl-mail-msg"></div></div>');
                var slot = host.querySelector(first ? '.slot-vote' : '.slot-mail');
                if (first) slot.parentNode.insertBefore(b, slot);   // первый вход — выше всего
                else slot.appendChild(b);
                b.querySelector('.cl-mail-save').onclick = function () {
                    var v = b.querySelector('.cl-mail-in').value.trim();
                    var nick = b.querySelector('.cl-nick-in').value.trim();
                    var btn = this; btn.disabled = true;
                    api('/profile', { key: key, email: v, name: nick }).then(function (r) {
                        btn.disabled = false;
                        b.querySelector('.cl-mail-msg').textContent =
                            r && r.ok ? (v ? L.mailOk : L.mailOff) : L.err;
                        if (r && r.ok) b.classList.remove('cl-first');
                    }).catch(function () { btn.disabled = false;
                        b.querySelector('.cl-mail-msg').textContent = L.err; });
                };
            }).catch(function () {});
    }

    /* Состав совета: кто ещё здесь и насколько живой. Ники, роли и число заседаний, в
       которых человек голосовал. Владелец 13 августа: «в списке все ники чтобы были
       видны и какая-то активность — в скольких заседаниях участвовал». */
    function mountPeople() {
        fetch(API + '/board').then(function (r) { return r.ok ? r.json() : null; })
            .then(function (d) {
                if (!d || !(d.people || []).length) return;
                var mm = d.members || {};
                var head = esc(L.roles) + ': ' + (mm.total || 0) +
                    (mm.human ? ' · ' + mm.human + ' ' + esc(L.roleHuman) : '') +
                    (mm.ai ? ' · ' + mm.ai + ' ' + esc(L.roleAi) : '');
                var rows = d.people.map(function (p) {
                    return '<li><b>' + esc(p.nick) + '</b>' +
                        (p.kind === 'ai' ? ' <span class="cl-mark">' + esc(L.roleAi) + '</span>' : '') +
                        '<span class="cl-mnums">' + (p.meetings || 0) + ' ' + esc(L.inMeetings) + '</span></li>';
                }).join('');
                host.querySelector('.slot-people').appendChild(block('<div class="cl-people"><h4>' + head + '</h4>' +
                    '<ul class="cl-mlist">' + rows + '</ul></div>'));
            }).catch(function () {});
    }

    /* Кабинет заседаний: что было, что решено, когда следующее. Владелец 13 августа:
       «нужно иметь как кабинет заседаний — прошло, по каждому что решено, сколько
       голосов, какие предложения на следующий совет, когда дата». */
    function mountHistory(key) {
        Promise.all([
            fetch(API + '/meetings').then(function (r) { return r.ok ? r.json() : null; }),
            key ? fetch(API + '/me?key=' + encodeURIComponent(key))
                    .then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; })
                : Promise.resolve(null)
        ]).then(function (res) {
            var d = res[0], me = res[1];
            if (!d || !(d.meetings || []).length) return;

            // Свои голоса — по заседаниям. Владелец 15 августа: «если я зайду потом, то по
            // каждому заседанию увижу, за что я голосовал, так?» До этого в кабинете было
            // только ЧИСЛО голосов: участник помнил, что голосовал, но не помнил как —
            // а именно это и нужно, чтобы вернуться к вопросу и передумать со знанием дела.
            var mine = {};
            (me && me.votes || []).forEach(function (v) {
                (mine[v.meeting] = mine[v.meeting] || []).push(v);
            });

            var box = block('<div class="cl-hist"><h4>' + esc(L.history) + '</h4>' +
                (d.next ? '<p class="cl-note">' + esc(L.nextMeet) + ': <b>' + esc(d.next) + '</b></p>' : '') +
                '<ul class="cl-mlist">' + d.meetings.map(function (m) {
                    var mark = m.status === 'closed' ? L.closedM : L.openM;
                    return '<li data-meet="' + esc(m.date) + '"><b>' + esc(m.date) + '</b> ' +
                        '<span class="cl-mark">' + esc(mark) + '</span>' +
                        '<span class="cl-mnums">' + m.questions + ' ' + esc(L.questionsN) +
                        (m.status === 'closed' ? ' · ' + m.decided + ' ' + esc(L.decidedN) : '') +
                        ' · ' + (m.voted || 0) + ' ' + esc(L.votedN) + '</span>' +
                        (mine[m.date] ? '<div class="cl-myvotes"></div>' : '') + '</li>';
                }).join('') + '</ul></div>');
            host.querySelector('.slot-hist').appendChild(box);

            // Подписи вопросов и вариантов лежат в файле заседания. Тянем только те файлы,
            // где человек действительно голосовал, — обычно один-два, а не всю историю.
            Object.keys(mine).forEach(function (date) {
                var cell = box.querySelector('li[data-meet="' + date + '"] .cl-myvotes');
                if (!cell) return;
                fetch('/data/council/' + date + '.json', { cache: 'no-store' })
                    .then(function (r) { return r.ok ? r.json() : null; })
                    .then(function (mt) {
                        var byId = {};
                        ((mt && mt.agenda) || []).forEach(function (q) { byId[q.id] = q; });
                        cell.innerHTML = '<div class="cl-myv-head">' + esc(L.myVotes) + '</div>' +
                            mine[date].map(function (v) {
                                var q = byId[v.question] || {};
                                var label = v.vote;
                                (q.options || []).forEach(function (o, i) {
                                    var id = (o && typeof o === 'object') ? String(o.id || (i + 1)) : String(i + 1);
                                    if (id === v.vote) label = (o && o.label) || String(o);
                                });
                                if (!q.options || !q.options.length) label = L[v.vote] || v.vote;
                                return '<div class="cl-myv"><span class="cl-myv-q">' +
                                       esc(q.title || v.question) + '</span>' +
                                       '<span class="cl-myv-a">' + esc(label) + '</span></div>';
                            }).join('');
                    }).catch(function () {});
            });
        }).catch(function () {});
    }

    /* Голосование по ближайшему заседанию. Вопросы берём из того же файла, по которому
       строится страница заседания, — один источник, иначе списки разойдутся. */
    function mountVoting(key) {
        // Повестку берём всегда свежую. Это единственный файл, который обязан быть
        // сегодняшним: заморозка снимает вопрос с голосования, секретарь переписывает
        // формулировку — а браузер с кэшем показал бы вчерашнее заседание и принял бы
        // голоса по вопросу, которого уже нет.
        fetch('/data/council/upcoming.json', { cache: 'no-store' })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (m) {
                if (!m || !m.agenda || !m.agenda.length) return;
                var box = document.createElement('div');
                box.className = 'cl-box cl-vote';
                box.innerHTML = '<h4>' + esc(L.voteTitle) + ' · ' + esc(m.date || '') + '</h4>';
                box.__ids = [];
                var picked = {};
                var sent = load('cl_sent_' + m.date, []);
                function updatePicked() {
                    var el = box.querySelector('.cl-picked');
                    if (el) el.textContent = L.chosen + ': ' + Object.keys(picked).length +
                                             ' ' + L.ofQ + ' ' + m.agenda.length;
                }
                m.agenda.forEach(function (q) {
                    var row = document.createElement('div');
                    row.className = 'cl-q';
                    box.__ids.push(q.id);
                    // Кнопки — по ВАРИАНТАМ вопроса, если они есть. Семь вопросов из восьми
                    // в повестке 16 августа — это выбор («куда пустить бюджет», «что считать
                    // бриллиантом»), и «за/против» на них не отвечает ни на что. Варианты
                    // приходят строками или объектами {id, label} — приводим к одному виду.
                    var opts = (q.options || []).map(function (o, i) {
                        return (o && typeof o === 'object')
                            ? { v: String(o.id || (i + 1)), t: String(o.label || o.id || ('вариант ' + (i + 1))), note: o.note || '' }
                            : { v: String(i + 1), t: String(o), note: '' };
                    });
                    if (!opts.length) {
                        opts = ['yes', 'no', 'abstain'].map(function (v) { return { v: v, t: L[v], note: '' }; });
                    }
                    // Знак вопроса открывает ОКНО С АБЗАЦЕМ, а не строку-подсказку.
                    // Владелец 13 августа: «при выборе должен быть тултип с объяснением,
                    // откуда возник вопрос, только чтобы тултип был не строкой, а абзацем,
                    // окошко». Пояснения к вариантам переехали туда же: раньше они жили в
                    // title= и на телефоне не показывались вовсе — там нет наведения мыши.
                    row.innerHTML = '<div class="cl-qt">' + esc(q.title || q.id) +
                        ' <button type="button" class="cl-why-btn" aria-label="' + esc(L.whyBtn) +
                        '" title="' + esc(L.whyBtn) + '">?</button></div>' +
                        '<div class="cl-frozen" hidden></div>' +
                        (key ? '<div class="cl-btns' + (opts.length > 3 ? ' cl-btns-wide' : '') + '">' +
                            opts.map(function (o) {
                                return '<button type="button" data-v="' + esc(o.v) + '">' +
                                       esc(o.t) + '</button>';
                            }).join('') + '</div>' +
                            '<div class="cl-qfoot"><button type="button" class="cl-freeze-btn">' +
                            esc(L.freeze) + '</button></div><div class="cl-res"></div>'
                             : '<div class="cl-res"></div>');
                    box.appendChild(row);
                    row.querySelector('.cl-why-btn').onclick = function () { showWhy(q, opts); };
                    if (key) row.querySelectorAll('.cl-btns button').forEach(function (b) {
                        b.onclick = function () {
                            if (row.classList.contains('is-frozen')) return;
                            row.querySelectorAll('.cl-btns button').forEach(function (x) { x.classList.remove('on'); });
                            b.classList.add('on');
                            picked[q.id] = b.dataset.v;
                            updatePicked();
                        };
                    });
                    if (key) {
                        row.querySelector('.cl-freeze-btn').onclick = function () {
                            askFreeze(key, m, q, row, function () { loadFrozen(m.date, box, key); });
                        };
                    }
                    // Заморозка снимает выбор: голосовать по снятому вопросу нельзя.
                    row.__clearPick = function () { delete picked[q.id]; updatePicked();
                        row.querySelectorAll('.cl-btns button').forEach(function (x) { x.classList.remove('on'); }); };
                });
                if (key) {
                    var foot = document.createElement('div');
                    foot.className = 'cl-vote-foot';
                    foot.innerHTML = '<div class="cl-picked"></div>' +
                        '<button type="button" class="cl-submit">' + esc(L.submitAll) + '</button>' +
                        '<div class="cl-msg cl-submit-msg"></div>';
                    box.appendChild(foot);
                    box.__foot = foot;
                    // Выбор есть, подтверждения сервера нет — говорим прямо, а не молчим.
                    if (Object.keys(picked).length && sent.length === 0) {
                        var warn = document.createElement('div');
                        warn.className = 'cl-msg cl-draft-warn';
                        warn.style.color = '#b31b1b';
                        warn.textContent = L.draftWarn;
                        foot.insertBefore(warn, foot.firstChild);
                    } else if (sent.length) {
                        var okm = document.createElement('div');
                        okm.className = 'cl-msg';
                        okm.style.color = '#2e7d32';
                        okm.textContent = L.sentMark + ' · ' + sent.length;
                        foot.insertBefore(okm, foot.firstChild);
                    }
                    foot.querySelector('.cl-submit').onclick = function () {
                        var ids = Object.keys(picked);
                        if (!ids.length) {
                            foot.querySelector('.cl-submit-msg').textContent = L.pickAll;
                            return;
                        }
                        // Голос — это ОСОЗНАННОЕ действие, а не касание кнопки. Владелец
                        // 13 августа: «пока кнопка не нажата, нельзя считать, что я что-то
                        // выбрал: я могу выбрать предварительно и потом изменить». Поэтому
                        // выбор до сих пор жил только в браузере, а здесь человек видит
                        // разом всё, за что расписывается, — и своё предложение тоже.
                        var proposal = (host.querySelector('.cl-text') || {}).value || '';
                        confirmVotes(m, picked, proposal.trim(), function () {
                            var btn = foot.querySelector('.cl-submit'); btn.disabled = true;
                            var left = ids.length, bad = 0, needMail = false, wasFrozen = false;
                            ids.forEach(function (qid) {
                                api('/vote', { key: key, meeting: m.date, question: qid, vote: picked[qid] })
                                    .then(function (r) {
                                        if (!(r && r.ok)) {
                                            bad++;
                                            if (r && r.error === 'email_required') needMail = true;
                                            // Кто-то заморозил вопрос, пока человек выбирал.
                                            // Не ошибка отправки, а изменившаяся повестка.
                                            if (r && r.error === 'frozen') wasFrozen = true;
                                        }
                                    })
                                    .catch(function () { bad++; })
                                    .then(function () {
                                        if (--left === 0) {
                                            btn.disabled = false;
                                            foot.querySelector('.cl-submit-msg').textContent =
                                                needMail ? L.needMail
                                              : wasFrozen ? L.frozenAnon
                                              : (bad ? L.err : L.submitted);
                                            // «Мой голос» ≠ «голос учтён». Заседание 23.08:
                                            // выбор жил в браузере, человек видел пометки и
                                            // считал, что проголосовал, а сервер не получил
                                            // ничего — кнопку отправки не нажали или ключ не
                                            // был введён. Подтверждение храним ТОЛЬКО после
                                            // ответа сервера ok и показываем отдельным знаком.
                                            if (!bad && !needMail) {
                                                store('cl_sent_' + m.date, ids);
                                                var w = box.querySelector('.cl-draft-warn');
                                                if (w) w.remove();
                                            }
                                            if (needMail) {
                                                var mi = host.querySelector('.cl-mail-in');
                                                if (mi) { mi.focus(); mi.scrollIntoView({ block: 'center' }); }
                                            }
                                            loadResults(m.date, box);
                                            loadFrozen(m.date, box, key);
                                        }
                                    });
                            });
                        });
                    };
                }
                host.querySelector('.slot-vote').appendChild(box);
                loadResults(m.date, box);
                loadFrozen(m.date, box, key);
            }).catch(function () {});
    }

    /* Окно «откуда взялся вопрос». Три части: происхождение (кто и на каком основании
       вынес), суть, и что означает каждый вариант. Всё абзацами: вопрос повестки — это
       не подпись к кнопке, в одну строку он честно не сжимается. */
    function showWhy(q, opts) {
        var parts = '';
        if (q.origin) parts += '<h5>' + esc(L.whyTitle) + '</h5><p>' + esc(q.origin) + '</p>';
        if (q.body) parts += '<h5>' + esc(L.whyAbout) + '</h5><p>' + esc(q.body) + '</p>';
        var notes = (opts || []).filter(function (o) { return o.note; });
        if (notes.length) {
            parts += '<h5>' + esc(L.whyOptions) + '</h5><ul class="cl-why-opts">' +
                notes.map(function (o) {
                    return '<li><b>' + esc(o.t) + '</b> — ' + esc(o.note) + '</li>';
                }).join('') + '</ul>';
        }
        modal('<h4>' + esc(q.title || q.id) + '</h4><div class="cl-why-body">' + parts + '</div>' +
              '<div class="cl-modal-btns"><button type="button" class="cl-cancel">' +
              esc(L.close) + '</button></div>');
    }

    /* Заморозка: блокирующий голос с обязательным объяснением. Кнопка сама по себе ничего
       не отправляет — сначала человек пишет причину и подтверждает, как и с голосованием. */
    function askFreeze(key, m, q, row, done) {
        var w = modal('<h4>' + esc(L.freezeTitle) + '</h4>' +
            '<p class="cl-note">' + esc(L.freezeNote) + '</p>' +
            '<div class="cl-freeze-q">' + esc(q.title || q.id) + '</div>' +
            '<textarea class="cl-freeze-why" rows="4" placeholder="' + esc(L.freezePh) + '"></textarea>' +
            '<div class="cl-msg cl-freeze-msg"></div>' +
            '<div class="cl-modal-btns">' +
            '<button type="button" class="cl-cancel">' + esc(L.cancel) + '</button>' +
            '<button type="button" class="cl-yes">' + esc(L.freezeYes) + '</button></div>');
        var ta = w.querySelector('.cl-freeze-why');
        ta.focus();
        w.querySelector('.cl-yes').onclick = function () {
            var why = ta.value.trim();
            var msg = w.querySelector('.cl-freeze-msg');
            if (why.length < 20) { msg.textContent = L.freezeShort; return; }
            this.disabled = true;
            var self = this;
            api('/freeze', { key: key, meeting: m.date, question: q.id, why: why })
                .then(function (r) {
                    if (r && r.ok) { w.remove(); if (row.__clearPick) row.__clearPick(); done(); return; }
                    self.disabled = false;
                    msg.textContent = (r && r.error === 'one_at_a_time') ? L.oneAtATime
                                    : (r && r.error === 'email_required') ? L.needMail
                                    : (r && r.error === 'why_required') ? L.freezeShort : L.err;
                })
                .catch(function () { self.disabled = false; msg.textContent = L.err; });
        };
    }

    /* Что заморожено — показываем всем и всегда, не дожидаясь закрытия заседания. Это не
       расклад голосов: снятый с голосования вопрос обязаны видеть все, иначе люди будут
       ждать решения, которого не будет. Имя заморозившего наружу не идёт. */
    function loadFrozen(meeting, box, key) {
        fetch(API + '/frozen?meeting=' + encodeURIComponent(meeting))
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (d) {
                if (!d || !d.frozen) return;
                box.querySelectorAll('.cl-q').forEach(function (row, i) {
                    var qid = (box.__ids || [])[i];
                    var f = qid && d.frozen[qid];
                    var cell = row.querySelector('.cl-frozen');
                    if (!cell) return;
                    if (!f) { cell.hidden = true; row.classList.remove('is-frozen'); return; }
                    row.classList.add('is-frozen');
                    if (row.__clearPick) row.__clearPick();
                    cell.hidden = false;
                    cell.innerHTML = '<div class="cl-frozen-head">' + esc(L.frozenLabel) + '</div>' +
                        '<p class="cl-frozen-anon">' + esc(L.frozenAnon) + '</p>' +
                        f.why.map(function (t) {
                            return '<p class="cl-frozen-why"><b>' + esc(L.frozenWhy) + ':</b> ' + esc(t) + '</p>';
                        }).join('') +
                        '<p class="cl-note">' + esc(f.quorum ? L.frozenQuorum : L.frozenNext) + '</p>' +
                        (key ? '<button type="button" class="cl-unfreeze">' + esc(L.unfreeze) + '</button>' : '');
                    var un = cell.querySelector('.cl-unfreeze');
                    if (un) un.onclick = function () {
                        un.disabled = true;
                        api('/freeze', { key: key, meeting: meeting, question: qid, undo: true })
                            .then(function () { loadFrozen(meeting, box, key); })
                            .catch(function () { un.disabled = false; });
                    };
                });
            }).catch(function () {});
    }

    /* Общее окно: у совета их уже три (подтверждение голосов, происхождение вопроса,
       заморозка), и каждое городило свою разметку и своё закрытие. */
    function modal(inner) {
        var wrap = document.createElement('div');
        wrap.className = 'cl-modal';
        wrap.innerHTML = '<div class="cl-modal-box">' + inner + '</div>';
        document.body.appendChild(wrap);
        function close() { wrap.remove(); }
        var c = wrap.querySelector('.cl-cancel');
        if (c) c.onclick = close;
        wrap.onclick = function (e) { if (e.target === wrap) close(); };
        return wrap;
    }

    function loadResults(meeting, box) {
        fetch(API + '/results?meeting=' + encodeURIComponent(meeting))
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (d) {
                if (!d) return;
                // Пока заседание идёт, расклад не отдаёт и сервер. Показываем ровно два
                // числа: сколько человек уже высказалось и сколько всего участников —
                // этого хватает, чтобы понять, ждут ли ещё кого-то, и не хватает, чтобы
                // подсмотреть чужой ответ и повторить его не думая.
                var head = box.querySelector('h4');
                if (!d.closed) {
                    var line = box.querySelector('.cl-wait');
                    if (!line) {
                        line = document.createElement('div');
                        line.className = 'cl-wait';
                        box.insertBefore(line, box.children[1] || null);
                    }
                    line.textContent = L.hidden + ' · ' + (d.voted || 0) + ' ' + L.votedN +
                                       (d.members ? ' ' + L.ofQ + ' ' + d.members : '');
                    return;
                }
                if (!d.results) return;
                box.querySelectorAll('.cl-q').forEach(function (row, i) {
                    var qid = (box.__ids || [])[i];
                    var r = qid && d.results[qid];
                    var cell = row.querySelector('.cl-res');
                    if (!r || !cell) return;
                    // Подписи берём с кнопок этого же вопроса: у вопроса с вариантами
                    // ключ итога — идентификатор варианта, и «yes/no» тут ни при чём.
                    var names = {};
                    row.querySelectorAll('.cl-btns button').forEach(function (b) {
                        names[b.dataset.v] = b.textContent;
                    });
                    var parts = Object.keys(r).sort(function (a, b) { return r[b] - r[a]; })
                        .map(function (k) { return (names[k] || L[k] || k) + ': ' + r[k]; });
                    if (parts.length) cell.textContent = parts.join(' · ');
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
