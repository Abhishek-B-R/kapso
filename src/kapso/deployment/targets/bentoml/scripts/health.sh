# Exit 0 while BentoCloud reports the deployment running.
set -euo pipefail
bentoml deployment get "$KAPSO_VALUE_DEPLOYMENT" -o json | "$KAPSO_INTERPRETER" -c 'import json, sys; sys.exit(0 if json.load(sys.stdin).get("status") == "running" else 1)'
