---
name: codex-update-models
description: Updates the Codex and ChatGPT (GPT) model and reasoning-effort lists used by the codex-image skill. Codex is read from a local file; GPT briefly opens chatgpt.com in a tab of the user's logged-in Chrome to read the model menu (no message sent, no quota used). Use when the user runs /codex-update-models or asks to update or see the latest models.
---

# codex-update-models

Atualiza as listas que a skill `codex-image` usa para perguntar "de qual cota gastar, qual modelo e qual esforço". Grava tudo em `~/.claude/codex-image/config.json`.

| Fonte | Como lê | Gasta cota? | O que o usuário vê |
|---|---|---|---|
| Codex | arquivo local `~/.codex/models_cache.json` (o mesmo do seletor do app) | Não | Nada |
| GPT | abre chatgpt.com numa aba do Chrome logado (via chrome-use), abre o menu de modelo/esforço, lê e fecha a aba | Não (nenhuma mensagem é enviada) | Uma aba abrindo e fechando por ~10–20 s |

Não usa screenshots nem controle de tela pelo Claude: tudo é feito por um script no terminal.

## Passos

1. **Avise antes de rodar**, em uma linha: "Vou ler os modelos do Codex (arquivo local) e do ChatGPT (uma aba do seu Chrome vai abrir e fechar por alguns segundos, sem enviar mensagem nem gastar cota)."
2. **Garanta o script.** Se `~/.claude/codex-image/update_models.py` não existir, ou não contiver a linha `VERSAO = "6"`, crie/sobrescreva com o conteúdo exato do bloco "Script". Caso contrário, não reescreva.
3. **Rode** `python3 ~/.claude/codex-image/update_models.py`
   - Só uma fonte: acrescente `--so codex` ou `--so gpt`.
   - Se a saída tiver `ANTIGO codex:`, pergunte se pode rodar `--so codex --refresh` (abre uma sessão curta e efêmera do Codex, sem rastro; gasta um mínimo da cota do Codex).
   - Use um timeout de pelo menos 120 s no comando.
4. **Responda curto**:
   - Codex: quantos modelos (em ordem de força, o primeiro é o topo de linha).
   - GPT: as opções por grupo (`[Modelo]`, `[Esforco]`) e o que está selecionado no site. No menu atual, modelos são itens de rádio e o esforço é um slider (Instantânea / Média / Alta); o script percorre o slider e volta à posição original.
   - Linhas `NOVOS:`, `REMOVIDOS:`, `OCULTADAS:` e `AVISO`, se houver. `OCULTADAS` são níveis como "Pro", que não têm gerador de imagem (o ChatGPT desenharia com Python ou recusaria), por isso a codex-image não os oferece.
   - Não abra nem mostre o `config.json` inteiro.
5. **Se houver linhas `ERRO`**, mostre ao usuário, para cada uma, o motivo e o `COMO CORRIGIR` exatamente como vieram, e diga que a última lista boa daquela fonte foi mantida. Não tente de novo em loop; espere o usuário corrigir.
6. **Sem padrões**: o config guarda só as listas (e `chrome_perfil`, se não usar a extensão); as imagens são mostradas no chat, sem pasta de saída fixa. As skills `codex-image` (pergunta) e `codex-image-auto` (o Claude decide) escolhem cota, modelo e esforço a cada geração.

## Requisitos (o script avisa se faltar algum)

- Codex CLI instalado e logado com a conta do ChatGPT (`codex login`).
- Para o GPT: Chrome logado em chatgpt.com, com o `chrome-use` e a extensão dele instalados.
- `python3` (no macOS, se faltar: `xcode-select --install`).

## Script

