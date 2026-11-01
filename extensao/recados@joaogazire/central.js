// Lógica pura (sem GNOME Shell) da central de notas no painel.
const ESTADOS = ['ativa', 'concluida', 'cancelada', 'arquivada'];
const CORES = ['amarelo', 'azul', 'verde', 'rosa', 'roxo', 'cinza'];
const MAX_TITULO = 60;
const MAX_NOTAS = 200;
const MAX_TEXTO = 2000;
const MAX_TRECHO = 80;

function contagem(v) {
    return Number.isInteger(v) && v >= 0 ? v : 0;
}

function lerLembretes(v) {
    if (!Array.isArray(v))
        return [];
    return v.slice(0, 20).filter(l => l && typeof l === 'object' && typeof l.quando === 'string' &&
        Number.isFinite(Date.parse(l.quando)) && typeof l.titulo === 'string')
        .map(l => ({quando: Date.parse(l.quando), titulo: l.titulo.slice(0, MAX_TITULO), feito: l.feito === true}));
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
                texto: typeof n.texto === 'string' ? n.texto.slice(0, MAX_TEXTO) : '',
                estado: ESTADOS.includes(n.estado) ? n.estado : 'ativa',
                lembretes: lerLembretes(n.lembretes),
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

// --- Busca na central: sem acento e sem diferença de maiúsculas ---
function normalizar(s) {
    return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

export function buscar(notas, termo) {
    const t = normalizar(termo.trim());
    if (!t)
        return notas.map(n => ({...n, trecho: ''}));
    const saida = [];
    for (const n of notas) {
        const linha = n.texto.split('\n').find(l => normalizar(l).includes(t));
        if (linha === undefined && !normalizar(n.titulo).includes(t))
            continue;
        let trecho = (linha ?? '').replace(/^\s*(#{1,6} |[-*+] (\[[ xX]\] ?)?)/, '').trim();
        if (trecho.length > MAX_TRECHO)
            trecho = `${trecho.slice(0, MAX_TRECHO - 1)}…`;
        saida.push({...n, trecho});
    }
    return saida;
}

export function separarPorEstado(notas) {
    const g = Object.fromEntries(ESTADOS.map(e => [e, []]));
    for (const n of notas)
        g[n.estado].push(n);
    return g;
}

// --- Lembretes na central: vencidos (não feitos, já passou) e próximos 7 dias ---
const SEMANA_MS = 7 * 24 * 3600 * 1000;

export function agendaDaCentral(notas, agoraMs) {
    const vencidos = [], proximos = [];
    for (const n of notas) {
        if (n.estado !== 'ativa')
            continue;
        for (const l of n.lembretes) {
            if (l.feito)
                continue;
            const item = {id: n.id, titulo: l.titulo, quando: l.quando};
            if (l.quando <= agoraMs)
                vencidos.push(item);
            else if (l.quando <= agoraMs + SEMANA_MS)
                proximos.push(item);
        }
    }
    const ordem = (a, b) => a.quando - b.quando;
    return {vencidos: vencidos.sort(ordem), proximos: proximos.sort(ordem)};
}
