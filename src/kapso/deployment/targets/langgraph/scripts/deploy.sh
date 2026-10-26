# The langgraph target's deployment: `langgraph deploy` under this
# deployment's own name (the CLI finds or creates the platform deployment
# by name; its default, the directory's name, is `workspace` for every
# deployment); it prints the deployment's URL, which the session records
# as the deployment_url value.
set -euo pipefail
langgraph deploy --name "kapso-$KAPSO_DEPLOYMENT_NAME"
