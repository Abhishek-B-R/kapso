---
description: "a phrasing kapso-harness should answer"
tags: [main, implicit, kapso-harness]
model: claude-opus-5-5
runs: 2
max_turns: 6
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

Our kapso attempts keep fetching the full dataset instead of the sample; improve the harness from the last run so they stop.
