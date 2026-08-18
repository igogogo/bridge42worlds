/* Проверка слоя знаний: проходит ли авторский ответ свой же квиз.
 *
 * Проверка гоняет НЕ копию правила, а сам js/quiz-grade.js — тот файл, который подключает
 * страница урока. Копия правила рано или поздно разойдётся с оригиналом, и проверка начнёт
 * подтверждать то, чего у читателя нет; здесь это невозможно по устройству.
 *
 * Что проверяется у каждого вопроса-прикидки:
 *   1. точный авторский ответ засчитывается (иначе вопрос непроходим — таких было девять);
 *   2. ответ у края допуска засчитывается, а чуть за краем — нет (иначе допуск бесконечный:
 *      «5000 эВ» принимал всё от 25 до миллиона, и вопрос переставал быть вопросом);
 *   3. знак ответа учитывается: у «порядок −10» ответ «10» не должен проходить.
 * У вопросов с выбором — что индекс верного ответа существует и вариантов не меньше двух,
 * а разбор не показывает пальцем на место («третий вариант»): порядок вариантов на странице
 * перемешивается, и такой разбор врёт читателю.
 * У свободных — что ключевые слова заданы (иначе засчитывается любой текст) и что при
 * needed > 1 они требуют разных мыслей, а не одного слова, засчитанного дважды.
 *
 * Перевод сверяется с русским как с оригиналом: тип вопроса, номер верного ответа, число
 * вариантов, числа прикидки, наличие самого квиза. Раньше каждая языковая ветка проверялась
 * в одиночку, и «квиза нет» выглядело как «проверять нечего».
 *
 *     node tools/quiz_check.js            все языки
 *     node tools/quiz_check.js --lang ru  только один
 *     node tools/quiz_check.js --legacy   старым правилом (см. ниже)
 *
 * Про --legacy. Именно этим режимом на ДОнормализованных данных были найдены девять
 * непроходимых вопросов: точный ответ автора не засчитывался, потому что старое правило
 * читало «±0,1» как «отличаться не более чем в 0,1 раза». На нынешних данных --legacy
 * ругается уже на другое — он читает tolAbs как множитель, — и это ожидаемо: режим
 * оставлен как памятник причине, а не как рабочая проверка.
 */
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..', 'data', 'theory', 'courses');
const G = require(path.join(__dirname, '..', 'js', 'quiz-grade.js'));

const argv = process.argv.slice(2);
const LEGACY = argv.includes('--legacy');
const ONE = argv.includes('--lang') ? argv[argv.indexOf('--lang') + 1] : null;
const LANGS = ONE ? [ONE] : ['ru', 'en', 'es', 'ar', 'fr'];

/** Старое правило — только для того, чтобы показать, что именно было сломано. */
function legacyEstimate(raw, q) {
    const val = parseFloat(String(raw).replace(',', '.'));
    const tol = q.tolerance || q.tolAbs || q.tolFactor || 3;
    const ratio = val > 0 && q.answer > 0 ? Math.max(val / q.answer, q.answer / val) : Infinity;
    return { ok: ratio <= tol, off: ratio, kind: 'factor', band: tol };
}
const grade = LEGACY ? legacyEstimate : G.estimate;

const problems = [];
let checked = 0, lessons = 0;

/* Ключевые слова свободного ответа грейдер ищет ПОДСТРОКОЙ (js/tutor.js: indexOf), и это
 * не придирка к стилю: при needed 2 вопрос обязан требовать двух разных мыслей, а не одной.
 * Два ключа-близнеца ломают ровно это. Дубль «ثلاثي الأبعاد» дважды даёт два очка за одно
 * слово читателя; вложенная пара — тем более: «ток» лежит внутри «поток», «эв» внутри «мэв»,
 * «ev» внутри never, level и seven. Читатель пишет одно слово — вопрос считает, что понял две
 * вещи. При needed 1 такие ключи безвредны, поэтому ругаемся только на needed > 1. */
function checkKeywords(where, q) {
    const kw = (q.keywords || []).map(k => String(k).toLowerCase().trim()).filter(Boolean);
    const need = q.needed || 1;
    if (need < 2 || !kw.length) return;
    const seen = new Set(), dup = new Set();
    kw.forEach(k => (seen.has(k) ? dup.add(k) : seen.add(k)));
    if (dup.size) {
        const many = dup.size > 1;
        problems.push(`${where}: ключ${many ? 'и' : ''} ${[...dup].map(k => `«${k}»`).join(', ')} ` +
            `повторя${many ? 'ются' : 'ется'} при needed ${need} — одно слово читателя закрывает вопрос целиком`);
    }
    const uniq = [...seen], pairs = [];
    for (let i = 0; i < uniq.length; i++) {
        for (let j = i + 1; j < uniq.length; j++) {
            const a = uniq[i], b = uniq[j];
            if (!a.includes(b) && !b.includes(a)) continue;
            const inner = a.includes(b) ? b : a, outer = a.includes(b) ? a : b;
            pairs.push(`«${inner}» внутри «${outer}»`);
        }
    }
    if (pairs.length) {
        problems.push(`${where}: при needed ${need} ключи входят друг в друга (${pairs.join('; ')}) — ` +
            `засчитываются оба за одно слово`);
    }
}

