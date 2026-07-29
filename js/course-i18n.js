/* Интерфейс курса на 4 языках.
 *
 * Материалы уроков переведены внутри JSON (ветки ru/en/es/ar), но подписи интерфейса — оглавление,
 * кнопки, вердикты теста — жили в разметке по-русски. Отсюда правило: если язык не русский,
 * оставшаяся кириллица на странице курса — это заведомо интерфейс, а не контент. Поэтому словарь
 * бьётся по точному тексту узла: промахнуться по смыслу он не может.
 */
(function (global) {
    'use strict';

    var LANG = global.B42_LANG || 'ru';

    // Порядок значений: en, es, ar
    var DICT = {
        'bridge42worlds · дерево знаний': ['bridge42worlds · knowledge tree',
            'bridge42worlds · árbol del conocimiento', 'bridge42worlds · شجرة المعرفة'],
        'Как работать с этим курсом · сколько времени займёт · опыты · материалы по теме': [
            'How to work through this course · how long it takes · experiments · further materials',
            'Cómo seguir este curso · cuánto tiempo lleva · experimentos · materiales del tema',
            'كيف تتقدّم في هذا المقرر · كم يستغرق · تجارب · مواد إضافية'],
        'Пройдено параграфов:': ['Paragraphs completed:', 'Párrafos completados:', 'الفقرات المنجزة:'],
        'Анализ размерностей': ['Dimensional analysis', 'Análisis dimensional', 'التحليل البُعدي'],
        'Всемирное тяготение': ['Universal gravitation', 'Gravitación universal', 'الجذب العام'],
        'Второе начало': ['Second law', 'Segundo principio', 'القانون الثاني'],
        'Вынужденные колебания': ['Driven oscillations', 'Oscilaciones forzadas', 'الاهتزازات القسرية'],
        'Гипотеза Планка и фотоэффект': ['Planck hypothesis and the photoelectric effect', 'Hipótesis de Planck y efecto fotoeléctrico', 'فرضية بلانك والتأثير الكهروضوئي'],
        'Гипотеза де Бройля': ['De Broglie hypothesis', 'Hipótesis de De Broglie', 'فرضية دي برولي'],
        'Закон Гука': ['Hooke’s law', 'Ley de Hooke', 'قانون هوك'],
        'Закон Кулона': ['Coulomb’s law', 'Ley de Coulomb', 'قانون كولوم'],
        'Закон Ома': ['Ohm’s law', 'Ley de Ohm', 'قانون أوم'],
        'Закон Снеллиуса': ['Snell’s law', 'Ley de Snell', 'قانون سنيل'],
        'Закон Фарадея': ['Faraday’s law', 'Ley de Faraday', 'قانون فاراداي'],
        'Закон радиоактивного распада': ['Radioactive decay law', 'Ley de desintegración radiactiva', 'قانون الاضمحلال الإشعاعي'],
        'Кинематика': ['Kinematics', 'Cinemática', 'علم الحركة'],
        'Клапейрон–Менделеев': ['Clapeyron–Mendeleev', 'Clapeyron–Mendeléiev', 'كلابيرون–مندليف'],
        'Клаузиус–Клапейрон': ['Clausius–Clapeyron', 'Clausius–Clapeyron', 'كلاوزيوس–كلابيرون'],
        'Кривая энергии связи': ['Binding energy curve', 'Curva de energía de enlace', 'منحنى طاقة الترابط'],
        'Напряжённость поля': ['Field strength', 'Intensidad del campo', 'شدة المجال'],
        'Первое начало · Карно': ['First law · Carnot', 'Primer principio · Carnot', 'القانون الأول · كارنو'],
        'Постулаты Эйнштейна': ['Einstein’s postulates', 'Postulados de Einstein', 'مسلّمات أينشتاين'],
        'Потенциал и разность потенциалов': ['Potential and potential difference', 'Potencial y diferencia de potencial', 'الجهد وفرق الجهد'],
        'Преобразования Лоренца': ['Lorentz transformations', 'Transformaciones de Lorentz', 'تحويلات لورنتز'],
        'Принцип Ландауэра': ['Landauer’s principle', 'Principio de Landauer', 'مبدأ لانداور'],
        'Принцип запрета Паули': ['Pauli exclusion principle', 'Principio de exclusión de Pauli', 'مبدأ استبعاد باولي'],
        'Принцип моделирования': ['Modelling principle', 'Principio de modelado', 'مبدأ النمذجة'],
        'Принцип суперпозиции': ['Superposition principle', 'Principio de superposición', 'مبدأ التراكب'],
        'Принцип эквивалентности': ['Equivalence principle', 'Principio de equivalencia', 'مبدأ التكافؤ'],
        'Рассеяние Рэлея': ['Rayleigh scattering', 'Dispersión de Rayleigh', 'تشتت رايلي'],
        'Сила Лоренца': ['Lorentz force', 'Fuerza de Lorentz', 'قوة لورنتز'],
        'Соотношение Гейзенберга': ['Heisenberg relation', 'Relación de Heisenberg', 'علاقة هايزنبرغ'],
        'Сохранение импульса и энергии': ['Conservation of momentum and energy', 'Conservación del momento y la energía', 'حفظ الزخم والطاقة'],
        'Три закона Ньютона': ['Newton’s three laws', 'Las tres leyes de Newton', 'قوانين نيوتن الثلاثة'],
        'Уравнение Шрёдингера': ['Schrödinger equation', 'Ecuación de Schrödinger', 'معادلة شرودنغر'],
        'Уравнения Максвелла': ['Maxwell’s equations', 'Ecuaciones de Maxwell', 'معادلات ماكسويل'],
        'Условие стоячей волны': ['Standing wave condition', 'Condición de onda estacionaria', 'شرط الموجة الموقوفة'],
        'Фазовое пространство': ['Phase space', 'Espacio de fases', 'فضاء الطور'],
        'Формула Бальмера и постулаты Бора': ['Balmer formula and Bohr’s postulates', 'Fórmula de Balmer y postulados de Bohr', 'صيغة بالمر ومسلّمات بور'],
        'Центростремительное ускорение': ['Centripetal acceleration', 'Aceleración centrípeta', 'التسارع المركزي'],
        'Эквивалентность массы и энергии': ['Mass–energy equivalence', 'Equivalencia masa-energía', 'تكافؤ الكتلة والطاقة'],
        'Энергия орбиты': ['Orbital energy', 'Energía orbital', 'طاقة المدار'],
        'Энергия связи': ['Binding energy', 'Energía de enlace', 'طاقة الترابط'],
        'Итог:': ['Takeaway:', 'En resumen:', 'الخلاصة:'],
        'Теги:': ['Tags:', 'Etiquetas:', 'الوسوم:'],
        'Законы:': ['Laws:', 'Leyes:', 'القوانين:'],
        'Учёные:': ['Scientists:', 'Científicos:', 'العلماء:'],
        'Итог': ['Takeaway', 'En resumen', 'الخلاصة'],
        'Четыре идеи проходят через весь курс. Встретив каждую заново, вы увидите её с другой стороны — и в этом смысл порядка тем.': ['Four ideas run through the whole course. Meeting each one again, you will see it from a new side — that is the point of the order of topics.', 'Cuatro ideas recorren todo el curso. Al reencontrar cada una, la verás desde otro ángulo: ese es el sentido del orden de los temas.', 'أربع أفكار تسري عبر المقرر كله. وحين تلتقي كلاً منها من جديد ستراها من زاوية أخرى — وهذا هو معنى ترتيب المواضيع.'],
        'Физика не закончена. Что такое время, почему растёт энтропия, как соединить гравитацию с квантами — и почему фазовое пространство оказывается языком для всего этого сразу. Читать можно в любой момент курса.': ['Physics is not finished. What time is, why entropy grows, how to join gravity with quanta — and why phase space turns out to be the language for all of it at once. Read this at any point in the course.', 'La física no está terminada. Qué es el tiempo, por qué crece la entropía, cómo unir la gravedad con los cuantos — y por qué el espacio de fases resulta ser el lenguaje de todo ello a la vez. Puede leerse en cualquier momento del curso.', 'الفيزياء لم تكتمل. ما الزمن، ولماذا تتزايد الإنتروبيا، وكيف نصل الجاذبية بالكمّ — ولماذا يتبيّن أن فضاء الطور هو لغة ذلك كله معاً. يمكن قراءته في أي وقت من المقرر.'],
        'Темы открываются по мере готовности материала. Звёзды начисляются за качество прохождения проверок внутри параграфов: три — если ответили почти без ошибок, одна — за зачёт. Прогресс хранится в вашем браузере.': ['Topics open up as the material becomes ready. Stars are awarded for how well you pass the checks inside paragraphs: three for almost no mistakes, one for a pass. Progress is kept in your browser.', 'Los temas se abren a medida que el material está listo. Las estrellas se otorgan por la calidad de las comprobaciones dentro de los párrafos: tres si respondes casi sin errores, una por aprobar. El progreso se guarda en tu navegador.', 'تُفتح المواضيع تباعاً مع جهوز المادة. وتُمنح النجوم بحسب جودة اجتياز الاختبارات داخل الفقرات: ثلاث إن أجبت بلا أخطاء تقريباً، وواحدة عند النجاح. ويُحفظ تقدّمك في متصفحك.'],
        'Не удалось загрузить дерево': ['Could not load the tree', 'No se pudo cargar el árbol', 'تعذّر تحميل الشجرة'],
        'Обзорные лекции': ['Overview lectures', 'Lecciones panorámicas', 'محاضرات عامة'],
        'Открытые вопросы': ['Open questions', 'Preguntas abiertas', 'الأسئلة المفتوحة'],
        'Введение': ['Introduction', 'Introducción', 'مقدمة'],
        'Что нужно понимать': ['What to understand', 'Qué hay que entender', 'ما ينبغي فهمه'],
        'Что означает каждый символ': ['What each symbol means', 'Qué significa cada símbolo', 'ماذا يعني كل رمز'],
        'Строгий вывод': ['Full derivation', 'Deducción rigurosa', 'الاشتقاق الكامل'],
        'Типовой расчёт': ['Worked example', 'Ejemplo resuelto', 'مثال محلول'],
        'Как запомнить': ['How to remember', 'Cómo recordarlo', 'كيف تتذكره'],
        'Частая ошибка': ['Common mistake', 'Error frecuente', 'خطأ شائع'],
        'Где это встречается': ['Where you meet it', 'Dónde aparece', 'أين نصادفه'],
        'Проверка знаний': ['Knowledge check', 'Comprobación', 'اختبار المعرفة'],
        'Вопросы': ['Questions', 'Preguntas', 'أسئلة'],
        'Проверьте себя': ['Test yourself', 'Ponte a prueba', 'اختبر نفسك'],
        'Сквозные нити': ['Threads across topics', 'Hilos entre temas', 'خيوط جامعة'],
        'Прикидка в уме': ['Mental estimate', 'Cálculo mental', 'تقدير ذهني'],
        'Прикиньте в уме — важен порядок': ['Estimate mentally — the order of magnitude matters',
            'Estima mentalmente: importa el orden de magnitud', 'قدّر ذهنياً — الرتبة هي المهمة'],
        'Точное значение': ['Exact value', 'Valor exacto', 'القيمة الدقيقة'],
        'измеряемая величина': ['measurable quantity', 'magnitud medible', 'كمية قابلة للقياس'],
        'Единицы:': ['Units:', 'Unidades:', 'الوحدات:'],
        'Константы': ['Constants', 'Constantes', 'الثوابت'],
        'Теги': ['Tags', 'Etiquetas', 'الوسوم'],
        'Законы': ['Laws', 'Leyes', 'القوانين'],
        'Учёные': ['Scientists', 'Científicos', 'العلماء'],
        'Темы': ['Topics', 'Temas', 'المواضيع'],
        'Статьи по теме:': ['Articles on this topic:', 'Artículos sobre el tema:', 'مقالات في هذا الموضوع:'],
        'Тьютор': ['Tutor', 'Tutor', 'المرشد'],
        'Проверить': ['Check', 'Comprobar', 'تحقّق'],
        'Спросить': ['Ask', 'Preguntar', 'اسأل'],
        'Спросить глубже': ['Ask deeper', 'Preguntar más a fondo', 'اسأل بعمق'],
        'Верно!': ['Correct!', '¡Correcto!', 'صحيح!'],
        'Не совсем.': ['Not quite.', 'No exactamente.', 'ليس تماماً.'],
        'Порядок верный!': ['Right order of magnitude!', '¡Orden de magnitud correcto!', 'الرتبة صحيحة!'],
        'Мимо порядка.': ['Off by an order of magnitude.', 'Fuera de orden de magnitud.', 'بعيد عن الرتبة.'],
        'вы промахнулись в': ['you were off by', 'te desviaste en', 'أخطأت بمقدار'],
        'Отлично — все вопросы верно.': ['Excellent — every answer correct.',
            'Excelente: todas las respuestas correctas.', 'ممتاز — كل الإجابات صحيحة.'],
        'Хорошо, но пара мест требует возврата.': ['Good, but a couple of spots need another look.',
            'Bien, pero un par de puntos merecen un repaso.', 'جيد، لكن بضعة مواضع تحتاج مراجعة.'],
        'Стоит перечитать вывод и покрутить стенд ещё раз.': [
            'Worth rereading the derivation and playing with the model again.',
            'Conviene releer la deducción y volver al simulador.',
            'يستحسن إعادة قراءة الاشتقاق وتجربة النموذج مرة أخرى.'],
        'Результат сохранён — он виден в оглавлении курса.': [
            'Result saved — it shows up in the course contents.',
            'Resultado guardado: aparece en el índice del curso.',
            'تم حفظ النتيجة — تظهر في فهرس المقرر.'],
        'Ответьте своими словами…': ['Answer in your own words…', 'Responde con tus palabras…', 'أجب بكلماتك…'],
        'Спросите о том, что не сходится…': ['Ask about whatever does not add up…',
            'Pregunta lo que no te encaja…', 'اسأل عمّا لا يتّضح لك…'],
        'Не понимаю — подведи к идее': ['I do not get it — walk me to the idea',
            'No lo entiendo: guíame hasta la idea', 'لم أفهم — قرّبني من الفكرة'],
        'ключевое': ['key', 'clave', 'أساسي'],
        'ключевая': ['key', 'clave', 'أساسية'],
        'Параграф пройден': ['Paragraph completed', 'Párrafo completado', 'تم إنجاز الفقرة'],
        'не пройден': ['not started', 'sin empezar', 'لم يبدأ'],
        'звёзд собрано': ['stars earned', 'estrellas ganadas', 'نجوم مكتسبة'],
        'начато вами': ['started by you', 'iniciados por ti', 'بدأتها'],
        'Карточка-шпаргалка': ['Cheat sheet', 'Chuleta', 'بطاقة مراجعة'],
        'шпаргалка': ['cheat sheet', 'chuleta', 'بطاقة مراجعة'],
        'дерево знаний': ['knowledge tree', 'árbol del conocimiento', 'شجرة المعرفة'],
        '🌳 Дерево знаний': ['🌳 Knowledge tree', '🌳 Árbol del conocimiento', '🌳 شجرة المعرفة'],
        'Дерево знаний': ['Knowledge tree', 'Árbol del conocimiento', 'شجرة المعرفة'],
        '← дерево знаний': ['← knowledge tree', '← árbol del conocimiento', '← شجرة المعرفة'],
        '← открытые вопросы': ['← open questions', '← preguntas abiertas', '← الأسئلة المفتوحة'],
        'Открытые вопросы': ['Open questions', 'Preguntas abiertas', 'الأسئلة المفتوحة'],
        '← К параграфу': ['← Back to the paragraph', '← Volver al párrafo', '← العودة إلى الفقرة'],
        '💬 Спросить тьютора': ['💬 Ask the tutor', '💬 Preguntar al tutor', '💬 اسأل المرشد'],
        '🖨 Распечатать / PDF': ['🖨 Print / PDF', '🖨 Imprimir / PDF', '🖨 طباعة / PDF'],
        'Язык физики': ['The language of physics', 'El lenguaje de la física', 'لغة الفيزياء'],
        'механика': ['mechanics', 'mecánica', 'الميكانيكا'],
        'термодинамика': ['thermodynamics', 'termodinámica', 'الديناميكا الحرارية'],
        'Термодинамика': ['Thermodynamics', 'Termodinámica', 'الديناميكا الحرارية'],
        'Интерактивный учебник на движке': ['Interactive textbook powered by',
            'Libro interactivo con el motor', 'كتاب تفاعلي بمحرك'],
        'интерактивный учебник': ['interactive textbook', 'libro interactivo', 'كتاب تفاعلي'],
        'в работе': ['in progress', 'en curso', 'قيد العمل'],
        'готова': ['ready', 'lista', 'جاهزة'],
        'скоро': ['soon', 'pronto', 'قريباً'],
        'не решено': ['unsolved', 'sin resolver', 'لم يُحل'],
        'не знаю': ['do not know', 'no lo sé', 'لا أعرف'],
        'по разделу': ['in section', 'en la sección', 'في القسم'],
        'Внимание.': ['Caution.', 'Atención.', 'تنبيه.'],
        'Статус.': ['Status.', 'Estado.', 'الحالة.'],
        'Разгадка.': ['The answer.', 'La clave.', 'الحل.'],
        'Дано': ['Given', 'Datos', 'المعطيات'],
        'Закон': ['Law', 'Ley', 'القانون'],
        'Решение': ['Solution', 'Solución', 'الحل'],
        'Ответ': ['Answer', 'Respuesta', 'الإجابة'],
        'Как запомнить:': ['How to remember:', 'Cómo recordarlo:', 'كيف تتذكره:'],
        'Не удалось загрузить материал': ['Could not load the material', 'No se pudo cargar el material',
            'تعذّر تحميل المادة'],
        'Не удалось загрузить учебник': ['Could not load the textbook', 'No se pudo cargar el libro',
            'تعذّر تحميل الكتاب'],
        'Не удалось загрузить данные:': ['Could not load the data:', 'No se pudieron cargar los datos:',
            'تعذّر تحميل البيانات:'],
        'Не удалось загрузить лекцию:': ['Could not load the lecture:', 'No se pudo cargar la lección:',
            'تعذّر تحميل المحاضرة:'],
        'Не удалось загрузить карточку:': ['Could not load the card:', 'No se pudo cargar la ficha:',
            'تعذّر تحميل البطاقة:'],
        'Курс': ['Course', 'Curso', 'المقرر'],
        'Лекция': ['Lecture', 'Lección', 'محاضرة'],
        'опирается на:': ['builds on:', 'se apoya en:', 'يعتمد على:'],
        'Связано с курсом:': ['Linked to the course:', 'Vinculado al curso:', 'مرتبط بالمقرر:'],
        'Как работать с этим курсом': ['How to work through this course', 'Cómo seguir este curso',
            'كيف تتقدّم في هذا المقرر'],
        'сколько времени': ['how long it takes', 'cuánto tiempo lleva', 'كم يستغرق']
    };

    // Шаблоны с числом: «Тема 3», «Параграф 1 · параграф 2 из 3»
    // и приставки, к которым приклеен уже переведённый хвост («опирается на: Mecánica»)
    var RULES = [
        [/^опирается на:\s*/, { en: 'builds on: ', es: 'se apoya en: ', ar: 'يعتمد على: ' }],
        [/^Связано с курсом:\s*/, { en: 'Linked to the course: ', es: 'Vinculado al curso: ',
            ar: 'مرتبط بالمقرر: ' }],
        [/^Пройдено параграфов:\s*/, { en: 'Paragraphs completed: ', es: 'Párrafos completados: ',
            ar: 'الفقرات المنجزة: ' }],
        [/^Итог:\s*/, { en: 'Takeaway: ', es: 'En resumen: ', ar: 'الخلاصة: ' }],
        [/^Тема\s+(\d+)/, { en: 'Topic $1', es: 'Tema $1', ar: 'الموضوع $1' }],
        [/^Параграф\s+(\d+)/, { en: 'Paragraph $1', es: 'Párrafo $1', ar: 'الفقرة $1' }],
        [/^(\d+)\s+из\s+(\d+)$/, { en: '$1 of $2', es: '$1 de $2', ar: '$1 من $2' }],
        [/^тем открыто из\s*/, { en: 'topics opened of ', es: 'temas abiertos de ', ar: 'مواضيع مفتوحة من ' }],
        [/·\s*параграф\s+(\d+)/, { en: '· paragraph $1', es: '· párrafo $1', ar: '· فقرة $1' }]
    ];

    var IDX = { en: 0, es: 1, ar: 2 };

    function tr(text) {
        var key = (text || '').trim();
        if (!key) return null;
        var hit = DICT[key];
        if (hit) return hit[IDX[LANG]];
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
        ['ru', 'en', 'es', 'ar'].forEach(function (l) {
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

    function start() {
        mountSwitcher();
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

    global.B42_T = tr;
})(window);
