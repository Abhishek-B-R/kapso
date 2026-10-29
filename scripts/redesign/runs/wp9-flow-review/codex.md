1. **[P1] The runner returns success for failed and advisory verdicts.** [semantic.sh:115](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/semantic.sh:115)  
   `report.py`’s exit status is replaced by the succeeding `echo`; the advisory branch additionally executes `exit 0`. A failed UX gate or advisory-only result therefore looks successful to release automation. **Smallest fix:** capture and return the report’s status, preserving 0, 1 and 3 through both branches.

2. **[P1] The runner deletes the machine before verifying an archive, and looks for the archive in the wrong directory.** [semantic.sh:151](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/semantic.sh:151)  
   `fresh_machine.sh fetch` writes to `runs/<id>/fetched`, whereas `judge_and_report` reads `runs/wp9/<id>/fetched`. Deletion happens unconditionally before that check, even when fetching fails. Normal runs cannot be reported at the expected location; failed transfers can destroy the only evidence. **Smallest fix:** share one archive destination, check fetch success and archive contents, then delete.

3. **[P1] Wheel-building logs become part of the wheel filename.** [semantic.sh:82](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/semantic.sh:82)  
   `WHEEL="$(build_wheel)"` captures the banner and all `tee` output, followed by the path. The installer consequently receives a multiline string that is not a file. **Smallest fix:** send diagnostics to stderr and return only the wheel path; abort provisioning if building fails.

4. **[P1] The fresh-machine scaffold omits files its drivers require.** [semantic.sh:63](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/semantic.sh:63)  
   The archive excludes `plugin/`, `.claude-plugin/`, `.agents/` and `docs.json`. S2 installs the unpacked directory as its marketplace, and S1 reads its `docs.json`; both fail before exercising the intended experience. S5 also invokes plugin commands without installing the plugin. **Smallest fix:** package the required manifests, plugin and navigation file, and provision the plugin for drivers that use it.

5. **[P1] The runner never supplies the wheel to drivers that require it.** [semantic.sh:50](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/semantic.sh:50)  
   S1 rejects its default branch invocation without `--wheel`. S2 reaches `step_cold_install` with `ctx.wheel=None` and calls `wheel.resolve()`. Installing the product globally does not satisfy either requirement. **Smallest fix:** pass the installed remote wheel’s absolute path to both drivers.

6. **[P1] S1 has no functioning judge/comprehension grading path.** [judge.py:187](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/judge.py:187)  
   The default judge selects only conversation steps, but S1 produces shell, build, attempt and reading steps. The runner supplies no S1 inputs, so aggregation receives no items. Separately, `comprehension_correct` is only read, never calculated. Even a perfect run cannot pass. **Smallest fix:** render S1’s executions, comprehension answers and facts explicitly, then grade and populate the comprehension metric.

7. **[P1] S1 cannot recognize any Codex execution.** [s1_cold_engineer.py:151](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/s1_cold_engineer.py:151)  
   `executions()` handles Claude’s `assistant/tool_use` and `user/tool_result` events exclusively. Codex emits `item.completed/command_execution`. Successful Codex runs therefore receive zero first-try successes and zero counted commands. **Smallest fix:** normalize both transcript formats into executions with their actual exit status before calculating metrics.

8. **[P1] Every normal S5 launch names a nonexistent config file.** [s5_injections.py:187](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/s5_injections.py:187)  
   The copied churn fixture contains no `kapso-config.yaml`, and S5 never creates one. The engine explicitly rejects a missing override file, so the injection suite fails at launch rather than testing failure recovery. **Smallest fix:** omit `--config` when using packaged defaults, or create and archive the intended override.

9. **[P1] S6 writes its isolated bank under a rejected config key.** [s6_experience.py:236](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/s6_experience.py:236)  
   Both builds write `experience.bank.local_path`; the engine’s actual key is `learning.bank.local_path`. Unknown nested keys are rejected by `load_config`, so build one cannot start. **Smallest fix:** use the canonical learning-bank key for both configurations.

