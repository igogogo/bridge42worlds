/* Экран ожидания: пока статья переводится или пишется — читатель играет, а не смотрит
   на спиннер. Идея владельца (ночь 2026-07-30): «пока идёт — надо что-то показать
   интересное: факты, мини-опрос с неожиданным ответом, баллы и звания как в науке».

   Источник — data/facts-<lang>.json: занятные факты, отсылки к фантастике и вопросы,
   собранные из УЖЕ НАПИСАННЫХ статей (facts_build.py). Ничего не генерируется на лету:
   ожидание не должно стоить денег.

   Баллы живут в localStorage. Когда появится вход (DevOps), их можно будет поднять
   на сервер — формат b42_score готов к этому: {points, answered, correct}.
   API: B42Waiting.open({title, promise}) → показывает экран, закрывает по разрешению
   промиса; B42Waiting.rank() → текущее звание. */
(function () {
    var LANG = (function () {
        var p = location.pathname.split('/'), i = p.indexOf('lang');
        if (i >= 0 && p[i + 1]) return p[i + 1];
        var q = new URLSearchParams(location.search).get('lang');
        if (q) return q;
        try { return localStorage.getItem('b42_lang') || 'ru'; } catch (e) { return 'ru'; }
    })();

    /* Звания — по научной лестнице, а не «уровень 7». Читателю понятно без объяснений,
       и это тот же язык, что у самого сайта. Пороги пологие в начале: первое звание
       должно прийти в первую же сессию, иначе игра не начинается. */
    var RANKS = {
        ru: ['Любопытный', 'Наблюдатель', 'Лаборант', 'Аспирант', 'Кандидат наук', 'Доктор наук', 'Профессор', 'Академик'],
        en: ['Curious', 'Observer', 'Lab assistant', 'Graduate', 'PhD', 'Doctor of Science', 'Professor', 'Academician'],
        es: ['Curioso', 'Observador', 'Ayudante', 'Doctorando', 'Doctor', 'Doctor en Ciencias', 'Profesor', 'Académico'],
        fr: ['Curieux', 'Observateur', 'Assistant', 'Doctorant', 'Docteur', 'Docteur ès sciences', 'Professeur', 'Académicien'],
        ar: ['فضولي', 'مراقب', 'مساعد مختبر', 'باحث', 'دكتور', 'دكتور في العلوم', 'أستاذ', 'عالِم']
    };
    var STEPS = [0, 3, 10, 25, 60, 120, 250, 500];

    var T = {
        ru: { wait: 'Готовим статью', sub: 'Обычно это занимает около минуты', quiz: 'Как думаете?',
              right: 'Верно', wrong: 'Мимо — но интуиция обычно ошибается именно тут',
              next: 'Ещё факт', src: 'откуда это', score: 'баллы', rank: 'звание', ready: 'Статья готова' },
        en: { wait: 'Preparing the article', sub: 'Usually about a minute', quiz: 'What do you think?',
              right: 'Correct', wrong: 'Off — intuition usually fails exactly here',
              next: 'Another fact', src: 'source', score: 'points', rank: 'rank', ready: 'Article is ready' },
        es: { wait: 'Preparando el artículo', sub: 'Suele tardar un minuto', quiz: '¿Qué opinas?',
              right: 'Correcto', wrong: 'Fallaste — la intuición suele fallar justo aquí',
              next: 'Otro dato', src: 'fuente', score: 'puntos', rank: 'rango', ready: 'El artículo está listo' },
        fr: { wait: "Préparation de l'article", sub: "En général une minute", quiz: 'Qu\'en pensez-vous ?',
              right: 'Correct', wrong: "Raté — l'intuition se trompe justement ici",
              next: 'Autre fait', src: 'source', score: 'points', rank: 'rang', ready: "L'article est prêt" },
        ar: { wait: 'نُحضّر المقال', sub: 'عادةً نحو دقيقة', quiz: 'ما رأيك؟',
              right: 'صحيح', wrong: 'خطأ — الحدس يخطئ هنا عادةً',
              next: 'حقيقة أخرى', src: 'المصدر', score: 'نقاط', rank: 'رتبة', ready: 'المقال جاهز' }
    };
    var t = T[LANG] || T.en;

    function score() {
        try { return JSON.parse(localStorage.getItem('b42_score') || '{}'); } catch (e) { return {}; }
    }
    function addPoints(n, correct) {
        var s = score();
        s.points = (s.points || 0) + n;
        s.answered = (s.answered || 0) + 1;
        if (correct) s.correct = (s.correct || 0) + 1;
        try { localStorage.setItem('b42_score', JSON.stringify(s)); } catch (e) {}
        return s;
    }
    function rank(points) {
        var names = RANKS[LANG] || RANKS.en, p = points != null ? points : (score().points || 0), i = 0;
        for (var k = 0; k < STEPS.length; k++) if (p >= STEPS[k]) i = k;
        return { name: names[i], next: STEPS[i + 1] || null, points: p };
    }

    var cache = null;
    function load() {
        if (cache) return Promise.resolve(cache);
        return fetch('/data/facts-' + LANG + '.json')
            .then(function (r) { return r.ok ? r.json() : { facts: [], quizzes: [] }; })
            .then(function (d) { cache = d; return d; })
            .catch(function () { return { facts: [], quizzes: [] }; });
    }
    function pick(a) { return a && a.length ? a[Math.floor(Math.random() * a.length)] : null; }

    /* Начинка карточки — общая для полноэкранного ожидания и для встроенного в выдачу:
       факт или мини-опрос плюс строка звания. Вынесена отдельно, чтобы вторая форма
       не была копией первой: любая правка вопроса-ответа должна доходить до обеих. */
    function mount(body, foot) {
        function paintRank() {
            if (!foot) return;
            var r = rank();
            foot.textContent = r.name + ' · ' + r.points + ' ' + t.score;
        }
        paintRank();

        function showFact(d) {
            var f = pick(d.facts);
            if (!f) { body.innerHTML = ''; return; }
            body.innerHTML = '<p class="b42-fact">' + f.t + '</p>' +
                '<a class="b42-fact-src" href="' + f.url + '">' + t.src + ' →</a>';
        }
        function showQuiz(d) {
            var q = pick(d.quizzes);
            if (!q) return showFact(d);
            body.innerHTML = '<div class="b42-quiz-q">' + t.quiz + '<b>' + q.q + '</b></div>' +
                '<div class="b42-quiz-opts">' + q.options.map(function (o) {
                    return '<button type="button" class="b42-opt">' + o + '</button>';
                }).join('') + '</div><div class="b42-quiz-res"></div>';
            var res = body.querySelector('.b42-quiz-res');
            body.querySelectorAll('.b42-opt').forEach(function (b) {
                b.addEventListener('click', function () {
                    var ok = b.textContent === q.answer;
                    body.querySelectorAll('.b42-opt').forEach(function (x) {
                        x.disabled = true;
                        if (x.textContent === q.answer) x.classList.add('right');
                        else if (x === b) x.classList.add('wrong');
                    });
                    addPoints(ok ? 3 : 1, ok);   // за попытку тоже балл: играть должно быть не страшно
                    paintRank();
                    res.innerHTML = '<span class="' + (ok ? 'ok' : 'no') + '">' +
                        (ok ? t.right : t.wrong) + '</span> <a href="' + q.url + '">' + t.src + ' →</a>';
                });
            });
        }

        return load().then(function (d) {
            // Каталога может не быть (не собран, не доехал) — тогда карточка показала бы
            // полосу загрузки над пустотой. Пустое ожидание хуже отсутствующего:
            // говорим об этом вызывающему, и он снимает карточку целиком.
            if (!(d.facts || []).length && !(d.quizzes || []).length) return null;
            (Math.random() < 0.55 ? showQuiz : showFact)(d);
            return function again() { (Math.random() < 0.5 ? showQuiz : showFact)(d); };
        });
    }

    function open(opts) {
        opts = opts || {};
        var ov = document.createElement('div');
        ov.className = 'b42-wait';
        ov.innerHTML =
            '<div class="b42-wait-box">' +
              '<div class="b42-wait-head"><b>' + (opts.title || t.wait) + '</b>' +
                '<span class="b42-wait-sub">' + t.sub + '</span></div>' +
              '<div class="b42-wait-bar"><i></i></div>' +
              '<div class="b42-wait-body"></div>' +
              '<div class="b42-wait-foot"><span class="b42-rank"></span>' +
                '<button type="button" class="b42-wait-next">' + t.next + '</button></div>' +
            '</div>';
        document.body.appendChild(ov);
        document.body.classList.add('b42-wait-open');

        mount(ov.querySelector('.b42-wait-body'), ov.querySelector('.b42-rank'))
            .then(function (again) {
                if (!again) {   // каталог пуст — прячем и кнопку «ещё факт», и подвал
                    ov.querySelector('.b42-wait-foot').style.display = 'none';
                    return;
                }
                ov.querySelector('.b42-wait-next').addEventListener('click', again);
            });

        function close(result) {
            document.body.classList.remove('b42-wait-open');
            ov.remove();
            return result;
        }
        if (opts.promise && opts.promise.then) {
            return opts.promise.then(close, function (e) { close(); throw e; });
        }
        return { close: close };
    }

    /* Встроенная форма — для ожиданий, которые нельзя перекрывать шторкой: поиск по
       смыслу идёт секунды, но читатель в это время смотрит на своё же поле ввода, и
       модальное окно поверх выдачи выглядело бы поломкой. Карточка встаёт НА МЕСТО
       будущего результата и исчезает, когда он приходит.

       Порог delay: быстрый (кэшированный) ответ не должен мигать карточкой — она
       появляется, только если ждём дольше указанного. */
    function inline(host, opts) {
        opts = opts || {};
        if (!host) return opts.promise;
        var delay = opts.delay != null ? opts.delay : 700;
        var node = null, done = false;

        var timer = setTimeout(function () {
            if (done) return;
            node = document.createElement('div');
            node.className = 'b42-wait-inline';
            node.innerHTML =
                '<div class="b42-wait-head"><b>' + (opts.title || t.wait) + '</b></div>' +
                '<div class="b42-wait-bar"><i></i></div>' +
                '<div class="b42-wait-body"></div>' +
                '<div class="b42-wait-foot"><span class="b42-rank"></span>' +
                  '<button type="button" class="b42-wait-next">' + t.next + '</button></div>';
            // В начало контейнера, а не в конец: в нём может лежать предыдущая выдача,
            // и карточка «идёт поиск» под старым списком читается как часть результата.
            host.insertBefore(node, host.firstChild);
            mount(node.querySelector('.b42-wait-body'), node.querySelector('.b42-rank'))
                .then(function (again) {
                    if (!node) return;
                    if (!again) { node.remove(); node = null; return; }   // показывать нечего
                    node.querySelector('.b42-wait-next').addEventListener('click', again);
                });
        }, delay);

        function stop(result) {
            done = true;
            clearTimeout(timer);
            if (node) { node.remove(); node = null; }
            return result;
        }
        if (opts.promise && opts.promise.then) {
            return opts.promise.then(stop, function (e) { stop(); throw e; });
        }
        return { close: stop };
    }

    window.B42Waiting = { open: open, inline: inline, rank: rank, score: score };
})();
