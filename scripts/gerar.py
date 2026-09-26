#!/usr/bin/env python3
"""codex-image: gera uma imagem pela cota do Codex ou do ChatGPT (GPT), sem API key.

Uso: python3 gerar.py --cota codex|gpt --prompt "..." [--modelo X] [--esforco Y]
                      [--tamanho 1024x1024] [--exato] [--pasta DIR]
       [--ref IMG --ref IMG ...] [--ref-chat] [--editar]
--ref/--ref-chat: referencias (Codex e GPT); o modelo ve as imagens e escreve o prompt final.
--ref-chat usa as imagens coladas na conversa atual do Claude Code (ultima mensagem com imagem).
--tamanho orienta a geracao; a resolucao nativa e mantida (qualidade), salvo com --exato.
Saida: so o caminho do PNG, ou linhas `ERRO` + `COMO CORRIGIR`.
Sem rastros: Codex roda com --ephemeral e a copia em generated_images e apagada;
GPT usa chat normal (o temporario nao gera imagem) e arquiva a conversa logo apos baixar.
"""
VERSAO = "8"
import argparse, base64, glob, unicodedata, json, math, os, re, shutil, subprocess, sys, tempfile, time
import datetime as dt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import update_models as um   # reusa CONFIG, ab_cmd/ab_eval, JS_BOTAO/JS_MENU

CODEX_HOME = um.CODEX_HOME
PNG_B64 = re.compile(r"iVBORw0KGgo[A-Za-z0-9+/=]{1000,}")


def sair_erro(motivo, correcao):
    print(f"ERRO: {motivo}\n  COMO CORRIGIR: {correcao}")
    sys.exit(1)


def ajustar_tamanho(txt):
    """Regras do gpt-image-2: lados multiplos de 16, proporcao ate 3:1, minimo 655.360 px."""
    m = re.fullmatch(r"\s*(\d+)\s*[xX]\s*(\d+)\s*", txt or "")
    if not m:
        sair_erro(f"tamanho '{txt}' invalido.", "use LARGURAxALTURA, ex.: 1024x1024 ou 1536x1024.")
    w, h = int(m[1]), int(m[2])
    if max(w, h) / min(w, h) > 3:          # corta a proporcao em 3:1
        w, h = (3 * h, h) if w > h else (w, 3 * w)
    if w * h < 655360:                      # sobe mantendo a proporcao
        f = math.sqrt(655360 / (w * h))
        w, h = w * f, h * f
    w, h = math.ceil(w / 16) * 16, math.ceil(h / 16) * 16
    return w, h


def destino(pasta, prompt, nome=None):
    Path(pasta).mkdir(parents=True, exist_ok=True)
    if nome:                                          # nome escolhido (projetos): nunca sobrescreve
        base = re.sub(r"\.png$", "", nome, flags=re.I)
        alvo, n = Path(pasta) / f"{base}.png", 2
        while alvo.exists():
            alvo, n = Path(pasta) / f"{base}-v{n}.png", n + 1
        return alvo
    slug = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", prompt.lower()).encode("ascii", "ignore").decode())[:40].strip("-") or "imagem"
    return Path(pasta) / f"{dt.datetime.now():%Y%m%d-%H%M%S}-{slug}.png"


# ----------------------------------------------------------------- Codex

def png_do_log(thread):
    """Ultimo recurso: imagem em base64 dentro do log da sessao."""
    logs = glob.glob(str(CODEX_HOME / "sessions" / "**" / f"*{thread}*.jsonl"), recursive=True)
    for log in logs:
        achados = PNG_B64.findall(Path(log).read_text(errors="ignore"))
        if achados:
            return base64.b64decode(achados[-1])
    return None


