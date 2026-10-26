# Exit 0 while the container runs and /health answers.
set -euo pipefail
# shellcheck disable=SC1091
. "$(dirname "$0")/common.sh"
[ "$(docker inspect -f '{{.State.Running}}' "$NAME" 2> /dev/null)" = "true" ]
"$KAPSO_INTERPRETER" - "$HEALTH_URL" <<'PY'
import sys
import urllib.request

response = urllib.request.urlopen(sys.argv[1], timeout=5)
sys.exit(0 if response.status == 200 else 1)
PY
