# The deployment as BentoCloud describes it; its logs are in the BentoCloud console.
set -euo pipefail
bentoml deployment get "$KAPSO_VALUE_DEPLOYMENT"
