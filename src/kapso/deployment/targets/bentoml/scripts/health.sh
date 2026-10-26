# Exit 0 while BentoCloud reports the deployment running.
set -euo pipefail
bentoml deployment get "$KAPSO_VALUE_DEPLOYMENT" -o json | grep -q '"running"'
