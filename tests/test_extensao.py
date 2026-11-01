import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(not shutil.which("gjs"), reason="sem gjs")
def test_logica_da_extensao():
    r = subprocess.run(["gjs", "-m", "tests/js/test_posicoes.js"], cwd=RAIZ, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_titulo_da_janela_carrega_id(tmp_path):
    pytest.importorskip("gi")
    from gi.repository import Gtk

    if not Gtk.init_check():
        pytest.skip("sem display")
    from recados.janela import JanelaNota
    from recados.notas import Repositorio

    repo = Repositorio(tmp_path / "r.db")
    n = repo.criar()
    assert JanelaNota(repo, n).get_title() == f"Post-it {n.id}"
    repo.fechar()


def test_app_id_igual_na_extensao():
    from recados.app import APP_ID

    js = (RAIZ / "extensao/recados@joaogazire/posicoes.js").read_text()
    assert f"'{APP_ID}'" in js


@pytest.mark.skipif(not shutil.which("gjs"), reason="sem gjs")
def test_logica_da_central():
    r = subprocess.run(["gjs", "-m", "tests/js/test_central.js"], cwd=RAIZ, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.skipif(not shutil.which("gjs"), reason="sem gjs")
def test_logica_da_pilha():
    r = subprocess.run(["gjs", "-m", "tests/js/test_pilha.js"], cwd=RAIZ, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.skipif(not shutil.which("gjs"), reason="sem gjs")
def test_logica_das_fixadas():
    r = subprocess.run(["gjs", "-m", "tests/js/test_fixadas.js"], cwd=RAIZ, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.skipif(not shutil.which("gjs"), reason="sem gjs")
def test_logica_da_busca():
    r = subprocess.run(["gjs", "-m", "tests/js/test_busca.js"], cwd=RAIZ, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.skipif(not shutil.which("node"), reason="sem node")
def test_extensao_e_modulo_es_valido(tmp_path):
    # .js sem package.json é lido como CommonJS e o node --check deixa passar erros: copia como .mjs
    for arq in (RAIZ / "extensao" / "recados@joaogazire").glob("*.js"):
        copia = tmp_path / (arq.stem + ".mjs")
        copia.write_text(arq.read_text())
        r = subprocess.run(["node", "--check", str(copia)], capture_output=True, text=True)
        assert r.returncode == 0, f"{arq.name}: {r.stderr}"


@pytest.mark.skipif(not shutil.which("gjs"), reason="sem gjs")
def test_logica_dos_estados():
    r = subprocess.run(["gjs", "-m", "tests/js/test_estados.js"], cwd=RAIZ, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.skipif(not shutil.which("gjs"), reason="sem gjs")
def test_logica_da_agenda():
    r = subprocess.run(["gjs", "-m", "tests/js/test_agenda.js"], cwd=RAIZ, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
