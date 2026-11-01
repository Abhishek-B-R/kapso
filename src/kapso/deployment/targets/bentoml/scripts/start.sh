# Start the terminated deployment again under the same name (BentoCloud
# keeps it), wait until it runs, and write its URL back into the record
# through the KAPSO_ENDPOINT line: a start may give it a new one.
set -euo pipefail
bentoml deployment start "$KAPSO_VALUE_DEPLOYMENT"
"$KAPSO_INTERPRETER" - "$KAPSO_VALUE_DEPLOYMENT" <<'PY'
import json
import subprocess
import sys
import time

name = sys.argv[1]
for attempt in range(60):   # up to ten minutes, the deploy script's own wait
    described = json.loads(subprocess.run(["bentoml", "deployment", "get", name, "-o", "json"], capture_output=True, text=True, check=True).stdout)
    if described.get("status") == "running":
        urls = described.get("endpoint_urls") or []
        if not urls:
            sys.exit(f"BentoCloud describes {name} as running without an endpoint URL")
        print(f"KAPSO_ENDPOINT={urls[0]}")
        sys.exit(0)
    time.sleep(10)
sys.exit(f"BentoCloud did not report {name} running within ten minutes (last status: {described.get('status')})")
PY