```python
#!/usr/bin/env python3
"""codex-update-models: atualiza as listas de modelos usadas pela skill codex-image.

- Codex: le o catalogo local do Codex (~/.codex/models_cache.json). Sem rede, sem cota.
- GPT:   abre o chatgpt.com numa aba do seu Chrome logado (via chrome-use), le o menu
         de modelo/esforco e fecha a aba. Nao envia mensagem, nao gasta cota.

Uso: python3 update_models.py [--so codex|gpt] [--refresh]
Saida curta, pensada para ser lida pelo Claude com poucos tokens.
"""
VERSAO = "6"
import json, os, re, shutil, subprocess, sys, time, datetime as dt
from pathlib import Path

CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
CACHE = CODEX_HOME / "models_cache.json"
CONFIG = Path(os.environ.get("CODEX_IMAGE_CONFIG",
              Path.home() / ".claude" / "codex-image" / "config.json"))
INTERNOS = {"codex-auto-review"}      # modelos internos que aparecem duplicados no seletor
STALE_H = 24
CHATGPT_URL = "https://chatgpt.com/"
SESSION = "codex-update-models"
AB_BINS = ("chrome-use", "agent-browser")
# Niveis sem gerador de imagem nativo: o ChatGPT desenha com Python ou recusa.
SEM_IMAGEM = re.compile(r"\bPro\b")

problemas = []   # (fonte, motivo, como_corrigir)


def falha(fonte, motivo, correcao):
    problemas.append((fonte, motivo, correcao))


def agora_iso():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def idade_horas(iso):
    try:
        t = dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return (dt.datetime.now(dt.timezone.utc) - t).total_seconds() / 3600
    except Exception:
        return None


# ----------------------------------------------------------------- Codex

def refresh_codex():
    try:
        subprocess.run(["codex", "exec", "--skip-git-repo-check", "--ephemeral",
                        "-c", 'model_reasoning_effort="low"', "Responda apenas: ok"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
    except FileNotFoundError:
        falha("codex", "o comando `codex` nao foi encontrado no terminal.",
              "instale com `brew install codex` (ou `npm i -g @openai/codex`) e rode `codex login`.")
    except subprocess.TimeoutExpired:
        falha("codex", "o Codex demorou mais de 3 min para responder no --refresh.",
              "confira a internet e se `codex login status` mostra 'Logged in using ChatGPT'; usei o cache atual.")


def ler_codex(antigo):
    if not CACHE.exists():
        falha("codex", f"o catalogo {CACHE} nao existe (o Codex nunca baixou a lista nesta maquina).",
              "abra o Codex uma vez ou rode esta skill com --refresh.")
        return antigo
    try:
        data = json.loads(CACHE.read_text())
    except Exception as e:
        falha("codex", f"nao consegui ler {CACHE} ({e.__class__.__name__}).",
              "abra o Codex uma vez para ele regravar o arquivo e rode de novo.")
        return antigo
    modelos, vistos = [], set()
    for m in sorted(data.get("models", []), key=lambda m: m.get("priority", 99)):
        slug = m.get("slug")
        if not slug or m.get("visibility") != "list" or slug in INTERNOS or slug in vistos:
            continue
        vistos.add(slug)
        niveis = [n.get("effort") if isinstance(n, dict) else n
                  for n in m.get("supported_reasoning_levels", [])]
        modelos.append({"slug": slug, "nome": m.get("display_name", slug),
                        "esforcos": [n for n in niveis if n],
                        "esforco_padrao": m.get("default_reasoning_level")})
    if not modelos:
        falha("codex", "o catalogo do Codex nao tem nenhum modelo visivel.",
              "atualize o Codex (`brew upgrade codex`) e rode com --refresh.")
        return antigo
    novo = {k: v for k, v in antigo.items() if not k.endswith("_padrao")}   # sem padroes salvos
    novo.update({"modelos": modelos, "catalogo_de": data.get("fetched_at"),
                 "versao_codex": data.get("client_version"), "lido_em": agora_iso()})
    idade = idade_horas(data.get("fetched_at"))
    if idade is not None and idade > STALE_H:
        print(f"ANTIGO codex: o catalogo local tem {idade:.0f}h. "
              "Para buscar o mais recente, rode de novo com --refresh (gasta um minimo da cota do Codex).")
    return novo


# ------------------------------------------------------------------- GPT

# Seletor de modelo/esforco (fica fora do <form>; so abre com clique por seletor, nao por coordenada)
BOTAO_SEL = 'button[aria-haspopup="menu"][aria-label*="odel"]'

JS_BOTAO = r"""(() => {
  const box = document.querySelector('#prompt-textarea, [contenteditable="true"].ProseMirror');
  if (!box) return JSON.stringify({erro: document.querySelector('a[href*="login"],button[data-testid*="login"]') ? 'login' : 'sem_composer'});
  const b = document.querySelector('BOTAO_SEL');
  if (!b) return JSON.stringify({erro: 'sem_seletor'});
  return JSON.stringify({texto: (b.innerText || '').trim() || b.getAttribute('aria-label')});
})()""".replace("BOTAO_SEL", BOTAO_SEL.replace("'", "\\'"))

# Le o menu aberto: modelos (menuitemradio) e o slider de esforco (posicao atual e rotulo).
# Deixa o foco no slider, para as setas esquerda/direita mudarem o esforco.
JS_MENU = r"""(() => {
  const m = [...document.querySelectorAll('[role="menu"]')].pop();
  if (!m) return JSON.stringify(null);
  const modelos = [...m.querySelectorAll('[role="menuitemradio"]')].map(e => {
    const t = (e.innerText || '').split('\n').map(s => s.trim()).filter(Boolean);
    return {texto: t[0], detalhe: t.slice(1).join(' ') || null, selecionado: e.getAttribute('aria-checked') === 'true'};
  }).filter(o => o.texto);
  const it = m.querySelector('[data-reasoning-slider]');
  const s = it && it.querySelector('[role="slider"]');
  if (it) it.focus();
  const st = it && document.getElementById((it.getAttribute('aria-describedby') || '').split(' ')[0]);
  return JSON.stringify({modelos, esforco: s ? {atual: +s.getAttribute('aria-valuenow'), max: +s.getAttribute('aria-valuemax'),
                                                 rotulo: st ? st.innerText.split(',')[0].trim() : null} : null});
})()"""


def abrir_menu(ab):
    ab_cmd(ab, "click", BOTAO_SEL)
    time.sleep(0.8)
    menu = ab_eval(ab, JS_MENU)
    if not menu:
        raise ErroChrome("o menu de modelo nao abriu")
    return menu


def mover_esforco(ab, passos):
    for _ in range(abs(passos)):
        ab_cmd(ab, "press", "ArrowRight" if passos > 0 else "ArrowLeft", timeout=10)
        time.sleep(0.4)
    return ab_eval(ab, JS_MENU)["esforco"]


def ler_esforcos(ab, esf):
    """O slider so mostra o rotulo da posicao atual: percorre 0..max e volta para onde estava."""
    mover_esforco(ab, -esf["atual"])
    rotulos = [ab_eval(ab, JS_MENU)["esforco"]["rotulo"]]
    for _ in range(esf["max"]):
        rotulos.append(mover_esforco(ab, 1)["rotulo"])
    mover_esforco(ab, esf["atual"] - esf["max"])
    return rotulos


class ErroChrome(Exception):
    pass


def ab_cmd(ab, *args, timeout=30, profile=None):
    cmd = [ab] + (["--profile", profile] if profile else []) + list(args) + ["--session", SESSION]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise ErroChrome(f"o chrome-use nao respondeu em {timeout}s ({args[0]})")
    if p.returncode != 0:
        cauda = " / ".join((p.stderr or p.stdout or "").strip().splitlines()[-2:])
        raise ErroChrome(f"chrome-use {args[0]} falhou: {cauda[:200]}")
    return p.stdout


def ab_eval(ab, js):
    out = ab_cmd(ab, "eval", js)
    for linha in reversed([l for l in out.splitlines() if l.strip()]):
        try:
            v = json.loads(linha)
        except Exception:
            continue
        return json.loads(v) if isinstance(v, str) else v
    raise ErroChrome("resposta do chrome-use em formato inesperado")


def relay_conectado(ab):
    try:
        p = subprocess.run([ab, "daemon", "status", "--json"], capture_output=True, text=True, timeout=10)
        d = json.loads(p.stdout or "{}")
        return bool(isinstance(d.get("data"), dict) and d["data"].get("relay"))
    except Exception:
        return False


def ler_gpt(antigo, perfil):
    ab = next((shutil.which(b) for b in AB_BINS if shutil.which(b)), None)
    if not ab:
        falha("gpt", "o chrome-use (que conversa com o seu Chrome) nao esta instalado.",
              "instale com `curl -fsSL https://raw.githubusercontent.com/leeguooooo/chrome-use/main/install.sh | sh`, "
              "depois rode `chrome-use extension install` e reinicie o Chrome.")
        return antigo
    if not perfil and not relay_conectado(ab):
        falha("gpt", "o chrome-use esta instalado, mas a extensao dele nao esta conectada ao seu Chrome aberto.",
              "rode `chrome-use extension install`, carregue a extensao ab-connect no Chrome "
              "(chrome://extensions > Modo do desenvolvedor > Carregar sem compactacao), reinicie o Chrome e rode de novo.")
        return antigo
    try:
        ab_cmd(ab, "open", CHATGPT_URL, timeout=45, profile=perfil)
        botao = None
        for _ in range(15):                    # espera a pagina carregar (~15s)
            botao = ab_eval(ab, JS_BOTAO)
            if isinstance(botao, dict) and "texto" in botao:
                break
            time.sleep(1)
        if not isinstance(botao, dict) or "texto" not in botao:
            erro = (botao or {}).get("erro") if isinstance(botao, dict) else None
            if erro == "login":
                falha("gpt", "o chatgpt.com abriu, mas o Chrome nao esta logado.",
                      "entre na sua conta em chatgpt.com nesse Chrome e rode de novo.")
            else:
                falha("gpt", "nao achei a caixa de mensagem ou o seletor de modelo no chatgpt.com (a OpenAI pode ter mudado o layout).",
                      "mantive a ultima lista que funcionou. Se persistir, edite `gpt.opcoes` no config manualmente.")
            return antigo
        menu = abrir_menu(ab)
        esf = menu.get("esforco")
        rotulos = ler_esforcos(ab, esf) if esf else []
        try:
            ab_cmd(ab, "press", "Escape", timeout=10)
        except ErroChrome:
            pass
    except ErroChrome as e:
        falha("gpt", f"{e}.",
              "confira se o Chrome esta aberto e logado no ChatGPT; se tiver a image-use, `image-use doctor` ajuda a diagnosticar.")
        return antigo
    finally:
        try:
            ab_cmd(ab, "close", timeout=15)
        except Exception:
            pass

    itens = [dict(m, grupo="Modelo") for m in menu["modelos"]]
    itens += [{"texto": r, "detalhe": None, "grupo": "Esforco", "selecionado": i == esf["atual"]}
              for i, r in enumerate(rotulos) if r]
    opcoes, removidas = [], []
    for i in itens:
        if SEM_IMAGEM.search(i["texto"]):
            removidas.append(i["texto"])
        else:
            opcoes.append(i)
    if not opcoes:
        falha("gpt", "o menu abriu, mas nao encontrei opcoes de modelo/esforco nele.",
              "mantive a ultima lista. Se persistir, edite `gpt.opcoes` no config manualmente.")
        return antigo
    sel = [o["texto"] for o in opcoes if o["selecionado"]]
    novo = {k: v for k, v in antigo.items() if not k.endswith("_padrao")}   # sem padroes salvos
    novo.update({"opcoes": opcoes, "selecionado_no_site": " / ".join(sel),
                 "lido_em": agora_iso(), "ocultadas_sem_imagem": removidas})
    return novo


