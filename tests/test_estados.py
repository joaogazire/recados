import pytest

from recados.notas import ESTADOS, Repositorio


@pytest.fixture
def repo(tmp_path):
    r = Repositorio(tmp_path / "r.db")
    yield r
    r.fechar()


def test_estados_e_padrao_ativa(repo):
    assert ESTADOS == ("ativa", "concluida", "cancelada", "arquivada")
    assert repo.criar("x").estado == "ativa"


def test_mudar_estado_tira_da_lista_de_ativas(repo):
    a, b = repo.criar("a"), repo.criar("b")
    n = repo.mudar_estado(a.id, "concluida")
    assert n.estado == "concluida" and n.estado_em is not None
    assert [x.id for x in repo.listar()] == [b.id]
    assert [x.id for x in repo.listar(estado="concluida")] == [a.id]
    assert {x.id for x in repo.listar(estado=None)} == {a.id, b.id}
    repo.mudar_estado(a.id, "ativa")
    assert {x.id for x in repo.listar()} == {a.id, b.id}


def test_estado_invalido(repo):
    n = repo.criar("a")
    with pytest.raises(ValueError):
        repo.mudar_estado(n.id, "sumida")
    with pytest.raises(KeyError):
        repo.mudar_estado(999, "arquivada")


def test_listar_cli_traz_estado(repo):
    from recados.resumo import resumo
    a = repo.criar("a")
    repo.criar("b")
    repo.mudar_estado(a.id, "arquivada")
    estados = {i["id"]: i["estado"] for i in resumo(repo)}
    assert estados[a.id] == "arquivada" and list(estados.values()).count("ativa") == 1
