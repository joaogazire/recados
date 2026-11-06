"""Projetos (PLANO-v3): cada projeto é uma nota ativa '# Nome' com uma seção '## Fazer…'.

Item novo entra no fim do primeiro '## Fazer…'. O que não é de projeto nenhum vai para a Inbox.
"""
from __future__ import annotations

import re
import time
import unicodedata
from typing import Callable

from recados import resumir
from recados.notas import Nota, Repositorio
from recados.resumo import assinatura, titulo_da_nota

INBOX = "Inbox"
_SECAO = re.compile(r"^## ")
_FAZER = re.compile(r"^## Fazer\b")
_FEITO = re.compile(r"^## Feito\b")
_ITEM = re.compile(r"^[-*+] \[([ xX])\]")  # só item de primeiro nível
_TAG = re.compile(r"^#[^\s#]\S*(\s+#[^\s#]\S*)*\s*$")  # linha só de tags: '#steamlog #app'
_PROMPT = ("Você classifica uma anotação em um dos projetos da lista. Cada projeto vem com os títulos de "
           "algumas notas dele, para você entender do que se trata. Responda só com o nome exato de um "
           "projeto da lista, ou Inbox se a anotação não tiver relação clara com nenhum.\nProjetos:\n{}")
ESPERA_S = 30  # não classifica nota que ainda está sendo digitada
MAX_DESCRICAO = 3
MAX_POR_RODADA = 10  # chamadas ao DeepSeek por rodada de 60 s


def normalizar(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.casefold())
    return "".join(c for c in s if c.isalnum())


def titulo(texto: str) -> str:
    primeira = texto.split("\n", 1)[0].strip()
    return primeira[2:].strip() if primeira.startswith("# ") else ""


def _e_projeto(n: Nota) -> bool:
    return bool(titulo(n.texto)) and any(_FAZER.match(l) for l in n.texto.split("\n"))


def _e_inbox(nome: str | None) -> bool:
    return normalizar(nome or "") == normalizar(INBOX)


def nomes(repo: Repositorio) -> list[str]:
    """Projetos que existem: o 'projeto' das notas não apagadas (de qualquer estado), sem a Inbox."""
    vistos: dict[str, str] = {}
    for n in sorted(repo.listar(estado=None), key=lambda n: -n.editada):
        if n.projeto and not _e_inbox(n.projeto):
            vistos.setdefault(normalizar(n.projeto), n.projeto)
    return list(vistos.values())


def descricoes(repo: Repositorio) -> dict[str, str]:
    """Nome do projeto → títulos de algumas notas dele (contexto para o DeepSeek)."""
    saida: dict[str, list[str]] = {}
    for n in sorted(repo.listar(estado=None), key=lambda n: -n.editada):
        if n.projeto and not _e_inbox(n.projeto):
            atual = n.resumo and n.resumo_de == assinatura(n.texto)  # resumo de texto antigo não vale
            t = n.resumo if atual else titulo_da_nota(n.texto)
            lista = saida.setdefault(n.projeto, [])
            if t and len(lista) < MAX_DESCRICAO:
                lista.append(t)
    return {k: "; ".join(v) for k, v in saida.items()}


def canonico(repo: Repositorio, nome: str) -> str:
    """Nome digitado → o projeto que já existe com esse nome (sem ligar para caixa/acento), ou ele limpo."""
    nome = " ".join(nome.split())
    if _e_inbox(nome):
        return INBOX
    return next((n for n in nomes(repo) if normalizar(n) == normalizar(nome)), nome)


def achar_nota(repo: Repositorio, nome: str) -> Nota | None:
    """Nota ativa do projeto onde entram itens novos: a que tem '## Fazer…'; 'Inbox' acha a nota '# Inbox'."""
    if _e_inbox(nome):
        return next((n for n in repo.listar() if _e_inbox(titulo(n.texto))), None)
    alvo = normalizar(nome)
    return next((n for n in repo.listar() if n.projeto and normalizar(n.projeto) == alvo and _e_projeto(n)), None)


