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
    j = JanelaNota(repo, n)  # nota com texto já abre em leitura
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


def test_app_abrir_nota_por_id(repo, monkeypatch):
    from recados.app import App
    a = App()
    a.repo = repo
    n = repo.criar("x")
    abertas = []
    monkeypatch.setattr("recados.app.JanelaNota", lambda r, nota, app, ler=True: type("J", (), {
        "present": lambda s: abertas.append(nota.id), "nota": nota})())
    monkeypatch.setattr(a, "get_windows", lambda: [])
    assert a.abrir_nota(n.id) is True
    assert abertas == [n.id]
    assert a.abrir_nota(999) is False


def test_nota_com_texto_abre_em_leitura_e_vazia_em_edicao(repo):
    cheia = JanelaNota(repo, repo.criar("# Oi\n- [ ] x"))
    assert cheia.em_leitura and cheia.leitura.get_visible() and not cheia.rolagem.get_visible()
    assert len(cheia.caixas_leitura()) == 1
    vazia = JanelaNota(repo, repo.criar())
    assert not vazia.em_leitura and vazia.rolagem.get_visible()


def test_preferencia_abrir_em_edicao(repo):
    j = JanelaNota(repo, repo.criar("# Oi"), ler=False)
    assert not j.em_leitura and j.rolagem.get_visible()


def test_nova_nota_usa_fonte_e_tamanho_das_preferencias(repo, tmp_path, monkeypatch):
    from recados import app as modapp
    from recados.janela import TAMANHOS
    from recados.preferencias import PADRAO, salvar
    pref = tmp_path / "p.json"
    salvar(pref, {**PADRAO, "fonte": "serifa", "tamanho": "G"})
    monkeypatch.setenv("RECADOS_PREFERENCIAS", str(pref))
    a = modapp.App()
    a.repo = repo
    monkeypatch.setattr(a, "_notas_abertas", lambda: {0: object()})
    recebidas = []
    monkeypatch.setattr(modapp, "JanelaNota", lambda r, nota, app, ler=True: (recebidas.append(nota), type("J", (), {
        "present": lambda s: None, "editor": type("E", (), {"grab_focus": lambda s: None})()})())[1])
    a.nova_nota()
    n = recebidas[-1]
    assert n.id is None and repo.listar() == []  # rascunho: só vai pro banco quando tiver texto
    assert n.fonte == "serifa" and (n.largura, n.altura) == TAMANHOS["G"]


def test_shutdown_ignora_janela_que_nao_e_nota(repo, monkeypatch):
    from recados.app import App
    a = App()
    a.repo = repo
    monkeypatch.setattr(a, "get_windows", lambda: [Gtk.Window()])
    monkeypatch.setattr("recados.app.Adw.Application.do_shutdown", lambda s: None)
    a.do_shutdown()


def _rascunho(**campos):
    from recados.notas import rascunho
    return rascunho(**campos)


def test_salva_a_cada_5_segundos():
    from recados.janela import ATRASO_SALVAR_MS
    assert ATRASO_SALVAR_MS == 5000


def test_rascunho_vazio_fechado_nao_vai_pro_banco(repo):
    j = JanelaNota(repo, _rascunho())
    j.definir_cor("rosa")
    j.salvar_agora()
    j.close()
    assert repo.listar() == []


def test_rascunho_com_texto_vira_nota_com_as_escolhas(repo):
    from recados.notas import TAMANHOS
    j = JanelaNota(repo, _rascunho(fonte="mono"))
    j.definir_cor("verde")
    j.definir_tamanho("G")
    j.buffer.set_text("comprar pão")
    j.salvar_agora()
    [n] = repo.listar()
    assert (n.texto, n.cor, n.fonte, (n.largura, n.altura)) == ("comprar pão", "verde", "mono", TAMANHOS["G"])
    assert j.nota.id == n.id and j.get_title() == f"Post-it {n.id}"


def test_apagar_rascunho_so_fecha(repo):
    j = JanelaNota(repo, _rascunho())
    j.apagar()
    assert repo.listar() == []


