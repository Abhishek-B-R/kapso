# Terminate the BentoCloud deployment and wait for it: its instances end,
# the name stays, and `bentoml deployment start` brings it back.
set -euo pipefail
bentoml deployment terminate "$KAPSO_VALUE_DEPLOYMENT" --wait
