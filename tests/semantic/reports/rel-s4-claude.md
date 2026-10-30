# S4 on claude_code

- run: S4-claude_code+codex-20261030T143227Z
- machine: kapso-fresh-rel-s4-claude
- package: 0.8.0 (60e47a961929)
- started: 2026-10-30T14:32:27+00:00  finished: 2026-10-30T16:05:34+00:00
- user: scripted
- pins: wheel_sha256 60e47a961929, suite_sha256 08f96bc21fad, campaign /home/ubuntu/out/work/s4-campaign

| step | kind | minutes | metrics | completed | artifacts | verdict |
|---|---|---|---|---|---|---|
| campaign | build | 90.8 | campaign_has_void=1, campaign_has_rejection=0 | no | 4/4 | FAIL |
| fact-sheet | shell | 0.3 | campaign_has_void=1, campaign_has_rejection=0 | yes | 3/3 | pass |
| reading-claude_code | reading | 0.9 | correct=None, cold=True | yes | 1/1 | pass |
| reading-codex | reading | 1.0 | correct=None, cold=None | yes | 1/1 | pass |

| bar | value | limit | verdict |
|---|---|---|---|
| readers_correct_min | - | {"min": 6} | FAIL |
| campaign_has_void | 1 | {"min": 1} | pass |
| campaign_has_rejection | 0 | {"min": 1} | FAIL |

Judge: FAILED (judging did not complete); the raw reply is kept beside the record. Not a pass.

Step notes:
- campaign: the churn example at 100 minutes and 2 experiments; the evaluator edited in main for the first attempt and restored for the second; the leak on the second attempt's branch during its evaluation phase
- campaign: the campaign ended done (max_iterations); it holds a void: True; a rejection: False
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
- codex login: the device-auth ChatGPT session of the owner, pushed by fresh_machine.sh at 2026-10-30T14:30:31Z; no Codex credit of the run itself

Transcripts:
- transcripts/reading-claude_code.jsonl
- transcripts/reading-codex.jsonl

Result: FAIL (3/4 steps; steps failed: campaign; bars unmet: readers_correct_min, campaign_has_rejection; the judge's bar not established)
