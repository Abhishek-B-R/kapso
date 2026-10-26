# The platform keeps the deployment; a start checks it answers again.
set -euo pipefail
bash "$(dirname "$0")/health.sh"
