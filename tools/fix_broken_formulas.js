/* Чинит формулы, которые читатель видит сырыми.
 *
 * Две поломки, найденные проверкой курса на телефоне:
 *   1) подпись обрезана посреди формулы — остаётся непарный `$`, и авто-набор KaTeX
 *      такой кусок не трогает: на экране висит «$v_{\text{II}}»;
 *   2) задвоенные слэши (`\\mathcal` вместо `\mathcal`) — формула не собирается вовсе.
 *
 * Правим только строки ВНЕ полей-формул (latex/eq/plate): там LaTeX уместен и парность
 * долларов не требуется.
 *
 *   node tools/fix_broken_formulas.js --dry    показать, что изменится
 *   node tools/fix_broken_formulas.js          записать
 */
const fs = require('fs');
const path = require('path');

const ROOT = 'data/theory/courses';
const DRY = process.argv.includes('--dry');
const FORMULA_FIELD = /(^|\.)(latex|eq|plate)($|\[)/;

function balanced(s) { return s.split('$').length % 2 === 1; }

/** Обрезает хвост с непарным `$` и подчищает повисшую пунктуацию. */
function dropDanglingMath(s) {
    if (balanced(s)) return s;
    const parts = s.split('$');
    return parts.slice(0, parts.length - 1).join('$').replace(/[\s,;:،·—-]+$/, '');
}

/* Усечение, которое НЕ рвёт формулу: режем только по пробелу ВНЕ `$…$`.
   Если до предела такой точки нет (текст начинается с длинной формулы) — берём ближайшую
   ПОСЛЕ предела: лучше подпись чуть длиннее, чем пустая или с оборванной формулой. */
function safeTruncate(s, max) {
    if (s.length <= max) return s;
    const stops = [];
    let inMath = false;
    for (let i = 0; i < s.length; i++) {
        if (s[i] === '$') inMath = !inMath;
        else if (s[i] === ' ' && !inMath) stops.push(i);
    }
    const before = stops.filter(i => i <= max).pop();
    const after = stops.find(i => i > max);
    const cut = before != null && before > 10 ? before : (after != null ? after : s.length);
    return dropDanglingMath(s.slice(0, cut)).replace(/[\s,;:،·—-]+$/, '');
}

function fixString(s) {
    let out = s;
    if (/\\\\[a-zA-Z]/.test(out)) out = out.replace(/\\\\/g, '\\');   // задвоенные слэши
    return dropDanglingMath(out);
}

let changed = 0;
const log = [];

function walk(o, p, file, lang) {
    if (o && typeof o === 'object') {
        // Подпись карточки — усечённый её же текст, и рвётся она посреди формулы.
        // Пересобираем из текста по-человечески, а не отрезаем «как есть».
        if (!Array.isArray(o) && typeof o.title === 'string' && typeof o.text === 'string'
            && !balanced(o.title)) {
            const rebuilt = safeTruncate(o.text, Math.max(24, o.title.length));
            if (rebuilt && rebuilt !== o.title) {
                changed++;
                log.push('  ' + file + ' [' + lang + '] ' + p + '.title' +
                         '\n      было:  ' + o.title.slice(0, 100) +
                         '\n      стало: ' + rebuilt.slice(0, 100));
                o.title = rebuilt;
            }
        }
        const keys = Array.isArray(o) ? o.map((_, i) => i) : Object.keys(o);
        for (const k of keys) {
            const child = o[k];
            const cp = p + (Array.isArray(o) ? '[' + k + ']' : '.' + k);
            if (typeof child === 'string') {
                if (FORMULA_FIELD.test(cp)) continue;
                const fixed = fixString(child);
                if (fixed !== child) {
                    changed++;
                    log.push('  ' + file + ' [' + lang + '] ' + cp +
                             '\n      было:  ' + child.slice(0, 100) +
                             '\n      стало: ' + fixed.slice(0, 100));
                    o[k] = fixed;
                }
            } else {
                walk(child, cp, file, lang);
            }
        }
    }
}

for (const topic of fs.readdirSync(ROOT)) {
    const d = path.join(ROOT, topic);
    if (!fs.statSync(d).isDirectory()) continue;
    for (const f of fs.readdirSync(d)) {
        if (!f.endsWith('.json')) continue;
        const file = path.join(d, f);
        const j = JSON.parse(fs.readFileSync(file, 'utf8'));
        const before = JSON.stringify(j);
        for (const L of ['ru', 'en', 'es', 'ar']) if (j[L]) walk(j[L], '', topic + '/' + f, L);
        if (!DRY && JSON.stringify(j) !== before) {
            fs.writeFileSync(file, JSON.stringify(j, null, 2) + '\n', 'utf8');
        }
    }
}

console.log(log.join('\n'));
console.log((DRY ? 'НАШЛОСЬ' : 'ИСПРАВЛЕНО') + ': ' + changed);
