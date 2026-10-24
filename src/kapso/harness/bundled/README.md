# Bundled harnesses

A harness in this directory loads by name: `kapso build --harness <name>`,
`Kapso().load_harness("<name>")`. The harness ports (WP8 of the redesign,
`docs/research/harness-ports.md`) fill it; until then `kapso harness list`
says none ship, and a harness is loaded by path or by repository
reference (`docs/research/onboarding.md`). The worked example lives under
`examples/harnesses/trading/`.
