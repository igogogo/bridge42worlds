/* Карусель миниатюр в ленте.
 *
 * Владелец 2026-08-25: «динамики не хватает — на экране я вижу всего две-три карточки,
 * а так они ещё будут крутиться». Только десктоп, по его же условию.
 *
 * ОТКУДА КАДРЫ. tools/carousel_frames.py отбирает из картинок PDF годные для блока 130 px
 * (не серые, не почти белые, не панорамы) и кладёт рядом с обложкой c_0..c_2.webp шириной
 * 400 px — ровно под .card-img-wrap на тройной плотности. Сколько кадров у какой статьи,
 * говорит data/carousel.json.
 *
 * ПОЧЕМУ ОТДЕЛЬНЫМ МОДУЛЕМ, А НЕ ПРАВКОЙ cardHTML. Ленту рисуют ДВА места (js/search.js
 * cardHTML и js/scroll.js drawRelated), и обе разметки ещё и лежат в кэше у читателей.
 * Модуль ничего не требует от разметки: находит .card-img-wrap, достаёт из адреса картинки
 * идентификатор статьи и достраивается сам. Выключить его — убрать один тег script.
 *
 * ЧЕГО ЗДЕСЬ СОЗНАТЕЛЬНО НЕТ.
 *   · Смены раз в секунду. Владелец просил секунду, но три карточки, мигающие вразнобой
 *     рядом с текстом, читать невозможно — это не лента, а гирлянда. Поставлено 3.5 с;
 *     менять здесь, в HOLD.
 *   · Работы за экраном. Крутится только то, что видно: иначе браузер честно перерисовывает
 *     всю ленту, и на слабой машине это слышно вентилятором.
 *   · Предзагрузки всех кадров. Три кадра на карточку × двадцать карточек — полтора мегабайта
 *     на входе ради картинок, которых читатель может и не увидеть. Кадр грузится перед показом.
 */
