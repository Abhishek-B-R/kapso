---
name: kaggle-cli
description: "The Kaggle command-line flow for a contest: telling a code competition from a file-upload one, reading the pages, downloading data, a portable script kernel, the push with the competition attached, polling the run, verifying the output, the submission through the task's procedure, reading the score, the session-pool discipline, and the failures with their fixes. Use when a task is scored on Kaggle, from the first download to the last score."
---
# The Kaggle CLI, end to end

You submit a plain Python script, not a notebook: Kaggle calls the thing
you submit a kernel, but a kernel can be a script (`kernel_type: script`)
with ordinary top-to-bottom code. Develop and test it as a normal file,
then push it.

## Settle the modality first

A **code competition** scores a file your kernel writes when Kaggle re-runs
it (internet off, the data mounted); a **file-upload competition** scores a
prediction file you produce locally. The task statement's Submission
section says which. The upload path is four steps: read the pages,
download the data, develop locally, submit the file through the task's
procedure and poll the score. The rest is the code-competition path.

```
read the pages      kaggle competitions pages <C> --page-name <name> --content
list, download      kaggle competitions files <C>; kaggle competitions download <C> -p data/   (then unzip)
push the kernel     kaggle kernels push -p kernel/            (once; see below)
poll the run        kaggle kernels status <owner>/<slug>      (until COMPLETE or ERROR)
inspect the output  kaggle kernels output <owner>/<slug> -p out/
submit              the task root's submission procedure (never the raw command)
read the score      kaggle competitions submissions <C> --format json   (poll until scored)
```

`--format json` where supported, `-q` in non-interactive runs. A private or
community competition is absent from search: name it by slug in every
command. Authentication is the account's token in its usual place; test it
with any authenticated call (`kaggle kernels list -m`), not with the
interactive login's own command.

## The kernel folder

`kernel/` holds the script and `kernel-metadata.json` (`kaggle kernels init
-p kernel/` writes a template): `id` as `owner/slug` (lowercase, dashes,
matching the title), `code_file`, `kernel_type: script` (fixed at creation,
so choose it from the start), `is_private: true` (public needs phone
verification and gains nothing), `enable_internet: false`,
`competition_sources: ["<C>"]` (what mounts the data), and the machine
shape and GPU flag the task's rules fix; never leave the shape unpinned
when a GPU is wanted, since an unpinned shape can draw hardware that
cannot train. List every attachment the task's starter declares.

Portability: never hard-code the input path; the data mounts under
`/kaggle/input/` in a subfolder that varies, so locate files by name with
a recursive search over the mounted inputs and the local data directory.
Write the output to `/kaggle/working/` on Kaggle. Add cheap assertions
(row count, no duplicate ids, the required columns) so a bad run fails
loudly. Instrument every kernel with stage-elapsed lines and a final total
against the cap, so a truncated log says which stage blew the budget.

## Push once

Push with the task's per-run time cap when the statement states one
(`--timeout <seconds>`). The first run after a competition is newly
attached to a new kernel can start before the data mounts and dies at
file-lookup time with a file-not-found; that failure is cheap and
unmistakable: re-push only when you see it. A reflexive double push wastes
a session and GPU quota. The push prints the version number: record it,
the submission needs it.

When several lanes share one account, the account's interactive sessions
are shared (a handful of GPU and CPU sessions at once; both a push and a
scoring re-run consume one). Where the task root provides a ticket office
for the pool, take a ticket before a push and release it when the run goes
terminal; a `Maximum ... session count reached` message is backpressure,
not failure: keep the recipe, wait, retry. A kernel that does not need a
GPU queues on the CPU pool, which is wider and usually idle.

## Poll, verify, submit, read

Poll the status until `COMPLETE` or `ERROR` (a cap-stopped run ends as
`CANCEL_ACKNOWLEDGED` with a truncated log and no traceback). Download the
output and check the submission file exists and the log shows the success
line; on an error, the log holds the traceback.

Submit through the submission procedure the task root provides: it records
the kernel version or the file's hash, the submission id, the message and
the score in the ledger the evaluator reads; a raw `kaggle competitions
submit` in the shell is refused by the harness because it records nothing.
The CLI exits 0 even on a rejected submission: the text is the only signal
(a rejected code submission prints a 403). A code submission re-runs the
kernel on Kaggle's scoring side and does not hold an interactive session;
re-submitting the same version is a fresh run that may score slightly
differently where the rules allow it.

Read the score by polling the submissions list until the status is
complete and the public score is populated; the message you gave with the
submission is the team's memory of what it was, so it names the idea and
the local score.

## Failures and their fixes

| Symptom | Cause | Fix |
|---|---|---|
| file-not-found on the data in the kernel | data not yet mounted on a new kernel's first run, or a hard-coded path | re-push once; locate files by name |
| the submission file missing from the output | the run errored, or it was written elsewhere | read the log; write to the working directory |
| a submit rejected for a missing data source or output file | a version without the competition attached, or a failed run | attach the competition; submit a completed version |
| a submit rejected on the version | the wrong version number | use the integer the push printed |
| status or output "not found" | no completed version yet | wait; a version must run before it is queryable |
| auth errors on every call | the token not picked up | put the token in its place; retest with an authenticated call |
| data access denied | the rules not accepted | accept them once on the site, then retry |
| the session cap reached | the account's pool is full | wait for a ticket; never weaken the solution over it |
