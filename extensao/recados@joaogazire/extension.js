import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

import {idDaJanela, lerPosicoes, gravarPosicao} from './posicoes.js';

const ARQUIVO = GLib.build_filenamev([GLib.get_user_data_dir(), 'recados', 'posicoes.json']);
const ATRASO_MS = 600;

function ler() {
    try {
        const [, bytes] = GLib.file_get_contents(ARQUIVO);
        return new TextDecoder().decode(bytes);
    } catch {
        return '';
    }
}

function gravar(texto) {
    try {
        GLib.mkdir_with_parents(GLib.path_get_dirname(ARQUIVO), 0o700);
        Gio.File.new_for_path(ARQUIVO).replace_contents(
            new TextEncoder().encode(texto), null, false, Gio.FileCreateFlags.REPLACE_DESTINATION, null);
    } catch (e) {
        console.error(`recados: não gravou posições: ${e}`);
    }
}

export default class RecadosExtension extends Extension {
    enable() {
        this._janelas = new Map(); // MetaWindow -> {ids de sinais, timeout}
        this._criada = global.display.connect('window-created', (_d, w) => this._vigiar(w));
        for (const ator of global.get_window_actors())
            this._vigiar(ator.meta_window, false);
    }

    disable() {
        global.display.disconnect(this._criada);
        for (const [w, s] of this._janelas)
            this._soltar(w, s);
        this._janelas = null;
    }

    _id(w) {
        return idDaJanela(w.get_wm_class(), w.get_title());
    }

    _vigiar(w, restaurar = true) {
        if (!w || this._janelas.has(w))
            return;
        const s = {sinais: [], timeout: 0, restaurou: !restaurar};
        this._janelas.set(w, s);
        const tentar = () => {
            const id = this._id(w);
            if (id === null || s.restaurou)
                return;
            s.restaurou = true;
            const p = lerPosicoes(ler())[id];
            if (p)
                w.move_frame(true, p.x, p.y);
        };
        s.sinais.push(w.connect('shown', tentar));
        s.sinais.push(w.connect('notify::title', tentar));
        s.sinais.push(w.connect('position-changed', () => this._agendar(w, s)));
        s.sinais.push(w.connect('unmanaged', () => {
            this._soltar(w, s);
            this._janelas?.delete(w);
        }));
    }

    _agendar(w, s) {
        if (s.timeout)
            GLib.source_remove(s.timeout);
        s.timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, ATRASO_MS, () => {
            s.timeout = 0;
            const id = this._id(w);
            if (id !== null && s.restaurou) {
                const r = w.get_frame_rect();
                gravar(gravarPosicao(ler(), id, r.x, r.y));
            }
            return GLib.SOURCE_REMOVE;
        });
    }

    _soltar(w, s) {
        if (s.timeout)
            GLib.source_remove(s.timeout);
        for (const id of s.sinais)
            w.disconnect(id);
    }
}
