"""Melhorias de 02/11: contador de tarefas, pendências na nota do dia, lixeira, lembrete por voz."""
import time
from datetime import date, datetime

import pytest

from recados.notas import Repositorio


@pytest.fixture
def repo(tmp_path):
    r = Repositorio(tmp_path / "r.db")
    yield r
    r.fechar()


# --- contador de tarefas ---
def test_contar_tarefas():
    from recados.markdown import contar_tarefas
    assert contar_tarefas("# t\n- [ ] a\n- [x] b\n  * [X] c\ntexto") == (2, 3)
    assert contar_tarefas("sem tarefas") == (0, 0)


# --- nota do dia herda pendências ---
def test_pendencias_so_as_abertas():
    from recados.dia import pendencias
    texto = "# 01/11/2026 (dom)\n- [ ] a\n- [x] b\n- [ ]   \n  - [ ] c\nsolto"
    assert pendencias(texto) == ["- [ ] a", "  - [ ] c"]


def test_nota_anterior_pega_o_dia_mais_recente_antes_de_hoje(repo):
    from recados.dia import nota_anterior
    repo.criar("# 30/10/2026 (sex)\n- [ ] velha")
    ontem = repo.criar("# 01/11/2026 (dom)\n- [ ] x")
    repo.criar("# 02/11/2026 (seg)\nhoje")
    repo.criar("# lista qualquer")
    assert nota_anterior(repo, date(2026, 11, 2)).id == ontem.id
    concluida = repo.mudar_estado(ontem.id, "concluida")
    assert nota_anterior(repo, date(2026, 11, 2)).id != concluida.id


# --- lixeira ---
def test_lixeira_lista_apagadas_e_purga_so_as_antigas(repo):
    velha, nova, viva = repo.criar("velha"), repo.criar("nova"), repo.criar("viva")
    repo.apagar(velha.id)
    repo.apagar(nova.id)
    repo._db.execute("UPDATE notas SET apagada = ? WHERE id = ?", (time.time() - 31 * 86400, velha.id))
    repo._db.commit()
    assert [n.id for n in repo.listar_apagadas()] == [velha.id, nova.id]
    assert repo.purgar_apagadas(dias=30) == 1
    assert [n.id for n in repo.listar_apagadas()] == [nova.id]
    assert [n.id for n in repo.listar()] == [viva.id]


def test_resumo_mostra_lixeira(repo):
    from recados.resumo import resumo
    n = repo.criar("# apagada")
    repo.apagar(n.id)
    itens = resumo(repo)
    assert [(i["id"], i["estado"]) for i in itens] == [(n.id, "lixeira")]


# --- lembrete por voz ---
def test_prompt_da_voz_ensina_lembrete():
    from recados import voz
    assert "@amanhã" in voz._PROMPT and "10h" in voz._PROMPT


def test_nota_de_voz_fixa_data_relativa(repo, monkeypatch):
    gi = pytest.importorskip("gi")
    from recados import app as modapp
    a = modapp.App()
    a.repo = repo
    monkeypatch.setattr(a, "abrir_nota", lambda i: True)
    a._nota_de_voz("# Pão\n- [ ] comprar pão @amanhã 10h")
    texto = repo.listar()[0].texto
    assert "@amanhã" not in texto and "10h" in texto
