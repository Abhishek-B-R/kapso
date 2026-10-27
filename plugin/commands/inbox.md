---
description: "What a paused Kapso campaign is waiting on you for, and the reply that resumes it"
argument-hint: "[campaign] [note]"
---
Follow the `kapso` skill (`/kapso:kapso`) for: $ARGUMENTS

With no campaign, the one `kapso inbox` lists as waiting. Show the request rows (key, hit, tried, fix, next); when the user says it is done, reply with a note through `kapso inbox reply <path> <id> "<note>" --detach`, never with a value. Pass `--config kapso-config.yaml` on every line when the project root holds that file.
