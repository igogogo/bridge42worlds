/* figures-i18n.js — подписи схем на четырёх языках.

   Схемы рисуются в js/figures.js, подписи на них были только по-русски: на английской,
   испанской и арабской версиях читатель видел кириллицу прямо на картинке. Ключ словаря —
   русская подпись как она написана в коде, поэтому промахнуться по смыслу нельзя.

   Подставляется в одной функции txt() — см. figures.js. Файл подключать ПЕРЕД figures.js.
   Собран tools/figures_i18n.py; после правки подписей в схемах прогнать его заново. */
window.B42FigText = {
  "стенка": {
    "en": "wall",
    "es": "pared",
    "ar": "جدار"
  },
  "долетят": {
    "en": "reach",
    "es": "llegan",
    "ar": "تصل"
  },
  "за &#916;t": {
    "en": "in &#916;t",
    "es": "en &#916;t",
    "ar": "خلال &#916;t"
  },
  "много": {
    "en": "many",
    "es": "muchos",
    "ar": "كثير"
  },
  "ударов": {
    "en": "collisions",
    "es": "choques",
    "ar": "الضربات"
  },
  "постоянная сила": {
    "en": "constant force",
    "es": "fuerza constante",
    "ar": "قوة ثابتة"
  },
  "Па = Н / м²": {
    "en": "Pa = N / m²",
    "es": "Pa = N / m²",
    "ar": "Pa = N / m²"
  },
  "площадь стенки": {
    "en": "wall area",
    "es": "área de la pared",
    "ar": "مساحة الجدار"
  },
  "ни одно направление": {
    "en": "no direction",
    "es": "ninguna dirección",
    "ar": "لا اتجاه واحد"
  },
  "не выделено": {
    "en": "is not preferred",
    "es": "no destacada",
    "ar": "غير مميز"
  },
  "k&#8342; — курс обмена": {
    "en": "k&#8342; — exchange rate",
    "es": "k&#8342; — tasa de intercambio",
    "ar": "k&#8342; — سعر الصرف"
  },
  "Дж &#8596; К": {
    "en": "J &#8596; K",
    "es": "J &#8596; K",
    "ar": "J &#8596; K"
  },
  "микромир: N, m, v": {
    "en": "microcosm: N, m, v",
    "es": "microcosmos: N, m, v",
    "ar": "العالم المصغر: N, m, v"
  },
  "макромир: P, V, T": {
    "en": "macroworld: P, V, T",
    "es": "macrocosmos: P, V, T",
    "ar": "العالم الكبير: P, V, T"
  },
  "T растёт": {
    "en": "T increases",
    "es": "T aumenta",
    "ar": "T يزداد"
  },
  "T стоит": {
    "en": "T is constant",
    "es": "T constante",
    "ar": "T ثابت"
  },
  "связи рвутся": {
    "en": "bonds break",
    "es": "los enlaces se rompen",
    "ar": "الروابط تنكسر"
  },
  "нагрев": {
    "en": "heating",
    "es": "calentamiento",
    "ar": "تسخين"
  },
  "67 кДж": {
    "en": "67 kJ",
    "es": "67 kJ",
    "ar": "67 kJ"
  },
  "кипение": {
    "en": "boiling",
    "es": "ebullición",
    "ar": "غليان"
  },
  "452 кДж": {
    "en": "452 kJ",
    "es": "452 kJ",
    "ar": "452 kJ"
  },
  "в 6,8 раза больше": {
    "en": "6.8 times larger",
    "es": "6.8 veces más",
    "ar": "أكبر بـ 6.8 مرة"
  },
  "пар": {
    "en": "vapor",
    "es": "vapor",
    "ar": "بخار"
  },
  "давление атмосферы": {
    "en": "atmospheric pressure",
    "es": "presión atmosférica",
    "ar": "الضغط الجوي"
  },
  "пузырёк": {
    "en": "bubble",
    "es": "burbuja",
    "ar": "فقاعة"
  },
  "раздвигает": {
    "en": "expands",
    "es": "desplaza",
    "ar": "يدفع"
  },
  "только давление": {
    "en": "only pressure",
    "es": "solo presión",
    "ar": "فقط الضغط"
  },
  "только температура": {
    "en": "only temperature",
    "es": "solo temperatura",
    "ar": "فقط درجة الحرارة"
  },
  "&#8747; каждую часть отдельно": {
    "en": "&#8747; each part separately",
    "es": "&#8747; cada parte por separado",
    "ar": "&#8747; كل جزء على حدة"
  },
  "0,5 атм": {
    "en": "0.5 atm",
    "es": "0.5 atm",
    "ar": "0.5 atm"
  },
  "1 атм": {
    "en": "1 atm",
    "es": "1 atm",
    "ar": "1 atm"
  },
  "2 атм": {
    "en": "2 atm",
    "es": "2 atm",
    "ar": "2 atm"
  },
  "газ": {
    "en": "gas",
    "es": "gas",
    "ar": "غاز"
  },
  "dU — нагрев": {
    "en": "dU — heating",
    "es": "dU — calentamiento",
    "ar": "dU — تسخين"
  },
  "P·dV — работа": {
    "en": "P·dV — work",
    "es": "P·dV — trabajo",
    "ar": "P·dV — شغل"
  },
  "ничего": {
    "en": "nothing",
    "es": "nada",
    "ar": "لا شيء"
  },
  "не пропадает": {
    "en": "does not disappear",
    "es": "no desaparece",
    "ar": "لا يختفي"
  },
  "до: 300 K": {
    "en": "before: 300 K",
    "es": "antes: 300 K",
    "ar": "قبل: 300 K"
  },
  "сжали": {
    "en": "compressed",
    "es": "comprimido",
    "ar": "ضغط"
  },
  "после: 420 K": {
    "en": "after: 420 K",
    "es": "después: 420 K",
    "ar": "بعد: 420 K"
  },
  "тепло": {
    "en": "heat",
    "es": "calor",
    "ar": "حرارة"
  },
  "не уходит": {
    "en": "does not escape",
    "es": "no sale",
    "ar": "لا يخرج"
  },
  "адиабата": {
    "en": "adiabatic",
    "es": "adiabática",
    "ar": "أدياباتي"
  },
  "изотерма P·V": {
    "en": "isotherm P·V",
    "es": "isoterma P·V",
    "ar": "متساوية الحرارة P·V"
  },
  "работа": {
    "en": "work",
    "es": "trabajo",
    "ar": "شغل"
  },
  "площадь": {
    "en": "area",
    "es": "área",
    "ar": "مساحة"
  },
  "= работа": {
    "en": "= work",
    "es": "= trabajo",
    "ar": "= شغل"
  },
  "нагреватель": {
    "en": "heat source",
    "es": "calentador",
    "ar": "مسخن"
  },
  "холодильник": {
    "en": "cold reservoir",
    "es": "foco frío",
    "ar": "مبرد"
  },
  "машина": {
    "en": "engine",
    "es": "máquina",
    "ar": "آلة"
  },
  "Q&#1093; никогда не ноль": {
    "en": "Q&#1093; never zero",
    "es": "Q&#1093; nunca es cero",
    "ar": "Q&#1093; أبداً صفر"
  },
  "только температуры": {
    "en": "only temperatures",
    "es": "solo temperaturas",
    "ar": "درجات الحرارة فقط"
  },
  "никакой конструкции": {
    "en": "no specific design",
    "es": "ninguna construcción",
    "ar": "لا تصميم معين"
  },
  "пассажир": {
    "en": "passenger",
    "es": "pasajero",
    "ar": "راكب"
  },
  "100 км/ч": {
    "en": "100 km/h",
    "es": "100 km/h",
    "ar": "100 km/h"
  },
  "наблюдатель": {
    "en": "observer",
    "es": "observador",
    "ar": "مراقب"
  },
  "v = 0 в вагоне": {
    "en": "v = 0 on the train",
    "es": "v = 0 en el vagón",
    "ar": "v = 0 في العربة"
  },
  "v = 100 с перрона": {
    "en": "v = 100 from the platform",
    "es": "v = 100 desde el andén",
    "ar": "v = 100 من الرصيف"
  },
  "секущая": {
    "en": "secant",
    "es": "secante",
    "ar": "قاطع"
  },
  "касательная": {
    "en": "tangent",
    "es": "tangente",
    "ar": "مماس"
  },
  "м": {
    "en": "m",
    "es": "m",
    "ar": "m"
  },
  "м/с": {
    "en": "m/s",
    "es": "m/s",
    "ar": "m/s"
  },
  "м/с²": {
    "en": "m/s²",
    "es": "m/s²",
    "ar": "m/s²"
  },
  "каждая ступень —": {
    "en": "each step —",
    "es": "cada paso —",
    "ar": "كل خطوة —"
  },
  "деление на время": {
    "en": "division by time",
    "es": "división por tiempo",
    "ar": "قسمة على الزمن"
  },
  "a = скорость изменения скорости": {
    "en": "a = rate of change of velocity",
    "es": "a = tasa de cambio de la velocidad",
    "ar": "a = معدل تغير السرعة"
  },
  "наклон прямой = ускорение": {
    "en": "slope of line = acceleration",
    "es": "pendiente de la recta = aceleración",
    "ar": "ميل الخط المستقيم = التسارع"
  },
  "площадь трапеции = перемещение": {
    "en": "area of trapezoid = displacement",
    "es": "área del trapecio = desplazamiento",
    "ar": "مساحة شبه المنحرف = الإزاحة"
  },
  "v&#8320;t — равномерная часть": {
    "en": "v&#8320;t — uniform part",
    "es": "v&#8320;t — parte uniforme",
    "ar": "v&#8320;t — الجزء المنتظم"
  },
  "сил нет — скорость постоянна": {
    "en": "no forces — velocity constant",
    "es": "sin fuerzas — velocidad constante",
    "ar": "لا قوى — السرعة ثابتة"
  },
  "равные промежутки за равное время": {
    "en": "equal displacements in equal time intervals",
    "es": "distancias iguales en tiempos iguales",
    "ar": "مسافات متساوية في أزمنة متساوية"
  },
  "вдвое большая сила — вдвое большее ускорение": {
    "en": "twice the force — twice the acceleration",
    "es": "doble fuerza — doble aceleración",
    "ar": "قوة مضاعفة — تسارع مضاعف"
  },
  "та же сила: вдвое тяжелее — вдвое медленнее разгон": {
    "en": "same force: twice as heavy — twice as slow acceleration",
    "es": "misma fuerza: doble masa — mitad de aceleración",
    "ar": "نفس القوة: ضعف الكتلة — نصف التسارع"
  },
  "больше сила →": {
    "en": "more force →",
    "es": "más fuerza →",
    "ar": "قوة أكبر →"
  },
  "быстрее разгон": {
    "en": "faster acceleration",
    "es": "aceleración más rápida",
    "ar": "تسارع أسرع"
  },
  "больше масса →": {
    "en": "more mass →",
    "es": "más masa →",
    "ar": "كتلة أكبر →"
  },
  "медленнее разгон": {
    "en": "slower acceleration",
    "es": "aceleración más lenta",
    "ar": "تسارع أبطأ"
  },
  "1 Н = 1 кг · 1 м/с²": {
    "en": "1 N = 1 kg · 1 m/s²",
    "es": "1 N = 1 kg · 1 m/s²",
    "ar": "1 N = 1 kg · 1 m/s²"
  },
  "масса уходит назад": {
    "en": "mass goes backward",
    "es": "masa retrocede",
    "ar": "الكتلة تتجه للخلف"
  },
  "верно даже когда": {
    "en": "true even when",
    "es": "cierto incluso cuando",
    "ar": "صحيح حتى عندما"
  },
  "масса меняется": {
    "en": "mass changes",
    "es": "la masa cambia",
    "ar": "الكتلة تتغير"
  },
  "равны по величине, приложены к РАЗНЫМ телам": {
    "en": "equal in magnitude, applied to DIFFERENT bodies",
    "es": "iguales en magnitud, aplicadas a cuerpos DISTINTOS",
    "ar": "متساوية في المقدار، مؤثرة على أجسام مختلفة"
  },
  "замкнутая система": {
    "en": "closed system",
    "es": "sistema cerrado",
    "ar": "نظام مغلق"
  },
  "внутренние силы гасятся → Σp = const": {
    "en": "internal forces cancel → Σp = const",
    "es": "fuerzas internas se cancelan → Σp = cte",
    "ar": "القوى الداخلية تلغى → Σp = ثابت"
  },
  "упругий": {
    "en": "elastic",
    "es": "elástico",
    "ar": "مرن"
  },
  "разлетелись,": {
    "en": "flew apart,",
    "es": "se separaron,",
    "ar": "انفصلوا،"
  },
  "E сохранилась": {
    "en": "E conserved",
    "es": "E se conservó",
    "ar": "E محفوظة"
  },
  "неупругий": {
    "en": "inelastic",
    "es": "inelástico",
    "ar": "غير مرن"
  },
  "слиплись,": {
    "en": "stuck together,",
    "es": "se pegaron,",
    "ar": "التصقوا،"
  },
  "часть E → тепло": {
    "en": "part of E → heat",
    "es": "parte de E → calor",
    "ar": "جزء من E → حرارة"
  },
  "импульс сохраняется в обоих случаях": {
    "en": "momentum conserved in both cases",
    "es": "el momento se conserva en ambos casos",
    "ar": "الزخم محفوظ في كلتا الحالتين"
  },
  "сдвиг в пространстве": {
    "en": "shift in space",
    "es": "traslación espacial",
    "ar": "إزاحة مكانية"
  },
  "импульс": {
    "en": "momentum",
    "es": "momento",
    "ar": "الزخم"
  },
  "сдвиг во времени": {
    "en": "shift in time",
    "es": "traslación temporal",
    "ar": "الإزاحة الزمنية"
  },
  "энергия": {
    "en": "energy",
    "es": "energía",
    "ar": "الطاقة"
  },
  "поворот": {
    "en": "rotation",
    "es": "rotación",
    "ar": "الدوران"
  },
  "момент импульса": {
    "en": "angular momentum",
    "es": "momento angular",
    "ar": "الزخم الزاوي"
  },
  "симметрия рождает закон сохранения": {
    "en": "symmetry gives conservation law",
    "es": "la simetría genera una ley de conservación",
    "ar": "التناظر يولد قانون الحفظ"
  },
  "величина v": {
    "en": "magnitude of v",
    "es": "magnitud v",
    "ar": "مقدار v"
  },
  "постоянна,": {
    "en": "constant,",
    "es": "constante,",
    "ar": "ثابت،"
  },
  "направление": {
    "en": "direction",
    "es": "dirección",
    "ar": "الاتجاه"
  },
  "меняется": {
    "en": "changes",
    "es": "cambia",
    "ar": "يتغير"
  },
  "значит есть ускорение": {
    "en": "so there is acceleration",
    "es": "significa que hay aceleración",
    "ar": "إذاً هناك تسارع"
  },
  "треугольник радиусов": {
    "en": "triangle of radii",
    "es": "triángulo de radios",
    "ar": "مثلث أنصاف الأقطار"
  },
  "треугольник скоростей": {
    "en": "triangle of velocities",
    "es": "triángulo de velocidades",
    "ar": "مثلث السرعات"
  },
  "всегда к центру": {
    "en": "always toward center",
    "es": "siempre hacia el centro",
    "ar": "دائماً نحو المركز"
  },
  "наблюдатель стоит": {
    "en": "observer stands still",
    "es": "observador en reposo",
    "ar": "المراقب ساكن"
  },
  "сила есть,": {
    "en": "force exists,",
    "es": "hay fuerza,",
    "ar": "توجد قوة،"
  },
  "ускорение есть,": {
    "en": "acceleration exists,",
    "es": "hay aceleración,",
    "ar": "يوجد تسارع،"
  },
  "F = ma сходится": {
    "en": "F = ma works",
    "es": "F = ma se cumple",
    "ar": "F = ma متوافقة"
  },
  "наблюдатель вращается": {
    "en": "observer rotates",
    "es": "observador gira",
    "ar": "المراقب يدور"
  },
  "тело покоится,": {
    "en": "body is at rest,",
    "es": "el cuerpo está en reposo,",
    "ar": "الجسم ساكن،"
  },
  "силы уравновешены —": {
    "en": "forces are balanced —",
    "es": "las fuerzas se equilibran —",
    "ar": "القوى متوازنة —"
  },
  "но откуда F?": {
    "en": "but where does F come from?",
    "es": "pero ¿de dónde F?",
    "ar": "لكن من أين F؟"
  },
  "кабина ускоряется": {
    "en": "cabin accelerates",
    "es": "la cabina acelera",
    "ar": "الكابينة تتسارع"
  },
  "нет источника,": {
    "en": "no source,",
    "es": "sin fuente,",
    "ar": "لا مصدر،"
  },
  "нет пары по": {
    "en": "no pair according to",
    "es": "no hay par según",
    "ar": "لا زوج وفق"
  },
  "третьему закону": {
    "en": "third law",
    "es": "la tercera ley",
    "ar": "للقانون الثالث"
  },
  "оттянули вправо —": {
    "en": "pulled to the right —",
    "es": "se estiró a la derecha —",
    "ar": "سحبنا لليمين —"
  },
  "тянет влево": {
    "en": "pulls to the left",
    "es": "jala hacia la izquierda",
    "ar": "يسحب لليسار"
  },
  "дважды продифференцировали — вернулись с минусом": {
    "en": "differentiated twice — came back with a minus",
    "es": "se derivó dos veces — se obtiene menos",
    "ar": "اشتقاق مرتين — عدنا بإشارة سالبة"
  },
  "A сокращается": {
    "en": "A cancels",
    "es": "A se cancela",
    "ar": "A تُختصر"
  },
  "уравнению всё равно, как сильно качнули": {
    "en": "equation does not care how far you pulled",
    "es": "a la ecuación le da igual la amplitud",
    "ar": "المعادلة لا تهتم بكمية الإزاحة"
  },
  "T — общий": {
    "en": "T is common",
    "es": "T común",
    "ar": "T — مشترك"
  },
  "большая A": {
    "en": "large A",
    "es": "A grande",
    "ar": "A كبير"
  },
  "малая A": {
    "en": "small A",
    "es": "A pequeña",
    "ar": "A صغير"
  },
  "тень": {
    "en": "shadow",
    "es": "sombra",
    "ar": "ظل"
  },
  "точка вращается": {
    "en": "point rotates",
    "es": "punto gira",
    "ar": "نقطة تدور"
  },
  "тень колеблется": {
    "en": "shadow oscillates",
    "es": "sombra oscila",
    "ar": "الظل يهتز"
  },
  "край": {
    "en": "edge",
    "es": "extremo",
    "ar": "حافة"
  },
  "центр": {
    "en": "center",
    "es": "centro",
    "ar": "مركز"
  },
  "зелёное — движение, охра — пружина": {
    "en": "green — motion, ochre — spring",
    "es": "verde — movimiento, ocre — resorte",
    "ar": "الأخضر — الحركة، المغرة — الزنبرك"
  },
  "сумма всегда одна: E = kA²/2": {
    "en": "sum always the same: E = kA²/2",
    "es": "la suma es siempre la misma: E = kA²/2",
    "ar": "المجموع دائماً واحد: E = kA²/2"
  },
  "у дна — парабола": {
    "en": "at bottom — parabola",
    "es": "en el fondo — parábola",
    "ar": "عند القاع — قطع مكافئ"
  },
  "сложная яма": {
    "en": "complex well",
    "es": "pozo complejo",
    "ar": "بئر معقد"
  },
  "значит внутри спрятана пружина": {
    "en": "means a spring is hidden inside",
    "es": "significa que dentro hay un resorte",
    "ar": "إذاً بداخله زنبرك مخفي"
  },
  "дальше от оси —": {
    "en": "farther from axis —",
    "es": "más lejos del eje —",
    "ar": "أبعد عن المحور —"
  },
  "больше момент": {
    "en": "greater torque",
    "es": "mayor momento",
    "ar": "عزم أكبر"
  },
  "момент импульса учитывает плечо": {
    "en": "angular momentum includes lever arm",
    "es": "el momento angular considera el brazo",
    "ar": "الزخم الزاوي يأخذ في الاعتبار الذراع"
  },
  "руки раскинуты: I большой, ω малая": {
    "en": "arms spread: I large, ω small",
    "es": "brazos extendidos: I grande, ω pequeña",
    "ar": "الذراعان ممدودتان: I كبير، ω صغيرة"
  },
  "руки прижаты: I малый, ω большая": {
    "en": "arms close: I small, ω large",
    "es": "brazos pegados: I pequeño, ω grande",
    "ar": "الذراعان مضغوطتان: I صغير، ω كبيرة"
  },
  "срыв": {
    "en": "breakaway",
    "es": "desprendimiento",
    "ar": "انزلاق"
  },
  "покоя": {
    "en": "static",
    "es": "reposo",
    "ar": "السكون"
  },
  "скольжения": {
    "en": "kinetic",
    "es": "deslizamiento",
    "ar": "الانزلاق"
  },
  "тяга": {
    "en": "traction",
    "es": "tracción",
    "ar": "قوة الجر"
  },
  "малая площадь": {
    "en": "small area",
    "es": "área pequeña",
    "ar": "مساحة صغيرة"
  },
  "большая площадь": {
    "en": "large area",
    "es": "área grande",
    "ar": "مساحة كبيرة"
  },
  "точек контакта столько же — сила трения та же": {
    "en": "same number of contact points — same friction force",
    "es": "la cantidad de puntos de contacto es la misma — la fuerza de fricción es la misma",
    "ar": "نقاط التلامس نفس العدد — قوة الاحتكاك نفسها"
  }
};
