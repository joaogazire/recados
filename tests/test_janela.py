import os

import pytest

gi = pytest.importorskip("gi")
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")
from gi.repository import Gtk  # noqa: E402

if not Gtk.init_check():
    pytest.skip("sem display", allow_module_level=True)

from recados.janela import JanelaNota  # noqa: E402
from recados.notas import Repositorio  # noqa: E402


@pytest.fixture
def repo(tmp_path):
    r = Repositorio(tmp_path / "r.db")
    yield r
    r.fechar()


def test_editar_texto_salva_no_repo(repo):
    n = repo.criar("velho")
    j = JanelaNota(repo, n)
    assert j.texto() == "velho"
    j.buffer.set_text("# novo")
    j.salvar_agora()
    assert repo.obter(n.id).texto == "# novo"


def test_trocar_cor_salva_e_muda_classe(repo):
    n = repo.criar()
    j = JanelaNota(repo, n)
    j.definir_cor("azul")
    assert repo.obter(n.id).cor == "azul"
    assert j.has_css_class("cor-azul") and not j.has_css_class("cor-amarelo")


def test_recolher_esconde_editor_e_salva(repo):
    n = repo.criar()
    j = JanelaNota(repo, n)
    j.alternar_recolhida()
    assert repo.obter(n.id).recolhida is True
    assert not j.rolagem.get_visible()
    j.alternar_recolhida()
    assert repo.obter(n.id).recolhida is False
    assert j.rolagem.get_visible()


def test_abre_recolhida_se_salva_assim(repo):
    n = repo.atualizar(repo.criar().id, recolhida=True)
    assert not JanelaNota(repo, n).rolagem.get_visible()


def test_realce_aplica_tag_negrito(repo):
    n = repo.criar("a **b**")
    j = JanelaNota(repo, n)
    it = j.buffer.get_iter_at_offset(3)
    assert any(t.props.name == "negrito" for t in it.get_tags())


def test_modo_leitura_mostra_checkbox_e_clicar_salva(repo):
    n = repo.criar("# T\n- [ ] pão")
    j = JanelaNota(repo, n)
    j.alternar_leitura()
    assert j.em_leitura and not j.rolagem.get_visible() and j.leitura.get_visible()
    caixas = j.caixas_leitura()
    assert len(caixas) == 1 and not caixas[0].get_active()
    caixas[0].set_active(True)
    assert repo.obter(n.id).texto == "# T\n- [x] pão"
    assert j.texto() == "# T\n- [x] pão"
    j.alternar_leitura()
    assert not j.em_leitura and j.rolagem.get_visible()


def test_clicar_caixa_no_editor_alterna(repo):
    n = repo.criar("- [ ] a")
    j = JanelaNota(repo, n)
    assert j.clicar_offset(3) is True
    j.salvar_agora()
    assert repo.obter(n.id).texto == "- [x] a"
    assert j.clicar_offset(6) is False


def test_apagar_com_desfazer(repo):
    n = repo.criar("x")
    j = JanelaNota(repo, n)
    j.apagar()
    assert repo.obter(n.id) is None and j.apagando
    j.desfazer_apagar()
    assert repo.obter(n.id).texto == "x" and not j.apagando


def test_trocar_fonte_salva_e_muda_classe(repo):
    n = repo.criar()
    j = JanelaNota(repo, n)
    assert j.has_css_class("fonte-sans")
    j.definir_fonte("serifa")
    assert repo.obter(n.id).fonte == "serifa"
    assert j.has_css_class("fonte-serifa") and not j.has_css_class("fonte-sans")


def test_preset_de_tamanho_salva_e_redimensiona(repo):
    from recados.janela import TAMANHOS
    n = repo.criar()
    j = JanelaNota(repo, n)
    larg, alt = TAMANHOS["G"]
    j.definir_tamanho("G")
    assert (repo.obter(n.id).largura, repo.obter(n.id).altura) == (larg, alt)
    assert j.get_default_size() == (larg, alt)
    assert len(TAMANHOS) >= 3
