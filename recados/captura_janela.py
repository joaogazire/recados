"""Caixinha de uma linha para a captura rápida (Super+Alt+N)."""
from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk  # noqa: E402


class JanelaCaptura(Gtk.Window):
    def __init__(self, ao_gravar: Callable[[str], None], app: Gtk.Application | None = None):
        super().__init__(application=app, title="Post-it: captura", decorated=False, default_width=420)
        self.add_css_class("recado")
        self.add_css_class("cor-azul")
        self.add_css_class("captura")
        self._ao_gravar = ao_gravar
        self.entrada = Gtk.Entry(placeholder_text="Anotar na Inbox… (Enter grava, Esc cancela)",
                                 margin_top=10, margin_bottom=10, margin_start=10, margin_end=10)
        self.entrada.connect("activate", self._gravar)
        self.set_child(self.entrada)
        teclas = Gtk.EventControllerKey()
        teclas.connect("key-pressed", self._tecla)
        self.add_controller(teclas)

    def _gravar(self, *_):
        texto = self.entrada.get_text()
        if texto.strip():
            self._ao_gravar(texto)
        self.close()

    def _tecla(self, _c, tecla, _cod, _mod):
        if tecla == Gdk.KEY_Escape:
            self.close()
            return True
        return False
