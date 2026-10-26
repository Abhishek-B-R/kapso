# End the scheduled runner; the account state and the log stay.
set -euo pipefail
# shellcheck disable=SC1091
. "$(dirname "$0")/common.sh"
if runner_alive; then
  kill "$(cat "$PID_FILE")"
fi
rm -f "$PID_FILE"
