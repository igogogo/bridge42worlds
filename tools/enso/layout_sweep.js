/* ОБХОД СЦЕН ПАНЕЛИ: ГДЕ ТЕКСТ НЕ ПОМЕЩАЕТСЯ.
 *
 * Владелец 16.09: «сделай такой обход постоянной проверкой». До этого поломки находил он сам,
 * глазами: «The watchdog is shouting — текст в карточки не помещается, карточки очень вытянуты».
 *
 * ПОЧЕМУ ЭТО НЕЛЬЗЯ ПРОВЕРИТЬ БЕЗ БРАУЗЕРА. Всё, что мы ловим здесь, — свойство РАСКЛАДКИ, а не
 * текста и не стилей по отдельности. Читая CSS, нельзя узнать, что именно этот заголовок в
 * именно этой колонке встанет по одному слову в строку: это зависит от ширины сцены, от длины
 * соседнего текста (а он приходит с данными и меняется каждый день) и от того, какое правило
 * победило в каскаде. Столкновение имён классов, из-за которого 15–16.09 осыпались карточки
 * пояснений на семи сценах, видно только на живой странице.
 *
 * ЧТО ИЩЕМ И ПОЧЕМУ ИМЕННО ЭТО:
 *  · stack — слова столбиком: три строки и больше, меньше 1,6 слова на строку, колонка уже
 *    115 пикселей. Так выглядит колонка, которую браузер сжал до самого длинного слова.
 *  · cutW / cutH — текст обрезан своим контейнером БЕЗ многоточия: читатель не видит ни конца
 *    фразы, ни знака, что она продолжается.
 *  · outOfCard — текст нарисован за пределами своей карточки и налезает на соседнюю.
 *  · sceneWide — сама сцена шире своего поля, а прокрутки нет: часть недоступна вовсе.
 *  · empty — сцена отрисовалась почти пустой: чаще всего это молча упавший источник.
 *
 * ЧЕГО НЕ СЧИТАЕМ ПОЛОМКОЙ (иначе проверка тонет в ложных тревогах и ей перестают верить):
 *  · элемент внутри контейнера, который РЕАЛЬНО прокручивается, — широкая таблица, лента KPI,
 *    карта: они сделаны так нарочно;
 *  · обрезку с многоточием — это объявленное сокращение, у него есть подсказка;
 *  · содержимое <svg> — там своя система координат, и мерить его этими мерками бессмысленно.
 *
 * ГДЕ ЗАПУСКАЕТСЯ. Обычно из tools/enso/check_layout.py в безоконном браузере. Руками —
 * вставить файл в консоль на /enso.html и позвать:
 *     await B42Layout.sweep()          // все вкладки и подвкладки
 *     B42Layout.audit(['.stage-body']) // только текущая сцена
 */
