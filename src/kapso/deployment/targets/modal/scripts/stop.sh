# Stop the Modal app: its containers end and its resources are released.
# `--yes`: the CLI asks for confirmation and aborts without a TTY.
set -euo pipefail
modal app stop "$KAPSO_VALUE_APP" --yes
