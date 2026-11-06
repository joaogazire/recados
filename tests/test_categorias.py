"""Um projeto tem várias notas: cada nota guarda o seu projeto; o DeepSeek classifica as novas."""
import time

import pytest

from recados.notas import Repositorio
from recados.projetos import INBOX, achar_nota, classificar, gravar_itens, nomes

STEAMLOG = "# Steamlog\n\n## Fazer\n- [ ] a\n\n## Feito\n- [x] b"


@pytest.fixture
def repo(tmp_path):
    r = Repositorio(tmp_path / "r.db")
    yield r
    r.fechar()


def _velha(repo, texto):
    """Nota editada há mais de 30 s (o classificador espera a pessoa parar de digitar)."""
    n = repo.criar(texto)
    repo._db.execute("UPDATE notas SET editada = ? WHERE id = ?", (time.time() - 120, n.id))
    repo._db.commit()
    return repo.obter(n.id)


def test_coluna_projeto_e_manual(repo):
    n = repo.criar("# x")
    assert n.projeto is None and n.projeto_manual is False
    repo.definir_projeto(n.id, "Steamlog", manual=True)
    m = repo.obter(n.id)
    assert m.projeto == "Steamlog" and m.projeto_manual is True and m.editada == n.editada
    with pytest.raises(ValueError):
        repo.definir_projeto(n.id, "   ")


def test_nomes_vem_da_coluna_sem_inbox_e_sem_lixeira(repo):
    a, b, c, d = (repo.criar(t) for t in ("# a", "# b", "# c", "# d"))
    repo.definir_projeto(a.id, "Steamlog")
    repo.definir_projeto(b.id, "Steamlog")
    repo.definir_projeto(c.id, INBOX)
    repo.definir_projeto(d.id, "Velho")
    repo.apagar(d.id)
    arq = repo.criar("# e")
    repo.definir_projeto(arq.id, "Vagou")
    repo.mudar_estado(arq.id, "cancelada")
    assert sorted(nomes(repo)) == ["Steamlog", "Vagou"]


def test_achar_nota_prefere_a_que_tem_fazer(repo):
    solta = repo.criar("# ideia solta")
    principal = repo.criar(STEAMLOG)
    for n in (solta, principal):
        repo.definir_projeto(n.id, "Steamlog")
    assert achar_nota(repo, "steamlog").id == principal.id


def test_gravar_itens_marca_o_projeto(repo):
    n = gravar_itens(repo, "Closet", True, ["a"])
    assert n.projeto == "Closet" and n.projeto_manual is True
    i = gravar_itens(repo, INBOX, False, ["b"])
    assert i.projeto == INBOX and i.projeto_manual is True  # a nota Inbox não é reclassificada


def test_classificar_nota_nova_com_contexto_dos_projetos(repo):
    s = _velha(repo, STEAMLOG)
    repo.definir_projeto(s.id, "Steamlog")
    e = _velha(repo, "# Estante\n\n## Fazer\n- [ ] foto")
    repo.definir_projeto(e.id, "Estante")
    nova = _velha(repo, "# Achievements\n- [ ] guia do Hollow Knight")
    perguntas = []

    def pedir(texto, nomes_, descricoes):
        perguntas.append((texto, nomes_, descricoes))
        return "Steamlog"

    assert classificar(repo, pedir) == 1
    assert repo.obter(nova.id).projeto == "Steamlog"
    texto, nomes_, descricoes = perguntas[0]
    assert "Hollow Knight" in texto and sorted(nomes_) == ["Estante", "Steamlog"]
    assert "Steamlog" in descricoes["Steamlog"]  # títulos das notas do projeto ajudam o DeepSeek


def test_classificar_nao_mexe_em_quem_ja_tem_projeto_manual_ou_esta_sendo_digitada(repo):
    s = _velha(repo, STEAMLOG)
    repo.definir_projeto(s.id, "Steamlog")
    manual = _velha(repo, "# x")
    repo.definir_projeto(manual.id, INBOX, manual=True)
    recente = repo.criar("# digitando agora sobre Steamlog")
    vazia = _velha(repo, "# ")

    def pedir(*_):
        raise AssertionError("não devia perguntar")

    assert classificar(repo, pedir) == 0
    assert repo.obter(recente.id).projeto is None and repo.obter(vazia.id).projeto is None


