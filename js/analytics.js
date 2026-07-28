// Аналитика-дашборд «карта облака»: 3D-россыпь статей/авторов, которую можно покрутить мышью.
// Self-contained canvas (без внешних либ — строгий CSP). Данные: data/analytics/*.json (офлайн-
// препросчёт analytics_build.py, БЕЗ DeepSeek). Юзер 2026-07-24: показать группировки, 3D, «вау».
(function () {
  var root = document.getElementById('analytics');
  // Мини-панель вида: без неё сцена «замирала» — перетаскивание выключает автовращение,
  // а включить обратно было нечем (замечание юзера 2026-07-28).
  var CTL = ({
    ru: { spin: 'вращение', zin: 'приблизить', zout: 'отдалить', reset: 'вернуть вид' },
    en: { spin: 'auto-rotate', zin: 'zoom in', zout: 'zoom out', reset: 'reset view' },
    es: { spin: 'rotación', zin: 'acercar', zout: 'alejar', reset: 'restablecer vista' },
    ar: { spin: 'دوران تلقائي', zin: 'تقريب', zout: 'إبعاد', reset: 'إعادة العرض' }
  })[LANG] || { spin: 'auto-rotate', zin: 'zoom in', zout: 'zoom out', reset: 'reset view' };


  if (!root) return;
  var LANG = window.lang || 'en';
  var L = ({
    ru: { title: 'Карта проекта', articles: 'Статьи', authors: 'Авторы', loading: 'Считаем карту…',
          hint: 'тяни — повернуть · колесо — зум · клик по точке', clusters: 'Тематические группы', n: 'точек',
          theoryExp: 'Цвет точки: экспериментатор (охра) → теоретик (циан)',
          introA: 'Каждая точка — <b>статья</b>. Чем ближе две точки, тем больше у статей общих тем. Цвет — <b>тематическая группа</b> (кластер), в которую их собрал алгоритм по общим тегам. Покрути шар мышью, чтобы разглядеть, из чего состоит наше облако статей и какие темы рядом.',
          introB: 'Каждая точка — <b>автор</b> (все, кого мы разобрали, — тысячи). Рядом — авторы с похожим профилем работ; облака — это направления. Цвет — от <b>экспериментатора</b> к <b>теоретику</b> (по разделам его статей). Смысл не в отдельной точке, а в том, <b>как ведёт себя всё множество</b>: где плотные ядра, где редкие ветви.' },
    en: { title: 'Project map', articles: 'Articles', authors: 'Authors', loading: 'Building the map…',
          hint: 'drag to rotate · wheel to zoom · click a point', clusters: 'Topic groups', n: 'points',
          theoryExp: 'Point colour: experimentalist (ochre) → theorist (cyan)',
          introA: 'Each dot is an <b>article</b>. The closer two dots, the more topics the articles share. Colour = a <b>topic group</b> (cluster) the algorithm formed from shared tags. Rotate the sphere to see what our article cloud is made of and which themes sit together.',
          introB: 'Each dot is an <b>author</b> — every one we processed, thousands of them. Nearby dots share a similar body of work; the clouds are fields. Colour runs from <b>experimentalist</b> to <b>theorist</b> (from their papers’ areas). The point isn’t any single dot but <b>how the whole set behaves</b>: where the dense cores are, where the thin branches reach.' },
    es: { title: 'Mapa del proyecto', articles: 'Artículos', authors: 'Autores', loading: 'Construyendo el mapa…',
          hint: 'arrastra para rotar · rueda para zoom · clic en un punto', clusters: 'Grupos temáticos', n: 'puntos',
          theoryExp: 'Color: experimental (ocre) → teórico (cian)',
          introA: 'Cada punto es un <b>artículo</b>. Cuanto más cerca, más temas comparten. El color es un <b>grupo temático</b> formado por etiquetas comunes. Gira la esfera para ver de qué se compone nuestra nube de artículos.',
          introB: 'Cada punto es un <b>autor</b> — todos los que procesamos, miles. Los cercanos comparten un perfil similar; las nubes son campos. El color va de <b>experimental</b> a <b>teórico</b>. Lo importante no es un punto, sino <b>cómo se comporta todo el conjunto</b>: dónde están los núcleos densos y dónde las ramas escasas.' },
    ar: { title: 'خريطة المشروع', articles: 'المقالات', authors: 'المؤلفون', loading: 'نبني الخريطة…',
          hint: 'اسحب للتدوير · العجلة للتكبير · انقر نقطة', clusters: 'مجموعات موضوعية', n: 'نقطة',
          theoryExp: 'لون النقطة: تجريبي (أوكر) → نظري (سماوي)',
          introA: 'كل نقطة <b>مقالة</b>. كلما اقتربت نقطتان زادت المواضيع المشتركة. اللون = <b>مجموعة موضوعية</b> شكّلها الخوارزم من الوسوم المشتركة. أدر الكرة لترى مِمّ تتكوّن سحابة مقالاتنا.',
          introB: 'كل نقطة <b>مؤلف</b> — كل من عالجناهم، بالآلاف. المتجاورون لهم ملف عمل متشابه؛ والسحب هي المجالات. يتدرّج اللون من <b>تجريبي</b> إلى <b>نظري</b>. المهم ليس نقطة واحدة بل <b>كيف يتصرّف المجموع كله</b>: أين النوى الكثيفة وأين الفروع المتناثرة.' }
  })[LANG] || null;
  var T = L || { title: 'Project map', articles: 'Articles', authors: 'Authors', loading: '…',
                 hint: 'drag to rotate · wheel to zoom', clusters: 'Topic groups', n: 'points',
                 theoryExp: 'experimentalist → theorist', introA: '', introB: '' };
  // Вкладка «Полёт» — интерактивное путешествие сквозь облако статей (юзер 2026-07-25: «чтобы можно
  // было побродить как в 3D, поиграть; путешествие по нашей вселенной»).
  var FLY = ({
    ru: { tab: 'Полёт', fs: 'на весь экран', speed: 'скорость', hint: 'веди — рулить · колесо/ползунок — скорость · клик по звезде в прицеле — открыть',
          intro: 'Ты <b>летишь сквозь нашу вселенную статей</b>. Каждая звезда — работа; чем ярче, тем ближе. Веди мышью или пальцем, чтобы поворачивать, меняй скорость колесом или ползунком. Наведись на звезду в центре — узнаешь её; кликни — откроешь.' },
    en: { tab: 'Fly', fs: 'fullscreen', speed: 'speed', hint: 'steer to turn · wheel/slider for speed · click a star in the crosshair to open',
          intro: 'You are <b>flying through our universe of articles</b>. Each star is a paper; the brighter, the closer. Steer with mouse or finger, change speed with the wheel or slider. Aim at the star in the centre to see it — click to open.' },
    es: { tab: 'Vuelo', fs: 'pantalla completa', speed: 'velocidad', hint: 'dirige para girar · rueda/control para velocidad · clic en la estrella central para abrir',
          intro: 'Vuelas <b>por nuestro universo de artículos</b>. Cada estrella es un trabajo; cuanto más brillante, más cerca. Dirige con el ratón o el dedo, cambia la velocidad con la rueda o el control. Apunta a la estrella del centro para verla y haz clic para abrirla.' },
    ar: { tab: 'تحليق', fs: 'ملء الشاشة', speed: 'السرعة', hint: 'وجّه للدوران · العجلة/المنزلق للسرعة · انقر النجمة في المنتصف لفتحها',
          intro: 'أنت <b>تحلّق عبر كوننا من المقالات</b>. كل نجمة بحث؛ كلما زاد سطوعها اقتربت. وجّه بالفأرة أو الإصبع، وغيّر السرعة بالعجلة أو المنزلق. صوّب نحو النجمة في المنتصف لتراها وانقر لفتحها.' }
  })[LANG] || { tab: 'Fly', fs: 'fullscreen', speed: 'speed', hint: 'steer · wheel = speed · click centre star', intro: '' };
  var HEAT = ({
    ru: { tab: 'Тепло', hint: 'тяни — вращать · колесо — приблизить',
          intro: 'Тепловой <b>ландшафт проекта</b>: по одной оси — тематические группы, по другой — месяцы. Чем выше и ярче столбик, тем больше статей вышло по этой теме в этот месяц. Тяни, чтобы покрутить.' },
    en: { tab: 'Heat', hint: 'drag to rotate · wheel to zoom',
          intro: 'A heat <b>landscape of the project</b>: one axis is topic groups, the other is months. The taller and brighter the bar, the more articles came out on that topic that month. Drag to rotate.' },
    es: { tab: 'Calor', hint: 'arrastra para girar · rueda para acercar',
          intro: 'Un <b>paisaje térmico del proyecto</b>: un eje son los grupos temáticos, el otro los meses. Cuanto más alta y brillante la barra, más artículos hubo. Arrastra para girar.' },
    ar: { tab: 'الحرارة', hint: 'اسحب للتدوير · العجلة للتقريب',
          intro: 'تضاريس حرارية <b>للمشروع</b>: محور للمجموعات الموضوعية وآخر للأشهر. كلما ارتفع العمود وسطع، زادت المقالات في ذلك الشهر. اسحب للتدوير.' }
  })[LANG] || { tab: 'Heat', hint: 'drag to rotate', intro: '' };

  // Новые представления (идеи владельца 2026-07-27): «замкнутое множество, покрутить», лист Мёбиуса.
  var VIEWS = ({
    ru: {
      sphere: 'Сфера', mobius: 'Мёбиус', matrix: 'Связи',
      sphereIntro: 'Всё знание проекта на <b>одной сфере</b>: понятия, законы и учёные разложены так, что близкое по смыслу оказалось рядом. Это <b>замкнутое множество</b> — у знания нет края, поверхность возвращается к себе. Крути глобус и смотри, какие материки образовались.',
      mobiusIntro: 'Наши статьи на <b>ленте Мёбиуса</b>. У неё одна сторона: идёшь вперёд — и возвращаешься к началу, только перевёрнутым. Так и с наукой: путь по «внешней» стороне незаметно выводит на «внутреннюю». Цвет — тематическая группа, лента закручена по времени.',
      matrixIntro: 'Квадрат <b>понятие × понятие</b>: чем ярче клетка, тем чаще два понятия встречаются в одной статье. Плотные квадраты вдоль диагонали — это области науки. А одинокие яркие точки вдали от диагонали — <b>мосты между дисциплинами</b>, самое интересное, что у нас есть.',
      hint: 'тяни — вращать · колесо — приблизить · наведи на точку'
    },
    en: {
      sphere: 'Sphere', mobius: 'Möbius', matrix: 'Links',
      sphereIntro: 'All the project’s knowledge on <b>one sphere</b>: concepts, laws and scientists arranged so that related things sit together. A <b>closed set</b> — knowledge has no edge, the surface returns to itself. Spin the globe and see which continents formed.',
      mobiusIntro: 'Our articles on a <b>Möbius strip</b>. It has one side: go forward and you return to the start, flipped. Science works the same way — the “outer” path quietly becomes the inner one. Colour is the topic group; the strip is wound by time.',
      matrixIntro: 'A <b>concept × concept</b> grid: the brighter the cell, the more often two ideas appear in one article. Dense squares along the diagonal are fields of science. Lone bright dots far from it are <b>bridges between disciplines</b> — the most interesting thing we have.',
      hint: 'drag to rotate · wheel to zoom · hover a point'
    },
    es: {
      sphere: 'Esfera', mobius: 'Möbius', matrix: 'Enlaces',
      sphereIntro: 'Todo el conocimiento en <b>una esfera</b>: conceptos, leyes y científicos colocados de modo que lo afín quede junto. Un <b>conjunto cerrado</b>: el saber no tiene borde. Gira el globo y mira qué continentes se formaron.',
      mobiusIntro: 'Nuestros artículos en una <b>cinta de Möbius</b>. Tiene una sola cara: avanzas y vuelves al inicio, del revés. Así es la ciencia. El color es el grupo temático.',
      matrixIntro: 'Una malla <b>concepto × concepto</b>: cuanto más brillante la celda, más veces aparecen juntos. Los cuadros densos son campos; los puntos aislados, <b>puentes entre disciplinas</b>.',
      hint: 'arrastra para rotar · rueda para acercar'
    },
    ar: {
      sphere: 'الكرة', mobius: 'موبيوس', matrix: 'الروابط',
      sphereIntro: 'كل معرفة المشروع على <b>كرة واحدة</b>: المفاهيم والقوانين والعلماء موزّعون بحيث يتجاور المتقارب. إنها <b>مجموعة مغلقة</b> — لا حافة للمعرفة. أدر الكرة وانظر أي قارات تشكّلت.',
      mobiusIntro: 'مقالاتنا على <b>شريط موبيوس</b>. له وجه واحد: تمضي قدمًا فتعود إلى البداية مقلوبًا. هكذا هو العلم. اللون يدل على المجموعة الموضوعية.',
      matrixIntro: 'شبكة <b>مفهوم × مفهوم</b>: كلما سطعت الخلية زاد ورودهما معًا. المربعات الكثيفة حقول علمية، والنقاط المنعزلة <b>جسور بين التخصصات</b>.',
      hint: 'اسحب للتدوير · العجلة للتقريب'
    }
  })[LANG] || null;
  var V = VIEWS || { sphere: 'Sphere', mobius: 'Mobius', matrix: 'Links',
                     sphereIntro: '', mobiusIntro: '', matrixIntro: '', hint: 'drag to rotate' };


  var V2 = ({
    ru: { tree: 'Дерево', spectrum: 'Ритм',
          treeIntro: 'Знание <b>упорядоченным деревом</b>, а не клубком связей: от ствола расходятся ветви-направления, на каждой — листья-статьи. Ветви подписаны именами, которые дал им ИИ, и отсортированы по весу: сверху то, чем проект богат, снизу — тонкие места.',
          specIntro: 'Есть ли у науки <b>ритм</b>? Это периодограмма Ломба-Скаргла — метод из астрономии для рядов с пропусками (в какие-то дни статей нет вовсе). По горизонтали период в днях, по вертикали сила повтора. Пики показывают, с какой периодичностью в нашем архиве всплывают публикации.' },
    en: { tree: 'Tree', spectrum: 'Rhythm',
          treeIntro: 'Knowledge as an <b>ordered tree</b> rather than a tangle: branches are directions, leaves are articles. Branch names come from AI, sorted by weight — the rich topics on top, thin ones below.',
          specIntro: 'Does science have a <b>rhythm</b>? A Lomb-Scargle periodogram — an astronomy method for uneven series (some days have no papers). X is period in days, Y is the strength of repetition. Peaks show how often publications surface in our archive.' },
    es: { tree: 'Árbol', spectrum: 'Ritmo',
          treeIntro: 'El conocimiento como <b>árbol ordenado</b>: las ramas son direcciones, las hojas artículos. Los nombres los da la IA y se ordenan por peso.',
          specIntro: '¿Tiene ritmo la ciencia? Periodograma de Lomb-Scargle, método astronómico para series irregulares. X: periodo en días; Y: fuerza de repetición.' },
    ar: { tree: 'الشجرة', spectrum: 'الإيقاع',
          treeIntro: 'المعرفة على هيئة <b>شجرة مرتّبة</b> لا شبكة متشابكة: الأفرع اتجاهات والأوراق مقالات. أسماء الأفرع من الذكاء الاصطناعي، مرتّبة حسب الوزن.',
          specIntro: 'هل للعلم <b>إيقاع</b>؟ مخطط لومب-سكارغل الدوري، وهو أسلوب فلكي للسلاسل غير المنتظمة. الأفقي: الدورة بالأيام، الرأسي: قوة التكرار.' }
  })[LANG] || { tree: 'Tree', spectrum: 'Rhythm', treeIntro: '', specIntro: '' };


  var V3 = ({
    ru: { tab: 'Напряжение',
          intro: 'Самое интересное в науке — не там, где много работ, а там, где области <b>сцепляются</b>. Слева — <b>мосты</b>: понятия из разных групп, которые постоянно встречаются в одних статьях. Справа — <b>разрывы</b>: области, где у нас много материала, но общего понятия между ними нет. Разрыв это не ошибка, а подсказка, куда расти.',
          bridges: 'Мосты между областями', gaps: 'Разрывы: связь напрашивается, но не названа',
          leads: 'что к нему ведёт' },
    en: { tab: 'Tension',
          intro: 'The interesting part of science is not where papers pile up, but where fields <b>lock together</b>. Left — <b>bridges</b>: concepts from different groups that keep appearing in the same articles. Right — <b>gaps</b>: areas rich in material but with no shared concept between them. A gap is not an error, it is a hint where to grow.',
          bridges: 'Bridges between fields', gaps: 'Gaps: a link begs to exist but is unnamed',
          leads: 'what leads to it' },
    es: { tab: 'Tensión',
          intro: 'Lo interesante no está donde hay muchos trabajos, sino donde los campos <b>se enganchan</b>. Izquierda: <b>puentes</b>. Derecha: <b>vacíos</b>, áreas ricas sin concepto común.',
          bridges: 'Puentes entre campos', gaps: 'Vacíos: falta el concepto que une', leads: 'qué lleva a él' },
    ar: { tab: 'التوتر',
          intro: 'الأهم ليس حيث تكثر الأبحاث بل حيث <b>تتشابك</b> المجالات. يسارًا <b>الجسور</b>، ويمينًا <b>الفجوات</b>: مجالات غنية بلا مفهوم يجمعها.',
          bridges: 'جسور بين المجالات', gaps: 'فجوات: رابط ينقصه الاسم', leads: 'ما يقود إليه' }
  })[LANG] || { tab: 'Tension', intro: '', bridges: 'Bridges', gaps: 'Gaps', leads: 'leads to' };


  // ── Трактовка: что именно видно на этом виде ПРЯМО СЕЙЧАС (считается по данным) ──────────
  var RD = ({
    ru: { h: 'Что это значит', of: 'из', arts: 'статей', biggest: 'Самая крупная группа',
          share: 'это {p}% архива', period: 'Самый заметный ритм — период около {n} дней',
          periodWhy: 'значит публикации приходят волнами такой длительности, а не ровным потоком',
          branches: 'Ветвей на дереве', thick: 'самая толстая', thin: 'самая тонкая',
          bridge: 'Сильнейший мост между областями', gapTxt: 'Разрывов, где связь напрашивается, но понятия нет',
          dense: 'Плотнее всего понятия связаны внутри', links: 'связей между разными областями',
          people: 'исследователей', theorists: 'из них тяготеют к теории', spread: 'облако раскинуто на',
          groups: 'тематических групп', noData: 'Данных пока мало для вывода.' },
    en: { h: 'What this means', of: 'of', arts: 'articles', biggest: 'Largest group',
          share: 'that is {p}% of the archive', period: 'Strongest rhythm — a period near {n} days',
          periodWhy: 'so papers arrive in waves of that length rather than a steady stream',
          branches: 'Branches on the tree', thick: 'thickest', thin: 'thinnest',
          bridge: 'Strongest bridge between fields', gapTxt: 'Gaps where a link begs to exist but has no concept',
          dense: 'Concepts are most tightly linked inside', links: 'links between different fields',
          people: 'researchers', theorists: 'of them lean theoretical', spread: 'the cloud spans',
          groups: 'topic groups', noData: 'Not enough data yet.' },
    es: { h: 'Qué significa', of: 'de', arts: 'artículos', biggest: 'Grupo más grande',
          share: 'es el {p}% del archivo', period: 'Ritmo más fuerte: periodo de unos {n} días',
          periodWhy: 'los artículos llegan en oleadas de esa duración', branches: 'Ramas del árbol',
          thick: 'la más gruesa', thin: 'la más fina', bridge: 'Puente más fuerte',
          gapTxt: 'Vacíos sin concepto que una', dense: 'Los conceptos se enlazan más dentro de',
          links: 'enlaces entre campos', people: 'investigadores', theorists: 'tienden a la teoría',
          spread: 'la nube abarca', groups: 'grupos temáticos', noData: 'Aún faltan datos.' },
    ar: { h: 'ماذا يعني هذا', of: 'من', arts: 'مقالة', biggest: 'أكبر مجموعة',
          share: 'أي {p}% من الأرشيف', period: 'أقوى إيقاع — دورة نحو {n} يومًا',
          periodWhy: 'أي أن الأبحاث تأتي على موجات بهذا الطول', branches: 'أفرع الشجرة',
          thick: 'الأسمك', thin: 'الأدق', bridge: 'أقوى جسر بين المجالات',
          gapTxt: 'فجوات ينقصها مفهوم جامع', dense: 'ترتبط المفاهيم بكثافة داخل',
          links: 'روابط بين مجالات مختلفة', people: 'باحثًا', theorists: 'يميلون إلى النظرية',
          spread: 'تمتد السحابة على', groups: 'مجموعات موضوعية', noData: 'البيانات غير كافية بعد.' }
  })[LANG] || null;
  var R = RD || { h: 'What this means', noData: '' };

  function clusterTitle(c) {
    var titles = (cache.articles && cache.articles.titles) || (state.data && state.data.titles) || {};
    var lt = titles[c] && (titles[c][LANG] || titles[c].en);
    return (lt && lt.title) || ('#' + c);
  }

  function reading(mode) {
    var d = state.data || {};
    var out = [];
    try {
      if (mode === 'articles' || mode === 'mobius' || mode === 'fly') {
        var cnt = {}; (d.points || []).forEach(function (p) { cnt[p.c] = (cnt[p.c] || 0) + 1; });
        var top = Object.keys(cnt).sort(function (a, b) { return cnt[b] - cnt[a]; })[0];
        var n = d.n || (d.points || []).length;
        if (top != null) {
          out.push('<b>' + R.biggest + ':</b> «' + clusterTitle(+top) + '» — ' + cnt[top] + ' ' + R.arts
                   + ', ' + R.share.replace('{p}', Math.round(cnt[top] / Math.max(1, n) * 100)) + '.');
          out.push(Object.keys(cnt).length + ' ' + R.groups + ' ' + R.of + ' ' + n + ' ' + R.arts + '.');
        }
      } else if (mode === 'authors') {
        var pts = d.points || [];
        var th = pts.filter(function (p) { return (p.th || 0) > 0.6; }).length;
        out.push('<b>' + pts.length.toLocaleString() + '</b> ' + R.people + ', ' + th.toLocaleString()
                 + ' ' + R.theorists + '.');
      } else if (mode === 'heat') {
        var h = state.heat;
        if (h) {
          var best = null;
          Object.keys(h.cells).forEach(function (k) { if (!best || h.cells[k] > h.cells[best]) best = k; });
          if (best) {
            var parts = best.split('|');
            out.push('<b>' + R.biggest + ':</b> «' + clusterTitle(+parts[0]) + '» — ' + h.cells[best]
                     + ' ' + R.arts + ' (' + parts[1] + ').');
          }
        }
      } else if (mode === 'spectrum') {
        var sp = state.spec;
        if (sp) {
          var pk = sp.pts.slice().sort(function (a, b) { return b.p - a.p; })[0];
          out.push('<b>' + R.period.replace('{n}', pk.per) + '</b> — ' + R.periodWhy + '.');
          out.push(sp.total + ' ' + R.arts + ' ' + R.of + ' ' + sp.days + ' ' + (LANG === 'ru' ? 'дней' : 'days') + '.');
        }
      } else if (mode === 'tree') {
        var tr = state.tree || [];
        if (tr.length) {
          out.push('<b>' + R.branches + ':</b> ' + tr.length + '. ' + R.thick + ' — «'
                   + clusterTitle(tr[0].c) + '» (' + tr[0].items.length + '), ' + R.thin + ' — «'
                   + clusterTitle(tr[tr.length - 1].c) + '» (' + tr[tr.length - 1].items.length + ').');
        }
      } else if (mode === 'tension') {
        var tn = state.tension;
        if (tn && tn.bridges && tn.bridges.length) {
          var b = tn.bridges[0];
          out.push('<b>' + R.bridge + ':</b> ' + niceLabel(b.a.id) + ' ⟷ ' + niceLabel(b.b.id) + '.');
          out.push(tn.bridges.length + ' ' + R.links + '. ' + R.gapTxt + ': ' + tn.gaps.length + '.');
        }
      } else if (mode === 'sphere' || mode === 'matrix') {
        var ents = (d.entities || []);
        var byC = {}; ents.forEach(function (e) { byC[e.c] = (byC[e.c] || 0) + 1; });
        var bc = Object.keys(byC).sort(function (a, b) { return byC[b] - byC[a]; })[0];
        out.push('<b>' + ents.length + '</b> ' + (LANG === 'ru' ? 'понятий в' : 'concepts in') + ' '
                 + Object.keys(byC).length + ' ' + R.groups + '.');
        if (bc != null) out.push(R.dense + ' «' + clusterTitle(+bc) + '» (' + byC[bc] + ').');
      }
    } catch (e) { /* трактовка не должна ронять вид */ }
    if (!out.length) return '';
    return '<div class="an-read"><div class="an-read-h">' + R.h + '</div><p>' + out.join(' ') + '</p></div>';
  }

  // честные подсказки: где нечего вращать — не обещаем вращение
  var HINTS = ({
    ru: { spectrum: 'наведи на пик — период в днях', tree: 'ветви сверху — самые крупные направления',
          tension: 'слева мосты, справа разрывы', matrix: 'ярче клетка — чаще встречаются вместе',
          sphere: 'тяни — вращать глобус · колесо — приблизить', mobius: 'тяни — вращать ленту · колесо — приблизить' },
    en: { spectrum: 'hover a peak — period in days', tree: 'top branches are the largest directions',
          tension: 'bridges on the left, gaps on the right', matrix: 'brighter cell — appear together more often',
          sphere: 'drag to spin the globe · wheel to zoom', mobius: 'drag to spin the strip · wheel to zoom' },
    es: { spectrum: 'pasa sobre un pico', tree: 'arriba las ramas mayores', tension: 'puentes y vacíos',
          matrix: 'celda más brillante = más coincidencias', sphere: 'arrastra para girar', mobius: 'arrastra para girar' },
    ar: { spectrum: 'مرّر فوق القمة', tree: 'الأفرع العليا هي الأكبر', tension: 'الجسور والفجوات',
          matrix: 'الخلية الأسطع تعني تكرارًا أكثر', sphere: 'اسحب لتدوير الكرة', mobius: 'اسحب لتدوير الشريط' }
  })[LANG] || {};

  var PAL = ['#2E8AA0', '#C77F3A', '#6C5CE7', '#2FA84F', '#D64545', '#C9A227', '#5AA9C9', '#E4A860',
             '#9B7EDE', '#4CAF50', '#E06666', '#00897B', '#8E24AA', '#F4511E', '#3949AB', '#00ACC1',
             '#7CB342', '#D81B60', '#5E35B1', '#FB8C00', '#43A047', '#1E88E5', '#6D4C41', '#546E7A'];

  // Панель-объяснение (юзер 2026-07-25: «дать объяснения — что такое кластеры, какие методы,
  // и внизу выводы про контент сайта»). Документация для пользователя, локализованная.
  var ABOUT = ({
    ru: '<h3>Как построена карта</h3>'
      + '<p>Статьи — связующая среда. Мы смотрим, какие <b>темы, разделы и понятия</b> встречаются в статьях вместе, '
      + 'и превращаем это в близость: похожие работы оказываются рядом. Всё считается <b>локально</b>, статистикой '
      + '(TF-IDF по тегам → кластеризация K-means → проекция в 3D методом t-SNE) — без обращения к ИИ, поэтому карту легко держать актуальной.</p>'
      + '<h3>Что значат группы и цвета</h3>'
      + '<ul><li><b>Точка</b> — статья (или автор). Чем ближе точки, тем больше общего.</li>'
      + '<li><b>Цвет</b> — тематическая группа (кластер), которую алгоритм выделил сам.</li>'
      + '<li><b>Название группы</b> даёт <b>ИИ</b>: он читает характерные теги кластера и пишет человеческое имя и краткую трактовку.</li>'
      + '<li>У авторов цвет ещё и по оси <b>экспериментатор → теоретик</b> (по разделам их статей).</li></ul>'
      + '<h3>Что сейчас на карте и куда развиваем</h3>'
      + '<p>Пока это две грани: <b>статьи</b> и <b>авторы</b> — весь наш контент, преломлённый через общие темы. '
      + 'Дальше строим <b>общую карту</b>: добавим вкладки <b>законов, учёных и тегов</b>, где всё связано между собой — '
      + 'чтобы можно было увидеть, из чего складывается знание проекта и куда оно растёт.</p>',
    en: '<h3>How the map is built</h3>'
      + '<p>Articles are the connective tissue. We look at which <b>topics, sections and concepts</b> co-occur in articles '
      + 'and turn that into closeness: similar work ends up nearby. Everything is computed <b>locally</b>, statistically '
      + '(TF-IDF over tags → K-means clustering → 3D projection via t-SNE) — no AI calls, so the map is easy to keep up to date.</p>'
      + '<h3>What the groups and colours mean</h3>'
      + '<ul><li>A <b>dot</b> is an article (or author). The closer the dots, the more they share.</li>'
      + '<li><b>Colour</b> is a topic group (cluster) the algorithm found on its own.</li>'
      + '<li>The <b>group name</b> comes from <b>AI</b>: it reads a cluster’s characteristic tags and writes a human name and a short reading.</li>'
      + '<li>For authors, colour also runs along an <b>experimentalist → theorist</b> axis.</li></ul>'
      + '<h3>What’s on the map now, and where it grows</h3>'
      + '<p>For now two facets: <b>articles</b> and <b>authors</b> — all our content refracted through shared themes. '
      + 'Next we build a <b>general map</b>: tabs for <b>laws, scientists and tags</b>, all interlinked — to see what the project’s knowledge is made of and where it’s heading.</p>',
    es: '<h3>Cómo se construye el mapa</h3>'
      + '<p>Los artículos son el tejido conector. Vemos qué <b>temas, secciones y conceptos</b> aparecen juntos '
      + 'y lo convertimos en cercanía. Todo se calcula <b>localmente</b> (TF-IDF → K-means → proyección 3D con t-SNE), sin IA.</p>'
      + '<h3>Qué significan los grupos y colores</h3>'
      + '<ul><li>Un <b>punto</b> es un artículo (o autor). Cuanto más cerca, más comparten.</li>'
      + '<li>El <b>color</b> es un grupo temático que el algoritmo encontró solo.</li>'
      + '<li>El <b>nombre del grupo</b> lo da la <b>IA</b> a partir de las etiquetas del clúster.</li>'
      + '<li>En autores, el color va de <b>experimental → teórico</b>.</li></ul>'
      + '<h3>Qué hay ahora y hacia dónde crece</h3>'
      + '<p>Por ahora dos facetas: <b>artículos</b> y <b>autores</b>. Luego un <b>mapa general</b> con pestañas de <b>leyes, científicos y etiquetas</b>.</p>',
    ar: '<h3>كيف بُنيت الخريطة</h3>'
      + '<p>المقالات هي النسيج الرابط. ننظر إلى <b>المواضيع والأقسام والمفاهيم</b> التي ترد معًا ونحوّلها إلى قُرب. '
      + 'يُحسب كل شيء <b>محليًا</b> إحصائيًا (TF-IDF ← تجميع K-means ← إسقاط ثلاثي الأبعاد t-SNE) دون ذكاء اصطناعي.</p>'
      + '<h3>ماذا تعني المجموعات والألوان</h3>'
      + '<ul><li><b>النقطة</b> مقالة (أو مؤلف). كلما اقتربت زاد المشترك.</li>'
      + '<li><b>اللون</b> مجموعة موضوعية اكتشفها الخوارزم.</li>'
      + '<li><b>اسم المجموعة</b> من <b>الذكاء الاصطناعي</b> اعتمادًا على وسوم العنقود.</li>'
      + '<li>لدى المؤلفين يتدرّج اللون من <b>تجريبي ← نظري</b>.</li></ul>'
      + '<h3>ما هو معروض الآن وإلى أين ينمو</h3>'
      + '<p>حاليًا وجهان: <b>المقالات</b> و<b>المؤلفون</b>. لاحقًا <b>خريطة عامة</b> بعلامات تبويب للقوانين والعلماء والوسوم.</p>'
  })[LANG] || '';

  root.innerHTML =
    '<h1 class="dash-h1">' + T.title + '</h1>' +
    '<div class="an-tabs"><button class="an-tab active" data-t="articles">' + T.articles + '</button>' +
    '<button class="an-tab" data-t="authors">' + T.authors + '</button>' +
    '<button class="an-tab" data-t="fly"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 12l18-8-7 18-2.5-7.5L3 12Z"/></svg> ' + FLY.tab + '</button>' +
    '<button class="an-tab" data-t="heat"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3.5" y="13" width="4" height="7.5" rx="1"/><rect x="10" y="8" width="4" height="12.5" rx="1"/><rect x="16.5" y="4" width="4" height="16.5" rx="1"/></svg> ' + HEAT.tab + '</button>' +
    '<button class="an-tab" data-t="sphere"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="8"/><ellipse cx="12" cy="12" rx="8" ry="3.4"/><path d="M12 4c2.2 2.3 3.4 5 3.4 8s-1.2 5.7-3.4 8"/><path d="M12 4c-2.2 2.3-3.4 5-3.4 8s1.2 5.7 3.4 8"/></svg> ' + V.sphere + '</button>' +
    '<button class="an-tab" data-t="mobius"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4.5 12c0-2.8 3.4-5 7.5-5s7.5 2.2 7.5 5-3.4 5-7.5 5-7.5-2.2-7.5-5Z"/><path d="M6.5 9.5c3 1.6 8 3.4 11 5"/></svg> ' + V.mobius + '</button>' +
    '<button class="an-tab" data-t="matrix"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="4" width="6.5" height="6.5" rx="1"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1"/></svg> ' + V.matrix + '</button>' +
    '<button class="an-tab" data-t="tree"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12h4"/><path d="M8 12V6h5"/><path d="M8 12v6h5"/><circle cx="15" cy="6" r="2"/><circle cx="15" cy="18" r="2"/><circle cx="4" cy="12" r="1.6"/></svg> ' + V2.tree + '</button>' +
    '<button class="an-tab" data-t="spectrum"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 18l3-6 3 9 3-13 3 8 3-4 3 6"/></svg> ' + V2.spectrum + '</button>' +
    '<button class="an-tab" data-t="tension"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12h5"/><path d="M15 12h5"/><path d="M9 8.5 12 12l-3 3.5"/><path d="M15 8.5 12 12l3 3.5"/></svg> ' + V3.tab + '</button></div>' +
    '<p class="an-intro" id="an-intro">' + T.introA + '</p>' +
    '<div class="an-stage" id="an-stage"><canvas id="an-canvas"></canvas><div class="an-hint">' + T.hint + '</div>' +
    '<div class="an-stage-ctl">' +
    '<button class="an-btn" id="an-spin" title="' + CTL.spin + '" aria-pressed="true"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 12a8 8 0 1 1-2.5-5.8"/><path d="M20 4v4h-4"/></svg></button>' +
    '<button class="an-btn" id="an-zin" title="' + CTL.zin + '"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6"/><path d="M15 15l5 5"/><path d="M8 10.5h5"/><path d="M10.5 8v5"/></svg></button>' +
    '<button class="an-btn" id="an-zout" title="' + CTL.zout + '"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6"/><path d="M15 15l5 5"/><path d="M8 10.5h5"/></svg></button>' +
    '<button class="an-btn" id="an-home" title="' + CTL.reset + '"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 11 12 4l8 7"/><path d="M6.5 9.5V19h11V9.5"/></svg></button>' +
    '<button class="an-btn" id="an-fs" title="' + (FLY.fs || 'fullscreen') + '"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 9V5.5A1.5 1.5 0 0 1 5.5 4H9"/><path d="M15 4h3.5A1.5 1.5 0 0 1 20 5.5V9"/><path d="M20 15v3.5a1.5 1.5 0 0 1-1.5 1.5H15"/><path d="M9 20H5.5A1.5 1.5 0 0 1 4 18.5V15"/></svg></button></div>' +
    '<div class="an-speed" id="an-speed"><span>' + (FLY.speed || 'speed') + '</span>' +
    '<input type="range" id="an-speed-r" min="0" max="60" value="18"></div>' +
    '<div class="an-tip" id="an-tip" hidden></div></div>' +
    '<div class="an-legend" id="an-legend"></div>' +
    '<div class="b42-loader" id="an-loading">' + T.loading + '</div>' +
    '<div class="an-about">' + ABOUT + '</div>';

  var canvas = document.getElementById('an-canvas'), ctx = canvas.getContext('2d');
  var tip = document.getElementById('an-tip'), legendEl = document.getElementById('an-legend');
  var state = { data: null, mode: 'articles', yaw: 0.6, pitch: -0.3, zoom: 1, spin: true, hover: -1,
                travel: 0, speed: 0.0011, fyaw: 0, fpitch: 0 };   // fly-режим: продвижение + руль
  var cache = {};

  function sizeCanvas() {
    var stage = document.getElementById('an-stage');
    var fs = stage && stage.classList.contains('an-fs');
    var w = canvas.clientWidth || 640, h = fs ? (window.innerHeight || 700) : 460;
    var dpr = window.devicePixelRatio || 1;
    canvas.width = w * dpr; canvas.height = h * dpr;
    canvas.style.height = h + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    state.W = w; state.H = h;
  }

  function load(mode) {
    state.mode = mode;
    // Авторов немного (у кого ≥4 статей), а разброс плотный — стартуем крупнее, чтобы облако читалось.
    state.zoom = mode === 'authors' ? 1.7 : 1;
    var intro = document.getElementById('an-intro');
    var hintEl = document.querySelector('.an-hint');
    // «Полёт» летит по облаку статей — переиспользуем те же точки; свой intro/hint, без легенды-кластеров.
    // сфера и матрица живут на со-встречаемости тегов, Мёбиус — на облаке статей
    var dataMode = (mode === 'fly' || mode === 'heat' || mode === 'mobius'
                 || mode === 'tree' || mode === 'spectrum') ? 'articles'
                 : ((mode === 'sphere' || mode === 'matrix' || mode === 'tension') ? 'cooc' : mode);
    var INTRO = { tension: V3.intro, tree: V2.treeIntro, spectrum: V2.specIntro,
                  sphere: V.sphereIntro, mobius: V.mobiusIntro, matrix: V.matrixIntro,
                  fly: FLY.intro, heat: HEAT.intro, authors: T.introB, articles: T.introA };
    if (intro) intro.innerHTML = INTRO[mode] || T.introA;
    if (hintEl) hintEl.textContent = HINTS[mode] || (mode === 'fly' ? FLY.hint : (mode === 'heat' ? HEAT.hint : T.hint));
    if (mode === 'fly') { state.travel = 0; state.fyaw = 0; state.fpitch = 0; state.speed = 0.0011; }
    var speedBox = document.getElementById('an-speed');
    if (speedBox) speedBox.style.display = mode === 'fly' ? 'flex' : 'none';
    var sr = document.getElementById('an-speed-r');
    if (sr && mode === 'fly') sr.value = Math.round(state.speed / 0.006 * 60);
    if (cache[dataMode]) { state.data = cache[dataMode]; prep(); return; }
    document.getElementById('an-loading').style.display = '';
    var FILE = { authors: 'authors-map', articles: 'articles-map', cooc: 'tags-cooc' };
    fetch('/data/analytics/' + (FILE[dataMode] || 'articles-map') + '.json')
      .then(function (r) { return r.json(); })
      .then(function (d) { cache[dataMode] = d; state.data = d; prep(); })
      .catch(function () { document.getElementById('an-loading').textContent = '—'; });
  }

  function prep() {
    document.getElementById('an-loading').style.display = 'none';
    // Виды на со-встречаемости (сфера, связи, напряжение) приходят без поля points — там entities.
    // Раньше строка ниже падала на них и молча ломала весь режим.
    if (!state.data || !Array.isArray(state.data.points)) {
      state.raw = state.data;
      var stage = document.getElementById('an-stage');
      if (state.mode === 'tension') {
        buildTension(); legendEl.innerHTML = renderTension();
        if (stage) stage.style.display = 'none';
        return;
      }
      if (stage) stage.style.display = '';
      if (state.mode === 'sphere') { buildSphere(); legendEl.innerHTML = ''; draw(); return; }
      if (state.mode === 'matrix') { legendEl.innerHTML = ''; draw(); return; }
      return;
    }
    // центрируем точки в [-0.5,0.5]
    state.pts = state.data.points.map(function (p) {
      return { x: p.x - 0.5, y: p.y - 0.5, z: (p.z != null ? p.z : 0.5) - 0.5,
               c: p.c, th: p.th, label: p.t || p.id, url: p.url, id: p.id };
    });
    // при большом множестве (все авторы, ~16k) — мельче точки и ниже альфа: важна форма облака, не точка.
    var N = state.pts.length;
    state.ptScale = N > 8000 ? 0.5 : N > 4000 ? 0.7 : 1;
    state.ptAlpha = N > 8000 ? 0.5 : N > 4000 ? 0.7 : 1;
    if (state.mode === 'tension') { buildTension();
      var _tnHtml = renderTension();
      var _tnRead = reading('tension');
      legendEl.innerHTML = _tnHtml + (_tnRead || '');
      document.getElementById('an-stage').style.display = 'none'; return; }
    document.getElementById('an-stage').style.display = '';
    if (state.mode === 'tree') { buildTree(); legendEl.innerHTML = ''; }
    else if (state.mode === 'spectrum') { buildSpectrum(); legendEl.innerHTML = ''; }
    else if (state.mode === 'sphere') { state.raw = state.data; buildSphere(); legendEl.innerHTML = ''; }
    else if (state.mode === 'mobius') { buildMobius(); legendEl.innerHTML = ''; }
    else if (state.mode === 'matrix') { state.raw = state.data; legendEl.innerHTML = ''; }
    else if (state.mode === 'heat') { buildHeat(); legendEl.innerHTML = ''; }
    else if (state.mode === 'fly') { legendEl.innerHTML = ''; }
    else { renderLegend(); }
    draw();
    var rd = reading(state.mode);
    if (rd) legendEl.innerHTML = legendEl.innerHTML + rd;
  }

  function colorOf(p) {
    if (state.mode === 'authors' && p.th != null) {
      // градиент экспериментатор(охра) → теоретик(циан)
      var t = p.th;
      var a = [199, 127, 58], b = [46, 138, 160];
      return 'rgb(' + Math.round(a[0] + (b[0] - a[0]) * t) + ',' + Math.round(a[1] + (b[1] - a[1]) * t) + ',' + Math.round(a[2] + (b[2] - a[2]) * t) + ')';
    }
    return PAL[p.c % PAL.length];
  }

  function project(p) {
    var cy = Math.cos(state.yaw), sy = Math.sin(state.yaw), cx = Math.cos(state.pitch), sx = Math.sin(state.pitch);
    var x = p.x * cy - p.z * sy;
    var z = p.x * sy + p.z * cy;
    var y = p.y * cx - z * sx;
    z = p.y * sx + z * cx;
    var scale = (state.H * 0.7 * state.zoom) / (1.8 + z);  // перспектива
    return { sx: state.W / 2 + x * scale, sy: state.H / 2 + y * scale, depth: z, r: Math.max(1.2, 3.2 * scale / (state.H * 0.7)) };
  }

  // ── Полёт: камера летит вперёд сквозь облако, точки уходят навстречу и рециркулируют (бесконечный
  //    тоннель из наших статей). Руль — небольшие углы fyaw/fpitch (поворот тоннеля), скорость — travel. ──
  var FLY_RANGE = 2.6, FLY_NEAR = 0.16;
  function projectFly(p) {
    var f = 1 - (((p.z + 0.5 + state.travel) % 1) + 1) % 1;  // 0..1, растёт travel → точка приближается
    var Z = f * FLY_RANGE + FLY_NEAR;
    var X = p.x, Y = p.y;
    var cy = Math.cos(state.fyaw), sy = Math.sin(state.fyaw);
    var X2 = X * cy - Z * sy, Z2 = X * sy + Z * cy;
    var cx = Math.cos(state.fpitch), sx = Math.sin(state.fpitch);
    var Y2 = Y * cx - Z2 * sx, Z3 = Y * sx + Z2 * cx;
    if (Z3 < 0.06) return null;                       // за камерой — не рисуем
    var scale = (state.H * 0.62) / Z3;
    return { sx: state.W / 2 + X2 * scale, sy: state.H / 2 + Y2 * scale, depth: Z3, r: Math.max(0.6, 5 / Z3) };
  }
  function drawFly() {
    ctx.clearRect(0, 0, state.W, state.H);
    var proj = [];
    for (var i = 0; i < state.pts.length; i++) {
      var pr = projectFly(state.pts[i]);
      if (!pr) continue;
      if (pr.sx < -40 || pr.sx > state.W + 40 || pr.sy < -40 || pr.sy > state.H + 40) continue;
      pr.i = i; pr.color = colorOf(state.pts[i]); proj.push(pr);
    }
    proj.sort(function (a, b) { return b.depth - a.depth; });   // дальние сначала
    for (var k = 0; k < proj.length; k++) {
      var q = proj[k];
      ctx.globalAlpha = Math.max(0.1, Math.min(1, 1.25 - q.depth / FLY_RANGE));
      ctx.fillStyle = q.color;
      ctx.beginPath(); ctx.arc(q.sx, q.sy, q.i === state.hover ? q.r * 1.8 : q.r, 0, 6.283); ctx.fill();
    }
    ctx.globalAlpha = 1;
    // прицел по центру
    ctx.strokeStyle = 'rgba(140,150,160,.5)'; ctx.lineWidth = 1;
    var cxp = state.W / 2, cyp = state.H / 2;
    ctx.beginPath(); ctx.arc(cxp, cyp, 13, 0, 6.283); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cxp - 20, cyp); ctx.lineTo(cxp - 15, cyp);
    ctx.moveTo(cxp + 15, cyp); ctx.lineTo(cxp + 20, cyp); ctx.stroke();
  }

  // ── Тепловой 3D-ландшафт: тема (кластер) × месяц, высота = число статей ──
  function buildHeat() {
    var months = {}, cells = {}, maxV = 0;
    (state.data.points || []).forEach(function (p) {
      var ym = (p.d || '').slice(0, 7); if (!ym) return;
      months[ym] = 1;
      var k = p.c + '|' + ym;
      cells[k] = (cells[k] || 0) + 1;
      if (cells[k] > maxV) maxV = cells[k];
    });
    var ms = Object.keys(months).sort();
    var cs = Object.keys(state.data.clusters || {}).map(Number).sort(function (a, b) { return a - b; });
    state.heat = { ms: ms, cs: cs, cells: cells, max: maxV || 1 };
    state.zoom = 1;
  }
  function drawHeat() {
    var h = state.heat; if (!h || !h.ms.length) return;
    ctx.clearRect(0, 0, state.W, state.H);
    var nx = h.ms.length, nz = h.cs.length;
    var bars = [];
    for (var i = 0; i < nx; i++) {
      for (var j = 0; j < nz; j++) {
        var v = h.cells[h.cs[j] + '|' + h.ms[i]] || 0;
        if (!v) continue;
        var fx = (i / Math.max(1, nx - 1)) - 0.5, fz = (j / Math.max(1, nz - 1)) - 0.5;
        var hh = (v / h.max) * 0.55;
        var base = project({ x: fx, y: 0.28, z: fz });
        var top = project({ x: fx, y: 0.28 - hh, z: fz });
        bars.push({ b: base, t: top, v: v, c: h.cs[j], depth: base.depth, w: Math.max(2, 26 / Math.max(nx, 8) * base.r * 4) });
      }
    }
    bars.sort(function (a, b) { return b.depth - a.depth; });
    bars.forEach(function (q) {
      var col = PAL[q.c % PAL.length];
      var inten = 0.35 + 0.65 * (q.v / h.max);
      ctx.globalAlpha = Math.max(0.25, Math.min(1, inten));
      ctx.strokeStyle = col; ctx.lineWidth = Math.max(2, q.w);
      ctx.beginPath(); ctx.moveTo(q.b.sx, q.b.sy); ctx.lineTo(q.t.sx, q.t.sy); ctx.stroke();
      ctx.fillStyle = col;
      ctx.beginPath(); ctx.arc(q.t.sx, q.t.sy, Math.max(1.5, q.w * 0.55), 0, 6.283); ctx.fill();
    });
    ctx.globalAlpha = 1;
  }


  // ── Сфера знания: понятия/законы/учёные на замкнутой поверхности ──────────────────────────
  // Раскладка Фибоначчи даёт равномерное покрытие, а угол закреплён за кластером — так близкое
  // по смыслу садится рядом и на глобусе проступают «материки» (владелец: «замкнутое множество»).
  function buildSphere() {
    var ents = (state.raw && state.raw.entities) || [];
    var n = ents.length || 1;
    var pts = ents.map(function (e, i) {
      var y = 1 - (i / Math.max(1, n - 1)) * 2;
      var r = Math.sqrt(Math.max(0, 1 - y * y));
      var golden = Math.PI * (3 - Math.sqrt(5));
      var th = golden * i + (e.c || 0) * 0.7;      // сдвиг по кластеру — группируем родственное
      return { x: Math.cos(th) * r * 0.5, y: y * 0.5, z: Math.sin(th) * r * 0.5,
               c: e.c || 0, label: niceLabel(e.id), id: e.id, w: e.n || 1 };
    });
    state.pts = pts;
    state.ptScale = 1; state.ptAlpha = 1; state.zoom = 1.15;
  }

  // ── Лист Мёбиуса: у ленты одна сторона — пройдя круг, возвращаешься перевёрнутым ───────────
  function buildMobius() {
    var src = (state.data && state.data.points) || [];
    var n = src.length || 1;
    var pts = src.map(function (p, i) {
      var u = (i / n) * Math.PI * 2;                       // вдоль ленты — по порядку (время)
      var v = ((p.c % 7) / 6 - 0.5) * 0.34;                // поперёк — по кластеру
      var R = 0.42;
      var cu = Math.cos(u), su = Math.sin(u), h = Math.cos(u / 2), s2 = Math.sin(u / 2);
      return { x: (R + v * h) * cu, y: v * s2, z: (R + v * h) * su,
               c: p.c, label: p.t || p.id, url: p.url, id: p.id };
    });
    state.pts = pts;
    state.ptScale = 0.8; state.ptAlpha = 0.85; state.zoom = 1.25;
  }

  // ── Тепловая матрица связей: понятие × понятие ────────────────────────────────────────────
  function drawMatrix() {
    var ents = (state.raw && state.raw.entities) || [];
    if (!ents.length) return;
    var m = Math.min(ents.length, 60);
    var list = ents.slice(0, m);
    var idx = {}; list.forEach(function (e, i) { idx[e.id] = i; });
    var W = state.W, H = state.H, pad = 8;
    var cell = Math.max(3, Math.floor((Math.min(W, H) - pad * 2) / m));
    var ox = (W - cell * m) / 2, oy = (H - cell * m) / 2;
    ctx.clearRect(0, 0, W, H);
    list.forEach(function (e, i) {
      (e.nb || []).forEach(function (nb) {
        var j = idx[nb[0]];
        if (j == null) return;
        var v = Math.min(1, nb[1] * 3);
        ctx.fillStyle = PAL[e.c % PAL.length];
        ctx.globalAlpha = 0.12 + v * 0.88;
        ctx.fillRect(ox + j * cell, oy + i * cell, cell - 1, cell - 1);
        ctx.fillRect(ox + i * cell, oy + j * cell, cell - 1, cell - 1);
      });
      ctx.globalAlpha = 0.5;
      ctx.fillStyle = PAL[e.c % PAL.length];
      ctx.fillRect(ox + i * cell, oy + i * cell, cell - 1, cell - 1);   // диагональ
    });
    ctx.globalAlpha = 1;
    state.matrix = { list: list, cell: cell, ox: ox, oy: oy, m: m };
  }


  // ── Каркасы форм: без них все виды выглядят одинаковой россыпью точек ────────────────────
  function strokeWire(pts3, close, alpha) {
    if (pts3.length < 2) return;
    ctx.globalAlpha = alpha;
    ctx.beginPath();
    for (var i = 0; i < pts3.length; i++) {
      var pr = project(pts3[i]);
      if (i === 0) ctx.moveTo(pr.sx, pr.sy); else ctx.lineTo(pr.sx, pr.sy);
    }
    if (close) ctx.closePath();
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  function drawGlobeWire() {
    ctx.strokeStyle = 'rgba(140,150,160,.34)';
    ctx.lineWidth = 1;
    var R = 0.5, i, j, ring;
    for (j = -2; j <= 2; j++) {                       // параллели
      var y = j * 0.19, r = Math.sqrt(Math.max(0.001, R * R - y * y));
      ring = [];
      for (i = 0; i <= 48; i++) {
        var a = i / 48 * Math.PI * 2;
        ring.push({ x: Math.cos(a) * r, y: y, z: Math.sin(a) * r });
      }
      strokeWire(ring, true, j === 0 ? 0.5 : 0.28);
    }
    for (j = 0; j < 6; j++) {                          // меридианы
      var ph = j / 6 * Math.PI;
      ring = [];
      for (i = 0; i <= 48; i++) {
        var b = i / 48 * Math.PI * 2;
        ring.push({ x: Math.cos(b) * R * Math.cos(ph), y: Math.sin(b) * R, z: Math.cos(b) * R * Math.sin(ph) });
      }
      strokeWire(ring, true, 0.22);
    }
  }

  function drawMobiusWire() {
    // сама лента: два края + перемычки, чтобы читалась поверхность с одной стороной
    ctx.strokeStyle = 'rgba(140,150,160,.4)';
    ctx.lineWidth = 1;
    var R = 0.42, w = 0.17, edgeA = [], edgeB = [], i, u, h, s2, cu, su;
    for (i = 0; i <= 160; i++) {
      u = i / 160 * Math.PI * 2;
      cu = Math.cos(u); su = Math.sin(u); h = Math.cos(u / 2); s2 = Math.sin(u / 2);
      edgeA.push({ x: (R + w * h) * cu, y: w * s2, z: (R + w * h) * su });
      edgeB.push({ x: (R - w * h) * cu, y: -w * s2, z: (R - w * h) * su });
    }
    strokeWire(edgeA, false, 0.55);
    strokeWire(edgeB, false, 0.55);
    ctx.globalAlpha = 0.2;
    for (i = 0; i < edgeA.length; i += 8) {
      var a = project(edgeA[i]), b = project(edgeB[i]);
      ctx.beginPath(); ctx.moveTo(a.sx, a.sy); ctx.lineTo(b.sx, b.sy); ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }

  // ── Дерево знаний: упорядоченная иерархия, а не граф (владелец 2026-07-27) ───────────────
  // Область науки → раздел → понятия. Растёт слева направо, ветви подписаны.
  function buildTree() {
    // Дерево должно ветвиться, а не расходиться веером из одной точки. Уровни настоящие,
    // из данных: ствол → тема (кластер) → год → статьи. Год — не украшение: по нему видно,
    // какая тема выросла недавно, а какая держится ровно.
    var src = (state.data && state.data.points) || [];
    var groups = {};
    src.forEach(function (p) {
      var c = String(p.c);
      (groups[c] = groups[c] || []).push(p);
    });
    state.tree = Object.keys(groups)
      .sort(function (a, b) { return groups[b].length - groups[a].length; })
      .slice(0, 12)
      .map(function (c) {
        var items = groups[c];
        var byYear = {};
        items.forEach(function (p) {
          var y = String(p.d || '').slice(0, 4) || '—';
          (byYear[y] = byYear[y] || []).push(p);
        });
        var twigs = Object.keys(byYear).sort().map(function (y) {
          return { year: y, items: byYear[y] };
        });
        return { c: +c, items: items, twigs: twigs };
      });
  }

  function drawTree() {
    var tr = state.tree || [];
    if (!tr.length) return;
    ctx.clearRect(0, 0, state.W, state.H);
    var titles = (state.data && state.data.titles) || {};
    var css = getComputedStyle(document.body);
    var ink = css.getPropertyValue('--text') || '#333';
    var mono = css.getPropertyValue('--mono') || 'monospace';

    // Сколько вертикали нужно: у каждой темы столько строк, сколько у неё лет.
    var rows = tr.reduce(function (s, b) { return s + b.twigs.length; }, 0);
    var padT = 22, padB = 14;
    var rowH = Math.max(11, Math.min(26, (state.H - padT - padB) / Math.max(1, rows)));
    var xTrunk = 16, xBranch = Math.max(120, state.W * 0.30), xTwig = xBranch + 54;
    var xLeaf = xTwig + 34, xEnd = state.W - 12;

    ctx.textBaseline = 'middle';
    ctx.lineCap = 'round';

    // ствол
    var yTop = padT, yBot = state.H - padB;
    ctx.strokeStyle = ink; ctx.globalAlpha = 0.22; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(xTrunk, yTop); ctx.lineTo(xTrunk, yBot); ctx.stroke();

    var y = padT;
    tr.forEach(function (br) {
      var col = PAL[br.c % PAL.length];
      var yFirst = y + rowH / 2;
      var yLast = y + (br.twigs.length - 0.5) * rowH;
      var yMid = (yFirst + yLast) / 2;

      // ствол → ветвь темы
      ctx.strokeStyle = col; ctx.globalAlpha = 0.55; ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(xTrunk, yMid);
      ctx.bezierCurveTo(xTrunk + 46, yMid, xBranch - 46, yMid, xBranch, yMid);
      ctx.stroke();

      // вертикаль ветви, от которой отходят годы
      if (br.twigs.length > 1) {
        ctx.globalAlpha = 0.35; ctx.lineWidth = 1.4;
        ctx.beginPath(); ctx.moveTo(xBranch, yFirst); ctx.lineTo(xBranch, yLast); ctx.stroke();
      }

      // подпись темы — человеческое имя от ИИ
      var lt = titles[br.c] && (titles[br.c][LANG] || titles[br.c].en);
      var label = (lt && lt.title) || ('#' + br.c);
      ctx.globalAlpha = 1; ctx.fillStyle = ink;
      ctx.font = '11.5px ' + mono; ctx.textAlign = 'right';
      ctx.fillText(label.slice(0, 30), xBranch - 8, yMid - 6);
      ctx.globalAlpha = 0.5;
      ctx.font = '10px ' + mono;
      ctx.fillText(br.items.length + '', xBranch - 8, yMid + 7);

      br.twigs.forEach(function (tw) {
        var ty = y + rowH / 2;
        // ветвь → год
        ctx.strokeStyle = col; ctx.globalAlpha = 0.4; ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.moveTo(xBranch, ty);
        ctx.bezierCurveTo(xBranch + 20, ty, xTwig - 20, ty, xTwig, ty);
        ctx.stroke();

        // подпись года
        ctx.globalAlpha = 0.65; ctx.fillStyle = ink;
        ctx.font = '9.5px ' + mono; ctx.textAlign = 'left';
        ctx.fillText(tw.year, xTwig + 3, ty);

        // листья — статьи этого года
        var maxN = Math.max(1, Math.floor((xEnd - xLeaf) / 6));
        var n = Math.min(tw.items.length, maxN);
        for (var k = 0; k < n; k++) {
          ctx.fillStyle = col;
          ctx.globalAlpha = 0.3 + 0.55 * (k / Math.max(1, n));
          ctx.beginPath(); ctx.arc(xLeaf + k * 6, ty, 2, 0, 6.283); ctx.fill();
        }
        if (tw.items.length > maxN) {
          ctx.globalAlpha = 0.5; ctx.fillStyle = ink; ctx.font = '9px ' + mono;
          ctx.fillText('+' + (tw.items.length - maxN), xLeaf + n * 6 + 4, ty);
        }
        y += rowH;
      });
    });
    ctx.globalAlpha = 1; ctx.textAlign = 'left';
  }

  // ── Статистика: спектр публикационной активности (Фурье) и периодограмма Ломба-Скаргла ──
  // Ряд неравномерный (в какие-то дни статей нет), поэтому Ломб-Скаргл честнее обычного Фурье —
  // он для неравномерных выборок и как раз пришёл из астрономии.
  function buildSpectrum() {
    var src = (state.data && state.data.points) || [];
    var byDay = {};
    src.forEach(function (p) { if (p.d) byDay[p.d] = (byDay[p.d] || 0) + 1; });
    var days = Object.keys(byDay).sort();
    if (days.length < 8) { state.spec = null; return; }
    var t0 = new Date(days[0]).getTime();
    var ts = days.map(function (d) { return (new Date(d).getTime() - t0) / 86400000; });
    var ys = days.map(function (d) { return byDay[d]; });
    var mean = ys.reduce(function (a, b) { return a + b; }, 0) / ys.length;
    var varr = ys.reduce(function (a, b) { return a + (b - mean) * (b - mean); }, 0) / Math.max(1, ys.length - 1);

    var out = [];
    for (var per = 2; per <= 200; per += 1) {          // период в днях
      var w = 2 * Math.PI / per;
      var s2 = 0, c2 = 0, k;
      for (k = 0; k < ts.length; k++) { s2 += Math.sin(2 * w * ts[k]); c2 += Math.cos(2 * w * ts[k]); }
      var tau = Math.atan2(s2, c2) / (2 * w);
      var cs = 0, ss = 0, cc = 0, sss = 0;
      for (k = 0; k < ts.length; k++) {
        var dt = ts[k] - tau, C = Math.cos(w * dt), S = Math.sin(w * dt), yv = ys[k] - mean;
        cs += yv * C; ss += yv * S; cc += C * C; sss += S * S;
      }
      var power = 0.5 * ((cc ? cs * cs / cc : 0) + (sss ? ss * ss / sss : 0)) / Math.max(1e-9, varr);
      out.push({ per: per, p: power });
    }
    var mx = out.reduce(function (a, b) { return b.p > a ? b.p : a; }, 0.0001);
    out.forEach(function (o) { o.p /= mx; });
    state.spec = { pts: out, days: days.length, total: ys.reduce(function (a, b) { return a + b; }, 0) };
  }

  // Подписи осей спектра — по ним читается, что вообще отложено на графике.
  var SPEC_AX = {
    ru: { x: 'период повторения, дни', y: 'сила ритма', days: 'дн' },
    en: { x: 'repeat period, days', y: 'rhythm strength', days: 'd' },
    es: { x: 'período de repetición, días', y: 'fuerza del ritmo', days: 'd' },
    ar: { x: 'دورة التكرار، أيام', y: 'قوة الإيقاع', days: 'ي' }
  };

  function drawSpectrum() {
    var sp = state.spec;
    ctx.clearRect(0, 0, state.W, state.H);
    if (!sp || !sp.pts || !sp.pts.length) return;
    var css = getComputedStyle(document.body);
    var mono = css.getPropertyValue('--mono') || 'monospace';
    var ink = css.getPropertyValue('--text') || '#333';
    var soft = css.getPropertyValue('--soft') || '#888';
    var padL = 52, padB = 40, padT = 26, padR = 16;
    var W = state.W - padL - padR, H = state.H - padT - padB;
    var n = sp.pts.length;
    var xAt = function (i) { return padL + (i / Math.max(1, n - 1)) * W; };
    var yAt = function (v) { return padT + H - v * H; };

    // Сетка — без неё по графику невозможно ничего прочесть: не видно ни уровня мощности,
    // ни того, какому периоду отвечает пик (замечание юзера 2026-07-28).
    ctx.font = '10px ' + mono;
    ctx.textBaseline = 'middle';
    ctx.strokeStyle = 'rgba(140,150,160,.16)'; ctx.lineWidth = 1;
    ctx.fillStyle = soft; ctx.textAlign = 'right';
    for (var g = 0; g <= 4; g++) {
      var v = g / 4, gy = yAt(v);
      ctx.beginPath(); ctx.moveTo(padL, gy); ctx.lineTo(padL + W, gy); ctx.stroke();
      ctx.fillText(v.toFixed(2), padL - 7, gy);
    }
    // вертикальная сетка с подписями периодов
    ctx.textAlign = 'center'; ctx.textBaseline = 'top';
    var ticks = 6;
    for (var s = 0; s <= ticks; s++) {
      var i = Math.round((s / ticks) * (n - 1));
      var gx = xAt(i);
      ctx.strokeStyle = 'rgba(140,150,160,.12)';
      ctx.beginPath(); ctx.moveTo(gx, padT); ctx.lineTo(gx, padT + H); ctx.stroke();
      ctx.fillStyle = soft;
      ctx.fillText(String(sp.pts[i].per), gx, padT + H + 6);
    }

    // оси
    ctx.strokeStyle = 'rgba(140,150,160,.5)'; ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padL, padT); ctx.lineTo(padL, padT + H); ctx.lineTo(padL + W, padT + H);
    ctx.stroke();

    // подписи осей
    var L = (SPEC_AX && SPEC_AX[LANG]) || SPEC_AX.ru;
    ctx.fillStyle = ink; ctx.font = '10.5px ' + mono;
    ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
    ctx.fillText(L.x, padL + W / 2, state.H - 8);
    ctx.save();
    ctx.translate(13, padT + H / 2); ctx.rotate(-Math.PI / 2);
    ctx.textAlign = 'center'; ctx.fillText(L.y, 0, 0);
    ctx.restore();

    // заливка под кривой — так виден сам «рельеф», а не только линия
    var cyan = css.getPropertyValue('--cyan') || '#2E8AA0';
    ctx.beginPath();
    ctx.moveTo(xAt(0), padT + H);
    sp.pts.forEach(function (o, i) { ctx.lineTo(xAt(i), yAt(o.p)); });
    ctx.lineTo(xAt(n - 1), padT + H); ctx.closePath();
    ctx.globalAlpha = 0.12; ctx.fillStyle = cyan; ctx.fill(); ctx.globalAlpha = 1;

    // кривая мощности
    ctx.strokeStyle = cyan; ctx.lineWidth = 1.7; ctx.beginPath();
    sp.pts.forEach(function (o, i) {
      var x = xAt(i), y = yAt(o.p);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Пики: подсвечиваем кружком с ореолом и ведём вертикаль к оси — сразу видно период.
    var ochre = css.getPropertyValue('--ochre') || '#C77F3A';
    var top = sp.pts.slice().sort(function (a, b) { return b.p - a.p; }).slice(0, 3);
    ctx.font = '11px ' + mono;
    top.forEach(function (o) {
      var i = sp.pts.indexOf(o), x = xAt(i), y = yAt(o.p);
      ctx.strokeStyle = ochre; ctx.globalAlpha = 0.35; ctx.lineWidth = 1;
      ctx.setLineDash([3, 3]);
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x, padT + H); ctx.stroke();
      ctx.setLineDash([]);
      ctx.globalAlpha = 0.18; ctx.fillStyle = ochre;
      ctx.beginPath(); ctx.arc(x, y, 7, 0, 6.283); ctx.fill();
      ctx.globalAlpha = 1;
      ctx.beginPath(); ctx.arc(x, y, 3.4, 0, 6.283); ctx.fill();
      ctx.fillStyle = ink; ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
      ctx.fillText(o.per + ' ' + L.days, Math.min(x + 8, state.W - 60), Math.max(14, y - 8));
      ctx.fillStyle = ochre;
    });
    ctx.globalAlpha = 1; ctx.textAlign = 'left';
  }

  // ── Напряжение: мосты между областями и разрывы там, где связь напрашивается ─────────────
  function buildTension() {
    var ents = ((state.data && state.data.entities) || []);
    var by = {};
    ents.forEach(function (e) { by[e.id] = e; });

    var seen = {}, bridges = [];
    ents.forEach(function (e) {
      (e.nb || []).forEach(function (nb) {
        var o = by[nb[0]];
        if (!o || o.c === e.c) return;                   // мост — только между РАЗНЫМИ группами
        var key = [e.id, o.id].sort().join('|');
        if (seen[key]) return;
        seen[key] = 1;
        bridges.push({ a: e, b: o, w: nb[1] });
      });
    });
    bridges.sort(function (x, y) { return y.w - x.w; });

    // разрывы: крупные группы, между которыми НЕТ ни одного моста
    var size = {}, linked = {};
    ents.forEach(function (e) { size[e.c] = (size[e.c] || 0) + (e.n || 1); });
    bridges.forEach(function (b) { linked[[b.a.c, b.b.c].sort().join('|')] = 1; });
    var cs = Object.keys(size).map(Number).sort(function (a, b) { return size[b] - size[a]; }).slice(0, 6);
    var gaps = [];
    for (var i = 0; i < cs.length; i++) {
      for (var j = i + 1; j < cs.length; j++) {
        if (!linked[[cs[i], cs[j]].sort().join('|')]) {
          gaps.push({ a: cs[i], b: cs[j], w: size[cs[i]] + size[cs[j]] });
        }
      }
    }
    gaps.sort(function (x, y) { return y.w - x.w; });
    state.tension = { bridges: bridges.slice(0, 12), gaps: gaps.slice(0, 5), by: by };
  }

  function renderTension() {
    var d = state.tension;
    if (!d) return '';
    var titles = (cache.articles && cache.articles.titles) || {};
    function clusterName(c) {
      var lt = titles[c] && (titles[c][LANG] || titles[c].en);
      return (lt && lt.title) || ('#' + c);
    }
    var br = d.bridges.map(function (b) {
      var pct = Math.round(b.w * 100);
      return '<div class="tn-row"><span class="tn-bar" style="width:' + Math.max(8, pct * 2) + 'px;background:'
        + PAL[b.a.c % PAL.length] + '"></span>'
        + '<span class="tn-n">' + niceLabel(b.a.id) + '</span>'
        + '<span class="tn-x">⟷</span>'
        + '<span class="tn-n">' + niceLabel(b.b.id) + '</span>'
        + '<span class="tn-w">' + pct + '</span></div>';
    }).join('');
    var gp = d.gaps.map(function (g) {
      return '<div class="tn-gap"><b>' + clusterName(g.a) + '</b><span class="tn-x">✕</span><b>'
        + clusterName(g.b) + '</b><span class="tn-w">' + g.w + '</span></div>';
    }).join('');
    return '<div class="tn-wrap"><div class="tn-col"><div class="tn-h">' + V3.bridges + '</div>' + br + '</div>'
      + '<div class="tn-col"><div class="tn-h">' + V3.gaps + '</div>' + gp + '</div></div>';
  }

  function draw() {
    if (!state.pts) return;
    if (state.mode === 'matrix') { drawMatrix(); return; }
    if (state.mode === 'tree') { drawTree(); return; }
    if (state.mode === 'spectrum') { drawSpectrum(); return; }
    if (state.mode === 'heat') { drawHeat(); return; }
    if (state.mode === 'fly') { drawFly(); return; }
    ctx.clearRect(0, 0, state.W, state.H);
    if (state.mode === 'sphere') drawGlobeWire();
    if (state.mode === 'mobius') drawMobiusWire();
    var proj = state.pts.map(function (p, i) { var pr = project(p); pr.i = i; pr.color = colorOf(p); return pr; });
    proj.sort(function (a, b) { return a.depth - b.depth; }); // дальние сначала
    for (var k = 0; k < proj.length; k++) {
      var pr = proj[k];
      var fade = 0.35 + 0.65 * (1 - (pr.depth + 0.5));
      ctx.globalAlpha = Math.max(0.12, Math.min(1, fade * (state.ptAlpha || 1)));
      ctx.fillStyle = pr.color;
      ctx.beginPath();
      ctx.arc(pr.sx, pr.sy, pr.i === state.hover ? pr.r * 2.4 : pr.r * (state.ptScale || 1), 0, 6.283);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  // Метки кластеров приходят как сырые id (теги snake_case у статей; коды разделов у авторов) —
  // переводим в человекочитаемые локализованные имена (юзер 2026-07-24: «на русской версии теги
  // по-английски — называй по-нашему»). tagsLoc/ARXIV_CAT_NAMES грузит search.js.
  function niceLabel(raw) {
    if (state.mode === 'authors') {
      // коды arXiv: подкатегория после точки бывает ЗАГЛАВНОЙ (astro-ph.CO) или строчной
      // (cond-mat.stat-mech) — пробуем варианты, берём первый, что есть в справочнике разделов.
      var m = window.ARXIV_CAT_NAMES || {};
      var dot = raw.replace(/_/g, '.'), up = dot.replace(/\.([a-z-]+)$/, function (_, s) { return '.' + s.toUpperCase(); });
      return m[dot] || m[up] || m[raw] || dot;
    }
    var t = window.tagsLoc && tagsLoc[raw];
    return (t && t.name) || raw.replace(/_/g, ' ');
  }
  function renderLegend() {
    var cl = state.data.clusters || {};
    var titles = state.data.titles || null;   // человеческие названия от LLM-трактовщика (если посчитаны)
    var extra = state.mode === 'authors' ? '<div class="an-axis">' + T.theoryExp + '</div>' : '';
    // Кластеры — КАРТОЧКАМИ (юзер 2026-07-25): цветная полоса, название-заголовок, описание ниже.
    var items = Object.keys(cl).map(function (c) {
      var col = state.mode === 'authors' ? PAL[c % PAL.length] : PAL[c % PAL.length];
      var lt = titles && titles[c] ? titles[c][LANG] || titles[c].en : null;
      var title = lt ? lt.title : (cl[c] || []).map(niceLabel).slice(0, 3).join(' · ');
      var desc = lt && lt.desc ? '<div class="an-card-d">' + lt.desc + '</div>' : '';
      return '<div class="an-card" style="--cc:' + col + '"><div class="an-card-t">' + title + '</div>' + desc + '</div>';
    }).join('');
    legendEl.innerHTML = '<div class="an-lg-h">' + T.clusters + ' · <b>' + state.data.n + '</b> ' + T.n + '</div>' +
      '<div class="an-cards">' + items + '</div>' + extra;
    // search.js грузит tagsLoc асинхронно — если легенда отрисовалась раньше и нет LLM-имён,
    // дорисуем её один раз, когда словарь тегов доедет (иначе на RU останутся англ. id).
    if (!titles && state.mode !== 'authors' && !(window.tagsLoc && Object.keys(window.tagsLoc).length) && !renderLegend._retry) {
      renderLegend._retry = setInterval(function () {
        if (window.tagsLoc && Object.keys(window.tagsLoc).length) {
          clearInterval(renderLegend._retry); renderLegend._retry = 0; renderLegend();
        }
      }, 300);
    }
  }

  // взаимодействие

  // Управление видом. Автовращение выключается перетаскиванием (так удобнее целиться),
  // поэтому нужна явная кнопка вернуть его — иначе сцена остаётся неподвижной навсегда.
  function setSpin(on) {
    state.spin = on;
    var b = document.getElementById('an-spin');
    if (b) { b.classList.toggle('active', on); b.setAttribute('aria-pressed', on ? 'true' : 'false'); }
  }
  var spinBtn = document.getElementById('an-spin');
  if (spinBtn) spinBtn.addEventListener('click', function () { setSpin(!state.spin); });
  var zinBtn = document.getElementById('an-zin');
  if (zinBtn) zinBtn.addEventListener('click', function () {
    state.zoom = Math.min(4, state.zoom * 1.25); draw();
  });
  var zoutBtn = document.getElementById('an-zout');
  if (zoutBtn) zoutBtn.addEventListener('click', function () {
    state.zoom = Math.max(0.4, state.zoom / 1.25); draw();
  });
  var homeBtn = document.getElementById('an-home');
  if (homeBtn) homeBtn.addEventListener('click', function () {
    state.yaw = 0.6; state.pitch = -0.3;
    state.zoom = (state.mode === 'authors') ? 1.7 : 1;
    setSpin(true); draw();
  });

  var drag = null;
  canvas.addEventListener('mousedown', function (e) { drag = { x: e.clientX, y: e.clientY }; setSpin(false); });
  window.addEventListener('mouseup', function () { drag = null; });
  window.addEventListener('mousemove', function (e) {
    if (drag) {
      if (state.mode === 'fly') {
        // руль: небольшой поворот тоннеля, с автовозвратом (см. цикл). Инверсия по X — как штурвал.
        state.fyaw = Math.max(-0.6, Math.min(0.6, state.fyaw - (e.clientX - drag.x) * 0.004));
        state.fpitch = Math.max(-0.5, Math.min(0.5, state.fpitch + (e.clientY - drag.y) * 0.004));
        drag = { x: e.clientX, y: e.clientY }; return;
      }
      state.yaw += (e.clientX - drag.x) * 0.01; state.pitch += (e.clientY - drag.y) * 0.01;
      state.pitch = Math.max(-1.5, Math.min(1.5, state.pitch));
      drag = { x: e.clientX, y: e.clientY }; draw(); return;
    }
    // hover: ближайшая точка к курсору (в fly проецируем через projectFly)
    var rect = canvas.getBoundingClientRect(), mx = e.clientX - rect.left, my = e.clientY - rect.top;
    if (mx < 0 || my < 0 || mx > state.W || my > state.H) { if (state.hover !== -1) { state.hover = -1; tip.hidden = true; } return; }
    var best = -1, bd = state.mode === 'fly' ? 18 : 12, fly = state.mode === 'fly';
    for (var i = 0; i < state.pts.length; i++) {
      var pr = fly ? projectFly(state.pts[i]) : project(state.pts[i]);
      if (!pr) continue;
      var d = Math.hypot(pr.sx - mx, pr.sy - my); if (d < bd) { bd = d; best = i; }
    }
    if (best !== state.hover || fly) {
      state.hover = best;
      if (best >= 0) { tip.hidden = false; tip.textContent = state.pts[best].label; tip.style.left = (mx + 12) + 'px'; tip.style.top = (my + 12) + 'px'; }
      else tip.hidden = true;
      if (!fly) draw();
    }
  });
  canvas.addEventListener('click', function () {
    if (state.hover >= 0 && state.pts[state.hover].url) window.location = state.pts[state.hover].url;
  });
  canvas.addEventListener('wheel', function (e) {
    e.preventDefault();
    if (state.mode === 'fly') { state.speed = Math.max(0, Math.min(0.006, state.speed + (e.deltaY < 0 ? 0.0006 : -0.0006))); return; }
    state.zoom = Math.max(0.4, Math.min(4, state.zoom * (e.deltaY < 0 ? 1.1 : 0.9))); draw();
  }, { passive: false });

  // Тач: рулить/вращать пальцем (мобилка, молодёжь — «поиграть»).
  canvas.addEventListener('touchstart', function (e) { var t = e.touches[0]; drag = { x: t.clientX, y: t.clientY }; state.spin = false; }, { passive: true });
  canvas.addEventListener('touchmove', function (e) {
    if (!drag) return; var t = e.touches[0];
    if (state.mode === 'fly') {
      state.fyaw = Math.max(-0.6, Math.min(0.6, state.fyaw - (t.clientX - drag.x) * 0.004));
      state.fpitch = Math.max(-0.5, Math.min(0.5, state.fpitch + (t.clientY - drag.y) * 0.004));
    } else {
      state.yaw += (t.clientX - drag.x) * 0.01;
      state.pitch = Math.max(-1.5, Math.min(1.5, state.pitch + (t.clientY - drag.y) * 0.01)); draw();
    }
    drag = { x: t.clientX, y: t.clientY };
  }, { passive: true });
  canvas.addEventListener('touchend', function () { drag = null; }, { passive: true });

  // Фуллскрин сцены (юзер 2026-07-25: «возможность развернуть на весь экран»)
  var fsBtn = document.getElementById('an-fs'), stageEl = document.getElementById('an-stage');
  if (fsBtn && stageEl) {
    fsBtn.addEventListener('click', function () {
      stageEl.classList.toggle('an-fs');
      sizeCanvas(); draw();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && stageEl.classList.contains('an-fs')) { stageEl.classList.remove('an-fs'); sizeCanvas(); draw(); }
    });
  }
  // Ползунок скорости полёта
  var speedR = document.getElementById('an-speed-r');
  if (speedR) speedR.addEventListener('input', function () { state.speed = (+speedR.value) / 60 * 0.006; });

  document.querySelectorAll('.an-tab').forEach(function (b) {
    b.addEventListener('click', function () {
      document.querySelectorAll('.an-tab').forEach(function (x) { x.classList.remove('active'); });
      b.classList.add('active'); state.spin = true; load(b.dataset.t);
    });
  });

  // Анимация: в обычном режиме — медленное авто-вращение; в полёте — постоянное движение вперёд
  // (travel) + плавный автовозврат руля к центру, чтобы «выравнивалось» само.
  (function loop() {
    if (state.pts) {
      if (state.mode === 'fly') {
        state.travel += state.speed;
        state.fyaw *= 0.96; state.fpitch *= 0.96;   // автоцентровка штурвала
        draw();
      } else if (state.spin) {
        state.yaw += 0.0025; draw();
      }
    }
    requestAnimationFrame(loop);
  })();

  window.addEventListener('resize', function () { sizeCanvas(); draw(); });
  sizeCanvas();
  load('articles');
})();
