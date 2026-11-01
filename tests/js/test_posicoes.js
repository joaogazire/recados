// Rodar: gjs -m tests/js/test_posicoes.js  (sai com código 1 se falhar)
import {idDaJanela, lerPosicoes, gravarPosicao, APP_ID} from '../../extensao/recados@joaogazire/posicoes.js';
import System from 'system';

let falhas = 0;
function igual(obtido, esperado, nome) {
    const a = JSON.stringify(obtido), b = JSON.stringify(esperado);
    if (a !== b) { falhas++; print(`FALHA ${nome}: ${a} !== ${b}`); } else print(`ok ${nome}`);
}

igual(APP_ID, 'io.github.joaowgf.Recados', 'app id');
igual(idDaJanela(APP_ID, 'Recado 12'), 12, 'id pelo título');
igual(idDaJanela(APP_ID, 'Post-it 7'), 7, 'id pelo título novo');
igual(idDaJanela('org.gnome.Nautilus', 'Recado 12'), null, 'outro app');
igual(idDaJanela(APP_ID, 'Recado'), null, 'sem número');
igual(idDaJanela(APP_ID, 'Recado 1x'), null, 'número inválido');
igual(lerPosicoes(''), {}, 'arquivo vazio');
igual(lerPosicoes('{lixo'), {}, 'json quebrado');
igual(lerPosicoes('{"3":{"x":1,"y":2},"4":{"x":"a","y":2},"5":[1]}'), {'3': {x: 1, y: 2}}, 'filtra inválidos');
igual(JSON.parse(gravarPosicao('{"3":{"x":1,"y":2}}', 7, 10, 20)), {'3': {x: 1, y: 2}, '7': {x: 10, y: 20}}, 'grava nova');
igual(JSON.parse(gravarPosicao('', 3, 5.7, -2)), {'3': {x: 6, y: -2}}, 'arredonda');

System.exit(falhas ? 1 : 0);
