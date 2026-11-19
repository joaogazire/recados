"""Caixinha de captura mais bonita: campo multilinha que cresce, animações e Enter/Shift+Enter."""
import pytest

gi = pytest.importorskip("gi")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk  # noqa: E402

if not Gtk.init_check():
    pytest.skip("sem display", allow_module_level=True)

from recados.captura_janela import JanelaCaptura, separar_itens  # noqa: E402


def caixa(gravados=None, **kw):
    gravados = [] if gravados is None else gravados
    return JanelaCaptura(["Steamlog"], lambda *a: gravados.append(a), lambda t: "Steamlog", **kw)


def test_campo_e_multilinha_com_quebra_automatica():
    c = caixa()
    assert isinstance(c.entrada, Gtk.TextView)
    assert c.entrada.get_wrap_mode() == Gtk.WrapMode.WORD_CHAR


def test_campo_cresce_com_o_texto_ate_um_limite_e_depois_rola():
    c = caixa()
    rolagem = c.entrada.get_parent()
    assert isinstance(rolagem, Gtk.ScrolledWindow)
    assert rolagem.get_propagate_natural_height() is True
    assert 120 <= rolagem.get_max_content_height() <= 400


def test_texto_de_varias_linhas_continua_legivel_pelo_get_text():
    c = caixa()
    c.entrada.set_text("um item bem comprido que passa de uma linha")
    assert c.entrada.get_text() == "um item bem comprido que passa de uma linha"


def test_enter_grava_e_shift_enter_quebra_linha():
    gravados = []
    c = caixa(gravados)
    c.projeto.set_selected(1)
    c.entrada.set_text("a")
    assert c._tecla_campo(None, Gdk.KEY_Return, 0, Gdk.ModifierType.SHIFT_MASK) is False  # deixa o TextView quebrar
    assert gravados == []
    assert c._tecla_campo(None, Gdk.KEY_Return, 0, 0) is True
    assert gravados == [("Steamlog", False, ["a"])]


def test_enter_do_teclado_numerico_tambem_grava():
    gravados = []
    c = caixa(gravados)
    c.projeto.set_selected(1)
    c.entrada.set_text("b")
    assert c._tecla_campo(None, Gdk.KEY_KP_Enter, 0, 0) is True
    assert gravados == [("Steamlog", False, ["b"])]


def test_cada_linha_vira_um_item():
    assert separar_itens("ler mais\ncatalogar; doar\n\n") == ["ler mais", "catalogar", "doar"]


def test_conteudo_entra_com_animacao():
    c = caixa()
    assert isinstance(c.revelador, Gtk.Revealer)
    assert c.revelador.get_transition_type() in (Gtk.RevealerTransitionType.SLIDE_DOWN,
                                                 Gtk.RevealerTransitionType.CROSSFADE)
    assert c.revelador.get_reveal_child() is False
    c.present()
    assert c.revelador.get_reveal_child() is True


def test_nome_do_projeto_novo_desliza_em_vez_de_pular():
    c = caixa()
    rev = c.nome_novo.get_parent()
    assert isinstance(rev, Gtk.Revealer)
    c.projeto.set_selected(len(c._opcoes) - 1)  # + Novo projeto…
    assert rev.get_reveal_child() is True
    c.projeto.set_selected(1)
    assert rev.get_reveal_child() is False


def test_procurando_projeto_mostra_spinner():
    c = caixa()
    c.entrada.set_text("algo")
    c._pedir_palpite()
    assert c.girando.get_spinning() is True
    c._palpite_pronto("Steamlog")
    assert c.girando.get_spinning() is False
