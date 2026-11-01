"""Nota do dia: uma nota por data, achada pela primeira linha."""
from __future__ import annotations

from datetime import date

from recados.notas import Nota, Repositorio

_DIAS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")


def titulo_do_dia(dia: date) -> str:
    return f"# {dia:%d/%m/%Y} ({_DIAS[dia.weekday()]})"


def nota_de_hoje(repo: Repositorio, dia: date | None = None) -> Nota | None:
    titulo = titulo_do_dia(dia or date.today())
    for n in repo.listar():
        if n.texto.split("\n", 1)[0].strip() == titulo:
            return n
    return None
