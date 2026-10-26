# The paper-trading deployment: the scheduled runner started in the
# background, its pid and log under deploy/. Run from the workspace.
set -euo pipefail
# shellcheck disable=SC1091
. "$(dirname "$0")/common.sh"
mkdir -p deploy
start_runner
