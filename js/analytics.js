// Аналитика-дашборд «карта облака»: 3D-россыпь статей/авторов, которую можно покрутить мышью.
// Self-contained canvas (без внешних либ — строгий CSP). Данные: data/analytics/*.json (офлайн-
// препросчёт analytics_build.py, БЕЗ DeepSeek). Юзер 2026-07-24: показать группировки, 3D, «вау».
(function () {
  var root = document.getElementById('analytics');
  // LANG объявлен ДО первого словаря. Аудит 16 августа, находка 5: CTL индексировался
  // [LANG] выше объявления var LANG — хойстинг поднимает объявление, но не значение,
  // индекс был undefined, и кнопки управления шли по-английски на всех языках.
  var LANG = window.lang || 'en';
  // Мини-панель вида: без неё сцена «замирала» — перетаскивание выключает автовращение,
  // а включить обратно было нечем (замечание юзера 2026-07-28).
  var CTL = ({
    ru: { spin: 'вращение: стоп / пуск', zin: 'приблизить', zout: 'отдалить', reset: 'вернуть вид',
          shapes: 'формы вместо одного цвета — для тех, кто различает цвета иначе' },
    en: { spin: 'auto-rotate: stop / start', zin: 'zoom in', zout: 'zoom out', reset: 'reset view',
          shapes: 'shapes as well as colour — for colour-blind readers' },
    es: { spin: 'rotación: parar / iniciar', zin: 'acercar', zout: 'alejar', reset: 'restablecer vista',
          shapes: 'formas además del color — para daltónicos' },
    fr: { spin: 'rotation : stop / marche', zin: 'zoomer', zout: 'reculer', reset: 'vue initiale',
          shapes: 'des formes en plus de la couleur — pour les daltoniens' },
    ar: { spin: 'الدوران: إيقاف / تشغيل', zin: 'تقريب', zout: 'إبعاد', reset: 'إعادة العرض',
          shapes: 'أشكال إلى جانب اللون — لمن يميّز الألوان بشكل مختلف' },
    zh: { spin: '旋转：开 / 关', zin: '放大', zout: '缩小', reset: '重置视图',
          shapes: '除颜色外还用形状 —— 为色觉不同的读者' }
  })[LANG] || { shapes: 'shapes as well as colour', spin: 'auto-rotate', zin: 'zoom in', zout: 'zoom out', reset: 'reset view' };


  if (!root) return;
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
    fr: { title: 'Carte du projet', articles: 'Articles', authors: 'Auteurs', loading: 'Construction de la carte…',
          hint: 'glisser pour tourner · molette pour zoomer · clic sur un point', clusters: 'Groupes thématiques', n: 'points',
          theoryExp: 'Couleur du point : expérimentateur (ocre) → théoricien (cyan)',
          introA: 'Chaque point est un <b>article</b>. Plus deux points sont proches, plus les articles partagent de thèmes. La couleur est un <b>groupe thématique</b> formé par l’algorithme à partir des tags communs. Faites tourner la sphère pour voir de quoi se compose notre nuage d’articles.',
          introB: 'Chaque point est un <b>auteur</b> — tous ceux que nous avons traités, des milliers. Les voisins partagent un profil de travaux similaire ; les nuages sont des domaines. La couleur va de l’<b>expérimentateur</b> au <b>théoricien</b>. L’important n’est pas un point isolé mais <b>le comportement de l’ensemble</b> : où sont les noyaux denses, où s’étirent les branches rares.' },
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
    zh: { title: '项目地图', articles: '文章', authors: '作者', loading: '正在构建地图…',
          hint: '拖动旋转 · 滚轮缩放 · 点击查看', clusters: '主题聚类', n: '点',
          theoryExp: '点的颜色：实验（赭石）→ 理论（青色）',
          introA: '每个点是一<b>篇文章</b>。两点越近，共同主题越多。颜色 = 算法自行划分的<b>主题聚类</b>。',
          introB: '每个点是一位<b>作者</b>。相近意味着主题相通。颜色 = 主题聚类，大小 = 作品数量。' },
    fr: { tab: 'Vol', fs: 'plein écran', speed: 'vitesse', hint: 'guidez pour tourner · molette/curseur pour la vitesse · clic sur l’étoile au centre pour ouvrir',
          intro: 'Vous <b>volez à travers notre univers d’articles</b>. Chaque étoile est un travail ; plus elle brille, plus elle est proche. Guidez à la souris ou au doigt, changez la vitesse à la molette. Visez l’étoile au centre pour la voir, cliquez pour l’ouvrir.' },
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
    zh: { tab: '飞行', fs: '全屏', speed: '速度',
          hint: '瞄准即可转向 · 滚轮或滑块调速 · 点击中心的星打开它',
          intro: '你正<b>飞越我们的文章宇宙</b>。每颗星是一项研究，越亮离得越近。用鼠标或手指转向，用滚轮或滑块调速。瞄准中心的星即可看清，点击打开。' },
    fr: { tab: 'Chaleur', hint: 'glisser pour tourner · molette pour zoomer',
          intro: 'Un <b>paysage thermique du projet</b> : un axe pour les groupes thématiques, l’autre pour les mois. Plus la barre est haute et brillante, plus il y a eu d’articles sur ce thème ce mois-là. Glissez pour tourner.' },
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
    zh: { tab: '热力', hint: '拖动旋转 · 滚轮缩放',
          intro: '<b>项目</b>的热力地形：一轴是主题聚类，另一轴是月份。柱子越高越亮，该月文章越多。拖动可旋转。' },
    fr: {
      sphere: 'Sphère', mobius: 'Möbius', matrix: 'Liens',
      sphereIntro: 'Tout le savoir du projet sur <b>une sphère</b> : concepts, lois et scientifiques disposés pour que le proche en sens soit proche en espace. Un <b>ensemble fermé</b> — le savoir n’a pas de bord. Faites tourner le globe et regardez quels continents se sont formés.',
      mobiusIntro: 'Nos articles sur un <b>ruban de Möbius</b>. Il n’a qu’une face : on avance et on revient au départ, retourné. La science fonctionne ainsi. La couleur est le groupe thématique ; le ruban s’enroule avec le temps.',
      matrixIntro: 'Une grille <b>concept × concept</b> : plus la case est brillante, plus deux idées apparaissent ensemble. Les carrés denses le long de la diagonale sont des domaines ; les points isolés au loin, des <b>ponts entre disciplines</b> — ce que nous avons de plus intéressant.',
      hint: 'glisser pour tourner · molette pour zoomer · survolez un point'
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
    fr: { tree: 'Arbre', spectrum: 'Rythme',
          treeIntro: 'Le savoir en <b>arbre ordonné</b> plutôt qu’en écheveau : les branches sont des directions, les feuilles des articles. Les noms viennent de l’IA, triés par poids — les thèmes riches en haut.',
          specIntro: 'La science a-t-elle un <b>rythme</b> ? Périodogramme de Lomb-Scargle, méthode d’astronomie pour les séries à trous. X : période en jours ; Y : force de répétition.' },
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
    fr: { tab: 'Tension',
          intro: 'L’intéressant n’est pas là où les travaux s’entassent, mais là où les domaines <b>s’accrochent</b>. À gauche, les <b>ponts</b> ; à droite, les <b>lacunes</b> : des zones riches sans concept commun. Une lacune n’est pas une erreur, c’est une piste.',
          bridges: 'Ponts entre domaines', gaps: 'Lacunes : le lien s’impose mais n’a pas de nom', leads: 'ce qui y mène' },
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
          groups: 'тематических групп', noData: 'Данных пока мало для вывода.',
          loose: 'Вне групп', looseWhy: 'работы, которые не примыкают ни к одной плотной теме — '
                 + 'это ответ карты, а не пропуск: так выглядит одиночное исследование' },
    en: { h: 'What this means', of: 'of', arts: 'articles', biggest: 'Largest group',
          share: 'that is {p}% of the archive', period: 'Strongest rhythm — a period near {n} days',
          periodWhy: 'so papers arrive in waves of that length rather than a steady stream',
          branches: 'Branches on the tree', thick: 'thickest', thin: 'thinnest',
          bridge: 'Strongest bridge between fields', gapTxt: 'Gaps where a link begs to exist but has no concept',
          dense: 'Concepts are most tightly linked inside', links: 'links between different fields',
          people: 'researchers', theorists: 'of them lean theoretical', spread: 'the cloud spans',
          groups: 'topic groups', noData: 'Not enough data yet.',
          loose: 'Outside the groups', looseWhy: 'papers that join no dense topic — this is the '
                 + 'map’s answer, not a gap: that is what solitary research looks like' },
    es: { h: 'Qué significa', of: 'de', arts: 'artículos', biggest: 'Grupo más grande',
          share: 'es el {p}% del archivo', period: 'Ritmo más fuerte: periodo de unos {n} días',
          periodWhy: 'los artículos llegan en oleadas de esa duración', branches: 'Ramas del árbol',
          thick: 'la más gruesa', thin: 'la más fina', bridge: 'Puente más fuerte',
          gapTxt: 'Vacíos sin concepto que una', dense: 'Los conceptos se enlazan más dentro de',
          links: 'enlaces entre campos', people: 'investigadores', theorists: 'tienden a la teoría',
          spread: 'la nube abarca', groups: 'grupos temáticos', noData: 'Aún faltan datos.',
          loose: 'Fuera de los grupos', looseWhy: 'trabajos que no se unen a ningún tema denso: '
                 + 'es la respuesta del mapa, no un hueco' },
    fr: { h: 'Ce que cela signifie', of: 'sur', arts: 'articles', biggest: 'Plus grand groupe',
          share: 'soit {p}% des archives', period: 'Rythme le plus net : période d’environ {n} jours',
          periodWhy: 'les articles arrivent par vagues de cette durée', branches: 'Branches de l’arbre',
          thick: 'la plus épaisse', thin: 'la plus fine', bridge: 'Pont le plus fort entre domaines',
          gapTxt: 'Lacunes où le lien s’impose sans concept', dense: 'Les concepts sont le plus liés dans',
          links: 'liens entre domaines', people: 'chercheurs', theorists: 'penchent vers la théorie',
          spread: 'le nuage s’étend sur', groups: 'groupes thématiques', noData: 'Pas encore assez de données.',
          loose: 'Hors des groupes', looseWhy: 'des travaux qui ne rejoignent aucun thème dense — '
                 + 'c’est la réponse de la carte, pas un manque' },
    ar: { h: 'ماذا يعني هذا', of: 'من', arts: 'مقالة', biggest: 'أكبر مجموعة',
          share: 'أي {p}% من الأرشيف', period: 'أقوى إيقاع — دورة نحو {n} يومًا',
          periodWhy: 'أي أن الأبحاث تأتي على موجات بهذا الطول', branches: 'أفرع الشجرة',
          thick: 'الأسمك', thin: 'الأدق', bridge: 'أقوى جسر بين المجالات',
          gapTxt: 'فجوات ينقصها مفهوم جامع', dense: 'ترتبط المفاهيم بكثافة داخل',
          links: 'روابط بين مجالات مختلفة', people: 'باحثًا', theorists: 'يميلون إلى النظرية',
          spread: 'تمتد السحابة على', groups: 'مجموعات موضوعية', noData: 'البيانات غير كافية بعد.',
          loose: 'خارج المجموعات', looseWhy: 'أعمال لا تنتمي إلى أي موضوع كثيف — هذا جواب الخريطة وليس نقصًا' }
  })[LANG] || null;
  var R = RD || { h: 'What this means', noData: '' };

  function clusterTitle(c) {
    var titles = (cache.articles && cache.articles.titles) || (state.data && state.data.titles) || {};
    var lt = titles[c] && (titles[c][LANG] || titles[c].en);
    if (lt && lt.title) return lt.title;
    // Имён от трактовщика может не быть (у карты v2 их пока нет вовсе). Тогда берём
    // характерные теги группы — так же, как делает легенда. Голое «#41» — это ровно
    // находка 1 августовского аудита: читателю показывали внутренний номер кластера.
    var cl = (state.data && state.data.clusters) || {};
    var tags = cl[c] || cl[String(c)];
    if (tags && tags.length) return tags.slice(0, 3).map(niceLabel).join(' · ');
    return isNoise(c) ? (R.loose || '—') : ('#' + c);
  }

  function reading(mode) {
    var d = state.data || {};
    var out = [];
    try {
      if (mode === 'articles' || mode === 'mobius' || mode === 'fly') {
        var cnt = {}; (d.points || []).forEach(function (p) { cnt[p.c] = (cnt[p.c] || 0) + 1; });
        var n = d.n || (d.points || []).length;
        // Крупнейшую тему ищем среди тем. У карты v2 самая многочисленная метка — «вне
        // групп» (40% корпуса), и без этого фильтра читатель увидел бы «Самая крупная
        // группа: «#-1» — 40% архива» — ровно та беда, из-за которой в августе чинили «#21».
        var keys = Object.keys(cnt).filter(function (c) { return !isNoise(c); });
        var top = keys.sort(function (a, b) { return cnt[b] - cnt[a]; })[0];
        if (top != null) {
          out.push('<b>' + R.biggest + ':</b> «' + clusterTitle(+top) + '» — ' + cnt[top] + ' ' + R.arts
                   + ', ' + R.share.replace('{p}', Math.round(cnt[top] / Math.max(1, n) * 100)) + '.');
          out.push(keys.length + ' ' + R.groups + ' ' + R.of + ' ' + n + ' ' + R.arts + '.');
        }
        // 40% работ вне групп — это не мелочь, о которой можно умолчать: не объяснив её,
        // мы оставляем читателя гадать, почему часть точек серая.
        var loose = 0;
        Object.keys(cnt).forEach(function (c) { if (isNoise(c)) loose += cnt[c]; });
        if (loose && R.loose) {
          out.push('<b>' + R.loose + ':</b> ' + loose + ' ' + R.arts + ' ('
                   + Math.round(loose / Math.max(1, n) * 100) + '%) — ' + R.looseWhy + '.');
        }
      } else if (mode === 'world') {
        // Чтение карты мира: три числа, которые отвечают на «где мы стоим».
        var L = (d.legend && (d.legend[LANG] || d.legend.ru)) || {};
        var pts = d.points || [];
        var gaps = pts.filter(function (p) { return p.gap; }).length;
        var covered = pts.filter(function (p) { return (p.o || 0) > 0; }).length;
        if (L.note) out.push(L.note);
        out.push('<b>' + (d.field || 0).toLocaleString() + '</b> ' + (L.world || '') +
                 ' · <b>' + (d.ours || 0).toLocaleString() + '</b> ' + (L.ours || '') + '.');
        out.push('Областей с нашими работами: <b>' + covered + '</b> из ' + pts.length +
                 '; значимых пустот: <b>' + gaps + '</b>.');
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
    fr: { spectrum: 'survolez un pic — période en jours', tree: 'les branches du haut sont les plus grandes',
          tension: 'ponts à gauche, lacunes à droite', matrix: 'case plus brillante = plus de co-occurrences',
          sphere: 'glisser pour tourner le globe', mobius: 'glisser pour tourner le ruban' },
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
      + 'и превращаем это в близость: похожие работы оказываются рядом. Всё считается <b>локально</b> '
      + '(смысловые векторы статей bge-m3 → проекция в 3D методом UMAP → выделение плотных групп методом HDBSCAN) — '
      + 'без обращения к ИИ, поэтому карту легко держать актуальной. Новые работы <b>подсаживаются</b> в уже '
      + 'построенную проекцию: карта не перекладывается каждый день, и вы узнаёте её через неделю.</p>'
      + '<p>Часть работ алгоритм оставляет <b>вне групп</b> и красит серым. Это не пропуск и не ошибка: '
      + 'так выглядит исследование, которое не примыкает ни к одной плотной теме.</p>'
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
      + '(semantic bge-m3 vectors of the papers → 3D projection via UMAP → dense groups via HDBSCAN) — no AI calls, '
      + 'so the map is easy to keep up to date. New papers are <b>seated into</b> the existing projection: the map is '
      + 'not relaid every day, so you still recognise it a week later.</p>'
      + '<p>Some papers are left <b>outside the groups</b> and drawn in grey. That is not a gap or an error: '
      + 'it is what research that joins no dense topic looks like.</p>'
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
      + 'y lo convertimos en cercanía. Todo se calcula <b>localmente</b> (vectores semánticos bge-m3 → proyección 3D '
      + 'con UMAP → grupos densos con HDBSCAN), sin IA. Los trabajos nuevos se <b>sientan</b> en la proyección ya '
      + 'construida: el mapa no se rehace cada día.</p>'
      + '<p>Algunos trabajos quedan <b>fuera de los grupos</b>, en gris. No es un hueco ni un error: '
      + 'así se ve una investigación que no se une a ningún tema denso.</p>'
      + '<h3>Qué significan los grupos y colores</h3>'
      + '<ul><li>Un <b>punto</b> es un artículo (o autor). Cuanto más cerca, más comparten.</li>'
      + '<li>El <b>color</b> es un grupo temático que el algoritmo encontró solo.</li>'
      + '<li>El <b>nombre del grupo</b> lo da la <b>IA</b> a partir de las etiquetas del clúster.</li>'
      + '<li>En autores, el color va de <b>experimental → teórico</b>.</li></ul>'
      + '<h3>Qué hay ahora y hacia dónde crece</h3>'
      + '<p>Por ahora dos facetas: <b>artículos</b> y <b>autores</b>. Luego un <b>mapa general</b> con pestañas de <b>leyes, científicos y etiquetas</b>.</p>',
    fr: '<h3>Comment la carte est construite</h3>'
      + '<p>Les articles sont le tissu conjonctif. Nous regardons quels <b>thèmes, domaines et concepts</b> '
      + 'apparaissent ensemble et convertissons cela en proximité : les travaux proches se retrouvent côte à côte. '
      + 'Tout est calculé <b>localement</b> (vecteurs sémantiques bge-m3 → projection 3D par UMAP → groupes denses '
      + 'par HDBSCAN), sans IA. Les nouveaux travaux sont <b>insérés</b> dans la projection existante : la carte '
      + 'n’est pas refaite chaque jour, vous la reconnaissez une semaine plus tard.</p>'
      + '<p>Certains travaux restent <b>hors des groupes</b>, en gris. Ce n’est ni un manque ni une erreur : '
      + 'voilà à quoi ressemble une recherche qui ne rejoint aucun thème dense.</p>'
      + '<h3>Ce que signifient les groupes et les couleurs</h3>'
      + '<ul><li><b>Un point</b> — un article (ou un auteur). Plus les points sont proches, plus ils ont en commun.</li>'
      + '<li><b>La couleur</b> — un groupe thématique que l’algorithme a dégagé lui-même.</li>'
      + '<li><b>Le nom du groupe</b> vient de l’<b>IA</b> : elle lit les tags caractéristiques et écrit un nom lisible.</li>'
      + '<li>Chez les auteurs, la couleur va de l’<b>expérimentateur</b> au <b>théoricien</b>.</li></ul>'
      + '<h3>Ce qui est affiché et vers quoi cela grandit</h3>'
      + '<p>Deux vues pour l’instant : <b>articles</b> et <b>auteurs</b>. Ensuite une <b>carte commune</b> avec des '
      + 'onglets pour les lois, les scientifiques et les tags.</p>',
    ar: '<h3>كيف بُنيت الخريطة</h3>'
      + '<p>المقالات هي النسيج الرابط. ننظر إلى <b>المواضيع والأقسام والمفاهيم</b> التي ترد معًا ونحوّلها إلى قُرب. '
      + 'يُحسب كل شيء <b>محليًا</b> إحصائيًا (متجهات دلالية bge-m3 ← إسقاط ثلاثي الأبعاد UMAP ← مجموعات كثيفة HDBSCAN) دون ذكاء اصطناعي. تُضاف الأعمال الجديدة إلى الإسقاط القائم، فلا تتغيّر الخريطة كل يوم.</p>'
      + '<p>تبقى بعض الأعمال <b>خارج المجموعات</b> بلون رمادي. هذا ليس نقصًا ولا خطأً: هكذا يبدو بحث لا ينتمي إلى أي موضوع كثيف.</p>'
      + '<h3>ماذا تعني المجموعات والألوان</h3>'
      + '<ul><li><b>النقطة</b> مقالة (أو مؤلف). كلما اقتربت زاد المشترك.</li>'
      + '<li><b>اللون</b> مجموعة موضوعية اكتشفها الخوارزم.</li>'
      + '<li><b>اسم المجموعة</b> من <b>الذكاء الاصطناعي</b> اعتمادًا على وسوم العنقود.</li>'
      + '<li>لدى المؤلفين يتدرّج اللون من <b>تجريبي ← نظري</b>.</li></ul>'
      + '<h3>ما هو معروض الآن وإلى أين ينمو</h3>'
      + '<p>حاليًا وجهان: <b>المقالات</b> و<b>المؤلفون</b>. لاحقًا <b>خريطة عامة</b> بعلامات تبويب للقوانين والعلماء والوسوم.</p>'
  })[LANG] || '';

  /* Шапка вида: слева — что это, справа — как читать. Раньше у десяти представлений был один
     заголовок на всю страницу, и, переключив вкладку, читатель видел новую картинку без единого
     слова о том, что перед ним. Стили (.an-head) были написаны заранее, но ни разу не подключены. */
  var HEAD = ({
    ru: { articles: 'точка — статья, цвет — тематическая группа',
          authors: 'точка — автор, цвет — от эксперимента к теории',
          fly: 'полёт внутри облака статей',
          heat: 'месяцы по горизонтали, группы по вертикали',
          sphere: 'теги на сфере: рядом те, что встречаются вместе',
          mobius: 'лента без изнанки — статьи по кругу',
          matrix: 'клетка — как часто два понятия встречаются вместе',
          tree: 'ветви — разделы, листья — статьи',
          spectrum: 'ритм выхода статей во времени',
          tension: 'мосты между областями и разрывы между ними' },
    en: { articles: 'a dot is an article, colour is a topic group',
          authors: 'a dot is an author, colour runs from experiment to theory',
          fly: 'a flight inside the cloud of articles',
          heat: 'months across, groups down',
          sphere: 'tags on a sphere: those that co-occur sit close',
          mobius: 'a one-sided band — articles around it',
          matrix: 'a cell shows how often two notions meet',
          tree: 'branches are sections, leaves are articles',
          spectrum: 'the rhythm of publishing over time',
          tension: 'bridges between fields and the gaps between them' },
    es: { articles: 'un punto es un artículo, el color es un grupo temático',
          authors: 'un punto es un autor, el color va de experimento a teoría',
          fly: 'un vuelo dentro de la nube de artículos',
          heat: 'meses en horizontal, grupos en vertical',
          sphere: 'etiquetas en una esfera: juntas las que coinciden',
          mobius: 'una banda de una sola cara — artículos alrededor',
          matrix: 'la celda muestra cuánto coinciden dos nociones',
          tree: 'las ramas son secciones, las hojas artículos',
          spectrum: 'el ritmo de publicación en el tiempo',
          tension: 'puentes entre áreas y las brechas entre ellas' },
    ar: { articles: 'النقطة مقالة، واللون مجموعة موضوعية',
          authors: 'النقطة مؤلف، واللون يتدرّج من التجريب إلى النظرية',
          fly: 'تحليق داخل سحابة المقالات',
          heat: 'الأشهر أفقيًا والمجموعات رأسيًا',
          sphere: 'وسوم على كرة: المتجاورة تتكرّر معًا',
          mobius: 'شريط بوجه واحد — المقالات حوله',
          matrix: 'الخلية تُظهر كم يلتقي مفهومان',
          tree: 'الفروع أقسام والأوراق مقالات',
          spectrum: 'إيقاع النشر عبر الزمن',
          tension: 'جسور بين المجالات والفجوات بينها' }
  })[LANG] || {};
  // Карта мира: координаты дают 600 областей поля arXiv, а не наши теги. Тексты вкладки
  // держим здесь, подробную легенду отдаёт сам файл данных (world-view.json).
  var WM = {
    ru: { tab: 'мир', hint: 'Каждый круг — область науки. Размер — сколько там работ у мира, цвет — какую долю разобрали мы.' },
    en: { tab: 'world', hint: 'Each circle is an area of science. Size is how many papers the world has; colour is the share we reviewed.' },
    es: { tab: 'mundo', hint: 'Cada círculo es un área de la ciencia. El tamaño indica los trabajos del mundo; el color, la parte analizada.' },
    fr: { tab: 'monde', hint: 'Chaque cercle est un domaine. La taille indique les travaux du monde ; la couleur, la part analysée.' },
    ar: { tab: 'العالم', hint: 'كل دائرة مجال علمي. الحجم عدد الأبحاث في العالم، واللون النسبة التي حلّلناها.' }
  }[LANG] || { tab: 'world', hint: '' };

  var HEAD_T = { articles: T.articles, authors: T.authors, world: WM.tab, fly: FLY.tab, heat: HEAT.tab,
                 sphere: V.sphere, mobius: V.mobius, matrix: V.matrix,
                 tree: V2.tree, spectrum: V2.spectrum, tension: V3.tab };

  var OVT = ({ ru: { tab: 'Обзор', hint: 'все виды на одном экране: числа и плитки; плитка открывает вид',
                     kArt: 'статей разобрано', kMap: 'на карте статей', kWorld: 'поле arXiv', kAuth: 'авторов на карте',
                     kCon: 'понятий в реестре', kTags: 'тегов в связях', kRhythm: 'выход по месяцам', kLang: 'языков',
                     full: 'полных', express: 'экспресс', groups: 'групп', noise: 'вне групп', ours: 'наших',
                     built: 'данные собраны', desk: 'на широком экране', open: 'открыть', months: 'мес.' },
               en: { tab: 'Overview', hint: 'every view on one screen: numbers and tiles; a tile opens the view',
                     kArt: 'articles reviewed', kMap: 'on the article map', kWorld: 'arXiv field', kAuth: 'authors on the map',
                     kCon: 'concepts in the registry', kTags: 'tags in co-occurrence', kRhythm: 'output by month', kLang: 'languages',
                     full: 'full', express: 'express', groups: 'groups', noise: 'outside groups', ours: 'ours',
                     built: 'data built', desk: 'on a wide screen', open: 'open', months: 'mo' },
               es: { tab: 'Resumen', hint: 'todas las vistas en una pantalla: cifras y fichas; la ficha abre la vista',
                     kArt: 'artículos analizados', kMap: 'en el mapa de artículos', kWorld: 'campo arXiv', kAuth: 'autores en el mapa',
                     kCon: 'conceptos en el registro', kTags: 'etiquetas en coocurrencia', kRhythm: 'salida por mes', kLang: 'idiomas',
                     full: 'completos', express: 'exprés', groups: 'grupos', noise: 'fuera de grupos', ours: 'nuestros',
                     built: 'datos generados', desk: 'en pantalla ancha', open: 'abrir', months: 'meses' },
               ar: { tab: 'نظرة عامة', hint: 'كل الأشكال في شاشة واحدة: أرقام وبطاقات؛ البطاقة تفتح الشكل',
                     kArt: 'مقالات محلّلة', kMap: 'على خريطة المقالات', kWorld: 'حقل arXiv', kAuth: 'مؤلفون على الخريطة',
                     kCon: 'مفاهيم في السجل', kTags: 'وسوم في التلازم', kRhythm: 'الإصدار شهريًا', kLang: 'لغات',
                     full: 'كاملة', express: 'سريعة', groups: 'مجموعات', noise: 'خارج المجموعات', ours: 'لدينا',
                     built: 'بُنيت البيانات', desk: 'على شاشة عريضة', open: 'فتح', months: 'شهر' },
               fr: { tab: 'Aperçu', hint: 'toutes les vues sur un écran : chiffres et tuiles ; une tuile ouvre la vue',
                     kArt: 'articles analysés', kMap: 'sur la carte des articles', kWorld: 'champ arXiv', kAuth: 'auteurs sur la carte',
                     kCon: 'concepts au registre', kTags: 'tags en cooccurrence', kRhythm: 'sortie par mois', kLang: 'langues',
                     full: 'complets', express: 'express', groups: 'groupes', noise: 'hors groupes', ours: 'à nous',
                     built: 'données générées', desk: 'sur grand écran', open: 'ouvrir', months: 'mois' } })[LANG] ||
            { tab: 'Overview', hint: 'every view on one screen: numbers and tiles; a tile opens the view',
              kArt: 'articles reviewed', kMap: 'on the article map', kWorld: 'arXiv field', kAuth: 'authors on the map',
              kCon: 'concepts in the registry', kTags: 'tags in co-occurrence', kRhythm: 'output by month', kLang: 'languages',
              full: 'full', express: 'express', groups: 'groups', noise: 'outside groups', ours: 'ours',
              built: 'data built', desk: 'on a wide screen', open: 'open', months: 'mo' };
  // Значок «i» у вкладки: подсказка о том, что на виде (владелец 05.09: как на панели El Niño).
  function ti(mode) {
    var t = mode === 'overview' ? OVT.hint : (HEAD[mode] || '');
    return t ? '<span class="ti" title="' + t.replace(/"/g, '&quot;') + '" data-tip-text="' + t.replace(/"/g, '&quot;') + '">i</span>' : '';
  }
  // Страница аналитики — широкая, как панель El Niño: колонка в 668px не вмещала ни карту, ни плитки.
  document.body.classList.add('an-wide');

  root.innerHTML =
    '<h1 class="dash-h1">' + T.title + '</h1>' +
    '<div class="an-tabs"><button class="an-tab active" data-t="overview">' + OVT.tab + ti('overview') + '</button>' +
    '<button class="an-tab" data-t="articles">' + T.articles + ti('articles') + '</button>' +
    '<button class="an-tab" data-t="world"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="8.5"/><ellipse cx="12" cy="12" rx="4" ry="8.5"/><path d="M3.8 9.5h16.4"/><path d="M3.8 14.5h16.4"/></svg> ' + WM.tab + '' + ti('world') + '</button>' +
    '<button class="an-tab" data-t="authors">' + T.authors + ti('authors') + '</button>' +
    '<button class="an-tab" data-t="fly"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 12l18-8-7 18-2.5-7.5L3 12Z"/></svg> ' + FLY.tab + '' + ti('fly') + '</button>' +
    '<button class="an-tab" data-t="heat"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3.5" y="13" width="4" height="7.5" rx="1"/><rect x="10" y="8" width="4" height="12.5" rx="1"/><rect x="16.5" y="4" width="4" height="16.5" rx="1"/></svg> ' + HEAT.tab + '' + ti('heat') + '</button>' +
    '<button class="an-tab" data-t="sphere"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="8"/><ellipse cx="12" cy="12" rx="8" ry="3.4"/><path d="M12 4c2.2 2.3 3.4 5 3.4 8s-1.2 5.7-3.4 8"/><path d="M12 4c-2.2 2.3-3.4 5-3.4 8s1.2 5.7 3.4 8"/></svg> ' + V.sphere + '' + ti('sphere') + '</button>' +
    '<button class="an-tab" data-t="mobius"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4.5 12c0-2.8 3.4-5 7.5-5s7.5 2.2 7.5 5-3.4 5-7.5 5-7.5-2.2-7.5-5Z"/><path d="M6.5 9.5c3 1.6 8 3.4 11 5"/></svg> ' + V.mobius + '' + ti('mobius') + '</button>' +
    '<button class="an-tab" data-t="matrix"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="4" width="6.5" height="6.5" rx="1"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1"/></svg> ' + V.matrix + '' + ti('matrix') + '</button>' +
    '<button class="an-tab" data-t="tree"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12h4"/><path d="M8 12V6h5"/><path d="M8 12v6h5"/><circle cx="15" cy="6" r="2"/><circle cx="15" cy="18" r="2"/><circle cx="4" cy="12" r="1.6"/></svg> ' + V2.tree + '' + ti('tree') + '</button>' +
    '<button class="an-tab" data-t="spectrum"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 18l3-6 3 9 3-13 3 8 3-4 3 6"/></svg> ' + V2.spectrum + '' + ti('spectrum') + '</button>' +
    '<button class="an-tab" data-t="tension"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12h5"/><path d="M15 12h5"/><path d="M9 8.5 12 12l-3 3.5"/><path d="M15 8.5 12 12l3 3.5"/></svg> ' + V3.tab + '' + ti('tension') + '</button></div>' +
    '<div class="anv" id="an-ov" hidden></div>' +
    '<p class="an-intro" id="an-intro">' + T.introA + '</p>' +
    '<div class="an-head" id="an-head"></div>' +
    '<div class="an-stage" id="an-stage"><canvas id="an-canvas"></canvas><div class="an-hint">' + T.hint + '</div>' +
    '<div class="an-stage-ctl">' +
    '<button class="an-btn" id="an-spin" title="' + CTL.spin + '" aria-pressed="true"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 12a8 8 0 1 1-2.5-5.8"/><path d="M20 4v4h-4"/></svg></button>' +
    '<button class="an-btn" id="an-zin" title="' + CTL.zin + '"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6"/><path d="M15 15l5 5"/><path d="M8 10.5h5"/><path d="M10.5 8v5"/></svg></button>' +
    '<button class="an-btn" id="an-zout" title="' + CTL.zout + '"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6"/><path d="M15 15l5 5"/><path d="M8 10.5h5"/></svg></button>' +
    '<button class="an-btn" id="an-shapes" title="' + CTL.shapes + '" aria-pressed="false"><svg class="ico-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="7" cy="7" r="3"/><rect x="14" y="4" width="6" height="6" rx="1"/><path d="M7 14l3 6H4l3-6Z"/><path d="M17 13.5l1.2 2.6 2.8.3-2.1 1.9.6 2.7-2.5-1.4-2.5 1.4.6-2.7-2.1-1.9 2.8-.3 1.2-2.6Z"/></svg></button>' +
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
    if (location.hash.slice(1) !== mode) { try { history.replaceState(null, '', '#' + mode); } catch (e) {} }
    var ovEl = document.getElementById('an-ov');
    ['an-intro', 'an-head', 'an-stage', 'an-legend'].forEach(function (id) {
      var e = document.getElementById(id); if (e) e.hidden = (mode === 'overview');
    });
    if (mode === 'overview') { if (ovEl) { ovEl.hidden = false; overview(); } state.spin = false; return; }
    if (ovEl) ovEl.hidden = true;
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
    var headEl = document.getElementById('an-head');
    if (headEl) {
      headEl.innerHTML = '<span class="an-head-t">' + (HEAD_T[mode] || '') + '</span>' +
                         '<span class="an-head-n">' + (HEAD[mode] || '') + '</span>';
    }
    if (hintEl) hintEl.textContent = HINTS[mode] || (mode === 'fly' ? FLY.hint
      : (mode === 'heat' ? HEAT.hint : (mode === 'world' ? WM.hint : T.hint)));
    if (mode === 'fly') { state.travel = 0; state.fyaw = 0; state.fpitch = 0; state.speed = 0.0011; }
    var speedBox = document.getElementById('an-speed');
    if (speedBox) speedBox.style.display = mode === 'fly' ? 'flex' : 'none';
    var sr = document.getElementById('an-speed-r');
    if (sr && mode === 'fly') sr.value = Math.round(state.speed / 0.006 * 60);
    if (cache[dataMode]) { state.data = cache[dataMode]; prep(); return; }
    document.getElementById('an-loading').style.display = '';
    var FILE = { authors: 'authors-map', articles: 'articles-map-v2', cooc: 'tags-cooc',
                 world: 'world-view' };
    // Карта статей — v2 (эмбеддинги + UMAP + HDBSCAN) с откатом на v1 (теги + t-SNE).
    // Откат нужен не для красоты: v2 строит отдельный скрипт, и пока он не встал в
    // фабрику, файла может не быть на свежей выкладке. Пустая карта хуже старой.
    var BACK = { 'articles-map-v2': 'articles-map' };
    var name = FILE[dataMode] || 'articles-map-v2';
    function grab(f, fallback) {
      return fetch('/data/analytics/' + f + '.json').then(function (r) {
        if (!r.ok) throw new Error(r.status);
        return r.json();
      }).catch(function (e) {
        if (!fallback) throw e;
        return grab(fallback, null);
      });
    }
    grab(name, BACK[name])
      .then(function (d) { cache[dataMode] = d; state.data = d; prep(); })
      .catch(function () { document.getElementById('an-loading').textContent = '—'; });
  }

  /* ОБЗОР: ПОЛОСА KPI И ПЛИТКИ ВИДОВ. Владелец 05.09: «аналитике удели внимание, сделать
     похожей на наш дашборд» — тот же приём, что на панели El Niño: сначала числа, потом
     мозаика всех видов, каждая плитка — живая мини-картинка на своих данных и ссылка в вид.
     Данные те же файлы, что и у видов (кэш общий); карта авторов (3 МБ) — только на широком
     экране и после остального. */
  var OV = { done: false };
  function ovGrab(name) {
    if (cache[name]) return Promise.resolve(cache[name]);
    return fetch('/data/analytics/' + ({ articles: 'articles-map-v2', authors: 'authors-map', cooc: 'tags-cooc', world: 'world-view' })[name] + '.json')
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { if (d) cache[name] = d; return d; }).catch(function () { return null; });
  }
  function fmtN(n) { return (n == null || isNaN(n)) ? '—' : String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, '\u2009'); }
  function ovKpi(kn, big, small, go, tipText) {
    return '<div class="anv-kpi" data-go="' + (go || '') + '"' + (tipText ? ' title="' + tipText.replace(/"/g, '&quot;') + '"' : '') + '>' +
      '<div class="kn">' + kn + '</div><div class="kv">' + big + '</div><div class="km">' + (small || '') + '</div></div>';
  }
  function overview() {
    var el = document.getElementById('an-ov');
    if (!el) return;
    if (OV.done) return;
    OV.done = true;
    el.innerHTML = '<div class="b42-loader">' + T.loading + '</div>';
    var wide = (window.innerWidth || 0) >= 900;
    Promise.all([ovGrab('articles'), ovGrab('world'), ovGrab('cooc'),
                 fetch('/data/corpus-stats.json').then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }),
                 (window._conceptsNamesP && window._conceptsNamesP.then) ? window._conceptsNamesP.catch(function () { return null; }) : Promise.resolve(window.conceptsNames || null)])
      .then(function (res) {
        var A = res[0], W = res[1], C = res[2], S = res[3], N = res[4];
        var months = (S && S.months) || [];
        var last = months.slice(-24);
        var gen = (S && S.generated_total) || {};
        var clusters = A && A.clusters ? Object.keys(A.clusters).length : 0;
        var noise = A ? Math.round(100 * (A.noise || 0) / Math.max(1, A.n || 1)) : 0;
        var built = (W && W.built) || (S && S.dump_date) || '';
        var spark = '';
        if (last.length > 2) {
          var mx = Math.max.apply(null, last.map(function (m) { return m.published || m.generated || 0; })) || 1;
          spark = '<svg class="anv-spark" viewBox="0 0 ' + (last.length * 6) + ' 24" preserveAspectRatio="none">' + last.map(function (m, i) {
            var v = (m.published || m.generated || 0) / mx, h = Math.max(1, Math.round(v * 22));
            return '<rect x="' + (i * 6) + '" y="' + (24 - h) + '" width="4" height="' + h + '" fill="var(--ochre)" opacity=".8"/>';
          }).join('') + '</svg>';
        }
        var strip = '<div class="anv-strip">' +
          ovKpi(OVT.kArt, fmtN(gen.gen) , fmtN(gen.full) + ' ' + OVT.full + ' · ' + fmtN(gen.express) + ' ' + OVT.express, 'articles') +
          ovKpi(OVT.kMap, A ? fmtN(A.n) : '—', A ? (clusters + ' ' + OVT.groups + ' · ' + noise + '% ' + OVT.noise) : '', 'articles') +
          ovKpi(OVT.kWorld, W ? fmtN(W.field) : '—', W ? (fmtN(W.ours) + ' ' + OVT.ours + ' · ' + (W.empty_regions || 0) + '/' + (W.n || 0)) : '', 'world', WM.hint) +
          ovKpi(OVT.kAuth, '<span id="anv-auth">' + (wide ? '…' : '—') + '</span>', wide ? '' : OVT.desk, 'authors') +
          ovKpi(OVT.kCon, N ? fmtN(Object.keys(N).length) : '—', '<a href="/lang/' + LANG + '/concepts/">' + OVT.open + ' →</a>', '') +
          ovKpi(OVT.kTags, C && C.entities ? fmtN(C.entities.length) : '—', '', 'sphere') +
          ovKpi(OVT.kRhythm, spark || '—', last.length ? (last[0].ym + ' → ' + last[last.length - 1].ym) : '', 'spectrum') +
          ovKpi(OVT.kLang, '5', 'ru · en · es · ar · fr', '') +
          '</div>';
        var ORDER = ['articles', 'world', 'authors', 'fly', 'heat', 'sphere', 'mobius', 'matrix', 'tree', 'spectrum', 'tension'];
        var tiles = '<div class="anv-grid">' + ORDER.map(function (m) {
          return '<div class="anv-tile" data-t="' + m + '"><div class="anv-t">' + (HEAD_T[m] || m) + '</div>' +
            '<canvas class="anv-cv" data-m="' + m + '"></canvas><div class="anv-c">' + (HEAD[m] || '') + '</div></div>';
        }).join('') + '</div>';
        var badge = built ? '<div class="anv-date" title="' + OVT.built + ' ' + built + '">' +
          '<svg viewBox="0 0 12 12" width="11" height="11" aria-hidden="true"><rect x="1" y="2.5" width="10" height="8.5" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.1"/><line x1="1" y1="5.2" x2="11" y2="5.2" stroke="currentColor" stroke-width="1.1"/><line x1="3.8" y1="1" x2="3.8" y2="3.5" stroke="currentColor" stroke-width="1.1"/><line x1="8.2" y1="1" x2="8.2" y2="3.5" stroke="currentColor" stroke-width="1.1"/></svg> ' + built + '</div>' : '';
        el.innerHTML = strip + tiles + badge;
        el.querySelectorAll('.anv-kpi[data-go]').forEach(function (k) {
          if (!k.dataset.go) return;
          k.addEventListener('click', function (e) { if (e.target.closest('a')) return; goTab(k.dataset.go); });
        });
        el.querySelectorAll('.anv-tile').forEach(function (t) { t.addEventListener('click', function () { goTab(t.dataset.t); }); });
        el.querySelectorAll('canvas.anv-cv').forEach(function (cv) { miniDraw(cv, cv.dataset.m, A, W, C, null); });
        if (wide) {
          var run = function () {
            ovGrab('authors').then(function (AU) {
              var s = document.getElementById('anv-auth');
              if (s) s.textContent = AU ? fmtN(AU.n) : '—';
              var cv = el.querySelector('canvas.anv-cv[data-m="authors"]');
              if (cv && AU) miniDraw(cv, 'authors', A, W, C, AU);
            });
          };
          if (window.requestIdleCallback) requestIdleCallback(run, { timeout: 4000 }); else setTimeout(run, 1200);
        }
      });
  }
  function goTab(mode) {
    var b = document.querySelector('.an-tab[data-t="' + mode + '"]');
    if (!b) return;
    document.querySelectorAll('.an-tab').forEach(function (x) { x.classList.remove('active'); });
    b.classList.add('active'); state.spin = true; load(mode);
    var top = document.getElementById('an-head'); if (top && top.scrollIntoView) top.scrollIntoView({ block: 'start', behavior: 'smooth' });
  }
  /* Мини-картинки плиток: тот же смысл, что у вида, но в сто строк и без интерактива. */
  function miniDraw(cv, m, A, W, C, AU) {
    var dpr = window.devicePixelRatio || 1, w = cv.clientWidth || 260, h = cv.clientHeight || 140;
    cv.width = w * dpr; cv.height = h * dpr;
    var g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, w, h);
    var cs = getComputedStyle(document.documentElement);
    var soft = cs.getPropertyValue('--soft').trim() || '#999', line = cs.getPropertyValue('--hair').trim() || '#ddd';
    var pts = (A && A.points) || [], ents = (C && C.entities) || [], wp = (W && W.points) || [];
    var pad = 8;
    function sx(x) { return pad + x * (w - 2 * pad); }
    function sy(y) { return pad + y * (h - 2 * pad); }
    g.globalAlpha = 1;
    if (m === 'articles' || m === 'fly' || m === 'mobius') {
      for (var i = 0; i < pts.length; i += 1) {
        var p = pts[i], z = p.z != null ? p.z : 0.5;
        var x, y, r;
        if (m === 'mobius') {
          var a = p.x * Math.PI * 2, R = Math.min(w, h) * 0.36;
          x = w / 2 + Math.cos(a) * (R + (p.y - 0.5) * 22); y = h / 2 + Math.sin(a) * (R * 0.55 + (p.y - 0.5) * 22) * 0.9; r = 1.1;
        } else if (m === 'fly') {
          var d = 0.35 + z;                                   // ближние крупнее
          x = w / 2 + (p.x - 0.5) * (w - 2 * pad) * d; y = h / 2 + (p.y - 0.5) * (h - 2 * pad) * d; r = 0.6 + z * 1.6;
        } else { x = sx(p.x); y = sy(p.y); r = 1.2; }
        g.fillStyle = palOf(p.c); g.globalAlpha = isNoise(p.c) ? 0.35 : 0.8;
        g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
      }
    } else if (m === 'heat' || m === 'spectrum') {
      var byM = {}, order = [];
      pts.forEach(function (p) { var k = (p.d || '').slice(0, 7); if (k.length !== 7) return; if (!byM[k]) { byM[k] = {}; order.push(k); } byM[k][p.c] = (byM[k][p.c] || 0) + 1; });
      order.sort(); order = order.slice(-24);
      var cl = {}; pts.forEach(function (p) { if (!isNoise(p.c)) cl[p.c] = (cl[p.c] || 0) + 1; });
      var top = Object.keys(cl).sort(function (a, b) { return cl[b] - cl[a]; }).slice(0, 8);
      var cw = (w - 2 * pad) / Math.max(1, order.length);
      if (m === 'heat') {
        var ch = (h - 2 * pad) / Math.max(1, top.length), mx = 1;
        order.forEach(function (k) { top.forEach(function (c) { mx = Math.max(mx, byM[k][c] || 0); }); });
        order.forEach(function (k, i) { top.forEach(function (c, j) {
          var v = (byM[k][c] || 0) / mx; if (!v) return;
          g.fillStyle = palOf(c); g.globalAlpha = 0.15 + v * 0.85;
          g.fillRect(pad + i * cw, pad + j * ch, Math.max(1, cw - 1), Math.max(1, ch - 1));
        }); });
      } else {
        var tot = order.map(function (k) { var s = 0; for (var c in byM[k]) s += byM[k][c]; return s; }), mm = Math.max.apply(null, tot.concat([1]));
        order.forEach(function (k, i) {
          var y0 = h - pad;
          top.forEach(function (c) { var v = byM[k][c] || 0; if (!v) return; var bh = v / mm * (h - 2 * pad);
            g.fillStyle = palOf(c); g.globalAlpha = 0.85; g.fillRect(pad + i * cw + 1, y0 - bh, Math.max(1, cw - 2), bh); y0 -= bh; });
        });
      }
    } else if (m === 'tree') {
      var cnt = {}; pts.forEach(function (p) { if (!isNoise(p.c)) cnt[p.c] = (cnt[p.c] || 0) + 1; });
      var ks = Object.keys(cnt), cx = w / 2, cy = h / 2, R2 = Math.min(w, h) * 0.42, mxc = Math.max.apply(null, ks.map(function (k) { return cnt[k]; }).concat([1]));
      g.strokeStyle = line; g.lineWidth = 1;
      ks.forEach(function (k, i) {
        var a = -Math.PI / 2 + i / ks.length * Math.PI * 2, x = cx + Math.cos(a) * R2, y = cy + Math.sin(a) * R2 * 0.8;
        g.globalAlpha = 0.6; g.beginPath(); g.moveTo(cx, cy); g.quadraticCurveTo((cx + x) / 2, cy, x, y); g.stroke();
        g.fillStyle = palOf(k); g.globalAlpha = 0.9; g.beginPath(); g.arc(x, y, 2 + Math.sqrt(cnt[k] / mxc) * 7, 0, Math.PI * 2); g.fill();
      });
      g.fillStyle = soft; g.beginPath(); g.arc(cx, cy, 3, 0, Math.PI * 2); g.fill();
    } else if (m === 'world') {
      var mw = Math.max.apply(null, wp.map(function (q) { return q.w || 0; }).concat([1]));
      wp.forEach(function (q) {
        var r = 0.8 + Math.sqrt((q.w || 0) / mw) * 6, cov = Math.max(0, Math.min(1, q.cov || 0));
        g.fillStyle = cov > 0 ? 'rgba(46,138,160,' + (0.18 + cov * 0.6).toFixed(2) + ')' : 'rgba(150,150,150,0.18)';
        g.beginPath(); g.arc(sx(q.x), sy(q.y), r, 0, Math.PI * 2); g.fill();
      });
    } else if (m === 'authors') {
      var ap = (AU && AU.points) || [];
      if (!ap.length) { g.fillStyle = soft; g.font = '11px ' + (cs.getPropertyValue('--mono') || 'monospace'); g.textAlign = 'center'; g.fillText(OVT.desk, w / 2, h / 2 + 4); return; }
      var step = Math.max(1, Math.floor(ap.length / 6000));
      for (var k2 = 0; k2 < ap.length; k2 += step) {
        var q2 = ap[k2], t = q2.th != null ? q2.th : 0.5, ca = [199, 127, 58], cb = [46, 138, 160];
        g.fillStyle = 'rgb(' + Math.round(ca[0] + (cb[0] - ca[0]) * t) + ',' + Math.round(ca[1] + (cb[1] - ca[1]) * t) + ',' + Math.round(ca[2] + (cb[2] - ca[2]) * t) + ')';
        g.globalAlpha = 0.6; g.beginPath(); g.arc(sx(q2.x), sy(q2.y), 1, 0, Math.PI * 2); g.fill();
      }
    } else if (m === 'sphere' || m === 'matrix' || m === 'tension') {
      var E = ents.slice().sort(function (a, b) { return (b.n || 0) - (a.n || 0); });
      var idx = {}; E.forEach(function (e, i) { idx[e.id] = i; });
      if (m === 'matrix') {
        var K = Math.min(22, E.length), cell = (Math.min(w, h) - 2 * pad) / Math.max(1, K), ox = (w - cell * K) / 2;
        for (var a1 = 0; a1 < K; a1++) for (var b1 = 0; b1 < K; b1++) {
          var wgt = 0; (E[a1].nb || []).forEach(function (nb) { if (nb[0] === E[b1].id) wgt = nb[1]; });
          if (a1 === b1) wgt = 0.12;
          if (!wgt) continue;
          g.fillStyle = palOf(E[a1].c); g.globalAlpha = Math.min(1, 0.15 + wgt * 6);
          g.fillRect(ox + b1 * cell, pad + a1 * cell, Math.max(1, cell - 1), Math.max(1, cell - 1));
        }
      } else if (m === 'sphere') {
        var K2 = Math.min(72, E.length), cx2 = w / 2, cy2 = h / 2, R3 = Math.min(w, h) * 0.44, pos = [];
        for (var i2 = 0; i2 < K2; i2++) { var an = i2 / K2 * Math.PI * 2; pos.push([cx2 + Math.cos(an) * R3 * 1.35, cy2 + Math.sin(an) * R3]); }
        g.strokeStyle = soft; g.lineWidth = 0.6; g.globalAlpha = 0.25;
        for (var i3 = 0; i3 < K2; i3++) (E[i3].nb || []).slice(0, 2).forEach(function (nb) { var j = idx[nb[0]]; if (j == null || j >= K2) return; g.beginPath(); g.moveTo(pos[i3][0], pos[i3][1]); g.lineTo(pos[j][0], pos[j][1]); g.stroke(); });
        g.globalAlpha = 0.9;
        for (var i4 = 0; i4 < K2; i4++) { g.fillStyle = palOf(E[i4].c); g.beginPath(); g.arc(pos[i4][0], pos[i4][1], 1.5 + Math.sqrt(E[i4].n || 1) / 8, 0, Math.PI * 2); g.fill(); }
      } else {
        var K3 = Math.min(40, E.length), base = h - pad - 4, xs = [];
        for (var i5 = 0; i5 < K3; i5++) xs.push(pad + i5 / Math.max(1, K3 - 1) * (w - 2 * pad));
        g.lineWidth = 0.8;
        for (var i6 = 0; i6 < K3; i6++) (E[i6].nb || []).slice(0, 3).forEach(function (nb) {
          var j = idx[nb[0]]; if (j == null || j >= K3 || j === i6) return;
          var x0 = xs[i6], x1 = xs[j], r = Math.abs(x1 - x0) / 2, cxm = (x0 + x1) / 2;
          g.strokeStyle = palOf(E[i6].c); g.globalAlpha = 0.25 + Math.min(0.6, nb[1] * 6);
          g.beginPath(); g.arc(cxm, base, r, Math.PI, 0); g.stroke();
        });
        g.globalAlpha = 0.9;
        for (var i7 = 0; i7 < K3; i7++) { g.fillStyle = palOf(E[i7].c); g.beginPath(); g.arc(xs[i7], base, 2, 0, Math.PI * 2); g.fill(); }
      }
    }
    g.globalAlpha = 1;
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
    // Где цвет означает кластер — показываем ряд точек с названиями групп; где не означает
    // (спектр, сфера и матрица на со-встречаемости) — легенда осталась бы обманом.
    if (state.mode === 'tree') { buildTree(); legendEl.innerHTML = clusterRow(); }
    else if (state.mode === 'spectrum') { buildSpectrum(); legendEl.innerHTML = ''; }
    else if (state.mode === 'sphere') { state.raw = state.data; buildSphere(); legendEl.innerHTML = ''; }
    else if (state.mode === 'mobius') { buildMobius(); legendEl.innerHTML = clusterRow(); }
    else if (state.mode === 'matrix') { state.raw = state.data; legendEl.innerHTML = ''; }
    else if (state.mode === 'heat') { buildHeat(); legendEl.innerHTML = clusterRow(); }
    else if (state.mode === 'fly') { legendEl.innerHTML = clusterRow(); }
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
    return palOf(p.c);
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
      // Шум в полосы не идёт (его нет в clusters), но раньше он задирал max и гасил
      // все остальные ячейки — они считались на фоне колонки, которой на картинке нет.
      if (isNoise(p.c)) return;
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
      .filter(function (c) { return !isNoise(c); })   // «вне групп» — не тема, ветвиться нечем
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
    ar: { x: 'دورة التكرار، أيام', y: 'قوة الإيقاع', days: 'ي' },
    fr: { x: 'période de répétition, jours', y: 'force du rythme', days: 'j' }
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
    if (state.shapes) drawHulls(proj);
    for (var k = 0; k < proj.length; k++) {
      var pr = proj[k];
      var fade = 0.35 + 0.65 * (1 - (pr.depth + 0.5));
      ctx.globalAlpha = Math.max(0.12, Math.min(1, fade * (state.ptAlpha || 1)));
      ctx.fillStyle = pr.color;
      var rr = pr.i === state.hover ? pr.r * 2.4 : pr.r * (state.ptScale || 1);
      // Форма несёт ту же информацию, что цвет. Владелец 13 августа: «я немного дальтоник —
      // придумать, чтобы был режим не ширины, а разной формы точки». Цвет остаётся, но
      // перестаёт быть единственным различителем: круг, квадрат, ромб, треугольник, звезда.
      if (state.shapes) markShape(pr.sx, pr.sy, rr, (state.pts[pr.i] && state.pts[pr.i].c) || 0);
      else { ctx.beginPath(); ctx.arc(pr.sx, pr.sy, rr, 0, 6.283); ctx.fill(); }
    }
    ctx.globalAlpha = 1;
    if (state.shapes) drawHullLabels(proj);
  }

  /* Пять различимых форм по номеру группы. Различимость проверяется не «на глаз в
     редакторе», а тем, что силуэты разной природы: круглое, угловатое, острое. */
  function markShape(x, y, r, c) {
    var s = ((c % 5) + 5) % 5;   // -1 % 5 === -1: без нормализации шум уезжал в «звезду»
    ctx.beginPath();
    if (s === 0) {                                   // круг
      ctx.arc(x, y, r, 0, 6.283);
    } else if (s === 1) {                            // квадрат
      ctx.rect(x - r, y - r, r * 2, r * 2);
    } else if (s === 2) {                            // ромб
      ctx.moveTo(x, y - r * 1.3); ctx.lineTo(x + r * 1.3, y);
      ctx.lineTo(x, y + r * 1.3); ctx.lineTo(x - r * 1.3, y);
    } else if (s === 3) {                            // треугольник
      ctx.moveTo(x, y - r * 1.4); ctx.lineTo(x + r * 1.25, y + r);
      ctx.lineTo(x - r * 1.25, y + r);
    } else {                                         // звезда
      for (var i = 0; i < 10; i++) {
        var ang = -1.5708 + i * 0.6283, rad = i % 2 ? r * 0.55 : r * 1.5;
        var px = x + Math.cos(ang) * rad, py = y + Math.sin(ang) * rad;
        if (i) ctx.lineTo(px, py); else ctx.moveTo(px, py);
      }
    }
    ctx.closePath();
    ctx.fill();
  }

  /* Границы групп полупрозрачной заливкой. Владелец 13 августа: «на визуалах с кластерами
     хорошо бы их границы полупрозрачными сферами обозначать и включать подписи».
     Рисуем не выпуклую оболочку (она цепляет случайные выбросы и превращается в кляксу),
     а круг вокруг центра группы радиусом в полтора среднего отклонения — так пятно
     показывает, где группа ЖИВЁТ, а не куда дотянулись её края. */
  function hulls(proj) {
    var by = {};
    proj.forEach(function (pr) {
      var c = (state.pts[pr.i] && state.pts[pr.i].c);
      if (c == null) return;
      (by[c] = by[c] || []).push(pr);
    });
    return Object.keys(by).map(function (c) {
      var g = by[c], n = g.length;
      var mx = g.reduce(function (s, p) { return s + p.sx; }, 0) / n;
      var my = g.reduce(function (s, p) { return s + p.sy; }, 0) / n;
      var sd = Math.sqrt(g.reduce(function (s, p) {
        return s + (p.sx - mx) * (p.sx - mx) + (p.sy - my) * (p.sy - my); }, 0) / n);
      return { c: +c, x: mx, y: my, r: Math.max(18, sd * 1.5), n: n };
    });
  }

  function drawHulls(proj) {
    hulls(proj).forEach(function (h) {
      ctx.globalAlpha = 0.10;
      ctx.fillStyle = PAL[h.c % PAL.length];
      ctx.beginPath(); ctx.arc(h.x, h.y, h.r, 0, 6.283); ctx.fill();
      ctx.globalAlpha = 0.35;
      ctx.strokeStyle = PAL[h.c % PAL.length];
      ctx.lineWidth = 1;
      ctx.stroke();
    });
    ctx.globalAlpha = 1;
  }

  function drawHullLabels(proj) {
    var hs = hulls(proj).sort(function (a, b) { return b.n - a.n; }).slice(0, 8);
    ctx.globalAlpha = 0.95;
    ctx.font = '600 11px ui-monospace, SFMono-Regular, Menlo, monospace';
    ctx.textAlign = 'center';
    hs.forEach(function (h) {
      var name = clusterTitle(h.c);
      if (!name) return;
      var w = ctx.measureText(name).width;
      ctx.fillStyle = 'rgba(12,16,24,.62)';
      ctx.beginPath();
      ctx.roundRect ? ctx.roundRect(h.x - w / 2 - 6, h.y - h.r - 20, w + 12, 16, 8)
                    : ctx.rect(h.x - w / 2 - 6, h.y - h.r - 20, w + 12, 16);
      ctx.fill();
      ctx.fillStyle = '#fff';
      ctx.fillText(name, h.x, h.y - h.r - 8);
    });
    ctx.globalAlpha = 1;
    ctx.textAlign = 'start';
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
  /* Компактная легенда — ряд точек с названиями групп. Карточки (.an-cards) слишком тяжелы для
     видов, где цвет лишь подсказка, а не предмет разговора, поэтому там легенду раньше просто
     стирали: у «дерева», «ленты», «тепла» и «полёта» цвет означал кластер, но что именно —
     нигде не было сказано. Стили (.lg-row/.lg-key/.lg-dot) лежали в CSS без применения. */
  /* Сколько точек в каждой группе — считаем по самим данным, а не по справочнику:
     справочник знает, КАК называется группа, но не сколько в ней работ сегодня. */
  function clusterCounts() {
    var n = {};
    ((state.data && state.data.points) || []).forEach(function (p) {
      if (p.c != null) n[p.c] = (n[p.c] || 0) + 1;
    });
    return n;
  }

  var SHAPE_CHAR = ['●', '■', '◆', '▲', '★'];

  /* Кластер -1 у карты v2 — не пропуск и не ошибка: HDBSCAN так говорит «работа не
     примыкает ни к одной плотной группе». Таких 40% корпуса, и это содержательный
     ответ, а не дыра. Но для кода это отрицательное число, и без единой трактовки
     оно ломается в восьми местах сразу: PAL[-1] undefined (точка рисуется цветом
     предыдущей), SHAPE_CHAR[-1] печатает 'undefined' в легенду, а «самая крупная
     группа» становится «#-1 — 40% архива». Поэтому одна функция на всех. */
  function isNoise(c) { return +c < 0; }
  var NOISE_COL = '#8A8A8A';
  function palOf(c) { return isNoise(c) ? NOISE_COL : PAL[((+c % PAL.length) + PAL.length) % PAL.length]; }
  function shapeOf(c) { return isNoise(c) ? '○' : SHAPE_CHAR[((+c % 5) + 5) % 5]; }

  function clusterRow() {
    var cl = (state.data && state.data.clusters) || {};
    var titles = state.data && state.data.titles;
    var keys = Object.keys(cl);
    if (!keys.length) return '';
    var cnt = clusterCounts();
    var items = keys.sort(function (a, b) { return (cnt[b] || 0) - (cnt[a] || 0); })
      .slice(0, 12).map(function (c) {
      var lt = titles && titles[c] ? (titles[c][LANG] || titles[c].en) : null;
      var name = lt ? lt.title : (cl[c] || []).map(niceLabel).slice(0, 2).join(' · ');
      // Число работ в группе и — если группа кликабельна — переход к их списку.
      // Владелец 13 августа: «каждый кластер это группа, хорошо бы количество статей
      // отобразить и в принципе перейти на список; возможно, это признак для фильтрации,
      // наряду с разделами».
      var n = cnt[c] || 0;
      var mark = state.shapes ? '<i class="lg-shape">' + shapeOf(c) + '</i>' : '';
      var body = mark + '<i class="lg-dot" style="background:' + palOf(c) + '"></i>' +
                 name + (n ? '<b class="lg-n">' + n + '</b>' : '');
      return clusterListable()
        ? '<a class="lg-key lg-link" href="javascript:void(0)" data-cluster="' + c + '">' + body + '</a>'
        : '<span class="lg-key">' + body + '</span>';
    }).join('');
    return '<div class="lg-row">' + items + '</div>';
  }

  /* Список статей группы имеет смысл там, где точка — это статья. На карте мира точка —
     область науки, и «перейти к статьям области» значило бы обещать список, которого у
     нас нет: в области могут лежать чужие работы, а не наши. */
  function clusterListable() {
    return state.mode === 'articles' || state.mode === 'mobius' || state.mode === 'fly'
        || state.mode === 'tree' || state.mode === 'heat';
  }

  /* Статьи выбранной группы — списком под картой, со ссылками. Данные уже загружены,
     ходить никуда не надо. */
  function showClusterList(c) {
    var pts = ((state.data && state.data.points) || []).filter(function (p) { return String(p.c) === String(c); });
    if (!pts.length) return;
    var titles = state.data.titles, lt = titles && titles[c] ? (titles[c][LANG] || titles[c].en) : null;
    var name = lt ? lt.title : ('#' + c);
    var box = document.getElementById('an-cluster-list');
    if (!box) {
      box = document.createElement('div');
      box.id = 'an-cluster-list';
      box.className = 'an-cluster-list';
      legendEl.parentNode.insertBefore(box, legendEl.nextSibling);
    }
    var rows = pts.slice(0, 200).map(function (p) {
      var t = p.t || p.id;
      return p.url ? '<a href="' + p.url + '">' + t + '</a>' : '<span>' + t + '</span>';
    }).join('');
    box.innerHTML = '<div class="an-cl-head"><b>' + name + '</b> · ' + pts.length + ' ' +
      (CL.arts || '') + (pts.length > 200 ? ' ' + (CL.first || '') : '') +
      '<button type="button" class="an-cl-x" aria-label="close">×</button></div>' +
      '<div class="an-cl-items">' + rows + '</div>';
    box.querySelector('.an-cl-x').onclick = function () { box.remove(); };
    box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  var CL = ({
    ru: { arts: 'статей в группе', first: '(показаны первые 200)' },
    en: { arts: 'papers in the group', first: '(first 200 shown)' },
    es: { arts: 'trabajos en el grupo', first: '(primeros 200)' },
    fr: { arts: 'travaux dans le groupe', first: '(les 200 premiers)' },
    ar: { arts: 'أعمال في المجموعة', first: '(أول 200)' }
  })[LANG] || { arts: 'papers in the group', first: '(first 200 shown)' };

  function renderLegend() {
    var cl = state.data.clusters || {};
    var titles = state.data.titles || null;   // человеческие названия от LLM-трактовщика (если посчитаны)
    var extra = state.mode === 'authors' ? '<div class="an-axis">' + T.theoryExp + '</div>' : '';
    // Кластеры — КАРТОЧКАМИ (юзер 2026-07-25): цветная полоса, название-заголовок, описание ниже.
    var cnt = clusterCounts();
    var listable = clusterListable();
    // Кластеров стало 60 вместо 24 — по порядку номеров это стена карточек, в которой
    // крупнейшая группа может оказаться в самом низу. Сортируем по числу работ.
    var items = Object.keys(cl).sort(function (a, b) { return (cnt[b] || 0) - (cnt[a] || 0); })
      .map(function (c) {
      var col = palOf(c);
      var lt = titles && titles[c] ? titles[c][LANG] || titles[c].en : null;
      var title = lt ? lt.title : (cl[c] || []).map(niceLabel).slice(0, 3).join(' · ');
      var desc = lt && lt.desc ? '<div class="an-card-d">' + lt.desc + '</div>' : '';
      // Сколько работ в группе — и вход в их список. Группа становится таким же признаком
      // отбора, как раздел arXiv (владелец 13 августа), а не просто цветом на картинке.
      var n = cnt[c] || 0;
      var shape = state.shapes ? '<i class="an-card-shape">' + shapeOf(c) + '</i>' : '';
      var num = n ? '<span class="an-card-n">' + n + '</span>' : '';
      var head = '<div class="an-card-t">' + shape + title + num + '</div>';
      var body = head + desc;
      return listable
        ? '<a class="an-card an-card-link" style="--cc:' + col + '" href="javascript:void(0)" data-cluster="' + c + '">' + body + '</a>'
        : '<div class="an-card" style="--cc:' + col + '">' + body + '</div>';
    }).join('');
    // Карточка «вне групп» — последней и без ссылки: список из двух тысяч работ, ничем
    // между собой не связанных, обещал бы читателю связь, которой нет.
    var loose = cnt[-1] || 0;
    if (loose && R.loose) {
      items += '<div class="an-card" style="--cc:' + NOISE_COL + '">'
             + '<div class="an-card-t">' + (state.shapes ? '<i class="an-card-shape">' + shapeOf(-1) + '</i>' : '')
             + R.loose + '<span class="an-card-n">' + loose + '</span></div>'
             + '<div class="an-card-d">' + R.looseWhy + '</div></div>';
    }
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
    // Остановленное вращение переживает переход между страницами: если человек его
    // выключил, значит оно ему мешает, и включать заново на каждой карте — навязчиво.
    try { localStorage.setItem('b42_an_spin', on ? '1' : '0'); } catch (e) {}
  }
  if (legendEl) legendEl.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('[data-cluster]');
    if (a) { e.preventDefault(); showClusterList(a.dataset.cluster); }
  });

  var spinBtn = document.getElementById('an-spin');
  if (spinBtn) spinBtn.addEventListener('click', function () { setSpin(!state.spin); });

  /* Формы вместо одного цвета. Выбор запоминаем: человеку, который различает цвета иначе,
     не должно приходиться включать это на каждой странице заново. По той же причине
     запоминаем и остановленное вращение — владелец 13 августа просил кнопку «стоп»,
     а она была, но безымянной иконкой и сбрасывалась при каждом заходе. */
  try {
    if (localStorage.getItem('b42_an_shapes') === '1') state.shapes = true;
    if (localStorage.getItem('b42_an_spin') === '0') state.spin = false;
  } catch (e) {}
  var shapesBtn = document.getElementById('an-shapes');
  function setShapes(on) {
    state.shapes = !!on;
    if (shapesBtn) {
      shapesBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
      shapesBtn.classList.toggle('on', !!on);
    }
    try { localStorage.setItem('b42_an_shapes', on ? '1' : '0'); } catch (e) {}
    draw();
  }
  if (shapesBtn) {
    shapesBtn.addEventListener('click', function () { setShapes(!state.shapes); });
    if (state.shapes) setShapes(true);
  }
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
    b.addEventListener('click', function (e) {
      if (e.target.closest('.ti')) { e.preventDefault(); return; }   // значок i — только подсказка
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
  // Стартовый вид — из адреса (#articles, #world…), иначе обзор.
  var VALID = ['overview', 'articles', 'world', 'authors', 'fly', 'heat', 'sphere', 'mobius', 'matrix', 'tree', 'spectrum', 'tension'];
  var h0 = location.hash.slice(1);
  var start = VALID.indexOf(h0) >= 0 ? h0 : 'overview';
  document.querySelectorAll('.an-tab').forEach(function (x) { x.classList.toggle('active', x.dataset.t === start); });
  load(start);
  window.addEventListener('hashchange', function () {
    var hm = location.hash.slice(1);
    if (VALID.indexOf(hm) >= 0 && hm !== state.mode) goTab(hm);
  });
})();
