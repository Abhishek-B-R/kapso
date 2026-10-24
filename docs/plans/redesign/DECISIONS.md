# Decisions taken during the implementation, for the owner to check

Started 2026-10-24. The owner asked for the implementation to run
autonomously and for any architecture or design decision that was not
discussed to be written here so it can be checked later. Newest first.
Each entry: what was decided, why, what the alternative was, and where it
shows.

## 2026-10-24, WP1 (planned; taken while revising the sub-plan after review)

**The brief has its own flag, `--brief`; `--goal-file` stays plain text.**
The design documents said `--goal-file kapso-brief.md`. A file that is not
a brief must not be guessed at (no silent fallback), and engineers do pass
plain problem statements by file today, so the two forms get two flags.
Alternative rejected: one flag that tries the brief grammar first.

**A solution's one path is `trace`.** `SolutionResult.code_path` and the
design's `Solution.trace` were the same directory: the workspace, checked
out at the delivered branch, with the record under `.kapso/`. One field,
named `trace`; deployment reads the code from it.

**`build()` writes `.kapso/solution.json` on every return, and `open()`
reads only that.** The alternative, reconstructing a solution from five
record files, needs rules for which file wins and has no durable
evaluation log to read. The facade already computes the delivered score,
the branch and the registry head at return; writing them is a few lines,
and a paused or budget-stopped campaign gets a record too.

**`Experience` is WP3's.** The design returns `Experience` from `learn()`;
today's `LessonResult` is that class. Renaming it belongs with the
experience work, not with `build`, so WP1 leaves `learn()` returning
`LessonResult` and only changes its parameter type.

**`kapso deploy` takes a solution, not a directory of code.** Today's
command constructs a result from any path. In the design `deploy` takes
the outcome of a build, so the command opens the record; deploying an
arbitrary directory is not a case of this verb. WP5 may add a `--repo`
form if a user needs it.

**`Kapso(config=...)`.** The constructor keyword follows the design; the
internal attribute keeps its name.

**A sentence goal is rendered as a brief too, so the engine always sees one
grammar.** `build("Raise AUC above 0.85")` renders `Objective    Raise AUC
above 0.85` into the goal text, the checkpoint fingerprints that, and a
resume parses it back; `kapso inbox` reads the objective's first line the
same way. Alternative rejected: passing a plain string through untouched,
which would have left the checkpoint holding two shapes and the resume
guessing which one it had.

**The brief keeps paragraphs and pasted indentation.** Blank lines between
two lines of the same field stay as paragraph breaks (elsewhere they are
nothing), and a field's continuation lines are dedented together, so a
pasted traceback or code block reaches the model with its relative
indentation. Rule 6 asked for the content whole; this is what "whole"
means for a multi-line objective. Alternative rejected: stripping every
continuation line, which flattens code.

