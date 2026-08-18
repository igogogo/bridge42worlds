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
  },
  "растяжение остужает": {
    "en": "stretching cools",
    "es": "el estiramiento enfría",
    "ar": "التمدّد يبرّد",
    "fr": "L'étirement refroidit"
  },
  "3000 K": {
    "en": "3000 K",
    "es": "3000 K",
    "ar": "3000 K",
    "fr": "3000 K"
  },
  "2,7 K": {
    "en": "2.7 K",
    "es": "2,7 K",
    "ar": "2.7 K",
    "fr": "2,7 K"
  },
  "T ∝ 1/a: во сколько раз выросла Вселенная, во столько остыл свет": {
    "en": "T ∝ 1/a: the light cooled by the factor the universe grew",
    "es": "T ∝ 1/a: la luz se enfrió tanto como creció el universo",
    "ar": "T ∝ 1/a: برد الضوء بمقدار ما نما الكون",
    "fr": "T ∝ 1/a : la lumière refroidit d'autant que l'Univers grandit"
  },
  "плазма: свет в тумане": {
    "en": "plasma: light in fog",
    "es": "plasma: luz en la niebla",
    "ar": "بلازما: ضوء في ضباب",
    "fr": "plasma : lumière dans le brouillard"
  },
  "атомы: свет уходит": {
    "en": "atoms: light escapes",
    "es": "átomos: la luz escapa",
    "ar": "ذرّات: الضوء ينطلق",
    "fr": "atomes : lumière s'échappe"
  },
  "до нас": {
    "en": "to us",
    "es": "hasta nosotros",
    "ar": "إلينا",
    "fr": "vers nous"
  },
  "3000 K — граница прозрачности": {
    "en": "3000 K — the transparency threshold",
    "es": "3000 K: el umbral de transparencia",
    "ar": "3000 K — حدّ الشفافية",
    "fr": "3000 K — le seuil de transparence"
  },
  "длина волны →": {
    "en": "wavelength →",
    "es": "longitud de onda →",
    "ar": "طول الموجة →",
    "fr": "longueur d'onde →"
  },
  "λ пика обратно пропорциональна T": {
    "en": "the peak λ is inversely proportional to T",
    "es": "la λ del pico es inversamente proporcional a T",
    "ar": "λ القمة تتناسب عكسياً مع T",
    "fr": "λ du pic est inversement proportionnelle à T"
  },
  "одинаковая температура без общей истории": {
    "en": "the same temperature with no shared history",
    "es": "la misma temperatura sin historia común",
    "ar": "الحرارة نفسها بلا تاريخ مشترك",
    "fr": "même température sans histoire commune"
  },
  "её горизонт": {
    "en": "its horizon",
    "es": "su horizonte",
    "ar": "أفقها",
    "fr": "son horizon"
  },
  "круги не пересекаются: сигнал не успевал пройти": {
    "en": "the circles do not overlap: no signal could pass",
    "es": "los círculos no se cruzan: ninguna señal pudo pasar",
    "ar": "الدائرتان لا تتقاطعان: لم تمرّ أي إشارة",
    "fr": "les cercles ne se chevauchent pas : le signal n'a pas pu passer"
  },
  "тянет только то, что внутри орбиты": {
    "en": "only what is inside the orbit pulls",
    "es": "solo tira lo que está dentro de la órbita",
    "ar": "لا يجذب إلا ما هو داخل المدار",
    "fr": "seulement ce qui est à l'intérieur de l'orbite attire"
  },
  "внешние слои не притягивают: их вклад взаимно гасится": {
    "en": "outer shells do not pull: their contributions cancel",
    "es": "las capas externas no tiran: sus aportes se cancelan",
    "ar": "الطبقات الخارجية لا تجذب: مساهماتها تتلاشى",
    "fr": "les couches externes n'attirent pas : leurs contributions s'annulent"
  },
  "как должно быть, если вся масса видна": {
    "en": "how it should look if all mass is visible",
    "es": "cómo debería ser si toda la masa es visible",
    "ar": "كيف ينبغي أن يكون لو كانت كل الكتلة مرئية",
    "fr": "comme cela devrait être si toute la masse est visible"
  },
  "радиус →": {
    "en": "radius →",
    "es": "radio →",
    "ar": "نصف القطر →",
    "fr": "rayon →"
  },
  "скорость": {
    "en": "speed",
    "es": "velocidad",
    "ar": "السرعة",
    "fr": "vitesse"
  },
  "v ∝ 1/√r — как у планет вокруг Солнца": {
    "en": "v ∝ 1/√r — like planets around the Sun",
    "es": "v ∝ 1/√r: como los planetas alrededor del Sol",
    "ar": "v ∝ 1/√r — مثل الكواكب حول الشمس",
    "fr": "v ∝ 1/√r — comme les planètes autour du Soleil"
  },
  "что измеряют на самом деле": {
    "en": "what is actually measured",
    "es": "lo que se mide en realidad",
    "ar": "ما يُقاس فعلاً",
    "fr": "ce qui est effectivement mesuré"
  },
  "измерено": {
    "en": "measured",
    "es": "medido",
    "ar": "مقيس",
    "fr": "mesuré"
  },
  "видимая масса": {
    "en": "visible mass",
    "es": "masa visible",
    "ar": "الكتلة المرئية",
    "fr": "masse visible"
  },
  "разница и есть тёмное гало": {
    "en": "the gap is the dark halo",
    "es": "la diferencia es el halo oscuro",
    "ar": "الفرق هو الهالة المعتمة",
    "fr": "la différence est le halo sombre"
  },
  "что происходит с плотностями при росте": {
    "en": "what happens to the densities as it grows",
    "es": "qué pasa con las densidades al crecer",
    "ar": "ماذا يحدث للكثافات مع النمو",
    "fr": "ce qui arrive aux densités lorsqu'il grandit"
  },
  "материя ∝ 1/a³": {
    "en": "matter ∝ 1/a³",
    "es": "materia ∝ 1/a³",
    "ar": "المادة ∝ 1/a³",
    "fr": "matière ∝ 1/a³"
  },
  "тёмная энергия — постоянна": {
    "en": "dark energy stays constant",
    "es": "la energía oscura permanece constante",
    "ar": "الطاقة المعتمة تبقى ثابتة",
    "fr": "l'énergie sombre reste constante"
  },
  "размер a →": {
    "en": "size a →",
    "es": "tamaño a →",
    "ar": "الحجم a →",
    "fr": "taille a →"
  },
  "пересечение кривых — момент смены знака ускорения": {
    "en": "where the curves cross, the sign of acceleration flips",
    "es": "donde se cruzan las curvas cambia el signo de la aceleración",
    "ar": "عند تقاطع المنحنيين تنقلب إشارة التسارع",
    "fr": "l'intersection des courbes : moment du changement de signe de l'accélération"
  },
  "раздувание одной выровнявшейся области": {
    "en": "one smoothed-out region blown up",
    "es": "una sola región ya uniforme, inflada",
    "ar": "منطقة واحدة تجانست ثم انتفخت",
    "fr": "gonflement d'une région lissée"
  },
  "до: успела выровняться": {
    "en": "before: had time to even out",
    "es": "antes: tuvo tiempo de uniformarse",
    "ar": "قبل: أتيح لها أن تتجانس",
    "fr": "avant : a eu le temps de s'homogénéiser"
  },
  "видимая часть": {
    "en": "the visible part",
    "es": "la parte visible",
    "ar": "الجزء المرئي",
    "fr": "la partie visible"
  },
  "после: та же однородность на всём небе": {
    "en": "after: the same uniformity across the whole sky",
    "es": "después: la misma uniformidad en todo el cielo",
    "ar": "بعد: التجانس نفسه في كل السماء",
    "fr": "après : la même uniformité sur tout le ciel"
  },
  "сначала тормозит, потом разгоняется": {
    "en": "first it slows, then it speeds up",
    "es": "primero frena, luego acelera",
    "ar": "يتباطأ أولاً ثم يتسارع",
    "fr": "d'abord ralentit, puis accélère"
  },
  "z ≈ 0,7": {
    "en": "z ≈ 0.7",
    "es": "z ≈ 0,7",
    "ar": "z ≈ 0.7",
    "fr": "z ≈ 0,7"
  },
  "торможение": {
    "en": "slowing down",
    "es": "frenado",
    "ar": "تباطؤ",
    "fr": "ralentissement"
  },
  "ускорение": {
    "en": "acceleration",
    "es": "aceleración",
    "ar": "تسارع",
    "fr": "accélération"
  },
  "время →": {
    "en": "time →",
    "es": "tiempo →",
    "ar": "الزمن →",
    "fr": "temps →"
  },
  "одинаковая вспышка как линейка": {
    "en": "an identical flash used as a ruler",
    "es": "un destello idéntico usado como regla",
    "ar": "وميض متطابق يُستخدم مسطرة",
    "fr": "un même flash comme règle"
  },
  "близко": {
    "en": "near",
    "es": "cerca",
    "ar": "قريب",
    "fr": "près"
  },
  "дальше": {
    "en": "farther",
    "es": "más lejos",
    "ar": "أبعد",
    "fr": "plus loin"
  },
  "ещё дальше": {
    "en": "farther still",
    "es": "aún más lejos",
    "ar": "أبعد أيضاً",
    "fr": "encore plus loin"
  },
  "светимость одна — значит видимая яркость меряет расстояние": {
    "en": "same luminosity, so apparent brightness measures distance",
    "es": "misma luminosidad: el brillo aparente mide la distancia",
    "ar": "اللمعان نفسه، فالسطوع الظاهري يقيس المسافة",
    "fr": "même luminosité, donc la luminosité apparente donne la distance"
  },
  "слои идут с разной скоростью": {
    "en": "layers move at different speeds",
    "es": "las capas van a distinta velocidad",
    "ar": "طبقات تتحرك بسرعات مختلفة",
    "fr": "les couches vont à des vitesses différentes"
  },
  "перескок": {
    "en": "hop across",
    "es": "salto",
    "ar": "قفزة",
    "fr": "saut"
  },
  "стенка: скорость нуль": {
    "en": "wall: zero velocity",
    "es": "pared: velocidad cero",
    "ar": "الجدار: سرعة صفر",
    "fr": "paroi : vitesse nulle"
  },
  "перенос импульса": {
    "en": "momentum transport",
    "es": "transporte de momento",
    "ar": "نقل الزخم",
    "fr": "transport de quantité de mouvement"
  },
  "поперёк потока": {
    "en": "across the flow",
    "es": "a través del flujo",
    "ar": "عبر التدفق",
    "fr": "en travers de l'écoulement"
  },
  "опыт, которым меряют вязкость": {
    "en": "the experiment that measures viscosity",
    "es": "el experimento que mide la viscosidad",
    "ar": "التجربة التي تقيس اللزوجة",
    "fr": "l'expérience qui mesure la viscosité"
  },
  "верхняя пластина: скорость u": {
    "en": "upper plate: speed u",
    "es": "placa superior: velocidad u",
    "ar": "اللوح العلوي: السرعة u",
    "fr": "plaque supérieure : vitesse u"
  },
  "нижняя пластина: скорость нуль": {
    "en": "lower plate: zero speed",
    "es": "placa inferior: velocidad cero",
    "ar": "اللوح السفلي: سرعة صفر",
    "fr": "plaque inférieure : vitesse nulle"
  },
  "зазор h": {
    "en": "gap h",
    "es": "separación h",
    "ar": "الفجوة h",
    "fr": "entrefer h"
  },
  "скорость растёт равномерно поперёк зазора": {
    "en": "speed grows uniformly across the gap",
    "es": "la velocidad crece uniformemente a través de la separación",
    "ar": "تنمو السرعة بانتظام عبر الفجوة",
    "fr": "la vitesse croît uniformément dans l'entrefer"
  },
  "что держит цилиндр внутри потока": {
    "en": "what holds the cylinder inside the flow",
    "es": "qué sostiene el cilindro dentro del flujo",
    "ar": "ما الذي يمسك الأسطوانة داخل التدفق",
    "fr": "ce qui retient le cylindre dans l'écoulement"
  },
  "вязкое трение": {
    "en": "viscous friction",
    "es": "fricción viscosa",
    "ar": "الاحتكاك اللزج",
    "fr": "frottement visqueux"
  },
  "перепад давления гонит, трение держит": {
    "en": "pressure difference drives, friction holds back",
    "es": "la diferencia de presión empuja, la fricción frena",
    "ar": "فرق الضغط يدفع والاحتكاك يكبح",
    "fr": "la différence de pression pousse, le frottement retient"
  },
  "параболический профиль скорости": {
    "en": "parabolic velocity profile",
    "es": "perfil parabólico de velocidad",
    "ar": "توزيع السرعة القطعي المكافئ",
    "fr": "profil parabolique des vitesses"
  },
  "у стенки нуль": {
    "en": "zero at the wall",
    "es": "cero en la pared",
    "ar": "صفر عند الجدار",
    "fr": "nul à la paroi"
  },
  "на оси быстрее всего": {
    "en": "fastest on the axis",
    "es": "lo más rápido en el eje",
    "ar": "الأسرع عند المحور",
    "fr": "le plus rapide sur l'axe"
  },
  "средняя скорость вдвое меньше максимальной": {
    "en": "the mean speed is half the maximum",
    "es": "la velocidad media es la mitad de la máxima",
    "ar": "متوسط السرعة نصف القيمة القصوى",
    "fr": "la vitesse moyenne vaut la moitié du maximum"
  },
  "расход собирается по кольцам": {
    "en": "the flow rate is summed over rings",
    "es": "el caudal se suma por anillos",
    "ar": "يُجمع التدفق على شكل حلقات",
    "fr": "le débit se somme anneau par anneau"
  },
  "сечение трубы": {
    "en": "pipe cross-section",
    "es": "sección del tubo",
    "ar": "مقطع الأنبوب",
    "fr": "section du tube"
  },
  "дальние кольца шире, но течение в них медленнее": {
    "en": "outer rings are wider, but the flow in them is slower",
    "es": "los anillos exteriores son más anchos, pero el flujo en ellos es más lento",
    "ar": "الحلقات الخارجية أوسع لكن الجريان فيها أبطأ",
    "fr": "les anneaux extérieurs sont plus larges, mais l'écoulement y est plus lent"
  },
  "радиус в четвёртой степени": {
    "en": "radius to the fourth power",
    "es": "el radio a la cuarta potencia",
    "ar": "نصف القطر أُس أربعة",
    "fr": "le rayon à la puissance quatre"
  },
  "радиус меньше на четверть — расход втрое": {
    "en": "radius down a quarter — flow rate down threefold",
    "es": "el radio baja un cuarto: el caudal cae tres veces",
    "ar": "نقص نصف القطر الربع يخفض التدفق ثلاث مرات",
    "fr": "rayon réduit d'un quart : débit divisé par trois"
  },
  "расход": {
    "en": "flow rate",
    "es": "caudal",
    "ar": "التدفق",
    "fr": "débit"
  },
  "инерция против вязкости": {
    "en": "inertia against viscosity",
    "es": "inercia frente a viscosidad",
    "ar": "القصور الذاتي في مواجهة اللزوجة",
    "fr": "inertie contre viscosité"
  },
  "ламинарное": {
    "en": "laminar",
    "es": "laminar",
    "ar": "صفائحي",
    "fr": "laminaire"
  },
  "турбулентное": {
    "en": "turbulent",
    "es": "turbulento",
    "ar": "مضطرب",
    "fr": "turbulent"
  },
  "вязкость сильнее": {
    "en": "viscosity wins",
    "es": "gana la viscosidad",
    "ar": "اللزوجة أقوى",
    "fr": "la viscosité l'emporte"
  },
  "инерция сильнее": {
    "en": "inertia wins",
    "es": "gana la inercia",
    "ar": "القصور الذاتي أقوى",
    "fr": "l'inertie l'emporte"
  },
  "три силы и предельная скорость": {
    "en": "three forces and the terminal speed",
    "es": "tres fuerzas y la velocidad límite",
    "ar": "ثلاث قوى والسرعة الحدية",
    "fr": "trois forces et la vitesse limite"
  },
  "вес шарика": {
    "en": "weight of the ball",
    "es": "peso de la bola",
    "ar": "وزن الكرة",
    "fr": "poids de la bille"
  },
  "выталкивающая сила": {
    "en": "buoyant force",
    "es": "empuje",
    "ar": "قوة الطفو",
    "fr": "poussée d'Archimède"
  },
  "сопротивление по Стоксу": {
    "en": "Stokes drag",
    "es": "resistencia de Stokes",
    "ar": "مقاومة ستوكس",
    "fr": "traînée de Stokes"
  },
  "равновесие трёх сил задаёт предельную скорость": {
    "en": "the balance of three forces sets the terminal speed",
    "es": "el equilibrio de tres fuerzas fija la velocidad límite",
    "ar": "توازن القوى الثلاث يحدد السرعة الحدية",
    "fr": "l'équilibre des trois forces fixe la vitesse limite"
  },
  "за одно и то же время": {
    "en": "in one and the same time",
    "es": "en el mismo tiempo",
    "ar": "في الزمن نفسه",
    "fr": "pendant le même temps"
  },
  "сколько втекло, столько и вытекло: A₁v₁ = A₂v₂": {
    "en": "what flows in flows out: A₁v₁ = A₂v₂",
    "es": "lo que entra, sale: A₁v₁ = A₂v₂",
    "ar": "ما يدخل يخرج: A₁v₁ = A₂v₂",
    "fr": "ce qui entre ressort : A₁v₁ = A₂v₂"
  },
  "что изменилось за &#916;t": {
    "en": "what changed in &#916;t",
    "es": "qué cambió en &#916;t",
    "ar": "ما الذي تغيّر خلال Δt",
    "fr": "ce qui a changé en &#916;t"
  },
  "середина не изменилась": {
    "en": "the middle is unchanged",
    "es": "el centro no cambió",
    "ar": "الوسط لم يتغيّر",
    "fr": "le milieu n’a pas changé"
  },
  "как будто перенесли &#916;V": {
    "en": "as if &#916;V had been moved",
    "es": "como si se trasladara &#916;V",
    "ar": "كأنّ ΔV قد نُقل",
    "fr": "comme si &#916;V avait été déplacé"
  },
  "вся бухгалтерия сводится к двум концам": {
    "en": "the whole accounting reduces to the two ends",
    "es": "toda la cuenta se reduce a los dos extremos",
    "ar": "كل الحساب يختصر إلى الطرفين",
    "fr": "tout le bilan se réduit aux deux extrémités"
  },
  "работа сил давления на концах": {
    "en": "work of the pressure forces at the ends",
    "es": "trabajo de las fuerzas de presión en los extremos",
    "ar": "شغل قوى الضغط عند الطرفين",
    "fr": "travail des forces de pression aux extrémités"
  },
  "работа = p·A·&#916;x = p·&#916;V": {
    "en": "work = p·A·&#916;x = p·&#916;V",
    "es": "trabajo = p·A·&#916;x = p·&#916;V",
    "ar": "الشغل = p·A·Δx = p·ΔV",
    "fr": "travail = p·A·&#916;x = p·&#916;V"
  },
  "подъём порции на разность высот": {
    "en": "lifting the parcel through a height difference",
    "es": "elevación de la porción por la diferencia de altura",
    "ar": "رفع الجزء بمقدار فرق الارتفاع",
    "fr": "élévation de la portion sur la différence de hauteur"
  },
  "уровень отсчёта": {
    "en": "reference level",
    "es": "nivel de referencia",
    "ar": "مستوى الإسناد",
    "fr": "niveau de référence"
  },
  "работа тяжести: &#8722;&#961;·&#916;V·g·(h₂ &#8722; h₁)": {
    "en": "work of gravity: &#8722;&#961;·&#916;V·g·(h₂ &#8722; h₁)",
    "es": "trabajo del peso: &#8722;&#961;·&#916;V·g·(h₂ &#8722; h₁)",
    "ar": "شغل الثقل: −ρ·ΔV·g·(h₂ − h₁)",
    "fr": "travail du poids : &#8722;&#961;·&#916;V·g·(h₂ &#8722; h₁)"
  },
  "энергия движения растёт как квадрат скорости": {
    "en": "energy of motion grows as the square of speed",
    "es": "la energía del movimiento crece como el cuadrado de la velocidad",
    "ar": "طاقة الحركة تنمو مع مربّع السرعة",
    "fr": "l’énergie du mouvement croît comme le carré de la vitesse"
  },
  "скорость вдвое — энергия вчетверо": {
    "en": "twice the speed, four times the energy",
    "es": "el doble de velocidad, el cuádruple de energía",
    "ar": "ضعف السرعة، أربعة أضعاف الطاقة",
    "fr": "vitesse doublée, énergie quadruplée"
  },
  "полная работа = прирост кинетической энергии": {
    "en": "total work = gain in kinetic energy",
    "es": "trabajo total = aumento de la energía cinética",
    "ar": "الشغل الكلي = الزيادة في الطاقة الحركية",
    "fr": "travail total = gain d’énergie cinétique"
  },
  "давление": {
    "en": "pressure",
    "es": "presión",
    "ar": "الضغط",
    "fr": "pression"
  },
  "тяжесть": {
    "en": "gravity",
    "es": "peso",
    "ar": "الثقل",
    "fr": "poids"
  },
  "движение": {
    "en": "motion",
    "es": "movimiento",
    "ar": "الحركة",
    "fr": "mouvement"
  },
  "&#916;V входит в каждое слагаемое и сокращается": {
    "en": "&#916;V appears in every term and cancels",
    "es": "&#916;V aparece en cada término y se cancela",
    "ar": "ΔV يظهر في كل حدّ ويُختصر",
    "fr": "&#916;V figure dans chaque terme et se simplifie"
  },
  "вдоль линии тока сумма не меняется": {
    "en": "along a streamline the sum does not change",
    "es": "a lo largo de una línea de corriente la suma no cambia",
    "ar": "على طول خط الانسياب لا يتغيّر المجموع",
    "fr": "le long d’une ligne de courant la somme ne change pas"
  },
  "сумма одна и та же": {
    "en": "the same total",
    "es": "la misma suma",
    "ar": "المجموع نفسه",
    "fr": "la même somme"
  },
  "широко": {
    "en": "wide",
    "es": "ancha",
    "ar": "واسع",
    "fr": "large"
  },
  "узко": {
    "en": "narrow",
    "es": "estrecha",
    "ar": "ضيّق",
    "fr": "étroit"
  },
  "выше": {
    "en": "higher",
    "es": "más alto",
    "ar": "أعلى",
    "fr": "plus haut"
  },
  "трубка Вентури": {
    "en": "Venturi tube",
    "es": "tubo de Venturi",
    "ar": "أنبوب فنتوري",
    "fr": "tube de Venturi"
  },
  "трубка Пито": {
    "en": "Pitot tube",
    "es": "tubo de Pitot",
    "ar": "أنبوب بيتو",
    "fr": "tube de Pitot"
  },
  "перепад давления меряет и расход, и скорость": {
    "en": "a pressure difference measures both flow rate and speed",
    "es": "una diferencia de presión mide tanto el caudal como la velocidad",
    "ar": "فرق الضغط يقيس التدفّق والسرعة معاً",
    "fr": "une différence de pression mesure le débit et la vitesse"
  },
  "жидкость в покое давит только по нормали": {
    "en": "a fluid at rest pushes only along the normal",
    "es": "un fluido en reposo empuja solo según la normal",
    "ar": "المائع الساكن يدفع عمودياً على السطح فقط",
    "fr": "un fluide au repos ne pousse que selon la normale"
  },
  "площадка A": {
    "en": "area A",
    "es": "área A",
    "ar": "المساحة A",
    "fr": "surface A"
  },
  "сдвига нет": {
    "en": "no shear",
    "es": "sin cizalla",
    "ar": "لا قصّ",
    "fr": "pas de cisaillement"
  },
  "клин в жидкости: три грани, три силы давления": {
    "en": "a wedge in the fluid: three faces, three pressure forces",
    "es": "una cuña en el fluido: tres caras, tres fuerzas de presión",
    "ar": "إسفين داخل المائع: ثلاثة أوجه وثلاث قوى ضغط",
    "fr": "un coin dans le fluide : trois faces, trois forces"
  },
  "сбоку": {
    "en": "from the side",
    "es": "por el lado",
    "ar": "من الجانب",
    "fr": "par le côté"
  },
  "снизу": {
    "en": "from below",
    "es": "por abajo",
    "ar": "من الأسفل",
    "fr": "par le bas"
  },
  "сверху": {
    "en": "from above",
    "es": "por arriba",
    "ar": "من الأعلى",
    "fr": "par le haut"
  },
  "на наклонную грань": {
    "en": "on the inclined face",
    "es": "sobre la cara inclinada",
    "ar": "على الوجه المائل",
    "fr": "sur la face inclinée"
  },
  "вес": {
    "en": "weight",
    "es": "peso",
    "ar": "الوزن",
    "fr": "poids"
  },
  "силы давления ∝ L²": {
    "en": "pressure forces ∝ L²",
    "es": "fuerzas de presión ∝ L²",
    "ar": "قوى الضغط ∝ L²",
    "fr": "forces de pression ∝ L²"
  },
  "вес ∝ L³": {
    "en": "weight ∝ L³",
    "es": "peso ∝ L³",
    "ar": "الوزن ∝ L³",
    "fr": "poids ∝ L³"
  },
  "уменьшаем клин — вес исчезает быстрее сил давления": {
    "en": "shrink the wedge: weight vanishes faster than pressure",
    "es": "al encoger la cuña el peso se va antes que la presión",
    "ar": "بتصغير الإسفين يتلاشى الوزن أسرع من قوى الضغط",
    "fr": "on réduit le coin : le poids s'efface avant la pression"
  },
  "добавленное давление доходит до каждой точки": {
    "en": "added pressure reaches every point",
    "es": "la presión añadida llega a todos los puntos",
    "ar": "الضغط المضاف يصل إلى كل نقطة",
    "fr": "la pression ajoutée atteint chaque point"
  },
  "выигрыш в силе равен отношению площадей, в работе — нет": {
    "en": "force gain equals the area ratio; no gain in work",
    "es": "la fuerza gana la razón de áreas; el trabajo no gana",
    "ar": "الكسب في القوة نسبة المساحتين ولا كسب في الشغل",
    "fr": "gain en force = rapport des aires ; aucun gain en travail"
  },
  "вертикальный столбик жидкости в равновесии": {
    "en": "a vertical column of fluid in equilibrium",
    "es": "una columna vertical de fluido en equilibrio",
    "ar": "عمود رأسي من المائع في اتزان",
    "fr": "une colonne verticale de fluide à l'équilibre"
  },
  "разность давлений сверху и снизу равна весу столбика": {
    "en": "the pressure difference holds up the column's weight",
    "es": "la diferencia de presiones sostiene el peso de la columna",
    "ar": "فرق الضغط يحمل وزن العمود",
    "fr": "l'écart de pression porte le poids de la colonne"
  },
  "разная форма, одна глубина — одна сила на дно": {
    "en": "different shapes, same depth: same force on the bottom",
    "es": "formas distintas, misma profundidad, misma fuerza",
    "ar": "أشكال مختلفة وعمق واحد: القوة على القاع نفسها",
    "fr": "formes différentes, même profondeur, même force"
  },
  "сила на дно одна и та же": {
    "en": "the force on the bottom is the same",
    "es": "la fuerza sobre el fondo es la misma",
    "ar": "القوة على القاع واحدة",
    "fr": "la force sur le fond est la même"
  },
  "лишний вес несут наклонные стенки": {
    "en": "the extra weight is carried by the slanted walls",
    "es": "el peso sobrante lo llevan las paredes inclinadas",
    "ar": "الوزن الزائد تحمله الجدران المائلة",
    "fr": "le poids en trop est repris par les parois"
  },
  "сообщающиеся сосуды: две несмешивающиеся жидкости": {
    "en": "communicating vessels: two immiscible liquids",
    "es": "vasos comunicantes: dos líquidos inmiscibles",
    "ar": "أوانٍ مستطرقة: سائلان لا يمتزجان",
    "fr": "vases communicants : deux liquides non miscibles"
  },
  "общий уровень": {
    "en": "common level",
    "es": "nivel común",
    "ar": "المستوى المشترك",
    "fr": "niveau commun"
  },
  "высоты столбов обратны плотностям": {
    "en": "column heights are inverse to the densities",
    "es": "las alturas son inversas a las densidades",
    "ar": "الارتفاعان يتناسبان عكسياً مع الكثافتين",
    "fr": "les hauteurs sont inverses des masses volumiques"
  },
  "силы давления на грани погружённого бруска": {
    "en": "pressure forces on the faces of a submerged block",
    "es": "fuerzas de presión sobre un bloque sumergido",
    "ar": "قوى الضغط على أوجه كتلة مغمورة",
    "fr": "forces de pression sur un bloc immergé"
  },
  "боковые гасятся": {
    "en": "side forces cancel",
    "es": "las laterales se anulan",
    "ar": "الجانبية تتلاشى",
    "fr": "les latérales s'annulent"
  },
  "разность этих сил и есть ρgV": {
    "en": "the difference of these forces is exactly ρgV",
    "es": "la diferencia de estas fuerzas es ρgV",
    "ar": "الفرق بين هاتين القوتين هو ρgV",
    "fr": "la différence de ces forces vaut ρgV"
  },
  "чем плотнее тело, тем глубже оно сидит": {
    "en": "the denser the body, the deeper it sits",
    "es": "cuanto más denso el cuerpo, más se hunde",
    "ar": "كلما زادت كثافة الجسم غاص أعمق",
    "fr": "plus le corps est dense, plus il s'enfonce"
  },
  "доля под водой = ρтела / ρжидкости": {
    "en": "submerged fraction = ρ(body) / ρ(fluid)",
    "es": "fracción sumergida = ρ(cuerpo) / ρ(fluido)",
    "ar": "الجزء المغمور = ρ(الجسم) / ρ(المائع)",
    "fr": "fraction immergée = ρ(corps) / ρ(fluide)"
  }
};
