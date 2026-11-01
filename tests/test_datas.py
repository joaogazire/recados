from datetime import datetime

from recados.datas import extrair, fixar_datas

AGORA = datetime(2026, 11, 1, 15, 0)  # domingo


def test_fixar_relativas_vira_data_absoluta():
    assert fixar_datas("- [ ] ligar @amanhã 9h", AGORA) == "- [ ] ligar @02/11 9h"
    assert fixar_datas("@hoje 18h30 reunião", AGORA) == "@01/11 18h30 reunião"
    assert fixar_datas("dentista @sex", AGORA) == "dentista @06/11"
    assert fixar_datas("feira @sexta 10h", AGORA) == "feira @06/11 10h"
    assert fixar_datas("hoje é @dom", AGORA) == "hoje é @01/11"
    assert fixar_datas("e-mail joao@amanha.com", AGORA) == "e-mail joao@amanha.com"
    assert fixar_datas("@15/11 14h já fixa", AGORA) == "@15/11 14h já fixa"


def test_extrair_lembretes():
    texto = "# Semana\n- [ ] dentista @06/11 14h30\n- [x] pagar conta @02/11\nideia solta @20/01"
    ls = extrair(texto, AGORA)
    assert [(l.linha, l.quando, l.titulo, l.feito) for l in ls] == [
        (1, datetime(2026, 11, 6, 14, 30), "dentista", False),
        (2, datetime(2026, 11, 2, 9, 0), "pagar conta", True),
        (3, datetime(2027, 1, 20, 9, 0), "ideia solta", False),  # já passou há muito: ano que vem
    ]


def test_extrair_ignora_data_invalida():
    assert extrair("@31/02 9h nada", AGORA) == []
    assert extrair("@15/11 25h nada", AGORA) == []


def test_ano_explicito():
    [l] = extrair("viagem @10/01/2027 7h", AGORA)
    assert l.quando == datetime(2027, 1, 10, 7, 0)
