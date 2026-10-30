# WP11: the release

2026-10-30. The builder. Branch `wp11-release`, cut from `redesign` at WP10's merge. Size S for the edits, a day of machine time for the gate, and a conflict pass that is M: `main` moved twenty commits past the integration branch's base while the redesign was built.

## Scope

The one release of the redesign: `main` brought into `redesign` with its twenty commits ported onto the redesigned modules, the version, the release notes with the rename mapping, the gate run from the release wheel, the merge of `redesign` into `main` at the owner's checkpoint, the tag, PyPI through the publish workflow, the docs site's rebuild, the marketplace at the tag. **Not in scope:** any feature; a cold-start IOAI reading (it needs a Kaggle account that never entered the practice competition, the owner's to make); S6 again (the owner, 2026-10-29: the WP9 reports stand); a rerun of any arm (the owner, 2026-10-29).

## Interface

- `main`'s twenty commits since the base (pull requests #161, #163, #164, #166, #167, #168, #169, #170: the weighted parent policy, one lane-env entry per lane, the knowledge search's description cut, `kapso report`, the repo-memory update windowed and budgeted per run, the inbox reply hint naming the campaign, the launch record's resolved paths, the NaN metric failing the codify gate) merged into the release branch, the nine conflicting files resolved by porting each change onto the redesigned module it lands in (the CLI package in place of `cli.py`, the generic strategy, the inbox, the config, the reference pages, the README), each with the tests that came with it, green.
- The version `0.8.0` in `pyproject.toml`, `src/kapso/__init__.py`, the two plugin manifests that carry one (`plugin/.claude-plugin/plugin.json`, `plugin/.codex-plugin/plugin.json`) and `CITATION.cff` (`scripts/check_citation.py --fix`).
- The release wheel: `python -m build --wheel` at the merge candidate (the release branch with `main` ported and the version bumped); its sha256 in every gate record's `package.wheel_sha256`.
- The gate: S1, S2, S4 and S5 on both hosts through `scripts/redesign/semantic.sh <test> <host> --machine <id>` on fresh machines from that wheel, one report per run under `tests/semantic/reports/` with `report.py`'s verdict; S3 is WP8's `s3-1` record; S6 is WP9's reports.
- The release notes: the GitHub release `v0.8.0` (`gh release create v0.8.0 --target main --notes-file …`), which triggers `publish.yml` to PyPI. Sections: the one-liner; what changed, package by package, in the user's terms; the rename mapping, complete (`kapso evolve` → `kapso build`; the modes → one packaged config with one override file; `learn init-bank`, `bank create|connect` → `kapso experience add|share`; `--knowledge` → `kapso experience add` and `--experience`; the deploy strategies → target skills; the Learn pages' six paths → two), sourced from each sub-plan's Interface and checked against the CLI; what the arms measured and what they did not.
- The docs site rebuilds from `main`; the plugin marketplaces (`.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`) read the repository at the tag.

## Ownership

Edits: the ports of `main`'s changes into the modules they land in (the one exception to "reads, never edits", bounded to those changes and their tests), `pyproject.toml`, `src/kapso/__init__.py`, the plugin manifests, `CITATION.cff`, this sub-plan, `tests/semantic/reports/`, `DECISIONS.md`. A gate failure in a package's own code is fixed on its package's branch as its own pull request, and the wheel is rebuilt.

## Changes

1. The sub-plan; `main` merged into the release branch and the nine conflicts resolved as ports, the suite green; the version bump with the citation fix; the wheel built from the merge candidate, its sha256 recorded here.
2. The release notes, drafted from the sub-plans' Interfaces, with the rename mapping checked against the CLI (`kapso --help` and each verb's) and the config loader; read by the owner.
3. The gate: S1, S2, S4, S5 on both hosts on fresh machines from the wheel, in parallel on distinct logins; each report committed as it lands; a failure goes back to its package's branch and the test reruns from a rebuilt wheel.
4. The owner's checkpoint: the eight reports, S3's record and S6's reports read; the release branch merged into `redesign` and `redesign` into `main` with its history kept, and pushed.
5. The tag and the release with the notes; `publish.yml` watched to PyPI green; `pip install leeroo-kapso==0.8.0` in a fresh venv, `kapso doctor`, the plugin's install line on Claude Code and on Codex, the docs site read once at its new navigation.

## Tests

- Syntactic: the ordinary gate at the merge candidate (CI on the merge pull requests); `scripts/check_citation.py` clean; the tests `main`'s commits carry, green on the ported code.
- Proof run: eight gate reports (four tests, two hosts) from the release wheel, each naming the wheel's sha256 and carrying a verdict.
- Semantic hooks: S1, S2, S4 and S5 recorded on both hosts; S3 from WP8; S6 from WP9.

## Acceptance

- `main`'s twenty commits are in the release with their tests; nothing of theirs is lost at the merge.
- `redesign` is merged into `main`; `v0.8.0` is on PyPI; the docs site shows the new navigation; the marketplaces install the plugin at the tag.
- Eight gate reports from the release wheel under `tests/semantic/reports/`, all passing; S3's record and S6's reports linked from the release notes.
- The release notes carry the complete rename mapping and say what the arms measured and what they did not.

## Risks

- The conflict pass: `kapso report` lands in a CLI that was split into a package, and the parent policy in a strategy that was rewritten; a port that changes behaviour is a finding on the package it touches, fixed there.
- A late gate failure: the fix lands on its package's branch, the wheel is rebuilt, the test reruns; the date moves before the gate does.
- The logins: the Claude logins near their weekly caps are shared; the Codex login is the semantic session's.
- The rename breaks released users: the notes' mapping, and no piecemeal landing.

## Hours

To be filled at the end.
