"""Lembretes das notas ativas e avisos (uma vez cada, mesmo entre reinícios)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from recados.datas import Lembrete, extrair
from recados.notas import Nota, Repositorio

JANELA_AVISO = timedelta(days=1)  # lembrete vencido há mais que isso não gera aviso
MAX_AVISADOS = 500


def lembretes_do_repo(repo: Repositorio, agora: datetime) -> list[tuple[Nota, Lembrete]]:
    return [(n, l) for n in repo.listar() for l in extrair(n.texto, agora)]


def chave(nota: Nota, l: Lembrete) -> str:
    return f"{nota.id}|{l.quando:%Y-%m-%dT%H:%M}|{l.titulo}"


class Avisador:
    def __init__(self, caminho: Path, avisar: Callable[[Nota, Lembrete], None]):
        self.caminho = Path(caminho)
        self.avisar = avisar
        try:
            dados = json.loads(self.caminho.read_text())
            self.avisados = [k for k in dados if isinstance(k, str)] if isinstance(dados, list) else []
        except (OSError, ValueError):
            self.avisados = []

    def checar(self, repo: Repositorio, agora: datetime) -> None:
        novos = False
        for nota, l in lembretes_do_repo(repo, agora):
            k = chave(nota, l)
            if l.feito or not (agora - JANELA_AVISO < l.quando <= agora) or k in self.avisados:
                continue
            self.avisar(nota, l)
            self.avisados.append(k)
            novos = True
        if novos:
            self.avisados = self.avisados[-MAX_AVISADOS:]
            self.caminho.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.caminho.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.avisados, ensure_ascii=False))
            tmp.replace(self.caminho)
