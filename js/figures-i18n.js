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
    "ar": "الجدار"
  },
  "долетят": {
    "en": "will reach",
    "es": "alcanzan",
    "ar": "تصل"
  },
  "за &#916;t": {
    "en": "in &#916;t",
    "es": "en &#916;t",
    "ar": "خلال Δt"
  },
  "много": {
    "en": "many",
    "es": "muchos",
    "ar": "كثير"
  },
  "ударов": {
    "en": "collisions",
    "es": "impactos",
    "ar": "ضربات"
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
    "ar": "لا اتجاه"
  },
  "не выделено": {
    "en": "not distinguished",
    "es": "privilegiada",
    "ar": "غير محدد"
  },
  "k&#8342; — курс обмена": {
    "en": "k&#8342; — exchange rate",
    "es": "k&#8342; — tipo de cambio",
    "ar": "k′ — سعر الصرف"
  },
  "Дж &#8596; К": {
    "en": "J &#8596; K",
    "es": "J &#8596; K",
    "ar": "J ↔ K"
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
    "ar": "T تزداد"
  },
  "T стоит": {
    "en": "T constant",
    "es": "T constante",
    "ar": "T ثابت"
  },
  "связи рвутся": {
    "en": "bonds break",
    "es": "los enlaces se rompen",
    "ar": "تنكسر الروابط"
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
    "es": "6.8 veces mayor",
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
    "ar": "ضغط الجو"
  },
  "пузырёк": {
    "en": "bubble",
    "es": "burbuja",
    "ar": "فقاعة"
  },
  "раздвигает": {
    "en": "expands",
    "es": "empuja",
    "ar": "يفصل"
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
    "ar": "∫ كل جزء على حدة"
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
    "en": "nothing lost",
    "es": "no se pierde",
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
    "es": "no se escapa",
    "ar": "لا يخرج"
  },
  "адиабата": {
    "en": "adiabat",
    "es": "adiabática",
    "ar": "أدياباتي"
  },
  "изотерма P·V": {
    "en": "isotherm P·V",
    "es": "isoterma P·V",
    "ar": "إيزوثيرم P·V"
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
    "en": "heater",
    "es": "foco caliente",
    "ar": "مسخن"
  },
  "холодильник": {
    "en": "refrigerator",
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
    "ar": "Qх ليس صفرًا أبدًا"
  },
  "только температуры": {
    "en": "only temperatures",
    "es": "solo temperaturas",
    "ar": "فقط درجات الحرارة"
  },
  "никакой конструкции": {
    "en": "no construction",
    "es": "sin construcción específica",
    "ar": "لا بناء"
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
    "en": "v = 0 in the train car",
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
    "ar": "كل مرحلة —"
  },
  "деление на время": {
    "en": "division by time",
    "es": "división por tiempo",
    "ar": "القسمة على الزمن"
  },
  "a = скорость изменения скорости": {
    "en": "a = rate of change of velocity",
    "es": "a = tasa de cambio de la velocidad",
    "ar": "a = معدل تغير السرعة"
  },
  "наклон прямой = ускорение": {
    "en": "slope of line = acceleration",
    "es": "pendiente de la recta = aceleración",
    "ar": "ميل المستقيم = التسارع"
  },
  "площадь трапеции = перемещение": {
    "en": "area of trapezoid = displacement",
    "es": "área del trapecio = desplazamiento",
    "ar": "مساحة شبه المنحرف = الإزاحة"
  },
  "v&#8320;t — равномерная часть": {
    "en": "v&#8320;t — uniform part",
    "es": "v&#8320;t — parte uniforme",
    "ar": "v₀t — الجزء المنتظم"
  },
  "сил нет — скорость постоянна": {
    "en": "no forces — velocity constant",
    "es": "no hay fuerzas — velocidad constante",
    "ar": "لا قوى — السرعة ثابتة"
  },
  "равные промежутки за равное время": {
    "en": "equal intervals in equal time",
    "es": "distancias iguales en tiempos iguales",
    "ar": "مسافات متساوية في أزمنة متساوية"
  },
  "вдвое большая сила — вдвое большее ускорение": {
    "en": "twice the force — twice the acceleration",
    "es": "fuerza doble — aceleración doble",
    "ar": "ضعف القوة — ضعف التسارع"
  },
  "та же сила: вдвое тяжелее — вдвое медленнее разгон": {
    "en": "same force: twice mass — half acceleration",
    "es": "misma fuerza: masa doble — aceleración mitad",
    "ar": "نفس القوة: ضعف الكتلة — نصف التسارع"
  },
  "больше сила →": {
    "en": "more force →",
    "es": "más fuerza →",
    "ar": "قوة أكبر →"
  },
  "быстрее разгон": {
    "en": "faster acceleration",
    "es": "mayor aceleración",
    "ar": "تسارع أسرع"
  },
  "больше масса →": {
    "en": "more mass →",
    "es": "más masa →",
    "ar": "كتلة أكبر →"
  },
  "медленнее разгон": {
    "en": "slower acceleration",
    "es": "menor aceleración",
    "ar": "تسارع أبطأ"
  },
  "1 Н = 1 кг · 1 м/с²": {
    "en": "1 N = 1 kg · 1 m/s²",
    "es": "1 N = 1 kg · 1 m/s²",
    "ar": "1 N = 1 kg · 1 m/s²"
  },
  "масса уходит назад": {
    "en": "mass goes backward",
    "es": "la masa se va hacia atrás",
    "ar": "الكتلة تندفع للخلف"
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
    "es": "iguales en magnitud, aplicadas a CUERPOS DIFERENTES",
    "ar": "متساويان في المقدار، على جسمين مختلفين"
  },
  "замкнутая система": {
    "en": "closed system",
    "es": "sistema cerrado",
    "ar": "نظام مغلق"
  },
  "внутренние силы гасятся → Σp = const": {
    "en": "internal forces cancel → Σp = const",
    "es": "fuerzas internas se cancelan → Σp = const",
    "ar": "القوى الداخلية تتلاشى → Σp = ثابت"
  },
  "упругий": {
    "en": "elastic",
    "es": "elástico",
    "ar": "مرن"
  },
  "разлетелись,": {
    "en": "scattered,",
    "es": "se separaron,",
    "ar": "تفرقت،"
  },
  "E сохранилась": {
    "en": "E conserved",
    "es": "E conservada",
    "ar": "E محفوظة"
  },
  "неупругий": {
    "en": "inelastic",
    "es": "inelástico",
    "ar": "غير مرن"
  },
  "слиплись,": {
    "en": "stuck together,",
    "es": "fusionados,",
    "ar": "التصقت،"
  },
  "часть E → тепло": {
    "en": "part of E → heat",
    "es": "parte de E → calor",
    "ar": "جزء من E → حرارة"
  },
  "импульс сохраняется в обоих случаях": {
    "en": "momentum conserved in both cases",
    "es": "el impulso se conserva en ambos casos",
    "ar": "الزخم محفوظ في كلتا الحالتين"
  },
  "сдвиг в пространстве": {
    "en": "shift in space",
    "es": "desplazamiento espacial",
    "ar": "الانتقال في الفضاء"
  },
  "импульс": {
    "en": "momentum",
    "es": "momento lineal",
    "ar": "الزخم"
  },
  "сдвиг во времени": {
    "en": "shift in time",
    "es": "desplazamiento temporal",
    "ar": "الانتقال في الزمن"
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
    "en": "magnitude v",
    "es": "magnitud de v",
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
    "ar": "إذن هناك تسارع"
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
    "en": "observer stationary",
    "es": "observador en reposo",
    "ar": "المراقب ساكن"
  },
  "сила есть,": {
    "en": "force present,",
    "es": "hay fuerza,",
    "ar": "توجد قوة،"
  },
  "ускорение есть,": {
    "en": "acceleration present,",
    "es": "hay aceleración,",
    "ar": "يوجد تسارع،"
  },
  "F = ma сходится": {
    "en": "F = ma works",
    "es": "F = ma se cumple",
    "ar": "F = ma صحيحة"
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
    "es": "fuerzas equilibradas —",
    "ar": "القوى متوازنة —"
  },
  "но откуда F?": {
    "en": "but where does F come from?",
    "es": "pero ¿de dónde viene F?",
    "ar": "لكن من أين القوة؟"
  },
  "кабина ускоряется": {
    "en": "cab accelerates",
    "es": "la cabina acelera",
    "ar": "المقصورة تتسارع"
  },
  "нет источника,": {
    "en": "no source,",
    "es": "no hay fuente,",
    "ar": "لا مصدر،"
  },
  "нет пары по": {
    "en": "no pair according to",
    "es": "no hay par por",
    "ar": "لا زوج حسب"
  },
  "третьему закону": {
    "en": "third law",
    "es": "tercera ley",
    "ar": "القانون الثالث"
  },
  "оттянули вправо —": {
    "en": "pulled to the right —",
    "es": "se tiró a la derecha —",
    "ar": "سحبنا لليمين —"
  },
  "тянет влево": {
    "en": "pulls left",
    "es": "tira hacia la izquierda",
    "ar": "يجذب لليسار"
  },
  "дважды продифференцировали — вернулись с минусом": {
    "en": "differentiated twice — got back with a minus",
    "es": "se derivó dos veces — regresó con signo menos",
    "ar": "فاضلنا مرتين — عدنا بإشارة سالبة"
  },
  "A сокращается": {
    "en": "A cancels",
    "es": "A se cancela",
    "ar": "A تُختصر"
  },
  "уравнению всё равно, как сильно качнули": {
    "en": "equation doesn't care how hard you push",
    "es": "no importa la amplitud del desplazamiento",
    "ar": "المعادلة مستقلة عن السعة"
  },
  "T — общий": {
    "en": "T common",
    "es": "T — común",
    "ar": "T — مشترك"
  },
  "большая A": {
    "en": "large A",
    "es": "A grande",
    "ar": "A كبيرة"
  },
  "малая A": {
    "en": "small A",
    "es": "A pequeña",
    "ar": "A صغيرة"
  },
  "тень": {
    "en": "shadow",
    "es": "sombra",
    "ar": "ظل"
  },
  "точка вращается": {
    "en": "point rotates",
    "es": "el punto gira",
    "ar": "النقطة تدور"
  },
  "тень колеблется": {
    "en": "shadow oscillates",
    "es": "la sombra oscila",
    "ar": "الظل يتذبذب"
  },
  "край": {
    "en": "edge",
    "es": "borde",
    "ar": "الطرف"
  },
  "центр": {
    "en": "center",
    "es": "centro",
    "ar": "المركز"
  },
  "зелёное — движение, охра — пружина": {
    "en": "green — motion, ochre — spring",
    "es": "verde — movimiento, ocre — resorte",
    "ar": "الأخضر — الحركة، المغرة — الزنبرك"
  },
  "сумма всегда одна: E = kA²/2": {
    "en": "sum always the same: E = kA²/2",
    "es": "la suma siempre es la misma: E = kA²/2",
    "ar": "المجموع ثابت دائمًا: E = kA²/2"
  },
  "у дна — парабола": {
    "en": "at bottom — parabola",
    "es": "en el fondo — parábola",
    "ar": "في القاع — قطع مكافئ"
  },
  "сложная яма": {
    "en": "complex well",
    "es": "pozo complejo",
    "ar": "بئر معقد"
  },
  "значит внутри спрятана пружина": {
    "en": "means a spring hidden inside",
    "es": "significa que dentro hay un resorte escondido",
    "ar": "أي أن بداخله زنبرك مخفي"
  },
  "дальше от оси —": {
    "en": "farther from axis —",
    "es": "más lejos del eje —",
    "ar": "أبعد عن المحور —"
  },
  "больше момент": {
    "en": "greater moment",
    "es": "mayor momento de inercia",
    "ar": "عزم أكبر"
  },
  "момент импульса учитывает плечо": {
    "en": "angular momentum includes lever arm",
    "es": "el momento angular considera el brazo de momento",
    "ar": "الزخم الزاوي يأخذ في الاعتبار الذراع"
  },
  "руки раскинуты: I большой, ω малая": {
    "en": "arms spread: I large, ω small",
    "es": "brazos extendidos: I grande, ω pequeña",
    "ar": "الذراعان ممدودتان: I كبير، ω صغير"
  },
  "руки прижаты: I малый, ω большая": {
    "en": "arms pressed: I small, ω large",
    "es": "brazos pegados: I pequeño, ω grande",
    "ar": "الذراعان مضمومتان: I صغير، ω كبير"
  },
  "срыв": {
    "en": "slip",
    "es": "deslizamiento",
    "ar": "انزلاق"
  },
  "покоя": {
    "en": "static",
    "es": "reposo",
    "ar": "سكون"
  },
  "скольжения": {
    "en": "kinetic",
    "es": "deslizamiento",
    "ar": "انزلاق"
  },
  "тяга": {
    "en": "traction",
    "es": "tracción",
    "ar": "الجر"
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
    "en": "contact points same number — friction force same",
    "es": "puntos de contacto iguales — misma fuerza de fricción",
    "ar": "عدد نقاط التلامس نفس العدد — قوة الاحتكاك نفسها"
  },
  "начало": {
    "en": "start",
    "es": "inicio",
    "ar": "بداية"
  },
  "конец": {
    "en": "end",
    "es": "fin",
    "ar": "نهاية"
  },
  "путей бесконечно много": {
    "en": "infinitely many paths",
    "es": "infinitos caminos",
    "ar": "مسارات لا نهائية"
  },
  "истинный": {
    "en": "true",
    "es": "verdadero",
    "ar": "حقيقي"
  },
  "K − U на каждом шаге": {
    "en": "K − U at each step",
    "es": "K − U en cada paso",
    "ar": "K − U في كل خطوة"
  },
  "сумма по всем шагам и есть действие": {
    "en": "sum over all steps is the action",
    "es": "suma sobre todos los pasos es la acción",
    "ar": "مجموع كل الخطوات هو الفعل"
  },
  "истинный путь": {
    "en": "true path",
    "es": "camino verdadero",
    "ar": "المسار الحقيقي"
  },
  "отклонение": {
    "en": "deviation",
    "es": "desviación",
    "ar": "انحراف"
  },
  "действие S": {
    "en": "action S",
    "es": "acción S",
    "ar": "الفعل S"
  },
  "одно и то же растяжение повсюду": {
    "en": "the same stretching everywhere",
    "es": "el mismo estiramiento en todas partes",
    "ar": "التمدّد نفسه في كل مكان"
  },
  "до": {
    "en": "before",
    "es": "antes",
    "ar": "قبل"
  },
  "после": {
    "en": "after",
    "es": "después",
    "ar": "بعد"
  },
  "метка стоит на своём номере, растёт расстояние": {
    "en": "each mark keeps its number; the distance grows",
    "es": "cada marca conserva su número; crece la distancia",
    "ar": "كل علامة تحفظ رقمها، والمسافة تنمو"
  },
  "дальше — значит быстрее": {
    "en": "farther means faster",
    "es": "más lejos significa más rápido",
    "ar": "الأبعد يعني الأسرع"
  },
  "наблюдатель": {
    "en": "observer",
    "es": "observador",
    "ar": "المراقب"
  },
  "v = H₀·d — та же картина из любой точки": {
    "en": "v = H₀·d — the same picture from any point",
    "es": "v = H₀·d: la misma imagen desde cualquier punto",
    "ar": "v = H₀·d — الصورة نفسها من أي نقطة"
  },
  "волна растягивается вместе с пространством": {
    "en": "the wave stretches along with space",
    "es": "la onda se estira junto con el espacio",
    "ar": "الموجة تستطيل مع الفضاء"
  },
  "галактика": {
    "en": "galaxy",
    "es": "galaxia",
    "ar": "مجرّة"
  },
  "мы": {
    "en": "us",
    "es": "nosotros",
    "ar": "نحن"
  },
  "короткая волна": {
    "en": "short wave",
    "es": "onda corta",
    "ar": "موجة قصيرة"
  },
  "длинная — краснее": {
    "en": "longer — redder",
    "es": "más larga: más roja",
    "ar": "أطول — أكثر حمرة"
  },
  "H = скорость роста ÷ текущий размер": {
    "en": "H = growth rate ÷ current size",
    "es": "H = ritmo de crecimiento ÷ tamaño actual",
    "ar": "H = معدّل النمو ÷ الحجم الحالي"
  },
  "a — размер сейчас": {
    "en": "a — size now",
    "es": "a: tamaño actual",
    "ar": "a — الحجم الآن"
  },
  "одно и то же H для всех пар галактик": {
    "en": "the same H for every pair of galaxies",
    "es": "el mismo H para cada par de galaxias",
    "ar": "نفس H لكل زوج من المجرّات"
  },
  "1/H₀ ≈ 14 млрд лет — оценка, не возраст": {
    "en": "1/H₀ ≈ 14 Gyr — an estimate, not the age",
    "es": "1/H₀ ≈ 14 mil millones de años: una estimación, no la edad",
    "ar": "1/H₀ ≈ 14 مليار سنة — تقدير لا عمر"
  },
  "от линии в спектре к расстоянию": {
    "en": "from a spectral line to a distance",
    "es": "de una línea espectral a una distancia",
    "ar": "من خط طيفي إلى مسافة"
  },
  "спектр": {
    "en": "spectrum",
    "es": "espectro",
    "ar": "الطيف"
  },
  "последний шаг верен только при малом z": {
    "en": "the last step holds only for small z",
    "es": "el último paso solo vale para z pequeño",
    "ar": "الخطوة الأخيرة تصحّ فقط عند z الصغير"
  },
  "растяжение остужает": {
    "en": "stretching cools",
    "es": "el estiramiento enfría",
    "ar": "التمدّد يبرّد"
  },
  "3000 K": {
    "en": "3000 K",
    "es": "3000 K",
    "ar": "3000 K"
  },
  "2,7 K": {
    "en": "2.7 K",
    "es": "2,7 K",
    "ar": "2.7 K"
  },
  "T ∝ 1/a: во сколько раз выросла Вселенная, во столько остыл свет": {
    "en": "T ∝ 1/a: the light cooled by the factor the universe grew",
    "es": "T ∝ 1/a: la luz se enfrió tanto como creció el universo",
    "ar": "T ∝ 1/a: برد الضوء بمقدار ما نما الكون"
  },
  "плазма: свет в тумане": {
    "en": "plasma: light in fog",
    "es": "plasma: luz en la niebla",
    "ar": "بلازما: ضوء في ضباب"
  },
  "атомы: свет уходит": {
    "en": "atoms: light escapes",
    "es": "átomos: la luz escapa",
    "ar": "ذرّات: الضوء ينطلق"
  },
  "до нас": {
    "en": "to us",
    "es": "hasta nosotros",
    "ar": "إلينا"
  },
  "3000 K — граница прозрачности": {
    "en": "3000 K — the transparency threshold",
    "es": "3000 K: el umbral de transparencia",
    "ar": "3000 K — حدّ الشفافية"
  },
  "длина волны →": {
    "en": "wavelength →",
    "es": "longitud de onda →",
    "ar": "طول الموجة →"
  },
  "λ пика обратно пропорциональна T": {
    "en": "the peak λ is inversely proportional to T",
    "es": "la λ del pico es inversamente proporcional a T",
    "ar": "λ القمة تتناسب عكسياً مع T"
  },
  "одинаковая температура без общей истории": {
    "en": "the same temperature with no shared history",
    "es": "la misma temperatura sin historia común",
    "ar": "الحرارة نفسها بلا تاريخ مشترك"
  },
  "её горизонт": {
    "en": "its horizon",
    "es": "su horizonte",
    "ar": "أفقها"
  },
  "круги не пересекаются: сигнал не успевал пройти": {
    "en": "the circles do not overlap: no signal could pass",
    "es": "los círculos no se cruzan: ninguna señal pudo pasar",
    "ar": "الدائرتان لا تتقاطعان: لم تمرّ أي إشارة"
  },
  "тянет только то, что внутри орбиты": {
    "en": "only what is inside the orbit pulls",
    "es": "solo tira lo que está dentro de la órbita",
    "ar": "لا يجذب إلا ما هو داخل المدار"
  },
  "внешние слои не притягивают: их вклад взаимно гасится": {
    "en": "outer shells do not pull: their contributions cancel",
    "es": "las capas externas no tiran: sus aportes se cancelan",
    "ar": "الطبقات الخارجية لا تجذب: مساهماتها تتلاشى"
  },
  "как должно быть, если вся масса видна": {
    "en": "how it should look if all mass is visible",
    "es": "cómo debería ser si toda la masa es visible",
    "ar": "كيف ينبغي أن يكون لو كانت كل الكتلة مرئية"
  },
  "радиус →": {
    "en": "radius →",
    "es": "radio →",
    "ar": "نصف القطر →"
  },
  "скорость": {
    "en": "speed",
    "es": "velocidad",
    "ar": "السرعة"
  },
  "v ∝ 1/√r — как у планет вокруг Солнца": {
    "en": "v ∝ 1/√r — like planets around the Sun",
    "es": "v ∝ 1/√r: como los planetas alrededor del Sol",
    "ar": "v ∝ 1/√r — مثل الكواكب حول الشمس"
  },
  "что измеряют на самом деле": {
    "en": "what is actually measured",
    "es": "lo que se mide en realidad",
    "ar": "ما يُقاس فعلاً"
  },
  "измерено": {
    "en": "measured",
    "es": "medido",
    "ar": "مقيس"
  },
  "видимая масса": {
    "en": "visible mass",
    "es": "masa visible",
    "ar": "الكتلة المرئية"
  },
  "разница и есть тёмное гало": {
    "en": "the gap is the dark halo",
    "es": "la diferencia es el halo oscuro",
    "ar": "الفرق هو الهالة المعتمة"
  },
  "что происходит с плотностями при росте": {
    "en": "what happens to the densities as it grows",
    "es": "qué pasa con las densidades al crecer",
    "ar": "ماذا يحدث للكثافات مع النمو"
  },
  "материя ∝ 1/a³": {
    "en": "matter ∝ 1/a³",
    "es": "materia ∝ 1/a³",
    "ar": "المادة ∝ 1/a³"
  },
  "тёмная энергия — постоянна": {
    "en": "dark energy stays constant",
    "es": "la energía oscura permanece constante",
    "ar": "الطاقة المعتمة تبقى ثابتة"
  },
  "размер a →": {
    "en": "size a →",
    "es": "tamaño a →",
    "ar": "الحجم a →"
  },
  "пересечение кривых — момент смены знака ускорения": {
    "en": "where the curves cross, the sign of acceleration flips",
    "es": "donde se cruzan las curvas cambia el signo de la aceleración",
    "ar": "عند تقاطع المنحنيين تنقلب إشارة التسارع"
  },
  "раздувание одной выровнявшейся области": {
    "en": "one smoothed-out region blown up",
    "es": "una sola región ya uniforme, inflada",
    "ar": "منطقة واحدة تجانست ثم انتفخت"
  },
  "до: успела выровняться": {
    "en": "before: had time to even out",
    "es": "antes: tuvo tiempo de uniformarse",
    "ar": "قبل: أتيح لها أن تتجانس"
  },
  "видимая часть": {
    "en": "the visible part",
    "es": "la parte visible",
    "ar": "الجزء المرئي"
  },
  "после: та же однородность на всём небе": {
    "en": "after: the same uniformity across the whole sky",
    "es": "después: la misma uniformidad en todo el cielo",
    "ar": "بعد: التجانس نفسه في كل السماء"
  },
  "сначала тормозит, потом разгоняется": {
    "en": "first it slows, then it speeds up",
    "es": "primero frena, luego acelera",
    "ar": "يتباطأ أولاً ثم يتسارع"
  },
  "z ≈ 0,7": {
    "en": "z ≈ 0.7",
    "es": "z ≈ 0,7",
    "ar": "z ≈ 0.7"
  },
  "торможение": {
    "en": "slowing down",
    "es": "frenado",
    "ar": "تباطؤ"
  },
  "ускорение": {
    "en": "acceleration",
    "es": "aceleración",
    "ar": "تسارع"
  },
  "время →": {
    "en": "time →",
    "es": "tiempo →",
    "ar": "الزمن →"
  },
  "одинаковая вспышка как линейка": {
    "en": "an identical flash used as a ruler",
    "es": "un destello idéntico usado como regla",
    "ar": "وميض متطابق يُستخدم مسطرة"
  },
  "близко": {
    "en": "near",
    "es": "cerca",
    "ar": "قريب"
  },
  "дальше": {
    "en": "farther",
    "es": "más lejos",
    "ar": "أبعد"
  },
  "ещё дальше": {
    "en": "farther still",
    "es": "aún más lejos",
    "ar": "أبعد أيضاً"
  },
  "светимость одна — значит видимая яркость меряет расстояние": {
    "en": "same luminosity, so apparent brightness measures distance",
    "es": "misma luminosidad: el brillo aparente mide la distancia",
    "ar": "اللمعان نفسه، فالسطوع الظاهري يقيس المسافة"
  }
};