def test_alfinete_fixa_e_grava_arquivo(repo, tmp_path, monkeypatch):
    import json
    destino = tmp_path / "fixadas.json"
    monkeypatch.setenv("RECADOS_FIXADAS", str(destino))
    n = repo.criar("oi")
    j = JanelaNota(repo, n)
    j.alternar_fixada()
    assert repo.obter(n.id).sempre_no_topo is True and j.has_css_class("fixada")
    assert json.loads(destino.read_text()) == [n.id]
    j.alternar_fixada()
    assert json.loads(destino.read_text()) == []


def test_rascunho_com_modelo_so_salva_se_mudar(repo):
    j = JanelaNota(repo, _rascunho())
    j.modelo = "# 01/11/2026 (dom)\n- [ ] "
    j.buffer.set_text(j.modelo)
    j.salvar_agora()
    assert repo.listar() == []
    j.buffer.set_text(j.modelo + "pão")
    j.salvar_agora()
    assert repo.listar()[0].texto.endswith("pão")


def test_apagar_fixada_tira_do_arquivo(repo, tmp_path, monkeypatch):
    import json
    destino = tmp_path / "fixadas.json"
    monkeypatch.setenv("RECADOS_FIXADAS", str(destino))
    j = JanelaNota(repo, repo.criar("oi"))
    j.alternar_fixada()
    j.apagar()
    assert json.loads(destino.read_text()) == []
    j.desfazer_apagar()
    assert json.loads(destino.read_text()) == [j.nota.id]


def test_nota_do_dia_nao_abre_dois_rascunhos(repo, monkeypatch):
    from recados.app import App
    a = App()
    a.repo = repo
    monkeypatch.setattr(a, "_notas_abertas", lambda: {})
    a.nota_do_dia()
    primeiro = a._rascunho_dia
    a.nota_do_dia()
    assert a._rascunho_dia is primeiro


def test_captura_com_inbox_aberta_atualiza_a_janela(repo, monkeypatch):
    from recados.app import App
    from recados.captura import capturar
    inbox = capturar(repo, "a")
    j = JanelaNota(repo, inbox)
    a = App()
    a.repo = repo
    monkeypatch.setattr(a, "_notas_abertas", lambda: {inbox.id: j})
    a.capturar("b")
    assert j.texto().endswith("- [ ] a\n- [ ] b")
    assert repo.obter(inbox.id).texto.endswith("- [ ] a\n- [ ] b")


def test_janela_de_captura_enter_grava(repo):
    from recados.captura_janela import JanelaCaptura
    recebidos = []
    c = JanelaCaptura(recebidos.append)
    c.entrada.set_text("ideia rápida")
    c.entrada.emit("activate")
    assert recebidos == ["ideia rápida"]


def test_concluir_nota_fecha_e_muda_estado(repo):
    n = repo.criar("- [x] a")
    j = JanelaNota(repo, n)
    j.definir_estado("concluida")
    assert repo.obter(n.id).estado == "concluida"


def test_aviso_tudo_feito(repo):
    j = JanelaNota(repo, repo.criar("# L\n- [ ] a\n- [x] b"), ler=False)
    assert not j.aviso_concluir.get_visible()
    j.buffer.set_text("# L\n- [x] a\n- [x] b")
    assert j.aviso_concluir.get_visible()
    j.buffer.set_text("sem caixas")
    assert not j.aviso_concluir.get_visible()


def test_reabrir_volta_para_ativa(repo, monkeypatch):
    from recados.app import App
    n = repo.criar("a")
    repo.mudar_estado(n.id, "cancelada")
    a = App()
    a.repo = repo
    monkeypatch.setattr(a, "_notas_abertas", lambda: {})
    monkeypatch.setattr(a, "_janela", lambda nota: type("J", (), {"present": lambda s: None})())
    assert a.reabrir_nota(n.id) is True
    assert repo.obter(n.id).estado == "ativa"
