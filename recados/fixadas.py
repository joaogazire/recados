"""Lista das notas fixadas no topo, lida pela extensão (no Wayland só o Shell põe janela por cima)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from recados.notas import Repositorio


def caminho_padrao() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share"
    return Path(os.environ.get("RECADOS_FIXADAS") or Path(base) / "recados" / "fixadas.json")


def gravar(repo: Repositorio, caminho: Path | None = None) -> None:
    caminho = Path(caminho or caminho_padrao())
    ids = sorted(n.id for n in repo.listar() if n.sempre_no_topo)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(".tmp")
    tmp.write_text(json.dumps(ids))
    tmp.replace(caminho)