def _citado(nome: str, texto: str, max_palavras: int = 4) -> bool:
    """O nome aparece como palavra(s) inteira(s): 'Steam Log' e 'post-it' valem, 'restante' não é Estante."""
    if len(nome) < 3:
        return False
    palavras = [normalizar(w) for w in re.split(r"\W+", texto) if normalizar(w)]
    return any("".join(palavras[i:j]) == nome
               for i in range(len(palavras)) for j in range(i + 1, min(i + max_palavras, len(palavras)) + 1))


def pedir_deepseek(texto: str, nomes_: list[str], desc: dict[str, str] | None = None) -> str:
    linhas = "\n".join(f"- {n}" + (f": {d}" if (d := (desc or {}).get(n)) else "") for n in nomes_)
    return resumir.conversar(_PROMPT.format(linhas), texto, max_tokens=20)


def sugerir_projeto(texto: str, nomes_: list[str],
                    pedir: Callable[[str, list[str]], str] = pedir_deepseek) -> str:
    """Nome escrito no texto ganha; senão o DeepSeek escolhe da lista; qualquer outra coisa é Inbox."""
    try:
        return _sugerir_ou_falhar(texto, nomes_, pedir)
    except Exception:  # rede, proxy, chave: sem palpite, Inbox
        return INBOX


def _sugerir_ou_falhar(texto: str, nomes_: list[str], pedir: Callable[[str, list[str]], str]) -> str:
    """Igual a sugerir_projeto, mas deixa o erro do DeepSeek subir (o classificador tenta de novo depois)."""
    if not texto.strip():
        return INBOX
    citados = [n for n in nomes_ if _citado(normalizar(n), texto)]
    if citados:
        return max(citados, key=lambda n: len(normalizar(n)))
    if not nomes_:
        return INBOX
    resposta = pedir(texto, nomes_)
    linha = next((l for l in resposta.strip().splitlines() if l.strip()), "")
    escolha = normalizar(linha)
    return next((n for n in nomes_ if normalizar(n) == escolha), INBOX)


def _limpar(itens: list[str]) -> list[str]:
    return [" ".join(i.split()) for i in itens if i.strip()]


def _caixas(itens: list[str]) -> list[str]:
    return [f"- [ ] {i}" for i in _limpar(itens)]


def _fim_sem_tags(linhas: list[str]) -> int:
    """Índice logo depois do último conteúdo que não é linha de tags nem linha em branco."""
    fim = len(linhas)
    while fim > 1 and (not linhas[fim - 1].strip() or _TAG.match(linhas[fim - 1].strip())):
        fim -= 1
    return fim


def _fim_da_secao(linhas: list[str], inicio: int) -> int:
    """Depois do último conteúdo da seção que começa em 'inicio' (antes de brancos, próxima seção ou tags)."""
    fim = next((i for i in range(inicio + 1, len(linhas)) if _SECAO.match(linhas[i])), None)
    if fim is None:
        fim = _fim_sem_tags(linhas)
    while fim > inicio + 1 and not linhas[fim - 1].strip():
        fim -= 1
    return fim


def inserir_itens(texto: str, itens: list[str]) -> str:
    novos = _caixas(itens)
    if not novos:
        return texto
    linhas = texto.split("\n")
    fazer = next((i for i, l in enumerate(linhas) if _FAZER.match(l)), None)
    if fazer is not None:
        p = _fim_da_secao(linhas, fazer)
        return "\n".join(linhas[:p] + novos + linhas[p:])
    secao = next((i for i, l in enumerate(linhas) if _SECAO.match(l)), None)
    if secao is not None:
        return "\n".join(linhas[:secao] + ["## Fazer", *novos, ""] + linhas[secao:])
    p = _fim_sem_tags(linhas)
    return "\n".join(linhas[:p] + novos + linhas[p:])


def novo_projeto(nome: str, itens: list[str]) -> str:
    return "\n".join([f"# {' '.join(nome.split())}", "", "## Fazer", *_caixas(itens)])


def itens_da_voz(md: str) -> list[str]:
    """Da nota que o DeepSeek montou: as tarefas; sem tarefa, o título; sem título útil, a transcrição."""
    corpo, _, transcricao = md.partition("\n---\nTranscrição:")
    linhas = corpo.split("\n")
    tarefas = [re.sub(r"^\s*[-*+] (\[ \] ?)?", "", l) for l in linhas[1:] if re.match(r"^\s*[-*+] ", l)]
    if _limpar(tarefas):
        return _limpar(tarefas)
    t = titulo(corpo)
    if t and t != "Ideia por voz":
        return [t]
    return _limpar([transcricao or corpo])