def refs_do_chat():
    """Extrai as imagens coladas pelo usuario na conversa atual do Claude Code.

    O Claude Code grava a conversa em <config>/projects/*/<CLAUDE_CODE_SESSION_ID>.jsonl, com as
    imagens coladas em base64. Formato interno, sem documentacao: se mudar, cai no ERRO abaixo.
    Devolve (pasta_temporaria, [caminhos]) na ordem de colagem.
    """
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    cfg = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
    logs = glob.glob(str(cfg / "projects" / "*" / f"{sid}.jsonl")) if sid else []
    if not logs:
        sair_erro("nao achei o registro desta conversa do Claude Code.",
                  "arraste o arquivo da imagem para o chat (cola o caminho) e use --ref.")
    ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}
    for linha in reversed(Path(logs[0]).read_text(errors="ignore").splitlines()):
        try:
            d = json.loads(linha)
        except Exception:
            continue
        # isMeta entra: com /comando, a imagem colada vem na entrada meta da expansao da skill
        conteudo = d.get("message", {}).get("content") if d.get("type") == "user" else None
        if not isinstance(conteudo, list):
            continue
        # so blocos de imagem de primeiro nivel: os de dentro de tool_result sao do Claude, nao do usuario
        imgs = [b["source"] for b in conteudo if isinstance(b, dict) and b.get("type") == "image"
                and b.get("source", {}).get("type") == "base64"]
        if imgs:
            pasta = Path(tempfile.mkdtemp(prefix="codex-image-ref-"))
            caminhos = []
            for i, src in enumerate(imgs, 1):
                c = pasta / f"imagem-{i}{ext.get(src.get('media_type'), '.png')}"
                c.write_bytes(base64.b64decode(src["data"]))
                caminhos.append(str(c))
            return pasta, caminhos
    sair_erro("nao achei imagem colada nesta conversa.",
              "cole a imagem no chat junto com o pedido, ou arraste o arquivo (cola o caminho) e use --ref.")


def pedido_codex(prompt, w, h, trab, refs, editar):
    fim = f"Salve o PNG final como {trab}/saida.png. Nao faca mais nada."
    if not refs:
        return (f"Use $imagegen (ferramenta nativa image_gen) para gerar UMA imagem de {w}x{h} px. "
                f"{fim} Prompt:\n{prompt}")
    lista = " ".join(f"Imagem {i} = {Path(r).name}." for i, r in enumerate(refs, 1))
    if editar:
        return (f"Anexei {len(refs)} imagem(ns), na ordem: {lista} Olhe todas com atencao. "
                f"Use $imagegen (ferramenta nativa image_gen) em modo EDICAO sobre a Imagem 1: aplique so o que o "
                f"pedido abaixo manda e preserve todo o resto (enquadramento, identidade, detalhes). As demais imagens "
                f"sao fontes para a edicao. Saida {w}x{h} px. {fim}\nPedido:\n{prompt}")
    return (f"Anexei {len(refs)} imagem(ns) de referencia, na ordem: {lista} Olhe todas com atencao e siga o papel "
            f"que o pedido da a cada uma (estilo, paleta, composicao, personagem/produto a manter...). Escreva voce "
            f"mesmo o melhor prompt possivel para o image_gen, detalhado e fiel as referencias, e use $imagegen "
            f"(ferramenta nativa image_gen) para gerar UMA imagem nova de {w}x{h} px, passando as referencias. "
            f"{fim}\nPedido:\n{prompt}")