10. **[P1] The tampering injection edits the campaign root, not the candidate being verified.** [s5_injections.py:437](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/s5_injections.py:437)  
    Implementation runs in `campaign/sessions/<branch>`, cloned from committed history. Integrity verification materializes that candidate’s branch. Appending to the campaign root’s evaluator does not change either clone or candidate commit; an unrelated invalid attempt could nevertheless satisfy `bool(voided)`. **Smallest fix:** modify the active session’s evaluator and require the resulting candidate’s integrity error to identify that file.

11. **[P1] The evaluator-crash injection renames a label file the fixture does not create.** [s5_injections.py:280](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/s5_injections.py:280)  
    Churn’s evaluator reads the external directory recorded in `evaluation/private_dir.txt`; the engine copies that evaluator tree without creating `kapso_evaluation/private/holdout_labels.csv`. The rename raises instead of injecting a crash. Moving a genuinely protected file would also risk testing integrity rejection instead. **Smallest fix:** inject through the evaluator’s actual external dependency, and verify the target attempt records an evaluator execution failure.

12. **[P1] Deployment parity passes even when predictions differ.** [plugin_proof.py:910](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/plugin_proof.py:910)  
    `deploy_parity()` returns `"differs (deployed …, delivered …)"`, but completion rejects only the exact string `"differs"`. It also accepts every `"not established: …"` result. Thus an incorrect or unproved deployment passes. **Smallest fix:** require `parity == "same"` and a successful deployment record.

13. **[P1] S5’s truthfulness bar measures liveness, not truthful user-visible state.** [s5_injections.py:129](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/s5_injections.py:129)  
    A live process with a fresh heartbeat passes regardless of its reported phase or failure class; a dead process passes without checking what `watch` displays. Missing observation windows are excluded from the aggregate. A broken watcher or an indefinitely mislabelled pause can therefore pass. **Smallest fix:** compare sampled user-visible status against injection-specific expectations, timestamp the actual fault, and fail missing observations.

14. **[P1] The author test records guide fixes that never happened.** [author_test.py:188](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/author_test.py:188)  
    The default sequence runs both author rounds before classification. `guide-fixes` consequently sees no classifications, reads an optional diff, changes nothing and unconditionally passes. Later grading uses the current development checkout’s guide for both rounds. **Smallest fix:** classify round one first, apply and verify its required guide changes, snapshot that guide, then run and grade round two against its own snapshot.

15. **[P1] Adjudicating one worst item can erase other failing items.** [judge.py:215](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/judge.py:215)  
    If pass one scores steps A=2 and B=3, and pass two scores both 5, only A is adjudicated. Giving A a 4 makes the entire dimension pass although B’s 3/5 disagreement remains unresolved. This breaks the promised minimum over steps. **Smallest fix:** adjudicate each straddling item/dimension, then aggregate the resolved item scores.

16. **[P2] The advisory path provisions neither the product nor usable host authentication.** [semantic.sh:129](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/semantic.sh:129)  
    A new Linux user receives only the scaffold. The wheel, fixture dependencies and host login are not installed or made available; the caller’s per-user CLI authentication does not follow `sudo -u`. This cannot provide the documented workaround for exhausted fresh-machine Codex credit. **Smallest fix:** explicitly provision the advisory user’s package, dependencies and authorized authentication route before running.

17. **[P2] S4’s default campaign is never staged.** [semantic.sh:55](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/semantic.sh:55)  
    The runner points S4 at `~/tampering-campaign`, but never transfers an S5 campaign there. `--machine` still goes through machine creation rather than reusing and staging the earlier run. **Smallest fix:** require an archived S5 campaign input, transfer and verify it, then pass its real path to S4.

18. **[P2] Preflight does not establish the routes or credit the run needs.** [semantic.sh:68](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/semantic.sh:68)  
    Host checks are `--version`, and the Codex probe only lists models—the plan explicitly records that this succeeds with exhausted credit. Persona and grader routes are not exercised, and preflight errors do not stop the outer script. **Smallest fix:** make a small generation request through each required credential route, validate it, and stop before provisioning on failure.

