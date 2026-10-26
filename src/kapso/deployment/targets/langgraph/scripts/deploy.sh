# The langgraph target's deployment: `langgraph deploy` prints the
# deployment's URL, which the session records as the deployment_url value.
set -euo pipefail
langgraph deploy
