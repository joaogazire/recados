import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import GObject from 'gi://GObject';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

import {idDaJanela, lerPosicoes, gravarPosicao, lerFixadas} from './posicoes.js';
import {lerResumo, folhas, habitual, registrarAmostra, buscar, separarPorEstado, agendaDaCentral} from './central.js';

const LANCADOR = GLib.build_filenamev([GLib.get_home_dir(), '.local', 'bin', 'recados']);
const ATUALIZAR_S = 60;
const HISTORICO = GLib.build_filenamev([GLib.get_user_data_dir(), 'recados', 'pendentes-por-dia.json']);
const TAM = 18;

function lerArquivo(caminho) {
    try {
        return new TextDecoder().decode(GLib.file_get_contents(caminho)[1]);
    } catch {
        return '';
    }
}

function gravarArquivo(caminho, texto) {
    try {
        GLib.mkdir_with_parents(GLib.path_get_dirname(caminho), 0o700);
        Gio.File.new_for_path(caminho).replace_contents(
            new TextEncoder().encode(texto), null, false, Gio.FileCreateFlags.REPLACE_DESTINATION, null);
    } catch (e) {
        console.error(`recados: não gravou ${caminho}: ${e}`);
    }
}

// Desenha 1 a 4 post-its empilhados (o da frente embaixo à esquerda); ✓ quando não há pendentes.
function desenharPilha(area, pilha) {
    const cr = area.get_context();
    const [w, h] = area.get_surface_size();
    const lado = Math.round(w * 0.62), passo = (w - lado) / 3;
    for (let i = pilha.n - 1; i >= 0; i--) {
        const x = i * passo, y = h - lado - i * passo;
        cr.rectangle(x + 0.5, y + 0.5, lado - 1, lado - 1);
        cr.setSourceRGBA(0.996, 0.941, 0.541, i ? 0.8 : 1);
        cr.fillPreserve();
        cr.setSourceRGBA(0.79, 0.72, 0.29, 1);
        cr.setLineWidth(1);
        cr.stroke();
    }
    if (pilha.feito) {
        const y0 = h - lado;
        cr.setSourceRGBA(0.18, 0.49, 0.2, 1);
        cr.setLineWidth(2);
        cr.moveTo(lado * 0.22, y0 + lado * 0.55);
        cr.lineTo(lado * 0.42, y0 + lado * 0.75);
        cr.lineTo(lado * 0.8, y0 + lado * 0.3);
        cr.stroke();
    }
    cr.$dispose();
}

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
        this._pilha = {n: 1, feito: true};
        this._icone = new St.DrawingArea({width: TAM, height: TAM, y_align: Clutter.ActorAlign.CENTER});
        this._icone.connect('repaint', a => desenharPilha(a, this._pilha));
        caixa.add_child(this._icone);
        this.add_child(caixa);
        this._notas = [];
        this._ocupado = false;
        this._montarMenu();
        this._desenhar();
        this.menu.connect('open-state-changed', (_m, aberto) => {
            if (aberto) {
                this.atualizar();
                if (this._busca)
                    global.stage.set_key_focus(this._busca);
            } else if (this._busca) {
                this._busca.set_text('');
            }
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

    // Monta o menu fixo uma vez; depois só a lista muda (não tira o foco da busca).
    _montarMenu() {
        this._busca = new St.Entry({hint_text: 'Buscar nas notas…', can_focus: true, x_expand: true,
            style_class: 'recados-busca', text: this._termo ?? ''});
        this._busca.clutter_text.connect('text-changed', () => {
            this._termo = this._busca.get_text();
            this._listar();
        });
        const linhaBusca = new PopupMenu.PopupBaseMenuItem({reactive: false, can_focus: false});
        linhaBusca.add_child(this._busca);
        this.menu.addMenuItem(linhaBusca);
        this._agenda = new PopupMenu.PopupMenuSection();
        this.menu.addMenuItem(this._agenda);
        this._secao = new PopupMenu.PopupMenuSection();
        this.menu.addMenuItem(this._secao);
        this._outros = {};
        for (const [estado, rotulo] of [['concluida', 'Concluídas'], ['cancelada', 'Canceladas'], ['arquivada', 'Arquivadas']]) {
            const sub = new PopupMenu.PopupSubMenuMenuItem(rotulo);
            this._outros[estado] = {sub, rotulo};
            this.menu.addMenuItem(sub);
        }
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        const nova = new PopupMenu.PopupMenuItem('Nova nota');
        nova.connect('activate', () => rodar(['--nova']));
        this.menu.addMenuItem(nova);
        const doDia = new PopupMenu.PopupMenuItem('Nota do dia');
        doDia.connect('activate', () => rodar(['--hoje']));
        this.menu.addMenuItem(doDia);
        const todas = new PopupMenu.PopupMenuItem('Mostrar todas');
        todas.connect('activate', () => rodar([]));
        this.menu.addMenuItem(todas);
        const prefs = new PopupMenu.PopupMenuItem('Preferências');
        prefs.connect('activate', () => rodar(['--preferencias']));
        this.menu.addMenuItem(prefs);
    }

    // Lista das notas (filtrada pela busca) dentro da seção do menu.
    // Lembretes: vencidos (em vermelho) e os próximos 7 dias, até 5 no total.
    _listarAgenda() {
        this._agenda.removeAll();
        const {vencidos, proximos} = agendaDaCentral(this._notas, Date.now());
        const itens = [...vencidos.map(l => [l, true]), ...proximos.map(l => [l, false])].slice(0, 5);
        for (const [l, atrasado] of itens) {
            const d = GLib.DateTime.new_from_unix_local(Math.floor(l.quando / 1000));
            const item = new PopupMenu.PopupMenuItem(`⏰ ${d.format('%d/%m %H:%M')}  ${l.titulo}`);
            if (atrasado)
                item.label.add_style_class_name('recados-vencido');
            item.connect('activate', () => rodar(['--abrir', String(l.id)]));
            this._agenda.addMenuItem(item);
        }
        if (itens.length)
            this._agenda.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
    }

    _listar() {
        this._listarAgenda();
        this._secao.removeAll();
        const grupos = separarPorEstado(this._notas);
        const termo = this._termo ?? '';
        // sem busca: só as ativas; com busca: procura em todas
        const achadas = buscar(termo.trim() ? this._notas : grupos.ativa, termo);
        for (const [estado, {sub, rotulo}] of Object.entries(this._outros)) {
            const lista = grupos[estado];
            sub.label.text = `${rotulo} (${lista.length})`;
            sub.visible = lista.length > 0;
            sub.menu.removeAll();
            for (const n of lista) {
                const item = new PopupMenu.PopupMenuItem(n.titulo);
                item.connect('activate', () => rodar(['--reabrir', String(n.id)]));
                sub.menu.addMenuItem(item);
            }
        }
        if (!achadas.length) {
            const vazio = this._notas.length ? 'Nada encontrado' : 'Nenhuma nota';
            this._secao.addMenuItem(new PopupMenu.PopupMenuItem(vazio, {reactive: false}));
        }
        for (const n of achadas) {
            const item = new PopupMenu.PopupBaseMenuItem();
            item.add_child(new St.Widget({style_class: `recados-ponto recados-${n.cor}`, y_align: Clutter.ActorAlign.CENTER}));
            const textos = new St.BoxLayout({vertical: true, x_expand: true, y_align: Clutter.ActorAlign.CENTER});
            textos.add_child(new St.Label({text: n.titulo}));
            if (n.trecho)
                textos.add_child(new St.Label({text: n.trecho, style_class: 'recados-trecho'}));
            item.add_child(textos);
            if (n.total) {
                const feito = n.pendentes === 0;
                item.add_child(new St.Label({
                    text: feito ? `✓ ${n.total}` : `${n.total - n.pendentes}/${n.total}`,
                    style_class: feito ? 'recados-feito' : 'recados-pendente',
                    y_align: Clutter.ActorAlign.CENTER,
                }));
            }
            const args = n.estado === 'ativa' ? ['--abrir', String(n.id)] : ['--reabrir', String(n.id)];
            item.connect('activate', () => rodar(args));
            this._secao.addMenuItem(item);
        }
    }

    _desenhar() {
        const pendentes = separarPorEstado(this._notas).ativa.reduce((acc, n) => acc + n.pendentes, 0);
        const hoje = GLib.DateTime.new_now_local().format('%Y-%m-%d');
        const historico = registrarAmostra(lerArquivo(HISTORICO), hoje, pendentes);
        gravarArquivo(HISTORICO, historico);
        this._pilha = folhas(pendentes, habitual(historico));
        this._icone.queue_repaint();
        this.accessible_name = `Post-it: ${pendentes} tarefas pendentes`;
        this._listar();
    }
});

