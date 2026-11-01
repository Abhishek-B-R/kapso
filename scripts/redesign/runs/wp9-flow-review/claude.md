I've finished reading the plan, the suite, every driver, the rubrics and the engine contracts they depend on. Here are my findings.

---

# WP9 semantic suite — flow review (Claude half)

Reviewed against `docs/plans/redesign/wp9-semantic-suite.md`, `docs/plans/semantic-production-tests.md`, and the engine the drivers drive (`search_strategies/base.py`, `experiment_workspace/*`, `evaluation_integrity.py`, `trace.py`, `observability.py`, `inbox.py`, `core/config.py`). Ranked most severe first. Severity = "can this make the suite record something false, let a real regression pass, or burn a machine run without measuring anything".

---

## 1. The fresh-machine archive is fetched to one directory and verified in another — and the machine is deleted before the verify

**`scripts/redesign/semantic.sh:23-24,44,151-153` + `scripts/redesign/fresh_machine.sh:27,87-92`**

`semantic.sh` sets `RUNS="$HERE/runs/wp9"`, `RUN_DIR="$RUNS/$RUN_ID"`, and `judge_and_report` reads `$RUN_DIR/fetched/out/record.json`. But `fresh_machine.sh`'s `cmd_fetch` copies into `$HERE/runs/$id/fetched/` — `scripts/redesign/runs/<id>/fetched/out`, not `runs/wp9/<id>/fetched/out`. The record is never where the runner looks.

Worse, the order is `fetch` (151) → `delete` (152) → verify (inside `judge_and_report`, 100). The sub-plan and `scripts/redesign/README.md:63-67` both promise "archives, **verifies** the record is fetched, **then** deletes".

**Consequence:** every fresh-machine run ends `no record at …/fetched/out/record.json`, exit 1, with the machine already destroyed — no judging, no report, and a 4–6 hour run that cannot be re-read. The one irreversible step runs before the check that guards it.

**Smallest fix:** give `cmd_fetch` a destination argument (or `mv "$HERE/runs/$RUN_ID/fetched" "$RUN_DIR/fetched"` right after the fetch), and move the `record.json` existence check between `fetch` and `delete`, aborting before `delete` when it is absent.

---

## 2. The scaffold the runner ships to the machine omits `docs.json`, `.claude-plugin/` and `plugin/` — S1 and S2 die on their first step

**`scripts/redesign/semantic.sh:62-64`**

```bash
tar -C "$ROOT" -czf "$1" scripts/redesign tests/semantic tests/fixtures/semantic_transcripts examples docs
```

The drivers then read, from `--clone ~/kapso-clone`:

- `s1_cold_engineer.py:87` → `clone/docs.json` (**not packed**) → `FileNotFoundError` inside `step_sandbox`, S1's first step;
- `plugin_proof.py:472` → `claude plugin marketplace add <clone>` needs `.claude-plugin/marketplace.json` (**not packed**) → `ctx.shell(check=True)` raises in `step_install`, S2's first step;
- `plugin_proof.py:676` → `plugin_round.sh` needs `plugin/evals`; `:1151` → `plugin/scripts/kapso-mcp`.

**Consequence:** S1 and S2 cannot start on a fresh machine at all — the two arms the acceptance section leads with.

**Smallest fix:** add `docs.json .claude-plugin plugin` to `pack_harness`.

---

## 3. S5 launches every campaign with `--config kapso-config.yaml`, which the churn fixture does not have

**`scripts/redesign/s5_injections.py:186-189`**

```python
f"... --config kapso-config.yaml --detach", cwd=project,
```

`ctx.fixture("churn-first-build", …)` copies the example and runs `generate.py`; `examples/churn-first-build/` ships **no** `kapso-config.yaml` and nothing in S5 writes one (contrast `s6_experience.py:236`, which calls `project_config` first). `load_config` (`src/kapso/core/config.py:79-80`) raises `ConfigError: kapso-config.yaml: no such file`, the CLI exits non-zero, and `Context.shell` defaults to `check=True`.

