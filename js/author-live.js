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
            mine: 'this is me too', mineTip: 'If these are your papers and the split is wrong, write to us'
        },
        es: {
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
        box.innerHTML = html;
        [].forEach.call(box.querySelectorAll('.agroup'), mountMore);
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

    if (!T) return;
    api('').then(function (d) {
        // Ответа нет — на странице остаётся список, вшитый при сборке. Пустая страница
        // была бы хуже устаревшей: автор, пришедший на своё имя, должен увидеть работы.
        if (d && d.groups && d.groups.length) render(d);
    }).catch(function () {});
})();
