#!/bin/sh
# Instala as skills codex-image* no Claude Code (~/.claude). Rode de dentro da pasta do repositorio.
set -e
cd "$(dirname "$0")"
for s in skills/*/; do
  mkdir -p ~/.claude/skills/"$(basename "$s")"
  cp "$s"SKILL.md ~/.claude/skills/"$(basename "$s")"/SKILL.md
done
mkdir -p ~/.claude/codex-image
cp scripts/gerar.py scripts/update_models.py ~/.claude/codex-image/
echo "Instalado. No Claude Code, rode /codex-update-models para montar a lista de modelos."
