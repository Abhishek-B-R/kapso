---
description: "What a Kapso build or this session is served: create your bank, share it with the team, add a teammate's bank or an ingested corpus, list, update, remove"
argument-hint: "add|list|share|update|remove [...]"
---
Follow the `kapso` skill (`/kapso:kapso`) for: $ARGUMENTS

With no argument, `kapso experience list` and the one-line menu (`add mine`, `add leeroopedia`, `add --repo <url> --name <n> --detach`, `share <git-url>`, `update`, `remove <ref>`). An ingest runs with `--detach`; a bank shared with the team is loaded by its git reference. Pass `--config kapso-config.yaml` on every line when the project root holds that file.
