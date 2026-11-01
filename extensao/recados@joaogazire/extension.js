import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import GObject from 'gi://GObject';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

import {idDaJanela, lerPosicoes, gravarPosicao} from './posicoes.js';
import {lerResumo, rotuloPainel} from './central.js';

const LANCADOR = GLib.build_filenamev([GLib.get_home_dir(), '.local', 'bin', 'recados']);
const ATUALIZAR_S = 60;

function rodar(args) {
    try {
        Gio.Subprocess.new([LANCADOR, ...args], Gio.SubprocessFlags.NONE);
    } catch (e) {
        console.error(`recados: não rodou ${args}: ${e}`);
    }
}

const Central = GObject.registerClass(
class Central extends PanelMenu.Button {
    _init() {
        super._init(0.5, 'Post-it');
        const caixa = new St.BoxLayout({style_class: 'panel-status-menu-box'});
        caixa.add_child(new St.Icon({icon_name: 'accessories-text-editor-symbolic', style_class: 'system-status-icon'}));
        this._contador = new St.Label({text: '', y_align: Clutter.ActorAlign.CENTER, style_class: 'recados-contador'});
        caixa.add_child(this._contador);
        this.add_child(caixa);
        this._notas = [];
        this._ocupado = false;
        this._desenhar();
        this.menu.connect('open-state-changed', (_m, aberto) => {
            if (aberto)
                this.atualizar();
        });
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, ATUALIZAR_S, () => {
            this.atualizar();
            return GLib.SOURCE_CONTINUE;
        });
        this.connect('destroy', () => GLib.source_remove(this._timer));
        this.atualizar();
    }

    atualizar() {
        if (this._ocupado)
            return;
        this._ocupado = true;
        let proc;
        try {
            proc = Gio.Subprocess.new([LANCADOR, '--listar'],
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE);
        } catch (e) {
            this._ocupado = false;
            console.error(`recados: --listar falhou: ${e}`);
            return;
        }
        proc.communicate_utf8_async(null, null, (p, res) => {
            this._ocupado = false;
            try {
                const [, saida] = p.communicate_utf8_finish(res);
                this._notas = lerResumo(saida ?? '');
            } catch (e) {
                console.error(`recados: --listar falhou: ${e}`);
                return;
            }
            if (this.menu)
                this._desenhar();
        });
    }

    _desenhar() {
        const rotulo = rotuloPainel(this._notas);
        this._contador.text = rotulo;
        this._contador.visible = rotulo !== '';
        this.menu.removeAll();
        if (!this._notas.length)
            this.menu.addMenuItem(new PopupMenu.PopupMenuItem('Nenhuma nota', {reactive: false}));
        for (const n of this._notas) {
            const item = new PopupMenu.PopupBaseMenuItem();
            item.add_child(new St.Widget({style_class: `recados-ponto recados-${n.cor}`, y_align: Clutter.ActorAlign.CENTER}));
            item.add_child(new St.Label({text: n.titulo, x_expand: true, y_align: Clutter.ActorAlign.CENTER}));
            if (n.total) {
                const feito = n.pendentes === 0;
                item.add_child(new St.Label({
                    text: feito ? `✓ ${n.total}` : `${n.total - n.pendentes}/${n.total}`,
                    style_class: feito ? 'recados-feito' : 'recados-pendente',
                    y_align: Clutter.ActorAlign.CENTER,
                }));
            }
            item.connect('activate', () => rodar(['--abrir', String(n.id)]));
            this.menu.addMenuItem(item);
        }
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        const nova = new PopupMenu.PopupMenuItem('Nova nota');
        nova.connect('activate', () => rodar(['--nova']));
        this.menu.addMenuItem(nova);
        const todas = new PopupMenu.PopupMenuItem('Mostrar todas');
        todas.connect('activate', () => rodar([]));
        this.menu.addMenuItem(todas);
        const prefs = new PopupMenu.PopupMenuItem('Preferências');
        prefs.connect('activate', () => rodar(['--preferencias']));
        this.menu.addMenuItem(prefs);
    }
});

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
        this._central = new Central();
        Main.panel.addToStatusArea(this.uuid, this._central);
        this._janelas = new Map(); // MetaWindow -> {ids de sinais, timeout}
        this._criada = global.display.connect('window-created', (_d, w) => this._vigiar(w));
        for (const ator of global.get_window_actors())
            this._vigiar(ator.meta_window, false);
    }

    disable() {
        this._central?.destroy();
        this._central = null;
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
