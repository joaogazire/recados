import json
import subprocess
import sys
from pathlib import Path

from recados.notas import Repositorio
from recados.resumo import resumo, titulo_da_nota

RAIZ = Path(__file__).resolve().parent.parent


def test_titulo_tira_markdown_e_pula_linhas_vazias():
    assert titulo_da_nota("\n\n# Compras **hoje**\n- [ ] pão") == "Compras hoje"
    assert titulo_da_nota("- [x] feito") == "feito"
    assert titulo_da_nota("   ") == "(vazia)"
    assert len(titulo_da_nota("a" * 200)) <= 60


def test_resumo_conta_pendentes(tmp_path):
    r = Repositorio(tmp_path / "r.db")
    r.criar("# Lista\n- [ ] a\n- [x] b\n- [ ] c", "azul")
    r.criar("ideia solta")
    itens = resumo(r)
    r.fechar()
    assert {k: v for k, v in itens[0].items() if k not in ("texto", "estado")} == {"id": 1, "titulo": "Lista", "cor": "azul", "pendentes": 2, "total": 3}
    assert itens[1]["pendentes"] == 0 and itens[1]["total"] == 0


def test_cli_listar_imprime_json_sem_abrir_janela(tmp_path):
    banco = tmp_path / "r.db"
    r = Repositorio(banco)
    r.criar("# Oi\n- [ ] x")
    r.fechar()
    p = subprocess.run([sys.executable, "-m", "recados", "--listar"], cwd=RAIZ, capture_output=True,
                       text=True, timeout=20, env={"RECADOS_BANCO": str(banco), "PATH": "/usr/bin",
                                                   "PYTHONPATH": str(RAIZ)})
    assert p.returncode == 0, p.stderr
    assert json.loads(p.stdout)[0]["titulo"] == "Oi"
