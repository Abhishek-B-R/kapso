# IOAI provided evaluation (read-and-execute only)

`evaluate.py` reports the candidate's own recorded submission: it reads the
ledger the task root's submission procedure (`kapso_datasets/submit.py`)
writes, refreshes pending entries from every page of the competition's
submissions list (each entry is attributed by the token the procedure put
in its message; the refresh is merged into the ledger under the
procedure's lock, so a submission made meanwhile is kept), finds this
candidate's submissions by the hash of the repository-relative file the
procedure recorded (its kernel source or its uploaded file), and prints
the latest one's public score oriented so that higher is better. A
pending submission is not a score: the run exits non-zero with the
reason, and is run again once the score lands. Missing, rejected and
out-of-window (before the campaign's start or after its end) submissions
are distinct non-zero outcomes. Nothing here is edited; the ledger it
refreshes lives outside the tree.
