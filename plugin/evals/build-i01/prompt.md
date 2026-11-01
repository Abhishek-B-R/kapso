---
description: "a phrasing kapso-build should answer"
tags: [main, implicit, kapso-build]
model: claude-opus-5-5
runs: 2
max_turns: 6
timeout_seconds: 180
allowed_tools: [Read, Glob, Grep, Skill]
---

I have a churn model in this repo (train.py, judged by evaluation/evaluate.py). Use Kapso to get the ROC AUC above 0.85. evaluation/evaluate.py is the judge and must not be changed. Kick it off and tell me how to follow along.
