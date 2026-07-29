/* Ищет кириллицу в СТРОКОВЫХ ЛИТЕРАЛАХ js/models.js — то, что попадает читателю на экран.
   Комментарии не считаются: код документирован по-русски, и это правильно. */
const fs = require('fs');

const src = fs.readFileSync('js/models.js', 'utf8').split('\n');
const CYR = /[А-Яа-яЁё]/;
const hits = [];

src.forEach((line, i) => {
    const code = line.replace(/\/\/.*$/, '');          // хвостовой комментарий
    if (/^\s*(\/\/|\*|\/\*)/.test(line)) return;       // строка-комментарий
    const lits = code.match(/'[^']*'|"[^"]*"/g) || [];
    lits.forEach(l => {
        if (CYR.test(l)) hits.push({ line: i + 1, lit: l });
    });
});

const byLit = {};
hits.forEach(h => (byLit[h.lit] = byLit[h.lit] || []).push(h.line));

console.log('Кириллица в литералах:', hits.length, '| разных:', Object.keys(byLit).length);
Object.keys(byLit)
    .sort((a, b) => byLit[b].length - byLit[a].length)
    .forEach(l => console.log(`  ${String(byLit[l].length).padStart(3)}  ${l}   стр. ${byLit[l].slice(0, 6).join(',')}`));
