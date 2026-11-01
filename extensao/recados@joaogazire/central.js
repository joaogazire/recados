// Lógica pura (sem GNOME Shell) da central de notas no painel.
const CORES = ['amarelo', 'azul', 'verde', 'rosa', 'roxo', 'cinza'];
const MAX_TITULO = 60;
const MAX_NOTAS = 200;

function contagem(v) {
    return Number.isInteger(v) && v >= 0 ? v : 0;
}

export function lerResumo(texto) {
    let dados;
    try {
        dados = JSON.parse(texto);
    } catch {
        return [];
    }
    if (!Array.isArray(dados))
        return [];
    return dados.slice(0, MAX_NOTAS)
        .filter(n => n && typeof n === 'object' && Number.isInteger(n.id) && n.id > 0)
        .map(n => {
            let titulo = typeof n.titulo === 'string' && n.titulo.trim() ? n.titulo.trim() : '(vazia)';
            if (titulo.length > MAX_TITULO)
                titulo = `${titulo.slice(0, MAX_TITULO - 1)}…`;
            return {
                id: n.id,
                titulo,
                cor: CORES.includes(n.cor) ? n.cor : 'amarelo',
                pendentes: contagem(n.pendentes),
                total: contagem(n.total),
            };
        });
}

export function rotuloPainel(notas) {
    const soma = notas.reduce((acc, n) => acc + (n.pendentes || 0), 0);
    return soma ? String(soma) : '';
}
