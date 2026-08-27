/* b42-live — общий слой подмены списков, приходящих с воркера.

   Динамика (D1 + Worker) отдаёт свежие списки статей: ленте, страницам
   сущностей (js/entity-live.js) и страницам авторов (js/author-live.js).
   Раньше каждая из них меняла innerHTML мгновенно — читатель видел рывок,
   а на пустом контейнере просто белое место, пока ответ в пути.

   Здесь три общие вещи, чтобы они не расползлись по трём файлам:
     B42Live.pending(box)   пометить: ответ в пути (приглушение; если пусто —
                            карточки-скелеты, чтобы место не прыгало)
     B42Live.swap(box, html) плавная подмена
     B42Live.fail(box)      воркер молчит — вернуть статику как была */
(function () {
'use strict';

function skeleton(n) {
    var s = '';
    for (var i = 0; i < (n || 3); i++) {
        s += '<div class="b42-skel" aria-hidden="true"><i class="sk-img"></i>' +
             '<div class="sk-lines"><i></i><i></i><i></i><i></i></div></div>';
    }
    return s;
}

function pending(box, opts) {
    if (!box) return;
    box.classList.add('live-loading');
    var empty = !box.querySelector('.article-card, .b42-skel');
    if (empty) {
        box.dataset.b42Skel = '1';
        box.innerHTML = skeleton((opts && opts.n) || 3);
    }
}

function swap(box, html) {
    if (!box) return;
    box.classList.remove('live-loading');
    delete box.dataset.b42Skel;
    box.innerHTML = html;
    /* перезапуск анимации входа: класс снимаем и ставим в следующем кадре */
    box.classList.remove('live-in');
    requestAnimationFrame(function () { box.classList.add('live-in'); });
}

function fail(box) {
    if (!box) return;
    box.classList.remove('live-loading');
    if (box.dataset.b42Skel) {          // скелет был единственным содержимым
        box.innerHTML = '';
        delete box.dataset.b42Skel;
    }
}

window.B42Live = {pending: pending, swap: swap, fail: fail, skeleton: skeleton};
})();
