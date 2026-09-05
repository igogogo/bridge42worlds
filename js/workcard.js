/* Карточка работы у курсора: наведи на номер — увидишь, о чём она у нас.
 *
 * Владелец 04.09: «статьи — там как будут тоже ссылки типа с номером arXiv, а по наведению
 * допустим резюме, там наша какая-то часть, и ссылка на нашу карточку? по всему сайту,
 * контекстно». И следом: «ссылки на работы тоже отдельно как-то рамочкой или шрифтом, чтобы
 * было чётко видно».
 *
 * ЗАЧЕМ. Номер работы сам по себе ничего не говорит: «2606.24358» это не знание, а адрес.
 * Раньше читателю оставалось либо уйти по ссылке и потерять место в тексте, либо не ходить
 * вовсе. Теперь наведение показывает НАШУ строку о работе — заголовок и однострочное резюме
 * с нашей же карточки, — а щелчок ведёт на нашу страницу, а не наружу.
 *
 * ОТКУДА ДАННЫЕ. Из воркера: /api/cards?ids=…&lang=… отдаёт по номеру заголовок, резюме и
 * адрес нашей страницы на языке страницы. Ничего не считаем на клиенте и ничего не держим в
 * разметке: карточка приходит по требованию и живёт в памяти вкладки до перезагрузки.
 *
 * ПОЧЕМУ ОТДЕЛЬНЫЙ ФАЙЛ. Такие ссылки должны работать одинаково в статье, на странице
 * понятия, закона, учёного и в дашборде. Один файл и один стиль — значит, поведение везде
 * одно, и новая страница получает его строкой подключения.
 */
(function () {
  'use strict';

  /* На проде это свой воркер, а при местной проверке страницы отдаёт простой сервер,
     у которого никакого /api нет. Чтобы карточку можно было смотреть локально, на
     localhost спрашиваем прод напрямую — воркер отдаёт /api/cards с заголовками CORS. */
  var LOCAL = /^(localhost|127\.0\.0\.1)$/.test(location.hostname);
  var API = LOCAL ? 'https://bridge42worlds.academy/api/cards' : '/api/cards';
  var cache = new Map();            // id -> карточка или null (нет у нас такой работы)
  var pending = new Map();          // id -> Promise, чтобы не спрашивать дважды
  var box = null, hideTimer = null, overCard = false, current = null;

  function lang() {
    var m = location.pathname.match(/\/lang\/([a-z]{2})\//);
    return m ? m[1] : (document.documentElement.lang || 'ru').slice(0, 2);
  }

  /* Номер приходит в разном виде: 2606.24358, 2606.24358v1, arXiv:2606.24358.
     Воркер знает версии, но кэш и запрос ведём по чистому номеру. */
  function clean(id) {
    var m = String(id || '').match(/(\d{4}\.\d{4,6})(v\d+)?/);
    return m ? m[1] + (m[2] || '') : '';
  }

  function fetchCards(ids) {
    var need = ids.filter(function (i) { return !cache.has(i) && !pending.has(i); });
    if (!need.length) return Promise.resolve();
    var p = fetch(API + '?ids=' + encodeURIComponent(need.join(',')) + '&lang=' + lang())
      .then(function (r) { return r.ok ? r.json() : { items: [] }; })
      .then(function (d) {
        var by = {};
        (d.items || []).forEach(function (it) { by[clean(it.id)] = it; });
        need.forEach(function (i) { cache.set(i, by[i] || by[clean(i)] || null); pending.delete(i); });
      })
      .catch(function () { need.forEach(function (i) { cache.set(i, null); pending.delete(i); }); });
    need.forEach(function (i) { pending.set(i, p); });
    return p;
  }

  function el() {
    if (box) return box;
    box = document.createElement('div');
    box.className = 'wk-card';
    box.setAttribute('role', 'dialog');
    box.addEventListener('mouseenter', function () { overCard = true; clearTimeout(hideTimer); });
    box.addEventListener('mouseleave', function () { overCard = false; later(); });
    box.addEventListener('click', function (e) {
      if (e.target.closest('.wk-x')) { hide(); e.preventDefault(); }
    });
    document.body.appendChild(box);
    return box;
  }

  function place(x, y) {
    var b = el(), pad = 14;
    b.style.visibility = 'hidden';
    b.classList.add('on');
    var w = b.offsetWidth, h = b.offsetHeight;
    var left = x + pad, top = y + pad;
    if (left + w > window.innerWidth - 8) left = Math.max(6, x - w - pad);
    if (top + h > window.innerHeight - 8) top = Math.max(6, y - h - pad);
    b.style.left = left + 'px';
    b.style.top = top + 'px';
    b.style.visibility = '';
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function show(node, x, y) {
    var id = clean(node.getAttribute('data-work'));
    if (!id) return;
    current = node;
    var b = el();
    var card = cache.get(id);
    if (card === undefined) {
      b.innerHTML = '<button type="button" class="wk-x" title="close">×</button>' +
        '<div class="wk-t">' + esc(id) + '</div><div class="wk-s">looking it up…</div>';
      place(x, y);
      fetchCards([id]).then(function () { if (current === node) show(node, x, y); });
      return;
    }
    if (!card) {
      /* Честно: работа есть на arXiv, но у нас её нет. Не выдумываем содержание. */
      b.innerHTML = '<button type="button" class="wk-x" title="close">×</button>' +
        '<div class="wk-t">arXiv ' + esc(id) + '</div>' +
        '<div class="wk-s">We have not parsed this work — only the reference is ours.</div>' +
        '<a class="wk-go" href="https://arxiv.org/abs/' + esc(id) + '" target="_blank" rel="noopener">open on arXiv →</a>';
      place(x, y);
      return;
    }
    b.innerHTML = '<button type="button" class="wk-x" title="close">×</button>' +
      '<div class="wk-t">' + esc(card.title || id) + '</div>' +
      (card.oneliner ? '<div class="wk-s">' + esc(card.oneliner) + '</div>' : '') +
      '<div class="wk-m">arXiv ' + esc(id) + (card.date ? ' · ' + esc(card.date) : '') + '</div>' +
      (card.url ? '<a class="wk-go" href="' + esc(card.url) + '">read our version →</a>' : '');
    place(x, y);
  }

  function hide() {
    clearTimeout(hideTimer);
    current = null;
    if (box) box.classList.remove('on');
  }

  function later() {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(function () { if (!overCard) hide(); }, 900);
  }

  function anchor(e) {
    return e.target.closest && e.target.closest('[data-work]');
  }

  document.addEventListener('mouseover', function (e) {
    if (overCard) return;
    var a = anchor(e);
    if (!a || a === current) return;
    show(a, e.clientX, e.clientY);
  });
  document.addEventListener('mouseout', function (e) { if (anchor(e)) later(); });
  document.addEventListener('click', function (e) {
    var a = anchor(e);
    if (a) {                       // на касании карточка открывается щелчком и остаётся
      e.preventDefault();
      show(a, e.clientX, e.clientY);
      return;
    }
    if (box && box.classList.contains('on') && !e.target.closest('.wk-card')) hide();
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') hide(); });

  /* Предзагрузка того, что видно: наведение тогда показывает карточку мгновенно, а не
     через сеть. Берём первые два десятка — больше на экран всё равно не помещается. */
  window.addEventListener('load', function () {
    var ids = [];
    document.querySelectorAll('[data-work]').forEach(function (n) {
      var i = clean(n.getAttribute('data-work'));
      if (i && ids.indexOf(i) < 0) ids.push(i);
    });
    if (ids.length) fetchCards(ids.slice(0, 20));
  });
})();
