# S2-mechanical on codex

- machine: dev-box
- package: 0.8.0.dev1 (c16a36e94479)
- started: 2026-10-27T01:12:12+00:00  finished: 2026-10-27T07:41:52+00:00

| step | messages | questions | minutes | longest message | completed | artifacts | verdict |
|---|---|---|---|---|---|---|---|
| install | 0 | 0 | 0.2 | 0 lines | yes | 1/1 | pass |
| setup | 1 | 0 | 1.3 | 4 lines | yes | 2/2 | pass |
| cold-install | - | - | - | - | - | - | deferred: one machine: the cold wheel install is the fresh machine's step |
| harness-export | 0 | 0 | 0.2 | 0 lines | yes | 5/5 | pass |
| campaign-tools | 1 | 0 | 0.8 | 3 lines | yes | 1/1 | pass |
| build-fraud | 2 | 1 | 2.4 | 7 lines | yes | 3/3 | pass |
| learn | - | - | - | - | - | - | deferred: hours on the development box; the Claude Code half runs it |
| learn-complete | - | - | - | - | - | - | deferred: hours on the development box; the Claude Code half runs it |
| session-brief | 1 | 0 | 0.3 | 5 lines | yes | 1/1 | pass |
| experience-share | - | - | - | - | - | - | deferred: deferred on Codex by the matrix |
| harness-improve | - | - | - | - | - | - | deferred: deferred on Codex by the matrix |
| cold-start | - | - | - | - | - | - | deferred: the launcher is Claude Code's path; Codex runs kapso-mcp from PATH |
| triggers | 0 | 0 | 47.9 | 0 lines | no | 4/4 | FAIL |
| build-data-only | 2 | 1 | 1.2 | 4 lines | yes | 1/1 | pass |
| build-empty-wish | 2 | 1 | 0.9 | 7 lines | yes | 1/1 | pass |
| build-churn | 1 | 0 | 1.2 | 7 lines | yes | 2/2 | pass |
| watch | 2 | 0 | 0.7 | 3 lines | yes | 1/1 | pass |
| review | 2 | 0 | 1.4 | 10 lines | yes | 2/2 | pass |
| build-pause | 1 | 0 | 0.8 | 4 lines | yes | 2/2 | pass |
| inbox | 2 | 0 | 0.8 | 5 lines | yes | 2/2 | pass |
| deploy | 2 | 0 | 8.8 | 3 lines | yes | 1/1 | pass |
| campaign-session-isolation | 0 | 0 | 9.8 | 0 lines | yes | 1/1 | pass |
| harness-new | 2 | 1 | 4.5 | 21 lines | yes | 3/3 | pass |
| codex-rules-probe | 0 | 0 | 0.2 | 0 lines | yes | 1/1 | pass |
| harness-probe | 0 | 0 | 8.8 | 0 lines | yes | 2/2 | pass |

Step notes:
- install: Codex: the plugin's skills load by name; its MCP tools reach a session through the `codex mcp add` line the setup skill runs
- setup: link clicks: judged by hand from the transcript (the logins were present, so none were needed)
- setup: the `codex mcp add kapso -- kapso-mcp` line's effect is the mcp list artifact
- build-fraud: evaluator files written by the session: ['evaluation/evaluate.py']
- session-brief: the sources recognised in the instructions: judged by hand from the answer
- triggers: main: {'build': '18/18', 'harness': '17/18', 'kapso': '17/17', 'review': '17/18', 'setup': '18/18'}; cross-skill false positives: ['harness-c03', 'review-c02']
- triggers: holdout: {'holdout': '10/10'}; cross-skill false positives: none
- triggers: the bar: nine of ten of each skill's cases passing every run, no near miss invoking the skill under test; the holdout is read the same way
- triggers: verdict recomputed from the artifacts after the bar's rule read the held-out cases as their own group
- build-data-only: candidate criteria judged by hand from the answers artifact
- build-empty-wish: candidate criteria judged by hand from the answers artifact
- review: the churn campaign ended: done
- inbox: the injected pause arrived: True
- deploy: the campaign deployed is the second machine's delivered churn campaign (generic_exp_0 at 0.847), restored under this box's work directory by restore_campaign.py with its old home rewritten and its deployment removed: the box's own sixty-minute build delivered nothing (see build-churn and review)
- harness-new: compared with the shipped harness by hand from harness-new-tree.txt
- codex-rules-probe: the session's cwd is a gitignored subdirectory of a repository, as an implementation session's is; the rules file sits in it

Notes:
- wheels: the campaign steps run from 04:15 UTC on (build-churn, build-pause, watch, inbox, harness-new, harness-probe, review, deploy, campaign-session-isolation, codex-rules-probe) ran on the second wheel bb288573… (rebuilt after the Codex adapter's fix, 6db87600); the other steps on the first c16a36e9… (built at 3e2ab47b), the package line's
- the trigger step's verdict was recomputed after the pull-request review under the first-read rule (87 of 89 main cases; two cross-skill false positives named in its notes)

Transcripts:
- transcripts/build-churn.jsonl
- transcripts/build-data-only.jsonl
- transcripts/build-empty-wish.jsonl
- transcripts/build-fraud.jsonl
- transcripts/build-pause.jsonl
- transcripts/campaign-tools.jsonl
- transcripts/deploy-2.jsonl
- transcripts/deploy.jsonl
- transcripts/harness-new.jsonl
- transcripts/inbox-reply.jsonl
- transcripts/inbox.jsonl
- transcripts/install.jsonl
- transcripts/review-2.jsonl
- transcripts/review.jsonl
- transcripts/session-brief.jsonl
- transcripts/setup.jsonl
- transcripts/watch-2.jsonl
- transcripts/watch.jsonl

Result: FAIL (18/19 steps)
