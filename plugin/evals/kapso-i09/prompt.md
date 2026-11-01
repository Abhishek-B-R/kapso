---
description: "a phrasing kapso should answer"
tags: [main, implicit, kapso]
model: claude-opus-5-5
runs: 2
max_turns: 6
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

kapso doctor says `[FAIL] OPENAI_API_KEY (embeddings)` but I exported OPENAI_API_KEY in my shell and `echo $OPENAI_API_KEY` shows it. Why, and how do I fix it?
