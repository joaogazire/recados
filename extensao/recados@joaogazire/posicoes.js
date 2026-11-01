// Lógica pura (sem GNOME Shell) para guardar posições das notas do Recados.
export const APP_ID = 'io.github.joaowgf.Recados';

export function idDaJanela(wmClass, titulo) {
    if (wmClass !== APP_ID || typeof titulo !== 'string')
        return null;
    const m = /^(?:Post-it|Recado) (\d+)$/.exec(titulo);
    return m ? Number(m[1]) : null;
}

export function lerPosicoes(texto) {
    let dados;
    try {
        dados = JSON.parse(texto);
    } catch {
        return {};
    }
    const saida = {};
    if (!dados || typeof dados !== 'object' || Array.isArray(dados))
        return saida;
    for (const [id, p] of Object.entries(dados)) {
        if (/^\d+$/.test(id) && p && Number.isFinite(p.x) && Number.isFinite(p.y))
            saida[id] = {x: p.x, y: p.y};
    }
    return saida;
}

export function gravarPosicao(texto, id, x, y) {
    const dados = lerPosicoes(texto);
    dados[String(id)] = {x: Math.round(x), y: Math.round(y)};
    return JSON.stringify(dados);
}

export function lerFixadas(texto) {
    let d;
    try {
        d = JSON.parse(texto);
    } catch {
        return [];
    }
    return Array.isArray(d) ? d.filter(v => Number.isInteger(v) && v > 0) : [];
}
