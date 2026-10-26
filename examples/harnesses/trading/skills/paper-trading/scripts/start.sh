# Start the scheduled runner again after a stop; the account state in
# paper_account.json carries over.
set -euo pipefail
# shellcheck disable=SC1091
. "$(dirname "$0")/common.sh"
start_runner