def test_inbox_e_reclassificada_quando_o_texto_muda_e_nao_repete_a_pergunta(repo):
    s = _velha(repo, STEAMLOG)
    repo.definir_projeto(s.id, "Steamlog")
    n = _velha(repo, "# comprar pão")
    respostas = iter(["Inbox"])
    assert classificar(repo, lambda *_: next(respostas)) == 1
    assert repo.obter(n.id).projeto == INBOX
    assert classificar(repo, lambda *_: (_ for _ in ()).throw(AssertionError("repetiu"))) == 0
    repo.atualizar(n.id, texto="# comprar pão\n- [ ] e ver o Steamlog")
    repo._db.execute("UPDATE notas SET editada = ? WHERE id = ?", (time.time() - 120, n.id))
    repo._db.commit()
    assert classificar(repo, lambda *_: "Inbox") == 1  # nome citado ganha antes do DeepSeek
    assert repo.obter(n.id).projeto == "Steamlog"


def test_deepseek_fora_do_ar_nao_marca_nada(repo):
    s = _velha(repo, STEAMLOG)
    repo.definir_projeto(s.id, "Steamlog")
    n = _velha(repo, "# comprar pão")

    def falha(*_):
        raise OSError("proxy fora")

    assert classificar(repo, falha) == 0
    assert repo.obter(n.id).projeto is None  # tenta de novo na próxima rodada


def test_resumo_da_central_leva_o_projeto(repo):
    from recados.resumo import resumo
    a = repo.criar("# a")
    repo.definir_projeto(a.id, "Steamlog")
    repo.criar("# b")
    assert [r["projeto"] for r in resumo(repo)] == ["Steamlog", INBOX]


# --- achados da revisão ---
def test_migracao_poe_projeto_nas_notas_que_ja_eram_projeto(tmp_path):
    import sqlite3
    caminho = tmp_path / "velho.db"
    r = Repositorio(caminho)
    s = r.criar(STEAMLOG)
    solta = r.criar("# ideia solta")
    r.fechar()
    db = sqlite3.connect(caminho)  # simula um banco de antes da coluna 'projeto'
    for c in ("projeto", "projeto_de", "projeto_manual"):
        db.execute(f"ALTER TABLE notas DROP COLUMN {c}")
    db.commit()
    db.close()
    r = Repositorio(caminho)
    assert r.obter(s.id).projeto == "Steamlog" and r.obter(solta.id).projeto is None
    r.fechar()


def test_classificador_nao_desfaz_escolha_manual_feita_no_meio(repo):
    s = _velha(repo, STEAMLOG)
    repo.definir_projeto(s.id, "Steamlog")
    n = _velha(repo, "# comprar pão")

    def pedir(*_):
        repo.definir_projeto(n.id, "Steamlog", manual=True)  # a pessoa escolheu enquanto o DeepSeek pensava
        return "Inbox"

    classificar(repo, pedir)
    m = repo.obter(n.id)
    assert m.projeto == "Steamlog" and m.projeto_manual is True


def test_classificador_para_no_primeiro_erro_e_so_olha_ativas_com_limite(repo):
    s = _velha(repo, STEAMLOG)
    repo.definir_projeto(s.id, "Steamlog")
    arq = _velha(repo, "# velha arquivada")
    repo.mudar_estado(arq.id, "arquivada")
    for i in range(3):
        _velha(repo, f"# nota {i}")
    chamadas = []

    def falha(*_):
        chamadas.append(1)
        raise OSError("fora")

    assert classificar(repo, falha) == 0 and len(chamadas) == 1
    assert classificar(repo, lambda *_: "Inbox", limite=2) == 2
    assert repo.obter(arq.id).projeto is None


def test_nome_digitado_vira_o_projeto_que_ja_existe(repo):
    from recados.projetos import canonico
    s = repo.criar("# a")
    repo.definir_projeto(s.id, "Steamlog")
    assert canonico(repo, " steamlog ") == "Steamlog"
    assert canonico(repo, "inbox") == INBOX
    assert canonico(repo, "  Projeto   Novo ") == "Projeto Novo"


def test_descricao_usa_resumo_so_se_for_do_texto_atual(repo):
    from recados.projetos import descricoes
    from recados.resumo import assinatura
    a = repo.criar("# **Guia** de conquistas")
    repo.definir_projeto(a.id, "Steamlog")
    repo.definir_resumo(a.id, "resumo velho", "hash-antigo")
    assert descricoes(repo) == {"Steamlog": "Guia de conquistas"}
    repo.definir_resumo(a.id, "Guia conquistas", assinatura(repo.obter(a.id).texto))
    assert descricoes(repo) == {"Steamlog": "Guia conquistas"}
