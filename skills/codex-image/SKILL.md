---
name: codex-image
description: Generates an image with the user's ChatGPT Plus (no API key), asking which quota (Codex or GPT), model and effort to use. Codex = codex exec + $imagegen (gpt-image-2); GPT = chrome-use driving chatgpt.com in the user's logged-in Chrome. Use when the user runs /codex-image or asks to generate an image and wants to choose the options. If the user wants Claude to decide, use codex-image-auto instead.
---

# codex-image

Gera uma imagem pela conta do ChatGPT Plus, sem API key e sem o Claude controlar a tela. Tudo roda pelo script `~/.claude/codex-image/gerar.py`, que imprime só o caminho do PNG (ou `ERRO` + `COMO CORRIGIR`). A imagem é mostrada aqui no chat e o arquivo é apagado (veja "Entrega"). Não há padrões salvos: cada geração pergunta.

Variante sem perguntas, em que o Claude decide tudo priorizando qualidade: `codex-image-auto`.

## Passos

1. **Config.** Leia `~/.claude/codex-image/config.json` (só `codex.modelos` e `gpt.opcoes`). Se não existir, diga: "Rode `/codex-update-models` antes." e pare.
2. **Pergunte com AskUserQuestion**, numa única chamada, o que o usuário ainda não disse no pedido:
   - **Cota**: `Codex` (sem navegador, sem rastro) ou `GPT` (abre uma aba do Chrome; a conversa é arquivada no fim).
   - **Modelo**: Codex, os `slug` de `codex.modelos` na ordem do catálogo (o primeiro é o mais forte); GPT, os `texto` de `gpt.opcoes` com `grupo` = `Modelo`. Com mais de 4 opções, mostre as 4 primeiras; o usuário usa "Other" para as demais.
   - **Esforço**: Codex, `esforcos` do modelo escolhido; GPT, os `texto` de `gpt.opcoes` com `grupo` = `Esforco`.
   - Se a cota for escolhida na mesma chamada, liste modelo/esforço das duas cotas com o prefixo `Codex:` / `GPT:`.
   - Não ofereça "salvar como padrão" e não grave escolhas no config.
3. **Refine o pedido** num prompt de imagem claro: assunto, estilo, composição, luz, cores, fundo, texto exato entre aspas (se houver).
4. **Tamanho**: o que o usuário pedir (`LARGURAxALTURA`), senão `1024x1024`. O script ajusta para as regras do gpt-image-2 (lados múltiplos de 16, proporção até 3:1, mínimo 655.360 px) e mantém a resolução nativa da saída. Só se o usuário exigir o tamanho exato em pixels, passe `--exato`.
5. **Se for GPT**, avise antes, em uma linha: "Uma aba do seu Chrome vai abrir no chatgpt.com para gerar a imagem."
6. **Rode** (timeout de 620 s):
   ```
   python3 ~/.claude/codex-image/gerar.py --cota <codex|gpt> --prompt "<prompt>" --modelo X --esforco Y [--tamanho WxH] [--exato] [--pasta DIR] [--ref-chat] [--ref IMG ...] [--editar]
   ```
7. **Entregue** como em "Entrega da imagem". Texto da resposta: no máximo uma linha (e a linha `AVISO`, se houver).
8. **Se sair `ERRO`**, mostre o motivo e o `COMO CORRIGIR` exatamente como vieram. Não tente de novo em loop.

## Imagens de referência (Codex e GPT)

- **Como chegam**:
  - **Coladas no chat** (o jeito normal): use `--ref-chat`. O script pega as imagens da mensagem mais recente do usuário que tenha imagem (no registro da conversa do Claude Code), na ordem em que foram coladas, e apaga as cópias no fim. Você já vê essas imagens na conversa: não precisa abri-las.
  - **Caminho de arquivo** (arrastado para o chat ou digitado): `--ref <caminho>`.
  - Dá para misturar: as coladas vêm primeiro (Imagem 1, 2...), depois as `--ref`, na ordem dada.
  - Se `--ref-chat` der `ERRO` (formato interno do Claude Code mudou, ou não há imagem colada), mostre o `COMO CORRIGIR` e peça o arquivo arrastado.
- **Não abra as referências de arquivo** (Read): o Codex vê as imagens e escreve ele mesmo o prompt final. O seu papel é dizer, no `--prompt`, o pedido e **o papel de cada imagem, pela ordem**: `Imagem 1 = estilo a seguir. Imagem 2 = paleta e luz. Imagem 3 = produto a manter idêntico.` Se o usuário não disse o papel e não dá para deduzir, pergunte.
- **Criar nova** (padrão): `--ref A --ref B ...` (até ~5; testado com 3).
- **Editar**: quando o pedido é mudar a própria imagem (trocar fundo, luz, remover/adicionar objeto), use `--editar`; a **primeira** `--ref` é a imagem editada, as demais são fontes (ex.: o objeto a inserir). O modelo redesenha o que muda, não cola pixel a pixel.
- Funciona nas duas cotas. No GPT, o script anexa as imagens no chatgpt.com (renomeadas imagem-1..N, na ordem) antes de enviar o pedido; a conversa é arquivada no fim, como sempre.

## Entrega da imagem (nada fica no computador)

- **Padrão**: o script salva numa pasta temporária privada. Envie o PNG com `SendUserFile` (`display: "render"`, `status: "normal"`, caption de uma linha com cota · modelo · esforço) e, logo depois, apague o arquivo com `rm "<caminho>"`. O app guarda a própria cópia no card: o usuário abre e baixa por ali. Não mostre o caminho temporário.
- **Pedido já é para o projeto** (ex.: asset de site): siga a skill `codex-image-project` (salva na pasta de imagens do projeto, com nome descritivo, e não apaga).
- **Sem `SendUserFile`** (ex.: `claude` num terminal comum): rode com `--pasta "<raiz do projeto>/codex-image-geradas"` e diga o caminho.
- **"Aplica no projeto" depois**: o arquivo temporário já foi apagado. Peça o arquivo baixado pelo card (normalmente em `~/Downloads`) ou gere de novo.
- Não abra a imagem (Read), a menos que o usuário peça.

## Rastros

- **Codex**: roda com `--ephemeral` (sem sessão, sem thread no app) e o script apaga a cópia em `~/.codex/generated_images/<thread>/`. Sobra só a cota gasta.
- **GPT**: o chat temporário do ChatGPT não gera imagem, então o script usa um chat normal e o **arquiva** logo após baixar (some da barra lateral; fica em Configurações > Chats arquivados, e a imagem pode continuar na Biblioteca). No app ChatGPT/Codex para Mac o chat some só na próxima vez que o app abrir (o script oculta o chat no catálogo local do app e pede uma reconciliação completa). O script nunca exclui conversas; o usuário apaga em lote em Configurações > Controles de dados > Excluir chats arquivados.

## Onde o Codex salva

O script procura, nesta ordem: PNG no diretório de trabalho temporário, `~/.codex/generated_images/<thread>/`, qualquer PNG novo em `~/.codex/generated_images/`, e por fim base64 no log da sessão.

## GPT

Tudo numa aba do Chrome via `chrome-use` (sessão `codex-image`): abre chatgpt.com, escolhe o modelo (item de rádio) e o esforço (slider) no menu "Selecionar modelo do ChatGPT", envia o pedido, espera o `<img alt="Imagem N gerada">` ficar estável, baixa o blob e arquiva a conversa. A escolha de modelo/esforço fica marcada no site. Se o menu mudar, rode `/codex-update-models`. Se o ChatGPT recusar o pedido, o script só percebe no limite de 5 min.
