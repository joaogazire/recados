// Rodar: gjs -m tests/js/test_pilha.js
import {folhas, habitual, registrarAmostra} from '../../extensao/recados@joaogazire/central.js';
import System from 'system';

let falhas = 0;
function igual(obtido, esperado, nome) {
    const a = JSON.stringify(obtido), b = JSON.stringify(esperado);
    if (a !== b) { falhas++; print(`FALHA ${nome}: ${a} !== ${b}`); } else print(`ok ${nome}`);
}

// histórico: maior número de pendentes de cada dia, só os últimos 14 dias
let h = registrarAmostra('', '2026-11-01', 5);
h = registrarAmostra(h, '2026-11-01', 3);
igual(JSON.parse(h), {'2026-11-01': 5}, 'guarda o maior do dia');
h = registrarAmostra(h, '2026-11-02', 9);
igual(habitual(h), 7, 'média dos dias');
let longo = '';
for (let d = 1; d <= 20; d++) longo = registrarAmostra(longo, `2026-10-${String(d).padStart(2, '0')}`, d);
igual(Object.keys(JSON.parse(longo)).length, 14, 'guarda só 14 dias');
igual(registrarAmostra('{lixo', '2026-11-01', 2), '{"2026-11-01":2}', 'arquivo quebrado recomeça');
igual(habitual(''), 4, 'sem histórico: 4');
igual(habitual('{"2026-11-01":1}'), 4, 'mínimo 4');

// folhas: 0 pendentes = 1 folha com ✓; o habitual enche a pilha (4 folhas)
igual(folhas(0, 8), {n: 1, feito: true}, 'nada pendente');
igual(folhas(1, 8), {n: 1, feito: false}, 'pouco');
igual(folhas(4, 8), {n: 2, feito: false}, 'metade do habitual');
igual(folhas(8, 8), {n: 4, feito: false}, 'o habitual');
igual(folhas(30, 8), {n: 4, feito: false}, 'acima do habitual não passa de 4');
igual(folhas(8, 40), {n: 1, feito: false}, 'escala com o habitual');
System.exit(falhas ? 1 : 0);
