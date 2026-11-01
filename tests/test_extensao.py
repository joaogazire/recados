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
    assert JanelaNota(repo, n).get_title() == f"Recado {n.id}"
    repo.fechar()


def test_app_id_igual_na_extensao():
    from recados.app import APP_ID

    js = (RAIZ / "extensao/recados@joaogazire/posicoes.js").read_text()
    assert f"'{APP_ID}'" in js
