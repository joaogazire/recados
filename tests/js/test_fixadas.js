// Rodar: gjs -m tests/js/test_fixadas.js
import {lerFixadas} from '../../extensao/recados@joaogazire/posicoes.js';
import System from 'system';

let falhas = 0;
function igual(obtido, esperado, nome) {
    const a = JSON.stringify(obtido), b = JSON.stringify(esperado);
    if (a !== b) { falhas++; print(`FALHA ${nome}: ${a} !== ${b}`); } else print(`ok ${nome}`);
}
igual(lerFixadas('[3, 7]'), [3, 7], 'lista de ids');
igual(lerFixadas('[3, "x", -1, 2.5, 9]'), [3, 9], 'filtra inválidos');
igual(lerFixadas('{lixo'), [], 'quebrado');
igual(lerFixadas('{"a":1}'), [], 'não é lista');
System.exit(falhas ? 1 : 0);