def gerar_codex(prompt, w, h, modelo, esforco, saida, exato, refs=(), editar=False):
    codex = shutil.which("codex") or "/Applications/ChatGPT.app/Contents/Resources/codex"
    if not os.path.exists(codex):
        sair_erro("o comando `codex` nao foi encontrado.",
                  "instale com `brew install codex` (ou `npm i -g @openai/codex`) e rode `codex login`.")
    trab = Path(tempfile.mkdtemp(prefix="codex-image-"))
    pedido = pedido_codex(prompt, w, h, trab, refs, editar)
    cmd = [codex, "exec", "--skip-git-repo-check", "--ephemeral", "--json", "-C", str(trab)]
    if modelo:
        cmd += ["-m", modelo]
    if esforco:
        cmd += ["-c", f'model_reasoning_effort="{esforco}"']
    cmd += [f"--image={r}" for r in refs]             # --image=X: o -i e variadico e engoliria o prompt
    inicio = time.time()
    try:
        p = subprocess.run(cmd + ["--", pedido], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        sair_erro("o Codex passou de 10 min sem terminar.", "tente de novo com esforco menor (low).")
    thread = next((json.loads(l).get("thread_id") for l in p.stdout.splitlines()
                   if '"thread.started"' in l), None)

    # a pasta de saida muda entre versoes: diretorio de trabalho, generated_images, log da sessao
    candidatos = sorted(trab.glob("**/*.png"), key=os.path.getmtime)
    if not candidatos and thread:
        candidatos = sorted((CODEX_HOME / "generated_images" / thread).glob("*.png"), key=os.path.getmtime)
    if not candidatos:
        candidatos = [Path(f) for f in sorted(glob.glob(str(CODEX_HOME / "generated_images" / "*" / "*.png")),
                                              key=os.path.getmtime) if os.path.getmtime(f) >= inicio]
    if candidatos:
        shutil.copy2(candidatos[-1], saida)
    elif thread and (dados := png_do_log(thread)):
        saida.write_bytes(dados)
    else:
        cauda = " / ".join((p.stderr or "").strip().splitlines()[-2:])[:200]
        if re.search(r"usage limit|rate limit|quota", p.stdout + p.stderr, re.I):
            sair_erro("a cota do Codex acabou por agora.", "espere o limite renovar ou use a cota GPT.")
        if re.search(r"not logged in|login|401", p.stderr, re.I):
            sair_erro("o Codex nao esta logado.", "rode `codex login` e escolha 'Sign in with ChatGPT'.")
        sair_erro(f"o Codex terminou sem gerar imagem ({cauda or 'sem detalhe'}).",
                  "tente de novo; se repetir, rode `codex exec \"use $imagegen: teste\"` para ver o erro completo.")
    shutil.rmtree(trab, ignore_errors=True)
    if thread:                                        # sem rastro: apaga a copia que o Codex guarda
        shutil.rmtree(CODEX_HOME / "generated_images" / thread, ignore_errors=True)
    if exato:
        redimensionar(saida, w, h)


def redimensionar(png, w, h):
    """O image_gen escolhe o proprio tamanho; ajusto com sips se a proporcao for a mesma."""
    out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(png)],
                         capture_output=True, text=True).stdout
    pw, ph = (int(x) for x in re.findall(r"pixel\w+: (\d+)", out))
    if (pw, ph) != (w, h) and abs(pw / ph - w / h) < 0.02:
        subprocess.run(["sips", "-z", str(h), str(w), str(png)], capture_output=True)


# ------------------------------------------------------------------- GPT

COMPOSER = '#prompt-textarea, [contenteditable="true"].ProseMirror'
# Sem marcas de autor/stop no DOM atual: a imagem pronta e um <img alt="Imagem N gerada"> (src blob:).
JS_ESTADO = r"""(() => {
  const imgs = [...document.querySelectorAll('img')]
    .filter(i => /gerada|generated/i.test(i.alt) && i.complete && i.naturalWidth >= 512);
  const i = imgs[imgs.length - 1];
  return JSON.stringify({img: i ? i.src : null, tam: i ? i.naturalWidth + 'x' + i.naturalHeight : null,
                         texto: (document.querySelector('main') || document.body).innerText.trim().slice(-200)});
})()"""


# Arquiva (reversivel) a conversa aberta: some da barra lateral, fica em "Chats arquivados".
JS_ARQUIVAR = r"""(async () => {
  const id = (location.pathname.match(/\/c\/([\w-]+)/) || [])[1];
  if (!id) return JSON.stringify({ok: false, status: 'sem id da conversa'});
  const s = await (await fetch('/api/auth/session')).json();
  const r = await fetch('/backend-api/conversation/' + id, {method: 'PATCH',
    headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + s.accessToken},
    body: JSON.stringify({is_archived: true})});
  return JSON.stringify({ok: r.ok, status: r.status, id});
})()"""


def reconciliar_app(conversa):
    """O app ChatGPT/Codex para Mac guarda um catalogo local dos chats e nao percebe o arquivamento pela web.
    Marca o chat como ausente (missing_candidate=1, como o proprio app faz; a barra lateral le so os 0), para ele
    sumir assim que o app reabrir, e zera last_full_reconciled_at (como nas migrations dele) para o app
    reconciliar tudo com o servidor. Formato interno: se mudar, ignora."""
    db = CODEX_HOME / "sqlite" / "codex-dev.db"
    if not db.exists():
        return
    import sqlite3
    try:
        with sqlite3.connect(db, timeout=5) as c:
            if c.execute("UPDATE local_thread_catalog SET missing_candidate = 1 "
                         "WHERE host_id LIKE 'chatgpt:%' AND thread_id = ?", (conversa,)).rowcount:
                c.execute("UPDATE local_thread_catalog_metadata SET catalog_revision = catalog_revision + 1")
            c.execute("UPDATE local_thread_catalog_sync_state SET last_full_reconciled_at = NULL "
                      "WHERE host_id LIKE 'chatgpt:%'")
    except sqlite3.Error:
        pass


