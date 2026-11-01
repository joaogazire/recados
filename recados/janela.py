"""Janela de uma nota: editor Markdown, cor, recolher, salvar sozinho."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")
from gi.repository import GLib, Gtk, GtkSource, Pango  # noqa: E402

from recados.markdown import realces  # noqa: E402
from recados.notas import CORES, Nota, Repositorio  # noqa: E402

ATRASO_SALVAR_MS = 400

_ESTILO_TAGS = {
    "titulo1": {"weight": Pango.Weight.BOLD, "scale": 1.5},
    "titulo2": {"weight": Pango.Weight.BOLD, "scale": 1.3},
    "titulo3": {"weight": Pango.Weight.BOLD, "scale": 1.15},
    "negrito": {"weight": Pango.Weight.BOLD},
    "italico": {"style": Pango.Style.ITALIC},
    "codigo": {"family": "monospace", "background": "rgba(0,0,0,0.08)"},
    "link": {"underline": Pango.Underline.SINGLE, "foreground": "#1c4f9c"},
    "marcador": {"weight": Pango.Weight.BOLD, "foreground": "rgba(0,0,0,0.55)"},
}


class JanelaNota(Gtk.Window):
    def __init__(self, repo: Repositorio, nota: Nota, app: Gtk.Application | None = None):
        super().__init__(application=app, title="Recado", decorated=False)
        self.repo = repo
        self.nota = nota
        self._salvar_id = 0
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

        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        caixa.append(self._barra())
        caixa.append(self.rolagem)
        self.set_child(caixa)

        self._aplicar_cor(nota.cor)
        if nota.recolhida:
            self.rolagem.set_visible(False)
        self.connect("close-request", self._ao_fechar)

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

    def alternar_recolhida(self) -> None:
        recolhida = not self.nota.recolhida
        if not recolhida:
            self.rolagem.set_visible(True)
        else:
            self._guardar_tamanho()
            self.rolagem.set_visible(False)
        self.nota = self.repo.atualizar(self.nota.id, recolhida=recolhida)
        if recolhida:
            self.set_default_size(self.nota.largura, 1)
        else:
            self.set_default_size(self.nota.largura, self.nota.altura)

    # --- internos ---
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
        self.salvar_agora()
        if not self.nota.recolhida:
            self._guardar_tamanho()
        return False
