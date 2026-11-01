import pytest

from recados.captura import TITULO_INBOX, acrescentar_item, capturar
from recados.notas import Repositorio


@pytest.fixture
def repo(tmp_path):
    r = Repositorio(tmp_path / "r.db")
    yield r
    r.fechar()


def test_acrescentar_item_no_fim():
    assert acrescentar_item("# Inbox\n- [ ] a", "b") == "# Inbox\n- [ ] a\n- [ ] b"
    assert acrescentar_item("# Inbox\n- [ ] a\n\n", "b") == "# Inbox\n- [ ] a\n- [ ] b"
    assert acrescentar_item("# Inbox", "  linha\ncom quebra  ") == "# Inbox\n- [ ] linha com quebra"


def test_capturar_cria_inbox_azul_na_primeira_vez(repo):
    n = capturar(repo, "ligar pro dentista")
    assert n.texto == f"{TITULO_INBOX}\n- [ ] ligar pro dentista" and n.cor == "azul"
    n2 = capturar(repo, "comprar pão")
    assert n2.id == n.id and n2.texto.endswith("- [ ] ligar pro dentista\n- [ ] comprar pão")


def test_capturar_texto_vazio_nao_faz_nada(repo):
    assert capturar(repo, "   ") is None
    assert repo.listar() == []
