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
 * У вопросов с выбором — что индекс верного ответа существует и вариантов не меньше двух.
 * У свободных — что ключевые слова заданы (иначе засчитывается любой текст).
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

for (const topic of fs.readdirSync(ROOT).sort()) {
    const dir = path.join(ROOT, topic);
    if (!fs.statSync(dir).isDirectory()) continue;
    for (const name of fs.readdirSync(dir).sort()) {
        if (!/^\d/.test(name) || !name.endsWith('.json')) continue;
        const data = JSON.parse(fs.readFileSync(path.join(dir, name), 'utf8'));
        lessons++;
        for (const lang of LANGS) {
            const quiz = (data[lang] || {}).quiz;
            if (!quiz) continue;
            for (const q of quiz) {
                const where = `${topic}/${data.id} [${lang}] ${q.id}`;
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
