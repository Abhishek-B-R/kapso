# Harness examples

A harness is the domain layer of Kapso: one directory per domain that tells
the engine's agents how work is done there, with what, under which rules,
and nothing about any particular task. The interface is described in
[`docs/research/harness-design.md`](../../docs/research/harness-design.md)
and the authoring guide in
[`docs/research/harness-authoring-guide.md`](../../docs/research/harness-authoring-guide.md).

| Example | What it shows |
|---|---|
| [`trading/`](trading/) | the complete shape: seven instruction pages, seven skills (one with a script, one a deployment workflow), two delegate agents, two local tool servers, six hooks listed per module |
| [`predictive-modelling/`](predictive-modelling/) | the manifest only, to show the same shape on a second domain |

The trading harness's scripts and servers run as written: the hook scripts
read a hook event on stdin and print a decision, the lookahead scan reads a
diff on stdin, and the two servers are FastMCP servers over a local store of
CSV or parquet bars. They are examples of the interface, not a trading system.
