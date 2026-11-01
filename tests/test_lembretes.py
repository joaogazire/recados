from datetime import datetime

import pytest

from recados.lembretes import Avisador, lembretes_do_repo
from recados.notas import Repositorio

AGORA = datetime(2026, 11, 1, 15, 0)


@pytest.fixture
def repo(tmp_path):
    r = Repositorio(tmp_path / "r.db")
    yield r
    r.fechar()


def test_lembretes_so_de_notas_ativas(repo):
    a = repo.criar("- [ ] a @01/11 14h")
    b = repo.criar("- [ ] b @01/11 14h")
    repo.mudar_estado(b.id, "arquivada")
    assert [(n.id, l.titulo) for n, l in lembretes_do_repo(repo, AGORA)] == [(a.id, "a")]


def test_avisador_avisa_uma_vez_so_os_vencidos_e_nao_feitos(repo, tmp_path):
    repo.criar("- [ ] vencido @01/11 14h\n- [x] feito @01/11 14h\n- [ ] futuro @01/11 16h\n- [ ] velho @20/10 9h")
    avisos = []
    av = Avisador(tmp_path / "avisados.json", lambda nota, l: avisos.append(l.titulo))
    av.checar(repo, AGORA)
    av.checar(repo, AGORA)
    assert avisos == ["vencido"]  # 'velho' passou de 1 dia: não incomoda
    Avisador(tmp_path / "avisados.json", lambda n, l: avisos.append(l.titulo)).checar(repo, AGORA)
    assert avisos == ["vencido"]  # lembra entre reinícios
