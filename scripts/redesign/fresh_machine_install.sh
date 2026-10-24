#!/usr/bin/env bash
# Runs ON the fresh machine (piped over ssh by fresh_machine.sh install):
# Python tooling, the two coding-agent CLIs, and the Kapso wheel as a tool.
# Argument: the wheel's file name under /tmp.
set -euo pipefail
WHEEL="/tmp/$1"

sudo apt-get update -qq
sudo apt-get install -y -qq git curl ca-certificates python3-venv >/dev/null

# uv: the installer the setup skill uses too.
curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null
export PATH="$HOME/.local/bin:$PATH"

# Node 22 for the coding-agent CLIs.
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - >/dev/null
sudo apt-get install -y -qq nodejs >/dev/null
sudo npm install -g --silent @anthropic-ai/claude-code @openai/codex

uv tool install --python 3.12 "$WHEEL" >/dev/null
echo "kapso $(kapso --version 2>/dev/null || echo installed)  python $(uv python find 3.12 2>/dev/null || true)"
echo "claude $(claude --version 2>/dev/null | head -1)"
echo "codex $(codex --version 2>/dev/null | head -1)"
