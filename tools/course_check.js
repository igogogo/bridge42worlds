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
// ссылки открывались как 404 — при полностью зелёной проверке. Правду читаем из соседнего
// рабочего дерева сайта; нет его рядом — молча пропускаем, это не ошибка курса.
const SITE = path.resolve(ROOT, '..', 'bridge42worlds').replace(/\\/g, '/');
// Одного графа знаний мало: у Фарадея и Бора страницы на сайте есть, а узлов в графе нет —
// проверка по графу ругалась бы на живые ссылки, и на таком шуме её перестают читать. Каталог
// страниц берём с диска, граф оставляем вторым источником. Каталоги языков совпадают
// (разница ru и en — служебный audit.html), поэтому хватает одного, русского.
let KNOWN = null;
if (fs.existsSync(SITE)) {
    KNOWN = { tag: new Set(), law: new Set(), sci: new Set() };
    [['law', 'laws'], ['tag', 'tags'], ['sci', 'scientists']].forEach(([kind, dir]) => {
        const d = SITE + '/lang/ru/' + dir;
        if (!fs.existsSync(d)) return;
        fs.readdirSync(d).forEach(n => { if (n.endsWith('.html')) KNOWN[kind].add(n.slice(0, -5)); });
    });
    try {
        const g = JSON.parse(fs.readFileSync(SITE + '/data/knowledge-graph.json', 'utf8'));
        (g.nodes || []).forEach(n => {
            const i = String(n.id).indexOf(':');
            // Учёные в графе записаны через пробел («sci:Isaac Newton»), а файл страницы —
            // через подчёркивание. Приводим к виду адреса, иначе граф добавляет двести имён,
            // которые ни с чем не совпадут, и мёртвая ссылка проходит незамеченной.
            if (i > 0 && KNOWN[n.kind]) KNOWN[n.kind].add(String(n.id).slice(i + 1).replace(/\s+/g, '_'));
        });
    } catch (e) { /* графа рядом нет — хватит каталога страниц */ }
    if (!KNOWN.tag.size && !KNOWN.law.size && !KNOWN.sci.size) KNOWN = null;
}

// Записи связей приходят в двух видах: голым id (entities урока и обзора) и объектом
// {id, name, note} (библиотека методички). Разбирать это в каждом вызывающем — плодить
// расхождения, поэтому нормализуем в одном месте.
function entId(v) { return (v && typeof v === 'object') ? v.id : v; }

// Учёного адресуют по-разному в разных местах страницы, и проверка обязана повторять именно
// то, что делает course.html: в связях урока и обзора он меняет пробелы на подчёркивания
// («Isaac Newton» → Isaac_Newton.html), а в библиотеке методички подставляет id как есть.
// Без этого различия проверка либо ругается на живую ссылку, либо пропускает мёртвую.
function checkEntities(where, ent, asIs) {
    if (!ent) return;
    [['tags', 'tag', 'тег'], ['laws', 'law', 'закон'], ['scientists', 'sci', 'учёный']]
        .forEach(([field, kind, word]) => {
            (ent[field] || []).forEach(v => {
                const id = entId(v);
                if (typeof id !== 'string' || !id) {
                    bad.push(`${where}: запись в «${field}» без id — ссылку собрать не из чего`);
                    return;
                }
                const url = asIs ? id : id.replace(/\s+/g, '_');
                if (!KNOWN || KNOWN[kind].has(url)) return;
                if (asIs && KNOWN[kind].has(id.replace(/\s+/g, '_'))) {
                    bad.push(`${where}: ${word} «${id}» — пробел в id, а методичка подставляет id ` +
                             `в адрес как есть; нужно «${id.replace(/\s+/g, '_')}»`);
                } else {
                    bad.push(`${where}: ${word} «${id}» — на сайте такой страницы нет, ссылка даст 404`);
                }
            });
        });
    checkArticles(where, ent.examples_from_articles);
}