19. **[P2] Fixture dependencies are not installed in every interpreter the drivers use.** [semantic.sh:91](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/semantic.sh:91)  
    The fixtures-only venv runs the drivers but lacks their full dependencies: `author_test.py` imports `judge.py`, which imports LiteLLM. Conversely, S1 prepends a separate Kapso venv without fixture requirements, and `proof2` never receives the fixture venv. Working flows can fail on missing imports rather than product behavior. **Smallest fix:** install the required wheel and fixture dependencies into each interpreter actually used, and verify imports there.

20. **[P2] The judge accepts passing scores without evidence.** [judge.py:120](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/judge.py:120)  
    An empty evidence list passes validation; an empty quote matches every line. Citation paths are also unrestricted, permitting files outside the supplied material or record directory. A lenient or adversarial reply can satisfy the contract without supporting its verdict. **Smallest fix:** require nonempty evidence and quotes, and validate citations against an allowlist of the exact rendered material supplied to that call.

21. **[P2] Malformed JSON bypasses the recorded judge-failure path.** [judge.py:103](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/judge.py:103)  
    Invalid JSON raises `JSONDecodeError`, while the caller catches only `JudgeFailure`. The raw reply remains, but the promised failure block is not written; a prior judge block can remain untouched. The narrow `try/except` also violates the repository’s explicit error-handling contract. **Smallest fix:** persist a nonpassing pending state before decoding, replace it only after complete validation, and propagate/report validation failure explicitly.

22. **[P2] S2’s judge omits consequential follow-up exchanges and artifacts.** [judge.py:190](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/judge.py:190)  
    A step is judged from only `<step>.jsonl`. Actual follow-ups live in `review-2.jsonl`, `deploy-2.jsonl`, `watch-2.jsonl` and `inbox-reply.jsonl`; none are included. The judge also receives no corresponding verification artifacts. An unsafe merge recommendation or failed proof call can be invisible. **Smallest fix:** record each step’s complete transcript list and render it with the relevant artifact evidence.

23. **[P2] Reaching the persona turn cap does not make a step incomplete.** [plugin_proof.py:323](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/plugin_proof.py:323)  
    Exhaustion merely appends a string to `user.events` and returns ordinary turns. Step completion predicates and the report never inspect it. A user still asking for help can therefore pass once an artifact exists. **Smallest fix:** return a structured termination reason and make cap exhaustion fail completion unless an explicit completion predicate was already satisfied.

24. **[P2] The persona crashes on the harness-export step’s missing README.** [simulated_user.py:138](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/simulated_user.py:138)  
    `next_message()` unconditionally reads `cwd/README.md`. `step_harness_export` converses in a newly created export directory, and the exporter writes no README there. A successful export thus crashes S2 before persona feedback is recorded. **Smallest fix:** supply a separate task-view path or explicitly create that step’s task view.

25. **[P2] The trading interview uses the churn persona.** [plugin_proof.py:832](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/plugin_proof.py:832)  
    The run-wide `ml-engineer` card is never replaced with `trading-author`; persona mode ignores `harness_policy`, so its module answers are unavailable too. The interview tests an uninformed churn engineer instead of the specified domain author, distorting both harness completeness and annoyance scores. **Smallest fix:** select and record the trading-author card for this step.

26. **[P2] Failed pushback never weakens acceptance, and Codex pushback is not detected.** [plugin_proof.py:569](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/plugin_proof.py:569)  
    Detection recognizes only Claude `result` events. Even when it returns `False`, the caller adds a note without applying the promised advisory restriction. A compliant persona that accepts the planted false baseline can still establish the engagement bars. **Smallest fix:** inspect normalized final messages from both hosts and enforce the specified advisory outcome when correction is absent.

27. **[P2] The second engineer’s experience is scripted and its success predicate does not prove use.** [plugin_proof.py:1013](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/plugin_proof.py:1013)  
    The driver launches the build directly instead of using the second-engineer persona and host. Completion accepts `done` or `failed` plus the substring `bank-remote` in `solution.json`, without a scored result or card-read evidence. Moreover, Codex defers the only step that creates `proof2`. **Smallest fix:** provision the teammate independently for both arms, drive their host conversation, and require a scored build and reads from the shared bank.

