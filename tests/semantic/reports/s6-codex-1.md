# S6 on claude_code

- run: S6-claude_code-20261028T231354Z
- machine: kapso-fresh-s6-codex-1
- package: 0.8.0.dev1 (-)
- started: 2026-10-28T23:13:54+00:00  finished: 2026-10-29T02:05:15+00:00
- user: scripted
- pins: suite_sha256 9eee52f12460, cadence_seconds 60.0, budget {'minutes': , learn_model claude-opus-

| step | kind | minutes | metrics | completed | artifacts | verdict |
|---|---|---|---|---|---|---|
| build-one | build | 15.8 | scored_observations=1, delivered=None | yes | 3/3 | pass |
| learn-build-one | build | 115.1 | cards_banked=2, bank_head=3cd9dcbfbfbb4266f56f8f039c6bc315c6ca8566 | yes | 2/2 | pass |
| build-two | build | 40.0 | scored_observations=2, delivered=None | yes | 3/3 | pass |
| comparison | shell | 0.3 | gap_min=-0.00039999999999995595, behind_points=5, lessons_cited=1, scored_observations_min=1, scored_observations={'build_one': 1, 'build_two': 2}, delivered={'build_one': 0.8501, 'build_two': 0.8497} | yes | 3/3 | pass |

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
- learn-build-one: the bank banked 2 card(s) at 3cd9dcbfbfbb4266f56f8f039c6bc315c6ca8566
- build-two: served: file:///home/ubuntu/out/bank-one.git
- build-two: scored observations: 2
- build-two: WP1/WP4/WP6/WP7 delivered 0.845, 0.847, 0.851 and nothing twice at this budget
- comparison: an observed pair with the spread beside it; a non-negative gap at every common checkpoint and a cited lesson is the bar; both builds must score at least one observation
- comparison: WP1/WP4/WP6/WP7 delivered 0.845, 0.847, 0.851 and nothing twice at this budget

The driver's own acts (named, never the persona's):
- both builds from the same seed, data, evaluator, config, models and machine; build one served nothing, build two served build one's banked experience

Notes:
- WP1/WP4/WP6/WP7 delivered 0.845, 0.847, 0.851 and nothing twice at this budget

Transcripts:

Result: PASS (4/4 steps)