JS_ANEXOS = r"""(() => {
  const f = document.querySelector('#prompt-textarea, [contenteditable="true"].ProseMirror').closest('form');
  const b = f && f.querySelector('button[data-testid="send-button"], button[aria-label="Enviar"], button[aria-label="Send prompt"]');
  return JSON.stringify({n: f ? [...f.querySelectorAll('img')].filter(i => i.complete && i.naturalWidth).length : 0,
                         pronto: !!b && !b.disabled});
})()"""


def anexar(ab, refs):
    """Anexa as referencias no composer, renomeadas imagem-1..N para a ordem ficar clara."""
    pasta = Path(tempfile.mkdtemp(prefix="codex-image-anexo-"))
    try:
        copias = []
        for i, r in enumerate(refs, 1):
            c = pasta / f"imagem-{i}{Path(r).suffix.lower()}"
            shutil.copy2(r, c)
            copias.append(str(c))
        um.ab_cmd(ab, "upload", 'form input[type="file"][accept="image/*"]', *copias, timeout=60)
        for _ in range(30):                           # espera as previas subirem
            e = um.ab_eval(ab, JS_ANEXOS)
            if e["n"] >= len(refs) and e["pronto"]:
                return
            time.sleep(1)
        raise um.ErroChrome("as imagens de referencia nao terminaram de subir no ChatGPT")
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


def escolher(ab, modelo, esforco):
    """Seleciona modelo (menuitemradio) e esforco (slider) no menu do ChatGPT."""
    menu = um.abrir_menu(ab)
    if modelo and not any(m["texto"] == modelo and m["selecionado"] for m in menu["modelos"]):
        if not any(m["texto"] == modelo for m in menu["modelos"]):
            raise um.ErroChrome(f"o modelo '{modelo}' nao esta no menu")
        um.ab_cmd(ab, "click", f"//*[@role='menuitemradio'][contains(normalize-space(.), '{modelo}')]")
        time.sleep(0.8)
        menu = um.ab_eval(ab, um.JS_MENU) or um.abrir_menu(ab)   # o clique pode fechar o menu
    esf = menu.get("esforco")
    if esforco and esf:
        atual = um.mover_esforco(ab, -esf["atual"])              # vai para o nivel 0 e sobe ate achar
        for _ in range(esf["max"]):
            if atual["rotulo"] == esforco:
                break
            atual = um.mover_esforco(ab, 1)
        if atual["rotulo"] != esforco:
            raise um.ErroChrome(f"o esforco '{esforco}' nao esta no menu")
    um.ab_cmd(ab, "press", "Escape", timeout=10)