**The `Solution` dropped three things the old result carried.**
`experiment_logs` (one line per node, re-derivable from the experiment
history and WP6's `kapso trace`), `resumed` (the checkpoint knows) and
`status_path` (always `trace/.kapso/status.json`). Each was a field nobody
acted on; rule 10.

**`final_report.json` carries flat keys instead of an opaque `metadata`
dictionary.** `learn()` writes `goal`, `succeeded`, `final_score`,
`stopped_reason`, `iterations`, `cumulative_iterations`, `cost_usd`. The
report's readers (the trajectory store, the mining crew) never read
`metadata` by key; they read the file as prose, so named keys serve them
better than a dump of the old dictionary.

**The facade resolves every path it is given, and the workspace keeps its
directory absolute.** The first proof run on the fresh machine crashed at
the first session close: `--output ../churn-build` reached the experiment
workspace relative, the session clone ran `git add ../churn-build/...`
from its own directory, and git refused it as outside the repository. The
code is unchanged from `main`, so every relative `--output` whose session
left run data behind crashed before WP1 too; the fresh machine found it
because nothing from the development checkout masked it. `build()` now
resolves `output`, `evaluation`, `data` and a local `repo` (a URL is left
alone), and `ExperimentWorkspace` takes `os.path.abspath` of its directory,
so a direct caller is covered as well. Rule 7 applies: no second code path
for relative directories.

**A five-minute budget starves the implementation; the proof uses
fifteen.** The budget's `clamp_timeout` bounds every session by the time
left outside the reserve, with a 60-second floor, so a five-minute
campaign gives its first implementation about a minute, which the deadline
then kills. The example brief says ten minutes and four experiments; the
proof run passes `--budget-minutes 15 --iterations 2` on the command so
each session has room, which is also what the flags-win-over-the-brief
rule is for. The ten-minute claim on the first-build page stands for the
whole example on a machine with the libraries installed; it is measured by
the proof run and will be corrected if the run says otherwise.

**The examples are the semantic fixtures, under `examples/`.** The docs
plan said one source; the WP0 fixture lived under `tests/semantic/`. It
moved to `examples/churn-first-build/`, and `tests/semantic/README.md`
points at the examples. Alternative rejected: a copy under `tests/`, which
is the drift the plan forbids.

**The engine pages stay at their URLs, regrouped as "How it works".** The
docs plan retires the Evolve pages into condensed How-it-works pages. WP1
regroups them in the navigation and fixes their snippets, and leaves the
condensation to the packages that change their content (the config, the
record and the trace), so each page is rewritten once. Two pages did move
into Build (the inbox, resume and budgets), with redirects.

**The older examples keep their evaluator inside the repository until
WP2.** Moving each `evaluate.py` into a protected `evaluation/` directory
changes how it is invoked and needs each example run again; the harness
re-base in WP2 does that work once. Until then the brief's rule ("the
evaluator is never modified") is what protects it, as it did before.

**`Brief` is both the Python object and the file, one grammar.** The
interfaces document left open whether the brief is an API object or a
CLI-only file. `Brief.read` parses the file into the object and
`Brief.write` emits it, so the plugin, the CLI and a script hand the engine
the same thing, and `build()` renders the whole brief into the engine's
goal text. Alternative rejected: a file-only brief that the CLI flattens
to a goal string, which would leave Python users without the structure.

**Two names are left for later packages, on purpose.** `Experience` as
`learn()`'s return collides with `load_experience`'s source handle; WP3
settles it with the experience work. Whether a brief's `Harness` line or
a `load_harness()` call wins when both are given is WP2's, with the
loader. Neither is decided here.

## 2026-10-24, WP0

**Codex on the fresh machine logs in with an API key, Claude with the shared
OAuth token.** The fresh machine (`scripts/redesign/fresh_machine.sh`)
authenticates Codex with the `openai-api-key` secret from the benchmark
project's Secret Manager, via `codex login --with-api-key` over ssh stdin,
and Claude Code with the `claude-oauth-token-3` secret the campaigns already
use. Why: a copied ChatGPT session is single-holder; the copy that refreshes
on the machine revokes the development box's session, which runs the long
campaigns. A key is metered per token, revocable per machine and leaves no
shared state; a ten-minute proof run costs cents. Alternative rejected:
copying `~/.codex/auth.json` as the campaign waves do. Consequence: proof
runs and semantic runs that use Codex bill the OpenAI API account rather
than the ChatGPT plan; the Claude side still spends the shared weekly
window, so the token gate (probe the CLI per model before a long run)
applies to the fresh machine too.

**The CLI's top-level help keeps its hand-written epilog for now.** The
reviewers suggested replacing it with the parsers' own `help=` strings. WP0
keeps the text byte-identical (apart from trailing whitespace) because its
contract is "no behaviour change"; WP1 rewrites the help when `evolve`
becomes `build`.

**`deploy --interactive` stops on SIGINT through a signal handler instead
of `try/except KeyboardInterrupt`.** Same behaviour (the software is stopped
and the command exits 0); CLAUDE.md rule 2 forbids exception handling, and
WP0 chose to fix the violation in the move rather than carry it into a new
file. WP5 rewrites deploy anyway.

**The semantic fixture's hold-out is not sealed yet, and says so.** The
labels live outside the directories the engine copies into a workspace, but
a process in the workspace can read the absolute path the evaluator uses.
Sealing is the engine's job (evaluation integrity and permissions, build
steps 2 and 6); the fixture measures the flow until then, and its README
states it. Alternative rejected: a fixture-level trick (an encrypted labels
file, a separate evaluator process with its own credentials) that would
have to be undone when the engine seals hold-outs properly.

**The fixture's signal was reshaped for headroom.** The first generator
gave a logistic baseline of 0.742 AUC that a boosting model could not beat
(0.728). A fixture where nothing beats the baseline cannot show a build
working, so the label's logit gained thresholds, an interaction and a tenure
curve: logistic 0.797, boosting with no feature work 0.832. The persona and
the README carry the measured numbers, not round ones.