def mover_concluido(texto: str, linha: int) -> str:
    """Depois de marcar/desmarcar a linha: [x] vai para o topo de '## Feito', [ ] volta para o fim do Fazer.

    Só mexe em item de primeiro nível (leva os subitens junto) e só em nota que tem '## Fazer…'.
    """
    linhas = texto.split("\n")
    if not 0 <= linha < len(linhas) or not (m := _ITEM.match(linhas[linha])):
        return texto
    fazer = next((i for i, l in enumerate(linhas) if _FAZER.match(l)), None)
    if fazer is None:
        return texto
    secao = next((linhas[i] for i in range(linha, -1, -1) if _SECAO.match(linhas[i])), "")
    feito = m.group(1) != " "
    if feito == bool(_FEITO.match(secao)):
        return texto  # já está no lugar certo
    fim = linha + 1
    while fim < len(linhas) and linhas[fim].startswith((" ", "\t")) and linhas[fim].strip():
        fim += 1
    bloco = linhas[linha:fim]
    resto = linhas[:linha] + linhas[fim:]
    if feito:
        alvo = next((i for i, l in enumerate(resto) if _FEITO.match(l)), None)
        if alvo is None:
            p = _fim_sem_tags(resto)
            return "\n".join(resto[:p] + ["", "## Feito", *bloco] + resto[p:])
        return "\n".join(resto[:alvo + 1] + bloco + resto[alvo + 1:])
    fazer = next(i for i, l in enumerate(resto) if _FAZER.match(l))
    p = _fim_da_secao(resto, fazer)
    return "\n".join(resto[:p] + bloco + resto[p:])


def gravar_itens(repo: Repositorio, nome: str, novo: bool, itens: list[str]) -> Nota | None:
    """Grava os itens no projeto (ou na Inbox), direto no banco. Projeto que não existe é criado."""
    if not _limpar(itens):
        return None
    nota = achar_nota(repo, nome)
    if nota is None and novo:  # já existe nota com esse título, só não tinha '## Fazer'
        nota = next((n for n in repo.listar() if normalizar(titulo(n.texto)) == normalizar(nome)), None)
    if nota is not None:
        nota = repo.atualizar(nota.id, texto=inserir_itens(nota.texto, itens))
    elif _e_inbox(nome):
        nota = repo.criar("\n".join([f"# {INBOX}", *_caixas(itens)]), "azul")
    else:
        nota = repo.criar(novo_projeto(nome, itens))
    if not nota.projeto_manual and (nota.projeto is None or _e_inbox(nota.projeto) or novo):
        repo.definir_projeto(nota.id, canonico(repo, nome), manual=True)
    return repo.obter(nota.id)


def classificar(repo: Repositorio, pedir=pedir_deepseek, agora: float | None = None,
                limite: int = MAX_POR_RODADA) -> int:
    """Põe no projeto as notas ativas sem projeto (ou na Inbox) cujo texto mudou. Devolve quantas classificou.

    Nota que já está num projeto de verdade fica lá; escolha manual nunca é mexida.
    """
    agora = agora or time.time()
    nomes_ = nomes(repo)
    desc = descricoes(repo)
    feitas = 0
    for n in repo.listar():
        if feitas >= limite:
            break
        if n.projeto_manual or (n.projeto and not _e_inbox(n.projeto)):
            continue
        h = assinatura(n.texto)
        if n.projeto_de == h or agora - n.editada < ESPERA_S or len(normalizar(n.texto)) < 3:
            continue
        if _e_inbox(titulo(n.texto)):  # a própria nota Inbox
            repo.definir_projeto(n.id, INBOX, de=h, manual=True)
            continue
        try:
            escolha = _sugerir_ou_falhar(n.texto, nomes_, lambda t, ns: pedir(t, ns, desc))
        except Exception:  # proxy fora: para e tenta de novo na próxima rodada
            break
        repo.definir_projeto(n.id, escolha, de=h, automatico=True)
        feitas += 1
    return feitas
