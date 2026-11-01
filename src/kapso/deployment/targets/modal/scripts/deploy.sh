# The modal target's deployment: `modal deploy`, then the function looked
# up under the app's name. Run from the workspace.
set -euo pipefail
: "${KAPSO_VALUE_APP:?export KAPSO_VALUE_APP=kapso-\$KAPSO_DEPLOYMENT_NAME first}"
modal deploy modal_app.py
bash "$(dirname "$0")/health.sh"
echo "the Modal app $KAPSO_VALUE_APP serves predict"
