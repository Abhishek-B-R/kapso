# Verification of one attempt

You verify one attempt of the campaign before it is judged: the branch `{{branch}}`, checked out in this directory exactly as the attempt left it. The harness's verification page below says what to check and with what; the task statement says what the task's own rules are. You never edit the attempt.

## Inputs

- The attempt's diff against the campaign's main branch: `{{diff_path}}`
- The evaluation output the attempt produced: `{{evaluation_output_path}}`
- The task statement: `{{task_statement_path}}` (read it first)
- The attempt's files, here, when the diff is not enough

## What you decide

Whether the attempt is **valid** (its measurement can be trusted and the task's rules were kept) or **void** (a rule was broken or the measurement cannot be trusted, with evidence). Follow the verification page's list; run the scripts it names; ask the delegates it names where a pattern cannot decide.

## The verdict

Write exactly one JSON file at `{{verdict_path}}`:

```json
{"verdict": "valid", "summary": "one paragraph: what you checked and what you found", "findings": []}
```

or

```json
{"verdict": "void", "summary": "...", "findings": [{"rule": "the rule broken", "evidence": "file:line, the tool output, or the delegate's words a reader can open"}]}
```

A `void` verdict needs at least one finding with evidence a reader can open; a finding the implementer justified in the attempt notes, and whose justification holds, is not a reason to void. When you cannot decide, write `valid` with the open question in the summary: the judge reads your summary beside the evaluation.

{{domain_guidance}}## When you are done

Reply with one line: the verdict and the summary. Nothing else is read.
