// Rodar: gjs -m tests/js/test_agenda.js
import {lerResumo, agendaDaCentral} from '../../extensao/recados@joaogazire/central.js';
import System from 'system';

let falhas = 0;
function igual(obtido, esperado, nome) {
    const a = JSON.stringify(obtido), b = JSON.stringify(esperado);
    if (a !== b) { falhas++; print(`FALHA ${nome}: ${a} !== ${b}`); } else print(`ok ${nome}`);
}
const agora = Date.parse('2026-11-01T15:00:00');
const notas = lerResumo(JSON.stringify([
    {id: 1, titulo: 'a', lembretes: [
        {quando: '2026-11-01T14:00:00', titulo: 'vencido', feito: false},
        {quando: '2026-11-01T13:00:00', titulo: 'feito', feito: true},
        {quando: '2026-11-03T09:00:00', titulo: 'logo', feito: false},
        {quando: '2026-12-25T09:00:00', titulo: 'longe', feito: false},
        {quando: 'lixo', titulo: 'x', feito: false},
    ]},
    {id: 2, titulo: 'b', estado: 'arquivada', lembretes: [{quando: '2026-11-02T09:00:00', titulo: 'arq', feito: false}]},
]));
const g = agendaDaCentral(notas, agora);
igual(g.vencidos.map(l => [l.id, l.titulo]), [[1, 'vencido']], 'vencidos');
igual(g.proximos.map(l => l.titulo), ['logo'], 'próximos 7 dias, só ativas');
System.exit(falhas ? 1 : 0);
