#!/usr/bin/env bash
# Cross-model review of a document or a diff: Codex (gpt-6-astra, xhigh) and
# Claude Code (opus-5) each read the brief and write their findings.
#
#   scripts/redesign/review.sh <brief.md> <out-dir>
#
# The brief names the files to read and the questions to answer; both
# reviewers run read-only from the repository root. Outputs:
#   <out-dir>/codex.md    <out-dir>/claude.md    <out-dir>/*.log
set -o pipefail
BRIEF="$1"
OUT="$2"
if [ -z "$BRIEF" ] || [ -z "$OUT" ]; then
  echo "usage: review.sh <brief.md> <out-dir>" >&2
  exit 2
fi
mkdir -p "$OUT"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
PROMPT="$(cat "$BRIEF")"

codex exec -m gpt-6-astra -c model_reasoning_effort="xhigh" --sandbox read-only --skip-git-repo-check -o "$OUT/codex.md" "$PROMPT" > "$OUT/codex.log" 2>&1
echo "codex exit=$?" >> "$OUT/codex.log"

claude -p "$PROMPT" --model claude-opus-5 --allowedTools "Read,Grep,Glob,Bash(git diff *),Bash(git log *),Bash(ls *),Bash(cat *),Bash(sed -n *)" --output-format text > "$OUT/claude.md" 2> "$OUT/claude.log"
echo "claude exit=$?" >> "$OUT/claude.log"

wc -c "$OUT/codex.md" "$OUT/claude.md"
