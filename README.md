# codex-image skills

Skills do Claude Code para gerar e editar imagens pela conta do **ChatGPT Plus**, sem API key:

- **Codex**: `codex exec --ephemeral` + skill nativa `$imagegen` (gpt-image-2). Sem navegador, sem rastro.
- **GPT**: dirige o chatgpt.com no Chrome logado via [`chrome-use`](https://github.com/leeguooooo/chrome-use) (inspeção de DOM, sem screenshots). A conversa é arquivada no fim.

| Skill | O que faz |
|---|---|
| `/codex-update-models` | Lê os modelos/esforços do Codex (arquivo local) e do ChatGPT (menu do site) e grava `~/.claude/codex-image/config.json`. |
| `/codex-image` | Pergunta cota, modelo e esforço; mostra a imagem no chat e apaga o arquivo. |
| `/codex-image-auto` | O Claude decide tudo, priorizando qualidade; mostra no chat e apaga. |
| `/codex-image-project` | Gera para o projeto aberto: lê pastas e identidade visual, salva com nome descritivo. |

Todas aceitam imagens de referência (coladas no chat ou por caminho) e edição (`--editar`), nas duas cotas.

## Instalar

Requisitos: macOS, `python3`, Codex CLI logado com a conta ChatGPT (`codex login`); para a cota GPT, Chrome logado no chatgpt.com com `chrome-use` e a extensão dele.

```sh
./install.sh
```

Depois, no Claude Code: `/codex-update-models`.

Detalhes, decisões e pendências: [PROGRESSO.md](PROGRESSO.md).