28. **[P2] S2’s inbox “recovery” removes the requirement that caused the pause.** [plugin_proof.py:744](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/plugin_proof.py:744)  
    The driver tells the host to proceed without enrichment, accepts a reply/note event, then immediately stops the campaign. This proves neither the requested resource was supplied nor the suspended work continued. **Smallest fix:** use the real enrichment fixture, retain the requirement, and require the matching `continued` event and a successful resumed attempt.

29. **[P2] Launch completion accepts failed campaigns and preexisting briefs.** [plugin_proof.py:535](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/plugin_proof.py:535)  
    `_launch_and_wait_status` treats any status file as a successful launch and only checks that a brief exists, although the fixture already contains one. S1’s build evidence uses the same status-existence shortcut. A detached child that immediately fails can earn first-try/build completion. **Smallest fix:** require a live running launch or valid returned solution, and verify the proposal/brief changes and approval actually required by the step.

30. **[P2] S1’s one-step-fix metric accepts arbitrarily many failed attempts.** [s1_cold_engineer.py:185](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/s1_cold_engineer.py:185)  
    It checks only whether the execution immediately preceding the first success failed. `[failure, failure, success]` therefore records `error_led_to_fix=True`, despite the first error not leading to its fix in one step. **Smallest fix:** evaluate every failed execution against its immediate successor and require all such transitions to succeed.

31. **[P2] S1 reconstructs executions and flow length from scripts’ final contents.** [s1_cold_engineer.py:160](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/s1_cold_engineer.py:160)  
    A script edited after a failed call is read in its final form for all executions. Flow counting later deduplicates filenames and reads them again, so reusing one filename across six tasks counts only the last script. Both first-try attribution and the twelve-line bar can be false. **Smallest fix:** capture the executed source at each invocation and count the actual successful flow’s statements.

32. **[P2] S1 shares already-mutated prerequisites between Python and CLI attempts.** [s1_cold_engineer.py:340](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/s1_cold_engineer.py:340)  
    Only build output directories are reset. Deployment, learning and the killed campaign remain after the Python attempt, so CLI evidence can come from the previous surface; the CLI resume no longer starts from the original killed state. **Smallest fix:** restore independent prerequisite snapshots and clean task workspaces for each surface, and associate evidence with that invocation.

33. **[P2] S1 looks for learning status in the wrong working directory.** [s1_cold_engineer.py:233](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/s1_cold_engineer.py:233)  
    The host runs from the sandbox, where the default `learning/status` resolves. The predicate checks `sandbox/task/learning/status` instead. A correct `kapso learn campaign-prereq --detach` can therefore fail its task. **Smallest fix:** resolve the effective status directory relative to the actual launch cwd and require a newly created status.

34. **[P2] S4’s answer key confuses valid runners-up with rejected candidates.** [s4_reading.py:70](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/s4_reading.py:70)  
    Every scored nonwinner is labelled rejected, while invalid candidates with cleared scores are omitted. This contradicts the engine’s rejection semantics and can penalize a correct reader while rewarding an incorrect explanation. **Smallest fix:** derive rejections from validity/verdict fields and their recorded reasons; keep valid nonwinning attempts separate.

35. **[P2] S4 checks every branch’s history when claiming facts about the delivered branch.** [s4_reading.py:61](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/s4_reading.py:61)  
    `git log --all` can find labels on an abandoned branch and declare that merging the delivered branch carries them. It also assumes one hardcoded label location. **Smallest fix:** inspect the delivered commit’s ancestry and the fixture’s actual protected/private paths.

36. **[P2] S4 ignores successful adjudication when calculating its hard bar.** [s4_reading.py:163](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/s4_reading.py:163)  
    `grade()` always takes the minimum of the first two passes. A question scored 0/1 and adjudicated correct still reduces `readers_correct_min` below six, making the run fail despite the resolved judge outcome. **Smallest fix:** calculate per-reader correctness from the same resolved item scores used by the final verdict.

37. **[P2] S5 does not prove that the resumed attempt used enrichment and scored.** [s5_injections.py:323](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/s5_injections.py:323)  
    Any authorized request satisfies `authorised_fetch_after_reply`; service entries have no timestamps or caller attribution. The host can make that request itself. `scored_after_resume` is computed from any attempt and is not required for completion. **Smallest fix:** correlate the fetch and score with the continued attempt after its reply, and require both.

