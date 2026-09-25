#!/bin/sh
# Installs the codex-image* skills into Claude Code (~/.claude).
# Works from a clone (./install.sh) or piped from curl (downloads the repo to a temp folder).
set -e
cd "$(dirname "$0")" 2>/dev/null || true
if [ ! -d skills ]; then
  tmp=$(mktemp -d)
  git clone --depth 1 -q https://github.com/almeidasrenato/codex-image-skills "$tmp"
  cd "$tmp"
fi
for s in skills/*/; do
  mkdir -p ~/.claude/skills/"$(basename "$s")"
  cp "$s"SKILL.md ~/.claude/skills/"$(basename "$s")"/SKILL.md
done
mkdir -p ~/.claude/codex-image
cp scripts/gerar.py scripts/update_models.py ~/.claude/codex-image/
echo "Installed. In Claude Code, run /codex-update-models to build the model list."
