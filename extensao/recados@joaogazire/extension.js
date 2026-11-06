import Atk from 'gi://Atk';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import GObject from 'gi://GObject';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {ensureActorVisibleInScrollView} from 'resource:///org/gnome/shell/misc/animationUtils.js';

import {idDaJanela, lerPosicoes, gravarPosicao, lerFixadas} from './posicoes.js';
import {lerResumo, folhas, habitual, registrarAmostra, buscar, separarPorEstado, agendaDaCentral, agruparPorProjeto} from './central.js';

const LANCADOR = GLib.build_filenamev([GLib.get_home_dir(), '.local', 'bin', 'recados']);
const ATUALIZAR_S = 60;
const HISTORICO = GLib.build_filenamev([GLib.get_user_data_dir(), 'recados', 'pendentes-por-dia.json']);
const TAM = 18;
const PREFERENCIAS = GLib.build_filenamev([GLib.get_user_config_dir(), 'recados', 'preferencias.json']);
const GRAVANDO = GLib.build_filenamev([GLib.get_user_data_dir(), 'recados', 'voz', 'gravando']);

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
        if (pilha.gravando)
            cr.setSourceRGBA(0.93, 0.27, 0.24, i ? 0.8 : 1);  // vermelho: gravando ideia por voz
        else
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

const ABRIR_MS = 220;
const FECHAR_MS = 170;

