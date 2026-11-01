"""Captura rápida: uma linha vira '- [ ] ...' no fim da nota Inbox."""
from __future__ import annotations

from recados.notas import Nota, Repositorio

TITULO_INBOX = "# Inbox"


def acrescentar_item(texto: str, item: str) -> str:
    item = " ".join(item.split())
    return f"{texto.rstrip()}\n- [ ] {item}"


def achar_inbox(repo: Repositorio) -> Nota | None:
    for n in repo.listar():
        if n.texto.split("\n", 1)[0].strip() == TITULO_INBOX:
            return n
    return None


def capturar(repo: Repositorio, item: str) -> Nota | None:
    if not item.strip():
        return None
    inbox = achar_inbox(repo)
    if inbox is None:
        return repo.criar(acrescentar_item(TITULO_INBOX, item), "azul")
    return repo.atualizar(inbox.id, texto=acrescentar_item(inbox.texto, item))
