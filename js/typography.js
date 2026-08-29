/* typography.js — плотное длинное тире на уже собранных страницах.

   Владелец 29.08: «у нас часто по тексту тире, типа astrophysics—from, что плохо,
   люди это воспринимают как то, что сделал ИИ… можно ли поправить не только у нас,
   но и так же на сайте, чтобы не пересобирать… хотя бы в пробелы их обрамить,
   а то так даже сливаются».

   ОТКУДА ОНО. Не из генерации, а из перевода: в русском тире — рядовой знак и стоит
   с пробелами («поле — это область»), переводчик переносил его в английский как есть
   и прижимал к словам. Счёт по корпусу: русских с пробелами 128 206 (норма),
   английских плотных — 62 325. Причина закрыта в промте переводчика; здесь лечится
   то, что уже написано и уже лежит на сайте.

   ПОЧЕМУ НА КЛИЕНТЕ. Иначе пришлось бы пересобрать 5 795 статей — тридцать пять тысяч
   страниц и часы работы — и заново их выложить. Правка в тексте страницы стоит доли
   миллисекунды и доезжает до читателя за пять минут (столько живёт кэш css/js), без
   единой пересборки. Когда страницы будут пересобираться по другому поводу, они
   приедут уже чистыми — тот же разбор делает tools/dash_fix.py в самих данных, —
   и здесь просто нечего будет исправлять.

   БЕЗ МОДЕЛИ, НАРОЧНО. Владелец: «это риск, что дешёвая модель нам текст сломает».
   Поэтому решают правила, и каждое из них — то, где выбор ОДНОЗНАЧЕН:
     · тире парой, вокруг вставки        → запятые: «qubit, a tiny loop, crunches»;
     · перед and/but/or/so/yet           → запятая: «loop, and the state flows»;
     · перед like/just/as/such           → запятая: «energy, like the force of an impact»;
     · перед a/an/the и коротким хвостом → запятая: «flaws, places where…»;
     · перед it/they/this/each/there…    → двоеточие: дальше идёт самостоятельное
       предложение, и запятая склеила бы два предложения в одно;
     · во всех остальных случаях         → тире с пробелами.
   Последнее правило и есть страховка: пробельное тире всегда грамматично (так пишет
   AP), и слова больше не слипаются. Гадать, где просится двоеточие, а где запятая,
   правила не пытаются — угаданное неверно читается хуже оставшегося тире.

   ТЕКСТ СКЛЕИВАЕМ ПО БЛОКУ, А НЕ ПО УЗЛУ. Понятия в тексте — ссылки, и абзац разрезан
   на куски: «…qubit», «—a tiny loop…». Тире оказывается в НАЧАЛЕ куска, буквы слева
   в нём нет, и правило по одному узлу его не видит — а это самый частый случай, ведь
   размечены как раз термины. Поэтому куски одного абзаца сшиваются в строку, решение
   принимается по ней, и правки раскладываются обратно по узлам с конца, чтобы
   смещения не поехали.

   ЧЕГО НЕ ТРОГАЕМ: диапазоны чисел («300–800 GeV» — там знак на своём месте), формулы
   KaTeX, code/pre, поля ввода. */
