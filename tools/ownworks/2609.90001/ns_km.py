# -*- coding: utf-8 -*-
"""Взгляд машины знаний на работу 2609.90001: куда это может развиться.

Владелец 09.09: его линия — гравитация эквивалентна жидкости; локальная сингулярность
течения может отвечать сингулярности эффективной метрики; такая точка — кандидат в «центр
антиэнтропии», где второе начало перестаёт быть абсолютным; удержать её можно там, где
вязкость исчезает: в сверхтекучем гелии и в конденсате Бозе–Эйнштейна; макроскопический
резонатор и квантовая жидкость — два пути к одной двери. Это должно войти в разбор как
мнение машины знаний, подробно, как развитие, «а не проигнорировано».

Форма — та же, что у tools/recommend.py: seen, strength, directions (с опорами из нашего
архива), ideas, significance, neighbours. Опоры — реальные работы корпуса по аналоговым
чёрным дырам, сверхтекучести, квантовым вихрям, энтропии и стреле времени.
"""

# Опоры из нашего архива (по понятиям analog_black_hole, analogue_black_holes,
# quantum_gravity_analogues, superfluidity, quantum_vortices, vortex_lattice, entropy).
W_SINK = "2604.24861"      # Black Holes in a Sink of Water
W_CLOUD = "2602.20508"     # Quantum Analog of a Black Hole in an Atomic Cloud
W_LIGHTV = "2603.01664"    # Black Holes from Light and Vortices
W_TABLE = "2602.04593"     # Hawking Radiation on a Tabletop
W_BOMB = "2511.05351"      # How a Whirlpool in a Cup Becomes a Black Hole Bomb
W_ARROW = "2508.14312"     # Twilight of Time: Why the Arrow Fades but Time Endures
W_HOURGL = "2509.07745"    # Hourglass of Entropy: How Cold Atoms Keep Time
W_ERASER = "2506.01351"    # The Eraser That Erases the Past: irreversibility from quantum information
W_FRICT = "2601.00190"     # Friction Vanishes Before Your Eyes
W_LEAP = "2512.07935"      # Quantum Leapfrog: How Vortices Play in Liquid Light
W_RINGS = "2601.06942"     # Vortex Rings Without a Grid
W_DISORD = "2512.21416"    # When Disorder Gifts Superfluidity
W_BOTTOM = "2601.01258"    # How Bottom Friction Reshapes Vortices in Shallow Water
W_DANCE = "2501.00037"     # Three Translators and the Dance of the Vortex

NEIGHBOURS = [W_SINK, W_CLOUD, W_LIGHTV, W_TABLE, W_BOMB, W_FRICT, W_LEAP, W_RINGS, W_ARROW, W_HOURGL]

