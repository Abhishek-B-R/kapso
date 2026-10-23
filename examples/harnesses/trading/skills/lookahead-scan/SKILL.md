---
name: lookahead-scan
description: Static scan of a diff for look-ahead patterns (negative shifts, centred windows, backward fills, forward as-of joins). Run it on the attempt's diff before launching the evaluation, and again in verification on the final diff.
---
# Look-ahead scan

```
git diff main...HEAD | python $KAPSO_HARNESS_ROOT/skills/lookahead-scan/scripts/scan.py
```

Prints the findings as JSON, one per added line that matches a rule, and
exits 1 when there are any, so a hit cannot be mistaken for a pass.

A finding is not always a bug: a negative shift builds a training label
legitimately. Every finding needs either a fix or a sentence in the attempt
notes saying why it is safe. In verification, a finding without that sentence
is evidence against the attempt.
