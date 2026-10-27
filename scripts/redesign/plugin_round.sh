#!/usr/bin/env bash
# The plugin's trigger suite, one host per call (wp7-plugin.md, change 9):
#
#   scripts/redesign/plugin_round.sh claude-triggers [--tag main|holdout] [more `claude plugin eval` flags]
#   scripts/redesign/plugin_round.sh codex-triggers  [--tag main|holdout] [codex_triggers.py flags]
#
# Claude Code: `claude plugin eval` over plugin/evals, one arm, the
# suite's pinned model, the result as JSON and rendered per skill and
# kind. Codex: codex_triggers.py over the same cases. Everything lands
# under scripts/redesign/runs/wp7-triggers/<host>-<stamp>/ (REPORT.md,
# the JSON, the streams, the logs).
set -o pipefail
HOST="$1"
if [ -z "$HOST" ]; then
  echo "usage: plugin_round.sh claude-triggers|codex-triggers [flags]" >&2
  exit 2
fi
shift
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
STAMP="$(date -u +%Y%m%dT%H%M%S)"
OUT="$ROOT/scripts/redesign/runs/wp7-triggers/$HOST-$STAMP"
mkdir -p "$OUT"
case "$HOST" in
  claude-triggers)
    TAG="main"
    if [ "${1:-}" = "--tag" ]; then TAG="$2"; shift 2; fi
    claude plugin eval plugin --ablation none --trust-plugin --json "$OUT/triggers.json" --threshold 1.0 \
      --no-publish --output-dir "$OUT/results" -j 4 --tag "$TAG" "$@" 2> "$OUT/stderr.log"
    echo "exit=$?" | tee "$OUT/exit.txt"
    python3 scripts/redesign/trigger_report.py "$OUT/triggers.json" | tee "$OUT/REPORT.md"
    ;;
  codex-triggers)
    PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}" python3 scripts/redesign/codex_triggers.py --out "$OUT" "$@" | tee "$OUT/REPORT.md"
    echo "exit=$?" | tee "$OUT/exit.txt"
    ;;
  *)
    echo "unknown host $HOST: claude-triggers or codex-triggers" >&2
    exit 2
    ;;
esac
echo "$OUT"