(function () {
    'use strict';

    var LANG = (document.documentElement.lang || 'en').slice(0, 2);

    /* Плотное длинное тире МЕЖДУ БУКВАМИ. Соседние буквы смотрим заглядыванием, а не
       захватом: при захвате в цепочке «x—y—z» второе тире осталось бы незамеченным —
       буква y уже съедена первым совпадением. Цифры исключены нарочно: «300—800» —
       диапазон, и там знак на своём месте.

       Буква — это \p{L}, а не \w: в JS \w это латиница, и «Поле—это» правило не
       видело вовсе. Русских плотных тире всего 388, но именно они и есть опечатка;
       по-арабски их 319, и там та же история. */
    var TIGHT = /(?<=\p{L})—(?=\p{L})/u;
    var TIGHT_G = /(?<=\p{L})—(?=\p{L})/gu;

    var COMMA_BEFORE = /^(and|but|or|nor|so|yet|like|just|as|such)\b/i;
    var CLAUSE_AHEAD = /^(it|its|it's|they|their|this|that|that's|these|those|there|there's|we|you|he|she|each|every)\b/i;
    var ARTICLE = /^(a|an|the)\b/i;

    /* Что поставить вместо тире по адресу off. Возвращает строку-замену. */
    function pick(s, off) {
        var word = s.slice(off + 1);
        if (COMMA_BEFORE.test(word)) return ', ';
        if (CLAUSE_AHEAD.test(word)) return ': ';
        if (ARTICLE.test(word) && word.split(/\s+/).length <= 9) return ', ';
        return ' — ';
    }

    /* Границы предложения вокруг адреса off — чтобы отличить пару тире от одиночного. */
    function bounds(s, off) {
        var a = 0, b = s.length, i;
        for (i = off; i > 0; i--) {
            if (/[.!?\n]/.test(s.charAt(i - 1))) { a = i; break; }
        }
        for (i = off; i < s.length; i++) {
            if (/[.!?\n]/.test(s.charAt(i))) { b = i + 1; break; }
        }
        return [a, b];
    }

    /* Список правок для строки: [[адрес, замена], …], по одному символу на адрес. */
    function edits(s) {
        var all = [], m;
        TIGHT_G.lastIndex = 0;
        while ((m = TIGHT_G.exec(s))) all.push(m.index);
        TIGHT_G.lastIndex = 0;
        if (!all.length) return [];

        if (LANG !== 'en') {
            /* Русский, испанский, французский, арабский: правила выше написаны про
               английские союзы, переносить их на другие языки — гадание. Разводим
               пробелами, что для русского вдобавок и есть верная типографика. */
            return all.map(function (o) { return [o, ' — ']; });
        }

        var out = [], used = {};
        for (var i = 0; i < all.length; i++) {
            if (used[all[i]]) continue;
            var bb = bounds(s, all[i]);
            var pair = [];
            for (var j = i; j < all.length && all[j] < bb[1]; j++) {
                if (all[j] >= bb[0]) pair.push(all[j]);
            }
            if (pair.length >= 2) {
                /* Пара — вставка внутрь фразы. Запятые с двух сторон: «qubit, a tiny
                   loop with zero resistance, crunches problems». Если внутри вставки
                   своя запятая, ещё две превратят фразу в кашу — тогда скобки. */
                var inner = s.slice(pair[0] + 1, pair[1]);
                var paren = inner.indexOf(',') >= 0;
                out.push([pair[0], paren ? ' (' : ', ']);
                out.push([pair[1], paren ? ') ' : ', ']);
                used[pair[0]] = used[pair[1]] = 1;
                /* Третье и последующие тире того же предложения — просто пробелами. */
                for (var k = 2; k < pair.length; k++) {
                    out.push([pair[k], ' — ']);
                    used[pair[k]] = 1;
                }
            } else {
                out.push([all[i], pick(s, all[i])]);
                used[all[i]] = 1;
            }
        }
        return out;
    }

    var SKIP = {SCRIPT: 1, STYLE: 1, CODE: 1, PRE: 1, TEXTAREA: 1, INPUT: 1, NOSCRIPT: 1};
    var INLINE = {A: 1, SPAN: 1, EM: 1, STRONG: 1, B: 1, I: 1, U: 1, S: 1, SUP: 1, SUB: 1,
                  SMALL: 1, MARK: 1, ABBR: 1, Q: 1, CITE: 1, TIME: 1, VAR: 1, WBR: 1, BR: 1};

    function skip(el) {
        for (var e = el; e && e !== document.body; e = e.parentElement) {
            if (SKIP[e.tagName]) return true;
            var c = e.className;
            if (typeof c === 'string' && /\b(katex|formula-latex|no-typo)\b/.test(c)) return true;
            if (e.getAttribute && e.getAttribute('data-no-typo') !== null) return true;
        }
        return false;
    }

    /* Ближайший НЕ строчный предок: он и есть абзац, по которому склеиваем текст. */
    function blockOf(el) {
        var e = el;
        while (e && INLINE[e.tagName]) e = e.parentElement;
        return e || document.body;
    }

    function sweep(root) {
        if (!root || (root.nodeType !== 1 && root.nodeType !== 11)) return;
        var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
        var node, groups = [], last = null, cur = null;
        while ((node = w.nextNode())) {
            var parent = node.parentElement;
            if (!parent || skip(parent)) { last = null; continue; }
            var blk = blockOf(parent);
            if (blk !== last) { cur = []; groups.push(cur); last = blk; }
            cur.push(node);
        }
        for (var g = 0; g < groups.length; g++) apply(groups[g]);
    }

    /* Литеральное «\n» посреди текста. Переводчик отдавал перенос строки экранированным,
       а разбор ответа считал «\n» перед латинской буквой началом команды LaTeX (\nu) и
       удваивал слэш — в тексте оставались два видимых символа. По-русски после переноса
       идёт кириллица, поэтому там их 141, а в английском, испанском и французском —
       по тридцать пять тысяч (владелец 29.08: «и там ещё символ встретился \nThe authors»).
       Причина закрыта в common.py, данные чистит tools/dash_fix.py; здесь убираем то,
       что уже лежит на страницах. Абзац при этом не появится — его расставляет сборщик, —
       но глаз больше не спотыкается о служебный значок. */
    var SLASH_N = /\\n(?=[A-ZА-ЯЁ])/g;

    function apply(nodes) {
        for (var q = 0; q < nodes.length; q++) {
            if (nodes[q].data.indexOf('\\n') >= 0) {
                var cleaned = nodes[q].data.replace(SLASH_N, '');
                if (cleaned !== nodes[q].data) nodes[q].data = cleaned;
            }
        }
        var s = '', starts = [], i;
        for (i = 0; i < nodes.length; i++) {
            starts.push(s.length);
            s += nodes[i].data;
        }
        if (s.indexOf('—') < 0 || !TIGHT.test(s)) return;
        var list = edits(s);
        if (!list.length) return;
        /* С конца: правка меняет длину, и адреса перед ней остаются верными. */
        list.sort(function (a, b) { return b[0] - a[0]; });
        for (i = 0; i < list.length; i++) {
            var off = list[i][0], rep = list[i][1];
            for (var n = nodes.length - 1; n >= 0; n--) {
                if (starts[n] <= off) {
                    var loc = off - starts[n];
                    var d = nodes[n].data;
                    if (d.charAt(loc) === '—') nodes[n].data = d.slice(0, loc) + rep + d.slice(loc + 1);
                    break;
                }
            }
        }
    }

    function start() {
        try { sweep(document.body); } catch (e) {}
        /* Лента, похожие статьи и карточки автора рисуются на клиенте из D1 уже после
           загрузки — без наблюдателя они остались бы нетронутыми. */
        if (!window.MutationObserver) return;
        var pending = [], timer = null;
        new MutationObserver(function (recs) {
            for (var i = 0; i < recs.length; i++) {
                for (var j = 0; j < recs[i].addedNodes.length; j++) {
                    if (recs[i].addedNodes[j].nodeType === 1) pending.push(recs[i].addedNodes[j]);
                }
            }
            if (timer || !pending.length) return;
            timer = setTimeout(function () {
                timer = null;
                var batch = pending; pending = [];
                for (var k = 0; k < batch.length; k++) {
                    try { sweep(batch[k]); } catch (e) {}
                }
            }, 60);
        }).observe(document.body, {childList: true, subtree: true});
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', start);
    } else {
        start();
    }
})();