(function () {
    'use strict';

    // Ручки подбора. Значения по умолчанию — ниже; window.B42CarouselOpts перебивает их,
    // если задан ДО загрузки скрипта. Заведено ради страницы подбора (carousel-demo.html):
    // спорить о том, три секунды или полторы, дешевле, глядя на живую ленту, чем правя код.
    var OPT = window.B42CarouselOpts || {};

    var MODE = OPT.mode || 'slide';                 // 'slide' — ВЫЕЗЖАЕТ сбоку, 'fade' — перетекает
    var FADE = OPT.fade || 620;                     // длительность движения, мс
    var HOLD = OPT.hold || 3500;                    // сколько кадр держится на экране, мс
    var MIN_FRAMES = OPT.minFrames || 2;            // меньше двух кадров — карточка статична
    var MIN_W = 900;        // ниже этого лента однополосная: карусель не для неё
    var TICK = 250;         // как часто проверяем, кому пора меняться
    var MAP_URL = '/data/carousel.json';

    // ── Гейты. Каждый — причина не запускаться вовсе ──────────────────────────
    // «Уменьшить движение» в системе — не про вкус: у части людей анимация вызывает
    // физический дискомфорт. Здесь это не деградация, а ровно то поведение, что было
    // до карусели: статичная обложка.
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    if (window.innerWidth < MIN_W) return;
    // Тонкий указатель = мышь. На планшете шириной 1024 карусель не нужна: там карточка
    // почти во всю ширину, и движение мешает так же, как на телефоне.
    if (window.matchMedia && !window.matchMedia('(pointer: fine)').matches) return;

    var map = null;             // id → сколько кадров
    var cards = [];             // живые карточки на экране
    var seen = [];              // уже обработанные обёртки
    var io = null;

    /* Из адреса картинки: /lang/ru/archive/2026-08-17/2608.16724v1/t_ai.webp
       Разметку не трогаем — всё нужное уже есть в src. */
    function partsOf(img) {
        var src = img.getAttribute('src') || '';
        var m = src.match(/\/archive\/[^/]+\/([^/]+)\//);
        if (!m) return null;
        return { base: src.slice(0, src.lastIndexOf('/') + 1), id: m[1] };
    }

    /* Сдвиг слоя по горизонтали в процентах ширины блока.
       Стилем это задать нельзя: положение меняется в момент подмены, а не по классу
       состояния, и промежуточных состояний два (едет / мгновенно вернулся). Inline-стиль
       заодно перебивает `.article-card:hover img { transform: scale(1.03) }` — у карточек
       с каруселью приближения по наведению больше нет, там наведение и так означает
       «остановись», а два разных ответа на одно движение мыши читаются как дёрганье. */
    function move(el, pct, animate) {
        el.style.transition = animate
            ? 'transform ' + FADE + 'ms cubic-bezier(.4, 0, .2, 1)'
            : 'none';
        // translate3d, а не translateX: запись с третьей координатой заставляет браузер
        // вынести слой на видеокарту и двигать его там. Разница на глаз небольшая, но
        // ровно она отделяет плавное движение от мелких рывков на слабой машине.
        el.style.transform = 'translate3d(' + pct + '%, 0, 0)';
    }

    function cardOf(wrap) {
        for (var i = 0; i < cards.length; i++) {
            if (cards[i].wrap === wrap) return cards[i];
        }
        return null;
    }

    function attach(wrap, idx) {
        if (seen.indexOf(wrap) !== -1) return;
        var img = wrap.querySelector('img');
        if (!img) return;
        var p = partsOf(img);
        if (!p) return;
        seen.push(wrap);
        var n = map[p.id] || 0;
        // Владелец 2026-08-25: «если картинка одна, то её не надо дёргать». Один кадр плюс
        // обложка — это не карусель, а перекидывание туда-сюда каждые 3.5 с: глаз читает
        // такое как сбой, а не как движение. Нужен круг хотя бы из трёх картинок.
        if (n < MIN_FRAMES) return;              // карточка остаётся статичной, как раньше

        // Второй слой для плавной подмены. Одним элементом обойтись нельзя: смена src
        // у единственной картинки даёт мигание в момент загрузки, и тем заметнее, чем
        // медленнее сеть.
        var b = document.createElement('img');
        // Прозрачный пиксель, а не пустой src: <img> без адреса — невалидная разметка, и
        // часть браузеров рисует на его месте значок «картинка не загрузилась». Здесь он
        // спрятан за краем обёртки и всё равно не виден, но полагаться на это незачем.
        b.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
        b.alt = '';
        b.setAttribute('aria-hidden', 'true');   // для читалки это тот же самый рисунок
        b.className = 'b42-c-layer';
        // loading="lazy" здесь ВРЕДЕН: слой стоит за правым краем обёртки, браузер считает
        // его невидимым и откладывает загрузку до момента показа — ровно то опоздание,
        // из-за которого между кадрами мелькал фон. Грузим сами и заранее, см. preload().
        if (MODE === 'slide') {
            // В режиме выезда прятать прозрачностью не нужно: слой стоит ЗА правым краем
            // обёртки, а у неё overflow:hidden — его не видно, пока он не поехал.
            move(b, 100, false);
        } else {
            b.style.opacity = '0';
        }
        wrap.appendChild(b);
        wrap.classList.add('has-carousel');

        var urls = [img.getAttribute('src')];    // нулевой кадр — обложка, она уже загружена
        for (var i = 0; i < n; i++) urls.push(p.base + 'c_' + i + '.webp');

        cards.push({
            wrap: wrap, layers: [img, b], top: 0, cur: 0, urls: urls,
            vis: false, hover: false,
            // Сдвиг старта: без него все карточки на экране меняются в одну секунду,
            // и лента моргает целиком. Пяти фаз хватает, чтобы движение читалось как
            // живое, а не как стробоскоп.
            //
            // Фазу ХРАНИМ, а не тратим один раз при создании. Первая версия задавала её
            // только здесь — и карточки всё равно шли в унисон: пока читатель не долистал
            // до ленты, сроки у всех успевали истечь, а наблюдатель видимости, поймав их
            // одним пакетом, назначал всем один и тот же новый срок. Сдвиг стирался ровно
            // в тот момент, ради которого был нужен.
            phase: (idx % 5) * (HOLD / 5),
            next: Date.now() + HOLD + (idx % 5) * (HOLD / 5)
        });

        wrap.addEventListener('mouseenter', function () { setHover(wrap, true); });
        wrap.addEventListener('mouseleave', function () { setHover(wrap, false); });
    }

    function setHover(wrap, on) {
        var c = cardOf(wrap);
        if (!c) return;
        c.hover = on;
        // Задержать, а не пропустить: иначе кадр сменится в ту же миллисекунду, когда
        // человек увёл мышь, — ровно то, чего он не ждал.
        if (!on) c.next = Date.now() + HOLD + c.phase;
    }

    /* Готовит СЛЕДУЮЩИЙ кадр в невидимом слое, пока текущий досиживает свои HOLD.

       Первая версия начинала загрузку в тот момент, когда кадру пора было выезжать, —
       и владелец сразу это увидел: «лагает, между кадрами какой-то фон». Фон и был:
       пустой слой выезжал первым, а картинка появлялась в нём уже на ходу. Три с половиной
       секунды простоя между кадрами — более чем достаточно, чтобы всё пришло заранее;
       грузить надо было не позже, а раньше. */
    function preload(c) {
        var back = c.layers[1 - c.top];
        var url = c.urls[(c.cur + 1) % c.urls.length];
        if (back.getAttribute('src') === url) return;
        back.onerror = function () {
            back.onerror = null;
            // Битый кадр выкидываем из круга навсегда: иначе карточка каждые 3.5 с
            // упиралась бы в него и стояла.
            var i = c.urls.indexOf(url);
            if (i > 0) c.urls.splice(i, 1);
            if (c.cur >= c.urls.length) c.cur = 0;
        };
        back.setAttribute('src', url);
    }

    function advance(c) {
        var nextIdx = (c.cur + 1) % c.urls.length;
        var back = c.layers[1 - c.top];
        var front = c.layers[c.top];
        var url = c.urls[nextIdx];

        // Кадр ещё не готов — не двигаемся вовсе. Показать пустой слой хуже, чем задержать
        // смену: читатель не знает, когда она должна была случиться, а пустоту видит.
        if (back.getAttribute('src') !== url) {
            preload(c);
            c.next = Date.now() + 400;
            return;
        }
        if (!back.complete || !back.naturalWidth) {
            c.next = Date.now() + 400;       // ещё едет по сети — подождём и проверим снова
            return;
        }

        function show() {
            if (MODE === 'slide') {
                // Новый кадр едет справа к нулю, старый уезжает влево — движение читается
                // как «лист перевернули», а не как «картинка мигнула».
                move(back, 0, true);
                move(front, -100, true);
                // Уехавший слой возвращаем за правый край БЕЗ анимации, иначе он проедет
                // обратно через всю обёртку у читателя на глазах. И сразу заказываем в него
                // следующий кадр — пусть грузится, пока новый висит свои HOLD.
                setTimeout(function () {
                    move(front, 100, false);
                    preload(c);
                }, FADE + 60);
            } else {
                back.style.opacity = '1';
                front.style.opacity = '0';
                setTimeout(function () { preload(c); }, FADE + 60);
            }
            c.top = 1 - c.top;
            c.cur = nextIdx;
            c.next = Date.now() + HOLD;
        }

        // decode() досчитывает картинку в пиксели ДО того, как она попадёт в кадр анимации.
        // Без него бывает, что загрузка уже завершилась, а первый кадр выезда рисуется ещё
        // пустым: браузер честно декодирует «по дороге». Это и есть та самая мелкая заминка.
        if (back.decode) {
            back.decode().then(show, show);
        } else {
            show();
        }
    }

    function tick() {
        if (document.hidden) return;            // во вкладке за спиной крутить незачем
        var now = Date.now();
        for (var i = 0; i < cards.length; i++) {
            var c = cards[i];
            if (!c.vis || c.hover || c.urls.length < 2) continue;
            if (now >= c.next) advance(c);
        }
    }

    /* Лента дорисовывается на скролле (renderMoreFeed) и перерисовывается при поиске.
       Наблюдаем за контейнером, а не вешаемся на конкретный вызов. */
    function scan() {
        var box = document.getElementById('search-results');
        if (!box) return;
        var wraps = box.querySelectorAll('.card-img-wrap');
        for (var i = 0; i < wraps.length; i++) {
            attach(wraps[i], i);
            if (io && !wraps[i].dataset.cObs) {
                wraps[i].dataset.cObs = '1';
                io.observe(wraps[i]);
            }
        }
        // Карточки и обёртки, выброшенные из DOM при перерисовке ленты, забываем: иначе
        // списки растут весь сеанс и tick перебирает мусор.
        cards = cards.filter(function (c) { return c.wrap.isConnected; });
        seen = seen.filter(function (w) { return w.isConnected; });
    }

    function start() {
        io = new IntersectionObserver(function (entries) {
            entries.forEach(function (e) {
                var c = cardOf(e.target);
                if (!c) return;
                c.vis = e.isIntersecting;
                if (e.isIntersecting) {
                    // Заказываем следующий кадр в ту же секунду, когда карточка показалась:
                    // у него есть все HOLD миллисекунд на загрузку, и к моменту выезда он
                    // готов. Раньше загрузка начиналась в момент подмены — отсюда заминка.
                    preload(c);
                    if (c.next < Date.now()) c.next = Date.now() + HOLD + c.phase;
                }
            });
        }, { rootMargin: '100px' });

        scan();
        var box = document.getElementById('search-results');
        if (box) new MutationObserver(scan).observe(box, { childList: true });
        setInterval(tick, TICK);
    }

    function boot() {
        if (!document.getElementById('search-results')) return;
        // Справочник тянем ЛЕНИВО и только здесь: в индекс ленты его класть нельзя —
        // тот грузится у каждого читателя на всех языках, и 13 августа из него как раз
        // выкидывали лишние поля ради веса. Отдельный файл ~90 КБ, только на десктопе.
        fetch(MAP_URL, { cache: 'force-cache' })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (j) { if (j) { map = j; start(); } })
            .catch(function () { /* нет справочника — лента просто статична, как раньше */ });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
