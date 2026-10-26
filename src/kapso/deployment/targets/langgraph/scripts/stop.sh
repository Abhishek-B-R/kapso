# End the conversation: the thread the calls shared is deleted on the
# platform and forgotten here; the deployment itself stays on the platform.
set -euo pipefail
"$KAPSO_INTERPRETER" - "$KAPSO_VALUE_DEPLOYMENT_URL" <<'PY'
import asyncio
import sys
from pathlib import Path

from langgraph_sdk import get_client

thread_file = Path(".kapso_langgraph_thread")
if thread_file.is_file():
    thread_id = thread_file.read_text(encoding="utf-8").strip()
    asyncio.run(get_client(url=sys.argv[1]).threads.delete(thread_id))
    thread_file.unlink()
PY
