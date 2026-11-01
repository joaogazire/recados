"""Resumo das notas para a central no painel do GNOME (sem GTK)."""
from __future__ import annotations

import hashlib
import re

from recados.notas import Repositorio

MAX_TITULO = 60
MAX_PALAVRAS = 5
_PREFIXO = re.compile(r"^\s*(?:#{1,6} |[-*+] (?:\[[ xX]\] ?)?|\d+\. )")
_ENFEITE = re.compile(r"\*\*|__|`|(?<!\w)[*_]|[*_](?!\w)")
_ITEM = re.compile(r"^[ \t]*[-*+] \[([ xX])\]", re.M)


def titulo_da_nota(texto: str) -> str:
    for linha in texto.split("\n"):
        limpo = _ENFEITE.sub("", _PREFIXO.sub("", linha)).strip()
        if limpo:
            return limpo if len(limpo) <= MAX_TITULO else limpo[: MAX_TITULO - 1] + "…"
    return "(vazia)"


def assinatura(texto: str) -> str:
    return hashlib.sha256(texto.encode()).hexdigest()[:16]


def resumo_local(texto: str) -> str:
    return " ".join(titulo_da_nota(texto).split()[:MAX_PALAVRAS])


def resumo(repo: Repositorio) -> list[dict]:
    saida = []
    for n in repo.listar(estado=None):
        marcas = _ITEM.findall(n.texto)
        atual = n.resumo and n.resumo_de == assinatura(n.texto)  # resumo de um texto antigo não vale
        titulo = n.resumo if atual else resumo_local(n.texto)
        saida.append({"id": n.id, "titulo": titulo, "cor": n.cor,
                      "pendentes": marcas.count(" "), "total": len(marcas), "texto": n.texto[:2000],
                      "estado": n.estado})
    return saida
