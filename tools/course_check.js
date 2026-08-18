// Сквозная проверка целостности курса: JSON, ссылки, модели, фигуры, схема параграфа.
const fs = require('fs'), path = require('path');
// Корень берём от самого скрипта. Раньше здесь стоял абсолютный путь к одному рабочему дереву,
// и проверка, запущенная из ветки, молча читала ЧУЖИЕ файлы: «0 ошибок» относилось не к тому,
// что правишь. Ошибка тихая и потому опасная — отчёт выглядел зелёным.
const ROOT = path.resolve(__dirname, '..').replace(/\\/g, '/');
const C = ROOT + '/data/theory/courses';
const bad = [], warn = [];

function readJSON(p) {
    try { return JSON.parse(fs.readFileSync(p, 'utf8')); }
    catch (e) { bad.push('НЕВАЛИДНЫЙ JSON: ' + p.replace(ROOT, '') + ' — ' + e.message); return null; }
}

// какие фигуры и модели вообще существуют
const figSrc = fs.readFileSync(ROOT + '/js/figures.js', 'utf8');
const FIGS = new Set([...figSrc.matchAll(/F\.([a-zA-Z][a-zA-Z0-9]*)\s*=\s*function/g)].map(m => m[1]));
const modSrc = fs.readFileSync(ROOT + '/js/models.js', 'utf8');
const MODELS = new Set([...modSrc.matchAll(/(\w+):\s*\w+Model[,\s}]/g)].map(m => m[1]));
const courseSrc = fs.readFileSync(ROOT + '/course.html', 'utf8');
const FACTORY = new Set([...courseSrc.matchAll(/(\w+):\s*'(\w+)'/g)].filter(m => MODELS.has(m[2])).map(m => m[1]));

// Связи урока ведут на страницы сайта. Проверяем, что такие страницы вообще есть:
// урок про гидростатику ссылался на Паскаля и Торричелли, которых в базе нет, и обе
// ссылки открывались как 404 — при полностью зелёной проверке. Граф читаем из соседнего
// рабочего дерева сайта; нет его рядом — молча пропускаем, это не ошибка курса.
const GRAPH = path.resolve(ROOT, '..', 'bridge42worlds', 'data', 'knowledge-graph.json');
let KNOWN = null;
if (fs.existsSync(GRAPH)) {
    try {
        const g = JSON.parse(fs.readFileSync(GRAPH, 'utf8'));
        KNOWN = { tag: new Set(), law: new Set(), sci: new Set() };
        (g.nodes || []).forEach(n => {
            const i = String(n.id).indexOf(':');
            if (i > 0 && KNOWN[n.kind]) KNOWN[n.kind].add(String(n.id).slice(i + 1));
        });
    } catch (e) { KNOWN = null; }
}
function checkEntities(where, ent) {
    if (!KNOWN || !ent) return;
    [['tags', 'tag', 'тег'], ['laws', 'law', 'закон'], ['scientists', 'sci', 'учёный']]
        .forEach(([field, kind, word]) => {
            (ent[field] || []).forEach(id => {
                if (!KNOWN[kind].has(id)) {
                    bad.push(`${where}: ${word} «${id}» — на сайте такой страницы нет, ссылка даст 404`);
                }
            });
        });
}

const tree = readJSON(C + '/index.json');
const topicsInTree = tree.topics.map(t => t.id);

// нити должны ссылаться на существующие темы
tree.ru.threads.forEach(th => th.path.forEach(id => {
    if (!topicsInTree.includes(id)) bad.push(`нить «${th.name}» ссылается на несуществующую тему: ${id}`);
}));
tree.topics.forEach(t => (t.needs || []).concat(t.feeds || []).forEach(id => {
    if (!topicsInTree.includes(id)) bad.push(`тема ${t.id}: связь на несуществующую тему ${id}`);
}));

const REQUIRED = ['title', 'subtitle', 'intro', 'standNote', 'formula', 'derivation', 'math', 'example', 'constants', 'memo', 'quiz'];
const stats = [];

