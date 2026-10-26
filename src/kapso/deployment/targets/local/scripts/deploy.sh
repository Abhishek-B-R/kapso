# The local target's deployment: the entry point imports in the engine's
# worker, the one every call runs, with the caller's variables loaded as
# the worker loads them. Run from the workspace.
set -euo pipefail
reply="$(echo '{"ping": true}' | "$KAPSO_INTERPRETER" -m kapso.deployment.worker "$KAPSO_WORKSPACE" main predict ${KAPSO_ENV_FILE:+"$KAPSO_ENV_FILE"})"
if [ "$reply" != '{"pong": true}' ]; then
  echo "the worker did not answer its ping: $reply" >&2
  exit 1
fi
echo "main.predict imports in the engine's worker"
