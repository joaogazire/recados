// Rodar: gjs -m tests/js/test_projetos.js
import {lerResumo, agruparPorProjeto} from '../../extensao/recados@joaogazire/central.js';
import System from 'system';

let falhas = 0;
function igual(obtido, esperado, nome) {
    const a = JSON.stringify(obtido), b = JSON.stringify(esperado);
    if (a !== b) { falhas++; print(`FALHA ${nome}: ${a} !== ${b}`); } else print(`ok ${nome}`);
}
const notas = lerResumo(JSON.stringify([
    {id: 1, titulo: 'a', projeto: 'Steamlog', pendentes: 2, total: 3},
    {id: 2, titulo: 'b', projeto: 'Inbox', pendentes: 1, total: 1},
    {id: 3, titulo: 'c', projeto: 'Estante', pendentes: 0, total: 0},
    {id: 4, titulo: 'd', projeto: 'Steamlog', pendentes: 1, total: 1},
    {id: 5, titulo: 'e'},
    {id: 6, titulo: 'f', projeto: 42},
    {id: 7, titulo: 'g', projeto: 'x'.repeat(100)},
]));
igual(notas.map(n => n.projeto.length), [8, 5, 7, 8, 5, 5, 60], 'projeto validado, padrão Inbox, limite 60');
const g = agruparPorProjeto(notas.slice(0, 6));
igual(g.map(p => p.projeto), ['Estante', 'Steamlog', 'Inbox'], 'ordem alfabética, Inbox por último');
igual(g.map(p => p.notas.map(n => n.id)), [[3], [1, 4], [2, 5, 6]], 'notas dentro de cada projeto');
igual(g.map(p => p.pendentes), [0, 3, 1], 'pendentes somados por projeto');
System.exit(falhas ? 1 : 0);
