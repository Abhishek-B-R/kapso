---
description: "a phrasing kapso-harness should answer"
tags: [main, implicit, kapso-harness]
model: claude-opus-5-5
runs: 2
max_turns: 6
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

Add a delegate to our harness that audits each attempt for look-ahead, and bump its version.