const ARQUIVO = GLib.build_filenamev([GLib.get_user_data_dir(), 'recados', 'posicoes.json']);
const ATRASO_MS = 600;
const FIXADAS = GLib.build_filenamev([GLib.get_user_data_dir(), 'recados', 'fixadas.json']);

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
        this._fixadas = new Set(lerFixadas(lerArquivo(FIXADAS)));
        this._monitor = Gio.File.new_for_path(FIXADAS).monitor_file(Gio.FileMonitorFlags.WATCH_MOVES, null);
        this._monitorId = this._monitor.connect('changed', () => {
            this._fixadas = new Set(lerFixadas(lerArquivo(FIXADAS)));
            for (const w of this._janelas.keys())
                this._fixar(w);
        });
        this._criada = global.display.connect('window-created', (_d, w) => this._vigiar(w));
        for (const ator of global.get_window_actors())
            this._vigiar(ator.meta_window, false);
    }

    disable() {
        this._monitor.disconnect(this._monitorId);
        this._monitor.cancel();
        this._monitor = null;
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
            this._fixar(w);
            const id = this._id(w);
            if (id === null || s.restaurou)
                return;
            s.restaurou = true;
            const p = lerPosicoes(ler())[id];
            if (p)
                w.move_frame(true, p.x, p.y);
        };
        this._fixar(w);
        s.sinais.push(w.connect('shown', tentar));
        s.sinais.push(w.connect('notify::title', tentar));
        s.sinais.push(w.connect('position-changed', () => this._agendar(w, s)));
        s.sinais.push(w.connect('unmanaged', () => {
            this._soltar(w, s);
            this._janelas?.delete(w);
        }));
    }

    // Põe por cima (ou tira) conforme o alfinete da nota; só o Shell consegue isso no Wayland.
    _fixar(w) {
        const id = this._id(w);
        if (id === null)
            return;
        const quer = this._fixadas.has(id);
        if (quer && !w.is_above())
            w.make_above();
        else if (!quer && w.is_above())
            w.unmake_above();
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