(function () {
  'use strict';

  var VERSION = 1;
  /* Сцена успевает встать не сразу: цепочка данных меряет свою ширину по requestAnimationFrame
     и повторяет через 250 мс, графики перерисовываются наблюдателем размера. Меряя раньше,
     проверка ловит промежуточную раскладку и выдаёт десятки замечаний на здоровой странице. */
  var SETTLE = 420;

  function path(el) {
    var s = el.tagName.toLowerCase();
    if (el.className && typeof el.className === 'string') {
      s += '.' + el.className.trim().split(/\s+/).slice(0, 3).join('.');
    }
    var p = el.parentElement;
    if (p && p.className && typeof p.className === 'string') {
      s = p.className.trim().split(/\s+/)[0] + ' > ' + s;
    }
    return s;
  }

  /* Ближайший предок, который вообще что-то режет. Если он при этом прокручивается —
     значит содержимое доступно, и это не поломка. */
  function clipper(el) {
    for (var n = el.parentElement; n && n !== document.body; n = n.parentElement) {
      var c = getComputedStyle(n);
      if (c.overflow !== 'visible' || c.overflowX !== 'visible' || c.overflowY !== 'visible') return n;
    }
    return null;
  }

  function ellipsised(el) {
    if (getComputedStyle(el).textOverflow === 'ellipsis') return true;
    var p = el.parentElement;
    return !!(p && getComputedStyle(p).textOverflow === 'ellipsis');
  }

  function audit(roots) {
    var bad = [];
    roots.forEach(function (sel) {
      var root = document.querySelector(sel);
      if (!root) return;
      [].forEach.call(root.querySelectorAll('*'), function (el) {
        var cs = getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') return;
        if (el.tagName === 'svg' || el.closest('svg')) return;
        var r = el.getBoundingClientRect();
        if (r.width < 2 || r.height < 2) return;
        var txt = (el.textContent || '').replace(/\s+/g, ' ').trim();
        var lh = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.4 || 14;

        // слова столбиком
        if (txt.length > 12 && el.children.length === 0) {
          var words = txt.split(' ').filter(Boolean).length;
          var lines = Math.round(r.height / lh);
          if (lines >= 3 && words >= 3 && words / lines < 1.6 && r.width < 115) {
            bad.push({ t: 'stack', p: path(el), w: Math.round(r.width), lines: lines, x: txt.slice(0, 60) });
          }
        }
        // обрезано по ширине без многоточия
        if ((cs.overflowX === 'hidden' || cs.overflow === 'hidden') && el.clientWidth > 0
            && el.scrollWidth > el.clientWidth + 2 && txt.length > 3 && cs.textOverflow !== 'ellipsis') {
          bad.push({ t: 'cutW', p: path(el), w: el.clientWidth, need: el.scrollWidth, x: txt.slice(0, 60) });
        }
        // обрезано по высоте
        if ((cs.overflowY === 'hidden' || cs.overflow === 'hidden') && el.clientHeight > 0
            && el.scrollHeight > el.clientHeight + 4 && txt.length > 3) {
          bad.push({ t: 'cutH', p: path(el), h: el.clientHeight, need: el.scrollHeight, x: txt.slice(0, 60) });
        }
        // вылез за свою карточку и налезает на соседей
        if (cs.overflow === 'visible' && el.children.length === 0 && txt.length > 8) {
          var box = el.closest('.card, .gl-i, .kpi, .tile, .risk, .ov-kpi, .ks');
          if (box && box !== el) {
            var br = box.getBoundingClientRect();
            if (r.right > br.right + 3 || r.left < br.left - 3) {
              var cl = clipper(el);
              var scrolls = cl && cl.scrollWidth > cl.clientWidth + 2;
              if (!scrolls && !ellipsised(el)) {
                bad.push({ t: 'outOfCard', p: path(el),
                  over: Math.round(Math.max(r.right - br.right, br.left - r.left)), x: txt.slice(0, 60) });
              }
            }
          }
        }
      });
      // сцена шире своего поля и при этом не прокручивается
      var rs = getComputedStyle(root);
      if (root.scrollWidth > root.clientWidth + 4 && rs.overflowX !== 'auto' && rs.overflowX !== 'scroll') {
        bad.push({ t: 'sceneWide', p: sel, w: root.clientWidth, need: root.scrollWidth, x: '' });
      }
    });
    // одинаковое сводим: одно замечание на (род, место, начало текста)
    var seen = {}, out = [];
    bad.forEach(function (b) {
      var k = b.t + '|' + b.p + '|' + (b.x || '').slice(0, 24);
      if (seen[k]) return;
      seen[k] = 1;
      out.push(b);
    });
    return out;
  }

  /* Кнопки подвкладок: только те, что переключают сцену. source/notes/stats открывают панель
     пояснений, ⛶ уводит в полный экран — их трогать нельзя, иначе обход уедет не туда.
     РЯДОВ С КЛАССОМ .seg В ШАПКЕ ДВА: первый — .seg.ctl-info внутри .stage-ctl (source, notes,
     stats), второй — настоящие подвкладки. Простое '.stage-head .seg' брало ПЕРВЫЙ, все его
     кнопки отсеивались фильтром, и обход считал, что подвкладок нет: он обходил только сцену
     по умолчанию у каждой вкладки и молча пропускал остальные. */
  function segs() {
    var row = document.querySelector('.stage-head > .seg:not(.ctl-info)');
    if (!row) return [];
    return [].slice.call(row.querySelectorAll('button')).filter(function (b) {
      return !b.classList.contains('sq') && !b.classList.contains('back-go')
        && !b.classList.contains('stats') && !b.hasAttribute('data-info');
    });
  }

  /* Подпись кнопки — только её собственный текст. В кнопке подвкладки сидит ещё значок
     подсказки <i class="ti">, и textContent приклеивал его к названию: «Sourcesi». */
  /* ЖДЁМ, ПОКА СЦЕНА ПЕРЕСТАНЕТ МЕНЯТЬСЯ. Постоянной паузы мало: глобус тянет свою библиотеку
     и дорисовывает узлы уже после неё, и обход мерил наполовину собранную сцену — отсюда
     замечания, которых на готовой странице нет (17.09). Смотрим на размер разметки сцены двумя
     замерами подряд: совпали — значит встала. Потолок держим, чтобы вечная анимация не
     остановила обход. */
  async function settle(ms, capMs) {
    await wait(ms);
    var b = document.querySelector('.stage-body');
    if (!b) return;
    var end = Date.now() + (capMs || 2600), prev = -1;
    while (Date.now() < end) {
      var now = b.innerHTML.length + '|' + Math.round(b.scrollHeight);
      if (now === prev) return;
      prev = now;
      await wait(260);
    }
  }

  function label(el) {
    var own = '';
    [].forEach.call(el.childNodes, function (n) { if (n.nodeType === 3) own += n.nodeValue; });
    return (own || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 26);
  }
  function wait(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  function emptyScene() {
    var b = document.querySelector('.stage-body');
    if (!b) return true;
    return (b.textContent || '').replace(/\s+/g, ' ').trim().length < 40;
  }

  async function sweep(opts) {
    opts = opts || {};
    var pause = opts.settle || SETTLE;
    var out = [], scenes = 0;

    function take(name, roots) {
      scenes++;
      if (roots.indexOf('.stage-body') >= 0 && emptyScene()) {
        out.push({ scene: name, t: 'empty', p: '.stage-body', x: 'сцена отрисовалась пустой' });
        return;
      }
      audit(roots).forEach(function (f) { f.scene = name; out.push(f); });
    }

    // рельсы одинаковы во всех сценах — смотрим один раз (на телефоне они и так свои вкладки)
    audit(['#railL', '#railR', '.kstrip']).forEach(function (f) { f.scene = 'rails'; out.push(f); });

    var n = document.querySelectorAll('.tab').length;
    for (var i = 0; i < n; i++) {
      // список вкладок пересобирается на каждый переход, а при смене ширины ещё и меняет длину
      var tabs = document.querySelectorAll('.tab');
      if (i >= tabs.length) break;
      var name = label(tabs[i]);
      tabs[i].click();
      await settle(pause);
      var m = segs().length;
      if (!m) { take(name, ['.stage-body']); continue; }
      for (var j = 0; j < m; j++) {
        var ss = segs();
        if (!ss[j]) break;
        var sub = label(ss[j]);
        ss[j].click();
        await settle(pause);
        take(name + ' / ' + sub, ['.stage-body']);
      }
    }
    return { version: VERSION, width: window.innerWidth, scenes: scenes, findings: out };
  }

  window.B42Layout = { version: VERSION, audit: audit, segs: segs, sweep: sweep };
})();
