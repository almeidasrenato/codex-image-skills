# Progresso: skills codex-image

Estado em 25/09/2026. Serve para retomar o trabalho numa sessão nova do Claude Code.

## Onde fica cada coisa

| O quê | Instalado em | No repositório |
|---|---|---|
| Skills | `~/.claude/skills/<nome>/SKILL.md` | `skills/<nome>/SKILL.md` |
| Script de geração (`VERSAO 8`) | `~/.claude/codex-image/gerar.py` | `scripts/gerar.py` |
| Leitor de modelos (`VERSAO 6`) | `~/.claude/codex-image/update_models.py` | `scripts/update_models.py` |
| Listas de modelos | `~/.claude/codex-image/config.json` | não versionado (gerado) |
| Wrapper do Codex CLI | `~/.local/bin/codex` (chama `/Applications/ChatGPT.app/Contents/Resources/codex`) | não versionado |

O repositório é a cópia de referência. Depois de editar algo em `~/.claude`, copie de volta (ou edite aqui e rode `./install.sh`).
O `SKILL.md` da `codex-update-models` embute o script inteiro; ao mudar `update_models.py`, suba `VERSAO` e atualize o bloco "Script" dele.

## Skills

- **`/codex-update-models`**: Codex lido de `~/.codex/models_cache.json` (em ordem de força; o primeiro é o topo de linha). GPT lido do menu do chatgpt.com via `chrome-use`, sem enviar mensagem. Grava só listas (sem padrões).
- **`/codex-image`**: pergunta cota, modelo e esforço (AskUserQuestion). Nada é salvo como padrão.
- **`/codex-image-auto`**: sem perguntas; regras: Codex, primeiro modelo do catálogo, `xhigh`, tamanho pelo uso (1024x1024 ícone, 1536x1024 paisagem, 1024x1536 retrato, 1536x512 faixa). Se a cota do Codex acabar, vai ao GPT uma vez.
- **`/codex-image-project`**: lê o projeto (pasta de imagens, espaço no layout, cores do Tailwind/CSS, imagens existentes), salva na pasta de imagens com `--nome` (nunca sobrescreve: `-v2`...). Só altera código se pedirem.

## Script `gerar.py`

```
python3 ~/.claude/codex-image/gerar.py --cota codex|gpt --prompt "..." --modelo X --esforco Y
  [--tamanho WxH] [--exato] [--pasta DIR] [--nome N] [--ref IMG ...] [--ref-chat] [--editar]
```

- Saída: só o caminho do PNG, ou `ERRO` + `COMO CORRIGIR`.
- Tamanho: ajusta às regras do gpt-image-2 (lados múltiplos de 16, proporção até 3:1, mínimo 655.360 px). Mantém a resolução nativa; `--exato` redimensiona com `sips`.
- Pasta padrão: temporária privada do usuário (`tempfile.gettempdir()/codex-image`).
- `--ref-chat`: pega as imagens coladas na última mensagem com imagem, lendo `~/.claude/projects/*/<CLAUDE_CODE_SESSION_ID>.jsonl` (formato interno, sem documentação). Com `/comando`, a imagem vem numa entrada `isMeta`.
- `--editar`: a primeira referência é a editada; as demais são fontes.

## Entrega e rastros

- **Chat (padrão)**: a skill mostra o PNG com `SendUserFile` (render) e apaga o arquivo. O app guarda a própria cópia no card (testado: abre e baixa depois de apagado). Limite: para revisar ou aplicar depois, o usuário baixa pelo card ou salva no projeto.
- **Sem o app** (terminal comum): salva em `codex-image-geradas/` na raiz do projeto.
- **Codex**: `--ephemeral` (sem thread/sessão no app) e o script apaga `~/.codex/generated_images/<thread>/`. Medido: nada novo em `~/.codex`, fora 3 linhas genéricas em `logs_2.sqlite`.
- **GPT**: o chat temporário do ChatGPT **não gera imagem**. O script usa chat normal e **arquiva** a conversa (PATCH `is_archived`). Nunca exclui; o usuário apaga em lote em Configurações > Controles de dados > Excluir chats arquivados. A imagem pode ficar na Biblioteca do ChatGPT.

## Caminho GPT (como o `chrome-use` é usado)

Tudo por inspeção de DOM (`eval` de JS, seletores CSS/XPath), sem screenshots, numa aba da sessão `codex-image`:
1. Abre chatgpt.com; composer = `.ProseMirror` (o `#prompt-textarea` sumiu).
2. Menu: botão `button[aria-haspopup="menu"][aria-label*="odel"]` ("Selecionar modelo do ChatGPT"); só abre com clique por **seletor** (coordenada não abre).
3. Modelos: `menuitemradio` (GPT-5.6 Sol, GPT-5.5). Esforço: slider `[data-reasoning-slider]` (Instantânea / Média / Alta), movido com setas; rótulo em `aria-describedby`.
4. Referências: `upload` em `form input[type="file"][accept="image/*"]` (renomeadas `imagem-1..N`); espera prévias e botão "Enviar".
5. `fill` no composer + Enter; espera um `<img alt="Imagem N gerada">` ficar igual em 2 leituras; `download-url` do blob; arquiva.

## Testes feitos (todos reais)

- Codex: geração simples; 3 referências; edição com 2 imagens; edição de foto colada no chat (sala: junção parede/piso + rodapé) e 2ª edição (parede azul).
- GPT: geração simples; edição com referência (parede azul), ~1 min.
- Rastros: Codex sem sobras em `~/.codex`; GPT arquivado (histórico inalterado).

## Tokens (medido nesta sessão)

- Gerar não gasta tokens do Claude (gasta cota do Plus). Por imagem: ~1–3 mil de saída e ~3–10 mil de entrada nova.
- O que pesa é a releitura do contexto a cada chamada: numa sessão longa (~280 mil), uma geração simples leu ~590 mil de cache; numa sessão nova seria ~75 mil.
- Dicas: gerar em sessão nova ou após `/clear`; verificar com zoom só quando preciso; evitar acumular imagens coladas.

## Pendências e limites

- GPT: se o ChatGPT recusar o pedido, o script só percebe no limite de 5 min.
- `--ref-chat` depende do formato interno do registro do Claude Code; se mudar, usar `--ref` com o arquivo arrastado.
- Imagens de referência testadas até 3 (recomendado até ~5).
- Proporção diferente da pedida não é corrigida (só redimensiona com `--exato` se a proporção bater).
- Chrome ficou "gerenciado pela organização" pela política do `chrome-use` (trava DNS seguro). Desfazer: `profiles remove -identifier com.leeguoo.chrome-use.connect`.
- Sobras de testes antigos: PNGs em `~/Pictures/codex-image/`, 2 threads de teste no histórico do app Codex (anteriores ao `--ephemeral`), 2 chats arquivados no ChatGPT.
