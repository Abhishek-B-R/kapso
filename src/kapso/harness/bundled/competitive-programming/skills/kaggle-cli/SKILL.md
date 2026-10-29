---
name: kaggle-cli
description: "The Kaggle command-line flow for a contest: telling a code competition from a file-upload one, the pages and the standings, downloading data, a kernel as a script or a notebook, the push with the competition attached, polling a version, verifying its output, the submission and its record in the ledger, reading the score, the shared account's session pool, the per-task or per-day quota, and the failures with their fixes. Use when a task is scored on Kaggle, from the first download to the last score."
---
# The Kaggle CLI, end to end

Kaggle calls the thing you run on its machines a kernel; it is a script
(`kernel_type: script`, ordinary top-to-bottom code) or a notebook
(`kernel_type: notebook`). The task's rules decide which; a script is the
simpler artefact and the rest of this skill assumes one. The type is fixed
when the kernel is created, so choose it from the start.

## Settle the modality first

A **code competition** scores a file your kernel writes when Kaggle re-runs
it (internet off, the data mounted); a **file-upload competition** scores a
prediction file you produce locally. The task statement's Submission
section says which. The upload path: read the pages, download the data,
develop locally, submit the file, record it, poll the score. The rest is
the code-competition path.

```
the pages           kaggle competitions pages <C> --page-name <name> --content
the standings       kaggle competitions leaderboard <C> --show
list, download      kaggle competitions files <C>; kaggle competitions download <C> -p data/   (then unzip)
push the kernel     kaggle kernels push -p kernel/                 (prints the version number: record it)
poll one version    kaggle kernels status <owner>/<slug>/<version>
its output          kaggle kernels output <owner>/<slug>/<version> -p out/<version>/
your kernels        kaggle kernels list -m                         (the harvest's list)
pull a kernel       kaggle kernels pull <owner>/<slug> -p <dir> -m  (a sibling's, to steal a component)
submit (code)       kaggle competitions submit <C> -k <owner>/<slug> -v <version> -f <output file> -m "<idea> local=<score>"
submit (file)       kaggle competitions submit <C> -f <file> -m "<idea> local=<score>"
the submissions     kaggle competitions submissions <C> --format json   (paginated; poll until scored)
```

`--format json` where supported, `-q` in non-interactive runs; never
`--sandbox` (it marks a host's test submission). A private or community
competition is absent from search: name it by slug in every command. The
CLI reads the account's token from `~/.kaggle/kaggle.json` or from the
`KAGGLE_USERNAME` and `KAGGLE_KEY` variables; test it with any
authenticated call (`kaggle kernels list -m`), not with the interactive
login's own command. The commands above are the 2.x CLI's; a flag that
differs on the installed one is read from its `-h`.

## The kernel folder

`kernel/` holds the script and `kernel-metadata.json` (`kaggle kernels init
-p kernel/` writes a template): `id` as `owner/slug` (lowercase, dashes,
matching the title), `code_file`, `kernel_type`, `is_private: true`
(public needs phone verification and gains nothing), `enable_internet:
false`, `competition_sources: ["<C>"]` (what mounts the data), and the
machine shape and GPU flag the task's rules fix; never leave the shape
unpinned when a GPU is wanted, since an unpinned shape can draw hardware
that cannot train. List every attachment the task's starter declares.

Portability: never hard-code the input path; the data mounts under
`/kaggle/input/` in a subfolder that varies, so locate files by name with
a recursive search over the mounted inputs and the local data directory.
Write the output to `/kaggle/working/` on Kaggle. Add cheap assertions
(row count, no duplicate ids, the required columns) so a bad run fails
loudly. Instrument every kernel with stage-elapsed lines and a final total
against the cap, so a truncated log says which stage blew the budget; a
published per-run cap binds the scoring re-run as well as the push.

## Push once, per version

Push with the task's per-run time cap when the statement states one
(`--timeout <seconds>`). The first run after a competition is newly
attached to a new kernel can start before the data mounts and dies at
file-lookup time with a file-not-found; that failure is cheap and
unmistakable: re-push only when you see it. A reflexive double push wastes
a session and GPU quota. Every push is a new version; status, output,
audit and submission name that version, and each version's output goes in
its own directory, so a later push never changes what an earlier one is
read as.

When several lanes share one account, the account's interactive sessions
are shared, and only a push takes one; a scoring re-run holds none. Where
the task root provides a ticket office for the pool, take a ticket before
a push and release it when the version goes terminal; a `Maximum ...
session count reached` message is backpressure, not failure: keep the
recipe, wait, retry.

## Poll, verify, submit, record, read

Poll the version's status until it is terminal: `COMPLETE`, `ERROR`, or
`CANCEL_ACKNOWLEDGED` (a cap-stopped run, with a truncated log and no
traceback). Download the output and check the submission file exists and
the log shows the success line; on an error, the log holds the traceback.

A submission spends shared quota and leaves a record: the kernel version
or the file's hash, the submission id, the message and, once it lands,
the score, in the ledger the task root names. The root's descriptor,
`kapso_datasets/contest.json`, is `{"competition": "<slug>", "ledger":
"<absolute path>", "procedure": "<command>"}`; where it names a
procedure, that procedure submits and records, and the raw command above
is refused in the shell by the harness; without one, submit with the
command and append the record to the ledger yourself: `{"submissions":
[...]}`, one entry per submission with `competition`, `submission_id`,
`kernel_ref` and `version` or `file_sha256`, `message`, `status` and
`public_score`. The CLI's exit code is not the signal on every version:
read the text (a rejected code submission says why, often with a 403). A
code submission re-runs the kernel on Kaggle's scoring side; re-submitting
the same version is a fresh run that may score slightly differently where
the rules allow it.

Read the score by polling the submissions list until the status is
complete and the public score is populated; the message you gave with the
submission is the team's memory of what it was, so it names the idea and
the local score. The quota is the statement's: per task or per day; when
it resets, the counter is the day's entries.

## Failures and their fixes

| Symptom | Cause | Fix |
|---|---|---|
| file-not-found on the data in the kernel | data not yet mounted on a new kernel's first run, or a hard-coded path | re-push once; locate files by name |
| the submission file missing from the output | the run errored, or it was written elsewhere | read the log; write to the working directory |
| a submit rejected for a missing data source or output file | a version without the competition attached, or a failed run | attach the competition; submit a completed version |
| a submit rejected on the version | the wrong version number | use the integer the push printed |
| status or output "not found" | no completed version yet | wait; a version must run before it is queryable |
| the run ends `CANCEL_ACKNOWLEDGED` | the per-run cap | read the stage timings; shrink the stage that blew it |
| auth errors on every call | the token not picked up | put the token in its place; retest with an authenticated call |
| data access denied | the rules not accepted | accept them once on the site, then retry |
| the session cap reached | the account's pool is full | wait for a ticket; never weaken the solution over it |
| the daily cap hit | the quota's window is a day | wait for the reset; plan the day's rounds against it |
