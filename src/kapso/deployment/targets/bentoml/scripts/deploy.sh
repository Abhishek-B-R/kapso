# The bentoml target's deployment: the workspace's deploy.py, then the
# deployment as BentoCloud describes it. Run from the workspace.
set -euo pipefail
: "${KAPSO_VALUE_DEPLOYMENT:?export KAPSO_VALUE_DEPLOYMENT=kapso-\$KAPSO_DEPLOYMENT_NAME first}"
"$KAPSO_INTERPRETER" deploy.py
bentoml deployment get "$KAPSO_VALUE_DEPLOYMENT" -o json
