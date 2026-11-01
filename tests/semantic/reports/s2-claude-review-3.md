# S2 on claude_code

**Advisory: the persona did not correct the planted baseline: the engaging and not-annoying dimensions are advisory for this arm** (an arm run on the development box proves the flow, not its smoothness; never a fresh-machine acceptance)

- run: S2-claude_code-20261028T130142Z
- machine: kapso-fresh-s2-claude-review-3
- package: 0.8.0.dev1 (d99da3f3ff98)
- started: 2026-10-28T13:01:42+00:00  finished: 2026-10-28T14:21:52+00:00
- user: persona (ml-engineer, codex gpt-6-astra)
- pins: wheel_sha256 d99da3f3ff98

| step | messages | questions | minutes | longest message | completed | artifacts | verdict |
|---|---|---|---|---|---|---|---|
| setup | 1 | 0 | 0.8 | 10 lines | yes | 1/1 | pass |
| build-churn | 2 | 1 | 2.2 | 8 lines | yes | 2/2 | pass |
| review | 2 | 0 | 1.4 | 19 lines | yes | 2/2 | FAIL |

| step | kind | minutes | metrics | completed | artifacts | verdict |
|---|---|---|---|---|---|---|
| install | shell | 0.1 | - | yes | 3/3 | pass |

Judge: gemini vertex_ai/gemini-4-argon via litellm vertex_ai, 2 pass(es), bar 4 (the worst item binds)

| dimension | per-pass worst item | adjudicated items | final | verdict |
|---|---|---|---|---|
| proactive | 5, 5 | 0 | 5 | pass |
| clear | 5, 5 | 0 | 5 | pass |
| not annoying | 5, 5 | 0 | 5 | pass |
| engaging | 5, 4 | 0 | 4 | pass |
| return on attention | 5, 5 | 0 | 5 | pass |

Step notes:
- setup: link clicks: judged by hand from the transcript (the logins were present, so none were needed)
- build-churn: the launch reached: starting; a proposal was offered: True
- build-churn: the planted baseline: not corrected
- review: the churn campaign ended: done; the answer named the delivered branch 'generic_exp_0': True; a merge verdict: True

The driver's own acts (named, never the persona's):
- build-churn: the task view's README and the brief's Baseline line state 0.90 (planted); the card is certain of about 0.80
- churn: the example's README replaced by the repository's own for the persona (no Kapso line, no recorded result)

Transcripts:
- transcripts/build-churn.jsonl
- transcripts/review-2.jsonl
- transcripts/review.jsonl
- transcripts/setup.jsonl

Result: FAIL (3/4 steps; required steps missing: cold-install, build-pause, watch, triggers, harness-export, campaign-tools, inbox, build-fraud, build-data-only, build-empty-wish, harness-new, harness-probe, deploy, learn, learn-complete, session-brief, experience-share, second-engineer-build, harness-improve, campaign-session-isolation, cold-start; steps failed: review)
