# Post-it

Post-its com Markdown na área de trabalho do Fedora/GNOME, no estilo dos Stickies do macOS. Cada nota é uma janelinha colorida que fica onde você deixou. Também dá para:

- anotar uma ideia rápida pelo teclado;
- falar uma ideia e ver o texto aparecer na nota enquanto fala;
- marcar tarefas;
- receber lembretes no GNOME e no Google Agenda;
- ver tudo pelo ícone no painel do GNOME.

> No código o projeto se chama **recados** (pasta, comando `recados`, banco). "Post-it" é o nome que aparece na tela.

---

## Instalar

### 1. O que precisa ter

Fedora com GNOME 50 (Wayland). Instale os pacotes do sistema:

```bash
sudo dnf install python3-gobject gtk4 libadwaita gtksourceview5 python3-numpy pipewire-utils
```

`pipewire-utils` traz o `pw-record`, que grava o microfone para a ideia por voz.

### 2. Rodar o instalador

```bash
git clone <este repositório> ~/Documentos/Code/recados   # ou use a pasta que já tem
cd ~/Documentos/Code/recados
./instalar.sh
```

O instalador pode ser rodado de novo sem estragar nada. Ele faz o seguinte:

| O quê | Onde |
|---|---|
| Comando `recados` | `~/.local/bin/recados` |
| Atalho no menu de aplicativos ("Post-it") | `~/.local/share/applications/` |
| Abrir sozinho ao entrar na sessão | `~/.config/autostart/` (com `--sessao`) |
| Extensão do GNOME (ícone no painel, posições, fixar por cima) | `~/.local/share/gnome-shell/extensions/recados@joaogazire` |
| Atalhos globais **Super+Alt+N** (captura) e **Super+Alt+V** (voz) | Configurações → Teclado → Atalhos personalizados |
| Whisper para a voz (~470 MB, só na 1ª vez) | `~/.local/share/recados/voz-venv` |

### 3. Sair e entrar na sessão

O GNOME só carrega uma extensão nova depois que você sai e entra na sessão de novo. Para conferir:

```bash
gnome-extensions info recados@joaogazire   # deve mostrar "Estado: ACTIVE"
```

### Opcionais

- **Resumos e ideia por voz com IA** usam o DeepSeek pelo proxy do [AI Usage Monitor](../ai-usage-monitor) (`127.0.0.1:8787`). A chave é lida de `~/.local/share/opencode/auth.json`. Sem isso, tudo continua funcionando: a central mostra as primeiras palavras da nota e a voz salva só a transcrição.
- **Google Agenda** reaproveita a autorização do [Agenda Esportiva](../agenda-esportiva) (`~/.config/agenda-esportiva/token.json`). Sem ela, os lembretes continuam chegando como avisos do GNOME, só não vão para o Google.

---

## Usar

### Notas

| Ação | Como |
|---|---|
| Nova nota | **Ctrl+N** numa nota, ou "Nova nota" no painel |
| Mostrar todas | `recados`, ou "Mostrar todas" no painel |
| Ler ↔ editar o Markdown | **Ctrl+E**, ou o ícone de olho |
| Recolher só para a barra | Duplo clique na barra de cima |
| Mudar a cor | Ícone de paleta (amarelo, azul, verde, rosa, roxo, cinza) |
| Fonte e tamanho | Ícone de fonte: Sans, Serifa ou Mono; tamanhos P, M, G e GG |
| Fixar por cima das outras janelas | Ícone de alfinete |
| Concluir, cancelar ou arquivar | Ícone ⋯. A nota sai da tela e vai para a central |
| Apagar | Lixeira. Aparece "Desfazer" por 5 s |

As notas salvam sozinhas 5 s depois da última tecla e também ao fechar. Uma nota nova só é salva se você escrever alguma coisa nela.

A nota com texto abre no **modo leitura**: Markdown formatado e caixinhas que você marca com um clique. Quando todas as caixas estiverem marcadas, aparece **"Tudo feito ✓ → Concluir nota"**.

#### Markdown que a nota entende

```markdown
# Título            ## Subtítulo
- item              1. item numerado
- [ ] tarefa        - [x] tarefa feita
**negrito**  *itálico*  `código`  [link](https://...)
```

### Captura rápida: **Super+Alt+N**

Abre uma caixinha de uma linha. Escreva e aperte **Enter**: o texto vira `- [ ] ...` no fim da nota **Inbox**, que é criada na primeira vez. **Esc** cancela.

### Ideia por voz: **Super+Alt+V**

1. Aperte **Super+Alt+V**. Abre uma nota verde com **● Gravando 0:00**, e o ícone do painel fica vermelho.
2. Fale. O texto vai aparecendo na nota a cada 2 ou 3 s, transcrito pelo Whisper no seu PC, sem internet.
3. Para terminar, aperte **Super+Alt+V** de novo ou clique em **Parar**. Depois de 5 minutos a gravação para sozinha.
4. A nota mostra "Resumindo a ideia…". Em seguida vira uma nota verde com:
   - um título e tópicos ou tarefas `- [ ]`, resumidos pelo DeepSeek;
   - a transcrição original no fim.

