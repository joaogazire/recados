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


// --- Ícone de pilha: a altura da pilha é relativa ao quanto você costuma ter pendente ---
const DIAS = 14;
const HABITUAL_MIN = 4;
const MAX_FOLHAS = 4;

function lerHistorico(texto) {
    let d;
    try {
        d = JSON.parse(texto);
    } catch {
        return {};
    }
    if (!d || typeof d !== 'object' || Array.isArray(d))
        return {};
    const saida = {};
    for (const [dia, v] of Object.entries(d)) {
        if (/^\d{4}-\d{2}-\d{2}$/.test(dia) && Number.isInteger(v) && v >= 0)
            saida[dia] = v;
    }
    return saida;
}

export function registrarAmostra(texto, dia, pendentes) {
    const h = lerHistorico(texto);
    h[dia] = Math.max(h[dia] ?? 0, pendentes);
    const dias = Object.keys(h).sort().slice(-DIAS);
    return JSON.stringify(Object.fromEntries(dias.map(d => [d, h[d]])));
}

export function habitual(texto) {
    const v = Object.values(lerHistorico(texto));
    if (!v.length)
        return HABITUAL_MIN;
    return Math.max(HABITUAL_MIN, Math.round(v.reduce((a, b) => a + b, 0) / v.length));
}

export function folhas(pendentes, habitualAtual) {
    if (pendentes <= 0)
        return {n: 1, feito: true};
    const n = Math.ceil((pendentes / Math.max(1, habitualAtual)) * MAX_FOLHAS);
    return {n: Math.min(MAX_FOLHAS, Math.max(1, n)), feito: false};
}
