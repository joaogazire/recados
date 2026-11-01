"""Migra os itens do antigo app Tarefas para notas do Recados (uma vez só)."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

from recados.app import caminho_banco
from recados.notas import Repositorio

URL_TAREFAS = "http://127.0.0.1:8000/api/tarefas"


def nota_de_item(item: dict) -> tuple[str, str]:
    titulo = item["titulo"].strip()
    if item.get("tipo") == "tarefa":
        cabeca = f"- [{'x' if item.get('concluida') else ' '}] {titulo}"
        cor = "azul"
    else:
        cabeca, cor = f"# {titulo}", "amarelo"
    partes = [cabeca]
    if (d := (item.get("descricao") or "").strip()):
        partes.append(d)
    if item.get("tags"):
        partes.append(" ".join(f"#{t}" for t in item["tags"]))
    return "\n\n".join(partes), cor


def migrar(repo: Repositorio, itens: list[dict], marca: Path) -> int:
    if marca.exists():
        return 0
    ordenados = sorted(itens, key=lambda i: (i.get("criada_em") or "", i["id"]))
    for item in ordenados:
        texto, cor = nota_de_item(item)
        repo.criar(texto, cor=cor)
    marca.write_text(f"{len(ordenados)} itens migrados\n")
    return len(ordenados)


def main() -> int:
    with urllib.request.urlopen(URL_TAREFAS, timeout=10) as r:
        itens = json.load(r)
    banco = caminho_banco()
    marca = banco.parent / "migrado-do-tarefas"
    if marca.exists():
        print("já migrado antes; nada feito")
        return 0
    repo = Repositorio(banco)
    try:
        n = migrar(repo, itens, marca)
    finally:
        repo.fechar()
    print(f"{n} notas criadas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