topicsInTree.forEach(tid => {
    const dir = C + '/' + tid;
    if (!fs.existsSync(dir)) { if (tree.topics.find(t => t.id === tid).status !== 'planned') bad.push(`тема ${tid} помечена готовой, но папки нет`); return; }
    const course = readJSON(dir + '/course.json');
    if (!course) return;
    let lessonCount = 0;
    (course.lessons || []).forEach(l => {
        const f = dir + '/' + l.id + '.json';
        if (!fs.existsSync(f)) { bad.push(`${tid}: обзор ссылается на ${l.id}, файла нет`); return; }
        lessonCount++;
        const L = readJSON(f); if (!L) return;
        const ru = L.ru || {};
        REQUIRED.forEach(k => { if (!ru[k]) warn.push(`${tid}/${l.id}: нет блока «${k}»`); });
        checkEntities(`${tid}/${l.id}`, L.entities);
        if (L.model && !FACTORY.has(L.model)) bad.push(`${tid}/${l.id}: модель «${L.model}» не зарегистрирована в course.html`);
        if (L.model && !fs.existsSync(ROOT + '/data/theory/' + L.model + '.json')) bad.push(`${tid}/${l.id}: нет данных модели ${L.model}.json`);
        (ru.derivation && ru.derivation.steps || []).forEach((s, i) => {
            if (s.figure && !FIGS.has(s.figure)) bad.push(`${tid}/${l.id}: шаг ${i + 1} — схемы «${s.figure}» нет в figures.js`);
            if (!s.figure) warn.push(`${tid}/${l.id}: шаг ${i + 1} без схемы`);
        });
        // Достроили вывод по-русски, перевод остался прежним — и проверка молчала: она смотрит
        // только в L.ru. Пробел перевода конвейер видит по отсутствию ключа или по кириллице,
        // а здесь ключ на месте и кириллицы нет — читатель на другом языке просто получает
        // старый, более короткий вывод. Сравниваем длину списка шагов.
        if (ru.derivation && ru.derivation.steps) {
            ['en', 'es', 'ar', 'fr'].forEach(lang => {
                const d = L[lang] && L[lang].derivation;
                if (!d || !d.steps) return;                       // блока нет — это обычный пробел перевода
                if (d.steps.length !== ru.derivation.steps.length) {
                    warn.push(`${tid}/${l.id}: вывод [${lang}] отстал от русского — ` +
                              `${d.steps.length} шагов против ${ru.derivation.steps.length}`);
                }
            });
        }
        (ru.quiz || []).forEach((q, i) => {
            if (q.type === 'mcq' && typeof q.answer !== 'number') bad.push(`${tid}/${l.id}: вопрос ${i + 1} mcq без числового answer`);
            if (q.type === 'mcq' && q.options && (q.answer < 0 || q.answer >= q.options.length)) bad.push(`${tid}/${l.id}: вопрос ${i + 1} answer вне диапазона`);
            if (q.type === 'free' && !q.keywords) bad.push(`${tid}/${l.id}: вопрос ${i + 1} free без keywords`);
            if (q.type === 'estimate' && typeof q.answer !== 'number') bad.push(`${tid}/${l.id}: вопрос ${i + 1} estimate без числа`);
            if (!q.why) warn.push(`${tid}/${l.id}: вопрос ${i + 1} без разбора`);
        });
        if (ru.constants && !ru.constants.items) bad.push(`${tid}/${l.id}: constants не в формате {title, items}`);
        if (ru.example && !ru.example.solution) bad.push(`${tid}/${l.id}: example без solution[]`);
    });
    const st = tree.topics.find(t => t.id === tid).status;
    stats.push({ topic: tid, lessons: lessonCount, declared: (course.lessons || []).length, status: st });
    if (st === 'ready' && lessonCount < (course.lessons || []).length) bad.push(`${tid}: статус ready, но параграфов ${lessonCount}/${course.lessons.length}`);
});

console.log('=== СОСТОЯНИЕ ===');
stats.forEach(s => console.log(`  ${s.topic.padEnd(16)} ${s.lessons}/${s.declared}  [${s.status}]`));
console.log('\n=== ОШИБКИ (' + bad.length + ') ===');
bad.forEach(b => console.log('  ✗ ' + b));
console.log('\n=== ЗАМЕЧАНИЯ (' + warn.length + ') ===');
warn.slice(0, 30).forEach(w => console.log('  · ' + w));
if (warn.length > 30) console.log('  … ещё ' + (warn.length - 30));
