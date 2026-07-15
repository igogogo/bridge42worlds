// bridge42worlds · карусель hero/concept картинок на странице обучающей статьи
// (.theory-img-pair, изначально пара figure бок о бок — юзер-фидбек 2026-07-15: по ширине
// вылезала за край текста). Перестраивает разметку в одну картинку + стрелки, клик открывает
// лайтбокс (js/lightbox.js через .mosaic-open, тот же компонент, что и в статьях с arXiv).
(function () {
    document.querySelectorAll('.theory-img-pair').forEach(function (pair) {
        var figs = Array.prototype.slice.call(pair.querySelectorAll('figure'));
        if (figs.length < 2) return;
        var items = figs.map(function (fig) {
            var img = fig.querySelector('img');
            var cap = fig.querySelector('figcaption');
            return { src: img.getAttribute('src'), alt: img.getAttribute('alt') || '', caption: cap ? cap.textContent : '' };
        });
        pair.innerHTML = '';
        pair.classList.add('mosaic');

        var frame = document.createElement('div');
        frame.className = 'tip-frame';
        var link = document.createElement('a');
        link.className = 'mosaic-open';
        var img = document.createElement('img');
        link.appendChild(img);
        frame.appendChild(link);

        var prev = document.createElement('button');
        prev.type = 'button'; prev.className = 'mosaic-arrow mosaic-prev'; prev.setAttribute('aria-label', 'Prev'); prev.textContent = '‹';
        var next = document.createElement('button');
        next.type = 'button'; next.className = 'mosaic-arrow mosaic-next'; next.setAttribute('aria-label', 'Next'); next.textContent = '›';
        frame.appendChild(prev);
        frame.appendChild(next);

        var caption = document.createElement('p');
        caption.className = 'tip-caption';

        pair.appendChild(frame);
        pair.appendChild(caption);

        var idx = 0;
        function render() {
            var it = items[idx];
            img.src = it.src;
            img.alt = it.alt;
            link.href = it.src;
            caption.textContent = it.caption;
        }
        prev.addEventListener('click', function () { idx = (idx - 1 + items.length) % items.length; render(); });
        next.addEventListener('click', function () { idx = (idx + 1) % items.length; render(); });
        render();
    });
})();
