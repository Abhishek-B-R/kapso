# Where the deployment is, which thread the calls share, and the agent
# server's runtime logs from the platform.
set -euo pipefail
echo "deployment: $KAPSO_VALUE_DEPLOYMENT_URL (assistant ${KAPSO_VALUE_ASSISTANT:-agent})"
if [ -f .kapso_langgraph_thread ]; then
  echo "thread: $(cat .kapso_langgraph_thread)"
else
  echo "thread: none yet"
fi
langgraph deploy logs --name "kapso-$KAPSO_DEPLOYMENT_NAME"