/* Варианты mcq страница ПЕРЕМЕШИВАЕТ при отрисовке (js/tutor.js: порядок тасуется, потому что
 * верный ответ стоял вторым в 64% вопросов). Значит любой разбор вида «третий вариант неверен»
 * у читателя показывает не на тот вариант — и звучит уверенно, что хуже молчания. Ищем такие
 * обороты на всех пяти языках; ловим и в подсказке, и в самом вопросе — там они врут так же. */
// Окончание слова пишем явным алфавитом, а не через \w: в JS \w — это только латиница с
// цифрами, поэтому «Последний вариант» и «première option» такому правилу не попадались,
// и по-русски проверка молчала ровно там, где нашлись живые случаи.
const RU = '[а-яё]*', ES = '[a-záéíóúñ]*', FR = '[a-zàâçéèêëîïôûùüÿœ]*';
const POSITIONAL = [
    new RegExp('(перв|втор|трет|четв[её]рт|пят|последн|верхн|нижн)' + RU + '\\s+(вариант|ответ|пункт|строк)' + RU, 'i'),
    new RegExp('(вариант|ответ|пункт)' + RU + '\\s+(перв|втор|трет|четв[её]рт|последн)' + RU, 'i'),
    /\b(first|second|third|fourth|fifth|last|final|top|bottom)\s+(option|answer|choice|item)s?\b/i,
    /\b(option|answer|choice)s?\s+(one|two|three|four)\b/i,
    // Без \b перед словом: граница слова в JS считается по латинице, и «última opción»
    // с ней не находилась — а это ровно тот случай, ради которого правило и писалось.
    new RegExp('(primer|segund|tercer|cuart|quint|[úu]ltim)' + ES + '\\s+(opci[óo]n|opciones|respuestas?)', 'i'),
    new RegExp('(opci[óo]n|respuesta)\\s+(primer|segund|tercer|cuart|[úu]ltim)' + ES, 'i'),
    new RegExp('\\b(premi|deuxi|troisi|quatri|derni)' + FR + '\\s+(options?|r[ée]ponses?|choix)\\b', 'i'),
    /(الخيار|الخيارات|الخيارين|الإجابة|الجواب)\s*(الأول|الثاني|الثالث|الرابع|الأخير|الأولى|الأخيرة|الأولان)/,
];
function checkPositional(where, q) {
    if (q.type !== 'mcq') return;
    ['why', 'hint', 'q'].forEach(field => {
        const text = q[field];
        if (typeof text !== 'string') return;
        for (const re of POSITIONAL) {
            const m = re.exec(text);
            if (m) {
                problems.push(`${where}: в «${field}» сказано «${m[0].trim()}» — варианты перемешиваются ` +
                    `при показе, читатель увидит этот вариант на другом месте`);
                return;
            }
        }
    });
}

/* Перевод квиза жил сам по себе: проверка шла по языковой ветке в одиночку и потому не видела
 * ни пропавшего квиза, ни расхождений с русским. А расходиться там есть чему — номер верного
 * ответа, число вариантов, тип вопроса, само число в прикидке: в переводе это те же данные,
 * и любое их «уточнение» превращает верный ответ в неверный на одном языке из пяти. Сверяем
 * с русским как с оригиналом. */
const CYR = /[а-яё]/i;
function compareWithRu(where, q, ru, lang) {
    if (q.type !== ru.type) {
        problems.push(`${where}: тип «${q.type}» против русского «${ru.type}»`);
        return;
    }
    if (ru.type === 'mcq') {
        if (q.answer !== ru.answer) {
            problems.push(`${where}: верный ответ ${q.answer}, по-русски ${ru.answer} — на одном из языков он неверный`);
        }
        const n = (q.options || []).length, rn = (ru.options || []).length;
        if (n !== rn) problems.push(`${where}: вариантов ${n}, по-русски ${rn}`);
    }
    if (ru.type === 'estimate') {
        ['answer', 'tolAbs', 'tolFactor', 'tolerance'].forEach(k => {
            if (q[k] !== ru[k]) problems.push(`${where}: ${k} = ${q[k]}, по-русски ${ru[k]}`);
        });
    }
    // Кириллица в keywords — пробел перевода, невидимый глазами: слова нигде не показываются,
    // а ответ на нужном языке мимо них проходит, и вопрос становится непроходимым.
    (q.keywords || []).forEach(k => {
        if (CYR.test(String(k))) problems.push(`${where}: ключевое слово «${k}» осталось русским — ` +
            `ответ на языке ${lang} его не содержит, вопрос непроходим`);
    });
}

