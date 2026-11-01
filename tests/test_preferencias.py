import json

from recados.preferencias import PADRAO, carregar, salvar


def test_sem_arquivo_usa_padrao(tmp_path):
    assert carregar(tmp_path / "p.json") == PADRAO
    assert PADRAO == {"fonte": "sans", "tamanho": "M", "abrir_em": "leitura", "abrir_na_sessao": True}


def test_salvar_e_carregar(tmp_path):
    p = tmp_path / "sub" / "p.json"
    salvar(p, {**PADRAO, "fonte": "mono", "abrir_na_sessao": False})
    assert carregar(p)["fonte"] == "mono" and carregar(p)["abrir_na_sessao"] is False


def test_valores_invalidos_voltam_ao_padrao(tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"fonte": "comic", "tamanho": "XXL", "abrir_em": 3, "abrir_na_sessao": "sim", "lixo": 1}))
    assert carregar(p) == PADRAO
    p.write_text("{quebrado")
    assert carregar(p) == PADRAO
