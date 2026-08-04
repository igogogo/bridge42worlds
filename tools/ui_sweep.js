/* Сплошной обход страниц: что уехало за экран, что налезло, что пусто.
 *
 * Владелец 2026-08-02: «надо сделать, чтобы работало, а не чинить постоянно — сделай за
 * один день под контролем, отдай все ошибки и дай тогда проверять».
 *
 * Запускается в консоли браузера на КАЖДОМ типе страницы (или через javascript_tool).
 * Возвращает список замечаний строками — их можно сразу вставлять в отчёт.
 *
 * Что ищем и почему именно это:
 *  · ВЫХОД ЗА ЭКРАН — источник горизонтального скролла; на телефоне это значит, что часть
 *    интерфейса недоступна вовсе (доскроллить до fixed-элемента нельзя).
 *  · МЕЛКИЙ ТЕКСТ (<11px) — на 375px читается плохо, а у нас арабский, где мелкий шрифт
 *    хуже вдвое: вязь теряет диакритику.
 *  · МАЛЕНЬКИЕ КНОПКИ (<32px) — палец не попадает. Норма 44px, 32 это уже уступка.
 *  · ПУСТЫЕ БЛОКИ-КОНТЕЙНЕРЫ — раздел есть, содержимого нет: чаще всего это молчаливо
 *    сломавшийся источник данных, а не задумка.
 *  · НАЛОЖЕНИЯ интерактивных элементов — кнопка под кнопкой; так пропал гамбургер на графе.
 */
(function b42Sweep() {
    var W = window.innerWidth, out = [];
    var seen = {};

    /* Элемент внутри прокручиваемого блока НЕ считается вылезающим.
       Формула шире колонки, лента миниатюр, широкая таблица — они лежат в контейнере
       с overflow-x:auto и прокручиваются внутри него. Их getBoundingClientRect всё равно
       показывает полную ширину раскладки, и наивная проверка объявляет дефектом ровно то,
       что сделано правильно. Первая версия этого обхода выдала 34 «замечания» на здоровой
       статье — почти все отсюда. Ложная тревога хуже отсутствия проверки: на неё тратят
       время, а потом перестают верить красному. */
    function inScroller(el) {
        for (var p = el.parentElement; p && p !== document.body; p = p.parentElement) {
            var ox = getComputedStyle(p).overflowX;
            if (ox === 'auto' || ox === 'scroll') return true;
        }
        return false;
    }

    function say(kind, el, detail) {
        var name = (el.id ? '#' + el.id : '') + (el.className && el.className.toString
            ? '.' + el.className.toString().trim().split(/\s+/).slice(0, 2).join('.') : el.tagName);
        var key = kind + name;
        if (seen[key]) return;                 // один и тот же класс — одно замечание
        seen[key] = 1;
        out.push(kind + ' · ' + name + (detail ? ' · ' + detail : ''));
    }

    var all = document.querySelectorAll('body *');
    for (var i = 0; i < all.length; i++) {
        var el = all[i], r = el.getBoundingClientRect();
        if (!r.width || !r.height) continue;
        var cs = getComputedStyle(el);
        if (cs.visibility === 'hidden' || cs.opacity === '0') continue;

        if ((r.right > W + 1 || r.left < -1) && !inScroller(el)) {
            say('ЗА ЭКРАН', el, Math.round(r.left) + '→' + Math.round(r.right) + ' при ' + W);
        }
        var fs = parseFloat(cs.fontSize);
        if (fs && fs < 11 && (el.textContent || '').trim().length > 3 && !el.children.length) {
            say('МЕЛКО', el, fs + 'px');
        }
        var clickable = el.matches('a, button, [role="button"], input, select, .ent, .lv-btn');
        if (clickable && (r.height < 28 || r.width < 24) && (el.textContent || '').trim().length <= 3) {
            say('МЕЛКАЯ КНОПКА', el, Math.round(r.width) + '×' + Math.round(r.height));
        }
        if (el.matches('[id$="-bar"], [class*="-list"], [class*="-grid"], section, .card-tags')
            && !el.children.length && !(el.textContent || '').trim()) {
            say('ПУСТО', el, '');
        }
    }

    return {
        ширина: W,
        скроллТела: document.body.scrollWidth,
        горизонтальныйСкролл: document.body.scrollWidth > W,
        замечаний: out.length,
        список: out.slice(0, 25)
    };
})();