for (const topic of fs.readdirSync(ROOT).sort()) {
    const dir = path.join(ROOT, topic);
    if (!fs.statSync(dir).isDirectory()) continue;
    for (const name of fs.readdirSync(dir).sort()) {
        if (!/^\d/.test(name) || !name.endsWith('.json')) continue;
        const data = JSON.parse(fs.readFileSync(path.join(dir, name), 'utf8'));
        lessons++;
        // Русский квиз — оригинал, с ним сверяем переводы. Читаем его всегда, даже когда
        // проверяют один язык (--lang ar): без оригинала сверять не с чем.
        const ruQuiz = (data.ru || {}).quiz || null;
        const ruById = new Map((ruQuiz || []).map(q => [q.id, q]));
        for (const lang of LANGS) {
            const branch = data[lang];
            const quiz = (branch || {}).quiz;
            // Ветка перевода есть, а квиза в ней нет — раньше это молча пропускалось, и урок
            // на трёх языках открывался без единого вопроса. Ветки нет вовсе — обычный пробел
            // перевода, о нём говорят другие проверки.
            if (!quiz) {
                if (lang !== 'ru' && branch && Object.keys(branch).length && ruQuiz) {
                    problems.push(`${topic}/${data.id} [${lang}]: перевод есть, а квиза в нём нет — ` +
                        `${ruQuiz.length} вопрос(ов) по-русски против нуля`);
                }
                continue;
            }
            if (lang !== 'ru' && ruQuiz) {
                const ids = new Set(quiz.map(q => q.id));
                ruById.forEach((_, id) => {
                    if (!ids.has(id)) problems.push(`${topic}/${data.id} [${lang}]: нет вопроса ${id}, который есть по-русски`);
                });
            }
            for (const q of quiz) {
                const where = `${topic}/${data.id} [${lang}] ${q.id}`;
                checkPositional(where, q);
                checkKeywords(where, q);
                if (lang !== 'ru' && ruQuiz) {
                    const ru = ruById.get(q.id);
                    if (!ru) problems.push(`${where}: вопроса с таким id нет по-русски`);
                    else compareWithRu(where, q, ru, lang);
                }
                if (q.type === 'estimate') {
                    checked++;
                    const exact = grade(q.answer, q);
                    if (!exact.ok) {
                        problems.push(`${where}: точный ответ ${q.answer} НЕ засчитан ` +
                            `(допуск ${exact.kind} ${exact.band}, промах ${exact.off})`);
                        continue;
                    }
                    // край допуска: внутри — да, снаружи — нет
                    const b = G.band(q);
                    const a = q.answer;
                    const inside = b.kind === 'abs' ? a + b.value * 0.95 : a * (1 + (b.value - 1) * 0.95);
                    const outside = b.kind === 'abs' ? a + b.value * 3 : a * b.value * 3;
                    if (!grade(inside, q).ok) {
                        problems.push(`${where}: ответ ${inside} внутри допуска, но не засчитан`);
                    }
                    if (grade(outside, q).ok) {
                        problems.push(`${where}: ответ ${outside} далеко за допуском, но засчитан ` +
                            `(допуск ${b.kind} ${b.value} — вопрос ничего не проверяет)`);
                    }
                    // Сам допуск тоже должен быть осмысленным. Без этой проверки скрипт
                    // «зелёный» и при tolFactor 50: край допуска считается ОТ допуска, поэтому
                    // чем он шире, тем легче его пройти. Ловили на мутации: испорченный вопрос
                    // проверка не заметила, пока не появилось правило ниже.
                    if (b.kind === 'factor' && b.value > 10) {
                        problems.push(`${where}: множитель ${b.value} шире порядка величины — ` +
                            `вопрос принимает почти любой ответ`);
                    }
                    if (b.kind === 'abs' && Math.abs(a) > 0 && b.value > Math.abs(a) * 0.6) {
                        problems.push(`${where}: допуск ±${b.value} при ответе ${a} — ` +
                            `это ${(b.value / Math.abs(a) * 100).toFixed(0)}% ответа, вопрос почти ничего не требует`);
                    }
                    if (a < 0 && grade(Math.abs(a), q).ok) {
                        problems.push(`${where}: ответ ${Math.abs(a)} противоположного знака засчитан`);
                    }
                } else if (q.type === 'mcq') {
                    checked++;
                    const n = (q.options || []).length;
                    if (n < 2) problems.push(`${where}: вариантов меньше двух`);
                    if (!(q.answer >= 0 && q.answer < n)) {
                        problems.push(`${where}: номер верного ответа ${q.answer} вне списка из ${n}`);
                    }
                } else if (q.type === 'free') {
                    checked++;
                    if (!(q.keywords || []).length) {
                        problems.push(`${where}: нет ключевых слов — засчитается любой текст`);
                    }
                }
            }
        }
    }
}

console.log(`параграфов: ${lessons} | вопросов проверено: ${checked}` + (LEGACY ? ' | СТАРЫМ правилом' : ''));
if (problems.length) {
    console.log(`\n=== НЕ ПРОХОДЯТ (${problems.length}) ===`);
    for (const p of problems) console.log('  ✗ ' + p);
    process.exit(1);
}
console.log('\n=== всё проходит: каждый авторский ответ засчитывается своим же квизом ===');
