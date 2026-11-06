"""Projetos no lugar da Inbox (PLANO-v3): uma nota por projeto, item novo cai em '## Fazer'."""
import pytest

from recados.notas import Repositorio
from recados.projetos import (INBOX, achar_nota, inserir_itens, itens_da_voz, mover_concluido,
                              novo_projeto, sugerir_projeto)

STEAMLOG = """# Steamlog
PC: https://steamlog.local

## Fazer: VM, Fase 1 (~3–5 h) ← primeiro
- [ ] gunicorn atrás do Caddy
- [ ] Segredos criptografados

## Depois: VM, Fase 2
- [ ] Login pela Steam

## Feito
- [x] Esconder demos/apps

#steamlog"""

POSTIT = """# Post-it

## Fazer
- [ ] Separar por projeto
  - [ ] Central filtra por projeto
- [ ] Melhorar a criação de nova nota

## Feito
- [x] App para Fedora

#postit"""


@pytest.fixture
def repo(tmp_path):
    r = Repositorio(tmp_path / "r.db")
    yield r
    r.fechar()




def test_achar_nota_por_nome_e_inbox(repo):
    s = repo.criar(STEAMLOG)
    repo.definir_projeto(s.id, "Steamlog")
    assert achar_nota(repo, "steamlog").id == s.id
    assert achar_nota(repo, INBOX) is None
    i = repo.criar("# Inbox\n- [ ] a")
    assert achar_nota(repo, INBOX).id == i.id


# --- sugestão de projeto ---
def test_sugere_pelo_nome_escrito_diferente_sem_deepseek():
    def nao_chamar(_t, _n):
        raise AssertionError("não devia chamar o DeepSeek")
    fala = "Essa é uma nota de teste para ver se está funcionando uma implementação no Steam Log."
    assert sugerir_projeto(fala, ["Steamlog", "Post-it", "Estante"], nao_chamar) == "Steamlog"
    assert sugerir_projeto("arrumar o post it", ["Steamlog", "Post-it"], nao_chamar) == "Post-it"


def test_deepseek_so_vale_se_for_projeto_conhecido():
    nomes_ = ["Steamlog", "Estante"]
    assert sugerir_projeto("guia de conquistas", nomes_, lambda t, n: "steamlog\n") == "Steamlog"
    assert sugerir_projeto("comprar pão", nomes_, lambda t, n: "Mercado") == INBOX
    assert sugerir_projeto("comprar pão", nomes_, lambda t, n: "Inbox") == INBOX


def test_deepseek_fora_do_ar_vai_para_inbox():
    def falha(_t, _n):
        raise OSError("proxy fora")
    assert sugerir_projeto("comprar pão", ["Steamlog"], falha) == INBOX
    assert sugerir_projeto("   ", ["Steamlog"], falha) == INBOX


# --- onde o item entra ---
def test_item_entra_no_fim_da_primeira_secao_fazer():
    novo = inserir_itens(STEAMLOG, ["guia de conquistas"])
    linhas = novo.split("\n")
    i = linhas.index("- [ ] guia de conquistas")
    assert linhas[i - 1] == "- [ ] Segredos criptografados"
    assert linhas[i + 1] == ""
    assert linhas[i + 2] == "## Depois: VM, Fase 2"
    assert novo.endswith("#steamlog")


def test_varios_itens_e_espacos_limpos():
    novo = inserir_itens(POSTIT, ["  a  b ", "c", "   "])
    assert "- [ ] Melhorar a criação de nova nota\n- [ ] a b\n- [ ] c\n\n## Feito" in novo


def test_inbox_sem_secoes_acrescenta_antes_da_tag():
    assert inserir_itens("# Inbox\n- [ ] a", ["b"]) == "# Inbox\n- [ ] a\n- [ ] b"
    assert inserir_itens("# Inbox\n- [ ] a\n\n#tag", ["b"]) == "# Inbox\n- [ ] a\n- [ ] b\n\n#tag"


def test_nota_com_secoes_mas_sem_fazer_ganha_fazer_antes_da_primeira():
    novo = inserir_itens("# X\n\n## Feito\n- [x] velho", ["novo"])
    assert novo == "# X\n\n## Fazer\n- [ ] novo\n\n## Feito\n- [x] velho"


def test_novo_projeto():
    assert novo_projeto("  Closet  ", ["a"]) == "# Closet\n\n## Fazer\n- [ ] a"


# --- voz ---
def test_itens_da_voz_pega_tarefas_e_nao_a_transcricao():
    md = "# Teste no Steam Log\n- [ ] verificar a categoria\n- ideia solta\n\n---\nTranscrição: blá"
    assert itens_da_voz(md) == ["verificar a categoria", "ideia solta"]


def test_voz_sem_tarefa_vira_um_item_com_o_titulo():
    assert itens_da_voz("# Ideia sobre a estante\n\n---\nTranscrição: x") == ["Ideia sobre a estante"]
    assert itens_da_voz("# Ideia por voz\n\n---\nTranscrição: comprar pão amanhã") == ["comprar pão amanhã"]


# --- [x] desce para Feito ---
def _linha(texto, trecho):
    return next(i for i, l in enumerate(texto.split("\n")) if trecho in l)


