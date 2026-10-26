# End the scheduled runner and wait for it to go (so a start that follows
# never overlaps it); the account state and the log stay.
set -euo pipefail
# shellcheck disable=SC1091
. "$(dirname "$0")/common.sh"
if runner_alive; then
  pid="$(cat "$PID_FILE")"
  kill "$pid"
  for _ in $(seq 1 50); do
    kill -0 "$pid" 2> /dev/null || break
    sleep 0.2
  done
  if kill -0 "$pid" 2> /dev/null; then
    kill -9 "$pid"
  fi
  echo "the paper runner (pid $pid) ended"
fi
rm -f "$PID_FILE"
