"""Realce de Markdown: devolve (início, fim, tag) em offsets de caractere."""
from __future__ import annotations

import re
from html import escape

_TITULO = re.compile(r"^(#{1,6}) .*$", re.M)
_MARCADOR = re.compile(r"^[ \t]*([-*+]|\d+\.)(?= )", re.M)
_ITEM = re.compile(r"^([ \t]*[-*+] )\[([ xX])\](?= |$)", re.M)
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
    for m in _ITEM.finditer(texto):
        i = m.end(1)
        saida.append((i, i + 3, "caixa" if m.group(2) == " " else "caixa-marcada"))
        ocupado.append((i, i + 3))
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


def alternar_item(texto: str, linha: int) -> str:
    """Marca/desmarca o item de checklist da linha (0-based); outras linhas ficam iguais."""
    linhas = texto.split("\n")
    if not 0 <= linha < len(linhas):
        return texto
    m = _ITEM.match(linhas[linha])
    if not m:
        return texto
    novo = "x" if m.group(2) == " " else " "
    i = m.end(1) + 1
    linhas[linha] = linhas[linha][:i] + novo + linhas[linha][i + 1:]
    return "\n".join(linhas)


_LISTA = re.compile(r"^[ \t]*(?:[-*+]|\d+\.) (.*)$")
_ITEM_LINHA = re.compile(r"^[ \t]*[-*+] \[([ xX])\] ?(.*)$")
_TITULO_LINHA = re.compile(r"^(#{1,6}) (.*)$")


def blocos(texto: str) -> list[tuple]:
    """Uma tupla (tipo, valor, conteúdo, linha) por linha, para o modo leitura."""
    saida = []
    for n, linha in enumerate(texto.split("\n")):
        if m := _ITEM_LINHA.match(linha):
            saida.append(("item", m.group(1) != " ", m.group(2), n))
        elif m := _TITULO_LINHA.match(linha):
            saida.append(("titulo", min(len(m.group(1)), 3), m.group(2), n))
        elif m := _LISTA.match(linha):
            saida.append(("lista", 0, m.group(1), n))
        elif not linha.strip():
            saida.append(("vazio", 0, "", n))
        else:
            saida.append(("paragrafo", 0, linha, n))
    return saida


_INLINE = re.compile(
    r"`(?P<cod>[^`\n]+)`"
    r"|\[(?P<lt>[^\]\n]+)\]\((?P<lu>https?://[^)\s]+)\)"
    r"|\*\*(?P<neg>[^*\n]+)\*\*|__(?P<neg2>[^_\n]+)__"
    r"|(?<![*\w])\*(?P<it>[^*\n]+)\*(?!\*)|(?<![_\w])_(?P<it2>[^_\n]+)_(?!\w)"
)


def para_pango(linha: str) -> str:
    """Formatação inline de Markdown em markup Pango, com todo texto escapado."""
    saida, pos = [], 0
    for m in _INLINE.finditer(linha):
        saida.append(escape(linha[pos:m.start()], quote=False))
        g = m.groupdict()
        if g["cod"] is not None:
            saida.append(f"<tt>{escape(g['cod'], quote=False)}</tt>")
        elif g["lt"] is not None:
            saida.append(f'<a href="{escape(g["lu"])}">{escape(g["lt"], quote=False)}</a>')
        elif (t := g["neg"] or g["neg2"]) is not None:
            saida.append(f"<b>{escape(t, quote=False)}</b>")
        else:
            saida.append(f"<i>{escape(g['it'] or g['it2'], quote=False)}</i>")
        pos = m.end()
    saida.append(escape(linha[pos:], quote=False))
    return "".join(saida)