# ------------------------------------------------------------------ main

def main():
    args = sys.argv[1:]
    so = args[args.index("--so") + 1] if "--so" in args and args.index("--so") + 1 < len(args) else None
    cfg = {}
    if CONFIG.exists():
        try:
            cfg = json.loads(CONFIG.read_text())
        except Exception:
            print(f"AVISO: {CONFIG} estava corrompido; vou recriar (padroes voltam ao normal).")
    antes_codex = {m["slug"] for m in cfg.get("codex", {}).get("modelos", [])}
    antes_gpt = {o["texto"] for o in cfg.get("gpt", {}).get("opcoes", [])}

    if so in (None, "codex"):
        if "--refresh" in args:
            refresh_codex()
        cfg["codex"] = ler_codex(cfg.get("codex", {}))
    if so in (None, "gpt"):
        cfg["gpt"] = ler_gpt(cfg.get("gpt", {}), cfg.get("chrome_perfil"))

    for k in ("cota_padrao", "tamanho_padrao", "pasta_saida"):   # sem padroes; a imagem vai para o chat
        cfg.pop(k, None)
    cfg["atualizado_em"] = agora_iso()
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))

    c = cfg.get("codex", {})
    if c.get("modelos"):
        print(f"CODEX {len(c['modelos'])} modelos:")
        for m in c["modelos"]:
            print(f"   {m['slug']} ({m['nome']}) esforcos: {','.join(m['esforcos']) or '-'}")
        agora = {m["slug"] for m in c["modelos"]}
        if antes_codex and agora - antes_codex: print("  NOVOS:", ", ".join(sorted(agora - antes_codex)))
        if antes_codex and antes_codex - agora: print("  REMOVIDOS:", ", ".join(sorted(antes_codex - agora)))
    g = cfg.get("gpt", {})
    if g.get("opcoes"):
        print(f"GPT (selecionado no site: {g.get('selecionado_no_site')}) {len(g['opcoes'])} opcoes:")
        for o in g["opcoes"]:
            grupo = f"[{o['grupo']}] " if o.get("grupo") else ""
            print(f"   {grupo}{o['texto']}" + (f" - {o['detalhe']}" if o.get("detalhe") else ""))
        agora = {o["texto"] for o in g["opcoes"]}
        if antes_gpt and agora - antes_gpt: print("  NOVOS:", ", ".join(sorted(agora - antes_gpt)))
        if antes_gpt and antes_gpt - agora: print("  REMOVIDOS:", ", ".join(sorted(antes_gpt - agora)))
        if g.get("ocultadas_sem_imagem"):
            print("  OCULTADAS (nao geram imagem):", ", ".join(g["ocultadas_sem_imagem"]))
    for fonte, motivo, correcao in problemas:
        print(f"ERRO {fonte}: {motivo}\n  COMO CORRIGIR: {correcao}")
    print(f"CONFIG: {CONFIG}")
    sys.exit(1 if problemas and not (c.get("modelos") or g.get("opcoes")) else 0)


if __name__ == "__main__":
    main()
```
