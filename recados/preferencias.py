"""Preferências do Recados (JSON em ~/.config/recados), sempre validadas."""
from __future__ import annotations

import json
import os
from pathlib import Path

from recados.notas import FONTES, TAMANHOS

PADRAO = {"fonte": "sans", "tamanho": "M", "abrir_em": "leitura", "abrir_na_sessao": True}
_VALIDOS = {
    "fonte": lambda v: v in FONTES,
    "tamanho": lambda v: v in TAMANHOS,
    "abrir_em": lambda v: v in ("leitura", "edicao"),
    "abrir_na_sessao": lambda v: isinstance(v, bool),
}


def caminho_padrao() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(os.environ.get("RECADOS_PREFERENCIAS") or Path(base) / "recados" / "preferencias.json")


def carregar(caminho: Path | None = None) -> dict:
    caminho = Path(caminho or caminho_padrao())
    try:
        dados = json.loads(caminho.read_text())
    except (OSError, ValueError):
        dados = {}
    if not isinstance(dados, dict):
        dados = {}
    return {k: dados[k] if k in dados and _VALIDOS[k](dados[k]) else v for k, v in PADRAO.items()}


def salvar(caminho: Path | None, prefs: dict) -> None:
    caminho = Path(caminho or caminho_padrao())
    limpo = {k: prefs[k] if k in prefs and _VALIDOS[k](prefs[k]) else v for k, v in PADRAO.items()}
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(".tmp")
    tmp.write_text(json.dumps(limpo, ensure_ascii=False, indent=2))
    tmp.replace(caminho)
