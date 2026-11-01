"""Resumo de até 5 palavras por nota, pelo DeepSeek via proxy local do AI Usage Monitor."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Callable

from recados.notas import Repositorio
from recados.resumo import MAX_PALAVRAS, assinatura, resumo_local  # noqa: F401 (resumo_local reexportado)

PROXY = "http://127.0.0.1:8787/v1/chat/completions"  # só local: a chave nunca sai daqui direto
MODELO = "deepseek-chat"
MAX_TEXTO = 2000
_PROMPT = ("Resuma do que se trata esta nota em no máximo 5 palavras, em português, sem pontuação "
           "final e sem aspas. Responda só com o resumo.")


def limpar(resposta: str) -> str | None:
    linha = next((l for l in resposta.strip().splitlines() if l.strip()), "")
    linha = linha.strip().strip("\"'“”‘’").strip()
    palavras = linha.split()[:MAX_PALAVRAS]
    if not palavras:
        return None
    return " ".join(palavras).rstrip(".!?;:,")


def chave(caminho: Path | None = None) -> str | None:
    caminho = Path(caminho or Path.home() / ".local/share/opencode/auth.json")
    try:
        k = json.loads(caminho.read_text())["deepseek"]["key"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return k if isinstance(k, str) and k else None


def pedir_deepseek(texto: str) -> str:
    k = chave()
    if not k:
        raise OSError("sem chave do DeepSeek")
    corpo = json.dumps({
        "model": MODELO, "temperature": 0.2, "max_tokens": 30,
        "messages": [{"role": "system", "content": _PROMPT}, {"role": "user", "content": texto[:MAX_TEXTO]}],
    }).encode()
    req = urllib.request.Request(PROXY, data=corpo, method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {k}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read(64 * 1024))["choices"][0]["message"]["content"]


def atualizar(repo: Repositorio, pedir: Callable[[str], str] = pedir_deepseek) -> int:
    """Resume as notas cujo texto mudou desde o último resumo. Devolve quantas resumiu."""
    feitos = 0
    for n in repo.listar():
        if not n.texto.strip():
            continue
        h = assinatura(n.texto)
        if n.resumo_de == h:
            continue
        try:
            r = limpar(pedir(n.texto))
        except Exception:  # rede, proxy fora, resposta estranha: tenta de novo na próxima rodada
            continue
        if r:
            repo.definir_resumo(n.id, r, h)
            feitos += 1
    return feitos
