/* Страница автора на живых данных: работы, разложенные по РЕАЛЬНЫМ людям.
 *
 * Владелец 25 августа: «в статистику на их странице добавляем сколько всего в архиве, по
 * разделам, сколько экспресс, сколько полных, сколько с разбором; список полный статей не
 * надо обрезать — у нас же лента с динамической прокруткой».
 *
 * ЧТО ЭТО МЕНЯЕТ. Раньше страница была статикой: список статей вшивался при сборке, а на
 * 46 712 авторов это 46 712 страниц, которые пересобираются при каждой правке шаблона.
 * Теперь тело страницы (имя, соавторы, теги, законы) остаётся статикой — его читает
 * поисковик, — а список работ и статистика приходят из D1 через /api/author. Правка
 * разметки списка больше не требует пересборки ни одной страницы.
 *
 * ПОЧЕМУ ГРУППЫ. Проход по Semantic Scholar показал: 3 011 наших ключей — это несколько
 * разных исследователей под одной подписью (zhang|y — семьдесят восемь человек). Владелец:
 * «лучше две страницы, чем одна с чужими работами». Здесь это сделано группами с якорями,
 * а не разными адресами: человек приходит, кликнув ИМЯ под статьёй, и ещё не знает, который
 * из трёх Пановых ему нужен — страница имени как развилка отвечает тому, что он кликнул.
 * Якорь #s2-<id> даёт ссылку на группу конкретного человека для писем авторам.
 *
 * Группа без идентификатора идёт ПОСЛЕДНЕЙ и говорит о нашей неуверенности в привязке, а
 * не о работах. Слова «не подтверждено» здесь нет намеренно: оно читается как сомнение в
 * самой работе, а сомневаемся мы в себе.
 */
