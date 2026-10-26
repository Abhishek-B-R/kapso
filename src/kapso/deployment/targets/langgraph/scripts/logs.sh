# Where the deployment is and which thread the calls share; the run logs
# are in LangSmith.
set -euo pipefail
echo "deployment: $KAPSO_VALUE_DEPLOYMENT_URL (assistant ${KAPSO_VALUE_ASSISTANT:-agent})"
if [ -f .kapso_langgraph_thread ]; then
  echo "thread: $(cat .kapso_langgraph_thread)"
else
  echo "thread: none yet"
fi
