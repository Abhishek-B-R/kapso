# Start the same container again after a stop: the same name, port, env
# file and GPU request, from the image the deployment built.
set -euo pipefail
# shellcheck disable=SC1091
. "$(dirname "$0")/common.sh"
docker rm -f "$NAME" > /dev/null 2>&1 || true
run_container > /dev/null
wait_for_health
