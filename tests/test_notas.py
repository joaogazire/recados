import pytest

from recados.notas import CORES, Repositorio


@pytest.fixture
def repo(tmp_path):
    r = Repositorio(tmp_path / "recados.db")
    yield r
    r.fechar()


def test_cria_nota_amarela_vazia_por_padrao(repo):
    n = repo.criar()
    assert n.id > 0
    assert n.texto == ""
    assert n.cor == "amarelo"
    assert n.recolhida is False and n.sempre_no_topo is False
    assert n.criada == n.editada


def test_cria_com_texto_e_cor(repo):
    n = repo.criar("# oi", cor="azul")
    assert repo.obter(n.id).texto == "# oi"
    assert repo.obter(n.id).cor == "azul"


def test_cor_invalida_e_recusada(repo):
    with pytest.raises(ValueError):
        repo.criar(cor="roxo-neon")
    n = repo.criar()
    with pytest.raises(ValueError):
        repo.atualizar(n.id, cor="xadrez")


def test_seis_cores_com_amarelo(repo):
    assert len(CORES) == 6 and "amarelo" in CORES


def test_atualizar_texto_muda_editada(repo):
    n = repo.criar("a")
    m = repo.atualizar(n.id, texto="b")
    assert m.texto == "b"
    assert m.editada >= n.editada


def test_atualizar_geometria_e_estado(repo):
    n = repo.criar()
    m = repo.atualizar(n.id, x=10, y=20, largura=300, altura=200, recolhida=True, sempre_no_topo=True)
    assert (m.x, m.y, m.largura, m.altura) == (10, 20, 300, 200)
    assert m.recolhida is True and m.sempre_no_topo is True


def test_atualizar_campo_desconhecido_e_recusado(repo):
    n = repo.criar()
    with pytest.raises(ValueError):
        repo.atualizar(n.id, id=99)


def test_atualizar_inexistente_e_keyerror(repo):
    with pytest.raises(KeyError):
        repo.atualizar(999, texto="x")


def test_listar_em_ordem_de_criacao(repo):
    a, b = repo.criar("a"), repo.criar("b")
    assert [n.id for n in repo.listar()] == [a.id, b.id]


def test_apagar_some_da_lista_e_restaurar_volta(repo):
    n = repo.criar("x")
    repo.apagar(n.id)
    assert repo.listar() == []
    assert repo.obter(n.id) is None
    repo.restaurar(n.id)
    assert [m.id for m in repo.listar()] == [n.id]


def test_purgar_remove_apagadas_de_vez(repo):
    n = repo.criar("x")
    repo.apagar(n.id)
    assert repo.purgar_apagadas() == 1
    with pytest.raises(KeyError):
        repo.restaurar(n.id)


def test_persiste_entre_aberturas(tmp_path):
    caminho = tmp_path / "sub" / "r.db"
    r = Repositorio(caminho)
    n = r.criar("fica")
    r.fechar()
    r2 = Repositorio(caminho)
    assert r2.obter(n.id).texto == "fica"
    r2.fechar()


def test_fonte_padrao_sans_e_troca(repo):
    from recados.notas import FONTES
    n = repo.criar()
    assert n.fonte == "sans" and set(FONTES) >= {"sans", "serifa", "mono"}
    assert repo.atualizar(n.id, fonte="mono").fonte == "mono"
    with pytest.raises(ValueError):
        repo.atualizar(n.id, fonte="comic")


def test_banco_antigo_ganha_coluna_fonte(tmp_path):
    import sqlite3
    p = tmp_path / "velho.db"
    db = sqlite3.connect(p)
    db.execute("CREATE TABLE notas (id INTEGER PRIMARY KEY AUTOINCREMENT, texto TEXT NOT NULL DEFAULT '',"
               " cor TEXT NOT NULL DEFAULT 'amarelo', x INTEGER, y INTEGER, largura INTEGER NOT NULL DEFAULT 260,"
               " altura INTEGER NOT NULL DEFAULT 220, recolhida INTEGER NOT NULL DEFAULT 0,"
               " sempre_no_topo INTEGER NOT NULL DEFAULT 0, criada REAL NOT NULL, editada REAL NOT NULL, apagada REAL)")
    db.execute("INSERT INTO notas (texto, criada, editada) VALUES ('oi', 1, 1)")
    db.commit(); db.close()
    r = Repositorio(p)
    assert r.listar()[0].fonte == "sans"
    r.fechar()
