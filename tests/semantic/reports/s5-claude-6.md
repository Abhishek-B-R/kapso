# S5 on claude_code

- run: S5-claude_code-20261028T160809Z
- machine: kapso-fresh-s5-claude-6
- package: 0.8.0.dev1 (-)
- started: 2026-10-28T16:08:09+00:00  finished: 2026-10-28T18:45:50+00:00
- user: scripted
- pins: suite_sha256 f0ff3154c04e, cadence_seconds 60.0, bank /home/ubuntu

| step | kind | minutes | metrics | completed | artifacts | verdict |
|---|---|---|---|---|---|---|
| evaluator-crash | injection | 16.2 | attempts_with_the_crash=1, labels_rebuilt_by_campaign=False, truthful=True, names_class=True, names_fix=True, resumed=True, user_messages=2, bank_intact=True | yes | 3/3 | pass |
| killed-writer | injection | 48.7 | writer_killed=True, shown_dead=True, truthful=True, names_class=True, names_fix=True, resumed=True, attempts_kept=True, attempts_before=0, attempts_after=2, user_messages=2, bank_intact=True | yes | 3/3 | FAIL |
| full-disk | injection | 60.6 | fill_said=dd: error writing '/home/ubuntu/out/work/s5-full-disk-disk/filler': No space left on device, enospc_in_log=True, shown_dead=False, truthful=None, names_class=True, names_fix=True, resumed=True, attempts_kept=True, attempts_before=0, attempts_after=2, user_messages=2, bank_intact=True, campaign_saved=True | no | 5/5 | FAIL |
| tampering | injection | 32.1 | evaluator_edited=1, voided=1, integrity_voids=1, truthful=True, names_class=True, names_fix=True, user_messages=1, bank_intact=True | yes | 3/3 | pass |
| bank-compare | shell | 0.0 | bank_intact=True | yes | 1/1 | pass |

| bar | value | limit | verdict |
|---|---|---|---|
| user_messages_max | 2 | {"max": 2} | pass |
| truthful_within_heartbeat | 1.0 | {"min": 1.0} | pass |
| requests_name_no_value | None | {"min": 1.0} | FAIL |
| bank_intact | 1.0 | {"min": 1.0} | pass |

Step notes:
- evaluator-crash: the hold-out labels moved away before the first evaluation: the protected evaluator crashes on every invocation, the engine's own included
- killed-writer: the writer killed with SIGKILL during the implementation phase; the heartbeat stops at once; a reader sees DEAD as soon as the writer is gone
- full-disk: a 64 MB tmpfs holding the campaign directory, filled while the writer is implementing; the writer dies with ENOSPC in the launch's log (kept outside the full disk; no try/except); the truth lives in the log and the receipt
- tampering: the evaluator edited inside the running attempt's session clone; the integrity check voids the attempt with the hash evidence; this campaign is S4's (left running to its end, never stopped)
- bank-compare: the bank /home/ubuntu/out/bank-seed.git: {'head': '6ace9b7db82c1c1e407ca15ee14efd9a6b80e8ab', 'cards': 3, 'readable': True} before, {'head': '6ace9b7db82c1c1e407ca15ee14efd9a6b80e8ab', 'cards': 3, 'readable': True} after

The driver's own acts (named, never the persona's):
- evaluator-crash: the fixture's generate.py removed after the data was generated (a real repository has no generator for its hold-out)
- full-disk: the fixture's generate.py removed after the data was generated (a real repository has no generator for its hold-out)
- killed-writer: the fixture's generate.py removed after the data was generated (a real repository has no generator for its hold-out)
- tampering: the fixture's generate.py removed after the data was generated (a real repository has no generator for its hold-out)

Notes:
- the CLI's documented shape of a limit it cannot wait out: a rate_limit_event whose status is rejected, then an error result; a reconstruction, no captured limit being in the archives

Transcripts:
- transcripts/evaluator-crash-2-user.jsonl
- transcripts/evaluator-crash-user.jsonl
- transcripts/full-disk-2-user.jsonl
- transcripts/full-disk-user.jsonl
- transcripts/killed-writer-2-user.jsonl
- transcripts/killed-writer-user.jsonl
- transcripts/tampering-user.jsonl

Result: FAIL (3/5 steps; required steps missing: provider-limit, missing-key, killed-session; steps failed: killed-writer, full-disk; bars unmet: requests_name_no_value)
