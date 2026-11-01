"""Datas nas notas: '@amanhã 9h', '@sex', '@15/11 14h30', '@10/01/2027 7h'.

Datas relativas (hoje, amanhã, dia da semana) viram absolutas ao salvar (fixar_datas),
senão um '@amanhã' escrito hoje andaria um dia para frente todo dia.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

HORA_PADRAO = time(9, 0)
_SEMANA = {"seg": 0, "segunda": 0, "ter": 1, "terça": 1, "terca": 1, "qua": 2, "quarta": 2,
           "qui": 3, "quinta": 3, "sex": 4, "sexta": 4, "sáb": 5, "sab": 5, "sábado": 5,
           "sabado": 5, "dom": 6, "domingo": 6}
_RELATIVAS = "hoje|amanhã|amanha|" + "|".join(sorted(_SEMANA, key=len, reverse=True))
TOKEN = re.compile(
    r"(?<![\w@.])@(?P<dia>" + _RELATIVAS + r"|\d{1,2}/\d{1,2}(?:/\d{4})?)"
    r"(?:\s+(?P<h>\d{1,2})h(?P<m>\d{2})?)?(?![\w/])",
    re.I,
)
_PREFIXO = re.compile(r"^\s*(?:[-*+] (?:\[[ xX]\] ?)?|\d+\. |#{1,6} )")
_FEITO = re.compile(r"^\s*[-*+] \[[xX]\]")


@dataclass(frozen=True)
class Lembrete:
    linha: int
    quando: datetime
    titulo: str
    feito: bool


def _dia_relativo(palavra: str, hoje: date) -> date | None:
    p = palavra.lower()
    if p == "hoje":
        return hoje
    if p in ("amanhã", "amanha"):
        return hoje + timedelta(days=1)
    if p in _SEMANA:
        return hoje + timedelta(days=(_SEMANA[p] - hoje.weekday()) % 7)
    return None


def _dia(palavra: str, hoje: date) -> date:
    """Levanta ValueError se a data não existe."""
    if (d := _dia_relativo(palavra, hoje)) is not None:
        return d
    partes = [int(x) for x in palavra.split("/")]
    if len(partes) == 3:
        return date(partes[2], partes[1], partes[0])
    d = date(hoje.year, partes[1], partes[0])
    if d < hoje - timedelta(days=30):  # já passou faz tempo: é do ano que vem
        d = date(hoje.year + 1, partes[1], partes[0])
    return d


def _quando(m: re.Match, hoje: date) -> datetime:
    d = _dia(m.group("dia"), hoje)
    if m.group("h") is None:
        return datetime.combine(d, HORA_PADRAO)
    return datetime.combine(d, time(int(m.group("h")), int(m.group("m") or 0)))


def fixar_datas(texto: str, agora: datetime) -> str:
    hoje = agora.date()

    def troca(m: re.Match) -> str:
        d = _dia_relativo(m.group("dia"), hoje)
        if d is None:
            return m.group(0)
        ini, fim = m.start("dia") - m.start(), m.end("dia") - m.start()
        return m.group(0)[:ini] + f"{d:%d/%m}" + m.group(0)[fim:]

    return TOKEN.sub(troca, texto)


def extrair(texto: str, agora: datetime) -> list[Lembrete]:
    saida = []
    hoje = agora.date()
    for n, linha in enumerate(texto.split("\n")):
        for m in TOKEN.finditer(linha):
            try:
                quando = _quando(m, hoje)
            except ValueError:
                continue
            resto = (linha[:m.start()] + linha[m.end():])
            titulo = " ".join(_PREFIXO.sub("", resto).split()) or "(lembrete)"
            saida.append(Lembrete(n, quando, titulo, bool(_FEITO.match(linha))))
            break  # um lembrete por linha
    return saida
