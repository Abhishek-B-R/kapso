# The container's last lines, or what stop.sh saved before removing it.
set -euo pipefail
# shellcheck disable=SC1091
. "$(dirname "$0")/common.sh"
if docker inspect "$NAME" > /dev/null 2>&1; then
  docker logs --tail 200 "$NAME" 2>&1
elif [ -f "$KAPSO_RECORD_DIR/container.log" ]; then
  cat "$KAPSO_RECORD_DIR/container.log"
fi
