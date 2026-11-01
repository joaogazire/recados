# Post-it v2: plano (01/11/2026)

Em ordem de esforço, do menor para o maior. Os tempos são de relógio, com o Sonnet 5.5 em esforço médio no Claude Code, e já incluem o teste vermelho, a implementação, o code-review e o commit.

## 1. Fixar no topo + nota do dia (~25 min)
- Botão de alfinete na barra da nota que liga e desliga o `sempre_no_topo`. A coluna já existe no banco.
- No Wayland o app GTK não consegue se colocar por cima das outras janelas. Quem faz isso é a extensão, com `make_above()` nas janelas cujo título é "Post-it N" e que estão marcadas. O app avisa a extensão pelo arquivo `fixadas.json`.
- "Nota do dia" fica na central e em Ctrl+D. Ela abre (ou cria) a nota `# 01/11/2026 (dom)`. A de hoje é encontrada pelo título.

## 2. Busca na central (~25 min)
- Um campo de texto no topo do menu do ícone do painel. Você digita "pão" e a lista mostra só as notas que têm "pão" no texto. Cada resultado traz o trecho do texto. Clicar abre a nota.
- Para isso, o `recados --listar` passa a mandar também um trecho do texto, e a busca acontece na própria extensão.

## 2b. Resumo de até 5 palavras na central (pedido em 01/11, junto com o item 2)
- A lista do painel mostra um resumo de no máximo 5 palavras por nota, em vez da primeira linha inteira.
- O resumo é gerado pelo DeepSeek, pelo proxy 127.0.0.1:8787 (chave lida de `~/.local/share/opencode/auth.json` e mandada só para o proxy local). Fica guardado no banco com o hash do texto e é refeito só quando o texto muda.
- Roda em segundo plano depois de salvar a nota. Se o DeepSeek falhar, a lista usa as primeiras 5 palavras do título.

## 3. Captura rápida por texto (~35 min)
- O Super+Alt+N abre uma caixinha de uma linha só. Você digita, aperta Enter e o texto vira um `- [ ] texto` no fim da nota "Inbox", que é criada se não existir. Esc cancela.
- "Nova nota" continua no painel e no Ctrl+N.

## 4. Central de status: concluídas, canceladas e arquivadas (~50 min)
- Coluna nova `estado` com os valores ativa, concluida, cancelada e arquivada, mais a data da mudança. A migração do banco é automática.
- Na barra da nota entra um menu ⋯ com Concluir, Cancelar e Arquivar. A nota sai da tela. A lixeira continua sendo o "apagar de vez".
- Nota com todas as caixas marcadas mostra um aviso "Tudo feito, concluir?".
- Na central do painel aparecem 3 submenus recolhíveis (Concluídas, Canceladas e Arquivadas), cada um com a quantidade. Um clique reabre a nota como ativa.

## 5. Lembretes com data + Google Agenda (~1 h 30)
- Você escreve numa linha `@amanhã 9h`, `@sex`, `@15/11 14h30` ou `@hoje 18h`. O realce marca a data, e o modo leitura mostra um chip com "sex 07/11 09:00".
- Na hora marcada sai uma notificação do GNOME, e clicar nela abre a nota. A central lista "Vencidos" e "Próximos".
- Google Agenda: cada linha com data vira um evento de 30 min no calendário "Post-it". Marcar `[x]` na tarefa apaga o evento, e mudar a data atualiza.
- Reaproveita o OAuth do Agenda Esportiva, que já tem o escopo `calendar`. O app OAuth está em modo Teste, então o token pode expirar em 7 dias e aí você precisa autorizar de novo com um clique.
- A sincronização roda quando a nota é salva, fora da interface, e sem internet fica na fila.

## 6. Ideia por voz → resumo no Post-it (~1 h 45)
- O DeepSeek não transcreve áudio, porque não tem API de fala. Fica assim:
  1. **Gravar**: um atalho, por exemplo Super+Alt+V, liga e desliga a gravação com `pw-record`. O ícone do painel fica vermelho enquanto grava.
  2. **Transcrever**: com o `faster-whisper` local, grátis e sem internet, modelo `small` em pt-BR. São cerca de 500 MB para baixar uma vez, e 30 s de fala levam uns 5 a 10 s de CPU.
  3. **Resumir**: o DeepSeek, pelo proxy que já está rodando em 127.0.0.1:8787 com a chave disponível, então o uso já aparece no AI Usage Monitor. O prompt devolve um título e de 1 a 5 tópicos ou tarefas `- [ ]`, sem inventar nada.
  4. **Gravar a nota**: cria uma nota verde com o resumo e, embaixo, a transcrição original numa seção recolhível.
- Sem internet, a nota fica só com a transcrição.

## Total
Cerca de 5 h 30 de relógio. Os passos que dependem de você ficam fora dessa conta: autorizar o Google (1 min) e esperar o download do modelo do Whisper (2 a 5 min).

## Status (01/11, fim do dia)
TODOS FEITOS: 1 (f99886c), 2+2b (9964bd6), 3 (45258c7), 4 (9f67772), 5 (aa24ec0), 6 (1f71476). 117 pytest.

## Decisão (01/11)
Agora: itens 1, 2 e 2b. Depois: 3, 4, 5 e 6 (voz do jeito descrito acima).

## Ordem sugerida
As 4 primeiras, uma por commit, numa sessão só (cerca de 2 h 15). Depois o item 5 e por último o 6, porque são os que dependem de serviços de fora.
