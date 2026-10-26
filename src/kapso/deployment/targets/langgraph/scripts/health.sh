# Exit 0 while the deployment lists its assistants.
set -euo pipefail
"$KAPSO_INTERPRETER" - "$KAPSO_VALUE_DEPLOYMENT_URL" <<'PY'
import asyncio
import sys

from langgraph_sdk import get_client

asyncio.run(get_client(url=sys.argv[1]).assistants.search())
PY