// Cabeçalho de grupo (projeto ou estado): nome, selo com a contagem e seta que gira.
// Clicar abre/fecha o grupo sem fechar o menu (como um submenu, mas sem a caixa destacada).
const Cabecalho = GObject.registerClass({Signals: {'alternar': {}}},
class Cabecalho extends PopupMenu.PopupBaseMenuItem {
    _init(rotulo, contagem, destaque, estaAberto) {
        super._init({style_class: 'recados-cabecalho'});
        this._estaAberto = estaAberto;  // quem sabe o estado é a Central (um grupo aberto por vez)
        this.label = new St.Label({text: rotulo, x_expand: true, y_align: Clutter.ActorAlign.CENTER});
        this.add_child(this.label);
        this.label_actor = this.label;
        if (contagem > 0) {
            this.add_child(new St.Label({
                text: String(contagem), y_align: Clutter.ActorAlign.CENTER,
                style_class: destaque ? 'recados-selo recados-selo-pendente' : 'recados-selo',
            }));
        }
        this._seta = new St.Icon({icon_name: 'pan-end-symbolic', style_class: 'popup-menu-arrow recados-seta',
            y_align: Clutter.ActorAlign.CENTER});
        this._seta.set_pivot_point(0.5, 0.5);
        this.add_child(this._seta);
        this.add_accessible_state(Atk.StateType.EXPANDABLE);
    }

    activate(_event) {
        this.emit('alternar');  // não fecha o menu
    }

    vfunc_key_press_event(event) {
        const tecla = event.get_key_symbol();
        const aberto = this._estaAberto();
        if ((tecla === Clutter.KEY_Right && !aberto) || (tecla === Clutter.KEY_Left && aberto)) {
            this.emit('alternar');
            return Clutter.EVENT_STOP;
        }
        return super.vfunc_key_press_event(event);
    }

    girar(aberto, animar) {
        if (aberto) {
            this.add_style_pseudo_class('checked');
            this.add_accessible_state(Atk.StateType.EXPANDED);
        } else {
            this.remove_style_pseudo_class('checked');
            this.remove_accessible_state(Atk.StateType.EXPANDED);
        }
        this._seta.remove_all_transitions();
        this._seta.ease({rotation_angle_z: aberto ? 90 : 0, duration: animar ? ABRIR_MS : 0,
            mode: Clutter.AnimationMode.EASE_OUT_CUBIC});
    }
});

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
        this._gravando = GLib.file_test(GRAVANDO, GLib.FileTest.EXISTS);
        GLib.mkdir_with_parents(GLib.path_get_dirname(GRAVANDO), 0o700);
        this._monitorVoz = Gio.File.new_for_path(GRAVANDO).monitor_file(Gio.FileMonitorFlags.NONE, null);
        this._monitorVoz.connect('changed', () => {
            this._gravando = GLib.file_test(GRAVANDO, GLib.FileTest.EXISTS);
            this._pilha = {...this._pilha, gravando: this._gravando};
            this._icone.queue_repaint();
        });
        this._desenhar();
        this.menu.connect('open-state-changed', (_m, aberto) => {
            if (aberto) {
                this._limitarAltura();
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
        this.connect('destroy', () => {
            GLib.source_remove(this._timer);
            this._monitorVoz.cancel();
        });
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
        this.menu.box.add_style_class_name('recados-menu');  // largura fixa: abrir um grupo não alarga o menu
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
        // projetos e estados rolam aqui dentro; "Nova nota" e companhia ficam sempre visíveis embaixo
        this._lista = new PopupMenu.PopupMenuSection();
        this._rolagem = new St.ScrollView({style_class: 'recados-rolagem vfade', overlay_scrollbars: true,
            hscrollbar_policy: St.PolicyType.NEVER, vscrollbar_policy: St.PolicyType.AUTOMATIC,
            child: this._lista.box});
        this._lista.actor = this._rolagem;
        this.menu.addMenuItem(this._lista);
        this._secao = new PopupMenu.PopupMenuSection();
        this._lista.addMenuItem(this._secao);
        this._estados = new PopupMenu.PopupMenuSection();
        this._lista.addMenuItem(this._estados);
        this._focaveis = new Map();  // chave estável → ator, para devolver o foco depois de refazer a lista
        this._assinatura = null;
        this._grupos = new Map();
        this._aberto = null;  // chave do grupo aberto; sobrevive às atualizações da lista
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        const nova = new PopupMenu.PopupMenuItem('Nova nota');
        nova.connect('activate', () => rodar(['--nova']));
        this.menu.addMenuItem(nova);
        const doDia = new PopupMenu.PopupMenuItem('Nota do dia');
        doDia.connect('activate', () => rodar(['--hoje']));
        this.menu.addMenuItem(doDia);
        // Esconde "Nota do dia" quando a opção está desligada nas preferências.
        this.menu.connect('open-state-changed', (_m, aberto) => {
            if (!aberto)
                return;
            let ligada = true;
            try {
                ligada = JSON.parse(lerArquivo(PREFERENCIAS) || '{}').nota_do_dia !== false;
            } catch {}
            doDia.visible = ligada;
        });
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

    _limitarAltura() {
        const area = Main.layoutManager.getWorkAreaForMonitor(Main.layoutManager.primaryIndex);
        const escala = St.ThemeContext.get_for_stage(global.stage).scale_factor;
        this._rolagem.style = `max-height: ${Math.round(area.height * 0.6 / escala)}px;`;
    }

    _listar() {
        this._listarAgenda();
        const termo = (this._termo ?? '').trim();
        const assinatura = `${termo}\u0000${JSON.stringify(this._notas)}`;
        if (assinatura === this._assinatura)
            return;  // nada mudou: não refaz (mantém foco e animações)
        this._assinatura = assinatura;
        const foco = global.stage.get_key_focus();
        const chaveFoco = [...this._focaveis].find(([, ator]) => ator === foco)?.[0];
        this._secao.removeAll();
        this._estados.removeAll();
        this._grupos.clear();
        this._focaveis.clear();
        const grupos = separarPorEstado(this._notas);
        if (termo) {  // com busca: lista plana, procura em todas (inclusive concluídas e lixeira)
            const achadas = buscar(this._notas, termo);
            if (!achadas.length)
                this._secao.addMenuItem(new PopupMenu.PopupMenuItem('Nada encontrado', {reactive: false}));
            for (const n of achadas)
                this._secao.addMenuItem(this._itemNota(n, null));
        } else {
            if (!grupos.ativa.length)
                this._secao.addMenuItem(new PopupMenu.PopupMenuItem('Nenhuma nota ativa', {reactive: false}));
            for (const g of agruparPorProjeto(grupos.ativa))  // um grupo por projeto, com as notas dele embaixo
                this._grupo(this._secao, `p:${g.projeto}`, g.projeto, g.pendentes, true, g.notas);
            const outros = [['concluida', 'Concluídas'], ['cancelada', 'Canceladas'], ['arquivada', 'Arquivadas'], ['lixeira', 'Lixeira']]
                .filter(([estado]) => grupos[estado].length);
            if (outros.length)
                this._estados.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            for (const [estado, rotulo] of outros)
                this._grupo(this._estados, `e:${estado}`, rotulo, grupos[estado].length, false, grupos[estado]);
            if (!this._grupos.has(this._aberto))
                this._aberto = null;  // o grupo aberto sumiu (ex.: projeto esvaziou)
            else
                this._mostrar(this._grupos.get(this._aberto), true, false);
        }
        this._focaveis.get(chaveFoco)?.grab_key_focus();
    }

    _focavel(chave, ator) {
        this._focaveis.set(chave, ator);
        ator.connect('key-focus-in', () => ensureActorVisibleInScrollView(this._rolagem, ator));
    }

    // Cabeçalho + corpo. As notas do corpo só são montadas quando o grupo abre; um grupo aberto por vez.
    _grupo(destino, chave, rotulo, contagem, destaque, notas) {
        const cab = new Cabecalho(rotulo, contagem, destaque, () => this._aberto === chave);
        cab.accessible_name = destaque ? `${rotulo}, ${contagem} a fazer` : `${rotulo}, ${contagem} notas`;
        const corpo = new PopupMenu.PopupMenuSection();
        corpo.actor.clip_to_allocation = true;
        corpo.actor.visible = false;
        destino.addMenuItem(cab);
        destino.addMenuItem(corpo);
        const g = {chave, cab, corpo, notas, montado: false};
        cab.connect('alternar', () => this._alternar(g));
        this._focavel(chave, cab);
        this._grupos.set(chave, g);
    }

    _alternar(g) {
        const atual = this._grupos.get(this._aberto);
        if (atual && atual !== g)
            this._mostrar(atual, false, true);
        const abrir = this._aberto !== g.chave;
        this._aberto = abrir ? g.chave : null;
        this._mostrar(g, abrir, true);
    }

    _mostrar(g, abrir, animar) {
        if (abrir && !g.montado) {
            for (const n of g.notas)
                g.corpo.addMenuItem(this._itemNota(n, g));
            g.montado = true;
        }
        g.cab.girar(abrir, animar);
        const a = g.corpo.actor;
        if (!abrir) {  // o foco não pode ficar num item que vai sumir
            const foco = global.stage.get_key_focus();
            if (foco && a.contains(foco))
                g.cab.grab_key_focus();
        }
        const altura = a.visible ? a.height : 0;  // continua de onde a animação anterior parou
        const opacidade = a.visible ? a.opacity : 0;
        a.remove_all_transitions();
        if (!animar) {
            a.visible = abrir;
            a.set_height(-1);
            a.opacity = 255;
            return;
        }
        if (abrir) {
            a.visible = true;
            a.set_height(-1);
            const [, alvo] = a.get_preferred_height(-1);
            a.set_height(altura);
            a.opacity = opacidade;
            a.ease({height: alvo, opacity: 255, duration: ABRIR_MS, mode: Clutter.AnimationMode.EASE_OUT_CUBIC,
                onComplete: () => a.set_height(-1)});
        } else {
            a.ease({height: 0, opacity: 0, duration: FECHAR_MS, mode: Clutter.AnimationMode.EASE_IN_CUBIC,
                onComplete: () => {
                    a.visible = false;
                    a.set_height(-1);
                    a.opacity = 255;
                }});
        }
    }

    _itemNota(n, g) {
        const dentro = g !== null;
        const item = new PopupMenu.PopupBaseMenuItem({style_class: dentro ? 'recados-nota recados-interna' : 'recados-nota'});
        this._focavel(`n:${n.id}`, item);
        if (dentro) {  // ← dentro de um grupo fecha o grupo e volta para o cabeçalho
            item.connect('key-press-event', (_a, ev) => {
                if (ev.get_key_symbol() !== Clutter.KEY_Left)
                    return Clutter.EVENT_PROPAGATE;
                this._alternar(g);
                return Clutter.EVENT_STOP;
            });
        }
        item.add_child(new St.Widget({style_class: `recados-ponto recados-${n.cor}`, y_align: Clutter.ActorAlign.CENTER}));
        const textos = new St.BoxLayout({vertical: true, x_expand: true, y_align: Clutter.ActorAlign.CENTER});
        // dentro do grupo o estado já está no cabeçalho; na busca plana, a marca diz de onde a nota vem
        const marca = dentro ? '' : ({lixeira: '🗑 Lixeira (clique restaura): ', concluida: '✓ ', cancelada: '✗ ', arquivada: '▣ '}[n.estado] ?? '');
        textos.add_child(new St.Label({text: `${marca}${n.titulo}`}));
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
        const opcao = {ativa: '--abrir', lixeira: '--restaurar'}[n.estado] ?? '--reabrir';
        const args = [opcao, String(n.id)];
        item.connect('activate', () => rodar(args));
        return item;
    }

    _desenhar() {
        const pendentes = separarPorEstado(this._notas).ativa.reduce((acc, n) => acc + n.pendentes, 0);
        const hoje = GLib.DateTime.new_now_local().format('%Y-%m-%d');
        const historico = registrarAmostra(lerArquivo(HISTORICO), hoje, pendentes);
        gravarArquivo(HISTORICO, historico);
        this._pilha = {...folhas(pendentes, habitual(historico)), gravando: this._gravando ?? false};
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
