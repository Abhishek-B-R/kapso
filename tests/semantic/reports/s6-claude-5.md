# S6 on claude_code

- run: S6-claude_code-20261028T111205Z
- machine: kapso-fresh-s6-claude-5
- package: 0.8.0.dev1 (-)
- started: 2026-10-28T11:12:05+00:00  finished: 2026-10-28T14:05:18+00:00
- user: scripted
- pins: suite_sha256 c3842709d398, cadence_seconds 60.0, budget {'minutes': , learn_model claude-opus-

| step | kind | minutes | metrics | completed | artifacts | verdict |
|---|---|---|---|---|---|---|
| build-one | build | 19.4 | scored_observations=1, delivered=None | yes | 3/3 | pass |
| learn-build-one | build | 135.8 | cards_banked=3, bank_head=53f04261cd846af53d5910014904cef1793ea085 | yes | 2/2 | pass |
| build-two | build | 17.6 | scored_observations=1, delivered=None | yes | 3/3 | pass |
| comparison | shell | 0.2 | gap_min=None, behind_points=0, lessons_cited=1, scored_observations_min=1, scored_observations={'build_one': 1, 'build_two': 1}, delivered={'build_one': 0.8508, 'build_two': 0.8509} | yes | 3/3 | pass |

| bar | value | limit | verdict |
|---|---|---|---|
| lessons_cited | 1 | {"min": 1} | pass |
| scored_observations_min | 1 | {"min": 1} | pass |

Step notes:
- build-one: served: nothing
- build-one: scored observations: 1
- build-one: WP1/WP4/WP6/WP7 delivered 0.845, 0.847, 0.851 and nothing twice at this budget
- learn-build-one: the learn runs on the development box over build one's campaign
- learn-build-one: the learning crews ran on claude-opus-5-5 (--learn-model): the token's window for the shipped model was spent
- learn-build-one: the bank banked 3 card(s) at 53f04261cd846af53d5910014904cef1793ea085
- build-two: served: file:///home/ubuntu/out/bank-one.git
- build-two: scored observations: 1
- build-two: WP1/WP4/WP6/WP7 delivered 0.845, 0.847, 0.851 and nothing twice at this budget
- comparison: an observed pair with the spread beside it; a non-negative gap at every common checkpoint and a cited lesson is the bar; both builds must score at least one observation
- comparison: WP1/WP4/WP6/WP7 delivered 0.845, 0.847, 0.851 and nothing twice at this budget

The driver's own acts (named, never the persona's):
- both builds from the same seed, data, evaluator, config, models and machine; build one served nothing, build two served build one's banked experience

Notes:
- WP1/WP4/WP6/WP7 delivered 0.845, 0.847, 0.851 and nothing twice at this budget

Transcripts:

Result: PASS (4/4 steps)
