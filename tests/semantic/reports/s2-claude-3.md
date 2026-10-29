# S2 on claude_code

**Advisory: the persona did not correct the planted baseline: the engaging and not-annoying dimensions are advisory for this arm** (an arm run on the development box proves the flow, not its smoothness; never a fresh-machine acceptance)

- run: S2-claude_code-20261028T210609Z
- machine: kapso-fresh-s2-claude-3
- package: 0.8.0.dev1 (b096fffa2449)
- started: 2026-10-28T21:06:09+00:00  finished: 2026-10-29T00:48:10+00:00
- user: persona (ml-engineer, codex gpt-5.6-sol)
- pins: wheel_sha256 b096fffa2449

| step | messages | questions | minutes | longest message | completed | artifacts | verdict |
|---|---|---|---|---|---|---|---|
| setup | 1 | 0 | 0.7 | 4 lines | yes | 1/1 | pass |
| build-churn | 2 | 1 | 2.4 | 15 lines | yes | 2/2 | FAIL |
| build-pause | 1 | 0 | 1.8 | 13 lines | yes | 2/2 | FAIL |
| watch | 2 | 0 | 0.5 | 3 lines | yes | 1/1 | pass |
| harness-export | 1 | 0 | 1.1 | 4 lines | yes | 5/5 | pass |
| campaign-tools | 1 | 0 | 1.0 | 5 lines | yes | 1/1 | pass |
| inbox | 2 | 1 | 1.8 | 10 lines | no | 2/2 | FAIL |
| build-fraud | 3 | 2 | 4.0 | 12 lines | yes | 4/4 | pass |
| build-data-only | 1 | 1 | 2.4 | 11 lines | yes | 1/1 | pass |
| build-empty-wish | 1 | 1 | 1.4 | 6 lines | yes | 1/1 | pass |
| harness-new | 4 | 2 | 6.2 | 33 lines | yes | 3/3 | pass |
| review | 2 | 0 | 1.4 | 20 lines | yes | 2/2 | FAIL |
| deploy | 2 | 2 | 1.0 | 8 lines | no | 1/1 | FAIL |
| learn | 1 | 1 | 0.3 | 5 lines | yes | 1/1 | pass |
| session-brief | 1 | 0 | 0.2 | 7 lines | yes | 1/1 | pass |
| experience-share | 1 | 0 | 0.5 | 6 lines | yes | 2/2 | pass |
| harness-improve | 2 | 1 | 1.4 | 14 lines | yes | 2/2 | pass |
| codex-rules-probe | - | - | - | - | - | - | deferred: Codex's mechanism; Claude Code's is the plugin switch, which the isolation step reads |

| step | kind | minutes | metrics | completed | artifacts | verdict |
|---|---|---|---|---|---|---|
| install | shell | 0.1 | - | yes | 3/3 | pass |
| cold-install | shell | 0.4 | - | yes | 1/1 | pass |
| triggers | shell | 19.7 | - | yes | 4/4 | pass |
| harness-probe | shell | 10.1 | - | yes | 2/2 | pass |
| learn-complete | shell | 112.1 | - | yes | 2/2 | pass |
| second-engineer-build | build | 20.1 | - | no | 1/1 | FAIL |
| campaign-session-isolation | shell | 9.8 | - | yes | 1/1 | pass |
| cold-start | shell | 0.2 | - | yes | 1/1 | pass |

Judge: gemini vertex_ai/gemini-4-argon via litellm vertex_ai, 2 pass(es), bar 4 (the worst item binds)

| dimension | per-pass worst item | adjudicated items | final | verdict |
|---|---|---|---|---|
| proactive | 4, 1 | 1 | 1 | FAIL |
| clear | 4, 4 | 0 | 4 | pass |
| not annoying | 4, 4 | 0 | 4 | pass |
| engaging | 2, 2 | 0 | 2 | FAIL |
| return on attention | 2, 2 | 2 | 2 | FAIL |

