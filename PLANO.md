# Recados — post-its estilo Stickies (macOS) para Fedora/GNOME

Substitui o Tarefas (abandonado em 01/11/2026). Ambiente: Fedora, GNOME 50.5, Wayland.

## Arquitetura (decidida 01/11)
- **App** Python 3 + GTK4 + libadwaita + GtkSourceView 5 (já instalados). Cada nota = uma janela pequena, sem barra de título.
- **Extensão GNOME** `recados@joaowgf` (mínima): só guarda e restaura posição/tamanho das janelas do app (Wayland não deixa o app se posicionar). Fala com o app por D-Bus; nada de lógica de notas nela.
- **Dados**: SQLite em `~/.local/share/recados/recados.db` (id, texto Markdown, cor, x, y, largura, altura, sempre-no-topo, recolhida, criada, editada). Sem rede, sem servidor.

## Requisitos (MVP)
1. Nova nota: atalho global (Super+Alt+N) e menu do ícone do app.
2. Editar em Markdown com destaque ao digitar (títulos, **negrito**, *itálico*, `código`, listas, links).
3. Checklist: `- [ ]` vira caixa clicável; clicar marca `[x]` no texto.
4. Modo leitura: alternar entre texto cru e Markdown renderizado (Ctrl+E).
5. 6 cores (amarelo padrão, como o Stickies), trocáveis pelo menu da nota.
6. Recolher a nota na barra de título (duplo clique), como no Stickies.
7. Salvar sozinho a cada alteração (sem botão salvar).
8. Reabrir todas as notas no login, no mesmo lugar e tamanho (via extensão).
9. Apagar com desfazer (5 s).
10. Migração: os 12 itens do Tarefas viram notas (título como `# título`, descrição embaixo, tags como `#tag`).

Fora do MVP: busca, sincronizar entre PCs, imagens, exportar.

## Ondas (testes antes do código, red→green)
| Onda | Entrega | Aceite | Tempo |
|---|---|---|---|
| 1 | Banco + modelo de nota | `pytest` (CRUD, autosave) | ~2 h |
| 2 | Janela da nota: editor + destaque Markdown + cores + recolher | `pytest` + abrir e usar | ~1 dia |
| 3 | Checklist clicável + modo leitura | `pytest` do parser de checklist | ~4 h |
| 4 | Extensão de posição + autostart + atalho global | reiniciar sessão, notas voltam no lugar | ~1 dia |
| 5 | Migração do Tarefas + desligar `tarefas.service` (código e banco ficam) | 12 notas criadas | ~1 h |
| 6 | Entrar no Ping (projects.yaml) | aparece no painel | ~15 min |

Total: uns 3–4 dias de trabalho.
