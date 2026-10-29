# S6 on codex

- run: S6-codex-20261029T032029Z
- machine: kapso-fresh-s6-codex-2
- package: 0.8.0.dev1 (-)
- started: 2026-10-29T03:20:29+00:00  finished: 2026-10-29T06:15:33+00:00
- user: scripted
- pins: suite_sha256 4fbb408fb8f7, cadence_seconds 60.0, budget {'minutes': 60, 'experiments': 3}, learn_model claude-opus-5-5
- suite: re-derived under suite 0df219d86711; the run pinned 4fbb408fb8f7 (a changed suite changes the verdict, never the record)

| step | messages | questions | minutes | longest message | completed | artifacts | verdict |
|---|---|---|---|---|---|---|---|
| review-two | 1 | 1 | 0.9 | 4 lines | yes | 1/1 | pass |

| step | kind | minutes | metrics | completed | artifacts | verdict |
|---|---|---|---|---|---|---|
| build-one | build | 40.7 | scored_observations=2, delivered=0.8508 | yes | 3/3 | pass |
| learn-build-one | build | 94.0 | cards_banked=1, bank_head=4a865ffc128f1a8d032ddca74493efac98dbd932 | yes | 2/2 | pass |
| build-two | build | 38.8 | scored_observations=2, delivered=0.8494 | yes | 3/3 | pass |
| comparison | shell | 0.4 | gap_min=-0.0013999999999999568, behind_points=0, lessons_cited=0, scored_observations_min=2, scored_observations={'build_one': 2, 'build_two': 2}, delivered={'build_one': 0.8508, 'build_two': 0.8494} | yes | 3/3 | pass |

| bar | value | limit | verdict |
|---|---|---|---|
| lessons_cited | 0 | {"min": 1} | FAIL |
| scored_observations_min | 2 | {"min": 1} | pass |
| review_names_served_cards | 1 | {"min": 1} | pass |

Step notes:
- build-one: served: nothing
- build-one: the campaign's sessions on codex
- build-one: scored observations: 2
- build-one: WP1/WP4/WP6/WP7 delivered 0.845, 0.847, 0.851 and nothing twice at this budget
- learn-build-one: the learn runs on the development box over build one's campaign
- learn-build-one: the learning crews ran on claude-opus-5-5 (--learn-model): the token's window for the shipped model was spent
- learn-build-one: the bank banked 1 card(s) at 4a865ffc128f1a8d032ddca74493efac98dbd932
- build-two: served: file:///home/ubuntu/out/bank-one.git
- build-two: the campaign's sessions on codex
- build-two: scored observations: 2
- build-two: WP1/WP4/WP6/WP7 delivered 0.845, 0.847, 0.851 and nothing twice at this budget
- review-two: cards the review named, of those the trace shows read or load-bearing: none
- review-two: re-read 2026-10-29 against the bank's own cards: served cards the review named: insights/basis-columns-encode-link-additive-forms.md
- comparison: an observed pair with the spread beside it; a non-negative gap at every common checkpoint and a cited lesson is the bar; both builds must score at least one observation
- comparison: WP1/WP4/WP6/WP7 delivered 0.845, 0.847, 0.851 and nothing twice at this budget

The driver's own acts (named, never the persona's):
- both builds from the same seed, data, evaluator, config, models and machine; build one served nothing, build two served build one's banked experience

Notes:
- WP1/WP4/WP6/WP7 delivered 0.845, 0.847, 0.851 and nothing twice at this budget
- codex login: the device-auth ChatGPT session of the owner, pushed by fresh_machine.sh at 2026-10-29T03:18:39Z; no Codex credit of the run itself
- re-derived 2026-10-29: the review step against the bank's own cards

Transcripts:
- transcripts/review-two.jsonl

Result: FAIL (5/5 steps; bars unmet: lessons_cited)