def gerar_gpt(prompt, w, h, modelo, esforco, saida, exato, refs=(), editar=False):
    ab = shutil.which("chrome-use")
    if not ab:
        sair_erro("o chrome-use nao esta instalado.",
                  "instale com `curl -fsSL https://raw.githubusercontent.com/leeguooooo/chrome-use/main/install.sh | sh` "
                  "e reinicie o Chrome.")
    um.SESSION = "codex-image"
    if not refs:
        pedido = f"Gere uma imagem com a ferramenta de geracao de imagens, formato {w}x{h} px. Sem texto na resposta. Prompt: {prompt}"
    elif editar:
        pedido = (f"Anexei {len(refs)} imagem(ns), na ordem: Imagem 1 a {len(refs)}. Com a ferramenta de geracao de imagens, "
                  f"EDITE a Imagem 1: aplique so o que o pedido abaixo manda e preserve todo o resto (enquadramento, "
                  f"identidade, detalhes). As demais imagens sao fontes para a edicao. Formato {w}x{h} px. "
                  f"Sem texto na resposta. Pedido: {prompt}")
    else:
        pedido = (f"Anexei {len(refs)} imagem(ns) de referencia, na ordem: Imagem 1 a {len(refs)}. Siga o papel que o pedido "
                  f"da a cada uma e gere UMA imagem nova com a ferramenta de geracao de imagens, fiel as referencias, "
                  f"formato {w}x{h} px. Sem texto na resposta. Pedido: {prompt}")
    try:
        um.ab_cmd(ab, "open", um.CHATGPT_URL, timeout=45)
        for _ in range(15):
            b = um.ab_eval(ab, um.JS_BOTAO)
            if isinstance(b, dict) and "texto" in b:
                break
            time.sleep(1)
        else:
            raise um.ErroChrome("o chatgpt.com nao carregou (Chrome logado?)")
        escolher(ab, modelo, esforco)
        if refs:
            anexar(ab, refs)
        um.ab_cmd(ab, "fill", COMPOSER, pedido)
        um.ab_cmd(ab, "press", "Enter", "--selector", COMPOSER, timeout=10)
        # ponytail: "pronta" = mesma imagem em 2 leituras seguidas; se o ChatGPT recusar, so percebe no timeout
        fim, anterior, e = time.time() + 300, None, {}
        while time.time() < fim:
            time.sleep(5)
            e = um.ab_eval(ab, JS_ESTADO)
            if e["img"] and (e["img"], e["tam"]) == anterior:
                break
            anterior = (e["img"], e["tam"]) if e["img"] else None
        else:
            raise um.ErroChrome(f"nenhuma imagem em 5 min; fim da pagina: \"{e.get('texto') or 'vazio'}\"")
        um.ab_cmd(ab, "download-url", e["img"], str(saida), timeout=90)
        arq = um.ab_eval(ab, JS_ARQUIVAR)
        if not arq.get("ok"):
            print(f"AVISO: nao consegui arquivar a conversa ({arq.get('status')}); arquive manualmente no ChatGPT.",
                  file=sys.stderr)
        else:
            reconciliar_app(arq.get("id"))
    except um.ErroChrome as e:
        sair_erro(f"{e}.", "confira se o Chrome esta aberto e logado no ChatGPT e se a cota de imagens nao acabou; "
                           "rode /codex-update-models se o menu mudou.")
    finally:
        try:
            um.ab_cmd(ab, "close", timeout=15)
        except Exception:
            pass
    if not saida.exists():
        sair_erro("a imagem nao foi salva.", "tente de novo; se repetir, confira `chrome-use status`.")
    if exato:
        redimensionar(saida, w, h)


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--cota", choices=("codex", "gpt"), required=True)
    a.add_argument("--prompt", required=True)
    a.add_argument("--modelo")
    a.add_argument("--esforco")
    a.add_argument("--tamanho")
    a.add_argument("--pasta")
    a.add_argument("--exato", action="store_true")
    a.add_argument("--ref", action="append", default=[], help="imagem de referencia (repita para varias)")
    a.add_argument("--ref-chat", action="store_true", help="usa as imagens coladas no chat do Claude Code")
    a.add_argument("--editar", action="store_true", help="edita a primeira --ref em vez de criar imagem nova")
    a.add_argument("--nome", help="nome do arquivo (sem extensao); se existir, vira -v2, -v3...")
    a = a.parse_args()
    if not um.CONFIG.exists():
        sair_erro("a lista de modelos ainda nao existe.", "rode /codex-update-models antes.")
    cfg = json.loads(um.CONFIG.read_text())
    refs = [str(Path(r).expanduser().resolve()) for r in a.ref]
    pasta_chat = None
    if a.ref_chat:
        pasta_chat, do_chat = refs_do_chat()
        refs = do_chat + refs                        # coladas primeiro, na ordem de colagem
    for r in refs:
        if not Path(r).is_file():
            sair_erro(f"a imagem de referencia '{r}' nao existe.", "confira o caminho (arraste o arquivo para o chat para colar o caminho).")
        if Path(r).suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
            sair_erro(f"'{Path(r).name}' nao e PNG, JPG, WEBP ou GIF.", "converta com `sips -s format png <arquivo> --out <novo.png>`.")
    if a.editar and not refs:
        sair_erro("--editar precisa de pelo menos uma --ref (a imagem a editar).", "passe a imagem com --ref.")
    modelo, esforco = a.modelo, a.esforco           # sem padroes salvos: quem chama decide
    w, h = ajustar_tamanho(a.tamanho or "1024x1024")
    # padrao: pasta temporaria privada do usuario; a skill renderiza no Claude e apaga o arquivo
    saida = destino(os.path.expanduser(a.pasta or Path(tempfile.gettempdir()) / "codex-image"), a.prompt, a.nome)
    try:
        (gerar_codex if a.cota == "codex" else gerar_gpt)(a.prompt, w, h, modelo, esforco, saida, a.exato, refs, a.editar)
    finally:                                         # sem rastro: apaga as copias das imagens coladas
        if pasta_chat:
            shutil.rmtree(pasta_chat, ignore_errors=True)
    print(saida)


if __name__ == "__main__":
    main()
