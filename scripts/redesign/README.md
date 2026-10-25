# scripts/redesign

Tooling the redesign's work packages use (`docs/plans/redesign/MASTER.md`).

## review.sh

```
scripts/redesign/review.sh <brief.md> <out-dir>
```

Runs two independent reviewers over a brief that names the files to read
and the questions to answer: Codex (`gpt-6-astra`, reasoning xhigh,
read-only sandbox) and Claude Code (`claude-opus-5`, read-only tools).
Outputs `codex.md` and `claude.md`. Every sub-plan and every pull request
of the redesign gets this before merge; the findings and their answers go
into the sub-plan's Review section.

## fresh_machine.sh

A GCP machine with nothing from the development checkout on it, for proof
runs and the semantic suite.

| | |
|---|---|
| project, zone | `trans-density-437811-p2`, `us-central1-a` (override with `KAPSO_FRESH_PROJECT`, `KAPSO_FRESH_ZONE`) |
| machine | `e2-standard-4`, Ubuntu 24.04, 50 GB disk, about $0.134 per hour |
| labels | `purpose=kapso-fresh,run=<run-id>`; `status` lists them |
| lifetime | created with `--max-run-duration 4h --instance-termination-action DELETE`, so an orphan deletes itself even if this script never runs again |
| install | `fresh_machine_install.sh` over ssh: uv, Node 22, `claude` and `codex` CLIs, the wheel as a `uv tool` |
| secrets | `claude-oauth-token-3` (another login's secret with `KAPSO_FRESH_CLAUDE_SECRET`, when the token rule says so) and `openai-api-key` from Secret Manager, written over ssh stdin into `~/.secrets/env` (mode 600); never on a command line, in instance metadata or in a log; Codex logs in with the API key |
| run | `run <id> "<command>"` sources `~/.secrets/env` and runs the command; output is tee'd to `scripts/redesign/runs/<id>/run-N.log` |
| delete | idempotent; verifies the instance and its disk are gone; prints the elapsed hours and the estimated cost |

`scripts/redesign/runs/` is the local record of each machine (create log,
wheel sha256, install log, run logs, deletion line). It is gitignored except
for the files a sub-plan cites as evidence.

Why an API key for Codex on the machine: a copied ChatGPT session is
single-holder, and the copy that refreshes on the machine revokes the
development box's, which runs the long campaigns. The Claude token is the
one the campaigns already use from the same secret store; probe its weekly
window before a long run, as the token rule says.
