import json

import pytest

from recados import resumir
from recados.notas import Repositorio


@pytest.fixture
def repo(tmp_path):
    r = Repositorio(tmp_path / "r.db")
    yield r
    r.fechar()


def test_resumo_local_corta_em_5_palavras():
    assert resumir.resumo_local("# Agente de viagens: criar conta no SerpApi") == "Agente de viagens: criar conta"
    assert resumir.resumo_local("") == "(vazia)"


def test_limpar_resposta_do_modelo():
    assert resumir.limpar('"Comprar pão e leite amanhã cedo."\n') == "Comprar pão e leite amanhã"
    assert resumir.limpar("   ") is None


def test_atualizar_guarda_resumo_e_nao_repete_se_texto_igual(repo):
    n = repo.criar("# Lista do mercado\n- [ ] pão\n- [ ] leite")
    chamadas = []

    def falso(texto):
        chamadas.append(texto)
        return "Lista de compras do mercado"

    resumir.atualizar(repo, pedir=falso)
    resumir.atualizar(repo, pedir=falso)
    assert len(chamadas) == 1
    assert repo.obter(n.id).resumo == "Lista de compras do mercado"
    repo.atualizar(n.id, texto="# Farmácia")
    resumir.atualizar(repo, pedir=falso)
    assert len(chamadas) == 2


def test_falha_do_modelo_nao_grava(repo):
    n = repo.criar("# Oi")

    def quebra(texto):
        raise OSError("sem rede")

    resumir.atualizar(repo, pedir=quebra)
    assert repo.obter(n.id).resumo is None


def test_listar_usa_resumo_e_manda_texto_para_busca(repo):
    from recados.resumo import resumo
    n = repo.criar("# Uma primeira linha bem comprida demais para a central\nlinha dois")
    assert resumo(repo)[0]["titulo"] == "Uma primeira linha bem comprida"
    repo.definir_resumo(n.id, "Linha comprida", "x")
    item = resumo(repo)[0]
    assert item["titulo"] == "Linha comprida" and "linha dois" in item["texto"]


def test_chave_lida_do_opencode(tmp_path):
    arq = tmp_path / "auth.json"
    arq.write_text(json.dumps({"deepseek": {"key": "sk-teste"}}))
    assert resumir.chave(arq) == "sk-teste"
    assert resumir.chave(tmp_path / "nao-existe.json") is None
