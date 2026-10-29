---
name: leakage-scan
description: "Static scan for data-access leaks on a time-cut prediction task: reads outside the prepared copy, the test table unmasked or its columns recovered, a cache location overridden, a reach outside a per-tick snapshot, a database load that re-truncates under per-row seed time, and the advisory sites where training and validation rows mix. Use on the attempt's diff before launching the evaluation, and over the whole candidate in verification."
---
# Leakage scan

```
git diff main...HEAD | python3 $KAPSO_HARNESS_ROOT/skills/leakage-scan/scripts/scan.py --diff --regime <frozen|seed-time|autocomplete>
python3 $KAPSO_HARNESS_ROOT/skills/leakage-scan/scripts/scan.py --tree . --regime <frozen|seed-time|autocomplete>
```

The regime is the one the domain statement records. The diff mode reads
the added lines of the diff; the tree mode reads every Python file under a
directory, for the whole candidate. Both print the findings as JSON, one
per line that matches a rule, with the file, the line, the rule and the
concern, and exit 1 when any finding is a violation, so a hit cannot be
mistaken for a pass.

Violations: the test table read with its input masks off; a read of the
columns the sanitizer removed; the library's cache location overridden; a
dataset download or a direct fetch of the benchmark's files; a private
table builder; a probe of the task tables' statistics; a reach outside the
tick's snapshot (another tick's directory, the rolling root); a path into
the pristine library cache; and, under the per-row seed-time regime, a
database load that truncates at the static cutoff (under the frozen
regime, a load that asks for the untruncated database).

Advisory (printed with the `verify:` prefix, exit 0 on their own): a
training or validation table read with its masks off, a concatenation of
training and validation rows, and a fit that names validation labels. Each
is legal for the test-predicting model and illegal for the model that
produces validation predictions, so the site is traced rather than
condemned: say in the attempt notes which chain it belongs to.

A finding is not always a bug. Every finding needs either a fix or a
sentence in the attempt notes saying why it is safe; in verification, a
finding without that sentence is evidence against the attempt.
