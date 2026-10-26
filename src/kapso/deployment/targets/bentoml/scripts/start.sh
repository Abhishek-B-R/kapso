# Deploy again after a termination, under the same name; the new URL is
# written back into the record through the KAPSO_ENDPOINT line.
set -euo pipefail
"$KAPSO_INTERPRETER" deploy.py
described="$(bentoml deployment get "$KAPSO_VALUE_DEPLOYMENT" -o json)"
"$KAPSO_INTERPRETER" - "$described" <<'PY'
import re
import sys

urls = re.findall(r"https://[^\s\"']+", sys.argv[1])
if not urls:
    sys.stderr.write("BentoCloud describes the deployment without an endpoint URL\n")
    sys.exit(1)
print(f"KAPSO_ENDPOINT={urls[0]}")
PY
