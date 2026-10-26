# Terminate the BentoCloud deployment: its instances end, the name stays.
set -euo pipefail
bentoml deployment terminate "$KAPSO_VALUE_DEPLOYMENT"
