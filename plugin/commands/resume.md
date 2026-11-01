---
description: "Resume a dead or stopped Kapso campaign from its checkpoint, after the diagnosis"
argument-hint: "<campaign> [--budget-minutes N]"
---
Follow the `kapso` skill (`/kapso:kapso`) for: $ARGUMENTS

The diagnosis comes first: a slow or stalled run is not resumed, and a dead one is classified from the log's last lines with its fix named. Then `kapso build --output <path> --resume --detach`, with only what changes (a bigger budget), and the watch line in the same reply. With more than one dead campaign, ask which. Pass `--config kapso-config.yaml` on every line when the project root holds that file.
