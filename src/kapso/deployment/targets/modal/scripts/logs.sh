# The app's line in Modal's listing; its logs stream from `modal app logs`.
set -euo pipefail
modal app list | grep -- "$KAPSO_VALUE_APP" || echo "the app $KAPSO_VALUE_APP is not listed"
echo "stream its logs with: modal app logs $KAPSO_VALUE_APP"
