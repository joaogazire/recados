"""Realce de Markdown: devolve (início, fim, tag) em offsets de caractere."""
from __future__ import annotations

import re

_TITULO = re.compile(r"^(#{1,6}) .*$", re.M)
_MARCADOR = re.compile(r"^[ \t]*([-*+]|\d+\.)(?= )", re.M)
_CODIGO = re.compile(r"`[^`\n]+`")
_LINK = re.compile(r"\[[^\]\n]+\]\([^)\s]+\)")
_NEGRITO = re.compile(r"\*\*[^*\n]+\*\*|__[^_\n]+__")
_ITALICO = re.compile(r"(?<![*\w])\*[^*\n]+\*(?!\*)|(?<![_\w])_[^_\n]+_(?!\w)")


def realces(texto: str) -> list[tuple[int, int, str]]:
    saida: list[tuple[int, int, str]] = []
    ocupado: list[tuple[int, int]] = []

    def livre(i: int, f: int) -> bool:
        return all(f <= a or i >= b for a, b in ocupado)

    for m in _TITULO.finditer(texto):
        nivel = min(len(m.group(1)), 3)
        saida.append((m.start(), m.end(), f"titulo{nivel}"))
        ocupado.append(m.span())
    for m in _MARCADOR.finditer(texto):
        if livre(*m.span(1)):
            saida.append((m.start(1), m.end(1), "marcador"))
            ocupado.append(m.span(1))
    for padrao, tag in ((_CODIGO, "codigo"), (_LINK, "link"), (_NEGRITO, "negrito"), (_ITALICO, "italico")):
        for m in padrao.finditer(texto):
            if livre(*m.span()):
                saida.append((m.start(), m.end(), tag))
                ocupado.append(m.span())
    return sorted(saida)
