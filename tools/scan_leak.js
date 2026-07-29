/* Опись утечки русского в переводы курса.
 * Делит находки на три вида, потому что чинятся они по-разному:
 *   1) внутри формул — короткие слова в \text{…}: нужен словарь подстрочников;
 *   2) названия законов на обзорных страницах (course.json → lessons[].law);
 *   3) прочий живой текст.
 *   node tools/scan_leak.js            сводка
 *   node tools/scan_leak.js --full     все места
 */
const fs = require('fs');
const path = require('path');
const ROOT = 'data/theory/courses';
const FULL = process.argv.includes('--full');
const CYR = /[А-Яа-яЁё]/;

const inFormula = {}, lawRows = [], proseRows = [];

function isFormulaField(p) { return /(^|\.)(latex|eq|plate)($|\[)/.test(p); }

function walk(o, p, file, lang) {
    if (typeof o === 'string') {
        if (!CYR.test(o)) return;
        if (isFormulaField(p)) {
            // собираем именно содержимое \text{…}, остальное в формулах кириллицей не бывает
            const m = o.match(/\\text\{([^}]*)\}/g) || [];
            m.forEach(t => {
                const w = t.replace(/\\text\{|\}/g, '');
                if (CYR.test(w)) (inFormula[w] = inFormula[w] || []).push(file + ' [' + lang + '] ' + p);
            });
            return;
        }
        if (/\.law$/.test(p)) lawRows.push({ file, lang, p, text: o });
        else proseRows.push({ file, lang, p, text: o });
        return;
    }
    if (Array.isArray(o)) return o.forEach((v, i) => walk(v, p + '[' + i + ']', file, lang));
    if (o && typeof o === 'object') return Object.keys(o).forEach(k => walk(o[k], p + '.' + k, file, lang));
}

for (const topic of fs.readdirSync(ROOT)) {
    const d = path.join(ROOT, topic);
    if (!fs.statSync(d).isDirectory()) continue;
    for (const f of fs.readdirSync(d)) {
        if (!f.endsWith('.json')) continue;
        const j = JSON.parse(fs.readFileSync(path.join(d, f), 'utf8'));
        for (const L of ['en', 'es', 'ar']) if (j[L]) walk(j[L], '', topic + '/' + f, L);
    }
}

console.log('=== 1. Русские слова внутри формул (\\text{…}) ===');
const words = Object.keys(inFormula).sort((a, b) => inFormula[b].length - inFormula[a].length);
words.forEach(w => console.log('  ' + String(inFormula[w].length).padStart(4) + '  «' + w + '»'));
console.log('  итого вхождений:', words.reduce((s, w) => s + inFormula[w].length, 0), '| разных слов:', words.length);

console.log('=== 2. Названия законов (…law) ===', lawRows.length);
const laws = {};
lawRows.forEach(r => (laws[r.text] = laws[r.text] || []).push(r.file + ' [' + r.lang + ']'));
Object.keys(laws).forEach(t => console.log('  ' + String(laws[t].length).padStart(3) + '  ' + t.slice(0, 80)));

console.log('=== 3. Прочий текст ===', proseRows.length);
(FULL ? proseRows : proseRows.slice(0, 20)).forEach(r =>
    console.log('  ' + r.file + ' [' + r.lang + '] ' + r.p + ' :: ' + r.text.slice(0, 80)));
