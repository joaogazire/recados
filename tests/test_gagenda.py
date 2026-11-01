from datetime import datetime

import pytest

from recados import gagenda
from recados.notas import Repositorio

AGORA = datetime(2026, 11, 1, 15, 0)


@pytest.fixture
def repo(tmp_path):
    r = Repositorio(tmp_path / "r.db")
    yield r
    r.fechar()


class Falso:
    def __init__(self):
        self.calendarios, self.eventos, self.chamadas = 0, {}, []

    def criar_calendario(self, nome):
        self.calendarios += 1
        return "cal1"

    def inserir(self, cal, evento):
        eid = f"e{len(self.eventos) + 1}"
        self.eventos[eid] = evento
        self.chamadas.append(("inserir", evento["summary"]))
        return eid

    def atualizar(self, cal, eid, evento):
        self.eventos[eid] = evento
        self.chamadas.append(("atualizar", evento["summary"]))

    def apagar(self, cal, eid):
        self.eventos.pop(eid, None)
        self.chamadas.append(("apagar", eid))


def test_sincroniza_cria_atualiza_e_apaga(repo, tmp_path):
    estado = tmp_path / "agenda.json"
    g = Falso()
    n = repo.criar("- [ ] dentista @06/11 14h\n- [ ] mercado @02/11")
    gagenda.sincronizar(repo, g, estado, AGORA)
    assert g.calendarios == 1 and sorted(c[1] for c in g.chamadas) == ["dentista", "mercado"]
    ev = next(e for e in g.eventos.values() if e["summary"] == "dentista")
    assert ev["start"]["dateTime"].startswith("2026-11-06T14:00:00")
    assert ev["end"]["dateTime"].startswith("2026-11-06T14:30:00")

    g.chamadas.clear()
    gagenda.sincronizar(repo, g, estado, AGORA)
    assert g.chamadas == []  # nada mudou: nenhuma chamada

    repo.atualizar(n.id, texto="- [ ] dentista @07/11 14h\n- [x] mercado @02/11")
    gagenda.sincronizar(repo, g, estado, AGORA)
    assert ("atualizar", "dentista") in g.chamadas and any(c[0] == "apagar" for c in g.chamadas)
    assert g.calendarios == 1


def test_lembrete_passado_nao_vai_pra_agenda(repo, tmp_path):
    g = Falso()
    repo.criar("- [ ] velho @20/10 9h")
    gagenda.sincronizar(repo, g, tmp_path / "agenda.json", AGORA)
    assert g.eventos == {}


def test_token_ausente_desliga_sincronizacao(tmp_path):
    assert gagenda.cliente_do_token(tmp_path / "nao-existe.json") is None


def test_evento_que_passou_fica_no_google(repo, tmp_path):
    from datetime import timedelta
    estado = tmp_path / "agenda.json"
    g = Falso()
    repo.criar("- [ ] dentista @01/11 16h")
    gagenda.sincronizar(repo, g, estado, AGORA)
    assert len(g.eventos) == 1
    gagenda.sincronizar(repo, g, estado, AGORA + timedelta(hours=3))
    assert len(g.eventos) == 1 and not any(c[0] == "apagar" for c in g.chamadas)


def test_dois_lembretes_com_mesmo_titulo(repo, tmp_path):
    g = Falso()
    repo.criar("- [ ] remédio @02/11 8h\n- [ ] remédio @02/11 20h")
    gagenda.sincronizar(repo, g, tmp_path / "agenda.json", AGORA)
    assert len(g.eventos) == 2
