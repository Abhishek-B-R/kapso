# S2-mechanical on claude_code

- run: S2-mechanical-claude_code-20261027T022441Z
- machine: kapso-fresh-wp7b
- package: 0.8.0.dev1 (c16a36e94479)
- started: 2026-10-27T02:24:41+00:00  finished: 2026-10-27T04:38:55+00:00
- user: scripted
- pins: wheel_sha256 c16a36e94479

| step | messages | questions | minutes | longest message | completed | artifacts | verdict |
|---|---|---|---|---|---|---|---|
| setup | 1 | 0 | 0.8 | 10 lines | yes | 1/1 | pass |
| build-churn | 2 | 1 | 1.6 | 9 lines | yes | 2/2 | pass |
| build-pause | 1 | 0 | 1.2 | 13 lines | yes | 2/2 | FAIL |
| watch | 2 | 0 | 0.7 | 3 lines | yes | 1/1 | pass |
| harness-export | 1 | 0 | 0.7 | 4 lines | yes | 5/5 | pass |
| campaign-tools | 1 | 0 | 0.7 | 5 lines | yes | 1/1 | pass |
| inbox | 2 | 1 | 1.8 | 8 lines | yes | 2/2 | pass |
| build-fraud | 2 | 1 | 2.7 | 16 lines | yes | 3/3 | FAIL |
| build-data-only | 2 | 1 | 2.8 | 10 lines | yes | 1/1 | pass |
| build-empty-wish | 2 | 1 | 2.0 | 12 lines | yes | 1/1 | pass |
| harness-new | 2 | 1 | 3.0 | 30 lines | yes | 3/3 | pass |
| review | 2 | 0 | 2.1 | 15 lines | yes | 2/2 | FAIL |
| deploy | 2 | 0 | 5.0 | 10 lines | yes | 1/1 | pass |
| learn | 1 | 1 | 1.1 | 6 lines | yes | 1/1 | pass |
| session-brief | 1 | 0 | 0.2 | 3 lines | yes | 1/1 | pass |
| harness-improve | 2 | 1 | 3.3 | 19 lines | yes | 2/2 | pass |
| experience-share | 1 | 0 | 0.3 | 5 lines | yes | 2/2 | pass |

| step | kind | minutes | metrics | completed | artifacts | verdict |
|---|---|---|---|---|---|---|
| install | shell | 0.1 | - | yes | 3/3 | pass |
| triggers | shell | 21.1 | - | yes | 4/4 | pass |
| harness-probe | shell | 9.8 | - | yes | 2/2 | pass |
| learn-complete | shell | 37.1 | - | no | 2/2 | FAIL |
| cold-start | shell | 0.1 | - | yes | 1/1 | pass |
| cold-install | shell | 0.2 | - | yes | 1/1 | pass |
| campaign-session-isolation | shell | 8.9 | - | yes | 1/1 | pass |

Step notes:
- setup: link clicks: judged by hand from the transcript (the logins were present, so none were needed)
- triggers: main: {'build': '19/20', 'harness': '20/20', 'kapso': '20/21', 'review': '19/20', 'setup': '20/20'}; cross-skill false positives: none
- triggers: holdout: {'holdout': '10/10'}; cross-skill false positives: none
- triggers: the bar: nine of ten of each skill's cases passing every run, no near miss invoking the skill under test; the holdout is read the same way
- triggers: verdict recomputed from the artifacts after the bar's rule read the held-out cases as their own group
- inbox: the injected pause arrived: True
- build-fraud: evaluator files written by the session: ['kapso_evaluation/evaluate.py']
- build-data-only: candidate criteria judged by hand from the answers artifact
- build-empty-wish: candidate criteria judged by hand from the answers artifact
- harness-new: compared with the shipped harness by hand from harness-new-tree.txt
- review: the churn campaign ended: done
- learn: the serving offer (session_sources) was made: True
- learn: the learning crews ran on claude-opus-5 for this round (--learn-model): the token's window for the shipped model was spent
- learn-complete: state failed, cards 0
- session-brief: the sources recognised in the instructions: judged by hand from the answer
- cold-start: partial: the uvx and pipx branches resolve only once the pin is on PyPI
- experience-share: the second user loads the shared bank by reference through kapso-mcp and lists it under the banks it reads; a served build at a tiny budget is left to WP9's round

The driver's own acts (named, never the persona's):
- the key written where the request's fix line says before the person says so (inbox)
- the fixture written for the criteria steps (build-data-only, build-empty-wish)
- the harness's module answers from the driver's policy (harness-new)

Notes:
- wheels: harness-improve, cold-install, experience-share and campaign-session-isolation ran on the second wheel bb288573… (rebuilt after the Codex adapter's fix, 6db87600); every other step on the first c16a36e9… (built at 3e2ab47b), the package line's

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

Result: FAIL (20/24 steps; steps failed: build-pause, build-fraud, review, learn-complete)
