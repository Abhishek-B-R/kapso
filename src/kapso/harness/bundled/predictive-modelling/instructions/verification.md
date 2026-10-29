# Verification

Check the attempt for leakage and for an honest validation. The verdict is
valid or void, with evidence.

1. Run the leakage-scan skill's script on the diff, with the regime the
   domain statement names. It reports reads outside the prepared copy and
   the task's data reference, label columns unmasked or recovered, a cache
   location overridden, a reach outside a per-tick snapshot, a database load
   that re-truncates under per-row seed time (the temporal-protocol skill
   names the call), and the sites where training and validation rows mix or
   a fit touches validation labels.
2. Ask the leakage-auditor with the diff and the evaluation output. Its
   findings name the file, the line, and the rows a feature would read ahead
   or the labels a model would see.
3. Read the evaluation output against the task's history. A validation score
   far above the published entries the task statement names, a windowed
   reading that collapses while the flat one holds, or a per-tick history
   that stops growing at a fixed date is evidence of a leak or of a
   dishonest origin.
4. Void when a finding stands without the attempt notes' sentence saying why
   it is safe; in verification, a finding without that sentence is evidence
   against the attempt. Otherwise valid, with a summary naming what was
   checked and what was found safe.
