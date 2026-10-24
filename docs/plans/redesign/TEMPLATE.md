# WP<n>: <name>

Date. Owner. Branch `redesign/wp<n>-<slug>`. Size estimate.

## Scope

What this package delivers, in five lines or fewer. Then **not in scope**:
the things a reader might expect here that belong to another package, with
the package named.

## Interface

What this package exposes (signatures, file formats, CLI lines, record
fields) and what it consumes from earlier packages. Frozen once the
sub-plan is approved; a change afterwards is a note here and a message to
the packages that depend on it.

## Ownership

The files and directories this package edits. Files it reads but must not
edit, with the owner named.

## Changes

The ordered list of changes, each one a commit: what, where, and the test
that proves it. Deletions listed as deletions.

## Tests

- Syntactic: the test files and what each pins (contract, negative case,
  golden).
- Proof run: the fixture, the budget, what the archived run must show.
- Semantic hooks: which S tests become runnable, and the numbers to
  record.

## Acceptance

The done-when list, each line checkable by someone who did not do the
work.

## Risks

What could go wrong and what is done about it.

## Review

The reviewer's findings and how each was answered. The owner's go.
