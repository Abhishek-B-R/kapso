# S4 on claude_code

- run: S4-20261028T185041Z
- machine: kapso-fresh-s4-claude-1
- package: 0.8.0.dev1 (-)
- started: 2026-10-28T18:50:41+00:00  finished: 2026-10-28T18:52:56+00:00
- user: scripted
- pins: suite_sha256 2be2673aa9fe, campaign /home/ubuntu

| step | kind | minutes | metrics | completed | artifacts | verdict |
|---|---|---|---|---|---|---|
| fact-sheet | shell | 0.2 | - | yes | 3/3 | pass |
| reading-claude_code | reading | 1.0 | correct=6, cold=True | yes | 1/1 | pass |
| reading-codex | reading | 0.9 | correct=6, cold=None | yes | 1/1 | pass |

| bar | value | limit | verdict |
|---|---|---|---|
| readers_correct_min | 6 | {"min": 6} | pass |

Judge: gemini vertex_ai/gemini-4-argon via litellm vertex_ai, 2 pass(es), bar 1 (the worst item binds)

| dimension | per-pass worst item | adjudicated items | final | verdict |
|---|---|---|---|---|
| what won | 1, 1 | 0 | 1 | pass |
| why | 1, 1 | 0 | 1 | pass |
| what was voided and on what evidence | 1, 1 | 0 | 1 | pass |
| what was rejected and why | 1, 1 | 0 | 1 | pass |
| what it cost | 1, 1 | 0 | 1 | pass |
| safe to merge | 1, 1 | 0 | 1 | pass |

Step notes:
- fact-sheet: the fact sheet extracted from the trace and the branch's history; checked by hand once; under judge/, never in the reader's directory
- reading-claude_code: graded by the judge against the fact sheet (the s4 rubric); the metrics filled by --grade
- reading-codex: graded by the judge against the fact sheet (the s4 rubric); the metrics filled by --grade

The driver's own acts (named, never the persona's):
- the fact sheet extracted by the driver and checked by hand; the readers see the trace and the campaign only

Transcripts:
- transcripts/reading-claude_code.jsonl
- transcripts/reading-codex.jsonl

Result: PASS (3/3 steps)
