# Post-it v3: projetos no lugar da Inbox (05/11/2026)

Pedido: "parar com essa questão de Inbox; filtrar por projeto e, dentro do projeto, ter o to-do do que vai fazer".

## Estado de hoje (feito em 05/11, só nos dados)
- Uma nota por projeto, título `# Projeto`, seções `## Fazer` e `## Feito` (às vezes `## Depois`/`## Cancelado`), tag `#projeto` no fim.
- Ativas: Steamlog (20, azul), Post-it (23, amarelo), Estante (22, verde), Closet assist (1, rosa).
- Histórico: Rotas (3), Vagou (2), Emerald TCG (21), AI Usage Monitor (25), Inventário Steam (26); Steamlog completa (24) segue arquivada.
- A Inbox (19) e as notas fundidas foram para a lixeira (somem de vez em 30 dias). Backup: `~/.local/share/recados/recados.db.bak-pre-projetos-20261105-221417`.
- A Inbox volta só como destino do que não tem relação com nenhum projeto.

## Pré-requisito
- Feito: trabalho de 02/11 commitado em 9517e16.

## Feito (05/11, noite)
Decisões do usuário: as 3 recomendadas, e a Inbox fica, mas só para o que não tem relação com nenhum projeto.
- Projeto = nota ativa `# Nome` com `## Fazer…` (sem coluna nova no banco). `recados/projetos.py`.
- Ctrl+N, Super+Alt+N e voz abrem a mesma caixinha: palpite local (nome citado no texto) → DeepSeek (só nomes da lista) → Inbox.
- Item entra no fim do primeiro `## Fazer…`; `[x]` desce para o topo de `## Feito` com os subitens.
- Ficou para depois: onda 4 (central do painel filtrada por projeto). Hoje cada projeto já é uma linha da central com o contador; filtro mexe na extensão e só aparece depois de relogar.

## Plano original (referência)

## Modelo
- **Projeto = nota principal** com título `# Nome`. O to-do é o checklist dela.
- Coluna nova `projeto TEXT` (migração automática). Na migração, cada nota ativa ganha `projeto` = título sem `#`. Notas extras (ideia por voz, plano arquivado) podem apontar para o mesmo projeto.
- Item novo entra no fim de `## Fazer` (cria a seção se não existir). Item marcado `[x]` desce para `## Feito`.

## Ondas (tempos com Sonnet em esforço médio, já com teste vermelho, code-review e commit)

### 1. Projeto no banco + `--listar` (~30 min)
- Coluna `projeto`, migração pelo título, `Repositorio.projetos()` → nome, id da nota principal, abertas/total.
- `--listar` manda `projeto` e o contador de cada nota.
- Teste: banco com notas `# Steamlog` e `# Estante` → `projetos()` devolve os dois com as contagens certas.

### 2. Item novo vai para o projeto, sem Inbox (~45 min)
- `captura.py`: `capturar(repo, projeto, item)` acrescenta `- [ ] item` em `## Fazer` da nota do projeto. Projeto que não existe → cria `# Projeto\n\n## Fazer\n- [ ] item`.
- Sai `TITULO_INBOX`/`achar_inbox`. Nada mais cria `# Inbox`.
- Teste: capturar em "Steamlog" põe o item antes de `## Feito`; capturar em projeto novo cria a nota.

### 3. Caixinha de captura com projeto (~45 min)
- Super+Alt+N e "Nova nota" abrem a caixinha com 2 campos: **projeto** (lista dos projetos ativos, com autocompletar e "+ novo projeto") e **o que fazer**.
- Projeto em branco: o DeepSeek sugere um dos projetos existentes (proxy 127.0.0.1:8787, mesmo esquema do resumo) e preenche o campo; Enter confirma. Sem DeepSeek, o campo vem com o último projeto usado.
- Não existe "sem projeto": Enter só grava com um projeto escolhido.

### 4. Central filtrada por projeto (~1 h)
- No topo do menu do painel: a lista de projetos com "N a fazer". Clicar num projeto mostra só os itens abertos dele (clicar no item abre a nota do projeto) e as notas extras do projeto.
- "Todos" continua existindo; busca e submenus de Concluídas/Canceladas/Arquivadas respeitam o filtro.
- Teste JS: `filtrarPorProjeto(notas, 'Steamlog')` devolve só as notas do Steamlog.

### 5. Voz entra num projeto (~30 min)
- Super+Alt+V: depois da transcrição, o DeepSeek resume e sugere o projeto; abre a caixinha da onda 3 já preenchida para você confirmar. Deixa de criar nota verde solta.

### 6. `[x]` desce para `## Feito` (~20 min)
- Ao marcar um item, ele sai de `## Fazer` e vai para o topo de `## Feito`. Ao desmarcar, volta.

**Total: ~4 h.** Ordem: 1 → 2 → 3 → 4; 5 e 6 são independentes.

## Decisões em aberto (pedir ao usuário antes da onda 1)
1. Projeto = uma nota só com o to-do (recomendado) ou várias notas soltas por projeto?
2. Projeto em branco: DeepSeek sugere e você confirma (recomendado) ou cai no último projeto usado sem perguntar?
3. Mover `[x]` para `## Feito` automaticamente (onda 6): sim ou não?
