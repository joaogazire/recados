import json
from datetime import date

import pytest

from recados.fixadas import gravar
from recados.notas import Repositorio
from recados.dia import nota_de_hoje, titulo_do_dia


@pytest.fixture
def repo(tmp_path):
    r = Repositorio(tmp_path / "r.db")
    yield r
    r.fechar()


def test_gravar_fixadas_lista_ids_marcados(repo, tmp_path):
    a, b, _ = repo.criar("a"), repo.criar("b"), repo.criar("c")
    repo.atualizar(a.id, sempre_no_topo=True)
    repo.atualizar(b.id, sempre_no_topo=True)
    repo.apagar(b.id)
    destino = tmp_path / "x" / "fixadas.json"
    gravar(repo, destino)
    assert json.loads(destino.read_text()) == [a.id]


def test_titulo_do_dia():
    assert titulo_do_dia(date(2026, 11, 1)) == "# 01/11/2026 (dom)"
    assert titulo_do_dia(date(2026, 11, 3)) == "# 03/11/2026 (ter)"


def test_nota_de_hoje_acha_pela_primeira_linha(repo):
    hoje = date(2026, 11, 1)
    assert nota_de_hoje(repo, hoje) is None
    repo.criar("# 31/10/2026 (sáb)\nontem")
    n = repo.criar("# 01/11/2026 (dom)\n- [ ] x")
    assert nota_de_hoje(repo, hoje).id == n.id
