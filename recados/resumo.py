"""Resumo das notas para a central no painel do GNOME (sem GTK)."""
from __future__ import annotations

import re

from recados.notas import Repositorio

MAX_TITULO = 60
_PREFIXO = re.compile(r"^\s*(?:#{1,6} |[-*+] (?:\[[ xX]\] ?)?|\d+\. )")
_ENFEITE = re.compile(r"\*\*|__|`|(?<!\w)[*_]|[*_](?!\w)")
_ITEM = re.compile(r"^[ \t]*[-*+] \[([ xX])\]", re.M)


def titulo_da_nota(texto: str) -> str:
    for linha in texto.split("\n"):
        limpo = _ENFEITE.sub("", _PREFIXO.sub("", linha)).strip()
        if limpo:
            return limpo if len(limpo) <= MAX_TITULO else limpo[: MAX_TITULO - 1] + "…"
    return "(vazia)"


def resumo(repo: Repositorio) -> list[dict]:
    saida = []
    for n in repo.listar():
        marcas = _ITEM.findall(n.texto)
        saida.append({"id": n.id, "titulo": titulo_da_nota(n.texto), "cor": n.cor,
                      "pendentes": marcas.count(" "), "total": len(marcas)})
    return saida
