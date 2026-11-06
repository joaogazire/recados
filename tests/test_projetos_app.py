"""Integração do PLANO-v3 no app: Ctrl+N/captura/voz abrem a caixinha com projeto; [x] desce para Feito."""
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
from recados.projetos import INBOX  # noqa: E402

STEAMLOG = "# Steamlog\n\n## Fazer\n- [ ] a\n\n## Feito\n- [x] velho\n\n#steamlog"


@pytest.fixture
def repo(tmp_path):
    r = Repositorio(tmp_path / "r.db")
    yield r
    r.fechar()


@pytest.fixture
def app(repo, monkeypatch, tmp_path):
    from recados import app as modapp
    monkeypatch.setenv("RECADOS_PREFERENCIAS", str(tmp_path / "p.json"))
    a = modapp.App()
    a.repo = repo
    monkeypatch.setattr(a, "_notas_abertas", lambda: {})
    monkeypatch.setattr(a, "send_notification", lambda *a_: None)
    caixas = []

    class Falsa:
        def __init__(self, projetos, ao_gravar, sugerir, app=None, itens=None, contexto="", projeto=None,
                     ao_cancelar=None):
            caixas.append(dict(projetos=projetos, ao_gravar=ao_gravar, sugerir=sugerir, itens=itens,
                               contexto=contexto, projeto=projeto, ao_cancelar=ao_cancelar))

        def present(self):
            pass

    monkeypatch.setattr(modapp, "JanelaCaptura", Falsa)
    a.caixas = caixas
    return a


def test_nova_nota_abre_a_caixinha_com_os_projetos(app, repo):
    repo.criar(STEAMLOG)
    repo.criar("# Inbox\n- [ ] x")
    app.nova_nota()
    assert app.caixas[-1]["projetos"] == ["Steamlog"] and app.caixas[-1]["itens"] is None
    assert repo.listar()[-1].texto.startswith("# Inbox")  # nada criado só por abrir


def test_nova_nota_de_dentro_de_um_projeto_ja_vem_nele(app, repo, monkeypatch):
    s = repo.criar(STEAMLOG)
    j = JanelaNota(repo, s)
    monkeypatch.setattr(app, "get_active_window", lambda: j)
    app.nova_nota()
    assert app.caixas[-1]["projeto"] == "Steamlog"


def test_captura_rapida_abre_a_mesma_caixinha(app, repo):
    repo.criar(STEAMLOG)
    app.mostrar_captura()
    assert app.caixas[-1]["projetos"] == ["Steamlog"]


def test_gravar_pela_caixinha_entra_no_fazer(app, repo):
    s = repo.criar(STEAMLOG)
    app.nova_nota()
    app.caixas[-1]["ao_gravar"]("Steamlog", False, ["guia"])
    assert "- [ ] a\n- [ ] guia\n\n## Feito" in repo.obter(s.id).texto


def test_gravar_com_o_projeto_aberto_passa_pela_janela(app, repo, monkeypatch):
    s = repo.criar(STEAMLOG)
    j = JanelaNota(repo, s)
    monkeypatch.setattr(app, "_notas_abertas", lambda: {s.id: j})
    app.capturar("Steamlog", False, ["guia"])
    assert "- [ ] a\n- [ ] guia" in j.texto()
    assert "- [ ] a\n- [ ] guia" in repo.obter(s.id).texto


def test_projeto_novo_abre_a_nota_dele(app, repo, monkeypatch):
    abertas = []
    monkeypatch.setattr(app, "abrir_nota", lambda i: abertas.append(i) or True)
    app.capturar("Closet", True, ["site"])
    n = repo.listar()[0]
    assert n.texto == "# Closet\n\n## Fazer\n- [ ] site" and abertas == [n.id]


def test_palpite_da_caixinha_usa_os_projetos_do_banco(app, repo, monkeypatch):
    from recados import projetos
    repo.criar(STEAMLOG)
    monkeypatch.setattr(projetos, "pedir_deepseek", lambda t, n: "Inbox")
    app.nova_nota()
    assert app.caixas[-1]["sugerir"]("teste no Steam Log") == "Steamlog"


def test_voz_abre_a_caixinha_com_os_itens_e_a_fala(app, repo):
    repo.criar(STEAMLOG)
    md = "# Teste no Steam Log\n- [ ] ver a categoria @amanhã 10h\n\n---\nTranscrição: teste no Steam Log"
    app._nota_de_voz(md)
    c = app.caixas[-1]
    assert len(c["itens"]) == 1 and c["itens"][0].startswith("ver a categoria @")
    assert "@amanhã" not in c["itens"][0] and "10h" in c["itens"][0]  # data já fixada
    assert "Steam Log" in c["contexto"]
    assert repo.listar() == [repo.listar()[0]]  # não criou nota verde solta


