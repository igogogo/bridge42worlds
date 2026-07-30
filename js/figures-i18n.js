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
    "ar": "الجدار",
    "fr": "paroi"
  },
  "долетят": {
    "en": "will reach",
    "es": "alcanzan",
    "ar": "تصل",
    "fr": "atteignent"
  },
  "за &#916;t": {
    "en": "in &#916;t",
    "es": "en &#916;t",
    "ar": "خلال Δt",
    "fr": "en &#916;t"
  },
  "много": {
    "en": "many",
    "es": "muchos",
    "ar": "كثير",
    "fr": "beaucoup"
  },
  "ударов": {
    "en": "collisions",
    "es": "impactos",
    "ar": "ضربات",
    "fr": "collisions"
  },
  "постоянная сила": {
    "en": "constant force",
    "es": "fuerza constante",
    "ar": "قوة ثابتة",
    "fr": "force constante"
  },
  "Па = Н / м²": {
    "en": "Pa = N / m²",
    "es": "Pa = N / m²",
    "ar": "Pa = N / m²",
    "fr": "Pa = N / m²"
  },
  "площадь стенки": {
    "en": "wall area",
    "es": "área de la pared",
    "ar": "مساحة الجدار",
    "fr": "aire de la paroi"
  },
  "ни одно направление": {
    "en": "no direction",
    "es": "ninguna dirección",
    "ar": "لا اتجاه",
    "fr": "aucune direction"
  },
  "не выделено": {
    "en": "not distinguished",
    "es": "privilegiada",
    "ar": "غير محدد",
    "fr": "non distinguée"
  },
  "k&#8342; — курс обмена": {
    "en": "k&#8342; — exchange rate",
    "es": "k&#8342; — tipo de cambio",
    "ar": "k′ — سعر الصرف",
    "fr": "k&#8342; — taux de change"
  },
  "Дж &#8596; К": {
    "en": "J &#8596; K",
    "es": "J &#8596; K",
    "ar": "J ↔ K",
    "fr": "J &#8596; K"
  },
  "микромир: N, m, v": {
    "en": "microcosm: N, m, v",
    "es": "microcosmos: N, m, v",
    "ar": "العالم المصغر: N, m, v",
    "fr": "microcosme : N, m, v"
  },
  "макромир: P, V, T": {
    "en": "macroworld: P, V, T",
    "es": "macrocosmos: P, V, T",
    "ar": "العالم الكبير: P, V, T",
    "fr": "macrocosme : P, V, T"
  },
  "T растёт": {
    "en": "T increases",
    "es": "T aumenta",
    "ar": "T تزداد",
    "fr": "T augmente"
  },
  "T стоит": {
    "en": "T constant",
    "es": "T constante",
    "ar": "T ثابت",
    "fr": "T constante"
  },
  "связи рвутся": {
    "en": "bonds break",
    "es": "los enlaces se rompen",
    "ar": "تنكسر الروابط",
    "fr": "rupture des liaisons"
  },
  "нагрев": {
    "en": "heating",
    "es": "calentamiento",
    "ar": "تسخين",
    "fr": "chauffage"
  },
  "67 кДж": {
    "en": "67 kJ",
    "es": "67 kJ",
    "ar": "67 kJ",
    "fr": "67 kJ"
  },
  "кипение": {
    "en": "boiling",
    "es": "ebullición",
    "ar": "غليان",
    "fr": "ébullition"
  },
  "452 кДж": {
    "en": "452 kJ",
    "es": "452 kJ",
    "ar": "452 kJ",
    "fr": "452 kJ"
  },
  "в 6,8 раза больше": {
    "en": "6.8 times larger",
    "es": "6.8 veces mayor",
    "ar": "أكبر بـ 6.8 مرة",
    "fr": "6,8 fois plus grand"
  },
  "пар": {
    "en": "vapor",
    "es": "vapor",
    "ar": "بخار",
    "fr": "vapeur"
  },
  "давление атмосферы": {
    "en": "atmospheric pressure",
    "es": "presión atmosférica",
    "ar": "ضغط الجو",
    "fr": "pression atmosphérique"
  },
  "пузырёк": {
    "en": "bubble",
    "es": "burbuja",
    "ar": "فقاعة",
    "fr": "bulle"
  },
  "раздвигает": {
    "en": "expands",
    "es": "empuja",
    "ar": "يفصل",
    "fr": "se dilate"
  },
  "только давление": {
    "en": "only pressure",
    "es": "solo presión",
    "ar": "فقط الضغط",
    "fr": "pression seulement"
  },
  "только температура": {
    "en": "only temperature",
    "es": "solo temperatura",
    "ar": "فقط درجة الحرارة",
    "fr": "température seulement"
  },
  "&#8747; каждую часть отдельно": {
    "en": "&#8747; each part separately",
    "es": "&#8747; cada parte por separado",
    "ar": "∫ كل جزء على حدة",
    "fr": "&#8747; chaque partie séparément"
  },
  "0,5 атм": {
    "en": "0.5 atm",
    "es": "0.5 atm",
    "ar": "0.5 atm",
    "fr": "0,5 atm"
  },
  "1 атм": {
    "en": "1 atm",
    "es": "1 atm",
    "ar": "1 atm",
    "fr": "1 atm"
  },
  "2 атм": {
    "en": "2 atm",
    "es": "2 atm",
    "ar": "2 atm",
    "fr": "2 atm"
  },
  "газ": {
    "en": "gas",
    "es": "gas",
    "ar": "غاز",
    "fr": "gaz"
  },
  "dU — нагрев": {
    "en": "dU — heating",
    "es": "dU — calentamiento",
    "ar": "dU — تسخين",
    "fr": "dU — chauffage"
  },
  "P·dV — работа": {
    "en": "P·dV — work",
    "es": "P·dV — trabajo",
    "ar": "P·dV — شغل",
    "fr": "P·dV — travail"
  },
  "ничего": {
    "en": "nothing",
    "es": "nada",
    "ar": "لا شيء",
    "fr": "rien"
  },
  "не пропадает": {
    "en": "nothing lost",
    "es": "no se pierde",
    "ar": "لا يختفي",
    "fr": "ne disparaît pas"
  },
  "до: 300 K": {
    "en": "before: 300 K",
    "es": "antes: 300 K",
    "ar": "قبل: 300 K",
    "fr": "avant : 300 K"
  },
  "сжали": {
    "en": "compressed",
    "es": "comprimido",
    "ar": "ضغط",
    "fr": "comprimé"
  },
  "после: 420 K": {
    "en": "after: 420 K",
    "es": "después: 420 K",
    "ar": "بعد: 420 K",
    "fr": "après : 420 K"
  },
  "тепло": {
    "en": "heat",
    "es": "calor",
    "ar": "حرارة",
    "fr": "chaleur"
  },
  "не уходит": {
    "en": "does not escape",
    "es": "no se escapa",
    "ar": "لا يخرج",
    "fr": "ne s'échappe pas"
  },
  "адиабата": {
    "en": "adiabat",
    "es": "adiabática",
    "ar": "أدياباتي",
    "fr": "adiabatique"
  },
  "изотерма P·V": {
    "en": "isotherm P·V",
    "es": "isoterma P·V",
    "ar": "إيزوثيرم P·V",
    "fr": "isotherme P·V"
  },
  "работа": {
    "en": "work",
    "es": "trabajo",
    "ar": "شغل",
    "fr": "travail"
  },
  "площадь": {
    "en": "area",
    "es": "área",
    "ar": "مساحة",
    "fr": "aire"
  },
  "= работа": {
    "en": "= work",
    "es": "= trabajo",
    "ar": "= شغل",
    "fr": "= travail"
  },
  "нагреватель": {
    "en": "heater",
    "es": "foco caliente",
    "ar": "مسخن",
    "fr": "source chaude"
  },
  "холодильник": {
    "en": "refrigerator",
    "es": "foco frío",
    "ar": "مبرد",
    "fr": "source froide"
  },
  "машина": {
    "en": "engine",
    "es": "máquina",
    "ar": "آلة",
    "fr": "moteur"
  },
  "Q&#1093; никогда не ноль": {
    "en": "Q&#1093; never zero",
    "es": "Q&#1093; nunca es cero",
    "ar": "Qх ليس صفرًا أبدًا",
    "fr": "Q&#1093; jamais nul"
  },
  "только температуры": {
    "en": "only temperatures",
    "es": "solo temperaturas",
    "ar": "فقط درجات الحرارة",
    "fr": "températures seulement"
  },
  "никакой конструкции": {
    "en": "no construction",
    "es": "sin construcción específica",
    "ar": "لا بناء",
    "fr": "aucune construction"
  },
  "пассажир": {
    "en": "passenger",
    "es": "pasajero",
    "ar": "راكب",
    "fr": "passager"
  },
  "100 км/ч": {
    "en": "100 km/h",
    "es": "100 km/h",
    "ar": "100 km/h",
    "fr": "100 km/h"
  },
  "наблюдатель": {
    "en": "observer",
    "es": "observador",
    "ar": "المراقب",
    "fr": "observateur"
  },
  "v = 0 в вагоне": {
    "en": "v = 0 in the train car",
    "es": "v = 0 en el vagón",
    "ar": "v = 0 في العربة",
    "fr": "v = 0 dans le wagon"
  },
  "v = 100 с перрона": {
    "en": "v = 100 from the platform",
    "es": "v = 100 desde el andén",
    "ar": "v = 100 من الرصيف",
    "fr": "v = 100 depuis le quai"
  },
  "секущая": {
    "en": "secant",
    "es": "secante",
    "ar": "قاطع",
    "fr": "sécante"
  },
  "касательная": {
    "en": "tangent",
    "es": "tangente",
    "ar": "مماس",
    "fr": "tangente"
  },
  "м": {
    "en": "m",
    "es": "m",
    "ar": "m",
    "fr": "m"
  },
  "м/с": {
    "en": "m/s",
    "es": "m/s",
    "ar": "m/s",
    "fr": "m/s"
  },
  "м/с²": {
    "en": "m/s²",
    "es": "m/s²",
    "ar": "m/s²",
    "fr": "m/s²"
  },
  "каждая ступень —": {
    "en": "each step —",
    "es": "cada paso —",
    "ar": "كل مرحلة —",
    "fr": "chaque étape —"
  },
  "деление на время": {
    "en": "division by time",
    "es": "división por tiempo",
    "ar": "القسمة على الزمن",
    "fr": "division par le temps"
  },
  "a = скорость изменения скорости": {
    "en": "a = rate of change of velocity",
    "es": "a = tasa de cambio de la velocidad",
    "ar": "a = معدل تغير السرعة",
    "fr": "a = taux de variation de la vitesse"
  },
  "наклон прямой = ускорение": {
    "en": "slope of line = acceleration",
    "es": "pendiente de la recta = aceleración",
    "ar": "ميل المستقيم = التسارع",
    "fr": "pente de la droite = accélération"
  },
  "площадь трапеции = перемещение": {
    "en": "area of trapezoid = displacement",
    "es": "área del trapecio = desplazamiento",
    "ar": "مساحة شبه المنحرف = الإزاحة",
    "fr": "aire du trapèze = déplacement"
  },
  "v&#8320;t — равномерная часть": {
    "en": "v&#8320;t — uniform part",
    "es": "v&#8320;t — parte uniforme",
    "ar": "v₀t — الجزء المنتظم",
    "fr": "v&#8320;t — partie uniforme"
  },
  "сил нет — скорость постоянна": {
    "en": "no forces — velocity constant",
    "es": "no hay fuerzas — velocidad constante",
    "ar": "لا قوى — السرعة ثابتة",
    "fr": "aucune force — vitesse constante"
  },
  "равные промежутки за равное время": {
    "en": "equal intervals in equal time",
    "es": "distancias iguales en tiempos iguales",
    "ar": "مسافات متساوية في أزمنة متساوية",
    "fr": "intervalles égaux en temps égal"
  },
  "вдвое большая сила — вдвое большее ускорение": {
    "en": "twice the force — twice the acceleration",
    "es": "fuerza doble — aceleración doble",
    "ar": "ضعف القوة — ضعف التسارع",
    "fr": "force double — accélération double"
  },
  "та же сила: вдвое тяжелее — вдвое медленнее разгон": {
    "en": "same force: twice mass — half acceleration",
    "es": "misma fuerza: masa doble — aceleración mitad",
    "ar": "نفس القوة: ضعف الكتلة — نصف التسارع",
    "fr": "même force : masse double — accélération moitié"
  },
  "больше сила →": {
    "en": "more force →",
    "es": "más fuerza →",
    "ar": "قوة أكبر →",
    "fr": "plus de force →"
  },
  "быстрее разгон": {
    "en": "faster acceleration",
    "es": "mayor aceleración",
    "ar": "تسارع أسرع",
    "fr": "accélération plus rapide"
  },
  "больше масса →": {
    "en": "more mass →",
    "es": "más masa →",
    "ar": "كتلة أكبر →",
    "fr": "plus de masse →"
  },
  "медленнее разгон": {
    "en": "slower acceleration",
    "es": "menor aceleración",
    "ar": "تسارع أبطأ",
    "fr": "accélération plus lente"
  },
  "1 Н = 1 кг · 1 м/с²": {
    "en": "1 N = 1 kg · 1 m/s²",
    "es": "1 N = 1 kg · 1 m/s²",
    "ar": "1 N = 1 kg · 1 m/s²",
    "fr": "1 N = 1 kg · 1 m/s²"
  },
  "масса уходит назад": {
    "en": "mass goes backward",
    "es": "la masa se va hacia atrás",
    "ar": "الكتلة تندفع للخلف",
    "fr": "masse recule"
  },
  "верно даже когда": {
    "en": "true even when",
    "es": "cierto incluso cuando",
    "ar": "صحيح حتى عندما",
    "fr": "vrai même quand"
  },
  "масса меняется": {
    "en": "mass changes",
    "es": "la masa cambia",
    "ar": "الكتلة تتغير",
    "fr": "la masse change"
  },
  "равны по величине, приложены к РАЗНЫМ телам": {
    "en": "equal in magnitude, applied to DIFFERENT bodies",
    "es": "iguales en magnitud, aplicadas a CUERPOS DIFERENTES",
    "ar": "متساويان في المقدار، على جسمين مختلفين",
    "fr": "égales en grandeur, appliquées à des corps DIFFÉRENTS"
  },
  "замкнутая система": {
    "en": "closed system",
    "es": "sistema cerrado",
    "ar": "نظام مغلق",
    "fr": "système fermé"
  },
  "внутренние силы гасятся → Σp = const": {
    "en": "internal forces cancel → Σp = const",
    "es": "fuerzas internas se cancelan → Σp = const",
    "ar": "القوى الداخلية تتلاشى → Σp = ثابت",
    "fr": "forces internes s'annulent → Σp = const"
  },
  "упругий": {
    "en": "elastic",
    "es": "elástico",
    "ar": "مرن",
    "fr": "élastique"
  },
  "разлетелись,": {
    "en": "scattered,",
    "es": "se separaron,",
    "ar": "تفرقت،",
    "fr": "dispersés,"
  },
  "E сохранилась": {
    "en": "E conserved",
    "es": "E conservada",
    "ar": "E محفوظة",
    "fr": "E conservée"
  },
  "неупругий": {
    "en": "inelastic",
    "es": "inelástico",
    "ar": "غير مرن",
    "fr": "inélastique"
  },
  "слиплись,": {
    "en": "stuck together,",
    "es": "fusionados,",
    "ar": "التصقت،",
    "fr": "collés,"
  },
  "часть E → тепло": {
    "en": "part of E → heat",
    "es": "parte de E → calor",
    "ar": "جزء من E → حرارة",
    "fr": "partie de E → chaleur"
  },
  "импульс сохраняется в обоих случаях": {
    "en": "momentum conserved in both cases",
    "es": "el impulso se conserva en ambos casos",
    "ar": "الزخم محفوظ في كلتا الحالتين",
    "fr": "impulsion conservée dans les deux cas"
  },
  "сдвиг в пространстве": {
    "en": "shift in space",
    "es": "desplazamiento espacial",
    "ar": "الانتقال في الفضاء",
    "fr": "décalage spatial"
  },
  "импульс": {
    "en": "momentum",
    "es": "momento lineal",
    "ar": "الزخم",
    "fr": "impulsion"
  },
  "сдвиг во времени": {
    "en": "shift in time",
    "es": "desplazamiento temporal",
    "ar": "الانتقال في الزمن",
    "fr": "décalage temporel"
  },
  "энергия": {
    "en": "energy",
    "es": "energía",
    "ar": "الطاقة",
    "fr": "énergie"
  },
  "поворот": {
    "en": "rotation",
    "es": "rotación",
    "ar": "الدوران",
    "fr": "rotation"
  },
  "момент импульса": {
    "en": "angular momentum",
    "es": "momento angular",
    "ar": "الزخم الزاوي",
    "fr": "moment cinétique"
  },
  "симметрия рождает закон сохранения": {
    "en": "symmetry gives conservation law",
    "es": "la simetría genera una ley de conservación",
    "ar": "التناظر يولد قانون الحفظ",
    "fr": "symétrie engendre loi de conservation"
  },
  "величина v": {
    "en": "magnitude v",
    "es": "magnitud de v",
    "ar": "مقدار v",
    "fr": "magnitude v"
  },
  "постоянна,": {
    "en": "constant,",
    "es": "constante,",
    "ar": "ثابت،",
    "fr": "constante,"
  },
  "направление": {
    "en": "direction",
    "es": "dirección",
    "ar": "الاتجاه",
    "fr": "direction"
  },
  "меняется": {
    "en": "changes",
    "es": "cambia",
    "ar": "يتغير",
    "fr": "change"
  },
  "значит есть ускорение": {
    "en": "so there is acceleration",
    "es": "significa que hay aceleración",
    "ar": "إذن هناك تسارع",
    "fr": "donc accélération"
  },
  "треугольник радиусов": {
    "en": "triangle of radii",
    "es": "triángulo de radios",
    "ar": "مثلث أنصاف الأقطار",
    "fr": "triangle des rayons"
  },
  "треугольник скоростей": {
    "en": "triangle of velocities",
    "es": "triángulo de velocidades",
    "ar": "مثلث السرعات",
    "fr": "triangle des vitesses"
  },
  "всегда к центру": {
    "en": "always toward center",
    "es": "siempre hacia el centro",
    "ar": "دائماً نحو المركز",
    "fr": "toujours vers le centre"
  },
  "наблюдатель стоит": {
    "en": "observer stationary",
    "es": "observador en reposo",
    "ar": "المراقب ساكن",
    "fr": "observateur immobile"
  },
  "сила есть,": {
    "en": "force present,",
    "es": "hay fuerza,",
    "ar": "توجد قوة،",
    "fr": "force présente,"
  },
  "ускорение есть,": {
    "en": "acceleration present,",
    "es": "hay aceleración,",
    "ar": "يوجد تسارع،",
    "fr": "accélération présente,"
  },
  "F = ma сходится": {
    "en": "F = ma works",
    "es": "F = ma se cumple",
    "ar": "F = ma صحيحة",
    "fr": "F = ma fonctionne"
  },
  "наблюдатель вращается": {
    "en": "observer rotates",
    "es": "observador gira",
    "ar": "المراقب يدور",
    "fr": "observateur tourne"
  },
  "тело покоится,": {
    "en": "body is at rest,",
    "es": "el cuerpo está en reposo,",
    "ar": "الجسم ساكن،",
    "fr": "corps au repos,"
  },
  "силы уравновешены —": {
    "en": "forces are balanced —",
    "es": "fuerzas equilibradas —",
    "ar": "القوى متوازنة —",
    "fr": "forces équilibrées —"
  },
  "но откуда F?": {
    "en": "but where does F come from?",
    "es": "pero ¿de dónde viene F?",
    "ar": "لكن من أين القوة؟",
    "fr": "mais d'où vient F ?"
  },
  "кабина ускоряется": {
    "en": "cab accelerates",
    "es": "la cabina acelera",
    "ar": "المقصورة تتسارع",
    "fr": "cabine accélère"
  },
  "нет источника,": {
    "en": "no source,",
    "es": "no hay fuente,",
    "ar": "لا مصدر،",
    "fr": "pas de source,"
  },
  "нет пары по": {
    "en": "no pair according to",
    "es": "no hay par por",
    "ar": "لا زوج حسب",
    "fr": "pas de paire selon"
  },
  "третьему закону": {
    "en": "third law",
    "es": "tercera ley",
    "ar": "القانون الثالث",
    "fr": "troisième loi"
  },
  "оттянули вправо —": {
    "en": "pulled to the right —",
    "es": "se tiró a la derecha —",
    "ar": "سحبنا لليمين —",
    "fr": "tiré vers la droite —"
  },
  "тянет влево": {
    "en": "pulls left",
    "es": "tira hacia la izquierda",
    "ar": "يجذب لليسار",
    "fr": "tire vers la gauche"
  },
  "дважды продифференцировали — вернулись с минусом": {
    "en": "differentiated twice — got back with a minus",
    "es": "se derivó dos veces — regresó con signo menos",
    "ar": "فاضلنا مرتين — عدنا بإشارة سالبة",
    "fr": "dérivé deux fois — revenu avec un moins"
  },
  "A сокращается": {
    "en": "A cancels",
    "es": "A se cancela",
    "ar": "A تُختصر",
    "fr": "A s'annule"
  },
  "уравнению всё равно, как сильно качнули": {
    "en": "equation doesn't care how hard you push",
    "es": "no importa la amplitud del desplazamiento",
    "ar": "المعادلة مستقلة عن السعة",
    "fr": "peu importe la force de la poussée"
  },
  "T — общий": {
    "en": "T common",
    "es": "T — común",
    "ar": "T — مشترك",
    "fr": "T — commun"
  },
  "большая A": {
    "en": "large A",
    "es": "A grande",
    "ar": "A كبيرة",
    "fr": "grand A"
  },
  "малая A": {
    "en": "small A",
    "es": "A pequeña",
    "ar": "A صغيرة",
    "fr": "petit A"
  },
  "тень": {
    "en": "shadow",
    "es": "sombra",
    "ar": "ظل",
    "fr": "ombre"
  },
  "точка вращается": {
    "en": "point rotates",
    "es": "el punto gira",
    "ar": "النقطة تدور",
    "fr": "point tourne"
  },
  "тень колеблется": {
    "en": "shadow oscillates",
    "es": "la sombra oscila",
    "ar": "الظل يتذبذب",
    "fr": "ombre oscille"
  },
  "край": {
    "en": "edge",
    "es": "borde",
    "ar": "الطرف",
    "fr": "bord"
  },
  "центр": {
    "en": "center",
    "es": "centro",
    "ar": "المركز",
    "fr": "centre"
  },
  "зелёное — движение, охра — пружина": {
    "en": "green — motion, ochre — spring",
    "es": "verde — movimiento, ocre — resorte",
    "ar": "الأخضر — الحركة، المغرة — الزنبرك",
    "fr": "vert — mouvement, ocre — ressort"
  },
  "сумма всегда одна: E = kA²/2": {
    "en": "sum always the same: E = kA²/2",
    "es": "la suma siempre es la misma: E = kA²/2",
    "ar": "المجموع ثابت دائمًا: E = kA²/2",
    "fr": "somme toujours la même : E = kA²/2"
  },
  "у дна — парабола": {
    "en": "at bottom — parabola",
    "es": "en el fondo — parábola",
    "ar": "في القاع — قطع مكافئ",
    "fr": "au fond — parabole"
  },
  "сложная яма": {
    "en": "complex well",
    "es": "pozo complejo",
    "ar": "بئر معقد",
    "fr": "puits complexe"
  },
  "значит внутри спрятана пружина": {
    "en": "means a spring hidden inside",
    "es": "significa que dentro hay un resorte escondido",
    "ar": "أي أن بداخله زنبرك مخفي",
    "fr": "donc ressort caché à l'intérieur"
  },
  "дальше от оси —": {
    "en": "farther from axis —",
    "es": "más lejos del eje —",
    "ar": "أبعد عن المحور —",
    "fr": "plus loin de l'axe —"
  },
  "больше момент": {
    "en": "greater moment",
    "es": "mayor momento de inercia",
    "ar": "عزم أكبر",
    "fr": "plus grand moment"
  },
  "момент импульса учитывает плечо": {
    "en": "angular momentum includes lever arm",
    "es": "el momento angular considera el brazo de momento",
    "ar": "الزخم الزاوي يأخذ في الاعتبار الذراع",
    "fr": "le moment cinétique tient compte du bras de levier"
  },
  "руки раскинуты: I большой, ω малая": {
    "en": "arms spread: I large, ω small",
    "es": "brazos extendidos: I grande, ω pequeña",
    "ar": "الذراعان ممدودتان: I كبير، ω صغير",
    "fr": "bras écartés : I grand, ω petit"
  },
  "руки прижаты: I малый, ω большая": {
    "en": "arms pressed: I small, ω large",
    "es": "brazos pegados: I pequeño, ω grande",
    "ar": "الذراعان مضمومتان: I صغير، ω كبير",
    "fr": "bras serrés : I petit, ω grand"
  },
  "срыв": {
    "en": "slip",
    "es": "deslizamiento",
    "ar": "انزلاق",
    "fr": "glissement"
  },
  "покоя": {
    "en": "static",
    "es": "reposo",
    "ar": "سكون",
    "fr": "statique"
  },
  "скольжения": {
    "en": "kinetic",
    "es": "deslizamiento",
    "ar": "انزلاق",
    "fr": "cinétique"
  },
  "тяга": {
    "en": "traction",
    "es": "tracción",
    "ar": "الجر",
    "fr": "traction"
  },
  "малая площадь": {
    "en": "small area",
    "es": "área pequeña",
    "ar": "مساحة صغيرة",
    "fr": "petite surface"
  },
  "большая площадь": {
    "en": "large area",
    "es": "área grande",
    "ar": "مساحة كبيرة",
    "fr": "grande surface"
  },
  "точек контакта столько же — сила трения та же": {
    "en": "contact points same number — friction force same",
    "es": "puntos de contacto iguales — misma fuerza de fricción",
    "ar": "عدد نقاط التلامس نفس العدد — قوة الاحتكاك نفسها",
    "fr": "même nombre de points de contact — force de frottement identique"
  },
  "начало": {
    "en": "start",
    "es": "inicio",
    "ar": "بداية",
    "fr": "début"
  },
  "конец": {
    "en": "end",
    "es": "fin",
    "ar": "نهاية",
    "fr": "fin"
  },
  "путей бесконечно много": {
    "en": "infinitely many paths",
    "es": "infinitos caminos",
    "ar": "مسارات لا نهائية",
    "fr": "une infinité de chemins"
  },
  "истинный": {
    "en": "true",
    "es": "verdadero",
    "ar": "حقيقي",
    "fr": "vrai"
  },
  "K − U на каждом шаге": {
    "en": "K − U at each step",
    "es": "K − U en cada paso",
    "ar": "K − U في كل خطوة",
    "fr": "K − U à chaque étape"
  },
  "сумма по всем шагам и есть действие": {
    "en": "sum over all steps is the action",
    "es": "suma sobre todos los pasos es la acción",
    "ar": "مجموع كل الخطوات هو الفعل",
    "fr": "la somme sur toutes les étapes est l'action"
  },
  "истинный путь": {
    "en": "true path",
    "es": "camino verdadero",
    "ar": "المسار الحقيقي",
    "fr": "chemin vrai"
  },
  "отклонение": {
    "en": "deviation",
    "es": "desviación",
    "ar": "انحراف",
    "fr": "écart"
  },
  "действие S": {
    "en": "action S",
    "es": "acción S",
    "ar": "الفعل S",
    "fr": "action S"
  },
  "одно и то же растяжение повсюду": {
    "en": "the same stretching everywhere",
    "es": "el mismo estiramiento en todas partes",
    "ar": "التمدّد نفسه في كل مكان",
    "fr": "le même étirement partout"
  },
  "до": {
    "en": "before",
    "es": "antes",
    "ar": "قبل",
    "fr": "avant"
  },
  "после": {
    "en": "after",
    "es": "después",
    "ar": "بعد",
    "fr": "après"
  },
  "метка стоит на своём номере, растёт расстояние": {
    "en": "each mark keeps its number; the distance grows",
    "es": "cada marca conserva su número; crece la distancia",
    "ar": "كل علامة تحفظ رقمها، والمسافة تنمو",
    "fr": "marque reste sur son numéro, distance croît"
  },
  "дальше — значит быстрее": {
    "en": "farther means faster",
    "es": "más lejos significa más rápido",
    "ar": "الأبعد يعني الأسرع",
    "fr": "plus loin signifie plus rapide"
  },
  "v = H₀·d — та же картина из любой точки": {
    "en": "v = H₀·d — the same picture from any point",
    "es": "v = H₀·d: la misma imagen desde cualquier punto",
    "ar": "v = H₀·d — الصورة نفسها من أي نقطة",
    "fr": "v = H₀·d — la même image de n'importe quel point"
  },
  "волна растягивается вместе с пространством": {
    "en": "the wave stretches along with space",
    "es": "la onda se estira junto con el espacio",
    "ar": "الموجة تستطيل مع الفضاء",
    "fr": "l'onde s'étire avec l'espace"
  },
  "галактика": {
    "en": "galaxy",
    "es": "galaxia",
    "ar": "مجرّة",
    "fr": "galaxie"
  },
  "мы": {
    "en": "us",
    "es": "nosotros",
    "ar": "نحن",
    "fr": "nous"
  },
  "короткая волна": {
    "en": "short wave",
    "es": "onda corta",
    "ar": "موجة قصيرة",
    "fr": "onde courte"
  },
  "длинная — краснее": {
    "en": "longer — redder",
    "es": "más larga: más roja",
    "ar": "أطول — أكثر حمرة",
    "fr": "longue — plus rouge"
  },
  "H = скорость роста ÷ текущий размер": {
    "en": "H = growth rate ÷ current size",
    "es": "H = ritmo de crecimiento ÷ tamaño actual",
    "ar": "H = معدّل النمو ÷ الحجم الحالي",
    "fr": "H = taux de croissance ÷ taille actuelle"
  },
  "a — размер сейчас": {
    "en": "a — size now",
    "es": "a: tamaño actual",
    "ar": "a — الحجم الآن",
    "fr": "a — taille maintenant"
  },
  "одно и то же H для всех пар галактик": {
    "en": "the same H for every pair of galaxies",
    "es": "el mismo H para cada par de galaxias",
    "ar": "نفس H لكل زوج من المجرّات",
    "fr": "le même H pour chaque paire de galaxies"
  },
  "1/H₀ ≈ 14 млрд лет — оценка, не возраст": {
    "en": "1/H₀ ≈ 14 Gyr — an estimate, not the age",
    "es": "1/H₀ ≈ 14 mil millones de años: una estimación, no la edad",
    "ar": "1/H₀ ≈ 14 مليار سنة — تقدير لا عمر",
    "fr": "1/H₀ ≈ 14 Gyr — une estimation, pas l'âge"
  },
  "от линии в спектре к расстоянию": {
    "en": "from a spectral line to a distance",
    "es": "de una línea espectral a una distancia",
    "ar": "من خط طيفي إلى مسافة",
    "fr": "de la raie spectrale à la distance"
  },
  "спектр": {
    "en": "spectrum",
    "es": "espectro",
    "ar": "الطيف",
    "fr": "spectre"
  },
  "последний шаг верен только при малом z": {
    "en": "the last step holds only for small z",
    "es": "el último paso solo vale para z pequeño",
    "ar": "الخطوة الأخيرة تصحّ فقط عند z الصغير",
    "fr": "la dernière étape n'est valable que pour z petit"
  }
};
