# The author test, judged

A model author with only the authoring guide, the design and the trading example wrote a harness for a repository, logging every guess as a line (docs/plans/semantic-production-tests.md, section 4). You hold the guide, the harness and the guess log. Score the harness against the guide's rules, 0 or 1 each:

- **pages under forty lines**: 1 when every page is.
- **every skill named on its page**: 1 when each skill the harness ships is named on the page of the module that uses it.
- **no task value in the harness**: 1 when no dataset or task name, metric value, quota, deadline or foreign path appears in the harness.
- **the ladder respected**: 1 when each attachment takes the cheapest form that does its job (a page line before a skill, a skill before a delegate, a delegate before a hook).

Then classify every line of the guess log as one of: a **structural gap** (a field, file, key, convention or host behaviour the engine or `check` would reject if guessed wrong, which the guide does not state), a **contradiction** in the guide, a **domain decision** (a choice the author was free to make), or **documented** (the guide says it; the author did not find it). Return the counts and, for each structural gap and contradiction, the sentence the guide lacks.
