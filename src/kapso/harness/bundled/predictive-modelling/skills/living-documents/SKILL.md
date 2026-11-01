---
name: living-documents
description: "The two append-only files a campaign keeps in the shared artifact directory the task statement names ($KAPSO_SHARED_CACHE_DIR in a Kapso campaign), the table information and the feature history, with the entry format and the append discipline. Use at the start of setup to create them when absent, before proposing a feature to read them, and after every experiment to append."
---
# Living documents

Two files live in the directory the task statement names for shared
artifacts (`$KAPSO_SHARED_CACHE_DIR` in a Kapso campaign: the directory
every session of the campaign shares and a resume keeps). Setup creates
them only when they are absent; every later session reads them first.
Each entry an earlier campaign left carries that campaign's task and
version in its header, so a reader knows which data it was measured on.

## `table_information.md`

Your knowledge base about the data, starting from the setup profile:
table and column semantics, the join graph and the multi-hop join paths
you use, unit quirks, null semantics, joins that worked, dead ends with
their measured reasons. Keep it factual; do not delete an earlier note
unless it is measured wrong.

## `features_history.md`

The campaign's persistent feature memory. Read it before proposing
features; append one entry for every feature or coherent feature group you
propose or test. Append-only: never delete or rewrite an existing entry;
write each entry in one append (open in append mode, write the whole
entry, close), so parallel lanes never interleave; an earlier campaign's
entries are evidence, not clutter.

```markdown
# Feature history (living memory)

### <feature or group name>  (<task>, <data version>)
- run/experiment: <id> | status: PROPOSED | TESTED-KEPT | TESTED-REJECTED | BLOCKED
- what: <tables/columns/transform in one line>
- outcome: <measured metric deltas / gate numbers, or why it was blocked>
- takeaway: <one line the next proposer should know>
```
