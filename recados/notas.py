"""Modelo e armazenamento das notas (SQLite local)."""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

CORES = ("amarelo", "azul", "verde", "rosa", "roxo", "cinza")
FONTES = ("sans", "serifa", "mono")
TAMANHOS = {"P": (200, 160), "M": (260, 220), "G": (360, 320), "GG": (480, 440)}

_EDITAVEIS = {"texto", "cor", "x", "y", "largura", "altura", "recolhida", "sempre_no_topo", "fonte"}
_BOOLEANOS = {"recolhida", "sempre_no_topo"}

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS notas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    texto TEXT NOT NULL DEFAULT '',
    cor TEXT NOT NULL DEFAULT 'amarelo',
    x INTEGER, y INTEGER,
    largura INTEGER NOT NULL DEFAULT 260,
    altura INTEGER NOT NULL DEFAULT 220,
    recolhida INTEGER NOT NULL DEFAULT 0,
    sempre_no_topo INTEGER NOT NULL DEFAULT 0,
    fonte TEXT NOT NULL DEFAULT 'sans',
    criada REAL NOT NULL,
    editada REAL NOT NULL,
    apagada REAL
);
"""


@dataclass(frozen=True)
class Nota:
    id: int | None  # None = rascunho, ainda fora do banco
    texto: str
    cor: str
    x: int | None
    y: int | None
    largura: int
    altura: int
    recolhida: bool
    sempre_no_topo: bool
    criada: float
    editada: float
    fonte: str = "sans"
    resumo: str | None = None  # até 5 palavras, gerado pelo DeepSeek
    resumo_de: str | None = None  # hash do texto que gerou o resumo


def rascunho(cor: str = "amarelo", fonte: str = "sans", largura: int = 260, altura: int = 220) -> Nota:
    """Nota nova que só vai para o banco quando ganhar texto."""
    return Nota(id=None, texto="", cor=cor, x=None, y=None, largura=largura, altura=altura,
                recolhida=False, sempre_no_topo=False, criada=0.0, editada=0.0, fonte=fonte)


def _checar_cor(cor: str) -> None:
    if cor not in CORES:
        raise ValueError(f"cor inválida: {cor!r}")


class Repositorio:
    def __init__(self, caminho: str | Path):
        caminho = Path(caminho)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(caminho)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript(_ESQUEMA)
        colunas = {c[1] for c in self._db.execute("PRAGMA table_info(notas)")}
        novas = {"fonte": "TEXT NOT NULL DEFAULT 'sans'", "resumo": "TEXT", "resumo_de": "TEXT"}
        with self._db:
            for nome, tipo in novas.items():  # nomes e tipos fixos, nada vem de fora
                if nome not in colunas:
                    self._db.execute(f"ALTER TABLE notas ADD COLUMN {nome} {tipo}")

    def fechar(self) -> None:
        self._db.close()

    @staticmethod
    def _nota(linha: sqlite3.Row) -> Nota:
        d = {k: linha[k] for k in linha.keys() if k != "apagada"}
        for b in _BOOLEANOS:
            d[b] = bool(d[b])
        return Nota(**d)

    def criar(self, texto: str = "", cor: str = "amarelo") -> Nota:
        _checar_cor(cor)
        agora = time.time()
        with self._db:
            cur = self._db.execute(
                "INSERT INTO notas (texto, cor, criada, editada) VALUES (?, ?, ?, ?)",
                (texto, cor, agora, agora),
            )
        return self.obter(cur.lastrowid)

    def obter(self, id_: int) -> Nota | None:
        linha = self._db.execute(
            "SELECT * FROM notas WHERE id = ? AND apagada IS NULL", (id_,)
        ).fetchone()
        return self._nota(linha) if linha else None

    def listar(self) -> list[Nota]:
        linhas = self._db.execute(
            "SELECT * FROM notas WHERE apagada IS NULL ORDER BY criada, id"
        ).fetchall()
        return [self._nota(l) for l in linhas]

    def atualizar(self, id_: int, **campos) -> Nota:
        desconhecidos = set(campos) - _EDITAVEIS
        if desconhecidos or not campos:
            raise ValueError(f"campos inválidos: {sorted(desconhecidos) or 'nenhum'}")
        if "cor" in campos:
            _checar_cor(campos["cor"])
        if "fonte" in campos and campos["fonte"] not in FONTES:
            raise ValueError(f"fonte inválida: {campos['fonte']!r}")
        valores = {k: int(v) if k in _BOOLEANOS else v for k, v in campos.items()}
        valores["editada"] = time.time()
        sets = ", ".join(f"{k} = ?" for k in valores)  # nomes vêm da lista branca
        with self._db:
            cur = self._db.execute(
                f"UPDATE notas SET {sets} WHERE id = ? AND apagada IS NULL",
                (*valores.values(), id_),
            )
        if cur.rowcount == 0:
            raise KeyError(id_)
        return self.obter(id_)

    def definir_resumo(self, id_: int, resumo: str, resumo_de: str) -> None:
        """Guarda o resumo sem mexer em 'editada' (não é edição do usuário)."""
        with self._db:
            self._db.execute(
                "UPDATE notas SET resumo = ?, resumo_de = ? WHERE id = ? AND apagada IS NULL",
                (resumo, resumo_de, id_),
            )

    def apagar(self, id_: int) -> None:
        with self._db:
            cur = self._db.execute(
                "UPDATE notas SET apagada = ? WHERE id = ? AND apagada IS NULL",
                (time.time(), id_),
            )
        if cur.rowcount == 0:
            raise KeyError(id_)

    def restaurar(self, id_: int) -> None:
        with self._db:
            cur = self._db.execute(
                "UPDATE notas SET apagada = NULL WHERE id = ? AND apagada IS NOT NULL", (id_,)
            )
        if cur.rowcount == 0:
            raise KeyError(id_)

    def purgar_apagadas(self) -> int:
        with self._db:
            cur = self._db.execute("DELETE FROM notas WHERE apagada IS NOT NULL")
        return cur.rowcount
