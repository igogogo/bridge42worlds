/* formula-live — свежая анатомия формулы с воркера.

   Страница формулы собирается статикой, но анатомия дописывается конвейером
   каждую ночь: переводы, системы единиц, новые применения. Ждать пересборки
   ради этого не нужно — тело статично, обвязка динамична.

   Если облако молчит или мы смотрим локально, остаётся ровно то, что собрала
   статика: ни одного пустого места. */
(function () {
'use strict';

var box = document.querySelector('.entity-body[data-formula]');
if (!box) return;
var API = (typeof window.B42_API === 'string' ? window.B42_API : '');
var LANG = document.documentElement.lang || 'ru';

fetch(API + '/api/formula?id=' + encodeURIComponent(box.dataset.formula))
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (d) {
        var f = d && d.formula;
        if (!f) return;
        /* Системы единиц могли приехать после сборки страницы — показываем их,
           если в статике блока ещё нет. */
        if (f.systems && f.systems.length && !document.querySelector('.fx-systems')) {
            var t = {ru: 'В других системах единиц', en: 'In other unit systems'};
            var wrap = document.createElement('div');
            wrap.className = 'fx-systems';
            wrap.innerHTML = '<h2 style="font-size:16px;margin:14px 0 6px">' +
                (t[LANG] || t.en) + '</h2>' + f.systems.map(function (u) {
                    return '<div style="margin:8px 0"><b style="font-family:var(--mono);' +
                        'font-size:11.5px">' + (u.system || '') + '</b>' +
                        '<div class="formula" style="margin:4px 0">$$' +
                        (u.latex || '') + '$$</div>' +
                        (u.note ? '<span style="color:var(--soft)">— ' + u.note + '</span>' : '') +
                        '</div>';
                }).join('');
            box.appendChild(wrap);
            if (window.renderMathInElement) {
                renderMathInElement(wrap, {output: 'html', delimiters: [
                    {left: '$$', right: '$$', display: true}]});
            }
        }
        /* Счётчик применений — всегда свежий: он растёт с каждой новой статьёй. */
        var st = document.querySelector('.tag-stats');
        if (st && f.n) {
            var lbl = LANG === 'ru' ? ' применений' : ' uses';
            st.textContent = f.n + lbl;
        }
    })
    .catch(function () {});
})();
