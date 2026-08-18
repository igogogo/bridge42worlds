/* Интерфейс курса на 5 языках.
 *
 * Материалы уроков переведены внутри JSON (ветки ru/en/es/ar), но подписи интерфейса — оглавление,
 * кнопки, вердикты теста — жили в разметке по-русски. Отсюда правило: если язык не русский,
 * оставшаяся кириллица на странице курса — это заведомо интерфейс, а не контент. Поэтому словарь
 * бьётся по точному тексту узла: промахнуться по смыслу он не может.
 */
(function (global) {
    'use strict';

    var LANG = global.B42_LANG || 'ru';

    // Порядок значений: en, es, ar, fr (пятый язык добавлен tools/dict_lang.py)
    var DICT = {
        'bridge42worlds · дерево знаний': ['bridge42worlds · knowledge tree',
            'bridge42worlds · árbol del conocimiento', 'bridge42worlds · شجرة المعرفة', 'bridge42worlds · arbre de connaissances'],
        'Как работать с этим курсом · сколько времени займёт · опыты · материалы по теме': [
            'How to work through this course · how long it takes · experiments · further materials',
            'Cómo seguir este curso · cuánto tiempo lleva · experimentos · materiales del tema',
            'كيف تتقدّم في هذا المقرر · كم يستغرق · تجارب · مواد إضافية', 'Comment travailler ce cours · durée · expériences · ressources'],
        'Пройдено параграфов:': ['Paragraphs completed:', 'Párrafos completados:', 'الفقرات المنجزة:', 'Paragraphes terminés :'],
        'Анализ размерностей': ['Dimensional analysis', 'Análisis dimensional', 'التحليل البُعدي', 'Analyse dimensionnelle'],
        'Всемирное тяготение': ['Universal gravitation', 'Gravitación universal', 'الجذب العام', 'Gravitation universelle'],
        'Второе начало': ['Second law', 'Segundo principio', 'القانون الثاني', 'Deuxième principe'],
        'Вынужденные колебания': ['Driven oscillations', 'Oscilaciones forzadas', 'الاهتزازات القسرية', 'Oscillations forcées'],
        'Гипотеза Планка и фотоэффект': ['Planck hypothesis and the photoelectric effect', 'Hipótesis de Planck y efecto fotoeléctrico', 'فرضية بلانك والتأثير الكهروضوئي', 'Hypothèse de Planck et effet photoélectrique'],
        'Гипотеза де Бройля': ['De Broglie hypothesis', 'Hipótesis de De Broglie', 'فرضية دي برولي', 'Hypothèse de de Broglie'],
        'Закон Гука': ['Hooke’s law', 'Ley de Hooke', 'قانون هوك', 'Loi de Hooke'],
        'Закон Кулона': ['Coulomb’s law', 'Ley de Coulomb', 'قانون كولوم', 'Loi de Coulomb'],
        'Закон Ома': ['Ohm’s law', 'Ley de Ohm', 'قانون أوم', "Loi d'Ohm"],
        'Закон Снеллиуса': ['Snell’s law', 'Ley de Snell', 'قانون سنيل', 'Loi de Snell'],
        'Закон Фарадея': ['Faraday’s law', 'Ley de Faraday', 'قانون فاراداي', 'Loi de Faraday'],
        'Закон радиоактивного распада': ['Radioactive decay law', 'Ley de desintegración radiactiva', 'قانون الاضمحلال الإشعاعي', 'Loi de décroissance radioactive'],
        'Кинематика': ['Kinematics', 'Cinemática', 'علم الحركة', 'Cinématique'],
        'Клапейрон–Менделеев': ['Clapeyron–Mendeleev', 'Clapeyron–Mendeléiev', 'كلابيرون–مندليف', 'Clapeyron–Mendeleïev'],
        'Клаузиус–Клапейрон': ['Clausius–Clapeyron', 'Clausius–Clapeyron', 'كلاوزيوس–كلابيرون', 'Clausius–Clapeyron'],
        'Кривая энергии связи': ['Binding energy curve', 'Curva de energía de enlace', 'منحنى طاقة الترابط', "Courbe d'énergie de liaison"],
        'Напряжённость поля': ['Field strength', 'Intensidad del campo', 'شدة المجال', 'Intensité du champ'],
        'Первое начало · Карно': ['First law · Carnot', 'Primer principio · Carnot', 'القانون الأول · كارنو', 'Premier principe · Carnot'],
        'Постулаты Эйнштейна': ['Einstein’s postulates', 'Postulados de Einstein', 'مسلّمات أينشتاين', "Postulats d'Einstein"],
        'Потенциал и разность потенциалов': ['Potential and potential difference', 'Potencial y diferencia de potencial', 'الجهد وفرق الجهد', 'Potentiel et différence de potentiel'],
        'Преобразования Лоренца': ['Lorentz transformations', 'Transformaciones de Lorentz', 'تحويلات لورنتز', 'Transformations de Lorentz'],
        'Принцип Ландауэра': ['Landauer’s principle', 'Principio de Landauer', 'مبدأ لانداور', 'Principe de Landauer'],
        'Принцип запрета Паули': ['Pauli exclusion principle', 'Principio de exclusión de Pauli', 'مبدأ استبعاد باولي', "Principe d'exclusion de Pauli"],
        'Принцип моделирования': ['Modelling principle', 'Principio de modelado', 'مبدأ النمذجة', 'Principe de modélisation'],
        'Принцип суперпозиции': ['Superposition principle', 'Principio de superposición', 'مبدأ التراكب', 'Principe de superposition'],
        'Принцип эквивалентности': ['Equivalence principle', 'Principio de equivalencia', 'مبدأ التكافؤ', "Principe d'équivalence"],
        'Рассеяние Рэлея': ['Rayleigh scattering', 'Dispersión de Rayleigh', 'تشتت رايلي', 'Diffusion Rayleigh'],
        'Сила Лоренца': ['Lorentz force', 'Fuerza de Lorentz', 'قوة لورنتز', 'Force de Lorentz'],
        'Соотношение Гейзенберга': ['Heisenberg relation', 'Relación de Heisenberg', 'علاقة هايزنبرغ', "Relation d'Heisenberg"],
        'Сохранение импульса и энергии': ['Conservation of momentum and energy', 'Conservación del momento y la energía', 'حفظ الزخم والطاقة', "Conservation de l'impulsion et de l'énergie"],
        'Три закона Ньютона': ['Newton’s three laws', 'Las tres leyes de Newton', 'قوانين نيوتن الثلاثة', 'Trois lois de Newton'],
        'Уравнение Шрёдингера': ['Schrödinger equation', 'Ecuación de Schrödinger', 'معادلة شرودنغر', 'Équation de Schrödinger'],
        'Уравнения Максвелла': ['Maxwell’s equations', 'Ecuaciones de Maxwell', 'معادلات ماكسويل', 'Équations de Maxwell'],
        'Условие стоячей волны': ['Standing wave condition', 'Condición de onda estacionaria', 'شرط الموجة الموقوفة', "Condition d'onde stationnaire"],
        'Фазовое пространство': ['Phase space', 'Espacio de fases', 'فضاء الطور', 'Espace des phases'],
        'Формула Бальмера и постулаты Бора': ['Balmer formula and Bohr’s postulates', 'Fórmula de Balmer y postulados de Bohr', 'صيغة بالمر ومسلّمات بور', 'Formule de Balmer et postulats de Bohr'],
        'Центростремительное ускорение': ['Centripetal acceleration', 'Aceleración centrípeta', 'التسارع المركزي', 'Accélération centripète'],
        'Эквивалентность массы и энергии': ['Mass–energy equivalence', 'Equivalencia masa-energía', 'تكافؤ الكتلة والطاقة', 'Équivalence masse-énergie'],
        'Энергия орбиты': ['Orbital energy', 'Energía orbital', 'طاقة المدار', 'Énergie orbitale'],
        'Энергия связи': ['Binding energy', 'Energía de enlace', 'طاقة الترابط', 'Énergie de liaison'],
        'Итог:': ['Takeaway:', 'En resumen:', 'الخلاصة:', 'Bilan :'],
        'Теги:': ['Tags:', 'Etiquetas:', 'الوسوم:', 'Tags :'],
        'Законы:': ['Laws:', 'Leyes:', 'القوانين:', 'Lois :'],
        'Учёные:': ['Scientists:', 'Científicos:', 'العلماء:', 'Scientifiques :'],
        'Итог': ['Takeaway', 'En resumen', 'الخلاصة', 'Bilan'],
        'Четыре идеи проходят через весь курс. Встретив каждую заново, вы увидите её с другой стороны — и в этом смысл порядка тем.': ['Four ideas run through the whole course. Meeting each one again, you will see it from a new side — that is the point of the order of topics.', 'Cuatro ideas recorren todo el curso. Al reencontrar cada una, la verás desde otro ángulo: ese es el sentido del orden de los temas.', 'أربع أفكار تسري عبر المقرر كله. وحين تلتقي كلاً منها من جديد ستراها من زاوية أخرى — وهذا هو معنى ترتيب المواضيع.', "Quatre idées traversent tout le cours. En retrouvant chacune, vous la verrez sous un autre angle — c'est là le sens de l'ordre des sujets."],
        'Физика не закончена. Что такое время, почему растёт энтропия, как соединить гравитацию с квантами — и почему фазовое пространство оказывается языком для всего этого сразу. Читать можно в любой момент курса.': ['Physics is not finished. What time is, why entropy grows, how to join gravity with quanta — and why phase space turns out to be the language for all of it at once. Read this at any point in the course.', 'La física no está terminada. Qué es el tiempo, por qué crece la entropía, cómo unir la gravedad con los cuantos — y por qué el espacio de fases resulta ser el lenguaje de todo ello a la vez. Puede leerse en cualquier momento del curso.', 'الفيزياء لم تكتمل. ما الزمن، ولماذا تتزايد الإنتروبيا، وكيف نصل الجاذبية بالكمّ — ولماذا يتبيّن أن فضاء الطور هو لغة ذلك كله معاً. يمكن قراءته في أي وقت من المقرر.', "La physique n'est pas finie. Qu'est-ce que le temps, pourquoi l'entropie augmente, comment relier la gravité aux quanta — et pourquoi l'espace des phases se révèle être le langage pour tout cela à la fois. Lisez ceci à tout moment du cours."],
        'Темы открываются по мере готовности материала. Звёзды начисляются за качество прохождения проверок внутри параграфов: три — если ответили почти без ошибок, одна — за зачёт. Прогресс хранится в вашем браузере.': ['Topics open up as the material becomes ready. Stars are awarded for how well you pass the checks inside paragraphs: three for almost no mistakes, one for a pass. Progress is kept in your browser.', 'Los temas se abren a medida que el material está listo. Las estrellas se otorgan por la calidad de las comprobaciones dentro de los párrafos: tres si respondes casi sin errores, una por aprobar. El progreso se guarda en tu navegador.', 'تُفتح المواضيع تباعاً مع جهوز المادة. وتُمنح النجوم بحسب جودة اجتياز الاختبارات داخل الفقرات: ثلاث إن أجبت بلا أخطاء تقريباً، وواحدة عند النجاح. ويُحفظ تقدّمك في متصفحك.', "Les sujets s'ouvrent au fur et à mesure que le matériel est prêt. Les étoiles sont attribuées en fonction de la qualité de vos réponses aux vérifications dans les paragraphes : trois pour presque aucune erreur, une pour une réussite. La progression est conservée dans votre navigateur."],
        'Не удалось загрузить дерево': ['Could not load the tree', 'No se pudo cargar el árbol', 'تعذّر تحميل الشجرة', "Impossible de charger l'arbre"],
        'Обзорные лекции': ['Overview lectures', 'Lecciones panorámicas', 'محاضرات عامة', "Conférences d'aperçu"],
        'Введение': ['Introduction', 'Introducción', 'مقدمة', 'Introduction'],
        'Что нужно понимать': ['What to understand', 'Qué hay que entender', 'ما ينبغي فهمه', "Ce qu'il faut comprendre"],
        'Что означает каждый символ': ['What each symbol means', 'Qué significa cada símbolo', 'ماذا يعني كل رمز', 'Ce que signifie chaque symbole'],
        'Строгий вывод': ['Full derivation', 'Deducción rigurosa', 'الاشتقاق الكامل', 'Dérivation complète'],
        'Типовой расчёт': ['Worked example', 'Ejemplo resuelto', 'مثال محلول', 'Exemple résolu'],
        'Как запомнить': ['How to remember', 'Cómo recordarlo', 'كيف تتذكره', 'Comment retenir'],
        'Частая ошибка': ['Common mistake', 'Error frecuente', 'خطأ شائع', 'Erreur fréquente'],
        'Где это встречается': ['Where you meet it', 'Dónde aparece', 'أين نصادفه', 'Où on le rencontre'],
        'Проверка знаний': ['Knowledge check', 'Comprobación', 'اختبار المعرفة', 'Vérification des connaissances'],

        /* Реплики тьютора. Они печатаются текстом из JS (UI_STRINGS в course.html), а не лежат
           в разметке, поэтому в словарь их не завели: заголовок панели переводился, а первая
           строка внутри оставалась русской на всех языках (находка QA). Затравки вопроса тоже
           здесь — они уходят в чат от имени читателя. */
        'Спрашивайте что угодно по этому параграфу — объясню на пальцах.': [
            'Ask anything about this paragraph — I will explain it in plain words.',
            'Pregunte lo que quiera sobre este párrafo: se lo explico con palabras sencillas.',
            'اسأل أي شيء عن هذه الفقرة — سأشرحه ببساطة.',
            'Posez n’importe quelle question sur ce paragraphe — je l’expliquerai simplement.'],
        'Думаю…': ['Thinking…', 'Pensando…', '…أفكر', 'Je réfléchis…'],
        'Демо-режим: живой тьютор включается на сервере. Это заготовленная подсказка.': [
            'Demo mode: the live tutor runs on the server. This is a prepared hint.',
            'Modo demo: el tutor en vivo funciona en el servidor. Esta es una pista preparada.',
            'وضع تجريبي: المرشد المباشر يعمل على الخادم. هذه تلميحة جاهزة.',
            'Mode démo : le tuteur en direct fonctionne sur le serveur. Ceci est un indice préparé.'],
        'Живой тьютор сейчас не подключён.': [
            'The live tutor is not connected right now.',
            'El tutor en vivo no está conectado ahora mismo.',
            'المرشد المباشر غير متصل حالياً.',
            'Le tuteur en direct n’est pas connecté pour le moment.'],
        'Объясни глубже, почему это так: ': [
            'Explain in more depth why this is so: ',
            'Explica con más profundidad por qué es así: ',
            'اشرح بعمق أكبر لماذا الأمر كذلك: ',
            'Explique plus en profondeur pourquoi il en est ainsi : '],
        'Я ответил так: ': ['My answer was: ', 'Mi respuesta fue: ', 'كانت إجابتي: ', 'Ma réponse était : '],
        'Не понимаю, где ошибка. Вопрос: ': [
            'I do not see where the mistake is. The question: ',
            'No veo dónde está el error. La pregunta: ',
            'لا أرى أين الخطأ. السؤال: ',
            'Je ne vois pas où est l’erreur. La question : '],
        'Помоги прикинуть в уме, по шагам, не давая сразу число: ': [
            'Help me estimate it mentally, step by step, without giving the number away: ',
            'Ayúdame a estimarlo mentalmente, paso a paso, sin darme el número de golpe: ',
            'ساعدني على التقدير ذهنياً، خطوة بخطوة، دون أن تعطيني الرقم مباشرة: ',
            'Aide-moi à l’estimer de tête, étape par étape, sans donner le nombre tout de suite : '],

        // разбор ответа в квизе: подводка к пояснению и промах в единицах ответа
        'Как на самом деле:': ['How it actually works:', 'Cómo es en realidad:',
            'كيف الأمر في الحقيقة:', 'Ce qu’il en est vraiment :'],
        'вы промахнулись на': ['you were off by', 'te desviaste en', 'أخطأت بمقدار', 'vous vous êtes trompé de'],
        'Этот материал ещё не переведён на ваш язык — показан английский текст.': [
            'This material has not been translated into your language yet — showing the English text.',
            'Este material aún no está traducido a su idioma: se muestra el texto en inglés.',
            'لم تُترجم هذه المادة إلى لغتك بعد — يظهر النص الإنجليزي.',
            'Ce contenu n’est pas encore traduit dans votre langue — le texte anglais est affiché.'],
        'Этот материал ещё не переведён на ваш язык — показан русский текст.': [
            'This material has not been translated into your language yet — showing the Russian text.',
            'Este material aún no está traducido a su idioma: se muestra el texto en ruso.',
            'لم تُترجم هذه المادة إلى لغتك بعد — يظهر النص الروسي.',
            'Ce contenu n’est pas encore traduit dans votre langue — le texte russe est affiché.'],
        'развернуть в справочнике': ['open in the reference', 'ver en el compendio',
            'افتح في المرجع', 'ouvrir dans l’aide-mémoire'],
        'В курсе:': ['In the course:', 'En el curso:', 'في المقرر:', 'Dans le cours :'],
        'Вопросы': ['Questions', 'Preguntas', 'أسئلة', 'Questions'],
        // подписи шпаргалки: жили только в разметке memo.html и на всех языках были русскими
        'К параграфу': ['Back to the paragraph', 'Volver al párrafo', 'إلى الفقرة', 'Retour au paragraphe'],
        'Схема': ['Diagram', 'Esquema', 'مخطط', 'Schéma'],
        'Печать': ['Print', 'Imprimir', 'طباعة', 'Imprimer'],
        // третий заголовок оглавления «края известного»: два соседних в словаре были, этот забыли
        'Смысл': ['Why it matters', 'Sentido', 'المعنى', "Pourquoi c'est important"],
        'Проверьте себя': ['Test yourself', 'Ponte a prueba', 'اختبر نفسك', 'Testez-vous'],
        'Сквозные нити': ['Threads across topics', 'Hilos entre temas', 'خيوط جامعة', 'Fils conducteurs'],
        'Прикидка в уме': ['Mental estimate', 'Cálculo mental', 'تقدير ذهني', 'Estimation mentale'],
        'Прикиньте в уме — важен порядок': ['Estimate mentally — the order of magnitude matters',
            'Estima mentalmente: importa el orden de magnitud', 'قدّر ذهنياً — الرتبة هي المهمة', "Estimez mentalement — l'ordre de grandeur compte"],
        'Точное значение': ['Exact value', 'Valor exacto', 'القيمة الدقيقة', 'Valeur exacte'],
        'измеряемая величина': ['measurable quantity', 'magnitud medible', 'كمية قابلة للقياس', 'grandeur mesurable'],
        'Единицы:': ['Units:', 'Unidades:', 'الوحدات:', 'Unités :'],
        'Константы': ['Constants', 'Constantes', 'الثوابت', 'Constantes'],
        'Теги': ['Tags', 'Etiquetas', 'الوسوم', 'Étiquettes'],
        'Законы': ['Laws', 'Leyes', 'القوانين', 'Lois'],
        'Учёные': ['Scientists', 'Científicos', 'العلماء', 'Scientifiques'],
        'Темы': ['Topics', 'Temas', 'المواضيع', 'Sujets'],
        'Статьи по теме:': ['Articles on this topic:', 'Artículos sobre el tema:', 'مقالات في هذا الموضوع:', 'Articles sur ce sujet :'],
        'Тьютор': ['Tutor', 'Tutor', 'المرشد', 'Tuteur'],
        'Проверить': ['Check', 'Comprobar', 'تحقّق', 'Vérifier'],
        'Спросить': ['Ask', 'Preguntar', 'اسأل', 'Demander'],
        'Спросить глубже': ['Ask deeper', 'Preguntar más a fondo', 'اسأل بعمق', 'Demander plus en profondeur'],
        'Верно!': ['Correct!', '¡Correcto!', 'صحيح!', 'Correct !'],
        'Не совсем.': ['Not quite.', 'No exactamente.', 'ليس تماماً.', 'Pas tout à fait.'],
        'Порядок верный!': ['Right order of magnitude!', '¡Orden de magnitud correcto!', 'الرتبة صحيحة!', 'Bon ordre de grandeur !'],
        'Мимо порядка.': ['Off by an order of magnitude.', 'Fuera de orden de magnitud.', 'بعيد عن الرتبة.', "À côté d'un ordre de grandeur."],
        'вы промахнулись в': ['you were off by', 'te desviaste en', 'أخطأت بمقدار', 'vous êtes à côté de'],
        'Отлично — все вопросы верно.': ['Excellent — every answer correct.',
            'Excelente: todas las respuestas correctas.', 'ممتاز — كل الإجابات صحيحة.', 'Excellent — toutes les réponses sont correctes.'],
        'Хорошо, но пара мест требует возврата.': ['Good, but a couple of spots need another look.',
            'Bien, pero un par de puntos merecen un repaso.', 'جيد، لكن بضعة مواضع تحتاج مراجعة.', "Bon, mais quelques points méritent un second coup d'œil."],
        'Стоит перечитать вывод и покрутить стенд ещё раз.': [
            'Worth rereading the derivation and playing with the model again.',
            'Conviene releer la deducción y volver al simulador.',
            'يستحسن إعادة قراءة الاشتقاق وتجربة النموذج مرة أخرى.', 'Il vaut la peine de relire la dérivation et de jouer à nouveau avec le modèle.'],
        'Результат сохранён — он виден в оглавлении курса.': [
            'Result saved — it shows up in the course contents.',
            'Resultado guardado: aparece en el índice del curso.',
            'تم حفظ النتيجة — تظهر في فهرس المقرر.', 'Résultat enregistré — il apparaît dans la table des matières du cours.'],
        'Ответьте своими словами…': ['Answer in your own words…', 'Responde con tus palabras…', 'أجب بكلماتك…', 'Répondez avec vos propres mots…'],
        'Спросите о том, что не сходится…': ['Ask about whatever does not add up…',
            'Pregunta lo que no te encaja…', 'اسأل عمّا لا يتّضح لك…', 'Demandez ce qui ne colle pas…'],
        'Не понимаю — подведи к идее': ['I do not get it — walk me to the idea',
            'No lo entiendo: guíame hasta la idea', 'لم أفهم — قرّبني من الفكرة', "Je ne comprends pas — guidez-moi vers l'idée"],
        'ключевое': ['key', 'clave', 'أساسي', 'clé'],
        'ключевая': ['key', 'clave', 'أساسية', 'clé'],
        'Параграф пройден': ['Paragraph completed', 'Párrafo completado', 'تم إنجاز الفقرة', 'Paragraphe terminé'],
        'не пройден': ['not started', 'sin empezar', 'لم يبدأ', 'non commencé'],
        'звёзд собрано': ['stars earned', 'estrellas ganadas', 'نجوم مكتسبة', 'étoiles obtenues'],
        'начато вами': ['started by you', 'iniciados por ti', 'بدأتها', 'commencé par vous'],
        'Карточка-шпаргалка': ['Cheat sheet', 'Chuleta', 'بطاقة مراجعة', 'Aide-mémoire'],
        'шпаргалка': ['cheat sheet', 'chuleta', 'بطاقة مراجعة', 'aide-mémoire'],
        'дерево знаний': ['knowledge tree', 'árbol del conocimiento', 'شجرة المعرفة', 'arbre de connaissances'],
        'Дерево знаний': ['Knowledge tree', 'Árbol del conocimiento', 'شجرة المعرفة', 'Arbre de connaissances'],
        '← дерево знаний': ['← knowledge tree', '← árbol del conocimiento', '← شجرة المعرفة', '← arbre de connaissances'],
        '← открытые вопросы': ['← open questions', '← preguntas abiertas', '← الأسئلة المفتوحة', '← questions ouvertes'],
        'Открытые вопросы': ['Open questions', 'Preguntas abiertas', 'الأسئلة المفتوحة', 'Questions ouvertes'],
        '← К параграфу': ['← Back to the paragraph', '← Volver al párrafo', '← العودة إلى الفقرة', '← Retour au paragraphe'],
        // Ключи с эмодзи («🌳 Дерево знаний», «💬 Спросить тьютора», «🖨 Распечатать / PDF»)
        // убраны 2026-07-29: в разметке таких надписей давно нет, знак теперь ставит код из
        // нашего набора, а словарь искал совпадение по строке вместе с эмодзи и не находил.
        'Спросить тьютора': ['Ask the tutor', 'Preguntar al tutor', 'اسأل المرشد', 'Demander au tuteur'],
        'Распечатать / PDF': ['Print / PDF', 'Imprimir / PDF', 'طباعة / PDF', 'Imprimer / PDF'],
        'Язык физики': ['The language of physics', 'El lenguaje de la física', 'لغة الفيزياء', 'Langage de la physique'],
        'механика': ['mechanics', 'mecánica', 'الميكانيكا', 'mécanique'],
        'термодинамика': ['thermodynamics', 'termodinámica', 'الديناميكا الحرارية', 'thermodynamique'],
        'Термодинамика': ['Thermodynamics', 'Termodinámica', 'الديناميكا الحرارية', 'Thermodynamique'],
        'Интерактивный учебник на движке': ['Interactive textbook powered by',
            'Libro interactivo con el motor', 'كتاب تفاعلي بمحرك', 'Manuel interactif propulsé par'],
        'интерактивный учебник': ['interactive textbook', 'libro interactivo', 'كتاب تفاعلي', 'manuel interactif'],
        'в работе': ['in progress', 'en curso', 'قيد العمل', 'en cours'],
        'готова': ['ready', 'lista', 'جاهزة', 'prêt'],
        'скоро': ['soon', 'pronto', 'قريباً', 'bientôt'],
        'не решено': ['unsolved', 'sin resolver', 'لم يُحل', 'non résolu'],
        'не знаю': ['do not know', 'no lo sé', 'لا أعرف', 'Je ne sais pas'],
        'по разделу': ['in section', 'en la sección', 'في القسم', 'dans la section'],
        'Внимание.': ['Caution.', 'Atención.', 'تنبيه.', 'Attention.'],
        'Статус.': ['Status.', 'Estado.', 'الحالة.', 'Statut.'],
        'Разгадка.': ['The answer.', 'La clave.', 'الحل.', 'La réponse.'],
        'Дано': ['Given', 'Datos', 'المعطيات', 'Données'],
        'Закон': ['Law', 'Ley', 'القانون', 'Loi'],
        'Решение': ['Solution', 'Solución', 'الحل', 'Solution'],
        'Ответ': ['Answer', 'Respuesta', 'الإجابة', 'Réponse'],
        'Как запомнить:': ['How to remember:', 'Cómo recordarlo:', 'كيف تتذكره:', 'Comment retenir:'],
        'Не удалось загрузить материал': ['Could not load the material', 'No se pudo cargar el material',
            'تعذّر تحميل المادة', 'Impossible de charger le matériel'],

        /* ── Длинный параграф: оглавление, «наверх», закладка, экраны ошибок (аудит 6.2) ── */
        'Содержание параграфа': ['In this paragraph', 'Contenido del párrafo',
            'محتويات الفقرة', 'Sommaire du paragraphe'],
        'Наверх': ['Back to top', 'Volver arriba', 'إلى الأعلى', 'Haut de page'],
        'Опыт': ['Experiment', 'Experimento', 'التجربة', 'Expérience'],
        'Формула': ['Formula', 'Fórmula', 'الصيغة', 'Formule'],
        'Вы читали отсюда': ['You stopped reading here', 'Aquí dejaste la lectura',
            'توقّفت عن القراءة هنا', 'Vous vous êtes arrêté ici'],
        'Продолжить': ['Continue', 'Continuar', 'متابعة', 'Continuer'],
        'Закрыть': ['Close', 'Cerrar', 'إغلاق', 'Fermer'],
        'Такой темы нет': ['No such topic', 'No existe ese tema',
            'لا يوجد موضوع بهذا الاسم', 'Ce sujet n’existe pas'],
        'В адресе указана тема, которой в курсе нет: похоже, ссылка устарела или в ней опечатка.': [
            'The address points to a topic the course does not have — the link is probably outdated or misspelled.',
            'La dirección apunta a un tema que el curso no tiene: seguramente el enlace está obsoleto o mal escrito.',
            'يشير العنوان إلى موضوع غير موجود في المقرر: على الأرجح أنّ الرابط قديم أو به خطأ إملائي.',
            'L’adresse pointe vers un sujet absent du cours : le lien est sans doute périmé ou mal orthographié.'],
        'Такого параграфа нет': ['No such paragraph', 'No existe ese párrafo',
            'لا توجد فقرة بهذا الاسم', 'Ce paragraphe n’existe pas'],
        'В этой теме нет параграфа с таким адресом. Вот всё, что в ней есть:': [
            'This topic has no paragraph at that address. Here is everything it does have:',
            'Este tema no tiene ningún párrafo en esa dirección. Esto es todo lo que contiene:',
            'لا تحتوي هذه المادة على فقرة بهذا العنوان، وهذا كل ما فيها:',
            'Ce sujet ne contient aucun paragraphe à cette adresse. Voici tout ce qu’il contient :'],
        'Темы курса': ['Course topics', 'Temas del curso', 'مواضيع المقرر', 'Sujets du cours'],
        'Открыть дерево знаний': ['Open the knowledge tree', 'Abrir el árbol del conocimiento',
            'افتح شجرة المعرفة', 'Ouvrir l’arbre de connaissances'],
        'Похоже, оборвалась связь с сервером. Обновите страницу — обычно этого хватает.': [
            'The connection to the server seems to have dropped. Reload the page — that usually settles it.',
            'Parece que se perdió la conexión con el servidor. Recarga la página: suele bastar con eso.',
            'يبدو أنّ الاتصال بالخادم قد انقطع. أعد تحميل الصفحة — عادةً ما يكفي ذلك.',
            'La connexion au serveur semble interrompue. Rechargez la page — cela suffit en général.'],
        'Обновить страницу': ['Reload the page', 'Recargar la página',
            'إعادة تحميل الصفحة', 'Recharger la page'],
        'Подробности для разработчика': ['Technical details', 'Detalles técnicos',
            'تفاصيل تقنية', 'Détails techniques'],

        'Не удалось загрузить учебник': ['Could not load the textbook', 'No se pudo cargar el libro',
            'تعذّر تحميل الكتاب', 'Impossible de charger le manuel'],
        'Не удалось загрузить данные:': ['Could not load the data:', 'No se pudieron cargar los datos:',
            'تعذّر تحميل البيانات:', 'Impossible de charger les données:'],
        'Не удалось загрузить лекцию:': ['Could not load the lecture:', 'No se pudo cargar la lección:',
            'تعذّر تحميل المحاضرة:', 'Impossible de charger la leçon:'],
        'Не удалось загрузить карточку:': ['Could not load the card:', 'No se pudo cargar la ficha:',
            'تعذّر تحميل البطاقة:', 'Impossible de charger la fiche:'],
        'Курс': ['Course', 'Curso', 'المقرر', 'Cours'],
        'Лекция': ['Lecture', 'Lección', 'محاضرة', 'Leçon'],
        'опирается на:': ['builds on:', 'se apoya en:', 'يعتمد على:', "s'appuie sur:"],
        'Связано с курсом:': ['Linked to the course:', 'Vinculado al curso:', 'مرتبط بالمقرر:', 'Lié au cours:'],
        'Как работать с этим курсом': ['How to work through this course', 'Cómo seguir este curso',
            'كيف تتقدّم في هذا المقرر', 'Comment travailler ce cours'],
        'сколько времени': ['how long it takes', 'cuánto tiempo lleva', 'كم يستغرق', 'combien de temps']
    };

    // Шаблоны с числом: «Тема 3», «Параграф 1 · параграф 2 из 3»
    // и приставки, к которым приклеен уже переведённый хвост («опирается на: Mecánica»)
    var RULES = [
        [/^опирается на:\s*/, { en: 'builds on: ', es: 'se apoya en: ', ar: 'يعتمد على: ', fr: 'repose sur : ' }],
        [/^Связано с курсом:\s*/, { en: 'Linked to the course: ', es: 'Vinculado al curso: ',
            ar: 'مرتبط بالمقرر: ', fr: 'Lié au cours : ' }],
        [/^Пройдено параграфов:\s*/, { en: 'Paragraphs completed: ', es: 'Párrafos completados: ',
            ar: 'الفقرات المنجزة: ', fr: 'Paragraphes terminés : ' }],
        [/^Итог:\s*/, { en: 'Takeaway: ', es: 'En resumen: ', ar: 'الخلاصة: ', fr: 'Bilan : ' }],
        [/^Тема\s+(\d+)/, { en: 'Topic $1', es: 'Tema $1', ar: 'الموضوع $1', fr: 'Sujet $1' }],
        [/^Параграф\s+(\d+)/, { en: 'Paragraph $1', es: 'Párrafo $1', ar: 'الفقرة $1', fr: 'Paragraphe $1' }],
        [/^(\d+)\s+из\s+(\d+)$/, { en: '$1 of $2', es: '$1 de $2', ar: '$1 من $2', fr: '$1 sur $2' }],
        [/^тем открыто из\s*/, { en: 'topics opened of ', es: 'temas abiertos de ', ar: 'مواضيع مفتوحة من ', fr: 'sujets ouverts sur ' }],
        [/·\s*параграф\s+(\d+)/, { en: '· paragraph $1', es: '· párrafo $1', ar: '· فقرة $1', fr: '· paragraphe $1' }]
    ];

    var IDX = { en: 0, es: 1, ar: 2, fr: 3 };

    function tr(text) {
        var key = (text || '').trim();
        if (!key) return null;
        var hit = DICT[key];
        // Нет перевода для этого языка — возвращаем null, то есть «оставить как есть». Раньше
        // отдавалось hit[undefined], и в тексте страницы появлялось слово «undefined»: ровно так
        // выглядела страница на пятом языке, пока браузер держал в кэше старую версию словаря.
        if (hit) {
            var v = hit[IDX[LANG]];
            return typeof v === 'string' && v ? v : null;
        }
        for (var i = 0; i < RULES.length; i++) {
            if (RULES[i][0].test(key)) {
                return key.replace(RULES[i][0], RULES[i][1][LANG]);
            }
        }
        return null;
    }

    /** Переводит подписи интерфейса внутри поддерева. Контент уроков не трогает: он уже на нужном
     *  языке, а значит под ключи словаря не попадает. */
    function translate(root) {
        if (LANG === 'ru') return;
        var walker = document.createTreeWalker(root || document.body, NodeFilter.SHOW_TEXT, null);
        var node, pending = [];
        while ((node = walker.nextNode())) {
            if (node.parentNode && /^(SCRIPT|STYLE|CODE)$/.test(node.parentNode.nodeName)) continue;
            var val = node.nodeValue;
            if (!/[а-яА-ЯёЁ]{2,}/.test(val)) continue;
            var out = tr(val);
            if (out !== null) pending.push([node, val.replace(val.trim(), out)]);
        }
        pending.forEach(function (p) { p[0].nodeValue = p[1]; });

        // подписи, живущие в атрибутах
        ['title', 'placeholder', 'aria-label', 'alt'].forEach(function (attr) {
            var els = (root || document).querySelectorAll('[' + attr + ']');
            Array.prototype.forEach.call(els, function (el) {
                var v = el.getAttribute(attr);
                if (!/[а-яА-ЯёЁ]{2,}/.test(v || '')) return;
                var o = tr(v);
                if (o !== null) el.setAttribute(attr, o);
            });
        });
    }

    function translateTitle() {
        if (LANG === 'ru') return;
        var t = document.title;
        Object.keys(DICT).forEach(function (k) {
            if (t.indexOf(k) === 0) t = DICT[k][IDX[LANG]] + t.slice(k.length);
        });
        document.title = t;
    }

    /* Переключатель языков в шапке — рисуем здесь, а не в каждой странице отдельно.
       Раньше его вставлял скрипт по списку файлов, и четыре новых справочника в список не попали:
       материалы переведены, а сменить язык нечем (юзер 2026-07-28). Теперь достаточно подключить
       этот файл — переключатель появится сам. */
    function mountSwitcher() {
        var bar = document.querySelector('.top-bar, .topnav, .bar');
        if (!bar || document.getElementById('course-langs')) return;
        var wrap = document.createElement('div');
        wrap.className = 'langs';
        wrap.id = 'course-langs';
        ['ru', 'en', 'es', 'ar', 'fr'].forEach(function (l) {
            var a = document.createElement('a');
            // сохраняем текущий адрес и параметры, меняем только язык
            var qs = new URLSearchParams(location.search);
            qs.set('lang', l);
            a.href = location.pathname + '?' + qs.toString() + location.hash;
            a.textContent = l.toUpperCase();
            if (l === LANG) a.className = 'active';
            a.addEventListener('click', function () {
                try { localStorage.setItem('b42_lang', l); } catch (e) {}
            });
            wrap.appendChild(a);
        });
        bar.appendChild(wrap);
    }

    /* Логотип учебных страниц статичен и потому всегда вёл на русскую главную. Подставляем
       текущий язык здесь, а не в десяти файлах: тот же приём, что и с переключателем. */
    function fixHomeLink() {
        Array.prototype.forEach.call(document.querySelectorAll('a.logo'), function (a) {
            if (/^\/lang\/[a-z]{2}\/index\.html$/.test(a.getAttribute('href') || '')) {
                a.href = '/lang/' + LANG + '/index.html';
            }
        });
    }

    function start() {
        mountSwitcher();
        fixHomeLink();
        if (LANG === 'ru') return;
        translate(document.body);
        translateTitle();
        // страницы курса дорисовывают оглавление и карточки после загрузки JSON
        var mo = new MutationObserver(function (muts) {
            muts.forEach(function (m) {
                Array.prototype.forEach.call(m.addedNodes, function (n) {
                    if (n.nodeType === 1) translate(n);
                    else if (n.nodeType === 3) {
                        var o = tr(n.nodeValue);
                        if (o !== null) n.nodeValue = n.nodeValue.replace(n.nodeValue.trim(), o);
                    }
                });
            });
        });
        mo.observe(document.body, { childList: true, subtree: true });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', start);
    } else {
        start();
    }

    /* ── Ветка материала на языке страницы ──────────────────────────────────────────
       Материалы переводятся не мгновенно: пятый язык сейчас есть у одной темы из
       шестнадцати. Раньше страницы писали `d[LANG] || d.ru` — то есть француз получал
       русский текст во французской рамке и НИКАКОГО предупреждения. Это ровно тот
       молчаливый откат, который мы вычищаем из генератора: читатель не понимает, это
       так задумано или сломалось.

       Теперь: сначала язык страницы, потом английский, только потом русский —
       латиница читается шире кириллицы, — и один раз на страницу показывается честная
       плашка «переведено не всё». */
    var FALLBACK_ORDER = ['en', 'ru'];
    var noticeShown = false;

    function showFallbackNotice(shownLang) {
        if (noticeShown || LANG === 'ru') return;
        noticeShown = true;
        var say = function () {
            if (!document.body || document.getElementById('b42-lang-notice')) return;
            var box = document.createElement('div');
            box.id = 'b42-lang-notice';
            box.style.cssText = 'max-width:680px;margin:10px auto 0;padding:9px 14px;border-radius:10px;' +
                'font-size:13px;line-height:1.5;background:var(--tag-bg,#eee);color:var(--muted,#555);' +
                'border:1px solid var(--border,#ddd)';
            box.textContent = shownLang === 'en'
                ? 'Этот материал ещё не переведён на ваш язык — показан английский текст.'
                : 'Этот материал ещё не переведён на ваш язык — показан русский текст.';
            document.body.insertBefore(box, document.body.firstChild);
            translate(box);
        };
        if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', say);
        else say();
    }

    /** Достаёт языковую ветку с честным откатом. Возвращает null, если веток нет вовсе. */
    function pick(obj) {
        if (!obj || typeof obj !== 'object') return obj;
        if (obj[LANG]) return obj[LANG];
        for (var i = 0; i < FALLBACK_ORDER.length; i++) {
            var l = FALLBACK_ORDER[i];
            if (obj[l]) { showFallbackNotice(l); return obj[l]; }
        }
        return null;
    }

    global.B42Lang = { pick: pick, current: function () { return LANG; } };
    global.B42_T = tr;
})(window);
