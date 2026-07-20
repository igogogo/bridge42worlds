// bridge42worlds · лайтбокс для картинок статьи (.mosaic-open) — открытие на месте вместо
// новой вкладки, стрелки вперёд/назад по всем картинкам статьи, подпись всегда видна.
(function () {
    let items = [];   // [{src, caption}] текущей галереи
    let idx = 0;
    let box = null;

    function build() {
        if (box) return box;
        box = document.createElement('div');
        box.className = 'lightbox';
        box.hidden = true;
        box.innerHTML =
            '<button type="button" class="lightbox-close" aria-label="Close">×</button>' +
            '<button type="button" class="lightbox-prev" aria-label="Prev">‹</button>' +
            '<figure class="lightbox-frame"><img class="lightbox-img" alt=""><figcaption class="lightbox-caption"></figcaption></figure>' +
            '<button type="button" class="lightbox-next" aria-label="Next">›</button>';
        document.body.appendChild(box);
        box.querySelector('.lightbox-close').addEventListener('click', close);
        box.querySelector('.lightbox-prev').addEventListener('click', () => show(idx - 1));
        box.querySelector('.lightbox-next').addEventListener('click', () => show(idx + 1));
        box.addEventListener('click', e => { if (e.target === box) close(); });
        return box;
    }

    function show(i) {
        idx = (i + items.length) % items.length;
        const it = items[idx];
        const img = box.querySelector('.lightbox-img');
        img.src = it.src;
        img.alt = it.caption;
        box.querySelector('.lightbox-caption').textContent = it.caption;
        const multi = items.length > 1;
        box.querySelector('.lightbox-prev').style.display = multi ? '' : 'none';
        box.querySelector('.lightbox-next').style.display = multi ? '' : 'none';
    }

    function open(gallery, startIdx) {
        build();
        items = gallery;
        box.hidden = false;
        document.body.style.overflow = 'hidden';
        show(startIdx);
    }
    // Публичный вход для js/gallery.js: галерея статьи открывает лайтбокс со ВСЕМИ картинками
    // с текущего индекса (клик по главному изображению), минуя делегирование по .mosaic-open.
    window.openLightbox = open;

    function close() {
        if (!box) return;
        box.hidden = true;
        document.body.style.overflow = '';
    }

    document.addEventListener('click', e => {
        const link = e.target.closest('.mosaic-open');
        if (!link) return;
        e.preventDefault();
        // Обложка (.ai-cover) не внутри .mosaic — своя одиночная "галерея" из одной картинки,
        // не мешаем её с подписанными рисунками статьи (иначе на весь экран может открыться
        // обложка со стрелкой на первый рисунок статьи).
        const track = link.closest('.mosaic-track, .mosaic');
        const links = track ? [...track.querySelectorAll('.mosaic-open')] : [link];
        const gallery = links.map(a => {
            const img = a.querySelector('img');
            return { src: a.getAttribute('href'), caption: img ? img.alt : '' };
        });
        open(gallery, links.indexOf(link));
    });

    document.addEventListener('keydown', e => {
        if (!box || box.hidden) return;
        if (e.key === 'Escape') close();
        else if (e.key === 'ArrowLeft') show(idx - 1);
        else if (e.key === 'ArrowRight') show(idx + 1);
    });
})();
