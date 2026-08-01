/* Отклик на действие: короткая искра из кнопки. Ничего не грузит, ничего не ломает.
 *
 * Владелец 2026-07-31: «нажали лайк — звёздочки вылетели, что-то мигнуло слабо, не сильно;
 * немного цвета можно, но в основном у нас спокойный контрастный строгий вид».
 * Отсюда мера: искры мелкие, живут 600 мс, цвет берётся у самой кнопки (звезда — охра
 * избранного, лайк — зелёный, дизлайк — приглушённый) — новых цветов в палитру не вводим.
 *
 * Живёт в JS и CSS, поэтому появляется без пересборки сайта — правило владельца
 * «если можно оживить без регенерации, делай так».
 *
 * Уважает prefers-reduced-motion: у кого движение отключено системно, тот получает
 * только смену цвета кнопки, без частиц.
 */
(function () {
    'use strict';
    var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

    function burst(el, opts) {
        if (reduce || !el) return;
        var o = opts || {};
        var n = o.count || 6;
        var r = el.getBoundingClientRect();
        var cx = r.left + r.width / 2, cy = r.top + r.height / 2;
        var host = document.createElement('div');
        host.className = 'b42-spark';
        host.style.left = cx + 'px';
        host.style.top = cy + 'px';
        for (var i = 0; i < n; i++) {
            var p = document.createElement('i');
            // Разлёт веером вверх: вниз частицы «падают» и читаются как ошибка.
            var a = (-140 + (280 / (n - 1)) * i) * Math.PI / 180;
            var dist = 16 + Math.random() * 14;
            p.style.setProperty('--dx', (Math.cos(a) * dist).toFixed(1) + 'px');
            p.style.setProperty('--dy', (Math.sin(a) * dist - 6).toFixed(1) + 'px');
            p.style.animationDelay = (i * 12) + 'ms';
            if (o.shape === 'star') p.classList.add('star');
            host.appendChild(p);
        }
        document.body.appendChild(host);
        setTimeout(function () { host.remove(); }, 700);
    }
    window.b42Spark = burst;

    // Одна точка на весь сайт: кнопки живут в разной разметке (лента, статья, карточки),
    // и вешать обработчик на каждую — тот самый класс «правило в двух местах».
    document.addEventListener('click', function (e) {
        var t = e.target.closest && e.target.closest('.fav-btn, .react-btn');
        if (!t) return;
        // Искра — только на включение. Снял лайк — это отмена, праздновать нечего.
        setTimeout(function () {
            var on = t.classList.contains('active') || t.classList.contains('liked');
            if (!on) return;
            var fav = t.classList.contains('fav-btn');
            burst(t, { shape: fav ? 'star' : 'dot', count: fav ? 7 : 5 });
            t.classList.add('b42-pop');
            setTimeout(function () { t.classList.remove('b42-pop'); }, 320);
        }, 30);   // ждём, пока обработчик лайка проставит своё состояние
    }, true);
})();
