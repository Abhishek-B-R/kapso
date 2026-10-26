# Deploy the app again after a stop (a stop removes it), under the same name.
set -euo pipefail
modal deploy modal_app.py
bash "$(dirname "$0")/health.sh"
