# The runner's last cycles.
set -euo pipefail
# shellcheck disable=SC1091
. "$(dirname "$0")/common.sh"
if [ -f "$LOG_FILE" ]; then
  tail -n 200 "$LOG_FILE"
else
  echo "no cycle has run yet"
fi
