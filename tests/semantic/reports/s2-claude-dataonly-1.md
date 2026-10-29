# S2 on claude_code

- run: S2-claude_code-20261028T134921Z
- machine: kapso-fresh-s2-claude-dataonly-1
- package: 0.8.0.dev1 (da503513b0e7)
- started: 2026-10-28T13:49:21+00:00  finished: 2026-10-28T14:02:30+00:00
- user: persona (ml-engineer, codex gpt-6-astra)
- pins: wheel_sha256 da503513b0e7

| step | messages | questions | minutes | longest message | completed | artifacts | verdict |
|---|---|---|---|---|---|---|---|
| setup | 1 | 0 | 0.8 | 8 lines | yes | 1/1 | pass |
| build-data-only | 3 | 1 | 2.6 | 15 lines | yes | 1/1 | FAIL |

| step | kind | minutes | metrics | completed | artifacts | verdict |
|---|---|---|---|---|---|---|
| install | shell | 0.1 | - | yes | 3/3 | pass |

Judge: gemini vertex_ai/gemini-4-argon via litellm vertex_ai, 2 pass(es), bar 4 (the worst item binds)

| dimension | per-pass worst item | adjudicated items | final | verdict |
|---|---|---|---|---|
| proactive | 5, 5 | 0 | 5 | pass |
| clear | 4, 5 | 0 | 4 | pass |
| not annoying | 5, 5 | 0 | 5 | pass |
| engaging | 5, 4 | 0 | 4 | pass |
| return on attention | 4, 5 | 0 | 4 | pass |

Step notes:
- setup: link clicks: judged by hand from the transcript (the logins were present, so none were needed)
- build-data-only: candidate criteria judged by hand from the answers artifact; a campaign was launched: False (the step forbids it)

The driver's own acts (named, never the persona's):
- churn: the example's README replaced by the repository's own for the persona (no Kapso line, no recorded result)
- fraud-data: the example's README replaced by the repository's own for the persona (no Kapso line, no recorded result)

Transcripts:
- transcripts/build-data-only.jsonl
- transcripts/setup.jsonl

Result: FAIL (2/3 steps; required steps missing: cold-install, build-churn, build-pause, watch, triggers, harness-export, campaign-tools, inbox, build-fraud, build-empty-wish, harness-new, harness-probe, review, deploy, learn, learn-complete, session-brief, experience-share, second-engineer-build, harness-improve, campaign-session-isolation, cold-start; steps failed: build-data-only)
