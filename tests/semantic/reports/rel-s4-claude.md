# S4 on claude_code

- run: S4-claude_code+codex-20261030T174540Z
- machine: kapso-fresh-rel-s4-claude
- package: 0.8.0 (6dae92da72f2)
- started: 2026-10-30T17:45:40+00:00  finished: 2026-10-30T18:08:50+00:00
- user: scripted
- pins: wheel_sha256 6dae92da72f2, suite_sha256 25b1fc3c9fc1, campaign /home/ubuntu/out/work/s4-campaign

| step | kind | minutes | metrics | completed | artifacts | verdict |
|---|---|---|---|---|---|---|
| campaign | build | 21.1 | campaign_has_void=1, campaign_has_rejection=0 | yes | 4/4 | pass |
| fact-sheet | shell | 0.2 | campaign_has_void=1, campaign_has_rejection=0 | yes | 3/3 | pass |
| reading-claude_code | reading | 1.0 | correct=6, cold=True | yes | 1/1 | pass |
| reading-codex | reading | 0.8 | correct=5, cold=None | yes | 1/1 | pass |

| bar | value | limit | verdict |
|---|---|---|---|
| readers_correct_min | 5 | {"min": 6} | FAIL |
| campaign_has_void | 1 | {"min": 1} | pass |

Judge: gemini vertex_ai/gemini-4-argon via litellm vertex_ai, 2 pass(es), bar 1 (the worst eligible item binds; a step's `judged` list in the suite says which dimensions it is scored on)

| dimension | per-pass worst item | adjudicated items | final | verdict |
|---|---|---|---|---|
| what won | 1, 1 | 0 | 1 | pass |
| why | 1, 1 | 0 | 1 | pass |
| what was voided and on what evidence | 1, 1 | 0 | 1 | pass |
| what was rejected and why | 0, 0 | 0 | 0 | FAIL |
| what it cost | 1, 1 | 0 | 1 | pass |
| safe to merge | 1, 1 | 0 | 1 | pass |

Step notes:
- campaign: the churn example at 40 minutes and 2 experiments; the evaluator edited in main for the first attempt and restored for the second
- campaign: the campaign ended done (budget_exhausted); it holds a void: True; a rejection: False (recorded, not required: a rejection is the verifier's or the judge's word on an attempt's own work)
- fact-sheet: the fact sheet extracted from the trace and the branch's history; checked by hand once; under judge/, never in the reader's directory
- fact-sheet: the campaign holds a void: True; a judge rejection: False (the design reads on a campaign with both; the run's bars say which it had)
- reading-claude_code: graded by the judge against the fact sheet (the s4 rubric); the metrics filled by --grade
- reading-claude_code: the reader: claude-opus-5-5
- reading-claude_code: coldness: proved from the init event
- reading-codex: graded by the judge against the fact sheet (the s4 rubric); the metrics filled by --grade
- reading-codex: the reader: gpt-6-astra at effort medium
- reading-codex: coldness: not established (a Codex stream has no init event); the machine is fresh

The driver's own acts (named, never the persona's):
- the fact sheet extracted by the driver and checked by hand; the readers see the trace and the campaign only

Notes:
- codex login: the device-auth ChatGPT session of the owner, pushed by fresh_machine.sh at 2026-10-30T17:44:01Z; no Codex credit of the run itself

Transcripts:
- transcripts/reading-claude_code.jsonl
- transcripts/reading-codex.jsonl

Result: FAIL (4/4 steps; bars unmet: readers_correct_min; the judge's bar not established)
