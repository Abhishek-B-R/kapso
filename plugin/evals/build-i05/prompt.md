---
description: "a phrasing kapso-build should answer"
tags: [main, implicit, kapso-build]
model: claude-opus-5-5
runs: 2
max_turns: 6
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

Build me a fraud scorer on data/transactions.csv that beats the rule-based one in score.py, and prove it.
