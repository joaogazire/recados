"""Caixinha de captura (Ctrl+N, Super+Alt+N e voz): escolhe o projeto e grava o item no '## Fazer' dele.

Projeto em "automático": o 1º Enter pede o palpite (nome citado no texto ou DeepSeek) e mostra;
o 2º Enter grava. Vários itens de uma vez: separar com ';' ou uma linha por item (Shift+Enter).
O campo é multilinha e cresce com o texto (até um limite, depois rola) para dar para ler tudo.
"""
from __future__ import annotations

import threading
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GLib, GObject, Gtk  # noqa: E402

from recados.projetos import INBOX  # noqa: E402

AUTO = "Projeto automático (palpite)"
NOVO = "+ Novo projeto…"


LARGURA = 460
ALTURA_MAX_CAMPO = 220  # px; passou disso, o campo rola
DICA = "Enter grava · Shift+Enter nova linha · Esc cancela"


def separar_itens(texto: str) -> list[str]:
    return [i.strip() for linha in texto.splitlines() for i in linha.split(";") if i.strip()]


class CampoTexto(Gtk.TextView):
    """TextView com get_text/set_text e o sinal 'activate' (Enter), como um Gtk.Entry multilinha."""

    __gsignals__ = {"activate": (GObject.SignalFlags.RUN_LAST, None, ())}

    def get_text(self) -> str:
        b = self.get_buffer()
        return b.get_text(b.get_start_iter(), b.get_end_iter(), False)

    def set_text(self, texto: str) -> None:
        self.get_buffer().set_text(texto)


class JanelaCaptura(Gtk.Window):
    def __init__(self, projetos: list[str], ao_gravar: Callable[[str, bool, list[str]], None],
                 sugerir: Callable[[str], str], app: Gtk.Application | None = None,
                 itens: list[str] | None = None, contexto: str = "", projeto: str | None = None,
                 ao_cancelar: Callable[[], None] | None = None):
        super().__init__(application=app, title="Post-it: captura", decorated=False, default_width=LARGURA)
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

        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=12, margin_bottom=10,
                        margin_start=12, margin_end=12)
        self.projeto = Gtk.DropDown.new_from_strings(self._opcoes)
        self.projeto.set_tooltip_text("Projeto onde o item vai entrar")
        if projeto in self._opcoes[1:-1]:
            self.projeto.set_selected(self._opcoes.index(projeto))
        self.projeto.connect("notify::selected", self._ao_trocar_projeto)
        caixa.append(self.projeto)

        self.nome_novo = Gtk.Entry(placeholder_text="Nome do projeto novo")
        self.nome_novo.add_css_class("campo")
        self.nome_novo.connect("activate", self._enter)
        self._rev_novo = Gtk.Revealer(transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN,
                                      transition_duration=180, child=self.nome_novo)
        caixa.append(self._rev_novo)

        self.entrada = CampoTexto(wrap_mode=Gtk.WrapMode.WORD_CHAR, accepts_tab=False,
                                  top_margin=8, bottom_margin=8, left_margin=10, right_margin=10)
        self.entrada.add_css_class("campo-texto")
        self.entrada.update_property([Gtk.AccessibleProperty.PLACEHOLDER], ["O que fazer…"])
        if itens:
            self.entrada.set_text("\n".join(itens))
        self.entrada.connect("activate", self._enter)
        self._placeholder = Gtk.Label(label="O que fazer… (uma linha por item)", xalign=0, can_target=False,
                                      margin_start=11, margin_top=8, valign=Gtk.Align.START)
        self._placeholder.add_css_class("placeholder")
        self.entrada.get_buffer().connect("changed", self._ao_mudar_texto)
        tecla_campo = Gtk.EventControllerKey(propagation_phase=Gtk.PropagationPhase.CAPTURE)
        tecla_campo.connect("key-pressed", self._tecla_campo)
        self.entrada.add_controller(tecla_campo)
        rolagem = Gtk.ScrolledWindow(child=self.entrada, propagate_natural_height=True,
                                     max_content_height=ALTURA_MAX_CAMPO,
                                     hscrollbar_policy=Gtk.PolicyType.NEVER)
        rolagem.add_css_class("campo")
        # o TextView calcula as linhas aos poucos; quando a altura real do texto muda, a janela acompanha
        rolagem.get_vadjustment().connect("notify::upper", lambda *_: GLib.idle_add(self._ajustar_altura))
        sobreposta = Gtk.Overlay(child=rolagem)
        sobreposta.add_overlay(self._placeholder)
        caixa.append(sobreposta)

        rodape = Gtk.Box(spacing=6)
        self.girando = Gtk.Spinner()
        rodape.append(self.girando)
        self.aviso = Gtk.Label(label=DICA, xalign=0, wrap=True, hexpand=True)
        self.aviso.add_css_class("dim-label")
        self.aviso.add_css_class("dica")
        rodape.append(self.aviso)
        caixa.append(rodape)

        self.revelador = Gtk.Revealer(transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN,
                                      transition_duration=200, child=caixa)
        self.set_child(self.revelador)
        self.connect("map", lambda *_: self.revelador.set_reveal_child(True))
        self._placeholder.set_visible(not self.entrada.get_text())

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

    def present(self):
        super().present()
        self.revelador.set_reveal_child(True)
        GLib.idle_add(self._ajustar_altura)

    def _ao_mudar_texto(self, *_):
        self._placeholder.set_visible(not self.entrada.get_text())
        GLib.idle_add(self._ajustar_altura)

    def _ajustar_altura(self):
        """Janela do tamanho do conteúdo: cresce quando o texto passa de uma linha e encolhe ao apagar."""
        if self._fechada:
            return GLib.SOURCE_REMOVE
        largura = self.get_width() or LARGURA
        _min, natural, _b1, _b2 = self.revelador.get_child().measure(Gtk.Orientation.VERTICAL, largura)
        if natural > 0 and natural != self.get_height():
            self.set_default_size(largura, natural)
        return GLib.SOURCE_REMOVE

    def _tecla_campo(self, _c, tecla, _cod, mod):
        if tecla not in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_ISO_Enter):
            return False
        if mod & Gdk.ModifierType.SHIFT_MASK:
            return False  # Shift+Enter: o TextView quebra a linha
        self.entrada.emit("activate")
        return True

    # --- estado ---
    def _escolhido(self) -> str:
        return self._opcoes[self.projeto.get_selected()]

    def _ao_trocar_projeto(self, *_):
        novo = self._escolhido() == NOVO
        self._rev_novo.set_reveal_child(novo)
        if novo:
            self.nome_novo.grab_focus()
        if not self._pensando:
            self.aviso.set_label(DICA)

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
        self.girando.start()
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
        self.girando.stop()
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
