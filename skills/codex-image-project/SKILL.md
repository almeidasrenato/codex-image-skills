---
name: codex-image-project
description: Generates images for the project currently being worked on, using the user's ChatGPT Plus (no API key), and saves them inside the project's own asset folder with descriptive names. Claude reads the project to match its folder conventions, visual identity and the size each image needs, and decides quota/model/effort prioritizing quality. Use when the user runs /codex-image-project, or asks for images for this project/site/app (hero, banners, product shots, illustrations, placeholders to replace).
---

# codex-image-project

Gera imagens **para o projeto aberto** e as salva dentro dele. Usa o mesmo script da `codex-image` (`~/.claude/codex-image/gerar.py`) e as mesmas regras de decisão da `codex-image-auto` (qualidade primeiro, sem perguntas, nada salvo como padrão). A diferença: o Claude olha o projeto antes, para a imagem sair no lugar, no tamanho e no estilo certos.

## Passos

1. **Config.** Leia `~/.claude/codex-image/config.json` (só `codex.modelos` e `gpt.opcoes`). Se não existir, diga: "Rode `/codex-update-models` antes." e pare.
2. **Leia o projeto** (rápido, sem varrer tudo):
   - **Pasta de imagens**: a que o projeto já usa, nesta ordem: `public/images`, `public/img`, `public/assets`, `src/assets/images`, `src/assets`, `assets/images`, `assets`, `static/images`, `static`, `images`, `img`. Se o usuário indicar outra, use a dele.
   - **Onde a imagem vai entrar** (se o pedido citar uma página/componente): leia esse arquivo para saber o espaço (proporção, largura em CSS) e o tom do texto ao redor.
   - **Identidade visual**: cores e fontes em `tailwind.config.*`, variáveis CSS (`:root`), tema ou design tokens; e 1 ou 2 imagens já existentes na pasta, para manter o estilo (foto, ilustração flat, 3D...).
3. **Decida** como na `codex-image-auto` (`~/.claude/skills/codex-image-auto/SKILL.md`, "Regras de decisão"): Codex, modelo topo de linha, `xhigh`, tamanho pelo uso. Com o espaço do layout conhecido, escolha a proporção dele. Use `--exato` quando o componente tiver dimensões fixas em pixels.
4. **Prompt**: completo e específico, como na `codex-image-auto`, **mais** a identidade do projeto: paleta em cores concretas (ex.: "azul #1E40AF e laranja #F97316"), estilo das imagens existentes, público e tom do produto. Em várias imagens, repita o mesmo trecho de estilo em todas.
4b. **Referências**: imagens do usuário ou do próprio projeto (ex.: logo, fotos já usadas, um print da página) viram `--ref`, seguindo "Imagens de referência" da `codex-image`. Para manter a identidade, prefira passar 1 ou 2 imagens existentes do projeto como referência de estilo em vez de só descrevê-las. Editar uma imagem do projeto: `--editar` com ela como primeira `--ref`, salvando com nome novo (o original fica intacto).
5. **Nome do arquivo**: curto, descritivo, em kebab-case, pelo papel da imagem (`hero-esportes`, `card-basquete`, `og-image`). Passe em `--nome`; o script nunca sobrescreve (cria `-v2`, `-v3`...).
6. **Anuncie em uma linha**: `Codex · gpt-6-astra · xhigh · 1536x1024 → public/images/hero-esportes.png`.
7. **Rode** (timeout de 620 s), da raiz do projeto:
   ```
   python3 ~/.claude/codex-image/gerar.py --cota codex --prompt "<prompt>" --modelo X --esforco Y --tamanho WxH [--exato] --pasta "<pasta de imagens do projeto>" --nome "<nome>" [--ref-chat] [--ref IMG ...] [--editar]
   ```
8. **Entregue sempre renderizando aqui no chat**: mostre cada imagem gerada com `SendUserFile` (`display: "render"`, `status: "normal"`, caption = caminho relativo no projeto). **Não apague**: o arquivo é do projeto.
9. **Uso no código**: só se o usuário pediu para aplicar (ex.: "coloca no hero"), troque a referência no componente/página, com `alt` descritivo. Se não pediu, diga em uma linha onde ela encaixaria e ofereça aplicar.
10. **Se sair `ERRO`**: igual à `codex-image-auto` (cota do Codex esgotada → GPT uma vez, avisando da aba, com as mesmas referências; outros erros → mostre motivo e `COMO CORRIGIR` e pare).

## Observações

- Formato: o script gera PNG. Se o projeto usa WebP/JPG para fotos pesadas, ofereça converter (`sips -s format jpeg`), não converta sem pedido.
- Nada fica fora do projeto: Codex roda com `--ephemeral` e sem cópia em `~/.codex`; no GPT a conversa é arquivada (veja "Rastros" na `codex-image`).
- Não abra a imagem com Read, a menos que o usuário peça para revisar.
