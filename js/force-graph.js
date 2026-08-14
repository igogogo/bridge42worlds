// Общий движок force-графа для облаков тегов / учёных / законов.
// Различия (данные, цвета, полые ли узлы, подписи, куда ведёт клик) — в конфиге opts.
// opts: {
//   canvas: id, resizeKey: 'window.__xResize',
//   build: (lang) => Promise<{nodes:[{id,name,...}], links:[[i,j],...]}>,
//   radius: (node) => number,           // node.deg уже проставлен
//   color:  (node) => cssColor,
//   hollow: (node) => bool,             // полое кольцо (вторичные узлы) vs сплошной
//   labelAlways: (node) => bool,        // показывать подпись всегда (не только на ховере/deg>=3)
//   href:   (node, lang) => url|null    // куда вести по клику
//   tooltip: (node) => string|null      // необязательно: текст всплывающей подсказки при наведении
// }
window.createForceGraph = function (opts) {
    var cv = document.getElementById(opts.canvas);
    if (!cv) return;
    var pp = window.location.pathname.split('/'), li = pp.indexOf('lang');
    var lang = (li >= 0 && pp[li + 1]) ? pp[li + 1] : 'ru';

    var ctx = cv.getContext('2d'), W = 0, H = 0, dpr = Math.max(1, window.devicePixelRatio || 1);
    var txtCol = getComputedStyle(document.body).getPropertyValue('--text').trim() || '#2c2c2a';
    var nodes = [], links = [], adj = [], alpha = 1, drag = -1, hover = -1, px = 0, py = 0, downXY = null, ready = false;

    // Кнопка «развернуть на весь экран» — CSS-оверлей поверх текущего канваса (не Fullscreen API:
    // на iOS Safari поддержка нестабильна для произвольных элементов). Канвас всегда лежит прямо
    // в бордер-боксе графа (.mini-graph / #tag-graph / #kg-graph / ...), так что один обработчик
    // здесь в общем движке покрывает все графы сайта разом.
    var fsContainer = cv.parentElement, isFs = false;

    // Тултип при наведении на узел — один div на граф, позиционируется у курсора. Только
    // hover (десктоп); на тач-устройствах наведения нет, там как раньше — тап сразу ведёт по href.
    var tip = null;
    if (opts.tooltip && fsContainer) {
        tip = document.createElement('div');
        tip.className = 'graph-tooltip';
        fsContainer.appendChild(tip);
    }

    // Предупреждение про большие графы (>100 узлов) — с подсказкой на кнопку ⛶ (юзер-фидбек
    // 2026-07-17: облако/эксплорер без фильтра по тегам легко перевал за 200+ узлов, тормозит и
    // нечитаемо). Один текст-шаблон общий для всех графов сайта (мини/облако/эксплорер).
    // Знак предупреждения ставит код (см. updateSizeWarning) — в самих строках его нет,
    // иначе рядом окажутся два предупреждающих знака: наш и вшитый в текст.
    var SIZE_WARN = {
        ru: '{n} объектов — построение графа может занять время. Для просмотра рекомендуем полноэкранный режим (кнопка сверху справа).',
        en: '{n} entities — building the graph may take a moment. For viewing we recommend fullscreen mode (button top right).',
        es: '{n} entidades — construir el grafo puede tardar un momento. Para verlo mejor, recomendamos el modo pantalla completa (botón arriba a la derecha).',
        zh: '{n} 个实体 — 图谱生成可能需要一点时间。建议使用全屏模式查看（右上角按钮）。',
        fr: '{n} entités — la construction du graphe peut prendre un moment. Pour la consultation, nous recommandons le mode plein écran (bouton en haut à droite).',
        ar: '{n} كيان — قد يستغرق بناء الرسم البياني بعض الوقت. للعرض الأفضل، ننصح بوضع ملء الشاشة (الزر أعلى اليمين).'
    };
    var warn = null;
    if (fsContainer) {
        warn = document.createElement('div');
        warn.className = 'graph-size-warning';
        warn.style.display = 'none';
        // Предупреждение советует открыть на весь экран — пусть само туда и открывает.
        // Оно выглядит как кнопка в левом верхнем углу, читатель по нему жал, а оно молчало
        // (юзер 2026-07-29). Теперь это настоящая кнопка.
        warn.setAttribute('role', 'button');
        warn.setAttribute('tabindex', '0');
        warn.style.cursor = 'pointer';
        warn.addEventListener('click', function (e) { e.stopPropagation(); setFs(true); });
        warn.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setFs(true); }
        });
        fsContainer.appendChild(warn);
    }
    // Мобильный лимит узлов (юзер 2026-07-25): на телефоне большой граф не читается и симуляция
    // не доходит до конца — точки виснут по углам. Режем до CAP по степени (оставляем самые связные),
    // с пометкой и ссылкой «показать все» — оверрайд для планшетов и т.п. Касается всех графов (движок общий).
    var MOBILE = window.matchMedia('(max-width: 640px)').matches;
    // Лимит узлов: телефон 50, десктоп 100 (юзер 2026-07-25 — «больше 100 нечитаемо»).
    // В ПОЛНОЭКРАННОМ режиме лимит снимается: там места хватает, показываем всё.
    var CAP = MOBILE ? 50 : 100;
    function graphFull() { try { return localStorage.getItem('b42_graph_full') === '1'; } catch (e) { return false; } }
    function capNodes(nn, ll) {
        if (isFs || graphFull() || nn.length <= CAP) return { nodes: nn, links: ll, from: 0 };
        var deg = nn.map(function () { return 0; });
        ll.forEach(function (l) { deg[l[0]]++; deg[l[1]]++; });
        var order = nn.map(function (_, i) { return i; }).sort(function (a, b) { return deg[b] - deg[a]; }).slice(0, CAP);
        var remap = {}; var out = [];
        order.forEach(function (i) { remap[i] = out.length; out.push(nn[i]); });
        var outL = ll.filter(function (l) { return remap[l[0]] != null && remap[l[1]] != null; })
                     .map(function (l) { return [remap[l[0]], remap[l[1]]]; });
        return { nodes: out, links: outL, from: nn.length };
    }
    var CAP_NOTE = {
        ru: 'Показаны {n} из {tot} (лёгкая мобильная версия — крупный граф на телефоне тормозит). ',
        en: 'Showing {n} of {tot} (light mobile version — a large graph lags on phones). ',
        es: 'Mostrando {n} de {tot} (versión móvil ligera — un grafo grande va lento en el teléfono). ',
        ar: 'عرض {n} من {tot} (نسخة هاتف مبسّطة — الرسم الكبير يتباطأ على الهاتف). ',
        fr: 'Affichage de {n} sur {tot} (version mobile allégée — un grand graphe rame sur téléphone). '
    };
    var SHOW_ALL = { ru: 'показать все', en: 'show all', es: 'mostrar todo', ar: 'عرض الكل',
                     fr: 'tout afficher' };
    function updateSizeWarning(n, cappedFrom) {
        if (!warn) return;
        if (cappedFrom) {
            var t = (CAP_NOTE[lang] || CAP_NOTE.en).replace('{n}', n).replace('{tot}', cappedFrom);
            warn.innerHTML = ((window.B42Icons && B42Icons.warn) ? B42Icons.warn(15) : '⚠') + ' ' + t;
            var a = document.createElement('a');
            a.href = '#'; a.className = 'graph-show-all'; a.textContent = SHOW_ALL[lang] || SHOW_ALL.en;
            a.addEventListener('click', function (e) {
                e.preventDefault();
                try { localStorage.setItem('b42_graph_full', '1'); } catch (_) {}
                rebuild();
            });
            warn.appendChild(a);
            warn.style.display = 'block';
            return;
        }
        if (n <= 100) { warn.style.display = 'none'; return; }
        var tpl = SIZE_WARN[lang] || SIZE_WARN.en;
        warn.textContent = tpl.replace('{n}', n);
        warn.style.display = 'block';
        showBigModal(n);
    }

    // Модалка при большом выборе (юзер 2026-07-25): честно предупреждаем, что будет долго,
    // и сразу даём кнопку «открыть в полноэкранном» — там и лимит снимается, и места хватает.
    var BIG = {
        ru: { t: 'Большой граф', d: 'Выбрано {n} объектов — построение займёт время, а на маленьком поле это плохо читается.', fs: 'Открыть на весь экран', ok: 'Всё равно показать' },
        en: { t: 'Large graph', d: '{n} objects selected — it will take a while and is hard to read in a small frame.', fs: 'Open fullscreen', ok: 'Show anyway' },
        es: { t: 'Grafo grande', d: '{n} objetos seleccionados — tardará y se lee mal en un marco pequeño.', fs: 'Pantalla completa', ok: 'Mostrar igual' },
        ar: { t: 'رسم بياني كبير', d: 'تم اختيار {n} عنصرًا — سيستغرق وقتًا ويصعب قراءته في إطار صغير.', fs: 'ملء الشاشة', ok: 'اعرض على أي حال' },
        fr: { t: 'Grand graphe', d: '{n} objets sélectionnés — le calcul prendra du temps et se lit mal dans un cadre étroit.', fs: 'Plein écran', ok: 'Afficher quand même' }
    };
    var bigShown = false;
    function showBigModal(n) {
        if (bigShown || isFs || !fsContainer) return;
        bigShown = true;
        var L = BIG[lang] || BIG.en;
        var m = document.createElement('div');
        m.className = 'graph-big-modal';
        m.innerHTML = '<div class="gbm-box"><div class="gbm-t">' + L.t + '</div>' +
            '<div class="gbm-d">' + L.d.replace('{n}', n) + '</div>' +
            '<div class="gbm-actions"><button type="button" class="gbm-fs">' + L.fs + '</button>' +
            '<button type="button" class="gbm-ok">' + L.ok + '</button></div></div>';
        fsContainer.appendChild(m);
        m.querySelector('.gbm-fs').addEventListener('click', function () { m.remove(); setFs(true); });
        m.querySelector('.gbm-ok').addEventListener('click', function () { m.remove(); });
        m.addEventListener('click', function (e) { if (e.target === m) m.remove(); });
    }
    function showTip(node, x, y) {
        if (!tip) return;
        var text = opts.tooltip(node);
        if (!text) { tip.style.display = 'none'; return; }
        tip.textContent = text;
        tip.style.display = 'block';
        /* Кламп по контейнеру. Подсказка — 280px, а контейнер на телефоне около 343px:
           у узла возле правого края она вылезала наружу и давала горизонтальную прокрутку
           всей страницы. Раньше координата ставилась как есть (курсор + 14). Комментарий
           «на тач наведения нет» тут не спасал: у канваса touch-action: none, протяжка
           пальцем идёт в ветку hover и подсказку действительно показывает. */
        var box = fsContainer.clientWidth, boxH = fsContainer.clientHeight;
        tip.style.left = Math.max(4, Math.min(x, box - tip.offsetWidth - 8)) + 'px';
        tip.style.top = Math.max(4, Math.min(y, boxH - tip.offsetHeight - 8)) + 'px';
    }
    function hideTip() { if (tip) tip.style.display = 'none'; }

    // Контролы графа (глубина +/-, чекбоксы-фильтры) живут ВНЕ бордер-бокса графа (соседями),
    // поэтому в полноэкранном режиме они пропадали (юзер-фидбек 2026-07-19: "держать +/- зум,
    // чекбокс-меню свернуть, тумблер фона"). При входе в FS переносим реальные DOM-узлы контролов
    // в оверлей внутри fsContainer (перенос сохраняет их обработчики), при выходе — возвращаем на
    // место. fsKeep — всегда видимы (глубина +/-), fsCollapsible — под кнопкой ☰ (свёрнуты).
    var fsBtn, bgBtn, fsPanel, fsCollapseBtn, fsCollapseWrap, ctrlHomes = [];
    var fsKeep = (opts.fsKeep || []).filter(Boolean);
    var fsCollapsible = (opts.fsCollapsible || []).filter(Boolean);
    if (fsContainer) {
        fsBtn = document.createElement('button');
        fsBtn.type = 'button'; fsBtn.className = 'graph-fs-btn'; fsBtn.setAttribute('aria-label', 'fullscreen');
        // рисунок берём из набора, чтобы «во весь экран» здесь и в других местах был одним знаком
        fsBtn.innerHTML = (window.B42Icons && B42Icons.expand) ? B42Icons.expand(18)
            : '<svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 3.6H3.6V9"/><path d="M15 3.6h5.4V9"/><path d="M20.4 15v5.4H15"/><path d="M9 20.4H3.6V15"/></svg>';
        fsBtn.addEventListener('click', function (e) { e.stopPropagation(); setFs(!isFs); });
        fsContainer.appendChild(fsBtn);

        // Тумблер фона (виден только в FS, см. CSS): прозрачный ⇄ сплошной. Прозрачный = сквозь
        // граф видна страница позади (юзер: "смотрится круто").
        bgBtn = document.createElement('button');
        bgBtn.type = 'button'; bgBtn.className = 'graph-fs-bgbtn'; bgBtn.setAttribute('aria-label', 'toggle background');
        bgBtn.textContent = '◑';
        bgBtn.addEventListener('click', function (e) { e.stopPropagation(); fsContainer.classList.toggle('graph-fs-transparent'); });
        fsContainer.appendChild(bgBtn);

        if (fsKeep.length || fsCollapsible.length) {
            fsPanel = document.createElement('div');
            fsPanel.className = 'graph-fs-controls';
            if (fsCollapsible.length) {
                fsCollapseBtn = document.createElement('button');
                fsCollapseBtn.type = 'button'; fsCollapseBtn.className = 'graph-fs-collapse-btn';
                // Кнопка подписана СЛОВОМ, а не только значком. Голый гамбургер над графом
                // читался как «непонятная иконка в окантовке»: владелец 2026-08-01 не смог
                // угадать, чья она и что делает. Значок сам по себе объясняет только тому,
                // кто уже знает ответ.
                var FLT = { ru: 'фильтры', en: 'filters', es: 'filtros', ar: 'المرشحات', fr: 'filtres' };
                var _lang = (document.documentElement.lang || 'en').slice(0, 2);
                var _word = FLT[_lang] || FLT.en;
                fsCollapseBtn.innerHTML = ((window.B42Icons && B42Icons.menu) ? B42Icons.menu(16) : '☰') +
                    '<span class="fs-flt-word">' + _word + '</span>';
                fsCollapseBtn.setAttribute('aria-label', _word);
                fsCollapseWrap = document.createElement('div');
                fsCollapseWrap.className = 'graph-fs-collapse';
                fsCollapseBtn.addEventListener('click', function (e) { e.stopPropagation(); fsCollapseWrap.classList.toggle('open'); });
            }
            fsContainer.appendChild(fsPanel);
        }
        document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && isFs) setFs(false); });
    }
    // Возврат через плейсхолдер, а НЕ insertBefore(el, savedNext): saved-next-сосед может сам
    // оказаться перенесённым (например filters стоял next для label, но тоже уезжает) — тогда
    // insertBefore падает. Заглушка-комментарий держит исходную позицию независимо от соседей.
    /* Порядок в панели фильтров — требование владельца 2026-08-01: «это не мелочи,
       это впечатление о продукте». Было: девять плашек разной длины в одном потоке,
       и «−1+» (глубина) стоял среди объектов, читаясь как ещё один фильтр.
       Стало три ряда: глубина уезжает в строку с кнопкой (она про вид, а не про отбор),
       объекты — своей строкой, связи — двухэтажными плашками «тег / закон» со стрелкой
       между этажами. Двухэтажность даёт одинаковую ширину всем шести и убирает
       обрезание длинных пар вроде «закон↔учёный». */
    function fsTidy(el) {
        if (!el || !el.querySelectorAll) return;
        // insertBefore здесь падал: на момент переезда fsCollapseWrap ещё НЕ был внутри
        // fsPanel (его добавляют следующей строкой), и браузер бросал NotFoundError —
        // а вместе с ним переставал открываться сам полноэкранный режим. Ставим рядом
        // с кнопкой обычным добавлением, порядок в строке задаёт CSS.
        var depth = el.querySelector('.mini-depth-ctrl');
        if (depth && fsPanel && depth.parentNode !== fsPanel) {
            try {
                fsPanel.appendChild(depth);
                depth.classList.add('fs-depth-inline');
            } catch (e) { /* глубина не переехала — не повод ронять полноэкранный режим */ }
        }
        el.querySelectorAll('.mg-edge-label').forEach(function (lab) {
            if (lab.dataset.fsStacked) return;
            var host = Array.prototype.filter.call(lab.childNodes, function (n) {
                return n.nodeType === 3 && /↔/.test(n.textContent);
            })[0];
            if (!host) return;
            var parts = host.textContent.split('↔');
            var box = document.createElement('span');
            box.className = 'mg-edge-stack';
            box.innerHTML = '<i>' + parts[0].trim() + '</i><b>↔</b><i>' + (parts[1] || '').trim() + '</i>';
            lab.replaceChild(box, host);
            lab.dataset.fsStacked = '1';
        });
    }

    function relocateControls(into) {
        if (!fsPanel) return;
        if (into) {
            ctrlHomes = [];
            var take = function (el, dest) {
                var ph = document.createComment('fs-ctrl');
                el.parentNode.insertBefore(ph, el);
                // ПОЧЕМУ снимаем hidden (владелец, пятый заход к одной проблеме, 2026-08-01).
                // На странице статьи фильтры мини-графа спрятаны атрибутом hidden — их
                // показывает своя кнопка «настройки». В полноэкранный режим блок переезжал
                // ВМЕСТЕ со скрытием, поэтому панель «фильтры» открывалась пустой: 0×0
                // пикселей. Кнопка работала всегда, показывать было нечего — снаружи это
                // неотличимо от «нажатие не срабатывает», и я четыре раза чинил не ту
                // болезнь (позицию, подпись, наложение). Атрибут снимаем на время переезда
                // и возвращаем на место, чтобы на самой странице поведение не изменилось.
                ctrlHomes.push({ el: el, ph: ph, wasHidden: el.hasAttribute('hidden') });
                el.removeAttribute('hidden');
                dest.appendChild(el);
                // Приборка — в try: любая ошибка косметики не должна мешать графу
                // открыться (уже наступали на это ровно здесь, 2026-08-01).
                try { fsTidy(el); } catch (e) { }
            };
            fsKeep.forEach(function (el) { take(el, fsPanel); });
            if (fsCollapsible.length) {
                fsCollapseWrap.classList.remove('open');  // фильтры свёрнуты по умолчанию в FS
                fsPanel.appendChild(fsCollapseBtn);
                fsCollapsible.forEach(function (el) { take(el, fsCollapseWrap); });
                fsPanel.appendChild(fsCollapseWrap);
            }
        } else {
            ctrlHomes.forEach(function (h) {
                if (h.wasHidden) h.el.setAttribute('hidden', '');   // вернуть как было на странице
                if (h.ph.parentNode) h.ph.parentNode.replaceChild(h.el, h.ph);
            });
            ctrlHomes = [];
        }
    }
    function setFs(v) {
        var _prevFs = isFs;
        isFs = v;
        if (v) relocateControls(true);
        fsContainer.classList.toggle('graph-fs-active', v);
        document.body.classList.toggle('graph-fs-open', v);
        fsBtn.innerHTML = v ? '<svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 6l12 12"/><path d="M18 6L6 18"/></svg>' : '<svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 9V5.5A1.5 1.5 0 0 1 5.5 4H9"/><path d="M15 4h3.5A1.5 1.5 0 0 1 20 5.5V9"/><path d="M20 15v3.5a1.5 1.5 0 0 1-1.5 1.5H15"/><path d="M9 20H5.5A1.5 1.5 0 0 1 4 18.5V15"/></svg>';
        // Фон полноэкранного: на десктопе прозрачный по умолчанию (юзер 2026-07-25 —
        // «сквозь граф видна страница, смотрится круто»), НА МОБИЛЬНОМ — сплошной
        // (владелец 2026-07-30: на телефоне прозрачность выглядит непонятно);
        // кнопка ◑ переключает в обе стороны на любом устройстве.
        var _touchFs = window.matchMedia && window.matchMedia('(hover: none)').matches;
        if (v && !_touchFs) fsContainer.classList.add('graph-fs-transparent');
        if (!v) { relocateControls(false); fsContainer.classList.remove('graph-fs-transparent'); }
        // resize() одного пересчёта W/H мало — авто-масштаб узлов в step() ограничен ×2.2 от
        // текущего разброса точек, скачок с компактного мини-графа на весь экран так не влезет.
        // restart() пересоздаёт позиции узлов уже в новых границах — граф сразу расправляется.
        restart();
    }

    function resize() {
        var r = cv.getBoundingClientRect(); W = r.width; H = r.height || 460;
        cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function _ingest(g) {
        var capped = capNodes(g.nodes || [], g.links || []);
        nodes = capped.nodes; links = capped.links;
        // Стартовая раскладка — спираль золотого угла, а не случайные точки. Случайный
        // старт на плотном графе даёт комки и пустоты, физика первые сотни шагов тратит
        // на их расталкивание, и часть узлов успевает уехать к стенкам. Спираль кладёт
        // узлы равномерно с первого кадра: те же 175 законов собираются заметно быстрее
        // и никуда не улетают. Заодно раскладка воспроизводима — один и тот же граф
        // выглядит одинаково при каждом открытии, и глазу не надо искать его заново.
        var GA = Math.PI * (3 - Math.sqrt(5)), RAD = Math.min(W, H) * 0.42;
        nodes.forEach(function (n, i) {
            var t = Math.sqrt((i + 0.5) / nodes.length) * RAD, a = i * GA;
            n.x = W / 2 + Math.cos(a) * t; n.y = H / 2 + Math.sin(a) * t;
            n.vx = 0; n.vy = 0; n.deg = 0;
        });
        links.forEach(function (l) { nodes[l[0]].deg++; nodes[l[1]].deg++; });
        nodes.forEach(function (n) { n.r = opts.radius(n); });
        adj = nodes.map(function () { return {}; });
        links.forEach(function (l) { adj[l[0]][l[1]] = 1; adj[l[1]][l[0]] = 1; });
        alpha = 1; hover = -1; drag = -1; ready = true;
        // Пред-прогрев без отрисовки: прокручиваем физику, чтобы граф появился уже почти собранным,
        // а не «слетался» из углов секундами (юзер 2026-07-25). Дёшево — это только числа, без paint.
        if (W > 0 && H > 0) { var warm = nodes.length > 250 ? 70 : 140; for (var _w = 0; _w < warm; _w++) step(); }
        updateSizeWarning(nodes.length, capped.from);
        // Данные пришли, граф начинает рисоваться — убираем лоадер-оверлей (юзер 2026-07-23:
        // «граф долго, но пока грузится пустое место — каунтер»).
        var kgl = document.getElementById('kg-loader');
        if (kgl) { kgl.classList.add('done'); setTimeout(function () { kgl.remove(); }, 320); }
    }

    function rebuild() {  // перестроить по новому фильтру (opts.build читает актуальное состояние)
        ready = false;
        opts.build(lang).then(_ingest);
    }

    opts.build(lang).then(_ingest);

    /* Силы графа. Владелец 2026-08-01: «в центре месиво, по краям пусто — пусть
       расползается по всему пространству».
       Что поменяно и почему:
       • расталкивание 1500 → 3400 и радиус действия 250 → 340: узлы в гуще отталкивались
         слабее, чем их стягивало к центру, и слипались в ком;
       • стяжка к центру 0.0026/0.0045 → 0.0011/0.0018: она нужна лишь чтобы облако
         не уплыло за край, а не чтобы собирать всех в точку;
       • длина связи 52 → 74: соседи стоят дальше, подписи перестают наезжать;
       • расталкивание учитывает РАЗМЕР узла: крупный (много статей) раздвигает соседей
         сильнее — раньше именно вокруг таких хабов и образовывалось месиво.
       Итоговый масштаб не меняется: облако всё равно вписывается в 85% канваса ниже
       по функции, поэтому «расползание» видно как равномерность, а не как рост. */
    var REPULSE = 3400, REPULSE_R2 = 115600, PULL_X = 0.0011, PULL_Y = 0.0018, LINK_LEN = 74;

    // Сетка соседей для отталкивания.
    //
    // Отталкивание считалось парами ВСЕХ СО ВСЕМИ: при 100 узлах это 5 тысяч пар за кадр —
    // незаметно, а в полноэкранном режиме, где лимит снят, узлов 773, и пар становится
    // 298 тысяч. Шестьдесят раз в секунду. Полный граф просто не открывался (владелец
    // 2026-08-08: «когда граф открываю полный, он целиком не рендерится»).
    //
    // При этом отталкивание действует только в радиусе REPULSE_R — всё, что дальше,
    // считалось впустую. Раскладываем узлы по клеткам размером в этот радиус и смотрим
    // только свою клетку и восемь соседних: дальше влияния всё равно нет. Пар остаётся
    // столько, сколько узлов реально рядом, — и это уже линейный счёт, а не квадратичный.
    // Радиус отталкивания зависит от ПЛОТНОСТИ, а не постоянен.
    //
    // Одной сетки соседей мало: базовый радиус 340 px рассчитан на сотню узлов, и при
    // холсте 1400x900 девять соседних клеток покрывают почти весь экран — соседями
    // оказываются все, и сетка ничего не экономит (замер: выигрыш всего вдвое).
    //
    // Но чем больше узлов на том же холсте, тем ближе они стоят друг к другу, и тем
    // меньше нужен радиус влияния: физика от этого не портится, узлы всё так же
    // расталкиваются с ближайшими. Сжимаем радиус как корень из плотности — и при 773
    // узлах пар остаётся 27 тысяч вместо 298 тысяч, легче в одиннадцать раз.
    // Считаем на каждом шаге, а не один раз при загрузке: nodes на тот момент ещё пуст,
    // и радиус остался бы прежним — ровно та ошибка, из-за которой правка сначала
    // не дала ничего. Стоит это два деления в кадр.
    var REPULSE_R2_EFF = REPULSE_R2, REPULSE_R = Math.sqrt(REPULSE_R2);
    var _grid = new Map();
    var REPULSE_EFF = REPULSE;
    function _tuneRadius() {
        // Радиус отталкивания сужаем на плотных графах — иначе каждый считается с каждым.
        // Но САМУ силу при этом надо УСИЛИВАТЬ: раньше сужался только радиус, и на 175
        // законах узлы переставали расталкиваться вовсе — сбивались в ком, а лишние
        // выдавливались к стенкам. Владелец 14 августа: «в углах накапливаются узлы и всё
        // практически останавливается». Держим произведение силы на радиус примерно
        // постоянным: меньше дальность — больше отдача вблизи.
        var k = Math.min(1, 100 / Math.max(1, nodes.length));
        REPULSE_R2_EFF = REPULSE_R2 * k;
        REPULSE_R = Math.sqrt(REPULSE_R2_EFF);
        REPULSE_EFF = REPULSE / Math.max(0.35, Math.sqrt(k));
    }

    function step() {
        var cx = W / 2, cy = H / 2;

        _tuneRadius();
        _grid.clear();
        for (var g = 0; g < nodes.length; g++) {
            var key = ((nodes[g].x / REPULSE_R) | 0) + ',' + ((nodes[g].y / REPULSE_R) | 0);
            var bucket = _grid.get(key);
            if (bucket) bucket.push(g); else _grid.set(key, [g]);
        }

        for (var i = 0; i < nodes.length; i++) {
            var a = nodes[i];
            var gx = (a.x / REPULSE_R) | 0, gy = (a.y / REPULSE_R) | 0;
            for (var ox = -1; ox <= 1; ox++) {
                for (var oy = -1; oy <= 1; oy++) {
                    var cellNodes = _grid.get((gx + ox) + ',' + (gy + oy));
                    if (!cellNodes) continue;
                    for (var ci = 0; ci < cellNodes.length; ci++) {
                        var j = cellNodes[ci];
                        if (j <= i) continue;      // пару считаем один раз, как и раньше
                        var b = nodes[j], dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy || 0.01;
                        if (d2 < REPULSE_R2_EFF) {
                            var d = Math.sqrt(d2);
                            // вес по размеру: r у нас 4-14, поэтому множитель ~1.0-1.6
                            var w = 1 + ((a.r + b.r) - 8) / 24;
                            var f = REPULSE_EFF * (w > 0.6 ? w : 0.6) / d2 / d;
                            a.vx += dx * f; a.vy += dy * f; b.vx -= dx * f; b.vy -= dy * f;
                        }
                    }
                }
            }
            // Стяжка слабее вдоль ДЛИННОЙ стороны холста. Прежние постоянные (Y сильнее X)
            // сплющивали облако по горизонтали — на телефоне в полноэкранном режиме холст
            // высокий, и граф оказывался узкой полосой посередине: сверху и снизу пусто,
            // в центре месиво (замер: центр плотнее углов в 64 раза). Теперь ось, по которой
            // места больше, притягивает мягче, и облако вытягивается туда, где пусто.
            var kx = W >= H ? 0.75 : 1.25, ky = H > W ? 0.75 : 1.25;
            a.vx += (cx - a.x) * PULL_X * kx; a.vy += (cy - a.y) * PULL_Y * ky;
        }
        links.forEach(function (l) {
            var a = nodes[l[0]], b = nodes[l[1]], dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy) || 0.01, f = (d - LINK_LEN) * 0.02 / d;
            a.vx += dx * f; a.vy += dy * f; b.vx -= dx * f; b.vy -= dy * f;
        });
        for (var k = 0; k < nodes.length; k++) {
            var n = nodes[k];
            if (k === drag) { n.x = px; n.y = py; n.vx = n.vy = 0; continue; }
            n.vx *= 0.85; n.vy *= 0.85; n.x += n.vx * alpha; n.y += n.vy * alpha;
            // Мягкая стенка вместо жёсткого зажима. Раньше вышедший за край узел
            // ПРИЛИПАЛ к границе (Math.max/Math.min), и вся лишняя плотность оседала
            // ободком по периметру и комками в углах — то, что владелец видел как
            // «в углах накапливаются узлы». Теперь край отталкивает пропорционально
            // тому, насколько глубоко узел зашёл: узел тормозится и возвращается сам,
            // а вписывание в окно ниже доводит картинку до края аккуратно.
            var m = 30 + n.r, push = 0.06;
            if (n.x < m) { n.vx += (m - n.x) * push; }
            else if (n.x > W - m) { n.vx -= (n.x - (W - m)) * push; }
            if (n.y < m) { n.vy += (m - n.y) * push; }
            else if (n.y > H - m) { n.vy -= (n.y - (H - m)) * push; }
            // Совсем далеко не отпускаем: узел, улетевший на три экрана, обратно ползёт
            // минутами, и человек видит «часть графа пропала».
            var far = 2;
            n.x = Math.max(-W * far, Math.min(W * (1 + far), n.x));
            n.y = Math.max(-H * far, Math.min(H * (1 + far), n.y));
        }
        // Мягкое вписывание облака в окно: масштабируем к ~85% канваса + центрируем,
        // чтобы граф не скучивался по центру, а занимал всё место (не трогаем во время драга).
        if (nodes.length > 1 && drag < 0) {
            var minx = 1e9, miny = 1e9, maxx = -1e9, maxy = -1e9;
            for (var q = 0; q < nodes.length; q++) {
                var nq = nodes[q];
                if (nq.x < minx) minx = nq.x; if (nq.x > maxx) maxx = nq.x;
                if (nq.y < miny) miny = nq.y; if (nq.y > maxy) maxy = nq.y;
            }
            var mgn = 44, bw = (maxx - minx) || 1, bh = (maxy - miny) || 1;
            var s = Math.max(0.6, Math.min(Math.min((W - 2 * mgn) / bw, (H - 2 * mgn) / bh), 2.2));
            var ccx = (minx + maxx) / 2, ccy = (miny + maxy) / 2, ease = 0.06;
            for (var t = 0; t < nodes.length; t++) {
                var nt = nodes[t];
                nt.x += ((W / 2 + (nt.x - ccx) * s) - nt.x) * ease;
                nt.y += ((H / 2 + (nt.y - ccy) * s) - nt.y) * ease;
            }
        }
        if (alpha > 0.03) alpha *= 0.992;
    }

    function draw() {
        ctx.clearRect(0, 0, W, H); ctx.lineWidth = 1;
        links.forEach(function (l) {
            var a = nodes[l[0]], b = nodes[l[1]], hot = hover >= 0 && (l[0] === hover || l[1] === hover);
            ctx.strokeStyle = hot ? 'rgba(120,120,120,0.5)' : 'rgba(140,140,140,0.13)';
            if (l[2] === 'dashed') ctx.setLineDash([3, 3]); // напр. закон↔учёный «оказал влияние», не «открыл»
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
            if (l[2] === 'dashed') ctx.setLineDash([]);
        });
        for (var i = 0; i < nodes.length; i++) {
            var a = nodes[i], dim = hover >= 0 && i !== hover && !adj[hover][i], col = opts.color(a);
            ctx.globalAlpha = dim ? 0.22 : 1;
            ctx.beginPath(); ctx.arc(a.x, a.y, a.r, 0, 7);
            if (opts.hollow(a)) {
                ctx.globalAlpha = dim ? 0.15 : 0.5; ctx.fillStyle = col; ctx.fill();
                ctx.globalAlpha = dim ? 0.3 : 0.85; ctx.lineWidth = 1.3; ctx.strokeStyle = col; ctx.stroke(); ctx.lineWidth = 1;
            } else {
                ctx.fillStyle = col; ctx.fill();
            }
            if (i === hover) { ctx.globalAlpha = 1; ctx.lineWidth = 2; ctx.strokeStyle = txtCol; ctx.stroke(); ctx.lineWidth = 1; }
        }
        ctx.textAlign = 'center';
        for (var j = 0; j < nodes.length; j++) {
            var n = nodes[j], always = opts.labelAlways && opts.labelAlways(n);
            if (j === hover || always || n.deg >= 3) {
                var strong = j === hover || (hover >= 0 && adj[hover][j]);
                ctx.font = (always ? '10px' : '9px') + ' sans-serif';
                ctx.globalAlpha = strong ? 0.95 : (hover >= 0 ? 0.08 : (always ? 0.6 : 0.28));
                ctx.fillStyle = txtCol; ctx.fillText(n.name, n.x, n.y - n.r - 3);
            }
        }
        ctx.globalAlpha = 1;
    }

    // Пока граф ещё «горячий» (alpha высок) — гоним несколько тиков физики на кадр: собирается
    // в разы быстрее по времени, без потери плавности у уже осевшего графа (юзер 2026-07-25).
    function loop() {
        if (ready) {
            var reps = alpha > 0.2 ? 4 : (alpha > 0.08 ? 2 : 1);
            for (var s = 0; s < reps; s++) step();
            draw();
        }
        requestAnimationFrame(loop);
    }
    function pos(e) { var r = cv.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; }
    function pick(x, y) { var bi = -1, bd = 1e9; for (var i = 0; i < nodes.length; i++) { var a = nodes[i], d = Math.hypot(a.x - x, a.y - y); if (d < a.r + 6 && d < bd) { bd = d; bi = i; } } return bi; }
    cv.addEventListener('pointerdown', function (e) { var p = pos(e), i = pick(p[0], p[1]); downXY = p; if (i >= 0) { drag = i; px = p[0]; py = p[1]; alpha = Math.max(alpha, 0.5); cv.setPointerCapture(e.pointerId); } });
    cv.addEventListener('pointermove', function (e) {
        var p = pos(e);
        if (drag >= 0) { px = p[0]; py = p[1]; hideTip(); }
        else {
            hover = pick(p[0], p[1]);
            cv.style.cursor = hover >= 0 ? 'pointer' : 'grab';
            if (hover >= 0 && opts.tooltip) showTip(nodes[hover], p[0] + 14, p[1] + 14); else hideTip();
        }
    });
    cv.addEventListener('pointerleave', hideTip);
    cv.addEventListener('pointerup', function (e) {
        var p = pos(e), moved = downXY && (Math.abs(p[0] - downXY[0]) + Math.abs(p[1] - downXY[1]) > 6);
        var i = pick(p[0], p[1]);
        if (!moved && i >= 0) { var url = opts.href(nodes[i], lang); if (url) window.location.href = url; }
        drag = -1; downXY = null;
    });

    function restart() {
        resize();
        for (var i = 0; i < nodes.length; i++) {
            nodes[i].x = Math.random() * (W - 80) + 40; nodes[i].y = Math.random() * (H - 80) + 40;
            nodes[i].vx = nodes[i].vy = 0;
        }
        alpha = 1;
    }
    window[opts.resizeKey] = restart;
    if (opts.rebuildKey) window[opts.rebuildKey] = rebuild;
    resize(); loop();
};
