# The author test, judged

A model author with only the authoring guide, the design and the trading example wrote a harness for a repository, logging every guess as a line (docs/plans/semantic-production-tests.md, section 4). You hold the guide, the harness and the guess log. Score the harness against the guide's rules, 0 or 1 each:

- **pages under forty lines**: 1 when every page is.
- **every skill named on its page**: 1 when each skill the harness ships is named on the page of the module that uses it.
- **no task value in the harness**: 1 when no dataset or task name, metric value, quota, deadline or foreign path appears in the harness.
- **the ladder respected**: 1 when each attachment takes the cheapest form that does its job (a page line before a skill, a skill before a delegate, a delegate before a hook). The brief asked the author for at least two skills, a delegate, a server and two hooks, so the question is never whether a kind of attachment exists but whether each one does a job only its form can do: a hook that restates a page line, or a server that returns a fixed list, fails this although the brief asked for a hook and a server.

(The guess log is classified separately, by the author test's own classifier, not here; this rubric scores only the four harness dimensions above.)
