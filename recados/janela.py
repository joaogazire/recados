"""Janela de uma nota: editor Markdown, cor, recolher, salvar sozinho."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")
from gi.repository import GLib, Gtk, GtkSource, Pango  # noqa: E402

from recados.markdown import alternar_item, blocos, para_pango, realces  # noqa: E402
from recados.notas import CORES, Nota, Repositorio  # noqa: E402

ATRASO_SALVAR_MS = 400
DESFAZER_MS = 5000

_ESTILO_TAGS = {
    "titulo1": {"weight": Pango.Weight.BOLD, "scale": 1.5},
    "titulo2": {"weight": Pango.Weight.BOLD, "scale": 1.3},
    "titulo3": {"weight": Pango.Weight.BOLD, "scale": 1.15},
    "negrito": {"weight": Pango.Weight.BOLD},
    "italico": {"style": Pango.Style.ITALIC},
    "codigo": {"family": "monospace", "background": "rgba(0,0,0,0.08)"},
    "link": {"underline": Pango.Underline.SINGLE, "foreground": "#1c4f9c"},
    "caixa": {"family": "monospace", "weight": Pango.Weight.BOLD, "foreground": "rgba(0,0,0,0.6)"},
    "caixa-marcada": {"family": "monospace", "weight": Pango.Weight.BOLD, "foreground": "#2f7d32"},
    "marcador": {"weight": Pango.Weight.BOLD, "foreground": "rgba(0,0,0,0.55)"},
}


class JanelaNota(Gtk.Window):
    def __init__(self, repo: Repositorio, nota: Nota, app: Gtk.Application | None = None):
        super().__init__(application=app, title=f"Recado {nota.id}", decorated=False)
        self.repo = repo
        self.nota = nota
        self._salvar_id = 0
        self._apagar_id = 0
        self.em_leitura = False
        self.apagando = False
        self.add_css_class("recado")
        self.set_default_size(nota.largura, nota.altura)

        self.buffer = GtkSource.Buffer()
        self.buffer.set_highlight_syntax(False)
        for nome, props in _ESTILO_TAGS.items():
            self.buffer.create_tag(nome, **props)
        self.buffer.set_text(nota.texto)
        self._realcar()
        self.buffer.connect("changed", self._ao_mudar)

        self.editor = GtkSource.View(buffer=self.buffer, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.editor.add_css_class("editor")
        for lado in ("top", "bottom", "left", "right"):
            getattr(self.editor, f"set_{lado}_margin")(10)
        self.rolagem = Gtk.ScrolledWindow(child=self.editor, vexpand=True)
        clique_editor = Gtk.GestureClick()
        clique_editor.connect("released", self._ao_clicar_editor)
        self.editor.add_controller(clique_editor)

        self._caixa_leitura = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4,
                                      margin_top=10, margin_bottom=10, margin_start=12, margin_end=12)
        self.leitura = Gtk.ScrolledWindow(child=self._caixa_leitura, vexpand=True, visible=False)
        self.leitura.add_css_class("leitura")

        self._aviso = Gtk.Box(spacing=6, visible=False, margin_start=8, margin_end=4)
        self._aviso.add_css_class("aviso")
        self._aviso.append(Gtk.Label(label="Nota apagada", hexpand=True, xalign=0))
        desfazer = Gtk.Button(label="Desfazer")
        desfazer.connect("clicked", lambda *_: self.desfazer_apagar())
        self._aviso.append(desfazer)

        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        caixa.append(self._barra())
        caixa.append(self.rolagem)
        caixa.append(self.leitura)
        caixa.append(self._aviso)
        self.set_child(caixa)

        self._aplicar_cor(nota.cor)
        self._mostrar_corpo()
        self.connect("close-request", self._ao_fechar)
        atalhos = Gtk.ShortcutController(scope=Gtk.ShortcutScope.MANAGED)
        atalhos.add_shortcut(Gtk.Shortcut(
            trigger=Gtk.ShortcutTrigger.parse_string("<Control>e"),
            action=Gtk.CallbackAction.new(lambda *_: (self.alternar_leitura(), True)[1])))
        self.add_controller(atalhos)

    # --- barra de título ---
    def _barra(self) -> Gtk.Widget:
        barra = Gtk.Box(spacing=2)
        barra.add_css_class("barra")
        nova = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="Nova nota (Ctrl+N)")
        nova.add_css_class("flat")
        nova.connect("clicked", lambda *_: self.activate_action("app.nova", None))
        barra.append(nova)
        barra.append(Gtk.Box(hexpand=True))

        cores = Gtk.Box(spacing=4, margin_start=6, margin_end=6, margin_top=6, margin_bottom=6)
        for cor in CORES:
            b = Gtk.Button(tooltip_text=cor)
            b.add_css_class("bolinha")
            b.add_css_class(f"cor-{cor}")
            b.connect("clicked", lambda _b, c=cor: (self.definir_cor(c), pop.popdown()))
            cores.append(b)
        pop = Gtk.Popover(child=cores)
        menu = Gtk.MenuButton(icon_name="color-select-symbolic", popover=pop, tooltip_text="Cor")
        menu.add_css_class("flat")
        barra.append(menu)

        ler = Gtk.Button(icon_name="view-reveal-symbolic", tooltip_text="Ler / editar (Ctrl+E)")
        ler.add_css_class("flat")
        ler.connect("clicked", lambda *_: self.alternar_leitura())
        barra.append(ler)

        lixo = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Apagar nota")
        lixo.add_css_class("flat")
        lixo.connect("clicked", lambda *_: self.apagar())
        barra.append(lixo)

        fechar = Gtk.Button(icon_name="window-close-symbolic", tooltip_text="Fechar")
        fechar.add_css_class("flat")
        fechar.connect("clicked", lambda *_: self.close())
        barra.append(fechar)

        clique = Gtk.GestureClick()
        clique.connect("pressed", self._ao_clicar_barra)
        alca = Gtk.WindowHandle(child=barra)
        alca.add_controller(clique)
        return alca

    def _ao_clicar_barra(self, gesto, n, _x, _y):
        if n == 2:
            gesto.set_state(Gtk.EventSequenceState.CLAIMED)
            self.alternar_recolhida()

    # --- API ---
    def texto(self) -> str:
        return self.buffer.get_text(self.buffer.get_start_iter(), self.buffer.get_end_iter(), True)

    def salvar_agora(self) -> None:
        if self._salvar_id:
            GLib.source_remove(self._salvar_id)
            self._salvar_id = 0
        texto = self.texto()
        if texto != self.nota.texto:
            self.nota = self.repo.atualizar(self.nota.id, texto=texto)

    def definir_cor(self, cor: str) -> None:
        self.nota = self.repo.atualizar(self.nota.id, cor=cor)
        self._aplicar_cor(cor)

    def _mostrar_corpo(self) -> None:
        visivel = not self.nota.recolhida and not self.apagando
        self.rolagem.set_visible(visivel and not self.em_leitura)
        self.leitura.set_visible(visivel and self.em_leitura)

    def alternar_recolhida(self) -> None:
        if self.apagando:
            return
        recolhida = not self.nota.recolhida
        if recolhida:
            self._guardar_tamanho()
        self.nota = self.repo.atualizar(self.nota.id, recolhida=recolhida)
        self._mostrar_corpo()
        if recolhida:
            self.set_default_size(self.nota.largura, 1)
        else:
            self.set_default_size(self.nota.largura, self.nota.altura)

    def alternar_leitura(self) -> None:
        self.salvar_agora()
        self.em_leitura = not self.em_leitura
        if self.em_leitura:
            self._montar_leitura()
        self._mostrar_corpo()
        if not self.em_leitura:
            self.editor.grab_focus()

    def caixas_leitura(self) -> list[Gtk.CheckButton]:
        filho, saida = self._caixa_leitura.get_first_child(), []
        while filho:
            if isinstance(filho, Gtk.CheckButton):
                saida.append(filho)
            filho = filho.get_next_sibling()
        return saida

    def clicar_offset(self, offset: int) -> bool:
        """Se o offset cai numa caixa [ ]/[x], alterna o item. Devolve se alternou."""
        it = self.buffer.get_iter_at_offset(offset)
        if not any(t.props.name in ("caixa", "caixa-marcada") for t in it.get_tags()):
            return False
        self._trocar_texto(alternar_item(self.texto(), it.get_line()), offset)
        return True

    def apagar(self) -> None:
        if self.apagando:
            return
        self.salvar_agora()
        self.repo.apagar(self.nota.id)
        self.apagando = True
        self._mostrar_corpo()
        self._aviso.set_visible(True)
        self.set_default_size(self.nota.largura, 1)
        self._apagar_id = GLib.timeout_add(DESFAZER_MS, self._fim_apagar)

    def desfazer_apagar(self) -> None:
        if not self.apagando:
            return
        if self._apagar_id:
            GLib.source_remove(self._apagar_id)
            self._apagar_id = 0
        self.repo.restaurar(self.nota.id)
        self.apagando = False
        self._aviso.set_visible(False)
        self._mostrar_corpo()
        if not self.nota.recolhida:
            self.set_default_size(self.nota.largura, self.nota.altura)

    def _fim_apagar(self):
        self._apagar_id = 0
        self.destroy()
        return GLib.SOURCE_REMOVE

    # --- internos ---
    def _trocar_texto(self, novo: str, cursor: int | None = None) -> None:
        if novo == self.texto():
            return
        self.buffer.begin_user_action()
        ini, fim = self.buffer.get_bounds()
        self.buffer.delete(ini, fim)
        self.buffer.insert(self.buffer.get_start_iter(), novo)
        self.buffer.end_user_action()
        if cursor is not None:
            self.buffer.place_cursor(self.buffer.get_iter_at_offset(cursor))

    def _ao_clicar_editor(self, gesto, n, x, y):
        if n != 1:
            return
        bx, by = self.editor.window_to_buffer_coords(Gtk.TextWindowType.WIDGET, int(x), int(y))
        ok, it = self.editor.get_iter_at_location(bx, by)
        if ok:
            self.clicar_offset(it.get_offset())

    def _montar_leitura(self) -> None:
        while (f := self._caixa_leitura.get_first_child()):
            self._caixa_leitura.remove(f)
        for tipo, valor, conteudo, linha in blocos(self.texto()):
            if tipo == "item":
                rot = Gtk.Label(use_markup=True, wrap=True, xalign=0)
                rot.set_markup(para_pango(conteudo))
                if valor:
                    rot.add_css_class("feito")
                w = Gtk.CheckButton(active=valor, child=rot)
                w.connect("toggled", self._ao_marcar, linha)
            elif tipo == "vazio":
                w = Gtk.Box(height_request=6)
            else:
                w = Gtk.Label(use_markup=True, wrap=True, xalign=0, selectable=False)
                markup = para_pango(conteudo)
                if tipo == "lista":
                    markup = "•  " + markup
                w.set_markup(markup)
                if tipo == "titulo":
                    w.add_css_class(f"titulo{valor}")
            self._caixa_leitura.append(w)

    def _ao_marcar(self, botao, linha):
        self._trocar_texto(alternar_item(self.texto(), linha))
        self.salvar_agora()
        botao.get_child().set_css_classes(["feito"] if botao.get_active() else [])

    def _aplicar_cor(self, cor: str) -> None:
        for c in CORES:
            self.remove_css_class(f"cor-{c}")
        self.add_css_class(f"cor-{cor}")

    def _realcar(self) -> None:
        ini, fim = self.buffer.get_bounds()
        for nome in _ESTILO_TAGS:
            self.buffer.remove_tag_by_name(nome, ini, fim)
        for i, f, tag in realces(self.texto()):
            self.buffer.apply_tag_by_name(
                tag, self.buffer.get_iter_at_offset(i), self.buffer.get_iter_at_offset(f)
            )

    def _ao_mudar(self, *_):
        self._realcar()
        if self._salvar_id:
            GLib.source_remove(self._salvar_id)
        self._salvar_id = GLib.timeout_add(ATRASO_SALVAR_MS, self._salvar_atrasado)

    def _salvar_atrasado(self):
        self._salvar_id = 0
        self.salvar_agora()
        return GLib.SOURCE_REMOVE

    def _guardar_tamanho(self) -> None:
        l, a = self.get_width(), self.get_height()
        if l > 50 and a > 50 and (l, a) != (self.nota.largura, self.nota.altura):
            self.nota = self.repo.atualizar(self.nota.id, largura=l, altura=a)

    def _ao_fechar(self, *_):
        if self.apagando:
            if self._apagar_id:
                GLib.source_remove(self._apagar_id)
                self._apagar_id = 0
            return False
        self.salvar_agora()
        if not self.nota.recolhida:
            self._guardar_tamanho()
        return False
