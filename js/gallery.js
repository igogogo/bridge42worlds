// bridge42worlds · галерея статьи: одно главное изображение + лента превью.
// Клик по превью меняет главное «в окне», ‹ › листают по всем картинкам, клик по главному —
// полноэкранный лайтбокс (js/lightbox.js, window.openLightbox) с текущего индекса.
// Разметку рендерит gen_mosaic() в generate.py. Одиночная картинка — без ленты/стрелок.
(function () {
    document.querySelectorAll('.gallery').forEach(function (g) {
        var mainImg = g.querySelector('.gallery-main-img');
        if (!mainImg) return;
        var mainLink = g.querySelector('.gallery-main');
        var cap = g.querySelector('.gallery-caption');
        var thumbs = [].slice.call(g.querySelectorAll('.gallery-thumb'));
        var images = thumbs.length
            ? thumbs.map(function (t) { return { src: t.dataset.src, caption: t.dataset.cap || '' }; })
            : [{ src: mainImg.getAttribute('src'), caption: mainImg.getAttribute('alt') || '' }];
        var idx = 0;

        function show(i) {
            idx = (i + images.length) % images.length;
            var it = images[idx];
            mainImg.src = it.src;
            mainImg.alt = it.caption;
            if (cap) { cap.textContent = it.caption; cap.style.display = it.caption ? '' : 'none'; }
            thumbs.forEach(function (t, j) { t.classList.toggle('is-active', j === idx); });
        }

        thumbs.forEach(function (t, j) { t.addEventListener('click', function () { show(j); }); });

        var prev = g.querySelector('.gallery-prev'), next = g.querySelector('.gallery-next');
        if (prev) prev.addEventListener('click', function (e) { e.stopPropagation(); e.preventDefault(); show(idx - 1); });
        if (next) next.addEventListener('click', function (e) { e.stopPropagation(); e.preventDefault(); show(idx + 1); });

        if (mainLink) mainLink.addEventListener('click', function (e) {
            e.preventDefault();
            if (window.openLightbox) window.openLightbox(images, idx);
        });

        show(0);
    });
})();