O áudio é apagado depois de processado.

### Lembretes com data

Escreva numa linha:

| Você escreve | Vira |
|---|---|
| `@hoje 18h` | hoje às 18:00 |
| `@amanhã 9h` | amanhã às 09:00 |
| `@sex` ou `@sexta` | a próxima sexta, às 09:00 |
| `@15/11 14h30` | 15/11 às 14:30 |
| `@10/01/2027 7h` | data com ano |

- Ao salvar, as datas relativas viram datas fixas: `@amanhã` vira `@02/11`. Assim o lembrete não muda de dia sozinho.
- Na hora marcada chega um **aviso do GNOME**. Clicar nele abre a nota.
- Cada lembrete aparece no calendário **"Post-it"** do Google Agenda, como um evento de 30 min. Marcar `[x]` antes da hora tira o evento da agenda. Eventos que já passaram ficam lá como histórico.

### Nota do dia: **Ctrl+D**

Abre a nota do dia, ou cria uma com `# 01/11/2026 (dom)` e uma tarefa vazia. Ela só é salva se você escrever algo.

### Central no painel do GNOME

O ícone é uma **pilha de post-its**:

- com nenhuma tarefa pendente, aparece 1 post-it com ✓;
- com tarefas pendentes, a pilha vai de 1 a 4 folhas, conforme a quantidade comparada à sua média dos últimos 14 dias;
- enquanto grava uma ideia por voz, a pilha fica vermelha.

Ao clicar no ícone, o menu mostra:

1. **Busca**: digite para procurar em todas as notas. Ignora acentos e maiúsculas e mostra o trecho onde a palavra aparece.
2. **Lembretes**: os vencidos em vermelho e os dos próximos 7 dias.
3. **Notas ativas**: um resumo de até 5 palavras e o progresso (`2/5`, `✓ 3`). Clicar traz a nota para a frente, mesmo que esteja fechada ou minimizada.
4. **Concluídas / Canceladas / Arquivadas**: clicar reabre a nota.
5. **Nova nota · Nota do dia · Mostrar todas · Preferências**.

### Preferências

Abra pelo ícone de engrenagem numa nota, por "Preferências" no painel, ou com `recados --preferencias`. Dá para escolher:

- a fonte e o tamanho das notas novas;
- se as notas abrem em leitura ou em edição;
- se as notas aparecem ao entrar na sessão.

### Linha de comando

```text
recados                 mostra todas as notas
recados --nova          nota nova
recados --capturar      captura rápida
recados --voz           começa/para a gravação de uma ideia
recados --hoje          nota do dia
recados --abrir ID      traz a nota ID
recados --reabrir ID    reabre uma nota concluída/cancelada/arquivada
recados --preferencias  preferências
recados --listar        imprime as notas em JSON (usado pela extensão)
```

---

## Onde ficam os dados

| Arquivo | Conteúdo |
|---|---|
| `~/.local/share/recados/recados.db` | as notas (SQLite) |
| `~/.config/recados/preferencias.json` | preferências |
| `~/.local/share/recados/posicoes.json` | posição de cada nota na tela (gravado pela extensão) |
| `~/.local/share/recados/fixadas.json` | notas fixadas por cima |
| `~/.local/share/recados/agenda.json` | ligação entre lembretes e eventos do Google |
| `~/.local/share/recados/avisados.json` | lembretes já avisados |
| `~/.local/share/recados/pendentes-por-dia.json` | histórico usado pelo ícone de pilha |

Backup: copie `recados.db` com o app fechado, ou use `sqlite3 recados.db ".backup copia.db"`.

**Privacidade:** o texto das notas (para os resumos de 5 palavras) e as transcrições da voz vão para o DeepSeek. O áudio nunca sai do PC.

---

## Desenvolvimento

```bash
python3 -m pytest -q        # testes Python + lógica da extensão (via gjs) + sintaxe ES (via node)
python3 -m recados          # roda direto da pasta
```

- `recados/`: o app (GTK4 + libadwaita + GtkSourceView).
- `extensao/recados@joaogazire/`: a extensão do GNOME Shell. A lógica pura fica em `central.js` e `posicoes.js`, e cada parte tem teste em `tests/js/`.
- Para testar a extensão sem sair da sessão, use um GNOME Shell aninhado: `dbus-run-session -- gnome-shell --devkit --wayland`, com `XDG_DATA_HOME` e `XDG_CONFIG_HOME` apontando para pastas temporárias.
- Os planos e o histórico de decisões estão em `PLANO.md` e `PLANO-v2.md`.
