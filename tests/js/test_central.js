// Rodar: gjs -m tests/js/test_central.js
import {lerResumo} from '../../extensao/recados@joaogazire/central.js';
import System from 'system';

let falhas = 0;
function igual(obtido, esperado, nome) {
    const a = JSON.stringify(obtido), b = JSON.stringify(esperado);
    if (a !== b) { falhas++; print(`FALHA ${nome}: ${a} !== ${b}`); } else print(`ok ${nome}`);
}

igual(lerResumo('{lixo'), [], 'json quebrado');
igual(lerResumo('{"a":1}'), [], 'não é lista');
igual(lerResumo('[{"id":2,"titulo":"Oi","cor":"azul","pendentes":1,"total":2},{"id":"x"},{"id":3,"titulo":5,"cor":"<b>","pendentes":0,"total":0}]'),
    [{id: 2, titulo: 'Oi', cor: 'azul', pendentes: 1, total: 2, texto: '', estado: 'ativa', lembretes: []}, {id: 3, titulo: '(vazia)', cor: 'amarelo', pendentes: 0, total: 0, texto: '', estado: 'ativa', lembretes: []}],
    'filtra e normaliza');
igual(lerResumo(JSON.stringify([{id: 1, titulo: 'a'.repeat(200), cor: 'rosa', pendentes: 0, total: 0}]))[0].titulo.length <= 60, true, 'corta título');
System.exit(falhas ? 1 : 0);
