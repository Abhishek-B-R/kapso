# Exit 0 while the scheduled runner is alive.
set -euo pipefail
# shellcheck disable=SC1091
. "$(dirname "$0")/common.sh"
runner_alive