def test_marcar_desce_para_o_topo_do_feito():
    marcado = STEAMLOG.replace("- [ ] gunicorn", "- [x] gunicorn")
    novo = mover_concluido(marcado, _linha(marcado, "gunicorn"))
    assert "## Fazer: VM, Fase 1 (~3–5 h) ← primeiro\n- [ ] Segredos criptografados\n\n## Depois" in novo
    assert "## Feito\n- [x] gunicorn atrás do Caddy\n- [x] Esconder demos/apps" in novo


def test_marcar_leva_os_subitens_junto():
    marcado = POSTIT.replace("- [ ] Separar", "- [x] Separar")
    novo = mover_concluido(marcado, _linha(marcado, "Separar"))
    assert novo.startswith("# Post-it\n\n## Fazer\n- [ ] Melhorar a criação de nova nota\n\n## Feito\n"
                           "- [x] Separar por projeto\n  - [ ] Central filtra por projeto\n- [x] App para Fedora")


def test_subitem_marcado_fica_onde_esta():
    marcado = POSTIT.replace("  - [ ] Central", "  - [x] Central")
    assert mover_concluido(marcado, _linha(marcado, "Central")) == marcado


def test_desmarcar_no_feito_volta_para_o_fim_do_fazer():
    desmarcado = STEAMLOG.replace("- [x] Esconder", "- [ ] Esconder")
    novo = mover_concluido(desmarcado, _linha(desmarcado, "Esconder"))
    assert "- [ ] Segredos criptografados\n- [ ] Esconder demos/apps\n\n## Depois" in novo
    assert "## Feito\n\n#steamlog" in novo


def test_sem_feito_cria_antes_da_tag():
    texto = "# X\n\n## Fazer\n- [x] a\n- [ ] b\n\n#x"
    assert mover_concluido(texto, 3) == "# X\n\n## Fazer\n- [ ] b\n\n## Feito\n- [x] a\n\n#x"


def test_nota_sem_fazer_nao_mexe():
    texto = "# Inbox\n- [x] a\n- [ ] b"
    assert mover_concluido(texto, 1) == texto
    assert mover_concluido(STEAMLOG, 99) == STEAMLOG


# --- gravar no banco (sem janela) ---
def test_gravar_no_projeto_existente(repo):
    from recados.projetos import gravar_itens
    s = repo.criar(STEAMLOG)
    repo.definir_projeto(s.id, "Steamlog")
    n = gravar_itens(repo, "steamlog", False, ["guia"])
    assert n.id == s.id and "- [ ] Segredos criptografados\n- [ ] guia\n\n## Depois" in repo.obter(s.id).texto


def test_gravar_na_inbox_cria_azul_e_depois_acrescenta(repo):
    from recados.projetos import gravar_itens
    n = gravar_itens(repo, INBOX, False, ["ligar pro dentista"])
    assert n.texto == "# Inbox\n- [ ] ligar pro dentista" and n.cor == "azul"
    n2 = gravar_itens(repo, INBOX, False, ["comprar pão"])
    assert n2.id == n.id and n2.texto.endswith("- [ ] ligar pro dentista\n- [ ] comprar pão")


def test_gravar_projeto_novo_e_nome_repetido_reaproveita(repo):
    from recados.projetos import gravar_itens
    n = gravar_itens(repo, "Closet", True, ["a"])
    assert n.texto == "# Closet\n\n## Fazer\n- [ ] a"
    assert gravar_itens(repo, "closet", True, ["b"]).id == n.id
    assert gravar_itens(repo, "Sumiu", False, ["c"]).texto == "# Sumiu\n\n## Fazer\n- [ ] c"


def test_gravar_sem_itens_nao_faz_nada(repo):
    from recados.projetos import gravar_itens
    assert gravar_itens(repo, INBOX, False, ["   "]) is None
    assert repo.listar() == []


# --- achados da revisão ---
def test_palpite_local_respeita_palavra_inteira():
    def inbox(_t, _n):
        return "Inbox"
    nomes_ = ["Estante", "Ping", "Rotas", "Steamlog", "Post-it"]
    assert sugerir_projeto("terminar o restante do relatório", nomes_, inbox) == INBOX
    assert sugerir_projeto("ir ao shopping", nomes_, inbox) == INBOX
    assert sugerir_projeto("contar as derrotas", nomes_, inbox) == INBOX
    assert sugerir_projeto("no Steam Log, ver horas", nomes_, inbox) == "Steamlog"
    assert sugerir_projeto("ajustar o ping do vagou", nomes_, inbox) == "Ping"
    assert sugerir_projeto("a cor do post-it", nomes_, inbox) == "Post-it"


def test_sem_projetos_nem_chama_o_deepseek():
    def nao_chamar(_t, _n):
        raise AssertionError("não devia chamar")
    assert sugerir_projeto("qualquer coisa", [], nao_chamar) == INBOX


def test_voz_guarda_topicos_soltos_tambem():
    assert itens_da_voz("# Ideias\n- [ ] fazer a\n- pensar em b\n\n---\nTranscrição: x") == ["fazer a", "pensar em b"]


def test_projeto_novo_com_nome_de_nota_que_ja_existe_reaproveita(repo):
    from recados.projetos import gravar_itens
    velha = repo.criar("# Closet\nideia solta")
    n = gravar_itens(repo, "Closet", True, ["a"])
    assert n.id == velha.id and n.texto == "# Closet\nideia solta\n- [ ] a"
