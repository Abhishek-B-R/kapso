---
name: living-documents
description: "The two append-only files a campaign keeps in its shared artifact directory, the table information and the feature history, with the entry format. Use at the start of setup to create them, before proposing a feature to read them, and after every experiment to append."
---
# Living documents

Two files live in the shared artifact directory and persist across
iterations, lanes and resumes. Consult both at the start of every session.

## `table_information.md`

Your knowledge base about the database, starting from the setup profile:
table and column semantics, the join graph and the multi-hop join paths you
use, unit quirks, null semantics, joins that worked, dead ends with their
measured reasons. Keep it factual; do not delete an earlier note unless it
is measured wrong.

## `features_history.md`

The campaign's persistent feature memory. Read it before proposing
features; append one entry for every feature or coherent feature group you
propose or test. Append-only: never delete or rewrite an existing entry;
parallel lanes append concurrently, and earlier campaigns' entries are
evidence, not clutter.

```markdown
# Feature history (living memory)

### <feature or group name>
- run/experiment: <id> | status: PROPOSED | TESTED-KEPT | TESTED-REJECTED | BLOCKED
- what: <tables/columns/transform in one line>
- outcome: <measured metric deltas / gate numbers, or why it was blocked>
- takeaway: <one line the next proposer should know>
```

Setup creates both files (the first with the profile's findings, the second
with the heading and no entries); every later session reads them first.
