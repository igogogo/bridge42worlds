/* figures-i18n.js — подписи схем на четырёх языках.

   Схемы рисуются в js/figures.js, подписи на них были только по-русски: на английской,
   испанской и арабской версиях читатель видел кириллицу прямо на картинке. Ключ словаря —
   русская подпись как она написана в коде, поэтому промахнуться по смыслу нельзя.

   Подставляется в одной функции txt() — см. figures.js. Файл подключать ПЕРЕД figures.js.
   Собран tools/figures_i18n.py; после правки подписей в схемах прогнать его заново. */
window.B42FigText = {
  "сдвиг: та же установка на новом месте": {
    "en": "shift: the same setup in a new place",
    "es": "desplazamiento: el mismo montaje en otro lugar",
    "ar": "إزاحة: التجربة نفسها في مكان جديد",
    "fr": "translation : le même dispositif ailleurs"
  },
  "скорость та же": {
    "en": "velocity unchanged",
    "es": "la velocidad no cambia",
    "ar": "السرعة نفسها",
    "fr": "la vitesse ne change pas"
  },
  "ε любое — значит, множитель при ε равен нулю": {
    "en": "ε is arbitrary — so the coefficient of ε vanishes",
    "es": "ε es arbitrario: el coeficiente de ε es cero",
    "ar": "ε اختياري — إذن معامل ε يساوي صفراً",
    "fr": "ε est quelconque : le coefficient de ε est nul"
  },
  "сдвигаем оба тела сразу": {
    "en": "shift both bodies at once",
    "es": "desplazamos ambos cuerpos a la vez",
    "ar": "نُزيح الجسمين معاً",
    "fr": "on translate les deux corps ensemble"
  },
  "сдвиг на ε": {
    "en": "shift by ε",
    "es": "desplazamiento ε",
    "ar": "إزاحة بمقدار ε",
    "fr": "translation de ε"
  },
  "расстояние то же — лагранжиан не изменился": {
    "en": "same separation — the Lagrangian is unchanged",
    "es": "misma distancia: el lagrangiano no cambia",
    "ar": "المسافة نفسها — اللاغرانجي لم يتغيّر",
    "fr": "même distance : le lagrangien ne change pas"
  },
  "сохраняется сумма импульсов, а не каждый по отдельности": {
    "en": "the sum of the momenta is conserved, not each one separately",
    "es": "se conserva la suma de los momentos, no cada uno por separado",
    "ar": "يُحفَظ مجموع كميات الحركة لا كلٌّ على حدة",
    "fr": "c'est la somme des quantités de mouvement qui se conserve"
  },
  "поворот на ε: радиус не меняется": {
    "en": "rotation by ε: the radius stays the same",
    "es": "rotación ε: el radio no cambia",
    "ar": "دوران بمقدار ε: نصف القطر ثابت",
    "fr": "rotation de ε : le rayon ne change pas"
  },
  "U зависит только от r": {
    "en": "U depends on r only",
    "es": "U depende solo de r",
    "ar": "U يعتمد على r وحده",
    "fr": "U ne dépend que de r"
  },
  "угол в L не входит": {
    "en": "the angle does not enter L",
    "es": "el ángulo no aparece en L",
    "ar": "الزاوية لا تظهر في L",
    "fr": "l'angle n'apparaît pas dans L"
  },
  "момент импульса — обобщённый импульс для угла": {
    "en": "angular momentum is the generalized momentum of the angle",
    "es": "el momento angular es el momento generalizado del ángulo",
    "ar": "الزخم الزاوي هو الزخم المعمَّم المرافق للزاوية",
    "fr": "le moment cinétique est le moment généralisé de l'angle"
  },
  "опыт, начатый позже, идёт точно так же": {
    "en": "an experiment started later runs exactly the same",
    "es": "un experimento iniciado más tarde transcurre igual",
    "ar": "تجربة تبدأ لاحقاً تسير بالطريقة نفسها",
    "fr": "une expérience lancée plus tard se déroule de même"
  },
  "старт": {
    "en": "start",
    "es": "inicio",
    "ar": "البداية",
    "fr": "départ"
  },
  "сдвиг во времени даёт сохранение энергии": {
    "en": "shifting in time yields conservation of energy",
    "es": "el desplazamiento en el tiempo da la conservación de la energía",
    "ar": "الإزاحة في الزمن تعطي حفظ الطاقة",
    "fr": "la translation dans le temps donne la conservation de l'énergie"
  },
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
    "ar": "Q&#1093; ليس صفرًا أبدًا",
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
  },
  "кривую обращают точка за точкой": {
    "en": "the curve is inverted point by point",
    "es": "la curva se invierte punto por punto",
    "ar": "يُعكس المنحنى نقطة بنقطة",
    "fr": "la courbe est inversée point par point"
  },
  "v(r): измерено": {
    "en": "v(r): measured",
    "es": "v(r): medido",
    "ar": "v(r): مقيس",
    "fr": "v(r) : mesuré"
  },
  "масса растёт линейно, плотность падает как обратный квадрат": {
    "en": "mass grows linearly, density falls as the inverse square",
    "es": "la masa crece linealmente, la densidad cae como el inverso del cuadrado",
    "ar": "الكتلة تنمو خطياً والكثافة تتناقص كمقلوب المربع",
    "fr": "la masse croît linéairement, la densité décroît comme l'inverse du carré"
  },
  "масса отклоняет луч — и картинка смещается": {
    "en": "mass bends the ray, and the image shifts",
    "es": "la masa desvía el rayo y la imagen se desplaza",
    "ar": "الكتلة تحرف الشعاع فتنزاح الصورة",
    "fr": "la masse dévie le rayon et l'image se déplace"
  },
  "видимые положения": {
    "en": "apparent positions",
    "es": "posiciones aparentes",
    "ar": "المواضع الظاهرية",
    "fr": "positions apparentes"
  },
  "источник": {
    "en": "source",
    "es": "fuente",
    "ar": "المصدر",
    "fr": "source"
  },
  "угол отклонения вдвое больше ньютоновского": {
    "en": "the deflection angle is twice the Newtonian one",
    "es": "el ángulo de desviación es el doble del newtoniano",
    "ar": "زاوية الانحراف ضعف القيمة النيوتونية",
    "fr": "l'angle de déviation vaut le double de la valeur newtonienne"
  },
  "дрейф мал, тепловая скорость велика": {
    "en": "the drift is tiny, the thermal speed is huge",
    "es": "la deriva es mínima, la velocidad térmica enorme",
    "ar": "الانجراف ضئيل والسرعة الحرارية هائلة",
    "fr": "la dérive est minime, la vitesse thermique énorme"
  },
  "пластина едет": {
    "en": "plate moving",
    "es": "placa en movimiento",
    "ar": "اللوح يتحرك",
    "fr": "plaque en mouvement"
  },
  "пластина стоит": {
    "en": "plate at rest",
    "es": "placa en reposo",
    "ar": "اللوح ساكن",
    "fr": "plaque immobile"
  },
  "&#10216;v&#10217; &#8776; 460 м/с": {
    "en": "⟨v⟩ ≈ 460 m/s",
    "es": "⟨v⟩ ≈ 460 m/s",
    "ar": "⟨v⟩ ≈ 460 م/ث",
    "fr": "⟨v⟩ ≈ 460 m/s"
  },
  "u — сантиметры в секунду": {
    "en": "u — centimetres per second",
    "es": "u: centímetros por segundo",
    "ar": "u — سنتيمترات في الثانية",
    "fr": "u — centimètres par seconde"
  },
  "шесть направлений — по одной шестой на каждое": {
    "en": "six directions — one sixth each",
    "es": "seis direcciones: un sexto cada una",
    "ar": "ستة اتجاهات — سُدس لكل منها",
    "fr": "six directions — un sixième chacune"
  },
  "вдоль площадки —": {
    "en": "along the patch —",
    "es": "a lo largo del área:",
    "ar": "بمحاذاة المساحة —",
    "fr": "le long de la surface —"
  },
  "ничего не переносят": {
    "en": "carry nothing across",
    "es": "no transportan nada",
    "ar": "لا تنقل شيئًا",
    "fr": "ne transportent rien"
  },
  "в каждую сторону": {
    "en": "in each direction",
    "es": "en cada sentido",
    "ar": "في كل اتجاه",
    "fr": "dans chaque sens"
  },
  "молекула помнит слой, в котором столкнулась": {
    "en": "a molecule remembers the layer where it last collided",
    "es": "la molécula recuerda la capa donde chocó por última vez",
    "ar": "الجزيء يتذكر الطبقة التي اصطدم فيها آخر مرة",
    "fr": "la molécule se souvient de la couche où elle a heurté"
  },
  "разность приносимого = 2&#955;&#183;du/dy": {
    "en": "difference carried = 2λ·du/dy",
    "es": "diferencia transportada = 2λ·du/dy",
    "ar": "الفرق المنقول = 2λ·du/dy",
    "fr": "différence transportée = 2λ·du/dy"
  },
  "сколько носильщиков &#215; сколько приносит каждый": {
    "en": "how many carriers × how much each brings",
    "es": "cuántos portadores × cuánto trae cada uno",
    "ar": "عدد الحاملات × ما ينقله كل منها",
    "fr": "combien de porteurs × ce qu'apporte chacun"
  },
  "носильщиков через площадку": {
    "en": "carriers crossing the patch",
    "es": "portadores que cruzan el área",
    "ar": "حاملات تعبر المساحة",
    "fr": "porteurs traversant la surface"
  },
  "импульса приносит каждый": {
    "en": "momentum brought by each",
    "es": "momento que trae cada uno",
    "ar": "الزخم الذي ينقله كل منها",
    "fr": "impulsion apportée par chacun"
  },
  "трение получилось, а не было постулировано": {
    "en": "friction came out of it; it was not postulated",
    "es": "el rozamiento resultó, no se postuló",
    "ar": "الاحتكاك نتج ولم يُفترض",
    "fr": "le frottement en résulte, il n'est pas postulé"
  },
  "носильщиков вдвое меньше — каждый идёт вдвое дальше": {
    "en": "half as many carriers — each one goes twice as far",
    "es": "la mitad de portadores: cada uno va el doble de lejos",
    "ar": "الحاملات نصف العدد — وكل منها يقطع ضعف المسافة",
    "fr": "deux fois moins de porteurs — chacun va deux fois plus loin"
  },
  "плотный газ: пробег мал": {
    "en": "dense gas: short free path",
    "es": "gas denso: recorrido libre corto",
    "ar": "غاز كثيف: مسار حر قصير",
    "fr": "gaz dense : libre parcours court"
  },
  "разрежённый: пробег велик": {
    "en": "rarefied gas: long free path",
    "es": "gas enrarecido: recorrido libre largo",
    "ar": "غاز مخلخل: مسار حر طويل",
    "fr": "gaz raréfié : libre parcours long"
  },
  "&#961;&#955; = nm &#183; 1/(&#8730;2&#183;n&#963;): концентрация сокращается": {
    "en": "ρλ = nm · 1/(√2·nσ): the concentration cancels",
    "es": "ρλ = nm · 1/(√2·nσ): la concentración se cancela",
    "ar": "ρλ = nm · 1/(√2·nσ): التركيز يُختصر",
    "fr": "ρλ = nm · 1/(√2·nσ) : la concentration s'élimine"
  },
  "нагрев: газ густеет, жидкость жидеет": {
    "en": "on heating the gas thickens and the liquid thins",
    "es": "al calentar, el gas espesa y el líquido se aligera",
    "ar": "بالتسخين تزداد لزوجة الغاز وتقل لزوجة السائل",
    "fr": "en chauffant, le gaz épaissit et le liquide s'allège"
  },
  "газ: &#8776; &#8730;T": {
    "en": "gas: ≈ √T",
    "es": "gas: ≈ √T",
    "ar": "غاز: ≈ √T",
    "fr": "gaz : ≈ √T"
  },
  "жидкость: &#8776; exp(E/kT)": {
    "en": "liquid: ≈ exp(E/kT)",
    "es": "líquido: ≈ exp(E/kT)",
    "ar": "سائل: ≈ exp(E/kT)",
    "fr": "liquide : ≈ exp(E/kT)"
  },
  "механизмы разные — потому и знак разный": {
    "en": "different mechanisms — hence the opposite sign",
    "es": "mecanismos distintos: de ahí el signo opuesto",
    "ar": "الآليتان مختلفتان — ومن هنا اختلاف الإشارة",
    "fr": "mécanismes différents — d'où le signe opposé"
  },
  "один механизм — три коэффициента": {
    "en": "one mechanism — three coefficients",
    "es": "un mecanismo, tres coeficientes",
    "ar": "آلية واحدة — ثلاثة معاملات",
    "fr": "un mécanisme — trois coefficients"
  },
  "диффузия": {
    "en": "diffusion",
    "es": "difusión",
    "ar": "الانتشار",
    "fr": "diffusion"
  },
  "теплопроводность": {
    "en": "thermal conduction",
    "es": "conducción térmica",
    "ar": "التوصيل الحراري",
    "fr": "conduction thermique"
  },
  "вязкость": {
    "en": "viscosity",
    "es": "viscosidad",
    "ar": "اللزوجة",
    "fr": "viscosité"
  },
  "переносится:": {
    "en": "what is carried:",
    "es": "qué se transporta:",
    "ar": "ما يُنقل:",
    "fr": "ce qui est transporté :"
  },
  "число частиц": {
    "en": "number of particles",
    "es": "número de partículas",
    "ar": "عدد الجسيمات",
    "fr": "nombre de particules"
  },
  "поток = &#8722;(1/3)&#955;&#10216;v&#10217; &#183; градиент того, что переносится": {
    "en": "flux = −(1/3)λ⟨v⟩ · gradient of whatever is carried",
    "es": "flujo = −(1/3)λ⟨v⟩ · gradiente de lo que se transporta",
    "ar": "التدفق = −(1/3)λ⟨v⟩ · تدرّج ما يُنقل",
    "fr": "flux = −(1/3)λ⟨v⟩ · gradient de ce qui est transporté"
  },
  "число Прандтля: что расплывается быстрее — импульс или тепло": {
    "en": "Prandtl number: what spreads faster — momentum or heat",
    "es": "número de Prandtl: qué se difunde antes, el momento o el calor",
    "ar": "عدد براندتل: أيهما ينتشر أسرع — الزخم أم الحرارة",
    "fr": "nombre de Prandtl : qu'est-ce qui diffuse le plus vite — l'impulsion ou la chaleur"
  },
  "ртуть": {
    "en": "mercury",
    "es": "mercurio",
    "ar": "الزئبق",
    "fr": "mercure"
  },
  "газы": {
    "en": "gases",
    "es": "gases",
    "ar": "الغازات",
    "fr": "gaz"
  },
  "вода": {
    "en": "water",
    "es": "agua",
    "ar": "الماء",
    "fr": "eau"
  },
  "глицерин": {
    "en": "glycerol",
    "es": "glicerina",
    "ar": "الغليسرين",
    "fr": "glycérine"
  },
  "у всех газов около 0,7 — переносчик-то один": {
    "en": "about 0.7 for every gas — the carrier is one and the same",
    "es": "cerca de 0,7 en todos los gases: el portador es el mismo",
    "ar": "نحو 0.7 لجميع الغازات — الحامل واحد",
    "fr": "environ 0,7 pour tous les gaz — le porteur est le même"
  },
  "почему 3000 К, а не 158 000 К": {
    "en": "why 3000 K and not 158 000 K",
    "es": "por qué 3000 K y no 158 000 K",
    "ar": "لماذا 3000 كلفن وليس 158 000",
    "fr": "pourquoi 3000 K et non 158 000 K"
  },
  "на атом — полтора миллиарда фотонов": {
    "en": "a billion and a half photons per atom",
    "es": "mil quinientos millones de fotones por átomo",
    "ar": "مليار ونصف فوتون لكل ذرة",
    "fr": "un milliard et demi de photons par atome"
  },
  "13,6 эВ": {
    "en": "13.6 eV",
    "es": "13,6 eV",
    "ar": "13.6 eV",
    "fr": "13,6 eV"
  },
  "хвост ещё ионизует": {
    "en": "the tail still ionizes",
    "es": "la cola aún ioniza",
    "ar": "الذيل ما زال يؤيّن",
    "fr": "la queue ionise encore"
  },
  "энергия фотона →": {
    "en": "photon energy →",
    "es": "energía del fotón →",
    "ar": "طاقة الفوتون →",
    "fr": "énergie du photon →"
  },
  "хвост нарисован крупнее: на деле там один фотон из миллиарда": {
    "en": "the tail is drawn larger: in reality it holds one photon in a billion",
    "es": "la cola se dibuja mayor: en realidad, un fotón de cada mil millones",
    "ar": "الذيل مرسوم أكبر مما هو عليه: في الواقع فوتون واحد من كل مليار",
    "fr": "la queue est dessinée plus grande : en réalité un photon sur un milliard"
  },
  "одна и та же линейка под разным углом": {
    "en": "the same ruler seen at different angles",
    "es": "la misma regla vista con ángulos distintos",
    "ar": "المسطرة نفسها تُرى بزوايا مختلفة",
    "fr": "la même règle vue sous des angles différents"
  },
  "размер пятна известен: докуда дошёл звук в плазме": {
    "en": "the spot size is known: how far sound travelled in the plasma",
    "es": "el tamaño de la mancha se conoce: hasta dónde llegó el sonido en el plasma",
    "ar": "حجم البقعة معروف: إلى أين وصل الصوت في البلازما",
    "fr": "la taille de la tache est connue : jusqu'où le son a voyagé dans le plasma"
  },
  "сфера": {
    "en": "sphere",
    "es": "esfera",
    "ar": "كرة",
    "fr": "sphère"
  },
  "плоскость": {
    "en": "plane",
    "es": "plano",
    "ar": "مستوٍ",
    "fr": "plan"
  },
  "седло": {
    "en": "saddle",
    "es": "silla de montar",
    "ar": "سرج",
    "fr": "selle"
  },
  "угол больше": {
    "en": "wider angle",
    "es": "ángulo mayor",
    "ar": "زاوية أكبر",
    "fr": "angle plus grand"
  },
  "ровно 1°": {
    "en": "exactly 1°",
    "es": "exactamente 1°",
    "ar": "‏1° بالضبط",
    "fr": "exactement 1°"
  },
  "угол меньше": {
    "en": "narrower angle",
    "es": "ángulo menor",
    "ar": "زاوية أصغر",
    "fr": "angle plus petit"
  },
  "измеряют ровно градус — значит, пространство плоское": {
    "en": "one degree is what is measured — so space is flat",
    "es": "se mide justo un grado: el espacio es plano",
    "ar": "المقاس درجة واحدة بالضبط — إذن الفضاء مسطّح",
    "fr": "on mesure exactement un degré : l'espace est plat"
  },
  "пробный путь: истинный плюс горб с множителем ε": {
    "en": "trial path: the true one plus a bump scaled by ε",
    "es": "camino de prueba: el real más una joroba con factor ε",
    "ar": "المسار التجريبي: المسار الحقيقي زائد نتوء بمعامل ε",
    "fr": "chemin d'essai : le vrai plus une bosse de facteur ε"
  },
  "форма горба любая, концы прижаты": {
    "en": "the bump may have any shape, the ends stay pinned",
    "es": "la joroba puede tener cualquier forma, los extremos quedan fijos",
    "ar": "شكل النتوء اختياري، والطرفان يبقيان مثبتين",
    "fr": "la bosse peut avoir n'importe quelle forme, les extrémités restent fixées"
  },
  "что означает «первый порядок обязан обнулиться»": {
    "en": "what «the first order must vanish» means",
    "es": "qué significa «el primer orden debe anularse»",
    "ar": "ماذا يعني «يجب أن تنعدم الرتبة الأولى»",
    "fr": "ce que signifie « le premier ordre doit s'annuler »"
  },
  "c₁ ≠ 0: есть куда упасть": {
    "en": "c₁ ≠ 0: there is room to fall",
    "es": "c₁ ≠ 0: hay hacia dónde caer",
    "ar": "c₁ ≠ 0: هناك متسع للهبوط",
    "fr": "c₁ ≠ 0 : il y a de quoi descendre"
  },
  "ненулевой наклон в нуле означает: рядом есть путь дешевле": {
    "en": "a nonzero slope at zero means a cheaper path lies right next to it",
    "es": "una pendiente no nula en cero significa que al lado hay un camino más barato",
    "ar": "ميل غير صفري عند الصفر يعني وجود مسار أرخص بالجوار",
    "fr": "une pente non nulle en zéro signifie qu'un chemin moins coûteux est juste à côté"
  },
  "сдвиг пути меняет сразу две вещи": {
    "en": "shifting the path changes two things at once",
    "es": "desplazar el camino cambia dos cosas a la vez",
    "ar": "إزاحة المسار تغيّر أمرين في آن واحد",
    "fr": "déplacer le chemin change deux choses à la fois"
  },
  "наклоны разные": {
    "en": "the slopes differ",
    "es": "las pendientes difieren",
    "ar": "الميلان مختلفان",
    "fr": "les pentes diffèrent"
  },
  "сдвиг координаты": {
    "en": "shift of the coordinate",
    "es": "desplazamiento de la coordenada",
    "ar": "إزاحة الإحداثي",
    "fr": "décalage de la coordonnée"
  },
  "сдвиг наклона": {
    "en": "shift of the slope",
    "es": "cambio de la pendiente",
    "ar": "تغيّر الميل",
    "fr": "changement de la pente"
  },
  "штрих — производная по времени": {
    "en": "prime = derivative with respect to time",
    "es": "la prima = derivada respecto al tiempo",
    "ar": "الشرطة = المشتقة بالنسبة إلى الزمن",
    "fr": "le prime = dérivée par rapport au temps"
  },
  "два слагаемых вариации — это цепное правило, ничего больше": {
    "en": "the two terms of the variation are just the chain rule, nothing more",
    "es": "los dos términos de la variación son solo la regla de la cadena, nada más",
    "ar": "حدّا التغاير ليسا سوى قاعدة السلسلة، لا أكثر",
    "fr": "les deux termes de la variation ne sont que la règle de la chaîne, rien de plus"
  },
  "производная переезжает с горба на импульсный множитель": {
    "en": "the derivative moves from the bump onto the momentum factor",
    "es": "la derivada pasa de la joroba al factor de momento",
    "ar": "المشتقة تنتقل من النتوء إلى معامل كمية الحركة",
    "fr": "la dérivée passe de la bosse au facteur d'impulsion"
  },
  "по частям": {
    "en": "by parts",
    "es": "por partes",
    "ar": "بالتجزئة",
    "fr": "par parties"
  },
  "[ ∂L/∂y′ · η ] на концах": {
    "en": "[ ∂L/∂y′ · η ] at the ends",
    "es": "[ ∂L/∂y′ · η ] en los extremos",
    "ar": "[ ∂L/∂y′ · η ] عند الطرفين",
    "fr": "[ ∂L/∂y′ · η ] aux extrémités"
  },
  "граничный член гибнет: концы закреплены": {
    "en": "the boundary term dies: the ends are fixed",
    "es": "el término de frontera muere: los extremos están fijos",
    "ar": "الحد الحدّي يتلاشى: الطرفان مثبتان",
    "fr": "le terme de bord disparaît : les extrémités sont fixées"
  },
  "удары со всех сторон почти гасятся": {
    "en": "hits from every side almost cancel",
    "es": "los golpes de todos lados casi se cancelan",
    "ar": "الضربات من كل الجهات تكاد تلغي بعضها",
    "fr": "les chocs de tous côtés s'annulent presque"
  },
  "зерно": {
    "en": "grain",
    "es": "grano",
    "ar": "حُبيبة",
    "fr": "grain"
  },
  "перевес": {
    "en": "net excess",
    "es": "exceso neto",
    "ar": "الفائض",
    "fr": "excédent net"
  },
  "N ≈ 10²⁰ ударов в секунду": {
    "en": "N ≈ 10²⁰ hits per second",
    "es": "N ≈ 10²⁰ golpes por segundo",
    "ar": "N ≈ 10²⁰ ضربة في الثانية",
    "fr": "N ≈ 10²⁰ chocs par seconde"
  },
  "перевес ~ √N, то есть доля 1/√N от всех ударов": {
    "en": "excess ~ √N, i.e. a fraction 1/√N of all hits",
    "es": "exceso ~ √N, o sea una fracción 1/√N de los golpes",
    "ar": "الفائض ~ √N، أي نسبة 1/√N من كل الضربات",
    "fr": "excédent ~ √N, soit une fraction 1/√N des chocs"
  },
  "путь длинный, смещение короткое": {
    "en": "the path is long, the displacement is short",
    "es": "el camino es largo, el desplazamiento corto",
    "ar": "المسار طويل والإزاحة قصيرة",
    "fr": "le chemin est long, le déplacement court"
  },
  "через N шагов": {
    "en": "after N steps",
    "es": "tras N pasos",
    "ar": "بعد N خطوة",
    "fr": "après N pas"
  },
  "смещение x": {
    "en": "displacement x",
    "es": "desplazamiento x",
    "ar": "الإزاحة x",
    "fr": "déplacement x"
  },
  "длина пути N·ℓ растёт как N": {
    "en": "path length N·ℓ grows as N",
    "es": "la longitud del camino N·ℓ crece como N",
    "ar": "طول المسار N·ℓ ينمو مثل N",
    "fr": "la longueur du chemin N·ℓ croît comme N"
  },
  "смещение растёт как √N": {
    "en": "displacement grows as √N",
    "es": "el desplazamiento crece como √N",
    "ar": "الإزاحة تنمو مثل √N",
    "fr": "le déplacement croît comme √N"
  },
  "квадрат суммы: что переживает усреднение": {
    "en": "square of a sum: what survives averaging",
    "es": "cuadrado de una suma: qué sobrevive al promediar",
    "ar": "مربع المجموع: ما الذي يبقى بعد المتوسّط",
    "fr": "carré d'une somme : ce qui survit à la moyenne"
  },
  "ℓᵢ² — всегда положительны": {
    "en": "ℓᵢ² — always positive",
    "es": "ℓᵢ² — siempre positivos",
    "ar": "ℓᵢ² — موجبة دائمًا",
    "fr": "ℓᵢ² — toujours positifs"
  },
  "ℓᵢℓⱼ — в среднем нуль": {
    "en": "ℓᵢℓⱼ — zero on average",
    "es": "ℓᵢℓⱼ — cero en promedio",
    "ar": "ℓᵢℓⱼ — صفر في المتوسّط",
    "fr": "ℓᵢℓⱼ — nuls en moyenne"
  },
  "их больше, но они гасятся": {
    "en": "there are more of them, but they cancel",
    "es": "son más numerosos, pero se cancelan",
    "ar": "عددها أكبر لكنها تلغي بعضها",
    "fr": "ils sont plus nombreux, mais ils s'annulent"
  },
  "остаётся только диагональ: N членов": {
    "en": "only the diagonal remains: N terms",
    "es": "sólo queda la diagonal: N términos",
    "ar": "يبقى القطر فقط: N حدًّا",
    "fr": "seule la diagonale reste : N termes"
  },
  "вчетверо дольше — вдвое дальше": {
    "en": "four times longer — twice as far",
    "es": "cuatro veces más tiempo, el doble de lejos",
    "ar": "أربعة أضعاف الزمن — ضعف المسافة",
    "fr": "quatre fois plus longtemps — deux fois plus loin"
  },
  "кривая круче всего в начале": {
    "en": "the curve is steepest at the start",
    "es": "la curva es más empinada al principio",
    "ar": "المنحنى أشدّ انحدارًا في البداية",
    "fr": "la courbe est la plus raide au début"
  },
  "взвесь в поле тяжести приходит в равновесие": {
    "en": "a suspension in gravity settles into equilibrium",
    "es": "una suspensión en gravedad alcanza el equilibrio",
    "ar": "المعلّق في حقل الجاذبية يبلغ التوازن",
    "fr": "une suspension dans la pesanteur atteint l'équilibre"
  },
  "оседание": {
    "en": "settling",
    "es": "sedimentación",
    "ar": "الترسّب",
    "fr": "sédimentation"
  },
  "встречные потоки равны — картина не меняется": {
    "en": "the opposing fluxes are equal — the picture does not change",
    "es": "los flujos opuestos son iguales: la imagen no cambia",
    "ar": "التدفّقان المتعاكسان متساويان — الصورة لا تتغيّر",
    "fr": "les flux opposés sont égaux — l'image ne change pas"
  },
  "в равновесии два потока равны": {
    "en": "at equilibrium the two fluxes are equal",
    "es": "en equilibrio los dos flujos son iguales",
    "ar": "عند التوازن يتساوى التدفّقان",
    "fr": "à l'équilibre les deux flux sont égaux"
  },
  "снос силой": {
    "en": "drift under the force",
    "es": "arrastre por la fuerza",
    "ar": "الانجراف بفعل القوة",
    "fr": "dérive sous la force"
  },
  "подставили n = n₀e^(−Fx/kT) — сократились и n, и F": {
    "en": "substitute n = n₀e^(−Fx/kT) — both n and F cancel",
    "es": "sustituimos n = n₀e^(−Fx/kT): se cancelan n y F",
    "ar": "بالتعويض n = n₀e^(−Fx/kT) يُختصر كلّ من n و F",
    "fr": "on substitue n = n₀e^(−Fx/kT) — n et F s'éliminent"
  },
  "трение и разброс задаются одной величиной": {
    "en": "friction and spreading are set by one and the same quantity",
    "es": "la fricción y la dispersión las fija una misma magnitud",
    "ar": "الاحتكاك والانتشار يحدّدهما المقدار نفسه",
    "fr": "le frottement et l'étalement sont fixés par une même grandeur"
  },
  "откуда берётся коэффициент трения": {
    "en": "where the friction coefficient comes from",
    "es": "de dónde sale el coeficiente de fricción",
    "ar": "من أين يأتي معامل الاحتكاك",
    "fr": "d'où vient le coefficient de frottement"
  },
  "вязкость η": {
    "en": "viscosity η",
    "es": "viscosidad η",
    "ar": "اللزوجة η",
    "fr": "viscosité η"
  },
  "скорость v": {
    "en": "velocity v",
    "es": "velocidad v",
    "ar": "السرعة v",
    "fr": "vitesse v"
  },
  "сила трения": {
    "en": "drag force",
    "es": "fuerza de fricción",
    "ar": "قوة الاحتكاك",
    "fr": "force de frottement"
  },
  "положения крупинки через равные промежутки": {
    "en": "positions of one grain at equal time intervals",
    "es": "posiciones de un grano a intervalos iguales",
    "ar": "مواضع الحُبيبة على فترات زمنية متساوية",
    "fr": "positions d'un grain à intervalles égaux"
  },
  "сетка окуляра": {
    "en": "eyepiece grid",
    "es": "retícula del ocular",
    "ar": "شبكة العدسة العينية",
    "fr": "réticule de l'oculaire"
  },
  "каждый отрезок — смещение за 30 секунд": {
    "en": "each segment is the displacement in 30 seconds",
    "es": "cada segmento es el desplazamiento en 30 segundos",
    "ar": "كل قطعة هي الإزاحة خلال 30 ثانية",
    "fr": "chaque segment est le déplacement en 30 secondes"
  },
  "усредняем квадраты отрезков — получаем ⟨x²⟩": {
    "en": "average the squares of the segments — that is ⟨x²⟩",
    "es": "promediamos los cuadrados de los segmentos: eso es ⟨x²⟩",
    "ar": "نأخذ متوسّط مربّعات القطع فنحصل على ⟨x²⟩",
    "fr": "on moyenne les carrés des segments — c'est ⟨x²⟩"
  },
  "гребень стоит на своём узле сопутствующей сетки": {
    "en": "a crest stays on its own comoving grid node",
    "es": "la cresta permanece en su nodo de la malla comóvil",
    "ar": "القمة تبقى عند عقدتها في الشبكة المرافقة",
    "fr": "la crête reste sur son nœud de la grille comobile"
  },
  "λ при излучении": {
    "en": "λ at emission",
    "es": "λ en la emisión",
    "ar": "λ عند الإصدار",
    "fr": "λ à l'émission"
  },
  "λ при приёме": {
    "en": "λ at reception",
    "es": "λ en la recepción",
    "ar": "λ عند الاستقبال",
    "fr": "λ à la réception"
  },
  "Δχ между гребнями не меняется — растёт только a": {
    "en": "Δχ between crests is unchanged — only a grows",
    "es": "Δχ entre crestas no cambia: solo crece a",
    "ar": "Δχ بين القمتين لا يتغير — ينمو a فقط",
    "fr": "Δχ entre les crêtes ne change pas — seul a croît"
  },
  "узор линий не искажается — он смещается целиком": {
    "en": "the line pattern is not distorted — it shifts as a whole",
    "es": "el patrón de líneas no se deforma: se desplaza entero",
    "ar": "نمط الخطوط لا يتشوّه — بل ينزاح ككل",
    "fr": "le motif des raies ne se déforme pas — il se décale en bloc"
  },
  "лаборатория": {
    "en": "laboratory",
    "es": "laboratorio",
    "ar": "المختبر",
    "fr": "laboratoire"
  },
  "Hα 656 нм": {
    "en": "Hα 656 nm",
    "es": "Hα 656 nm",
    "ar": "Hα 656 nm",
    "fr": "Hα 656 nm"
  },
  "Hα 702 нм": {
    "en": "Hα 702 nm",
    "es": "Hα 702 nm",
    "ar": "Hα 702 nm",
    "fr": "Hα 702 nm"
  },
  "по каждой линии z выходит одним и тем же": {
    "en": "every line must give the same z",
    "es": "cada línea debe dar el mismo z",
    "ar": "كل خط يعطي القيمة نفسها لـ z",
    "fr": "chaque raie donne le même z"
  },
  "рядом с сегодня кривая a(t) — почти прямая": {
    "en": "near today the curve a(t) is almost a straight line",
    "es": "cerca de hoy la curva a(t) es casi una recta",
    "ar": "قرب اليوم يكون منحنى a(t) شبه مستقيم",
    "fr": "près d'aujourd'hui la courbe a(t) est presque une droite"
  },
  "настоящая a(t)": {
    "en": "true a(t)",
    "es": "a(t) real",
    "ar": "a(t) الحقيقي",
    "fr": "vraie a(t)"
  },
  "сегодня": {
    "en": "today",
    "es": "hoy",
    "ar": "اليوم",
    "fr": "aujourd'hui"
  },
  "z = 0,1": {
    "en": "z = 0.1",
    "es": "z = 0,1",
    "ar": "z = 0.1",
    "fr": "z = 0,1"
  },
  "z = 0,5": {
    "en": "z = 0.5",
    "es": "z = 0,5",
    "ar": "z = 0.5",
    "fr": "z = 0,5"
  },
  "проценты": {
    "en": "a few percent",
    "es": "unos pocos por ciento",
    "ar": "بضعة بالمئة",
    "fr": "quelques pour cent"
  },
  "десятки процентов": {
    "en": "tens of percent",
    "es": "decenas de por ciento",
    "ar": "عشرات بالمئة",
    "fr": "des dizaines de pour cent"
  },
  "вся кривая": {
    "en": "the whole curve",
    "es": "toda la curva",
    "ar": "المنحنى كله",
    "fr": "toute la courbe"
  },
  "линейная формула честна примерно до z = 0,1": {
    "en": "the linear formula holds up to about z = 0.1",
    "es": "la fórmula lineal vale hasta z ≈ 0,1",
    "ar": "الصيغة الخطية صالحة حتى z ≈ 0.1 تقريبًا",
    "fr": "la formule linéaire est valable jusqu'à z ≈ 0,1 environ"
  },
  "мысленная плоскость в неоднородном газе": {
    "en": "an imaginary plane in a non-uniform gas",
    "es": "un plano imaginario en un gas no uniforme",
    "ar": "مستوٍ تخيّلي في غاز غير متجانس",
    "fr": "un plan imaginaire dans un gaz non uniforme"
  },
  "больше пересечений": {
    "en": "more crossings",
    "es": "más cruces",
    "ar": "عمليات عبور أكثر",
    "fr": "plus de traversées"
  },
  "меньше пересечений": {
    "en": "fewer crossings",
    "es": "menos cruces",
    "ar": "عمليات عبور أقل",
    "fr": "moins de traversées"
  },
  "гуще": {
    "en": "denser",
    "es": "más denso",
    "ar": "أكثف",
    "fr": "plus dense"
  },
  "реже": {
    "en": "sparser",
    "es": "más diluido",
    "ar": "أقل كثافة",
    "fr": "moins dense"
  },
  "слева молекул больше — значит, и пересечений слева направо больше": {
    "en": "more molecules on the left, so more crossings from left to right",
    "es": "hay más moléculas a la izquierda, por eso hay más cruces de izquierda a derecha",
    "ar": "الجزيئات أكثر على اليسار، لذلك العبور من اليسار إلى اليمين أكثر",
    "fr": "plus de molécules à gauche, donc plus de traversées de gauche à droite"
  },
  "грубая модель: шесть направлений, по одной шестой на каждое": {
    "en": "a crude model: six directions, one sixth for each",
    "es": "modelo tosco: seis direcciones, un sexto para cada una",
    "ar": "نموذج تقريبي: ستة اتجاهات، سدس لكل منها",
    "fr": "modèle grossier : six directions, un sixième pour chacune"
  },
  "на единицу площади за секунду": {
    "en": "per unit area per second",
    "es": "por unidad de área y segundo",
    "ar": "لكل وحدة مساحة في الثانية",
    "fr": "par unité de surface et par seconde"
  },
  "точный расчёт даёт ¼ вместо ⅙ — на оценку порядка это не влияет": {
    "en": "the exact calculation gives ¼ instead of ⅙ — the order of magnitude is unaffected",
    "es": "el cálculo exacto da ¼ en vez de ⅙: el orden de magnitud no cambia",
    "ar": "الحساب الدقيق يعطي ¼ بدل ⅙ — ورتبة المقدار لا تتغيّر",
    "fr": "le calcul exact donne ¼ au lieu de ⅙ — sans effet sur l'ordre de grandeur"
  },
  "молекула приносит концентрацию с расстояния λ": {
    "en": "a molecule brings the concentration from a distance λ away",
    "es": "la molécula trae la concentración desde una distancia λ",
    "ar": "الجزيء يحمل التركيز من مسافة λ",
    "fr": "la molécule apporte la concentration depuis une distance λ"
  },
  "последнее столкновение": {
    "en": "last collision",
    "es": "última colisión",
    "ar": "آخر تصادم",
    "fr": "dernière collision"
  },
  "приносит n(x−λ)": {
    "en": "brings n(x−λ)",
    "es": "trae n(x−λ)",
    "ar": "يحمل n(x−λ)",
    "fr": "apporte n(x−λ)"
  },
  "между столкновениями молекула летит по прямой и ничего не забывает": {
    "en": "between collisions a molecule flies straight and forgets nothing",
    "es": "entre colisiones la molécula vuela recto y no olvida nada",
    "ar": "بين التصادمات يطير الجزيء في خط مستقيم ولا ينسى شيئاً",
    "fr": "entre deux collisions la molécule vole en ligne droite et n'oublie rien"
  },
  "на длине λ концентрация меняется почти линейно": {
    "en": "over a length λ the concentration changes almost linearly",
    "es": "en una longitud λ la concentración cambia casi linealmente",
    "ar": "على طول λ يتغيّر التركيز خطياً تقريباً",
    "fr": "sur une longueur λ la concentration varie presque linéairement"
  },
  "поток идёт против градиента": {
    "en": "the flux runs against the gradient",
    "es": "el flujo va en contra del gradiente",
    "ar": "التدفق يسير عكس التدرّج",
    "fr": "le flux va à contre-gradient"
  },
  "поток j": {
    "en": "flux j",
    "es": "flujo j",
    "ar": "التدفق j",
    "fr": "flux j"
  },
  "рост концентрации": {
    "en": "concentration increases",
    "es": "la concentración crece",
    "ar": "التركيز يتزايد",
    "fr": "la concentration croît"
  },
  "поток и градиент смотрят в разные стороны — отсюда минус": {
    "en": "flux and gradient point opposite ways — hence the minus sign",
    "es": "flujo y gradiente apuntan en sentidos opuestos: de ahí el signo menos",
    "ar": "التدفق والتدرّج في اتجاهين متعاكسين — ومن هنا إشارة السالب",
    "fr": "flux et gradient pointent en sens opposés — d'où le signe moins"
  },
  "что втекло минус что вытекло — то накопилось": {
    "en": "what flowed in minus what flowed out is what accumulated",
    "es": "lo que entró menos lo que salió es lo que se acumuló",
    "ar": "ما دخل ناقص ما خرج هو ما تراكم",
    "fr": "ce qui est entré moins ce qui est sorti, voilà ce qui s'est accumulé"
  },
  "накопление": {
    "en": "accumulation",
    "es": "acumulación",
    "ar": "التراكم",
    "fr": "accumulation"
  },
  "ширина пятна растёт как корень из времени": {
    "en": "the width of the spot grows as the square root of time",
    "es": "el ancho de la mancha crece como la raíz cuadrada del tiempo",
    "ar": "عرض البقعة يزداد كجذر الزمن",
    "fr": "la largeur de la tache croît comme la racine du temps"
  },
  "ширина": {
    "en": "width",
    "es": "ancho",
    "ar": "العرض",
    "fr": "largeur"
  },
  "вчетверо дольше — всего вдвое шире": {
    "en": "four times longer — only twice as wide",
    "es": "cuatro veces más tiempo, solo el doble de ancho",
    "ar": "أربعة أضعاف الزمن — الضِعف فقط في العرض",
    "fr": "quatre fois plus longtemps — seulement deux fois plus large"
  },
  "от чего зависит коэффициент диффузии": {
    "en": "what the diffusion coefficient depends on",
    "es": "de qué depende el coeficiente de difusión",
    "ar": "على ماذا يعتمد معامل الانتشار",
    "fr": "de quoi dépend le coefficient de diffusion"
  },
  "длина пробега": {
    "en": "mean free path",
    "es": "recorrido libre medio",
    "ar": "المسار الحر المتوسط",
    "fr": "libre parcours moyen"
  },
  "тепловая скорость": {
    "en": "thermal speed",
    "es": "velocidad térmica",
    "ar": "السرعة الحرارية",
    "fr": "vitesse thermique"
  },
  "нагрели вдвое — D вырос почти втрое; сжали вдвое — D упал вдвое": {
    "en": "double the temperature — D nearly triples; double the pressure — D halves",
    "es": "doblar la temperatura casi triplica D; doblar la presión lo reduce a la mitad",
    "ar": "مضاعفة الحرارة تزيد D نحو ثلاثة أضعاف؛ مضاعفة الضغط تنصّفه",
    "fr": "doubler la température triple presque D ; doubler la pression le divise par deux"
  },
  "время": {
    "en": "time",
    "es": "tiempo",
    "ar": "الزمن",
    "fr": "temps"
  },
  "выпуклая кривая: каждому наклону — своя касательная": {
    "en": "a convex curve: one tangent for every slope",
    "es": "curva convexa: una tangente para cada pendiente",
    "ar": "منحنى محدّب: لكل ميل مماس واحد",
    "fr": "courbe convexe : une tangente pour chaque pente"
  },
  "наклон = p": {
    "en": "slope = p",
    "es": "pendiente = p",
    "ar": "الميل = p",
    "fr": "pente = p"
  },
  "дифференцируем H = p&#8201;q&#775; &#8722; L по всем переменным сразу": {
    "en": "differentiate H = p&#8201;q&#775; &#8722; L in all variables at once",
    "es": "diferenciamos H = p&#8201;q&#775; &#8722; L en todas las variables a la vez",
    "ar": "نفاضل H = p&#8201;q&#775; &#8722; L بالنسبة لكل المتغيرات معًا",
    "fr": "différentions H = p&#8201;q&#775; &#8722; L selon toutes les variables"
  },
  "ноль по определению импульса": {
    "en": "zero by the definition of momentum",
    "es": "cero por la definición del momento",
    "ar": "صفر بحكم تعريف كمية الحركة",
    "fr": "nul par la définition de l’impulsion"
  },
  "скорость исчезла из ответа — обмен честный": {
    "en": "velocity is gone from the answer: the swap is honest",
    "es": "la velocidad desaparece del resultado: el cambio es legítimo",
    "ar": "اختفت السرعة من النتيجة: التبديل سليم",
    "fr": "la vitesse a disparu du résultat : l’échange est honnête"
  },
  "dq и dp независимы — коэффициенты сравниваем порознь": {
    "en": "dq and dp are independent: coefficients match separately",
    "es": "dq y dp son independientes: los coeficientes se igualan por separado",
    "ar": "dq وdp مستقلان: تُطابق المعاملات كلٌّ على حدة",
    "fr": "dq et dp sont indépendants : coefficients comparés séparément"
  },
  "из Лежандра и Лагранжа": {
    "en": "from Legendre and Lagrange",
    "es": "de Legendre y Lagrange",
    "ar": "من ليجاندر ولاغرانج",
    "fr": "de Legendre et Lagrange"
  },
  "общий вид дифференциала": {
    "en": "the general form of a differential",
    "es": "forma general del diferencial",
    "ar": "الصيغة العامة للتفاضل",
    "fr": "forme générale de la différentielle"
  },
  "минус пришёл из первой строки, а не введён рукой": {
    "en": "the minus comes from the first line, not by hand",
    "es": "el signo menos viene de la primera línea, no se pone a mano",
    "ar": "الإشارة السالبة تأتي من السطر الأول لا باليد",
    "fr": "le moins vient de la première ligne, pas de la main"
  },
  "облако состояний течёт как несжимаемая жидкость": {
    "en": "the cloud of states flows like an incompressible fluid",
    "es": "la nube de estados fluye como un fluido incompresible",
    "ar": "سحابة الحالات تجري كمائع غير قابل للانضغاط",
    "fr": "le nuage d’états s’écoule comme un fluide incompressible"
  },
  "позже": {
    "en": "later",
    "es": "más tarde",
    "ar": "لاحقًا",
    "fr": "plus tard"
  },
  "ещё позже": {
    "en": "later still",
    "es": "aún más tarde",
    "ar": "بعد ذلك",
    "fr": "encore plus tard"
  },
  "площадь пятна одна и та же": {
    "en": "the area of the blob is the same",
    "es": "el área de la mancha es la misma",
    "ar": "مساحة البقعة هي نفسها",
    "fr": "l’aire de la tache est la même"
  },
  "слой воздуха толщиной Δh покоится": {
    "en": "a layer of air of thickness Δh is at rest",
    "es": "una capa de aire de espesor Δh está en reposo",
    "ar": "طبقة هواء سماكتها Δh في حالة سكون",
    "fr": "une couche d'air d'épaisseur Δh est au repos"
  },
  "столб воздуха": {
    "en": "column of air",
    "es": "columna de aire",
    "ar": "عمود الهواء",
    "fr": "colonne d'air"
  },
  "сумма трёх сил равна нулю": {
    "en": "the three forces sum to zero",
    "es": "las tres fuerzas suman cero",
    "ar": "مجموع القوى الثلاث يساوي صفراً",
    "fr": "la somme des trois forces est nulle"
  },
  "отношение не зависит от толщины слоя": {
    "en": "the ratio does not depend on the layer thickness",
    "es": "la razón no depende del espesor de la capa",
    "ar": "النسبة لا تعتمد على سماكة الطبقة",
    "fr": "le rapport ne dépend pas de l'épaisseur"
  },
  "толстый слой": {
    "en": "thick layer",
    "es": "capa gruesa",
    "ar": "طبقة سميكة",
    "fr": "couche épaisse"
  },
  "тоньше": {
    "en": "thinner",
    "es": "más delgada",
    "ar": "أرق",
    "fr": "plus mince"
  },
  "в пределе": {
    "en": "in the limit",
    "es": "en el límite",
    "ar": "في الحد",
    "fr": "à la limite"
  },
  "одна температура: плотность идёт следом за давлением": {
    "en": "one temperature: density follows the pressure",
    "es": "una sola temperatura: la densidad sigue a la presión",
    "ar": "درجة حرارة واحدة: الكثافة تتبع الضغط",
    "fr": "une seule température : la densité suit la pression"
  },
  "T одинакова": {
    "en": "T is the same",
    "es": "T es la misma",
    "ar": "T واحدة",
    "fr": "T identique"
  },
  "давление высокое": {
    "en": "high pressure",
    "es": "presión alta",
    "ar": "ضغط مرتفع",
    "fr": "pression élevée"
  },
  "давление низкое": {
    "en": "low pressure",
    "es": "presión baja",
    "ar": "ضغط منخفض",
    "fr": "pression faible"
  },
  "наклон пропорционален самому значению": {
    "en": "the slope is proportional to the value itself",
    "es": "la pendiente es proporcional al propio valor",
    "ar": "الميل يتناسب مع القيمة نفسها",
    "fr": "la pente est proportionnelle à la valeur elle-même"
  },
  "высота ⟶": {
    "en": "altitude ⟶",
    "es": "altura ⟶",
    "ar": "الارتفاع ⟵",
    "fr": "altitude ⟶"
  },
  "только высота": {
    "en": "altitude only",
    "es": "solo la altura",
    "ar": "الارتفاع وحده",
    "fr": "l'altitude seule"
  },
  "∫ каждую часть отдельно": {
    "en": "∫ each side separately",
    "es": "∫ cada parte por separado",
    "ar": "∫ كل طرف على حدة",
    "fr": "∫ chaque membre séparément"
  },
  "каждая шкала высот отнимает одну и ту же долю": {
    "en": "each scale height removes the same fraction",
    "es": "cada altura de escala quita la misma fracción",
    "ar": "كل ارتفاع مقياسي يقتطع النسبة نفسها",
    "fr": "chaque hauteur d'échelle retire la même fraction"
  },
  "высота, в шкалах H": {
    "en": "altitude, in units of H",
    "es": "altura, en unidades de H",
    "ar": "الارتفاع بوحدات H",
    "fr": "altitude, en unités de H"
  },
  "у каждого газа своя шкала высот": {
    "en": "every gas has its own scale height",
    "es": "cada gas tiene su propia altura de escala",
    "ar": "لكل غاز ارتفاعه المقياسي",
    "fr": "chaque gaz a sa propre hauteur d'échelle"
  },
  "водород: 120 км": {
    "en": "hydrogen: 120 km",
    "es": "hidrógeno: 120 km",
    "ar": "الهيدروجين: 120 km",
    "fr": "hydrogène : 120 km"
  },
  "азот: 8,7 км": {
    "en": "nitrogen: 8.7 km",
    "es": "nitrógeno: 8,7 km",
    "ar": "النيتروجين: 8.7 km",
    "fr": "azote : 8,7 km"
  },
  "углекислый газ: 5,5 км": {
    "en": "carbon dioxide: 5.5 km",
    "es": "dióxido de carbono: 5,5 km",
    "ar": "ثاني أكسيد الكربون: 5.5 km",
    "fr": "dioxyde de carbone : 5,5 km"
  },
  "высота, км": {
    "en": "altitude, km",
    "es": "altura, km",
    "ar": "الارتفاع، km",
    "fr": "altitude, km"
  },
  "H = kT / (mg): чем тяжелее молекула, тем ниже столб": {
    "en": "H = kT/(mg): the heavier the molecule, the lower the column",
    "es": "H = kT/(mg): cuanto más pesada la molécula, más bajo el pilar",
    "ar": "H = kT/(mg): كلما ثقل الجزيء انخفض العمود",
    "fr": "H = kT/(mg) : plus la molécule est lourde, plus la colonne est basse"
  },
  "заселённость падает экспоненциально с энергией": {
    "en": "level population falls exponentially with energy",
    "es": "la población decae exponencialmente con la energía",
    "ar": "إشغال المستوى يتناقص أسّياً مع الطاقة",
    "fr": "la population décroît exponentiellement avec l'énergie"
  },
  "колебание N₂: 11 kT": {
    "en": "N₂ vibration: 11 kT",
    "es": "vibración de N₂: 11 kT",
    "ar": "اهتزاز N₂: 11 kT",
    "fr": "vibration de N₂ : 11 kT"
  },
  "одна молекула из 80 000": {
    "en": "one molecule in 80,000",
    "es": "una molécula de cada 80 000",
    "ar": "جزيء واحد من كل 80000",
    "fr": "une molécule sur 80 000"
  },
  "счёт пересечений одинаков в обе стороны": {
    "en": "the count of crossings is the same both ways",
    "es": "el número de cruces es igual en ambos sentidos",
    "ar": "عدد العبورات متساوٍ في الاتجاهين",
    "fr": "le nombre de traversées est le même dans les deux sens"
  },
  "горячее": {
    "en": "hotter",
    "es": "más caliente",
    "ar": "أسخن",
    "fr": "plus chaud"
  },
  "холоднее": {
    "en": "colder",
    "es": "más frío",
    "ar": "أبرد",
    "fr": "plus froid"
  },
  "энергии больше": {
    "en": "more energy",
    "es": "más energía",
    "ar": "طاقة أكبر",
    "fr": "plus d'énergie"
  },
  "энергии меньше": {
    "en": "less energy",
    "es": "menos energía",
    "ar": "طاقة أقل",
    "fr": "moins d'énergie"
  },
  "переносится разность энергий, а не число частиц": {
    "en": "what is transported is the difference of energies, not the number of particles",
    "es": "se transporta la diferencia de energías, no el número de partículas",
    "ar": "المنقول هو فرق الطاقات، لا عدد الجسيمات",
    "fr": "ce qui est transporté est la différence d'énergies, non le nombre de particules"
  },
  "молекула помнит последнее столкновение": {
    "en": "a molecule remembers its last collision",
    "es": "la molécula recuerda su última colisión",
    "ar": "الجزيء يتذكر آخر تصادم له",
    "fr": "la molécule se souvient de sa dernière collision"
  },
  "приносит энергию точки x &#8722; &#955;": {
    "en": "it brings the energy of the point x &#8722; &#955;",
    "es": "trae la energía del punto x &#8722; &#955;",
    "ar": "يحمل طاقة النقطة x &#8722; &#955;",
    "fr": "elle apporte l'énergie du point x &#8722; &#955;"
  },
  "на отрезке в две длины пробега кривая неотличима от прямой": {
    "en": "over two mean free paths the curve is indistinguishable from a straight line",
    "es": "en dos recorridos libres medios la curva es indistinguible de una recta",
    "ar": "على مسافة مسارين حرين يصبح المنحنى غير مميز عن الخط المستقيم",
    "fr": "sur deux libres parcours la courbe est indiscernable d'une droite"
  },
  "профиль температуры": {
    "en": "temperature profile",
    "es": "perfil de temperatura",
    "ar": "منحنى توزع درجة الحرارة",
    "fr": "profil de température"
  },
  "одноатомный: три степени свободы": {
    "en": "monatomic: three degrees of freedom",
    "es": "monoatómico: tres grados de libertad",
    "ar": "أحادي الذرة: ثلاث درجات حرية",
    "fr": "monoatomique : trois degrés de liberté"
  },
  "двухатомный: пять": {
    "en": "diatomic: five",
    "es": "diatómico: cinco",
    "ar": "ثنائي الذرة: خمس",
    "fr": "diatomique : cinq"
  },
  "теплоёмкость одной молекулы": {
    "en": "heat capacity of a single molecule",
    "es": "capacidad calorífica de una molécula",
    "ar": "السعة الحرارية لجزيء واحد",
    "fr": "capacité thermique d'une seule molécule"
  },
  "рост температуры": {
    "en": "temperature rises",
    "es": "la temperatura crece",
    "ar": "اتجاه ازدياد الحرارة",
    "fr": "la température croît"
  },
  "поток тепла": {
    "en": "heat flux",
    "es": "flujo de calor",
    "ar": "التدفق الحراري",
    "fr": "flux de chaleur"
  },
  "плотный газ": {
    "en": "dense gas",
    "es": "gas denso",
    "ar": "غاز كثيف",
    "fr": "gaz dense"
  },
  "разрежённый вдвое": {
    "en": "twice as rarefied",
    "es": "dos veces más enrarecido",
    "ar": "أقل كثافة بمقدار الضعف",
    "fr": "deux fois plus raréfié"
  },
  "пробег короче": {
    "en": "shorter free path",
    "es": "recorrido más corto",
    "ar": "مسار حر أقصر",
    "fr": "libre parcours plus court"
  },
  "пробег вдвое длиннее": {
    "en": "free path twice as long",
    "es": "recorrido dos veces más largo",
    "ar": "مسار حر أطول بالضعف",
    "fr": "libre parcours deux fois plus long"
  },
  "произведение n&#183;&#955; не зависит от давления": {
    "en": "the product n&#183;&#955; does not depend on pressure",
    "es": "el producto n&#183;&#955; no depende de la presión",
    "ar": "الجداء n&#183;&#955; لا يعتمد على الضغط",
    "fr": "le produit n&#183;&#955; ne dépend pas de la pression"
  },
  "температура падает по прямой в каждом слое": {
    "en": "temperature falls along a straight line in each layer",
    "es": "la temperatura cae en línea recta en cada capa",
    "ar": "تنخفض درجة الحرارة خطياً داخل كل طبقة",
    "fr": "la température décroît linéairement dans chaque couche"
  },
  "кирпич": {
    "en": "brick",
    "es": "ladrillo",
    "ar": "الطوب",
    "fr": "brique"
  },
  "утеплитель": {
    "en": "insulation",
    "es": "aislante",
    "ar": "المادة العازلة",
    "fr": "isolant"
  },
  "R = L / &#954;, сопротивления складываются": {
    "en": "R = L / &#954;, resistances add up",
    "es": "R = L / &#954;, las resistencias se suman",
    "ar": "R = L / &#954;، المقاومات تتجمع",
    "fr": "R = L / &#954;, les résistances s'additionnent"
  },
  "поток одинаков во всех сечениях": {
    "en": "the flux is the same through every cross-section",
    "es": "el flujo es el mismo en todas las secciones",
    "ar": "التدفق نفسه عبر كل مقطع",
    "fr": "le flux est le même à travers chaque section"
  },
  "диэлектрик: колебания решётки": {
    "en": "insulator: lattice vibrations",
    "es": "dieléctrico: vibraciones de la red",
    "ar": "عازل: اهتزازات الشبكة البلورية",
    "fr": "diélectrique : vibrations du réseau"
  },
  "металл: электроны проводимости": {
    "en": "metal: conduction electrons",
    "es": "metal: electrones de conducción",
    "ar": "معدن: إلكترونات التوصيل",
    "fr": "métal : électrons de conduction"
  },
  "медленно": {
    "en": "slow",
    "es": "lento",
    "ar": "بطيء",
    "fr": "lent"
  },
  "быстро": {
    "en": "fast",
    "es": "rápido",
    "ar": "سريع",
    "fr": "rapide"
  },
  "&#954; / (&#963;T) = 2,44&#183;10&#8315;&#8312; Вт&#183;Ом/К&#178;": {
    "en": "&#954; / (&#963;T) = 2.44&#183;10&#8315;&#8312; W&#183;&#937;/K&#178;",
    "es": "&#954; / (&#963;T) = 2,44&#183;10&#8315;&#8312; W&#183;&#937;/K&#178;",
    "ar": "&#954; / (&#963;T) = 2.44&#183;10&#8315;&#8312; W&#183;&#937;/K&#178;",
    "fr": "&#954; / (&#963;T) = 2,44&#183;10&#8315;&#8312; W&#183;&#937;/K&#178;"
  },
  "одни и те же частицы несут заряд и тепло": {
    "en": "the same particles carry both charge and heat",
    "es": "las mismas partículas llevan carga y calor",
    "ar": "الجسيمات نفسها تحمل الشحنة والحرارة",
    "fr": "les mêmes particules transportent charge et chaleur"
  },
  "одна температура — разные скорости": {
    "en": "one temperature — many speeds",
    "es": "una temperatura, muchas velocidades",
    "ar": "درجة حرارة واحدة — سرعات مختلفة",
    "fr": "une température, des vitesses variées"
  },
  "сколько молекул": {
    "en": "how many molecules",
    "es": "cuántas moléculas",
    "ar": "كم عدد الجزيئات",
    "fr": "combien de molécules"
  },
  "вопрос не «какая скорость», а «какая доля»": {
    "en": "the question is not «what speed» but «what fraction»",
    "es": "la pregunta no es «qué velocidad» sino «qué fracción»",
    "ar": "السؤال ليس «ما السرعة» بل «ما النسبة»",
    "fr": "la question n'est pas «quelle vitesse» mais «quelle fraction»"
  },
  "пространство скоростей": {
    "en": "velocity space",
    "es": "espacio de velocidades",
    "ar": "فضاء السرعات",
    "fr": "espace des vitesses"
  },
  "одна молекула": {
    "en": "one molecule",
    "es": "una molécula",
    "ar": "جزيء واحد",
    "fr": "une molécule"
  },
  "модуль скорости —": {
    "en": "the speed is",
    "es": "el módulo de la velocidad es",
    "ar": "مقدار السرعة هو",
    "fr": "le module de la vitesse est"
  },
  "расстояние от нуля": {
    "en": "the distance from the origin",
    "es": "la distancia al origen",
    "ar": "المسافة من نقطة الأصل",
    "fr": "la distance à l'origine"
  },
  "весь газ — облако точек, самое густое у начала координат": {
    "en": "the whole gas is a cloud of points, densest near the origin",
    "es": "todo el gas es una nube de puntos, más densa cerca del origen",
    "ar": "الغاز كله سحابة من النقاط، أكثفها قرب نقطة الأصل",
    "fr": "tout le gaz est un nuage de points, plus dense près de l'origine"
  },
  "ни одно направление не выделено": {
    "en": "no direction is singled out",
    "es": "ninguna dirección es privilegiada",
    "ar": "لا اتجاه مُفضَّل على غيره",
    "fr": "aucune direction n'est privilégiée"
  },
  "одинаковый модуль —": {
    "en": "same speed —",
    "es": "mismo módulo:",
    "ar": "المقدار نفسه —",
    "fr": "même module —"
  },
  "одинаковая плотность": {
    "en": "same density",
    "es": "misma densidad",
    "ar": "الكثافة نفسها",
    "fr": "même densité"
  },
  "плотность облака — функция одного только модуля": {
    "en": "the density of the cloud depends on the speed alone",
    "es": "la densidad de la nube depende solo del módulo",
    "ar": "كثافة السحابة دالة في المقدار وحده",
    "fr": "la densité du nuage ne dépend que du module"
  },
  "вероятность энергии падает по экспоненте": {
    "en": "the probability of an energy falls exponentially",
    "es": "la probabilidad de una energía cae exponencialmente",
    "ar": "احتمال الطاقة يتناقص أُسّيًا",
    "fr": "la probabilité d'une énergie décroît exponentiellement"
  },
  "энергия &#949;": {
    "en": "energy &#949;",
    "es": "energía &#949;",
    "ar": "الطاقة &#949;",
    "fr": "énergie &#949;"
  },
  "энергии складываются": {
    "en": "energies add",
    "es": "las energías se suman",
    "ar": "الطاقات تُجمَع",
    "fr": "les énergies s'additionnent"
  },
  "вероятности умножаются": {
    "en": "probabilities multiply",
    "es": "las probabilidades se multiplican",
    "ar": "الاحتمالات تُضرَب",
    "fr": "les probabilités se multiplient"
  },
  "сумму в произведение превращает только экспонента": {
    "en": "only the exponential turns a sum into a product",
    "es": "solo la exponencial convierte una suma en un producto",
    "ar": "الدالة الأُسّية وحدها تحوّل الجمع إلى ضرب",
    "fr": "seule l'exponentielle change une somme en produit"
  },
  "все молекулы с модулем v лежат в шаровом слое": {
    "en": "every molecule of speed v lies in a spherical shell",
    "es": "todas las moléculas de módulo v están en una capa esférica",
    "ar": "كل الجزيئات ذات المقدار v تقع في قشرة كروية",
    "fr": "toutes les molécules de module v sont dans une coque sphérique"
  },
  "площадь сферы": {
    "en": "area of the sphere",
    "es": "área de la esfera",
    "ar": "مساحة الكرة",
    "fr": "aire de la sphère"
  },
  "толщина слоя": {
    "en": "thickness of the shell",
    "es": "espesor de la capa",
    "ar": "سُمك القشرة",
    "fr": "épaisseur de la coque"
  },
  "объём 4&#960;v²dv": {
    "en": "volume 4&#960;v²dv",
    "es": "volumen 4&#960;v²dv",
    "ar": "الحجم 4&#960;v²dv",
    "fr": "volume 4&#960;v²dv"
  },
  "при v → 0 слой стягивается в точку — медленных молекул почти нет": {
    "en": "as v → 0 the shell shrinks to a point — slow molecules are almost absent",
    "es": "cuando v → 0 la capa se reduce a un punto: casi no hay moléculas lentas",
    "ar": "عندما v → 0 تنكمش القشرة إلى نقطة — تكاد الجزيئات البطيئة تنعدم",
    "fr": "quand v → 0 la coque se réduit à un point : presque pas de molécules lentes"
  },
  "горка получается из борьбы двух сомножителей": {
    "en": "the hump is the result of two competing factors",
    "es": "la joroba surge de la pugna entre dos factores",
    "ar": "الحدبة نتيجة تنازع عاملين",
    "fr": "la bosse naît de la lutte entre deux facteurs"
  },
  "слева душит геометрия, справа — экспонента, максимум посередине": {
    "en": "geometry chokes it on the left, the exponential on the right, the peak sits between",
    "es": "geometría a la izquierda, exponencial a la derecha: el máximo en medio",
    "ar": "الهندسة تخنقها يسارًا والأُسّية يمينًا، والقمة بينهما",
    "fr": "la géométrie l'étouffe à gauche, l'exponentielle à droite, le maximum est entre les deux"
  },
  "три скорости одного и того же газа": {
    "en": "three speeds of one and the same gas",
    "es": "tres velocidades del mismo gas",
    "ar": "ثلاث سرعات لغاز واحد بعينه",
    "fr": "trois vitesses d'un seul et même gaz"
  },
  "вероятнейшая": {
    "en": "most probable",
    "es": "más probable",
    "ar": "الأكثر احتمالًا",
    "fr": "la plus probable"
  },
  "средняя": {
    "en": "mean",
    "es": "media",
    "ar": "المتوسطة",
    "fr": "moyenne"
  },
  "среднеквадр.": {
    "en": "rms",
    "es": "cuadr. media",
    "ar": "الجذر التربيعي",
    "fr": "quadr. moyenne"
  },
  "длинный хвост тянет среднее вправо": {
    "en": "the long tail pulls the mean to the right",
    "es": "la cola larga arrastra la media hacia la derecha",
    "ar": "الذيل الطويل يجذب المتوسط إلى اليمين",
    "fr": "la longue queue tire la moyenne vers la droite"
  },
  "отношение 1 : 1,128 : 1,225 одинаково для любого газа": {
    "en": "the ratio 1 : 1.128 : 1.225 is the same for any gas",
    "es": "la razón 1 : 1,128 : 1,225 es la misma para cualquier gas",
    "ar": "النسبة 1 : 1,128 : 1,225 واحدة لأي غاز",
    "fr": "le rapport 1 : 1,128 : 1,225 est le même pour tout gaz"
  },
  "порог сдвинулся чуть — хвост вырос в разы": {
    "en": "the threshold barely moved — the tail grew several times over",
    "es": "el umbral se movió poco, la cola creció varias veces",
    "ar": "العتبة تحركت قليلًا — والذيل تضاعف أضعافًا",
    "fr": "le seuil a peu bougé — la queue a été multipliée"
  },
  "порог": {
    "en": "threshold",
    "es": "umbral",
    "ar": "العتبة",
    "fr": "seuil"
  },
  "быстрее порога": {
    "en": "faster than the threshold",
    "es": "más rápidas que el umbral",
    "ar": "أسرع من العتبة",
    "fr": "plus vite que le seuil"
  },
  "средняя скорость подросла на проценты, доля за порогом — в разы": {
    "en": "the mean speed rose by percents, the fraction beyond the threshold by factors",
    "es": "la velocidad media subió un pequeño porcentaje; la fracción tras el umbral, varias veces",
    "ar": "السرعة المتوسطة ارتفعت نسبًا مئوية، أما النسبة وراء العتبة فتضاعفت",
    "fr": "la vitesse moyenne gagne des pour cent, la fraction au-delà du seuil est multipliée"
  },
  "подставляем L = K(q&#775;) &#8722; U(q)": {
    "en": "substitute L = K(q&#775;) &#8722; U(q)",
    "es": "sustituimos L = K(q&#775;) &#8722; U(q)",
    "ar": "نُعوّض L = K(q&#775;) &#8722; U(q)",
    "fr": "on remplace L = K(q&#775;) &#8722; U(q)"
  },
  "масса на ускорение": {
    "en": "mass times acceleration",
    "es": "masa por aceleración",
    "ar": "الكتلة في التسارع",
    "fr": "masse fois accélération"
  },
  "сила": {
    "en": "force",
    "es": "fuerza",
    "ar": "القوة",
    "fr": "force"
  },
  "Ньютон получился следствием, а не отдельным постулатом": {
    "en": "Newton comes out as a consequence, not a separate postulate",
    "es": "Newton resulta una consecuencia, no un postulado aparte",
    "ar": "قانون نيوتن ينتج نتيجةً، لا مُسلَّمةً منفصلة",
    "fr": "Newton en découle : ce n'est pas un postulat séparé"
  },
  "одно уравнение связывает два разных вопроса": {
    "en": "one equation ties together two different questions",
    "es": "una ecuación enlaza dos preguntas distintas",
    "ar": "معادلة واحدة تربط سؤالين مختلفين",
    "fr": "une équation relie deux questions différentes"
  },
  "сдвинем координату": {
    "en": "shift the coordinate",
    "es": "desplacemos la coordenada",
    "ar": "نُزيح الإحداثي",
    "fr": "déplaçons la coordonnée"
  },
  "изменим скорость": {
    "en": "change the velocity",
    "es": "cambiemos la velocidad",
    "ar": "نُغيّر السرعة",
    "fr": "changeons la vitesse"
  },
  "ответ на второй вопрос, взятый по времени, равен первому": {
    "en": "the answer to the second question, differentiated in time, equals the first",
    "es": "la respuesta a la segunda pregunta, derivada en el tiempo, es igual a la primera",
    "ar": "جواب السؤال الثاني، مشتقّاً بالزمن، يساوي جواب الأول",
    "fr": "la réponse à la seconde question, dérivée en temps, égale la première"
  },
  "координата меняется, а импульс держится": {
    "en": "the coordinate keeps changing, the momentum holds",
    "es": "la coordenada cambia y el momento se mantiene",
    "ar": "الإحداثي يتغيّر بينما كمية الحركة ثابتة",
    "fr": "la coordonnée varie, la quantité de mouvement tient"
  },
  "&#8706;L/&#8706;q&#775; — ровная линия": {
    "en": "&#8706;L/&#8706;q&#775; — a flat line",
    "es": "&#8706;L/&#8706;q&#775;: una línea plana",
    "ar": "&#8706;L/&#8706;q&#775; — خط مستقيم أفقي",
    "fr": "&#8706;L/&#8706;q&#775; — une ligne plate"
  },
  "сама координата при этом гуляет": {
    "en": "while the coordinate itself wanders",
    "es": "mientras la propia coordenada oscila",
    "ar": "في حين أنّ الإحداثي نفسه يتذبذب",
    "fr": "alors que la coordonnée, elle, oscille"
  },
  "вторую переменную выбираем заново": {
    "en": "the second variable is chosen anew",
    "es": "la segunda variable se elige de nuevo",
    "ar": "نختار المتغيّر الثاني من جديد",
    "fr": "on choisit à nouveau la seconde variable"
  },
  "координата и скорость": {
    "en": "coordinate and velocity",
    "es": "coordenada y velocidad",
    "ar": "الإحداثي والسرعة",
    "fr": "coordonnée et vitesse"
  },
  "координата и импульс": {
    "en": "coordinate and momentum",
    "es": "coordenada y momento",
    "ar": "الإحداثي وكمية الحركة",
    "fr": "coordonnée et quantité de mouvement"
  },
  "теперь обе переменные равноправны": {
    "en": "now both variables stand on equal footing",
    "es": "ahora ambas variables están en pie de igualdad",
    "ar": "الآن المتغيّران متكافئان",
    "fr": "les deux variables sont désormais sur un pied d'égalité"
  },
  "два уравнения первого порядка вместо одного второго": {
    "en": "two first-order equations instead of one of second order",
    "es": "dos ecuaciones de primer orden en lugar de una de segundo",
    "ar": "معادلتان من الرتبة الأولى بدل واحدة من الرتبة الثانية",
    "fr": "deux équations du premier ordre au lieu d'une du second"
  },
  "вот этот минус": {
    "en": "this very minus",
    "es": "justo este signo menos",
    "ar": "هذه الإشارة السالبة بالذات",
    "fr": "c'est ce signe moins"
  },
  "без минуса точки разбегались бы; с ним они ходят по кругу": {
    "en": "without the minus the points would run apart; with it they go round",
    "es": "sin el menos los puntos se dispersarían; con él giran en círculo",
    "ar": "بدون الإشارة السالبة تتباعد النقاط؛ ومعها تدور في حلقة",
    "fr": "sans le moins les points s'écarteraient ; avec lui ils tournent"
  },
  "состояние груза — одна точка на плоскости (q, p)": {
    "en": "the state of the weight is one point on the (q, p) plane",
    "es": "el estado de la masa es un punto en el plano (q, p)",
    "ar": "حالة الكتلة نقطة واحدة في المستوي (q, p)",
    "fr": "l'état de la masse est un point du plan (q, p)"
  },
  "q = 0, вся энергия в движении": {
    "en": "q = 0, all the energy is in motion",
    "es": "q = 0: toda la energía está en el movimiento",
    "ar": "q = 0، الطاقة كلّها في الحركة",
    "fr": "q = 0, toute l'énergie est dans le mouvement"
  },
  "энергия в пружине": {
    "en": "energy stored in the spring",
    "es": "energía en el resorte",
    "ar": "الطاقة مخزّنة في النابض",
    "fr": "énergie dans le ressort"
  },
  "полный обход эллипса — один период колебания": {
    "en": "one lap round the ellipse is one period of the oscillation",
    "es": "una vuelta completa a la elipse es un período de oscilación",
    "ar": "دورة كاملة حول القطع الناقص تساوي زمناً دورياً واحداً",
    "fr": "un tour complet de l'ellipse fait une période d'oscillation"
  },
  "каждому запасу энергии — своя замкнутая кривая": {
    "en": "each amount of energy has its own closed curve",
    "es": "a cada cantidad de energía le corresponde su curva cerrada",
    "ar": "لكل مقدار من الطاقة منحنٍ مغلق خاص به",
    "fr": "à chaque réserve d'énergie sa propre courbe fermée"
  },
  "меньше энергии": {
    "en": "less energy",
    "es": "menos energía",
    "ar": "طاقة أقل",
    "fr": "moins d'énergie"
  },
  "больше энергии": {
    "en": "more energy",
    "es": "más energía",
    "ar": "طاقة أكبر",
    "fr": "plus d'énergie"
  },
  "сойти на соседнюю кривую точка не может": {
    "en": "the point cannot step onto a neighbouring curve",
    "es": "el punto no puede pasar a una curva vecina",
    "ar": "لا يمكن للنقطة الانتقال إلى منحنٍ مجاور",
    "fr": "le point ne peut pas passer sur une courbe voisine"
  },
  "около пятнадцати процентов": {
    "en": "about fifteen per cent",
    "es": "cerca del quince por ciento",
    "ar": "نحو خمسة عشر بالمئة",
    "fr": "environ quinze pour cent"
  }
};
