/* Плашка предзапуска: «мост ещё строится» — v0.8, ~80%, запуск ≈ через две недели.
 *
 * Решение владельца 2026-07-31: сайт в непродуктивной эксплуатации, посетитель должен
 * с порога видеть — мы ещё в разработке, но знакомиться уже можно; нашёл ошибку — напиши,
 * зовём в наблюдательный совет; проект открытый и некоммерческий.
 *
 * Поведение: при первом заходе — карточка под шапкой (на телефоне — снизу листом);
 * закрыл — сворачивается в маленький бейдж «β 80%» в углу, клик разворачивает обратно.
 * Выбор помнится 7 дней (localStorage). Языки — все пять, из <html lang>.
 *
 * Отзыв: форма шлёт POST /api/feedback (Worker: сохранить + алерт в Telegram-канал —
 * так мы ТОЧНО увидим). Ручка ещё не выложена или упала — честный фолбэк: открываем
 * почтовый клиент с готовым письмом. Требование владельца: ни одно сообщение не должно
 * потеряться молча.
 */
(function () {
    'use strict';
    var KEY = 'b42_beta_seen';
    var MAIL = 'bridge42worlds@gmail.com';
    var PCT = 80;

    var LANG = (document.documentElement.lang || 'en').slice(0, 2);
    var T = {
        ru: { title: 'Мост ещё строится', ver: 'версия 0.8 · предзапуск',
              body: 'Готово примерно на 80% — запуск через пару недель. Сайт уже живой: читайте, пробуйте, знакомьтесь со смыслом проекта.',
              found: 'Нашли ошибку или есть идея?', write: 'Написать нам',
              council: 'У нас есть наблюдательный совет — можем пригласить вас поучаствовать в разработке.',
              open: 'Проект открытый и некоммерческий.', about: 'О проекте',
              ph: 'Что вы заметили или предлагаете…', email_ph: 'Почта для ответа (необязательно)',
              send: 'Отправить', sent: 'Спасибо! Мы получили ваше сообщение.',
              mailFallback: 'Откроем ваш почтовый клиент — ручка отзывов ещё в пути.',
              close: 'Свернуть' },
        en: { title: 'The bridge is still being built', ver: 'v0.8 · pre-launch',
              body: 'About 80% ready — launching in a couple of weeks. The site is already alive: read, explore, get what we are about.',
              found: 'Found a bug or have an idea?', write: 'Write to us',
              council: 'We have an advisory board — we can invite you to take part in building the site.',
              open: 'An open, non-commercial project.', about: 'About',
              ph: 'What you noticed or suggest…', email_ph: 'Email for a reply (optional)',
              send: 'Send', sent: 'Thank you! We received your message.',
              mailFallback: 'Opening your mail app — the feedback endpoint is still on its way.',
              close: 'Dismiss' },
        es: { title: 'El puente aún se está construyendo', ver: 'v0.8 · prelanzamiento',
              body: 'Listo en torno al 80%: lanzamos en un par de semanas. El sitio ya está vivo: lea, explore, conozca nuestro sentido.',
              found: '¿Encontró un error o tiene una idea?', write: 'Escríbanos',
              council: 'Tenemos un consejo asesor: podemos invitarle a participar en el desarrollo.',
              open: 'Proyecto abierto y sin ánimo de lucro.', about: 'Sobre el proyecto',
              ph: 'Qué notó o qué propone…', email_ph: 'Correo para responder (opcional)',
              send: 'Enviar', sent: '¡Gracias! Recibimos su mensaje.',
              mailFallback: 'Abrimos su correo: el buzón del sitio aún está en camino.',
              close: 'Ocultar' },
        ar: { title: 'الجسر ما زال قيد البناء', ver: 'الإصدار 0.8 · ما قبل الإطلاق',
              body: 'جاهز بنحو 80% — الإطلاق خلال أسبوعين تقريبًا. الموقع حيّ بالفعل: اقرأ وجرّب وتعرّف على فكرتنا.',
              found: 'وجدت خطأ أو لديك فكرة؟', write: 'راسلنا',
              council: 'لدينا مجلس استشاري — يمكننا دعوتك للمشاركة في تطوير الموقع.',
              open: 'مشروع مفتوح وغير تجاري.', about: 'عن المشروع',
              ph: 'ما الذي لاحظته أو تقترحه…', email_ph: 'بريد للرد (اختياري)',
              send: 'إرسال', sent: 'شكرًا! وصلتنا رسالتك.',
              mailFallback: 'سنفتح بريدك — قناة الملاحظات ما زالت في الطريق.',
              close: 'إخفاء' },
        fr: { title: 'Le pont est encore en construction', ver: 'v0.8 · pré-lancement',
              body: 'Prêt à environ 80 % — lancement dans deux semaines. Le site vit déjà : lisez, explorez, saisissez notre idée.',
              found: 'Un bug, une idée ?', write: 'Écrivez-nous',
              council: 'Nous avons un conseil consultatif — nous pouvons vous inviter à participer au développement.',
              open: 'Projet ouvert et non commercial.', about: 'À propos',
              ph: 'Ce que vous avez remarqué ou proposez…', email_ph: 'E-mail pour la réponse (facultatif)',
              send: 'Envoyer', sent: 'Merci ! Message bien reçu.',
              mailFallback: 'Ouverture de votre messagerie — la boîte du site arrive bientôt.',
              close: 'Réduire' }
    };
    var L = T[LANG] || T.en;
    var aboutUrl = '/lang/' + (T[LANG] ? LANG : 'en') + '/about.html';

    function esc(s) { var d = document.createElement('i'); d.textContent = s; return d.innerHTML; }
    function seen() { try { var v = localStorage.getItem(KEY); return v && (Date.now() - Number(v) < 7 * 864e5); } catch (e) { return false; } }
    function remember() { try { localStorage.setItem(KEY, String(Date.now())); } catch (e) {} }

    var card = document.createElement('div');
    card.className = 'beta-card';
    card.setAttribute('role', 'dialog');
    card.innerHTML =
        '<button type="button" class="beta-x" aria-label="' + esc(L.close) + '">×</button>' +
        '<div class="beta-head">🌉 <b>' + esc(L.title) + '</b> <span class="beta-ver">' + esc(L.ver) + '</span></div>' +
        '<div class="beta-bar"><i style="width:' + PCT + '%"></i><em>' + PCT + '%</em></div>' +
        '<p>' + esc(L.body) + '</p>' +
        '<p class="beta-links">' + esc(L.open) + ' <a href="' + aboutUrl + '">' + esc(L.about) + '</a> · ' +
        '<a href="/council.html">' + esc(L.council) + '</a></p>' +
        '<div class="beta-form">' +
        '<div class="beta-found">' + esc(L.found) + '</div>' +
        '<textarea rows="2" class="beta-msg" placeholder="' + esc(L.ph) + '"></textarea>' +
        '<input type="email" class="beta-mail" placeholder="' + esc(L.email_ph) + '">' +
        '<button type="button" class="beta-send">' + esc(L.send) + '</button>' +
        '</div>';

    var badge = document.createElement('button');
    badge.type = 'button';
    badge.className = 'beta-badge';
    badge.innerHTML = 'β <i style="width:' + PCT + '%"></i><span>' + PCT + '%</span>';
    badge.title = L.title + ' — ' + L.ver;

    function show() { card.classList.add('on'); badge.classList.remove('on'); }
    function hide() { card.classList.remove('on'); badge.classList.add('on'); remember(); }
    card.querySelector('.beta-x').onclick = hide;
    badge.onclick = show;

    card.querySelector('.beta-send').onclick = function () {
        var msg = card.querySelector('.beta-msg').value.trim();
        if (!msg) { card.querySelector('.beta-msg').focus(); return; }
        var mail = card.querySelector('.beta-mail').value.trim();
        var btn = this;
        btn.disabled = true;
        var payload = { message: msg.slice(0, 2000), email: mail.slice(0, 120),
                        page: location.pathname, lang: LANG };
        fetch('/api/feedback', {
            method: 'POST', headers: { 'content-type': 'application/json' },
            body: JSON.stringify(payload)
        }).then(function (r) {
            if (!r.ok) throw new Error('http ' + r.status);
            var f = card.querySelector('.beta-form');
            f.innerHTML = '<div class="beta-found">' + esc(L.sent) + '</div>';
        }).catch(function () {
            // Ручки ещё нет или сеть упала — сообщение НЕ теряем: готовое письмо.
            btn.disabled = false;
            var f = card.querySelector('.beta-found');
            f.textContent = L.mailFallback;
            location.href = 'mailto:' + MAIL +
                '?subject=' + encodeURIComponent('bridge42worlds β: отзыв со страницы ' + location.pathname) +
                '&body=' + encodeURIComponent(msg + (mail ? '\n\n← ' + mail : ''));
        });
    };

    document.addEventListener('DOMContentLoaded', function () {
        document.body.appendChild(card);
        document.body.appendChild(badge);
        if (seen()) badge.classList.add('on'); else card.classList.add('on');
    });
})();
