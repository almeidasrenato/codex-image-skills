Quero continuar um projeto de duas skills para gerar imagens pelo meu ChatGPT Plus, sem API key. Contexto e tarefas abaixo.

## Contexto (já decidido)

- Estou no macOS (Apple Silicon). Tenho o Codex CLI instalado e logado com minha conta do ChatGPT Plus.
- Nada de OPENAI_API_KEY. Nada de o Claude controlar minha tela (sem screenshots/cliques do Claude). Tudo via scripts no terminal, com saída curta para gastar poucos tokens.
- São duas skills, com nomes em inglês começando com "codex":
  1. `codex-update-models` (`/codex-update-models`): já pronta, anexada como SKILL.md. Lê os modelos do Codex (`~/.codex/models_cache.json`) e os do ChatGPT web (abre chatgpt.com numa aba do meu Chrome via `chrome-use`, lê o menu de modelo/esforço, fecha a aba) e grava tudo em `~/.claude/codex-image/config.json`.
  2. `codex-image` (`/codex-image`): ainda NÃO existe. É a que gera a imagem.
- Os dois caminhos de geração gastam cotas diferentes do meu Plus:
  - **Codex**: `codex exec` + skill nativa `$imagegen` (gpt-image-2), com `-m <modelo>` e `-c model_reasoning_effort="<esforço>"`. Sem navegador.
  - **GPT**: cota do chat do ChatGPT, via a ferramenta `image-use` (github.com/leeguooooo/image-use) com `--backend web`, que dirige meu Chrome logado pela extensão `chrome-use`. Ela seleciona o item do menu pelo texto exato (`--web-model "<rótulo>"`). Meu ChatGPT está em português (ex.: o seletor mostra "Alta"). O nível "Pro" não gera imagem e deve ser ocultado.

## Tarefas, nesta ordem

1. **Instalar a codex-update-models**: copie o SKILL.md anexado para `~/.claude/skills/codex-update-models/SKILL.md` (crie a pasta). Não altere o conteúdo.
2. **Rodar `/codex-update-models`** seguindo a skill. Se a parte GPT der ERRO, me mostre o motivo e o "COMO CORRIGIR" e me ajude a instalar o que faltar (chrome-use, extensão, image-use). Não tente em loop.
3. **Validar a leitura do menu do ChatGPT**: o leitor foi testado só numa página simulada. Confira se os grupos/itens gravados em `gpt.opcoes` batem com o menu real (modelos GPT-5.6 / GPT-5.5 e os níveis de esforço). Se não baterem, ajuste o JS do script (`JS_BOTAO` / `JS_MENU`), suba `VERSAO` e atualize o SKILL.md.
4. **Criar a skill `codex-image`** em `~/.claude/skills/codex-image/SKILL.md`, com um script próprio (Python stdlib) salvo em `~/.claude/codex-image/`. Requisitos:
   - Ler `~/.claude/codex-image/config.json`. Se não existir, orientar a rodar `/codex-update-models` antes.
   - Perguntar com opções clicáveis (AskUserQuestion), pulando o que já tiver padrão salvo: **cota** (GPT ou Codex), **modelo** e **esforço** (listas do config), e oferecer "salvar como padrão".
   - O Claude refina meu pedido num prompt de imagem claro. O script recebe prompt, tamanho e pasta, gera, e imprime **só o caminho do PNG** (ou `ERRO` + `COMO CORRIGIR`, no mesmo formato da codex-update-models).
   - Codex: tratar os locais de saída que mudam entre versões (arquivo no diretório de trabalho, `~/.codex/generated_images/`, ou base64 no log da sessão) e respeitar as regras de tamanho do gpt-image-2 (lados múltiplos de 16, proporção até 3:1, mínimo de 655.360 pixels).
   - GPT: selecionar modelo **e** esforço no menu antes de gerar. O `--web-model` da image-use só clica um item de primeiro nível; verifique se ela lida com o submenu de modelos e, se não lidar, faça a seleção com `chrome-use` antes de chamar a image-use.
   - Avisar antes de rodar o caminho GPT que uma aba do Chrome vai abrir.
   - Revisar a imagem (abrir o PNG) só se eu pedir.
5. **Teste real**: gere uma imagem pequena por cada caminho (ex.: "ícone minimalista de foguete azul, fundo branco") e me mostre os caminhos dos arquivos.

Ao final, me dê um resumo curto do que foi instalado, o que funcionou e o que ficou pendente.