KM = {
"ru": {
    "seen": "Построено течение, у которого скорость уходит в бесконечность за конечное время при гладкой внешней силе, из покоя и с конечной энергией: сингулярность живёт в игле, сжимающейся быстрее, чем разгоняется, а недостающую силу поставляет сама жидкость через среднее напряжение колебательных импульсов. Вязкость не подавлена, а встроена в самоподобный баланс. Для нас это не только ответ на пункты (C) и (D) формулировки Феффермана, но и первый строго построенный пример локальной сингулярности сплошной среды при конечной энергии — объект, с которым можно работать дальше.",
    "strength": "Механизм полностью явный: вихрь-игла, кольцо, две семьи импульсов, тепловая внешность. Это значит, что его можно не только доказывать, но и переносить: считать его эффективную метрику, спрашивать, что с ним делает исчезающая вязкость, и пробовать воспроизводить в лаборатории. Работы с явной конструкцией редки, и ценность здесь именно в ней.",
    "directions": [
        {"text": "Связь с общей теорией относительности. С 1981 года известно, что возмущения в движущейся жидкости распространяются по эффективной метрике, а горизонты и излучение Хокинга воспроизводятся в воде и в атомных облаках. Естественный следующий шаг: посчитать акустическую метрику построенного течения. Игла с расходящейся скоростью и обращающейся в ноль энергией — кандидат на точку, где эффективная метрика теряет гладкость, то есть на лабораторный аналог сингулярности пространства-времени с конечной энергией. Мы держим в уме границу: аналоговая гравитация переносит кинематику полей на кривом фоне, а не уравнения Эйнштейна; но именно поэтому вопрос «какая метрика у иглы» честный и решаемый.",
         "based_on": [W_SINK, W_CLOUD, W_LIGHTV, W_TABLE]},
        {"text": "Сингулярность как центр антиэнтропии. Гипотеза, которую мы принимаем как рабочую: локальная сингулярность — окно, где второе начало перестаёт быть абсолютным и порядок может рождаться из хаоса. У построенного течения есть прямая проверка: посчитать бюджет энтропии отдельно в ядре, в кольце и снаружи. Энергия в него вносится силой, поэтому глобальный баланс положителен; вопрос в том, есть ли область, где локальное производство энтропии отрицательно и удерживается импульсами, а не размазывается диссипацией. Если такая область существует и её размер следует масштабам работы, «центр антиэнтропии» перестаёт быть словом и становится измеримой величиной.",
         "based_on": [W_ARROW, W_HOURGL, W_ERASER]},
        {"text": "Сверхтекучее и конденсат Бозе–Эйнштейна. В классической жидкости вязкость съедает импульсы, и это часть конструкции; в сверхтекучем гелии и в конденсате вязкость исчезает, вихри квантуются, сами собираются в решётки, а квантовая турбулентность — порядок в хаосе — наблюдается в лаборатории. Отсюда рабочая мысль владельца: там, где диссипации нет, сингулярность может не рассеяться, а удержаться. Программа: перенести механизм кольцевых импульсов в уравнение Гросса–Питаевского и спросить, где в нём остаётся нужное среднее напряжение, когда вязкого затухания нет, а квантованное давление есть.",
         "based_on": [W_FRICT, W_LEAP, W_RINGS, W_DISORD]},
        {"text": "Макроскопический резонатор. Два встречно вращающихся колеса в противофазе — это принудительное вращательное течение со сдвигом, то есть ровно тот фон, на котором в работе растут импульсы по центробежному механизму. Что можно измерить прямо: напряжение Рейнольдса в кольце между ядром и внешним течением и его зависимость от скорости вращения. Совпадение знака и роста с конструкцией было бы первой лабораторной точкой на этой карте; аналоговая «бомба» в чашке с водоворотом показывает, что такие измерения делаются.",
         "based_on": [W_BOMB, W_BOTTOM, W_DANCE]},
        {"text": "Два пути к одной двери. Резонатор в метрике и резонатор в квантовой жидкости описываются одной математикой: у обоих есть фон со сдвигом, кольцо и колебания, поставляющие напряжение. Стоит собрать таблицу соответствий: что в игле отвечает горизонту, что — квантованному вихрю, что — накачке. Так становится видно, какая из двух дверей ближе к эксперименту, а какая — к теории.",
         "based_on": [W_LIGHTV, W_CLOUD]},
    ],
    "ideas": [
        "Вывести акустическую метрику построенного течения и проверить, обращается ли её кривизна в бесконечность при t → 1 и как это согласуется с исчезающей энергией ядра.",
        "Посчитать локальное производство энтропии по трём зонам конструкции — ядро, кольцо, внешность — и найти, есть ли область с отрицательным балансом, удерживаемая импульсами.",
        "Повторить механизм кольцевых импульсов в модели Гросса–Питаевского при нулевой вязкости: сохраняется ли взрыв, и что заменяет вязкое гашение импульсов.",
        "Собрать вращающуюся установку со встречными приводами и измерить напряжение Рейнольдса в кольце как функцию скорости: это самый дешёвый способ увидеть механизм руками.",
    ],
    "significance": "Если сингулярность течения переносится на эффективную метрику, обычная и квантовая жидкости становятся стендом для вопросов, которые в самой гравитации не проверить: как ведёт себя энтропия рядом с сингулярностью и может ли порядок удерживаться там, где непрерывное описание ломается. Работа OpenAI впервые даёт для такого стенда явную, строго построенную сингулярность с конечной энергией.",
},
"en": {
    "seen": "A flow is constructed whose speed becomes infinite in finite time under a smooth external force, from rest and with finite energy: the singularity lives in a needle that shrinks faster than it speeds up, and the missing force is supplied by the fluid itself through the mean stress of oscillatory pulses. Viscosity is not suppressed but built into a self-similar balance. For us this is not only an answer to alternatives (C) and (D) of Fefferman's statement, but the first rigorously built example of a local singularity of a continuous medium at finite energy: an object one can keep working with.",
    "strength": "The mechanism is fully explicit: needle vortex, annulus, two families of pulses, heat exterior. That means it can not only be proved but transferred: compute its effective metric, ask what vanishing viscosity does to it, try to reproduce it in a laboratory. Works with an explicit construction are rare, and the value lies precisely there.",
    "directions": [
        {"text": "The link to general relativity. Since 1981 it has been known that disturbances in a moving fluid propagate on an effective metric, and horizons and Hawking radiation are reproduced in water and in atomic clouds. The natural next step: compute the acoustic metric of the constructed flow. A needle with divergent speed and vanishing energy is a candidate for a point where the effective metric loses smoothness, i.e. for a laboratory analogue of a spacetime singularity at finite energy. We keep the boundary in mind: analogue gravity carries the kinematics of fields on a curved background, not Einstein's equations; but that is exactly why 'what is the needle's metric' is an honest, solvable question.",
         "based_on": [W_SINK, W_CLOUD, W_LIGHTV, W_TABLE]},
        {"text": "The singularity as a centre of anti-entropy. A hypothesis we adopt as a working one: a local singularity is a window where the second law stops being absolute and order can be born from chaos. The constructed flow admits a direct test: compute the entropy budget separately in the core, in the annulus and outside. Energy is injected by the force, so the global balance is positive; the question is whether there is a region where local entropy production is negative and is held by the pulses rather than smeared by dissipation. If such a region exists and its size follows the scalings of the paper, 'centre of anti-entropy' stops being a phrase and becomes a measurable quantity.",
         "based_on": [W_ARROW, W_HOURGL, W_ERASER]},
        {"text": "Superfluids and Bose–Einstein condensates. In a classical fluid viscosity eats the pulses, and that is part of the construction; in superfluid helium and in a condensate viscosity vanishes, vortices are quantized, they self-assemble into lattices, and quantum turbulence, order in chaos, is observed in the laboratory. Hence the working idea: where there is no dissipation, a singularity may not disperse but hold. The programme: carry the annulus-pulse mechanism into the Gross–Pitaevskii equation and ask where the required mean stress survives when viscous damping is absent and quantum pressure is present.",
         "based_on": [W_FRICT, W_LEAP, W_RINGS, W_DISORD]},
        {"text": "A macroscopic resonator. Two counter-rotating wheels in antiphase are a driven rotating shear flow, i.e. exactly the background on which the paper's pulses grow by the centrifugal mechanism. What can be measured directly: the Reynolds stress in the annulus between core and exterior and its dependence on rotation speed. Agreement of sign and growth with the construction would be the first laboratory point on this map; the analogue 'bomb' in a cup with a whirlpool shows that such measurements are done.",
         "based_on": [W_BOMB, W_BOTTOM, W_DANCE]},
        {"text": "Two paths to one door. A resonator in the metric and a resonator in a quantum fluid are described by one mathematics: both have a sheared background, an annulus, and oscillations that supply stress. It is worth building a correspondence table: what in the needle answers to the horizon, what to a quantized vortex, what to the pumping. Then one sees which of the two doors is closer to experiment and which to theory.",
         "based_on": [W_LIGHTV, W_CLOUD]},
    ],
    "ideas": [
        "Derive the acoustic metric of the constructed flow and check whether its curvature diverges as t → 1 and how that squares with the vanishing core energy.",
        "Compute local entropy production over the three zones of the construction, core, annulus, exterior, and look for a region with negative balance held by the pulses.",
        "Repeat the annulus-pulse mechanism in a Gross–Pitaevskii model at zero viscosity: does the blowup survive, and what replaces viscous damping of the pulses.",
        "Build a rotating tank with counter-rotating drives and measure the Reynolds stress in the annulus as a function of speed: the cheapest way to see the mechanism with one's own hands.",
    ],
    "significance": "If a flow singularity transfers to an effective metric, ordinary and quantum fluids become a testbed for questions that cannot be tested in gravity itself: how entropy behaves next to a singularity and whether order can hold where the continuous description breaks. OpenAI's paper gives such a testbed, for the first time, an explicit, rigorously built singularity at finite energy.",
},
"es": {
    "seen": "Se construye un flujo cuya velocidad se hace infinita en tiempo finito bajo una fuerza externa suave, desde el reposo y con energía finita: la singularidad vive en una aguja que se encoge más rápido de lo que acelera, y la fuerza que falta la aporta el propio fluido mediante la tensión media de pulsos oscilatorios. La viscosidad no se suprime, se integra en un balance autosemejante. Para nosotros no es solo la respuesta a las alternativas (C) y (D) del enunciado de Fefferman, sino el primer ejemplo construido con rigor de una singularidad local de un medio continuo con energía finita: un objeto con el que se puede seguir trabajando.",
    "strength": "El mecanismo es completamente explícito: vórtice-aguja, anillo, dos familias de pulsos, exterior de calor. Eso significa que no solo se puede demostrar sino trasladar: calcular su métrica efectiva, preguntar qué le hace la viscosidad que se anula, intentar reproducirlo en el laboratorio. Los trabajos con construcción explícita son raros, y el valor está precisamente ahí.",
    "directions": [
        {"text": "La conexión con la relatividad general. Desde 1981 se sabe que las perturbaciones en un fluido en movimiento se propagan sobre una métrica efectiva, y los horizontes y la radiación de Hawking se reproducen en agua y en nubes atómicas. El siguiente paso natural: calcular la métrica acústica del flujo construido. Una aguja con velocidad divergente y energía que se anula es candidata a punto donde la métrica efectiva pierde suavidad, es decir, a análogo de laboratorio de una singularidad del espacio-tiempo con energía finita. Tenemos presente el límite: la gravedad análoga traslada la cinemática de los campos sobre un fondo curvo, no las ecuaciones de Einstein; pero justo por eso la pregunta «cuál es la métrica de la aguja» es honesta y resoluble.",
         "based_on": [W_SINK, W_CLOUD, W_LIGHTV, W_TABLE]},
        {"text": "La singularidad como centro de antientropía. Una hipótesis que adoptamos como de trabajo: una singularidad local es una ventana donde la segunda ley deja de ser absoluta y el orden puede nacer del caos. El flujo construido admite una prueba directa: calcular el balance de entropía por separado en el núcleo, en el anillo y fuera. La energía la inyecta la fuerza, así que el balance global es positivo; la cuestión es si hay una región donde la producción local de entropía es negativa y la sostienen los pulsos en lugar de difuminarla la disipación. Si esa región existe y su tamaño sigue las escalas del trabajo, «centro de antientropía» deja de ser una frase y pasa a ser una magnitud medible.",
         "based_on": [W_ARROW, W_HOURGL, W_ERASER]},
        {"text": "Superfluidos y condensados de Bose–Einstein. En un fluido clásico la viscosidad se come los pulsos, y eso es parte de la construcción; en el helio superfluido y en un condensado la viscosidad se anula, los vórtices se cuantizan, se autoensamblan en redes, y la turbulencia cuántica, orden en el caos, se observa en el laboratorio. De ahí la idea de trabajo: donde no hay disipación, una singularidad puede no dispersarse sino sostenerse. El programa: llevar el mecanismo de pulsos anulares a la ecuación de Gross–Pitaevskii y preguntar dónde sobrevive la tensión media necesaria cuando no hay amortiguación viscosa pero sí presión cuántica.",
         "based_on": [W_FRICT, W_LEAP, W_RINGS, W_DISORD]},
        {"text": "Un resonador macroscópico. Dos ruedas contrarrotantes en contrafase son un flujo rotatorio forzado con cizalla, es decir, exactamente el fondo sobre el que crecen los pulsos del trabajo por el mecanismo centrífugo. Lo que se puede medir directamente: la tensión de Reynolds en el anillo entre núcleo y exterior y su dependencia de la velocidad de rotación. La coincidencia de signo y crecimiento con la construcción sería el primer punto de laboratorio en este mapa; la «bomba» análoga en una taza con remolino muestra que tales medidas se hacen.",
         "based_on": [W_BOMB, W_BOTTOM, W_DANCE]},
        {"text": "Dos caminos a una misma puerta. Un resonador en la métrica y un resonador en un fluido cuántico se describen con una misma matemática: ambos tienen un fondo con cizalla, un anillo y oscilaciones que aportan tensión. Vale la pena construir una tabla de correspondencias: qué en la aguja responde al horizonte, qué al vórtice cuantizado, qué al bombeo. Así se ve cuál de las dos puertas está más cerca del experimento y cuál de la teoría.",
         "based_on": [W_LIGHTV, W_CLOUD]},
    ],
    "ideas": [
        "Derivar la métrica acústica del flujo construido y comprobar si su curvatura diverge cuando t → 1 y cómo cuadra con la energía del núcleo que se anula.",
        "Calcular la producción local de entropía en las tres zonas de la construcción, núcleo, anillo, exterior, y buscar una región con balance negativo sostenida por los pulsos.",
        "Repetir el mecanismo de pulsos anulares en un modelo de Gross–Pitaevskii con viscosidad cero: ¿sobrevive la explosión y qué sustituye a la amortiguación viscosa de los pulsos?",
        "Montar un tanque rotatorio con accionamientos contrarrotantes y medir la tensión de Reynolds en el anillo en función de la velocidad: la forma más barata de ver el mecanismo con las propias manos.",
    ],
    "significance": "Si una singularidad del flujo se traslada a una métrica efectiva, los fluidos ordinarios y cuánticos se convierten en banco de pruebas para preguntas que en la propia gravedad no se pueden probar: cómo se comporta la entropía junto a una singularidad y si el orden puede sostenerse donde la descripción continua se rompe. El trabajo de OpenAI da a ese banco, por primera vez, una singularidad explícita y rigurosamente construida con energía finita.",
},
"ar": {
    "seen": "بُني جريان تصبح سرعته لانهائية في زمن منتهٍ تحت قوة خارجية ملساء، من السكون وبطاقة منتهية: يسكن التفرّد إبرةً تنكمش أسرع مما تتسارع، والقوة الناقصة يوفرها المائع نفسه عبر الإجهاد المتوسط لنبضات اهتزازية. اللزوجة لم تُكبت بل أُدمجت في توازن ذاتي التشابه. هذا عندنا ليس جوابًا عن البديلين (C) و(D) في صياغة فيفرمان فحسب، بل أول مثال مبني بصرامة على تفرّد موضعي لوسط متصل بطاقة منتهية: شيء يمكن مواصلة العمل عليه.",
    "strength": "الآلية صريحة بالكامل: دوامة إبرية، حلقة، عائلتان من النبضات، خارج حراري. أي أنه يمكن لا البرهنة عليها فحسب بل نقلها: حساب متريتها الفعّالة، والسؤال عما تفعله بها اللزوجة المتلاشية، ومحاولة إعادة إنتاجها في المختبر. الأعمال ذات البناء الصريح نادرة، وهنا تكمن القيمة تحديدًا.",
    "directions": [
        {"text": "الصلة بالنسبية العامة. منذ 1981 معروف أن الاضطرابات في مائع متحرك تنتشر على مترية فعّالة، وأن الآفاق وإشعاع هوكينغ يُستنسخان في الماء وفي السحب الذرية. الخطوة التالية الطبيعية: حساب المترية الصوتية للجريان المبني. إبرة بسرعة متباعدة وطاقة متلاشية مرشحة لتكون نقطة تفقد فيها المترية الفعّالة سلاستها، أي نظيرًا مختبريًا لتفرّد الزمكان بطاقة منتهية. ونضع الحد نصب أعيننا: الجاذبية التناظرية تنقل حركيات الحقول على خلفية منحنية لا معادلات أينشتاين؛ ولهذا بالذات يكون سؤال «ما مترية الإبرة» سؤالًا أمينًا وقابلًا للحل.",
         "based_on": [W_SINK, W_CLOUD, W_LIGHTV, W_TABLE]},
        {"text": "التفرّد مركزًا لمضاد الإنتروبيا. فرضية نتبناها فرضيةَ عمل: التفرّد الموضعي نافذة يكف فيها القانون الثاني عن أن يكون مطلقًا ويمكن للنظام أن يولد من الفوضى. للجريان المبني اختبار مباشر: حساب ميزانية الإنتروبيا على حدة في النواة وفي الحلقة وفي الخارج. الطاقة تُحقن بالقوة، فالميزان الشامل موجب؛ والسؤال هل ثمة منطقة يكون فيها إنتاج الإنتروبيا الموضعي سالبًا وتمسكه النبضات بدل أن يبدده التبديد. إن وُجدت مثل هذه المنطقة وتبع حجمها مقاييس العمل، كفّ «مركز مضاد الإنتروبيا» عن أن يكون عبارة وصار كمية قابلة للقياس.",
         "based_on": [W_ARROW, W_HOURGL, W_ERASER]},
        {"text": "السوائل الفائقة ومكثفات بوز–أينشتاين. في المائع الكلاسيكي تلتهم اللزوجة النبضات، وهذا جزء من البناء؛ أما في الهيليوم الفائق وفي المكثف فتتلاشى اللزوجة، وتتكمّم الدوامات، وتتجمع ذاتيًا في شبكات، ويُرصد الاضطراب الكمي، النظام في الفوضى، في المختبر. ومن هنا فكرة العمل: حيث لا تبديد، قد لا يتبدد التفرّد بل يصمد. البرنامج: نقل آلية النبضات الحلقية إلى معادلة غروس–بيتايفسكي والسؤال أين يبقى الإجهاد المتوسط المطلوب حين يغيب التخميد اللزج ويحضر الضغط الكمي.",
         "based_on": [W_FRICT, W_LEAP, W_RINGS, W_DISORD]},
        {"text": "مرنان ماكروسكوبي. عجلتان متعاكستا الدوران في تضاد طوري هما جريان دوراني مدفوع بقص، أي بالضبط الخلفية التي تنمو عليها نبضات العمل بالآلية الطاردة المركزية. ما يمكن قياسه مباشرة: إجهاد رينولدز في الحلقة بين النواة والخارج وتبعيته لسرعة الدوران. توافق الإشارة والنمو مع البناء سيكون أول نقطة مختبرية على هذه الخريطة؛ و«القنبلة» التناظرية في كوب فيه دوامة تبيّن أن مثل هذه القياسات تُجرى.",
         "based_on": [W_BOMB, W_BOTTOM, W_DANCE]},
        {"text": "طريقان إلى باب واحد. مرنان في المترية ومرنان في مائع كمي تصفهما رياضيات واحدة: لكليهما خلفية بقص وحلقة واهتزازات توفر الإجهاد. يجدر بناء جدول تقابلات: ما الذي يقابل الأفق في الإبرة، وما يقابل الدوامة المكمّمة، وما يقابل الضخ. عندها يُرى أي البابين أقرب إلى التجربة وأيهما إلى النظرية.",
         "based_on": [W_LIGHTV, W_CLOUD]},
    ],
    "ideas": [
        "اشتقاق المترية الصوتية للجريان المبني والتحقق هل يتباعد انحناؤها عندما t → 1 وكيف يتسق ذلك مع طاقة النواة المتلاشية.",
        "حساب إنتاج الإنتروبيا الموضعي في المناطق الثلاث للبناء، النواة والحلقة والخارج، والبحث عن منطقة بميزان سالب تمسكها النبضات.",
        "تكرار آلية النبضات الحلقية في نموذج غروس–بيتايفسكي بلزوجة صفرية: هل يصمد الانفجار، وما الذي يحل محل التخميد اللزج للنبضات.",
        "بناء حوض دوار بمحركات متعاكسة وقياس إجهاد رينولدز في الحلقة بدلالة السرعة: أرخص طريقة لرؤية الآلية باليد.",
    ],
    "significance": "إن انتقل تفرّد الجريان إلى مترية فعّالة، صارت الموائع العادية والكمية منصة اختبار لأسئلة لا تُختبر في الجاذبية نفسها: كيف تسلك الإنتروبيا بجوار التفرّد، وهل يمكن للنظام أن يصمد حيث ينكسر الوصف المتصل. يمنح عمل OpenAI هذه المنصة، لأول مرة، تفرّدًا صريحًا مبنيًا بصرامة بطاقة منتهية.",
},
"fr": {
    "seen": "Un écoulement est construit dont la vitesse devient infinie en temps fini sous une force extérieure lisse, depuis le repos et à énergie finie : la singularité vit dans une aiguille qui rétrécit plus vite qu'elle n'accélère, et la force manquante est fournie par le fluide lui-même via la contrainte moyenne d'impulsions oscillatoires. La viscosité n'est pas supprimée mais intégrée à un bilan autosimilaire. Pour nous, ce n'est pas seulement une réponse aux alternatives (C) et (D) de l'énoncé de Fefferman, mais le premier exemple rigoureusement construit d'une singularité locale d'un milieu continu à énergie finie : un objet avec lequel on peut continuer à travailler.",
    "strength": "Le mécanisme est entièrement explicite : tourbillon-aiguille, anneau, deux familles d'impulsions, extérieur de chaleur. Il peut donc non seulement être prouvé mais transféré : calculer sa métrique effective, demander ce qu'en fait une viscosité qui s'annule, tenter de le reproduire en laboratoire. Les travaux à construction explicite sont rares, et la valeur est précisément là.",
    "directions": [
        {"text": "Le lien avec la relativité générale. Depuis 1981 on sait que les perturbations d'un fluide en mouvement se propagent sur une métrique effective, et que les horizons et le rayonnement de Hawking se reproduisent dans l'eau et dans des nuages atomiques. Étape suivante naturelle : calculer la métrique acoustique de l'écoulement construit. Une aiguille à vitesse divergente et énergie évanescente est candidate au point où la métrique effective perd sa régularité, c'est-à-dire à un analogue de laboratoire d'une singularité de l'espace-temps à énergie finie. Nous gardons la limite en tête : la gravité analogue transporte la cinématique des champs sur un fond courbe, pas les équations d'Einstein ; mais c'est précisément pourquoi la question « quelle est la métrique de l'aiguille » est honnête et soluble.",
         "based_on": [W_SINK, W_CLOUD, W_LIGHTV, W_TABLE]},
        {"text": "La singularité comme centre d'anti-entropie. Une hypothèse que nous adoptons comme hypothèse de travail : une singularité locale est une fenêtre où le second principe cesse d'être absolu et où l'ordre peut naître du chaos. L'écoulement construit admet un test direct : calculer le bilan d'entropie séparément dans le cœur, dans l'anneau et à l'extérieur. L'énergie est injectée par la force, donc le bilan global est positif ; la question est de savoir s'il existe une région où la production locale d'entropie est négative et tenue par les impulsions plutôt qu'étalée par la dissipation. Si une telle région existe et que sa taille suit les échelles du travail, « centre d'anti-entropie » cesse d'être une formule et devient une grandeur mesurable.",
         "based_on": [W_ARROW, W_HOURGL, W_ERASER]},
        {"text": "Superfluides et condensats de Bose–Einstein. Dans un fluide classique la viscosité dévore les impulsions, et cela fait partie de la construction ; dans l'hélium superfluide et dans un condensat la viscosité s'annule, les tourbillons sont quantifiés, ils s'auto-assemblent en réseaux, et la turbulence quantique, ordre dans le chaos, s'observe en laboratoire. D'où l'idée de travail : là où il n'y a pas de dissipation, une singularité peut ne pas se disperser mais tenir. Programme : porter le mécanisme des impulsions annulaires dans l'équation de Gross–Pitaevskii et demander où la contrainte moyenne requise survit lorsque l'amortissement visqueux est absent et la pression quantique présente.",
         "based_on": [W_FRICT, W_LEAP, W_RINGS, W_DISORD]},
        {"text": "Un résonateur macroscopique. Deux roues contrarotatives en opposition de phase forment un écoulement tournant forcé avec cisaillement, c'est-à-dire exactement le fond sur lequel les impulsions du travail croissent par le mécanisme centrifuge. Ce qui se mesure directement : la contrainte de Reynolds dans l'anneau entre cœur et extérieur et sa dépendance à la vitesse de rotation. Un accord du signe et de la croissance avec la construction serait le premier point de laboratoire sur cette carte ; la « bombe » analogue dans une tasse avec tourbillon montre que de telles mesures se font.",
         "based_on": [W_BOMB, W_BOTTOM, W_DANCE]},
        {"text": "Deux chemins vers une même porte. Un résonateur dans la métrique et un résonateur dans un fluide quantique sont décrits par une seule mathématique : tous deux ont un fond cisaillé, un anneau et des oscillations qui fournissent la contrainte. Il vaut la peine de dresser une table de correspondances : ce qui, dans l'aiguille, répond à l'horizon, au tourbillon quantifié, au pompage. On voit alors laquelle des deux portes est la plus proche de l'expérience et laquelle de la théorie.",
         "based_on": [W_LIGHTV, W_CLOUD]},
    ],
    "ideas": [
        "Dériver la métrique acoustique de l'écoulement construit et vérifier si sa courbure diverge quand t → 1 et comment cela s'accorde avec l'énergie évanescente du cœur.",
        "Calculer la production locale d'entropie sur les trois zones de la construction, cœur, anneau, extérieur, et chercher une région à bilan négatif tenue par les impulsions.",
        "Reproduire le mécanisme des impulsions annulaires dans un modèle de Gross–Pitaevskii à viscosité nulle : l'explosion survit-elle, et qu'est-ce qui remplace l'amortissement visqueux des impulsions ?",
        "Monter une cuve tournante à entraînements contrarotatifs et mesurer la contrainte de Reynolds dans l'anneau en fonction de la vitesse : la façon la moins coûteuse de voir le mécanisme de ses propres mains.",
    ],
    "significance": "Si une singularité d'écoulement se transfère à une métrique effective, les fluides ordinaires et quantiques deviennent un banc d'essai pour des questions intestables dans la gravité elle-même : comment l'entropie se comporte près d'une singularité et si l'ordre peut tenir là où la description continue se brise. Le travail d'OpenAI donne à ce banc, pour la première fois, une singularité explicite, rigoureusement construite, à énergie finie.",
},
}