**Consequence:** `step_provider_limit` — the first injection — raises before anything is injected. The whole S5 arm (six classes, ~4 machine hours, the campaign S4 then reads) never runs.

**Smallest fix:** drop `--config kapso-config.yaml` from `S5.launch`, or call `project_config(project, {})` in `S5.project()` so the file exists. (Note the known layering gotcha: passing *any* `--config` changes engine defaults, so dropping the flag is the truer run.)

---

## 4. S5's evaluator-crash moves a path that does not exist, and could not reach the engine's evaluation even if it did

**`scripts/redesign/s5_injections.py:280-282`**

```python
labels = campaign / "kapso_evaluation" / "private" / "holdout_labels.csv"
labels.rename(moved)
```

The churn fixture's labels live at `<project>/private/holdout_labels.csv`, outside the campaign, reached through the absolute path in `evaluation/private_dir.txt` (`examples/churn-first-build/generate.py:134-135`; the generator's own header says "nothing under `private/` is copied into a workspace"). `Context.fixture` even excludes `private` from the copy. `campaign/kapso_evaluation/private/` never exists → `Path.rename` raises `FileNotFoundError`.

The driver's docstring (`:16-19`) and the step note (`:295`) assert the opposite ("the engine seals and commits them there"). It also would not work as described: candidate evaluation and the integrity check run in a worktree materialised from the branch ref (`experiment_workspace.py:188-204`, `search_strategies/base.py:864-874`), so a working-tree deletion in the campaign root is invisible to them.

**Consequence:** the driver crashes mid-run (after the provider-limit campaign), so `missing-key`, `killed-session`, `killed-writer`, `full-disk`, `tampering` and `bank-compare` never execute — and the record keeps one step. The engine's behaviour under a crashing evaluator stays untested, which is the one thing WP6 left open.

**Smallest fix:** move `project / "private" / "holdout_labels.csv"` (the path `private_dir.txt` names). Because it is read through an absolute path outside git, that *does* break every invocation including the engine's own — exactly the injection the plan wants.

---

## 5. S5's tampering edits a tree no attempt commits — and its predicate accepts an ordinary rejection as the void

**`scripts/redesign/s5_injections.py:437-441,445,452`**