// «Статьи по теме» — единственное место, где из урока видно живую науку, а не учебник.
// Страница собирает адрес как /lang/ЯЗЫК/archive/ДАТА/ID/ и берёт подпись из title, поэтому
// запись без даты она молча пропускает, а без заголовка показывает голый номер препринта.
// Двенадцать параграфов держали по три записи с одними id и why — блок не выводился ВООБЩЕ,
// и проверка при этом была зелёной: она в entities не заглядывала.
function checkArticles(where, arts) {
    (arts || []).forEach(a => {
        const id = (a && a.id) || '?';
        if (!a || !a.date) { bad.push(`${where}: статья «${id}» без date — блок «Статьи по теме» её не покажет`); return; }
        if (!a.title) { bad.push(`${where}: статья «${id}» без title — в списке будет номер препринта вместо названия`); }
        // Дата тут не украшение, а часть адреса: ошиблись днём — ссылка 404, хотя статья есть.
        if (KNOWN && !fs.existsSync(SITE + '/lang/ru/archive/' + a.date + '/' + id + '/index.html')) {
            bad.push(`${where}: статьи ${id} за ${a.date} нет в архиве сайта — ссылка даст 404`);
        }
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
const LANGS = ['en', 'es', 'ar', 'fr'];
const stats = [];

// Методичка темы (guide.json) до сих пор не проверялась вообще, хотя ссылок в ней больше,
// чем в самом уроке: библиотека «материалы по теме» лежит ОТДЕЛЬНО в каждой языковой ветке.
// Отсюда болезнь, которую видно только у читателя: русский список законов починили, а в
// en/es/ar остались прежние мёртвые id — на трёх языках из четырёх страница ведёт в 404.
// Поэтому идём по всем веткам, а не по одной русской, и сверяем набор с русским: расхождение
// набора значит, что перевод отстал от правки, даже если каждая ссылка сама по себе живая.
function checkGuide(tid, dir) {
    const f = dir + '/guide.json';
    if (!fs.existsSync(f)) { warn.push(`${tid}: нет методички guide.json`); return; }
    const G = readJSON(f); if (!G) return;
    const ruLib = (G.ru || {}).library;
    if (!ruLib) { warn.push(`${tid}/guide: нет раздела «материалы по теме»`); return; }
    checkEntities(`${tid}/guide [ru]`, ruLib, true);
    LANGS.forEach(lang => {
        const b = G[lang];
        if (!b || typeof b !== 'object') return;      // ветки нет — обычный пробел перевода, его ловит перевод
        const lib = b.library;
        if (!lib) { warn.push(`${tid}/guide [${lang}]: нет раздела «материалы по теме», а по-русски он есть`); return; }
        checkEntities(`${tid}/guide [${lang}]`, lib, true);
        ['laws', 'scientists', 'tags'].forEach(field => {
            const r = (ruLib[field] || []).map(entId).join(', ');
            const t = (lib[field] || []).map(entId).join(', ');
            if (r !== t) warn.push(`${tid}/guide [${lang}]: «${field}» ведут не туда, куда русские — ` +
                                   `[${t}] против [${r}]`);
        });
    });
}

topicsInTree.forEach(tid => {
    const dir = C + '/' + tid;
    if (!fs.existsSync(dir)) { if (tree.topics.find(t => t.id === tid).status !== 'planned') bad.push(`тема ${tid} помечена готовой, но папки нет`); return; }
    const course = readJSON(dir + '/course.json');
    if (!course) return;
    // Обзор темы даёт те же ссылки, что и параграф, — и той же строкой кода на странице.
    // Проверяли только параграфы, поэтому в обзорах спокойно жили id, которых на сайте нет
    // никогда не было: newtons_laws_of_motion вместо трёх отдельных законов Ньютона.
    checkEntities(`${tid}/обзор`, course.entities);
    checkGuide(tid, dir);
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
