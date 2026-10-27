---
description: "A Kapso harness: write one from the repository, improve one from a run, or check, list, add, update, remove and export"
argument-hint: "new|improve <campaign>|check <ref>|list|add <ref>|update <ref>|remove <ref>|export <ref> --host claude_code|codex"
---
For `new` and `improve`, follow the `kapso-harness` skill (`/kapso:kapso-harness`); for `check`, `list`, `add`, `update`, `remove` and `export`, the `kapso` skill (`/kapso:kapso`), which runs `kapso harness <verb> …` and reads the result. The request: $ARGUMENTS

With no argument, `kapso harness list` and the one-line menu. Pass `--config kapso-config.yaml` on every line when the project root holds that file.
