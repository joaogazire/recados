"""Nota do dia: uma nota por data, achada pela primeira linha."""
from __future__ import annotations

import re
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


_TITULO = re.compile(r"^# (\d{2})/(\d{2})/(\d{4}) \(")
_ABERTA = re.compile(r"^[ \t]*[-*+] \[ \][ \t]*\S")


def data_da_nota(texto: str) -> date | None:
    m = _TITULO.match(texto.split("\n", 1)[0])
    if not m:
        return None
    try:
        return date(int(m[3]), int(m[2]), int(m[1]))
    except ValueError:
        return None


def nota_anterior(repo: Repositorio, dia: date | None = None) -> Nota | None:
    """A nota do dia ativa mais recente antes de 'dia'."""
    dia = dia or date.today()
    candidatas = [(d, n) for n in repo.listar() if (d := data_da_nota(n.texto)) and d < dia]
    return max(candidatas, key=lambda c: c[0])[1] if candidatas else None


def pendencias(texto: str) -> list[str]:
    """Linhas de tarefa ainda abertas ('- [ ] algo'), sem as vazias."""
    return [l.rstrip() for l in texto.split("\n") if _ABERTA.match(l)]
