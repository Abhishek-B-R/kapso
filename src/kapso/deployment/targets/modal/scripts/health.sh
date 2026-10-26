# Exit 0 while the function can be looked up under the app's name.
set -euo pipefail
"$KAPSO_INTERPRETER" - "$KAPSO_VALUE_APP" <<'PY'
import sys

import modal

modal.Function.from_name(sys.argv[1], "predict").hydrate()
PY
