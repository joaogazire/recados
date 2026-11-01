import pytest

from recados.migrar import migrar, nota_de_item
from recados.notas import Repositorio

IDEIA = {"id": 1, "titulo": "App de livros", "descricao": "notas e estante", "concluida": 0,
         "tipo": "ideia", "criada_em": "2026-11-01T17:56:41Z", "tags": ["app", "livros"]}
TAREFA = {"id": 2, "titulo": "Testar viagem", "descricao": "linha 1\nlinha 2", "concluida": 1,
          "tipo": "tarefa", "criada_em": "2026-10-29T04:18:15Z", "tags": []}


def test_ideia_vira_nota_amarela_com_titulo_e_tags():
    assert nota_de_item(IDEIA) == ("# App de livros\n\nnotas e estante\n\n#app #livros", "amarelo")


def test_tarefa_vira_checklist_azul_marcada_se_concluida():
    assert nota_de_item(TAREFA) == ("- [x] Testar viagem\n\nlinha 1\nlinha 2", "azul")
    aberta = dict(TAREFA, concluida=0, descricao="", tags=["x"])
    assert nota_de_item(aberta) == ("- [ ] Testar viagem\n\n#x", "azul")


def test_migrar_cria_em_ordem_antiga_primeiro_e_nao_repete(tmp_path):
    repo = Repositorio(tmp_path / "r.db")
    marca = tmp_path / "migrado"
    assert migrar(repo, [IDEIA, TAREFA], marca) == 2
    assert [n.texto.splitlines()[0] for n in repo.listar()] == ["- [x] Testar viagem", "# App de livros"]
    assert marca.exists()
    assert migrar(repo, [IDEIA, TAREFA], marca) == 0
    assert len(repo.listar()) == 2
    repo.fechar()