Step notes:
- setup: link clicks: judged by hand from the transcript (the logins were present, so none were needed)
- build-churn: the launch reached: starting; a proposal was offered: True
- build-churn: the planted baseline: not corrected
- watch: the status at the read: state=running phase=ideation; the answer reflected it: True
- triggers: main: {'build': '19/20', 'harness': '20/20', 'kapso': '20/21', 'review': '20/20', 'setup': '20/20'}; cross-skill false positives: none
- triggers: holdout: {'holdout': '10/10'}; cross-skill false positives: none
- triggers: the bar: nine of ten of each skill's cases passing every run, no near miss invoking the skill under test; the holdout is read the same way
- inbox: the injected pause arrived: True
- inbox: the request was replied: True; the campaign resumed (a continued event): False
- build-fraud: evaluator files written by the session: ['build/evaluation/evaluate.py']
- build-fraud: the evaluator's contract: ok
- build-data-only: candidate criteria judged by hand from the answers artifact; a campaign was launched: False (the step forbids it)
- build-empty-wish: candidate criteria judged by hand from the answers artifact; a campaign was launched: False (the step forbids it)
- harness-new: compared with the shipped harness by hand from harness-new-tree.txt
- review: the churn campaign ended: done; the answer named the delivered branch None: True; a merge verdict: True
- deploy: the deployed call against the delivered predictions: not established: no deployment record
- learn: the serving offer (session_sources) was made: True
- learn: the learning crews ran on claude-opus-5-5 for this round (--learn-model): the token's window for the shipped model was spent
- learn-complete: state done, cards 2
- session-brief: a bank tool succeeded (a card read): True; the sources recognised judged by hand from the answer
- experience-share: the second user loads the shared bank by reference through kapso-mcp and lists it under the banks it reads; a served build at a tiny budget is left to WP9's round
- second-engineer-build: served the shared bank: False; a scored delivery: False; the bank in the build's records: False; final state: None
- cold-start: partial: the uvx and pipx branches resolve only once the pin is on PyPI

The driver's own acts (named, never the persona's):
- build-churn: the task view's README and the brief's Baseline line state 0.90 (planted); the card is certain of about 0.80
- churn-pause: the example's README replaced by the repository's own for the persona (no Kapso line, no recorded result)
- churn: the example's README replaced by the repository's own for the persona (no Kapso line, no recorded result)
- fraud-data: the example's README replaced by the repository's own for the persona (no Kapso line, no recorded result)
- fraud: the example's README replaced by the repository's own for the persona (no Kapso line, no recorded result)
- harness-improve: answered by the trading-author card (its knowledge the step needs), not the run's ml-engineer
- harness-new: answered by the trading-author card (its knowledge the step needs), not the run's ml-engineer
- inbox: the key written where the request's fix line says before the person says so
- second-engineer-build: the churn fixture copied to the second user's home; the build run as that user with the bank by reference
- trading-author: the example's README replaced by the repository's own for the persona (no Kapso line, no recorded result)

Transcripts:
- transcripts/build-churn.jsonl
- transcripts/build-data-only.jsonl
- transcripts/build-empty-wish.jsonl
- transcripts/build-fraud.jsonl
- transcripts/build-pause.jsonl
- transcripts/campaign-tools.jsonl
- transcripts/deploy-2.jsonl
- transcripts/deploy.jsonl
- transcripts/experience-share.jsonl
- transcripts/harness-export.jsonl
- transcripts/harness-improve.jsonl
- transcripts/harness-new.jsonl
- transcripts/inbox-reply.jsonl
- transcripts/inbox.jsonl
- transcripts/learn.jsonl
- transcripts/review-2.jsonl
- transcripts/review.jsonl
- transcripts/session-brief.jsonl
- transcripts/setup.jsonl
- transcripts/watch-2.jsonl
- transcripts/watch.jsonl

Result: FAIL (19/25 steps; steps failed: build-churn, build-pause, inbox, review, deploy, second-engineer-build; the judge's bar not established)