def test_marcar_no_modo_leitura_desce_para_feito(repo):
    s = repo.criar(STEAMLOG)
    j = JanelaNota(repo, s, ler=True)
    j._ao_marcar(Gtk.CheckButton(active=True, child=Gtk.Label()), 3)
    assert repo.obter(s.id).texto == "# Steamlog\n\n## Fazer\n\n## Feito\n- [x] a\n- [x] velho\n\n#steamlog"


def test_clicar_caixa_no_editor_tambem_desce(repo):
    s = repo.criar(STEAMLOG)
    j = JanelaNota(repo, s, ler=False)
    off = len("# Steamlog\n\n## Fazer\n- [")
    assert j.clicar_offset(off) is True
    j.salvar_agora()
    assert "## Feito\n- [x] a\n- [x] velho" in repo.obter(s.id).texto


def test_caixinha_de_verdade_dois_enters_no_automatico(repo):
    from recados.captura_janela import AUTO, JanelaCaptura
    gravados = []
    c = JanelaCaptura(["Steamlog", "Estante"], lambda *a: gravados.append(a), lambda t: "Estante")
    assert c._escolhido() == AUTO
    c.entrada.set_text("ler mais; catalogar")
    c._palpite_pronto("Estante")  # o 1º Enter pediria o palpite numa thread; aqui chega direto
    assert c._escolhido() == "Estante" and gravados == []
    c.entrada.emit("activate")
    assert gravados == [("Estante", False, ["ler mais", "catalogar"])]


def test_caixinha_de_verdade_escolha_manual_grava_no_1o_enter(repo):
    from recados.captura_janela import JanelaCaptura
    gravados = []
    c = JanelaCaptura(["Steamlog"], lambda *a: gravados.append(a), lambda t: "Steamlog")
    c.projeto.set_selected(2)  # Inbox
    c.entrada.set_text("comprar pão")
    c.entrada.emit("activate")
    assert gravados == [(INBOX, False, ["comprar pão"])]


def test_caixinha_escolha_manual_grava_mesmo_com_palpite_pendente(repo):
    from recados.captura_janela import JanelaCaptura
    gravados = []
    c = JanelaCaptura(["Steamlog"], lambda *a: gravados.append(a), lambda t: "Steamlog")
    c.entrada.set_text("x")
    c._pensando = True  # palpite ainda vindo do DeepSeek
    c.projeto.set_selected(1)  # a pessoa escolheu Steamlog na mão
    c.entrada.emit("activate")
    assert gravados == [("Steamlog", False, ["x"])]


def test_caixinha_vem_na_inbox_quando_aberta_da_inbox(repo):
    from recados.captura_janela import JanelaCaptura
    c = JanelaCaptura(["Steamlog"], lambda *a: None, lambda t: "Steamlog", projeto=INBOX)
    assert c._escolhido() == INBOX


def test_caixinha_cancelada_avisa(repo):
    from recados.captura_janela import JanelaCaptura
    canceladas = []
    c = JanelaCaptura(["Steamlog"], lambda *a: None, lambda t: "Steamlog", ao_cancelar=lambda: canceladas.append(1))
    c.present()
    c.close()
    assert canceladas == [1]
    gravou = JanelaCaptura(["Steamlog"], lambda *a: None, lambda t: "", ao_cancelar=lambda: canceladas.append(2))
    gravou.present()
    gravou.projeto.set_selected(1)
    gravou.entrada.set_text("x")
    gravou.entrada.emit("activate")
    assert canceladas == [1]  # gravou: não é cancelamento


def test_voz_cancelada_nao_perde_a_ideia_vai_para_inbox(app, repo):
    app._nota_de_voz("# Ideia\n- [ ] ligar pro João\n\n---\nTranscrição: ligar pro João")
    app.caixas[-1]["ao_cancelar"]()
    assert repo.listar()[0].texto == "# Inbox\n- [ ] ligar pro João"


def test_marcar_no_editor_nao_joga_o_cursor_pro_fim(repo):
    s = repo.criar(STEAMLOG)
    j = JanelaNota(repo, s, ler=False)
    off = len("# Steamlog\n\n## Fazer\n- [")
    j.clicar_offset(off)
    assert j.buffer.get_iter_at_mark(j.buffer.get_insert()).get_offset() == off