(function () {
    'use strict';

    var box = document.getElementById('search-results');
    if (!box || !box.dataset.akey) return;

    var AKEY = box.dataset.akey;
    var NAME = box.dataset.authorName || '';
    var PAGE = 20;

    var L = (document.documentElement.lang || 'en').slice(0, 2);
    var T = {
        ru: {
            works: ['работа', 'работы', 'работ'], express: 'экспресс', full: 'полных', km: 'с разбором',
            sections: 'Разделы', more: 'Показать ещё', loading: 'Загружаю…',
            people: 'Под этим именем в архиве работы разных исследователей — {n}. ' +
                    'Списки разделены, чтобы чужие работы не попали в чужой список.',
            unattr: 'Работы под этим именем, которые мы пока не отнесли уверенно ни к одному ' +
                    'из исследователей выше. Мы сверяемся с авторскими записями Semantic ' +
                    'Scholar; где они молчат — мы не угадываем.',
            hidden: 'Ещё {g} исследователей с этим именем, {w} работ — они не помещаются на страницу.',
            arch: 'В arXiv {t} работ ({y}) · мы пересказали {o} ({p}%)',
            arcOurs: 'у нас {n}', lgRest: 'не пересказано',
            legend: 'серым — все работы автора в arXiv по годам, голубым — наши пересказы',
            mine: 'это тоже я', mineTip: 'Если это ваши работы и они разделены неверно — напишите нам'
        },
        en: {
            works: ['paper', 'papers'], express: 'express', full: 'full', km: 'with our notes',
            sections: 'Fields', more: 'Show more', loading: 'Loading…',
            people: 'Papers under this name belong to {n} different researchers. ' +
                    'The lists are kept apart so that no one gets someone else’s work.',
            unattr: 'Papers under this name that we have not yet confidently attributed to any ' +
                    'of the researchers above. We follow Semantic Scholar’s author records; ' +
                    'where they are silent, we do not guess.',
            hidden: '{g} more researchers share this name, with {w} papers — too many for one page.',
            arch: '{t} papers on arXiv ({y}) · we retold {o} ({p}%)',
            arcOurs: 'we retold {n}', lgRest: 'not retold yet',
            legend: 'grey — all the author’s arXiv papers by year, blue — our retellings',
            mine: 'this is me too', mineTip: 'If these are your papers and the split is wrong, write to us'
        },
        es: {
            arcOurs: 'hemos contado {n}', lgRest: 'sin contar',
            works: ['trabajo', 'trabajos'], express: 'exprés', full: 'completos', km: 'con nuestras notas',
            sections: 'Áreas', more: 'Ver más', loading: 'Cargando…',
            people: 'Los trabajos con este nombre pertenecen a {n} investigadores distintos. ' +
                    'Las listas se mantienen separadas para que nadie reciba el trabajo ajeno.',
            unattr: 'Trabajos con este nombre que aún no hemos atribuido con seguridad a ninguno ' +
                    'de los investigadores anteriores. Seguimos los registros de autor de ' +
                    'Semantic Scholar; donde callan, no adivinamos.',
            hidden: '{g} investigadores más comparten este nombre, con {w} trabajos.',
            mine: 'yo también soy', mineTip: 'Si son sus trabajos y la división es incorrecta, escríbanos'
        },
        ar: {
            arcOurs: 'لدينا {n}', lgRest: 'لم نروِ بعد',
            works: ['بحث', 'أبحاث'], express: 'موجزة', full: 'كاملة', km: 'مع ملاحظاتنا',
            sections: 'المجالات', more: 'عرض المزيد', loading: 'جارٍ التحميل…',
            people: 'الأبحاث تحت هذا الاسم تعود إلى {n} باحثين مختلفين. ' +
                    'نفصل القوائم حتى لا يُنسب عمل أحد إلى غيره.',
            unattr: 'أبحاث تحت هذا الاسم لم ننسبها بعد بثقة إلى أي من الباحثين أعلاه. ' +
                    'نعتمد على سجلات المؤلفين في Semantic Scholar؛ وحيث تصمت، لا نخمّن.',
            hidden: 'يشترك {g} باحثين آخرين في هذا الاسم، ولهم {w} بحثًا.',
            mine: 'هذا أنا أيضًا', mineTip: 'إذا كانت هذه أبحاثك والتقسيم غير صحيح، راسلنا'
        },
        fr: {
            arcOurs: 'nous en avons {n}', lgRest: 'non racontés',
            works: ['travail', 'travaux'], express: 'express', full: 'complets', km: 'avec nos notes',
            sections: 'Domaines', more: 'Voir plus', loading: 'Chargement…',
            people: 'Les travaux sous ce nom appartiennent à {n} chercheurs différents. ' +
                    'Les listes restent séparées pour que le travail de l’un ne revienne pas à l’autre.',
            unattr: 'Travaux sous ce nom que nous n’avons pas encore attribués avec certitude ' +
                    'à l’un des chercheurs ci-dessus. Nous suivons les fiches d’auteur de ' +
                    'Semantic Scholar ; là où elles se taisent, nous ne devinons pas.',
            hidden: '{g} autres chercheurs portent ce nom, avec {w} travaux.',
            mine: 'c’est moi aussi', mineTip: 'Si ce sont vos travaux et que la séparation est fausse, écrivez-nous'
        }
    }[L] || null;

    /* Число работ словом. «1 papers» и «1 работ» — мелочь, которую замечают все и
       никто не чинит; на странице, куда учёный приходит по своему имени, это первое,
       что он видит. Русский требует трёх форм, остальные наши языки — двух. */
    function nWorks(n) {
        var f = T.works;
        if (f.length === 3) {
            var d = n % 10, h = n % 100;
            return n + ' ' + (d === 1 && h !== 11 ? f[0]
                : (d >= 2 && d <= 4 && (h < 12 || h > 14)) ? f[1] : f[2]);
        }
        return n + ' ' + (n === 1 ? f[0] : f[1]);
    }

    function ver() {
        return (typeof effVersion === 'function' ? effVersion() : 'popular');
    }

    /* Адрес ручек. В проде сайт и воркер — один источник, поэтому по умолчанию свой же.
       window.B42_API нужен для локального просмотра: страница отдаётся простым файловым
       сервером на 8420, ручек там нет, и без переключателя проверить разметку глазами
       можно было бы только выкладкой. */
    var API = (typeof window.B42_API === 'string' ? window.B42_API : '');

    function api(params) {
        var q = API + '/api/author?key=' + encodeURIComponent(AKEY) +
                '&lang=' + encodeURIComponent(L) + '&version=' + encodeURIComponent(ver()) +
                '&limit=' + PAGE + (params || '');
        return fetch(q).then(function (r) { return r.ok ? r.json() : null; });
    }

    function esc(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    /* Карточки рисует cardHTML из search.js — тот же самый, что в ленте. Своя отрисовка
       здесь была бы третьей копией разметки карточки, а мы уже знаем, чем это кончается:
       правку делают в одной, а расходятся все три. */
    function cards(items) {
        var v = ver();
        return items.map(function (a) {
            a.version = v;
            return (typeof cardHTML === 'function') ? cardHTML(a) : '';
        }).join('');
    }

    function statLine(g) {
        var bits = [nWorks(g.total)];
        if (g.express) bits.push(g.express + ' ' + T.express);
        if (g.full) bits.push(g.full + ' ' + T.full);
        if (g.km) bits.push(g.km + ' ' + T.km);
        var years = (g.first || '').slice(0, 4);
        if (years && (g.last || '').slice(0, 4) !== years) years += '–' + (g.last || '').slice(0, 4);
        if (years) bits.push(years);
        var s = '<div class="agroup-stat">' + esc(bits.join(' · ')) + '</div>';
        if (g.sections && g.sections.length) {
            s += '<div class="agroup-sections">' + esc(T.sections) + ': ' +
                 g.sections.map(function (x) { return esc(x.cat) + ' ' + x.n; }).join(' · ') +
                 '</div>';
        }
        return s;
    }

    /* Заголовок группы. Лучший вариант — имя из записи S2: оно часто полнее нашего
       («Alexander D. Panov» против «A. Panov»), и именно им человек узнаёт своего
       однофамильца. Пока это поле не заполнено, ставить наше имя во все заголовки нельзя:
       четыре одинаковых «A. D. Panov» подряд читаются как сбой вёрстки, а не как четыре
       разных человека. Тогда заголовком становится то, что РЕАЛЬНО их различает, —
       основная область и годы. Это честно: мы показываем то, что знаем. */
    function groupTitle(g) {
        if (g.s2 && g.name) return esc(g.name);
        var sec = (g.sections && g.sections[0]) ? g.sections[0].cat : '';
        var y = (g.first || '').slice(0, 4);
        if (y && (g.last || '').slice(0, 4) !== y) y += '–' + (g.last || '').slice(0, 4);
        return esc([sec, y].filter(Boolean).join(' · '));
    }

    function groupBlock(g, i, many) {
        var id = g.s2 ? ('s2-' + g.s2) : 'unattributed';
        var head = '';
        if (many) {
            // Заголовок группы — имя из записи S2: оно часто полнее нашего, и именно им
            // человек отличает своего однофамильца. Пока проход S2 не заполнил поле,
            // показываем наше — страница не должна ждать чужой работы.
            var title = g.s2 ? groupTitle(g) : '';
            head = '<div class="agroup-head">' +
                '<h3 id="' + esc(id) + '">' + title +
                    (g.s2 && g.name && NAME && g.name !== NAME
                        ? ' <span class="agroup-alias">(' + esc(NAME) + ')</span>' : '') +
                '</h3>' +
                (g.s2 ? '' : '<p class="agroup-note">' + esc(T.unattr) + '</p>') +
                statLine(g) + '</div>';
        }
        return '<section class="agroup" data-s2="' + esc(g.s2 || 'none') + '" data-page="0">' +
            head + '<div class="agroup-list">' + cards(g.items) + '</div>' +
            (g.more ? '<button type="button" class="agroup-more">' + esc(T.more) + '</button>' : '') +
            '</section>';
    }

    function mountMore(sec) {
        var btn = sec.querySelector('.agroup-more');
        if (!btn) return;
        btn.addEventListener('click', function () {
            var p = (+sec.dataset.page || 0) + 1;
            btn.disabled = true;
            btn.textContent = T.loading;
            api('&s2=' + encodeURIComponent(sec.dataset.s2) + '&page=' + p).then(function (d) {
                if (!d || !d.items || !d.items.length) { btn.remove(); return; }
                sec.querySelector('.agroup-list').insertAdjacentHTML('beforeend', cards(d.items));
                sec.dataset.page = p;
                if (d.more) { btn.disabled = false; btn.textContent = T.more; } else { btn.remove(); }
                if (typeof initAllTooltips === 'function') initAllTooltips();
            }).catch(function () { btn.disabled = false; btn.textContent = T.more; });
        });
    }


    /* ─── Пять действий автора ──────────────────────────────────────────────
     *
     * Владелец 25 августа: «подтвердить что всё отлично · добавить статью которой не
     * хватает и где я автор · указать автора который тоже я · убрать статью, это не я ·
     * убрать целиком мою страницу, я против… но только надо прислать письмо с
     * аккредитованного адреса».
     *
     * Порядок кнопок не случаен: сначала то, что человек сделает чаще всего и с
     * удовольствием (подтвердить), в конце — то, что он делает в раздражении (снять
     * страницу). Прятать последнее нельзя: право человека на себя важнее нашей ленты,
     * и если его спрятать, он напишет не нам, а куда-нибудь ещё.
     *
     * Адрес мы спрашиваем, хотя он у нас есть: в облаке лежат только отпечатки адресов,
     * самих адресов там нет. Человеку об этом сказано прямо — иначе вопрос «зачем вы
     * спрашиваете то, что и так знаете» останется без ответа и будет выглядеть подвохом.
     */
    /* ПЯТЬ ДЕЙСТВИЙ АВТОРА. Ни одного поля на странице.
     *
     * Форма с полем «ваш адрес» ушла целиком, и дело не в удобстве: письмо приходит
     * С СОБСТВЕННОГО АДРЕСА автора, и это подтверждение сильнее любого поля, которое
     * можно заполнить чужим адресом. Ни токена, ни базы адресов нам не нужно.
     * Владелец 31.08: «кнопки должны вызывать стандартное действие — открытие
     * почтового клиента; в письмо вставить идентификатор автора и идентификаторы
     * статей, которые он выбрал».
     *
     * Печатать автор всё-таки будет — но В ПИСЬМЕ, где стоят подписанные пропуски.
     * Отдельная строчка «или просто напишите нам» исчезла: это поведение каждой кнопки.
     *
     * pick — что становится выбираемым на странице:
     *   ''     ничего, письмо открывается сразу
     *   'work' квадратик у каждой работы
     *   'group' кружок у каждой группы под этим именем
     */
    var ACTIONS = {
        ru: [
            ['confirm',  'Всё верно, это мои работы', '',
             'Подтверждаю: работы в этом списке мои.'],
            ['add',      'Не хватает моей статьи', '',
             'Не хватает работ (номер arXiv или ссылка, по одной в строке):'],
            ['merge',    'Вон тот автор — тоже я', 'group',
             'Тоже я:'],
            ['remove',   'Эта статья не моя', 'work',
             'Не мои работы:'],
            ['withdraw', 'Уберите мою страницу', '',
             'Прошу убрать эту страницу.']
        ],
        en: [
            ['confirm',  'Correct — these are my papers', '',
             'I confirm: the papers in this list are mine.'],
            ['add',      'A paper of mine is missing', '',
             'Missing papers (arXiv id or link, one per line):'],
            ['merge',    'That author is me as well', 'group',
             'That is me too:'],
            ['remove',   'This paper is not mine', 'work',
             'Not my papers:'],
            ['withdraw', 'Please take my page down', '',
             'Please take this page down.']
        ]
    };
    var UI2 = {
        ru: {
            head: 'Это ваша страница?',
            lead: 'Вы автор и что-то здесь не так — поправим. Нажмите нужное: откроется ' +
                  'ваша почта с готовым письмом. Заполнять здесь ничего не надо — письмо ' +
                  'приходит с вашего адреса, и это и есть подтверждение.',
            hint: {
                confirm: '',
                add: 'Номер работы есть в её адресе на arXiv: arxiv.org/abs/2412.00159 — впишите его в письме.',
                group: 'Отметьте группу, которая тоже вы. Если второе имя — другая страница, откройте её и вставьте адрес в письмо.',
                work: 'Отметьте работы, которые не ваши. Если знаете, чьи они, — напишите в письме.',
                withdraw: ''
            },
            write: 'Написать нам', writeN: 'Написать нам · {n}',
            works: ['работа', 'работы', 'работ'], groups: 'группа',
            copy: 'Скопировать письмо', copied: 'Письмо скопировано',
            noCopy: 'Скопировать не вышло. Напишите на author@bridge42worlds.academy — тема и текст выше.',
            addLine: 'Чьи они, если знаете:'
        },
        en: {
            head: 'Is this your page?',
            lead: 'You are the author and something here is wrong — we will fix it. Press what ' +
                  'you need: your mail app opens with the letter ready. Nothing to fill in here — ' +
                  'the letter comes from your own address, and that is the confirmation.',
            hint: {
                confirm: '',
                add: 'The id is in the arXiv address: arxiv.org/abs/2412.00159 — type it in the letter.',
                group: 'Tick the group that is also you. If the second name is another page, open it and paste its address into the letter.',
                work: 'Tick the papers that are not yours. If you know whose they are, say so in the letter.',
                withdraw: ''
            },
            write: 'Write to us', writeN: 'Write to us · {n}',
            works: ['paper', 'papers', 'papers'], groups: 'group',
            copy: 'Copy the letter', copied: 'Letter copied',
            noCopy: 'Could not copy. Write to author@bridge42worlds.academy — subject and text above.',
            addLine: 'Whose are they, if you know:'
        }
    };

    function claimsBlock() {
        var l = (L === 'ru') ? 'ru' : 'en';
        var t = UI2[l], acts = ACTIONS[l];
        var html = '<section class="aclaim"><h3>' + esc(t.head) + '</h3>' +
            '<p class="aclaim-lead">' + esc(t.lead) + '</p><div class="aclaim-acts">';
        acts.forEach(function (a) {
            html += '<button type="button" class="aclaim-btn" data-act="' + a[0] +
                    '" data-pick="' + a[2] + '">' + esc(a[1]) + '</button>';
        });
        html += '</div><p class="aclaim-hint" hidden></p>' +
            '<div class="aclaim-go" hidden>' +
            '<button type="button" class="aclaim-write"></button>' +
            '<button type="button" class="aclaim-copy"></button>' +
            '<span class="aclaim-said" hidden></span></div></section>';
        return html;
    }

    function mountClaims(root, personId) {
        var l = (L === 'ru') ? 'ru' : 'en';
        var t = UI2[l], acts = ACTIONS[l];
        var sec = root.querySelector('.aclaim');
        if (!sec) return;
        var hint = sec.querySelector('.aclaim-hint');
        var go = sec.querySelector('.aclaim-go');
        var write = sec.querySelector('.aclaim-write');
        var copy = sec.querySelector('.aclaim-copy');
        var said = sec.querySelector('.aclaim-said');
        var cur = null, pick = '';

        function byAct(a) {
            var f = acts.filter(function (x) { return x[0] === a; })[0];
            return f || ['', '', '', ''];
        }
        function plural(n, forms) {
            if (l !== 'ru') return forms[n === 1 ? 0 : 1];
            var m = n % 100;
            if (m > 4 && m < 20) return forms[2];
            m = n % 10;
            return forms[m === 1 ? 0 : (m > 1 && m < 5 ? 1 : 2)];
        }
        /* Отмеченное на странице. Работы опознаём по data-id самой карточки,
           группы — по data-s2 секции: оба признака уже стоят в разметке. */
        function chosenWorks() {
            return Array.prototype.slice.call(
                root.querySelectorAll('.aclaim-tick:checked')).map(function (i) {
                    var card = i.closest('.article-card');
                    return { id: i.value,
                             title: (card && card.querySelector('h2, h3, .card-title')
                                     || {}).textContent || '' };
                });
        }
        function chosenGroup() {
            var r = root.querySelector('.aclaim-pick:checked');
            if (!r) return null;
            var g = r.closest('.agroup');
            var h = g && g.querySelector('.agroup-head h3');
            return { s2: r.value, title: (h ? h.textContent : '').trim() };
        }

        /* Отметки ставим и снимаем по требованию: в обычном состоянии страницы
           их быть не должно — это список работ, а не анкета. */
        function marks(kind) {
            root.querySelectorAll('.aclaim-tick, .aclaim-pick').forEach(function (x) {
                var wrap = x.closest('.aclaim-mark');
                if (wrap) wrap.remove(); else x.remove();
            });
            if (kind === 'work') {
                root.querySelectorAll('.article-card[data-id]').forEach(function (c) {
                    var lab = document.createElement('label');
                    lab.className = 'aclaim-mark';
                    lab.innerHTML = '<input type="checkbox" class="aclaim-tick" value="' +
                        esc(c.dataset.id) + '">';
                    c.insertBefore(lab, c.firstChild);
                });
            } else if (kind === 'group') {
                root.querySelectorAll('.agroup').forEach(function (g) {
                    var h = g.querySelector('.agroup-head');
                    if (!h || (g.dataset.s2 || 'none') === 'none') return;
                    var lab = document.createElement('label');
                    lab.className = 'aclaim-mark';
                    lab.innerHTML = '<input type="radio" name="aclaim-group" ' +
                        'class="aclaim-pick" value="' + esc(g.dataset.s2) + '">';
                    h.insertBefore(lab, h.firstChild);
                });
            }
            root.addEventListener('change', count);
        }
        function count() {
            if (pick === 'work') {
                var n = chosenWorks().length;
                write.textContent = n
                    ? t.writeN.replace('{n}', n + ' ' + plural(n, t.works))
                    : t.write;
            } else if (pick === 'group') {
                var g = chosenGroup();
                write.textContent = g ? t.writeN.replace('{n}', t.groups) : t.write;
            } else {
                write.textContent = t.write;
            }
        }

        /* ПИСЬМО. Зелёного и охры тут нет — есть подставленное и пропуски. Пропуск
           это строка подчёркиваний: в почтовом клиенте её видно, и понятно, что
           вписать. Ссылка на страницу идёт первой: по ней мы найдём человека, даже
           если ключ покажется нам странным. */
        function letter() {
            var a = byAct(cur), NL = '\r\n';
            var blank = '______________________________';
            var body = [
                (l === 'ru' ? 'Страница: ' : 'Page: ') + location.origin + location.pathname,
                (l === 'ru' ? 'Ключ: ' : 'Key: ') + AKEY +
                    (personId ? ' · ' + personId : ''),
                '', a[3]
            ];
            if (pick === 'work') {
                chosenWorks().forEach(function (w) {
                    body.push('  ' + w.id + (w.title ? ' — ' + w.title.trim().slice(0, 90) : ''));
                });
                body.push('', t.addLine, blank);
            } else if (pick === 'group') {
                var g = chosenGroup();
                body.push('  ' + (g ? (g.s2 + (g.title ? ' · ' + g.title : '')) : blank));
                body.push('', (l === 'ru' ? 'Или другая страница (вставьте ссылку):'
                                          : 'Or another page (paste the link):'), blank);
            } else if (cur === 'add') {
                body.push(blank, blank);
            } else {
                body.push('', (l === 'ru' ? 'Что добавить (не обязательно):'
                                          : 'Anything to add (optional):'), blank);
            }
            var subj = (l === 'ru' ? 'Автор: ' : 'Author: ') + (NAME || AKEY) +
                ' — ' + a[1];
            return { subject: subj, body: body.join(NL) };
        }

        sec.querySelectorAll('.aclaim-btn').forEach(function (b) {
            b.addEventListener('click', function () {
                var same = (cur === b.dataset.act);
                sec.querySelectorAll('.aclaim-btn').forEach(function (x) {
                    x.classList.remove('on');
                });
                said.hidden = true;
                if (same) {           // повторное нажатие выключает режим
                    cur = null; pick = ''; marks(''); hint.hidden = true; go.hidden = true;
                    return;
                }
                b.classList.add('on');
                cur = b.dataset.act; pick = b.dataset.pick || '';
                var h = t.hint[pick || cur] || '';
                hint.textContent = h; hint.hidden = !h;
                marks(pick);
                count();
                copy.textContent = t.copy;
                // Выбирать нечего — письмо открывается сразу, без лишнего шага.
                if (!pick) { go.hidden = true; send(); } else { go.hidden = false; }
            });
        });

        function send() {
            var m = letter();
            location.href = 'mailto:author@bridge42worlds.academy?subject=' +
                encodeURIComponent(m.subject) + '&body=' + encodeURIComponent(m.body);
        }
        write.addEventListener('click', send);
        /* Запасной путь: на части машин mailto: не открывает ничего, и кнопка
           тогда выглядит сломанной. Даём тот же текст в буфер. */
        copy.addEventListener('click', function () {
            var m = letter();
            var txt = 'author@bridge42worlds.academy' + '\r\n' + m.subject + '\r\n\r\n' + m.body;
            (navigator.clipboard ? navigator.clipboard.writeText(txt)
                                 : Promise.reject()).then(function () {
                said.hidden = false; said.textContent = t.copied;
            }).catch(function () {
                /* Не скопировалось — говорим об этом, а не про почту: свалить свою
                   неудачу на чужое приложение значит отправить человека чинить не то. */
                said.hidden = false; said.textContent = t.noCopy;
            });
        });
    }

    /* Диаграмма лет в две серии: серым весь arXiv-портфель автора, голубым поверх —
       наши пересказы. Одна картинка отвечает на оба вопроса сразу: «сколько у него
       вообще» и «какую долю мы разобрали». Обычные div-столбики, без библиотек. */
    /* Диаграмма лет ВЛОЖЕННЫМИ множествами (утверждено владельцем на прототипе).
       Колонка — все работы автора в arXiv за год. Внутри снизу вверх: с нашим разбором,
       полные без разбора, экспрессы, и сверху серым — то, чего мы не пересказали.
       Так одна картинка отвечает сразу на «сколько он написал» и «какую долю мы взяли».

       Прежняя версия рисовала две серии рядом — серую и голубую. Рядом стоящие столбики
       читаются как сравнение двух независимых величин, а здесь одна ВХОДИТ в другую;
       вложение показывает это без подписи. */
    function archChart(arch) {
        var det = {};
        (arch.oursDetail || []).forEach(function (r) { det[r.y] = r; });
        var years = Object.keys(arch.byYear || {});
        Object.keys(det).forEach(function (y) { if (years.indexOf(y) === -1) years.push(y); });
        years.sort();
        if (years.length < 2) return '';
        years = years.slice(-26);
        var mx = 1;
        years.forEach(function (y) {
            mx = Math.max(mx, arch.byYear[y] || 0, (det[y] || {}).n || 0);
        });
        var H = 116;
        var bars = years.map(function (y) {
            var all = arch.byYear[y] || 0;
            var o = det[y] || { n: 0, ex: 0, km: 0 };
            var km = o.km, ex = o.ex;
            var fullNoKm = Math.max(0, (o.n - ex) - km);
            var rest = Math.max(0, all - o.n);
            var u = H / mx;
            function seg(n, cls) {
                return n ? '<i class="' + cls + '" style="height:' +
                    Math.max(3, Math.round(n * u)) + 'px"></i>' : '';
            }
            // nWorks, а не хвост словаря: иначе «1 papers» и «1 работ» —
            // мелочь, которую замечают все.
            var tip = y + ': ' + nWorks(all);
            if (o.n) tip += ' \u00b7 ' + T.arcOurs.replace('{n}', o.n);
            var lab = (Number(y) % 5 === 0 || y === years[years.length - 1]) ? y.slice(2) : '';
            return '<span class="abar" title="' + esc(tip) + '">' +
                   '<span class="abar-stack">' + seg(rest, 'abar-rest') + seg(ex, 'abar-ex') +
                   seg(fullNoKm, 'abar-full') + seg(km, 'abar-km') + '</span>' +
                   '<i class="abar-yr">' + lab + '</i></span>';
        }).join('');
        return '<div class="abars">' + bars + '</div>' +
               '<div class="abars-legend">' +
               '<span><i class="lg lg-rest"></i>' + esc(T.lgRest) + '</span>' +
               '<span><i class="lg lg-ex"></i>' + esc(T.express) + '</span>' +
               '<span><i class="lg lg-full"></i>' + esc(T.full) + '</span>' +
               '<span><i class="lg lg-km"></i>' + esc(T.km) + '</span></div>';
    }

    function archLine(arch, ours) {
        var y = arch.first && arch.last && arch.first !== arch.last
            ? arch.first + '–' + arch.last : (arch.first || '');
        var pct = arch.total ? Math.round(ours * 100 / arch.total) : 0;
        return '<p class="arch-line">' + esc(
            T.arch.replace('{t}', arch.total).replace('{y}', y)
                  .replace('{o}', ours).replace('{p}', pct)) + '</p>';
    }

    function render(d) {
        var many = d.groups.length > 1;
        var html = '';
        if (many) {
            html += '<p class="agroup-intro">' +
                esc(T.people.replace('{n}', d.people || d.groups.length)) + '</p>';
        }
        html += d.groups.map(function (g, i) { return groupBlock(g, i, many); }).join('');
        if (d.hiddenGroups) {
            html += '<p class="agroup-intro">' +
                esc(T.hidden.replace('{g}', d.hiddenGroups).replace('{w}', d.hiddenWorks)) + '</p>';
        }
        // Кнопки автора — СВЕРХУ, под портретом и до списка (владелец 25.08: «кнопки
        // должны быть под дашбордом, а не внизу — до конца прокрутки можно и не дойти»).
        // Мой первый вариант ставил их после списка «сначала посмотри, потом жалуйся» —
        // но у автора с полусотней работ до низа действительно никто не долистает.
        // Портфель arXiv — над кнопками: сначала полная картина человека, потом действия.
        var head = '';
        if (d.archive && d.archive.total) {
            head += archLine(d.archive, d.stats ? d.stats.total : 0) + archChart(d.archive);
        }
        html = head + claimsBlock() + html;
        if (window.B42Live) B42Live.swap(box, html);
        else box.innerHTML = html;
        [].forEach.call(box.querySelectorAll('.agroup'), mountMore);
        mountClaims(box, (d.groups[0] && d.groups[0].s2) || '');
        if (typeof initAllTooltips === 'function') initAllTooltips();
        if (typeof initReveal === 'function') initReveal();

        // Общая строка над телом страницы — та статистика, которую просил владелец.
        var top = document.querySelector('.tag-stats');
        if (top && d.stats && d.stats.total) {
            var s = d.stats, bits = [nWorks(s.total)];
            if (s.express) bits.push(s.express + ' ' + T.express);
            if (s.full) bits.push(s.full + ' ' + T.full);
            if (s.km) bits.push(s.km + ' ' + T.km);
            var y = (s.first || '').slice(0, 4);
            if (y && (s.last || '').slice(0, 4) !== y) y += '–' + (s.last || '').slice(0, 4);
            if (y) bits.push(y);
            var ico = top.querySelector('svg');
            top.innerHTML = (ico ? ico.outerHTML + ' ' : '') + esc(bits.join(' · '));
        }
        // Якорь из адреса отрабатываем сами: разметка появилась после разбора страницы,
        // и браузер к своему моменту прокрутки этих заголовков ещё не видел.
        if (location.hash) {
            var t = document.getElementById(location.hash.slice(1));
            if (t) t.scrollIntoView({ block: 'start' });
        }
    }

    // Перерисовка по требованию: search.js зовёт её, когда читатель очистил поиск или
    // переключил уровень сложности. Данные берём заново — уровень меняет тексты карточек.
    var _last = null;
    window.B42AuthorLive = function () {
        if (_last) render(_last);
        api('').then(function (d) { if (d && d.groups && d.groups.length) { _last = d; render(d); } })
               .catch(function () {});
    };

    if (!T) return;
    api('').then(function (d) {
        _last = d;
        // Ответа нет — на странице остаётся список, вшитый при сборке. Пустая страница
        // была бы хуже устаревшей: автор, пришедший на своё имя, должен увидеть работы.
        if (d && d.groups && d.groups.length) render(d);
    }).catch(function () {});
})();
