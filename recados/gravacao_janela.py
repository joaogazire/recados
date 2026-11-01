"""Janela que aparece enquanto grava uma ideia: indicador, tempo e o texto chegando ao vivo."""
from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402


class JanelaGravacao(Gtk.Window):
    def __init__(self, ao_parar: Callable[[], None], app: Gtk.Application | None = None):
        super().__init__(application=app, title="Post-it: gravando", decorated=False,
                         default_width=320, default_height=200)
        for c in ("recado", "cor-verde", "gravacao"):
            self.add_css_class(c)
        self.status = Gtk.Label(xalign=0, hexpand=True, use_markup=True)
        self.botao_parar = Gtk.Button(label="Parar")
        self.botao_parar.add_css_class("destructive-action")
        self.botao_parar.connect("clicked", lambda *_: ao_parar())
        barra = Gtk.Box(spacing=6, margin_start=10, margin_end=6, margin_top=6, margin_bottom=6)
        barra.add_css_class("barra")
        barra.append(self.status)
        barra.append(self.botao_parar)
        self.texto = Gtk.Label(label="", wrap=True, xalign=0, yalign=0, selectable=False,
                               margin_start=12, margin_end=12, margin_top=8, margin_bottom=12)
        self.texto.add_css_class("ao-vivo")
        self._aguardando = Gtk.Label(label="Fale sua ideia… o texto aparece aqui.", xalign=0,
                                     margin_start=12, margin_top=8)
        self._aguardando.add_css_class("dim-label")
        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        caixa.append(Gtk.WindowHandle(child=barra))
        caixa.append(self._aguardando)
        caixa.append(Gtk.ScrolledWindow(child=self.texto, vexpand=True))
        self.set_child(caixa)
        self.tique(0)

    def tique(self, segundos: int) -> None:
        self.status.set_markup(f'<span foreground="#c01c28">●</span> <b>Gravando</b>  {segundos // 60}:{segundos % 60:02d}')

    def mostrar_texto(self, texto: str) -> None:
        self._aguardando.set_visible(not texto)
        self.texto.set_label(texto)

    def resumindo(self) -> None:
        self.status.set_markup("<b>Resumindo a ideia…</b>")
        self.botao_parar.set_sensitive(False)
