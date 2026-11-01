// Rodar: gjs -m tests/js/test_estados.js
import {lerResumo, separarPorEstado} from '../../extensao/recados@joaogazire/central.js';
import System from 'system';

let falhas = 0;
function igual(obtido, esperado, nome) {
    const a = JSON.stringify(obtido), b = JSON.stringify(esperado);
    if (a !== b) { falhas++; print(`FALHA ${nome}: ${a} !== ${b}`); } else print(`ok ${nome}`);
}
const notas = lerResumo(JSON.stringify([
    {id: 1, titulo: 'a', estado: 'ativa', pendentes: 2, total: 2},
    {id: 2, titulo: 'b', estado: 'concluida', pendentes: 1, total: 1},
    {id: 3, titulo: 'c', estado: 'hackeada'},
    {id: 4, titulo: 'd'},
]));
igual(notas.map(n => n.estado), ['ativa', 'concluida', 'ativa', 'ativa'], 'estado validado, padrão ativa');
const g = separarPorEstado(notas);
igual(g.ativa.map(n => n.id), [1, 3, 4], 'ativas');
igual(g.concluida.map(n => n.id), [2], 'concluídas');
igual(g.cancelada, [], 'canceladas vazia');
igual(g.arquivada, [], 'arquivadas vazia');
System.exit(falhas ? 1 : 0);
