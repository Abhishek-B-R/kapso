# S2-mechanical on claude_code

- run: S2-mechanical-claude_code-20261027T011337Z
- machine: kapso-fresh-wp7
- package: 0.8.0.dev1 (c16a36e94479)
- started: 2026-10-27T01:13:37+00:00  finished: 2026-10-27T02:30:53+00:00
- user: scripted
- pins: wheel_sha256 c16a36e94479

| step | messages | questions | minutes | longest message | completed | artifacts | verdict |
|---|---|---|---|---|---|---|---|
| setup | 1 | 0 | 1.3 | 10 lines | yes | 1/1 | pass |
| build-churn | 2 | 1 | 2.2 | 9 lines | yes | 2/2 | pass |
| build-pause | 1 | 0 | 1.3 | 12 lines | yes | 2/2 | pass |
| watch | 2 | 0 | 0.7 | 3 lines | yes | 1/1 | pass |
| harness-export | 1 | 0 | 0.5 | 3 lines | yes | 5/5 | pass |
| campaign-tools | 1 | 0 | 0.8 | 5 lines | yes | 1/1 | pass |
| inbox | 2 | 0 | 1.0 | 16 lines | no | 2/2 | FAIL |
| build-fraud | 2 | 1 | 3.0 | 11 lines | yes | 3/3 | pass |
| build-data-only | 2 | 1 | 2.3 | 10 lines | yes | 1/1 | pass |
| build-empty-wish | 2 | 1 | 1.3 | 12 lines | yes | 1/1 | pass |
| harness-new | 3 | 2 | 3.3 | 27 lines | no | 1/1 | FAIL |
| review | 2 | 0 | 2.2 | 20 lines | yes | 2/2 | FAIL |
| deploy | 2 | 0 | 9.4 | 8 lines | yes | 1/1 | pass |

| step | kind | minutes | metrics | completed | artifacts | verdict |
|---|---|---|---|---|---|---|
| install | shell | 0.1 | - | yes | 3/3 | pass |
| cold-install | shell | 0.2 | - | no | 1/1 | FAIL |
| triggers | shell | 22.0 | - | yes | 4/4 | pass |
| harness-probe | shell | 0.0 | - | no | 0/0 | FAIL |

Step notes:
- setup: link clicks: judged by hand from the transcript (the logins were present, so none were needed)
- triggers: the bar per skill is read off triggers-main/REPORT.md
- inbox: the injected pause arrived: True
- build-fraud: evaluator files written by the session: ['kapso_evaluation/evaluate.py']
- build-data-only: candidate criteria judged by hand from the answers artifact
- build-empty-wish: candidate criteria judged by hand from the answers artifact
- harness-new: compared with the shipped harness by hand from harness-new-tree.txt
- harness-probe: no harness was written
- review: the churn campaign ended: done

The driver's own acts (named, never the persona's):
- the key written where the request's fix line says before the person says so (inbox)
- the fixture written for the criteria steps (build-data-only, build-empty-wish)
- the harness's module answers from the driver's policy (harness-new)

Transcripts:
- transcripts/build-churn.jsonl
- transcripts/build-data-only.jsonl
- transcripts/build-empty-wish.jsonl
- transcripts/build-fraud.jsonl
- transcripts/build-pause.jsonl
- transcripts/campaign-tools.jsonl
- transcripts/deploy-2.jsonl
- transcripts/deploy.jsonl
- transcripts/harness-export.jsonl
- transcripts/harness-new.jsonl
- transcripts/inbox-reply.jsonl
- transcripts/inbox.jsonl
- transcripts/review-2.jsonl
- transcripts/review.jsonl
- transcripts/setup.jsonl
- transcripts/watch-2.jsonl
- transcripts/watch.jsonl

Result: FAIL (12/17 steps; required steps missing: learn, learn-complete, session-brief, experience-share, harness-improve, campaign-session-isolation, cold-start; steps failed: cold-install, inbox, harness-new, harness-probe, review)
