// Rodar: gjs -m tests/js/test_busca.js
import {buscar, lerResumo} from '../../extensao/recados@joaogazire/central.js';
import System from 'system';

let falhas = 0;
function igual(obtido, esperado, nome) {
    const a = JSON.stringify(obtido), b = JSON.stringify(esperado);
    if (a !== b) { falhas++; print(`FALHA ${nome}: ${a} !== ${b}`); } else print(`ok ${nome}`);
}
const notas = lerResumo(JSON.stringify([
    {id: 1, titulo: 'Mercado', cor: 'azul', pendentes: 1, total: 2, texto: '# Mercado\n- [ ] Pão francês\n- [x] leite'},
    {id: 2, titulo: 'Dentista', cor: 'rosa', pendentes: 0, total: 0, texto: 'Ligar pro dentista às 15h'},
]));
igual(notas[0].texto.includes('Pão'), true, 'texto passa pela validação');
igual(buscar(notas, '').map(n => n.id), [1, 2], 'vazio mostra tudo');
igual(buscar(notas, 'pao').map(n => n.id), [1], 'sem acento e sem caixa');
igual(buscar(notas, 'DENTISTA')[0].trecho, 'Ligar pro dentista às 15h', 'trecho da linha');
igual(buscar(notas, 'xyz'), [], 'nada');
igual(lerResumo('[{"id":1,"titulo":"a","texto":5}]')[0].texto, '', 'texto inválido vira vazio');
System.exit(falhas ? 1 : 0);
