# Stop and remove the container, its last lines saved beside the record
# (they vanish with the container).
set -euo pipefail
# shellcheck disable=SC1091
. "$(dirname "$0")/common.sh"
if docker inspect "$NAME" > /dev/null 2>&1; then
  docker logs --tail 200 "$NAME" > "$KAPSO_RECORD_DIR/container.log" 2>&1 || true
  docker rm -f "$NAME" > /dev/null
fi
