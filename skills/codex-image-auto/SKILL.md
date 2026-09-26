---
name: codex-image-auto
description: Generates an image with the user's ChatGPT Plus (no API key) without asking anything - Claude picks the quota (Codex or GPT), model, effort and size itself, always prioritizing image quality. Use when the user runs /codex-image-auto, says to decide for them ("escolha você", "decide você", "sem perguntar"), or wants a quick image shown in the chat. For images that belong to the project being worked on (site/app assets), use codex-image-project instead.
---

# codex-image-auto

Mesma geração da `codex-image` (script `~/.claude/codex-image/gerar.py`), mas **sem perguntas**: o Claude decide tudo, sempre priorizando a qualidade da imagem. Nada é salvo como padrão; cada geração decide de novo pelo contexto.

## Passos

1. **Config.** Leia `~/.claude/codex-image/config.json` (só `codex.modelos` e `gpt.opcoes`). Se não existir, diga: "Rode `/codex-update-models` antes." e pare.
2. **Decida** pelas regras abaixo, sem AskUserQuestion. Se o usuário disse algo (cota, modelo, tamanho), isso vence a regra.
3. **Anuncie em uma linha** o que escolheu, ex.: `Codex · gpt-6-astra · xhigh · 1536x1024`. Se for GPT, acrescente: "uma aba do seu Chrome vai abrir".
4. **Rode** (timeout de 620 s):
   ```
   python3 ~/.claude/codex-image/gerar.py --cota <codex|gpt> --prompt "<prompt>" --modelo X --esforco Y --tamanho WxH [--exato] [--pasta DIR] [--ref-chat] [--ref IMG ...] [--editar]
   ```
5. **Entregue sempre renderizando aqui no chat**: toda imagem gerada vai para `SendUserFile` (`display: "render"`, `status: "normal"`), mesmo quando salva no projeto ou em `--pasta` escolhida. Não troque isso por `Read`. Depois siga "Entrega da imagem" da skill `codex-image` (`~/.claude/skills/codex-image/SKILL.md`): arquivo temporário é apagado; arquivo salvo no projeto fica (veja a skill `codex-image-project`).
6. **Se sair `ERRO`**: se for cota do Codex esgotada, troque para GPT uma vez (avisando da aba), com as mesmas referências. Qualquer outro erro: mostre motivo e `COMO CORRIGIR` como vieram e pare.

## Regras de decisão (qualidade primeiro)

- **Imagens de referência**: se o usuário der imagens, siga "Imagens de referência" da `codex-image` (papel de cada imagem no prompt, `--editar` para mudar a própria imagem, não abra as imagens).

- **Cota: Codex.** Controla o tamanho pedido, não abre navegador e não deixa rastro. Use GPT só se o Codex estiver sem cota ou se o usuário pedir.
- **Modelo Codex**: o primeiro de `codex.modelos` (o catálogo vem em ordem de força; o primeiro é o topo de linha).
- **Esforço Codex**: `xhigh` se o modelo tiver; senão o maior da lista dele. A imagem em si sai do gpt-image-2; o raciocínio melhora a leitura do pedido. `max`/`ultra` só somam minutos sem ganho visível na imagem, então só use se o usuário pedir.
- **Modelo GPT**: o primeiro `texto` de `gpt.opcoes` com `grupo` = `Modelo` que não tenha `detalhe` de descontinuação (ex.: "Disponível até ...").
- **Esforço GPT**: o último `texto` com `grupo` = `Esforco` (o mais alto).
- **Tamanho** pelo uso (o script mantém a resolução nativa, que costuma ser maior):
  - ícone, avatar, logo, produto isolado: `1024x1024`;
  - paisagem, banner, hero de site, slide: `1536x1024`;
  - retrato, story, pôster, capa de celular: `1024x1536`;
  - faixa larga (cabeçalho): `1536x512`.
  - `--exato` só quando o destino exige pixels exatos (favicon, espaço fixo num layout).
- **Prompt**: escreva um prompt de imagem completo e específico: assunto e ação, composição e enquadramento, estilo/meio (foto, ilustração vetorial, 3D...), luz, paleta, materiais e texturas, fundo, texto exato entre aspas (curto), e o que evitar. Em português ou inglês, o que for mais preciso para o tema.
- **Várias imagens numa tarefa**: mantenha estilo, paleta e tamanho coerentes entre elas (repita o trecho de estilo no prompt de cada uma).

## Rastros

Iguais aos da `codex-image`: Codex com `--ephemeral` e a cópia em `~/.codex/generated_images/<thread>/` apagada; GPT em chat normal arquivado logo após baixar (o chat temporário não gera imagem; o script nunca exclui conversas).