38. **[P2] S5 records recovery checks without enforcing them.** [s5_injections.py:385](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/s5_injections.py:385)  
    The driver accepts a running process and an attempt count at least as large as before; it does not verify retained attempt identities or new progress. `names_fix` and the full-disk `enospc_in_log` metric are likewise not gates. Restarting from scratch, supplying no actionable fix, or recovering from a different fault can pass within the scripted two-message count. **Smallest fix:** require the actual fault, diagnosis/fix and checkpoint-preserving progress.

39. **[P2] Bare banks are treated as unreadable-but-intact.** [s5_injections.py:151](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/s5_injections.py:151)  
    `bank_state()` expects a `.git` child, but Kapso’s own bank is bare. It returns `{head: None, cards: None}` before and after, and equality satisfies preservation even if bank contents changed or disappeared. **Smallest fix:** validate the repository with Git, read its HEAD and tree, require at least one card, and fail unreadable comparisons.

40. **[P2] The full-disk campaign is discarded before archival.** [s5_injections.py:426](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/s5_injections.py:426)  
    Unmounting the tmpfs removes the campaign, checkpoint, sessions and Git history from the directory later fetched by the runner. The retained status/trace summaries cannot prove checkpoint preservation. **Smallest fix:** copy and verify the complete campaign onto persistent storage before unmounting.

41. **[P2] S6’s gap excludes exactly the intervals where experience can make the user wait longer.** [s6_experience.py:93](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/s6_experience.py:93)  
    When build one has a score and build two has none, the gap is `None` and omitted from the minimum. A second build that delivers nothing until it finally catches up passes with gap zero. Differing timeline end times also discard comparisons. **Smallest fix:** use a common budget horizon, carry completed incumbents forward, and explicitly fail or mark unestablished intervals where only build one has a result.

42. **[P2] S6 manufactures the review and counts reading as lesson use.** [s6_experience.py:118](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/s6_experience.py:118)  
    Any nonempty `read_by` satisfies `lessons_cited`, even with no load-bearing card. The “review” is then formatted by the driver, without invoking `kapso-review`. The suite passes when the product never explains a useful lesson to the user. **Smallest fix:** require evidence of actual attempt use and have the real host review the run and cite those lesson identities.

43. **[P2] S6 always records delivered scores from a nonexistent trace field.** [s6_experience.py:156](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/s6_experience.py:156)  
    The real `delivered` object contains branch, commit and evidence, but no `score`. Successful runs consequently record delivered scores as null; the unit fixture uses an invented shape that hides this. **Smallest fix:** resolve the delivered branch to its attempt and read `evaluation.score`.

44. **[P2] A completely documented authoring experience fails because it produces no guesses.** [author_test.py:183](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/author_test.py:183)  
    Completion requires `bool(guesses)`. An author who legitimately needs zero guesses cannot pass round two, even with a valid harness and zero structural gaps. **Smallest fix:** require an explicit completed guess log, allowing it to state that there were no guesses.

45. **[P2] The evaluator contract accepts unusable result values and never tests rejection behavior.** [plugin_proof.py:783](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/plugin_proof.py:783)  
    It runs one submission and checks only a loose metric-line regex and JSON key presence. A constant scorer, nonnumeric JSON score or evaluator that accepts malformed predictions can pass. **Smallest fix:** reuse the fixture contract checks, including valid finite values, output consistency and at least one malformed-submission rejection.

46. **[P2] Host models and deadlines bypass the suite’s declared knobs.** [plugin_proof.py:42](/home/ubuntu/kapso/.claude/worktrees/kapso-plugin/scripts/redesign/plugin_proof.py:42)  
    Shared hosts hardcode models and a 1,800-second timeout; S1, S4 and author drivers use them rather than `suite.json`’s reader settings and step budgets. For example, changing the configured reader model has no effect, and a forty-minute author budget is cut at thirty minutes. **Smallest fix:** pass the appropriate suite role settings and deadline into each host invocation and record the effective values.