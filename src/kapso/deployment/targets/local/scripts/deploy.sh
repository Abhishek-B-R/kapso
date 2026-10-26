# The local target's deployment: the entry point imports in the engine's
# interpreter with the caller's variables set. Run from the workspace.
set -euo pipefail
if [ -n "${KAPSO_ENV_FILE:-}" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$KAPSO_ENV_FILE"
  set +a
fi
"$KAPSO_INTERPRETER" - <<'PY'
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
module = importlib.import_module("main")
if not callable(getattr(module, "predict", None)):
    sys.stderr.write("main.py has no module-level predict function\n")
    sys.exit(1)
print("main.predict imports")
PY