The driver appends a line to `campaign/kapso_evaluation/evaluate.py` (the campaign root's working tree). But an implementation session is a **git clone** of the campaign repo (`experiment_workspace/experiment_session.py:114-117`), checked out at the parent branch, so it carries the *committed* evaluator; the integrity check verifies the *materialised branch ref* (`base.py:864-874`). The only path by which a campaign-root edit reaches a session is `sync_registered_evaluation`, which runs only `if registered_evaluation_manifest` (`generic/implementation.py:177-178`) — i.e. with a maintainer-registered evaluation, and `evaluation_maintainer.enabled` is `false` in `src/kapso/config.yaml:383` with no fixture config turning it on.

Then the predicate:

```python
voided = trace.get("voided", [])
... workspace is not None and bool(voided) and diagnosis["names_class"]
```

`trace._voided` (`trace.py:418-437`) lists **every** attempt with `evaluation_valid == False` — a judge rejection ("judged not valid") as much as an integrity void.

**Consequence:** the step passes on a campaign where nothing was tampered-voided (any judge-rejected attempt plus the word "evaluator" in the host's answer suffices) and the record claims the integrity check fired. S4 then reads this campaign as "a void with its hash evidence"; its fact sheet reports a rejection as a void, and Q3 — the question S4 exists for — is graded against a false key.

**Smallest fix:** edit the evaluator inside the running attempt's session clone (`<campaign>/sessions/<branch>/kapso_evaluation/evaluate.py`, the path `experiment_workspace.py:427` mints) while the status shows `implementation`; and require the void to be the integrity one: `any(v["reason"].startswith("rejected:") and "evaluate.py" in v["reason"] for v in voided)`.

---

## 6. S1 can never pass: `comprehension_correct` has no producer, and the S1 judge has nothing to judge

**`scripts/redesign/s1_cold_engineer.py:397`, `tests/semantic/suite.json:25`, `scripts/redesign/judge.py:187-195`, `scripts/redesign/semantic.sh:102-112`**

`run_metrics` reads `comprehension_correct` back out of `record["metrics"]` and nothing ever writes it (there is no `--grade` path in S1, unlike `s4_reading.grade`). `bar_met(None, {"min": 1.0})` is `False`, so the S1 verdict is `FAIL` on every run, however good.

The judge cannot fill it either: with `--rubric s1` and no `--inputs` (the runner passes `--inputs` only for s4 and author), `judge_record` iterates for `kind == "conversation"` — S1 emits only `shell`, `build`, `attempt` and `reading` steps, so `materials` is empty and `aggregate` calls `min()` on an empty sequence → `ValueError` traceback, which `semantic.sh` swallows (no `set -e`). The record ends unjudged, and `tests/semantic/rubrics/s1.md:9` asks for a comprehension verdict that the JSON contract (exactly the rubric's three dimensions) forbids anyway.

**Consequence:** S1's headline acceptance ("the comprehension key correct on every verb") is never computed, and its verdict is a guaranteed FAIL that tells the reader nothing.

**Smallest fix:** give S1 an `--inputs artifacts/comprehension-answers.txt` judging path plus an `s1_cold_engineer.py --grade` that writes `metrics.comprehension_correct` from the judge block (mirroring `s4_reading.grade`), and add a `comprehension` dimension to `s1.md`'s dimension list so the contract permits it.

---

## 7. S1's execution counting only understands Claude Code's stream — the Codex arm records 0 of 12 for a perfect run

**`scripts/redesign/s1_cold_engineer.py:142-175`**

`executions()` matches `row["type"] == "assistant"` → `message.content[].tool_use` named `Bash`, and reads results from `row["type"] == "user"` → `tool_result`. A Codex transcript (`plugin_proof.CodexHost.turn:202-212`) is `item.completed` / `command_execution` rows. So for every Codex attempt `found == []`, hence `first_try=False`, `wrong_calls=0`, `executions=0`, `commands=[]`.

**Consequence:** `first_try_count` is always 0 for the Codex arm (bar: 9) while `errors_led_to_fix` passes vacuously at 1.0 and `cli_commands` passes at 0. The record states that the Codex engineer failed all twelve attempts on first try and used zero commands. That is a false record of a real arm, not a missing measurement. The same blindness makes `session_init`/`is_cold` return `None` on Codex, so `step_sandbox` passes without proving isolation there.

**Smallest fix:** add the Codex branch to `executions()` (command text from `item.command`, errored from the item's `exit_code`/`aggregated_output`), and treat `cold is None` as "not proved" in the sandbox note rather than a pass.

---

## 8. The persona arm runs all 25 steps on one card — so the harness interview has neither the module answers nor the patience the design gives it

**`scripts/redesign/plugin_proof.py:226-241,308-316,830-832`; `scripts/redesign/semantic.sh:51`**

`UserMode` loads a single card at construction and `converse` uses `self.user.card` for every step. The runner always passes `--user persona:ml-engineer`. The sub-plan's interface assigns `trading-author` the six module answers for `harness-new` ("the harness's module answers as the `trading-author` card's knowledge", named as an intervention) and `second-engineer` the served build; `tests/semantic/personas/trading-author.yaml` exists and holds exactly those answers with `patience: 8`. `ml-engineer.yaml` knows nothing about the trading repository and has `patience: 2`, after which the prompt tells it to "answer in one line and say that you have answered enough".

Also note `plugin_proof.py:831` appends the "module answers from the driver's policy" intervention **only** in scripted mode, so in persona mode the answers come from nowhere and the record does not say so.

**Consequence:** `harness-new` — the longest, most expensive conversation in S2 — is driven by a persona that cannot answer the interview and goes terse after two questions. The step fails on content the product never got a fair chance at, and `harness-probe`/`harness-improve` (which depend on `new_harness`) fail behind it.

**Smallest fix:** a per-step card map (`harness-new → trading-author`, the criteria steps → their card), falling back to the `--user` card; and move the intervention note out of the `scripted` branch.

---

## 9. In persona mode `harness-export` crashes the run: the persona reads a README that is not there

**`scripts/redesign/simulated_user.py:138` ← `scripts/redesign/plugin_proof.py:704`**

`next_message` does `readme = (task_dir / "README.md").read_text(...)` unconditionally. `step_harness_export` converses with `cwd = work/export-claude_code`, the directory `kapso harness export --to` wrote; `export_harness` (`src/kapso/harness/export.py:68-118`) writes `.claude/skills/…`, `.mcp.json`, `kapso-harness-<name>.md` and agents — never a `README.md`.

**Consequence:** `FileNotFoundError` at step 8 of 25 in the S2 persona arm, every time. `--from` can restart it, but the arm cannot complete unattended.

**Smallest fix:** in `step_harness_export`, converse from the project directory (or write the task view's README into the export directory and name it as an intervention).

---

## 10. S5's "handled" is a substring match, the fix is never gated, and the user-message bar is true by construction

**`scripts/redesign/s5_injections.py:96-113,139,229-231,471`; `tests/semantic/suite.json:35`**

`CLASS_WORDS` accepts: `limit` (provider-limit — matches "budget limit"), `evaluat` (evaluator-crash — matches any mention of "evaluation"), `key` (missing-key), `session` (killed-session), `evaluator` (tampering). `names_fix` is computed and stored but appears in **no** `completed` predicate and **no** bar. And `user_messages` is `len(turns)` where the driver always sends exactly the scripted one or two turns, so `user_messages_max ≤ 2` can never fail.

**Consequence:** S5's acceptance — "each of the six classes handled with at most two user messages", where handled means the skill names the class *and* the fix — is gated by a word that appears in almost any answer about a campaign, plus a bar that is a tautology. A skill that misdiagnoses every injection passes S5 as long as the engine's own artifacts are right.

**Smallest fix:** tighten each regex to the class's discriminating phrase (`rate.?limit|429`, `holdout_labels|hold-out labels`, `DATA_API_KEY`, `no space left|ENOSPC`, `integrity|hash`), add `names_fix` to each `completed`, and make the message bar meaningful — count turns until `resumed` is observed and let the driver keep asking up to the cap instead of stopping at two.

---

## 11. The timeline samples the status file, not `kapso watch --json` — so a `watch` that lies about liveness still passes

**`scripts/redesign/status_timeline.py:44-60`; `scripts/redesign/s5_injections.py:374,419`**

The sub-plan says the sampler "samples `kapso watch <campaign> --json`". It instead reads `.kapso/status.json` directly and re-implements liveness (`pid_alive = Path(f"/proc/{pid}").exists()`), duplicating `observability.pid_alive:104-110`. The product's verdict — `view.alive` folded with the three-missed-heartbeat rule into `DEAD` by `render_listing:186-187` — is never sampled, and `killed-writer`/`full-disk` assert recovery against `/proc` rather than against what the user reads.

**Consequence:** the S5 claim "`watch` reports DEAD within three heartbeats" is not measured. If `watch`'s liveness logic regressed to printing RUNNING for a dead writer, S5 would still be green — the exact regression a user would hit first.

**Smallest fix:** sample `kapso watch <campaign> --json` and store its `state`/`alive`/`heartbeat_age_seconds` beside the raw status row; compute `truthful_within` from the watch verdict.

---

## 12. S4's answer key is wrong for "what was rejected", and its hold-out leak check cannot see a leak

**`scripts/redesign/s4_reading.py:55-62,70-73`**

`rejected` is built as "every attempt with a score that is not the delivered branch" — that is the list of **losers**, not rejections. A rejected attempt has `evaluation_valid == False` and `score is None` (`base.py:893-896`), so it is excluded from `rejected` and appears under `voided`. The `reason` field is `attempt["judge"]` serialised, often `null`.

`labels_in_history` greps `git log --all -- kapso_evaluation/private`, a path this fixture never has: the labels live at `<project>/private/`, reachable only through the absolute path in `private_dir.txt`.

**Consequence:** `rubrics/s4.md`'s "what was rejected and why: 1 when the rejected candidates and their reasons match the fact sheet" grades the reader against a wrong key — a correct reader is marked wrong, and `readers_correct_min ≥ 6` becomes unreachable. And the "safe to merge" fact always says "the private directory is not in the branch's history" whatever the engine did, so a real hold-out leak into the delivered branch would be reported as safe.

**Smallest fix:** take `rejected` from `trace["voided"]` entries whose reason starts with `judged not valid`/`rejected:`, and report the losers separately as "scored but not delivered"; for the labels, search the delivered tree for the label file by name and by the `MANIFEST.json` sha256 (`git log --all -- '*holdout_labels.csv'` plus a content grep), not one hard-coded directory.

---

## 13. The persona's satisfaction, the turn cap and the pushback result never reach the report or the verdict

**`tests/semantic/report.py:122-216`; `scripts/redesign/plugin_proof.py:244,320-323,560-573`**

`UserMode.record()` carries `events` (every `DONE` and every turn-cap end) and `pushback`; `render()` prints `interventions` and nothing else from `user`. No verdict clause implements the design's rule that "a persona that does not push back makes the arm advisory for the `not annoying` and `engaging` dimensions, said in the record".

`pushed_back` is also host-blind: it only inspects `row.get("type") == "result"` — a Claude Code row. On the Codex host no such row exists, so `stated` is always `False` and the record always says "the planted baseline: never stated by the host".

**Consequence:** a run where the persona nodded through everything — the design's named risk — is reported as a clean PASS at 4+ on `not annoying` and `engaging`, with the evidence that would have qualified it invisible. The Codex arm's pushback check silently never fires.

**Smallest fix:** render `user.events` and `user.pushback` in the report, derive the advisory marking from `pushback is False` in `verdict()`, and read the host's text from the host's own final-text extraction (the same logic `judge.final_texts` already has for both vendors).

---

## 14. The author test's two rounds run against the same guide, `guide-fixes` fixes nothing and always passes, and the classifier's prompt ships invalid JSON

**`scripts/redesign/author_test.py:58-72,188-203,206-220`; `scripts/redesign/semantic.sh:104-112`**

Three separate problems in the same chain:

1. `main` with no `--round` runs `round-1`, `guide-fixes`, `round-2` in one process, while the classification that identifies the gaps runs later, on the dev box, via `--grade`. So `step_guide_fixes` reads `round_one["classification"]` — absent — and records "0 structural gaps and contradictions fed into the guide", `completed=True` unconditionally, having edited nothing. Round two then re-samples the *unchanged* guide.
2. `CLASSIFY` is applied with `.replace`, not `.format`, so its `{{` escapes survive: the prompt instructs the model to reply with `{{"classifications": [{{"index": …}}]}}`. A compliant reply is not JSON and `extract_json` raises.
3. `grade()` builds the guide text from the current checkout, so once the pages are fixed, round-1's genuine structural gaps classify as `already_in_guide`.

**Consequence:** `structural_gaps_round2` — the test's only bar — measures run-to-run variance of one guide, not whether the guide was repaired; `guide-fixes` is a step that cannot fail; and grading may not run at all. The headline number ("zero structural gaps in round two") is uninterpretable.

**Smallest fix:** single the braces in `CLASSIFY` (or `.format` it); make `guide-fixes` require a non-empty round-1 classification and a non-empty `git diff --stat` of the guide pages; and run round two as its own invocation after the pages are edited (the runner already supports `--round`).

---

## 15. The judge: a top score with no evidence validates, steps with no transcript are silently dropped, half of some conversations is never rendered, and min-over-items is wrong for the author test

**`scripts/redesign/judge.py:120-122,159-166,187-195`**

- `validate` requires `evidence` to be a *list* but accepts `[]`. A reply of `{"scores": {"proactive": {"score": 5, "evidence": []}, …}}` passes every check. The quote-at-location rule — the whole defence against a lenient judge — is opt-out.
- `if not transcript.is_file(): continue` drops a conversation step from the judged set with no record, and the run's dimension score is then the minimum over a smaller set. If none exist, `aggregate` crashes on an empty `min()`.
- Only `transcripts/<step>.jsonl` is rendered, so `review-2`, `deploy-2`, `watch-2` and `inbox-reply` — where the user asks "is it safe to merge?" and "call it once" — are never judged. The judge grades half of those exchanges.
- `aggregate`'s minimum-over-items is right for S2 steps and S4 readers, but `semantic.sh:106` feeds it `round-1-harness.md` **and** `round-2-harness.md`: round one's harness (expected to be the weaker one) binds the author rubric's four dimensions.

**Consequence:** a lenient judge passes a bad S2 run by omitting evidence; a missing transcript quietly shrinks the judged surface; the follow-up turns go ungraded; and a good author round two is sunk by round one.

**Smallest fix:** require `len(evidence) >= 1` per dimension; raise a `JudgeFailure` naming the step when a required conversation step has no transcript; render every `transcripts/*.jsonl` whose name starts with the step name; judge the author rounds as separate records (or bar round two's scores explicitly).

---

## 16. Two rubrics ask for output the judge's contract rejects, and `s2.md` contradicts the suite's own message budgets

**`tests/semantic/rubrics/s1.md:9`, `tests/semantic/rubrics/author.md:10`, `tests/semantic/rubrics/s2.md:7`; `scripts/redesign/judge.py:34-38,113-114`**

`s1.md` closes with "Then the comprehension key: … list the verbs answered wrongly"; `author.md` closes with "Then classify every line of the guess log … Return the counts". The contract says "exactly one JSON object … one entry per dimension, every dimension of the rubric, **no other**", and `validate` raises on any extra key. A judge that obeys the rubric produces a recorded **judge failure**, which `report.py:168-169` turns into FAIL.

Separately, `s2.md`'s `not annoying` says "no message over twelve lines plus the brief", while `suite.json` budgets `setup` at 40 lines, `harness-new` at 60 and `deploy` at 30. The judge and the budget disagree about the same property, and the judge's verdict is the binding one.

**Consequence:** a compliant judge sinks a good run (and a non-compliant one is the only one that passes); and `not annoying` penalises messages the suite's own budgets bless.

**Smallest fix:** delete the trailing paragraphs from `s1.md`/`author.md` (the classification already has its own prompt in `author_test.CLASSIFY`; the comprehension key needs its own dimension — see #6), and make `s2.md`'s line cap read "over the step's `longest_message_lines` budget".

---

## 17. The "question asked" detector counts a polite closing line, and `watch` requires zero questions

**`scripts/redesign/plugin_proof.py:46-50,115-124,614`**

`APPROVAL_ASKED` includes `\blet me know\b` and `\byour answers?\b`, matched against the last eight non-empty lines. `step_watch` requires `all(not turn.asked for turn in turns)` and `suite.json` budgets `watch` at `questions: 0`.

**Consequence:** a correct watch answer ending "Let me know if you want the full trace" is counted as a question, fails the step's predicate *and* its budget, and fails the S2 run — a bar failing while the experience is exactly right. The same regex inflates `questions` (the only hard "not annoying" metric) across every step.

**Smallest fix:** require the approval phrases to be in the final non-empty line and anchor them to a request (`\b(let me know|say go|shall i|want me to)\b[^.]*\?|^(go|yes)\b`), or drop `let me know`/`your answers` and rely on `AskUserQuestion` plus a trailing `?`.

---

## 18. Several "completed" predicates are not evidence the user got what they needed

**`scripts/redesign/plugin_proof.py:614,800,896,974,1021-1028`**

- **`review:896`** — `finished and solution.is_file()`. Both are facts about the campaign, true whether or not the host said anything useful. A host that answers "I can't read that campaign" passes `review`.
- **`watch:614`** — any of `running|setup|ideation|implementation|phase|best` appearing in the text, never compared with `status.json`. A host that reports a dead campaign as running passes.
- **`_criteria_step:800`** — "did not launch" is `any(path.name == "status.json" … if name in str(path))`, i.e. the campaign path must contain the literal string `build-data-only` / `build-empty-wish`. A host launching into `../fraud-data-campaign` — what the skill would actually propose — is invisible, so the step passes **even when the host launched against an explicit "do not launch anything"**. That is the one behaviour these two steps exist to catch.
- **`session-brief:974`** — `any("bank" in name for name in names)`: any tool whose *name* contains "bank", even if the call errored.
- **`second-engineer-build:1021`** — `state in ("done","failed")` counts a failed build as done, and `served` is the substring `bank-remote` in `solution.json`.

**Smallest fix:** for `review`, require the answer to name the delivered branch and a merge verdict; for `watch`, compare the answer's phase/best with the status read at that moment; for the criteria steps, snapshot the set of `**/.kapso/status.json` under `ctx.work` before the step and fail on any new one; for `session-brief`, require a successful bank-tool result and a title that occurs in the bank.

---

## 19. S1's `error_led_to_fix` passes for any eventual recovery, `wrong_calls` is ungated, and task 5's evidence is looked for in the wrong directory

**`scripts/redesign/s1_cold_engineer.py:178-194,234`; `tests/semantic/suite.json:25`**

`led_to_fix` is `first_success is not None and found[first_success-1]["errored"] is True` — but every entry before `first_success` errored by construction, so it is `True` whenever there was any error and any later success. Three wrong calls then a success scores the same as one. The design's bar is "every error leads to its fix **in one step**", and `wrong_calls` — the metric that would say so — appears in no bar (`suite.json:25`), despite the sub-plan's interface listing `wrong_calls_max`.

`evidence_of`'s `learn-status` branch globs `sandbox/task/learning/status/*.json` and `prereq.parent/"task"/learning/status` — the same path twice. `learning.status_dir` is the relative `learning/status` (`src/kapso/config.yaml:427`), resolved from the invocation's cwd; the engineer runs from the sandbox, so the file lands in `sandbox/learning/status/`.

**Consequence:** the one-step recovery claim is not measured, and task 5 is recorded as a failure on both surfaces for a learn that launched correctly (two of twelve attempts lost, `minutes_to_launch` null).

**Smallest fix:** `led_to_fix = (wrong == 1)`, add `wrong_calls_max: {"max": 1}` to S1's bars, and glob `sandbox/**/learning/status/*.json`.

---

## 20. S6's gate is the coin-flip number, not the claim the design says it supports; and the enrichment service serves ids the fixture does not use

**`tests/semantic/suite.json:40`; `scripts/redesign/s6_experience.py:52,97-99`; `scripts/redesign/enrichment_service.py:21,62`**

S6's bars are `gap_min ≥ 0.0`, `lessons_cited ≥ 1`, `scored_observations_min ≥ 1`, all hard. The sub-plan's own risk section says the gap at this budget "is dominated by whether an attempt landed… the claim it supports is that the served cards were read and cited", and the acceptance allows "the pair reported as the design's bar unmet with the numbers". `report.py` has no such mode: a negative gap is `FAIL`, with `SPREAD` ("0.845, 0.847, 0.851 and nothing twice") recorded right beside it as proof that the sign is noise.

Separately, `enrichment_service.ROWS = 3000` serves `C000001…C003000`, while the fixture's training ids are `C000001…C010000` and the hold-out's are `C010001…C013000` (`generate.py:30-31,89,129-130`). The table the "missing-key" injection hands back covers 30% of train and **none** of the rows the evaluator scores — the comment at `:21` says it serves both ranges.

**Consequence:** S6's verdict is a coin flip on a quantity the design calls a sample; and the missing-key recovery is recorded as successful ("the authorised fetch of the resumed attempt") while the fetched table cannot be joined to the hold-out, so `scored_after_resume` means nothing.

**Smallest fix:** move `gap_min` out of S6's `bars` into reported metrics (keep `lessons_cited` and `scored_observations_min` as the gate), and derive the served id range from the fixture's `MANIFEST.json` row counts instead of the literal 3000.

---

## 21. Rule-level defects worth fixing together

- **A quota-refused persona becomes a satisfied user.** `simulated_user.next_message:144-149` raises only on a non-zero exit, a timeout or empty text. `claude -p --output-format json` returns a `result` payload with `is_error: true` (a limit, `error_max_turns`) that this code hands back as the persona's message, which then becomes the host's next user turn. The design says explicitly "a quota-refused persona is never a satisfied user". **Fix:** raise when `is_error` is true or `subtype != "success"`, and when the Codex stream carries no `agent_message`.
- **Config-like literals outside `suite.json`** (Rule 1), where `suite.json` is declared "the one home of the suite's knobs and bars": the host models `CLAUDE_MODEL`/`CODEX_MODEL` and `TURN_TIMEOUT` (`plugin_proof.py:42-44`) — so the record's pins cannot say which host model produced the measured experience; `TRIGGER_BAR = 0.9` (`:619`), literally a bar; the budgets baked into `CHURN_WISH`/`FRAUD_WISH`/`--pause-minutes` (`:51-64,1183`) while `suite.json` has a `builds` block; `enrichment_service.ROWS` (#20).
- **`semantic.sh` fails soft everywhere.** No `set -e` (`:17`): a failed `create`/`install`/`run` marches on to `fetch` and `delete`. The preflight (`:66-79`) prints and gates nothing — a dead Vertex route or a missing host login still provisions a machine and spends the hours; the persona's vendor route is never probed, though the README promises "every role's route".
- **The runner's exit status does not carry the verdict**, contrary to the acceptance and `README.md:72`: `:115-116` runs `report.py` and then `echo`, so the script exits 0; the advisory branch ends `exit 0` outright. **Fix:** `python3 report.py …; status=$?; …; exit $status`.
- **`suite_get "['machine']['max_run']['AUTHOR']"`** (`:41-42,142`) — `suite.json` has `"author"` lowercase, so the author run raises a `KeyError`, `KAPSO_FRESH_MAX_RUN` goes empty and the machine silently gets the 4h default instead of 3h.
- **The advisory arm cannot authenticate.** `:129-132` creates a fresh Linux user and runs the driver under `sudo -u … -H bash -lc`, which carries neither a stored `~/.claude` login nor `CLAUDE_CODE_OAUTH_TOKEN` (and `plugin_proof.seed_env` reads that variable from the environment it does not have). Since every Codex-dependent arm is supposed to run this way "until the credit exists", the only currently-runnable path cannot start a host session. **Fix:** write `~/.secrets/env` for that user as `fresh_machine.sh:48-51` does and source it in the `bash -lc` line.
- **`judge.py:199-212` vs `report.py:73`**: `suite.json`'s `judge.passes` is read by the judge but hard-coded as `len(passes) == 2` in the verdict and `2 - len(...)` in the render; raising `passes` to 3 would fail every run.
- **The S4 runner line has no campaign.** `semantic.sh:55` runs `s4_reading.py --campaign ~/tampering-campaign` on a machine it just created; nothing transfers S5's tampering campaign there (the plan says S4 runs "on S5's machine"). The `fact-sheet` step records `kapso trace failed` and the run cannot pass.
- **PyYAML is unpinned and incidental.** The drivers `import yaml` and run under `~/fixtures-venv/bin/python3` (`:91-96,150`); no example's `requirements.txt` names PyYAML — it arrives only as a transitive dependency of `dbt-core`. Add it to the venv command explicitly.

---

## Two notes that are not findings but bear on how the numbers should be read

- **The step openings are the driver's, not the persona's.** In persona mode the first user message of every conversation step is still `ctx.host.command("build", wish)` with a hand-written wish (`plugin_proof.py:533`), and `inbox-reply`, `watch-2`, `review-2`, `deploy-2` and `campaign-tools` are fully scripted sentences (`:715-718,742-747`) with their intent falling back to the bare step name (`:308`). The record says `user.kind: persona` and names only the out-of-band *acts* as interventions. Listing the scripted openings in `user.interventions` would keep the record honest about which words were the persona's.
- **`harness-new`'s budget is unreachable under the global turn cap.** `suite.json` gives it `messages: 14, questions: 8`; `converse` caps persona exchanges at `min(max_turns, turn_cap=8)` (`:309`). A legitimate ten-turn interview inside its declared budget is cut short and recorded as a turn-cap incomplete. Either cap per step from the step's `messages` budget, or lower the budget to the cap so the two agree.
