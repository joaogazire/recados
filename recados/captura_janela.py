"""Caixinha de captura (Ctrl+N, Super+Alt+N e voz): escolhe o projeto e grava o item no '## Fazer' dele.

Projeto em "automático": o 1º Enter pede o palpite (nome citado no texto ou DeepSeek) e mostra;
o 2º Enter grava. Vários itens de uma vez: separar com ';'.
"""
from __future__ import annotations

import threading
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from recados.projetos import INBOX  # noqa: E402

AUTO = "Projeto automático (palpite)"
NOVO = "+ Novo projeto…"


def separar_itens(texto: str) -> list[str]:
    return [i.strip() for i in texto.split(";") if i.strip()]


class JanelaCaptura(Gtk.Window):
    def __init__(self, projetos: list[str], ao_gravar: Callable[[str, bool, list[str]], None],
                 sugerir: Callable[[str], str], app: Gtk.Application | None = None,
                 itens: list[str] | None = None, contexto: str = "", projeto: str | None = None,
                 ao_cancelar: Callable[[], None] | None = None):
        super().__init__(application=app, title="Post-it: captura", decorated=False, default_width=460)
        self.add_css_class("recado")
        self.add_css_class("cor-azul")
        self.add_css_class("captura")
        self._ao_gravar = ao_gravar
        self._sugerir = sugerir
        self._contexto = contexto  # texto extra para o palpite (a fala inteira, na voz)
        self._opcoes = [AUTO, *projetos, INBOX, NOVO]
        self._ao_cancelar = ao_cancelar  # fechou sem gravar (na voz: não perder a ideia)
        self._pensando = False
        self._gravou = False
        self._fechada = False

        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=10, margin_bottom=10,
                        margin_start=10, margin_end=10)
        self.projeto = Gtk.DropDown.new_from_strings(self._opcoes)
        self.projeto.set_tooltip_text("Projeto onde o item vai entrar")
        if projeto in self._opcoes[1:-1]:
            self.projeto.set_selected(self._opcoes.index(projeto))
        self.projeto.connect("notify::selected", self._ao_trocar_projeto)
        caixa.append(self.projeto)
        self.nome_novo = Gtk.Entry(placeholder_text="Nome do projeto novo", visible=False)
        self.nome_novo.connect("activate", self._enter)
        caixa.append(self.nome_novo)
        self.entrada = Gtk.Entry(placeholder_text="O que fazer… (vários: separe com ;)")
        if itens:
            self.entrada.set_text("; ".join(itens))
        self.entrada.connect("activate", self._enter)
        caixa.append(self.entrada)
        self.aviso = Gtk.Label(label="Enter grava · Esc cancela", xalign=0, wrap=True)
        self.aviso.add_css_class("dim-label")
        caixa.append(self.aviso)
        self.set_child(caixa)

        teclas = Gtk.EventControllerKey()
        teclas.connect("key-pressed", self._tecla)
        self.add_controller(teclas)
        self.connect("close-request", self._ao_fechar)
        self.entrada.grab_focus()
        if itens and self._escolhido() == AUTO:
            self._pedir_palpite()

    def _ao_fechar(self, *_):
        self._fechada = True
        if not self._gravou and self._ao_cancelar is not None:
            self._ao_cancelar()
        return False

    # --- estado ---
    def _escolhido(self) -> str:
        return self._opcoes[self.projeto.get_selected()]

    def _ao_trocar_projeto(self, *_):
        novo = self._escolhido() == NOVO
        self.nome_novo.set_visible(novo)
        if novo:
            self.nome_novo.grab_focus()
        if not self._pensando:
            self.aviso.set_label("Enter grava · Esc cancela")

    # --- Enter ---
    def _enter(self, *_):
        if self._pensando and self._escolhido() == AUTO:
            return  # o palpite ainda vem; escolher o projeto na mão destrava
        itens = separar_itens(self.entrada.get_text())
        if not itens:
            self.entrada.grab_focus()
            return
        escolhido = self._escolhido()
        if escolhido == AUTO:
            self._pedir_palpite()
            return
        if escolhido == NOVO:
            nome = " ".join(self.nome_novo.get_text().split())
            if not nome:
                self.aviso.set_label("Dê um nome ao projeto novo.")
                self.nome_novo.grab_focus()
                return
            self._gravou = True
            self._ao_gravar(nome, True, itens)
        else:
            self._gravou = True
            self._ao_gravar(escolhido, False, itens)
        self.close()

    def _pedir_palpite(self):
        texto = "\n".join(t for t in (self.entrada.get_text(), self._contexto) if t.strip())
        if not texto.strip():
            return
        self._pensando = True
        self.aviso.set_label("Procurando o projeto…")

        def trabalho():
            try:
                nome = self._sugerir(texto)
            except Exception:
                nome = INBOX
            GLib.idle_add(self._palpite_pronto, nome)

        threading.Thread(target=trabalho, daemon=True).start()

    def _palpite_pronto(self, nome: str):
        if self._fechada:
            return GLib.SOURCE_REMOVE
        self._pensando = False
        if self._escolhido() == AUTO:  # a pessoa não escolheu outro enquanto o palpite vinha
            self.projeto.set_selected(self._opcoes.index(nome if nome in self._opcoes else INBOX))
        self.aviso.set_label(f"Vai para {self._escolhido()}. Enter confirma, ou troque acima.")
        self.entrada.grab_focus()
        return GLib.SOURCE_REMOVE

    def _tecla(self, _c, tecla, _cod, _mod):
        if tecla == Gdk.KEY_Escape:
            self.close()
            return True
        return False
