"""The experience package retired a set of names (docs/plans/redesign/
wp3-experience.md): the serving switch, the bank verb and the learn
init-bank form, the research, learn_knowledge and index_kg verbs, the
constructor's index keyword and the build flag for it, the gate's old
bank variable, the task family and the serving scope keyword, and the
`family:` card coordinate. The config package (wp4-config.md) retired
the modes and their loader, the mode flag, the flat strategy parameters
and the two agent blocks: the config is the packaged file plus one
override file, with the hosts table and the three roles under
`search_strategy.params`. Nothing under the code, the tests, the
skills, the examples, the benchmarks, the bot or the published docs
names one: every executable contract and every text a model or a
person reads moved to the new design. The plans and the research notes
are history and stay; the scenario fixtures recorded before the
coordinate change keep their cards as they were served, and a test of
the rule that a retired form is refused keeps the form it refuses."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPE = ("src", "tests", "skills", "examples", "benchmarks", "moltbook_bot", "docs", "README.md", "docs.json")
SUFFIXES = {".py", ".md", ".mdx", ".yaml", ".yml", ".json", ".toml", ".txt", ".sh"}
PROSE_SUFFIXES = SUFFIXES - {".py"}
EXCLUDED_PARTS = ("__pycache__", ".kapso", "plans", "research")
# The configuration keys the config package retired: a role's `cli`,
# `model`, `effort`, `timeout`, `gates` and `web` and ideation's
# `ensemble`, `selector`, `lens_planner` and `candidates_per_member`
# replace them. The two timeouts live on as the benchmark runners' own
# session-cap names, so they are retired as config keys in prose only.
RETIRED_KEYS = (
    "idea_generation_model", "implementation_model", "implementation_cli", "implementation_web",
    "ideation_gates", "implementation_gates", "ideation_ensemble", "ideation_selector",
    "ideation_lens_planner", "ideation_candidates_per_member", "implementation_fallback_model",
)
RETIRED_KEYS_IN_PROSE = RETIRED_KEYS + ("ideation_timeout", "implementation_timeout")
RETIRED = re.compile(
    r"serving\.enabled"
    r"|kapso bank\b"
    r"|learn init-bank"
    r"|\b(?:kapso|k)\.research\("
    r"|Kapso\(\)\.research\("
    r"|kapso research"
    r"|learn_knowledge"
    r"|index_kg"
    r"|kg_index="
    r"|--kg-index"
    r"|KAPSO_BANK_DIR"
    r"|KAPSO_BANK_HEAD"
    r"|KAPSO_TASK_FAMILY"
    r"|KAPSO_TASK_DATASET"
    r"|kapso-mcp --gates"
    r"|serving_scope"
    r"|\bfamily:\w"
    # The observability package (wp6-observability.md): the session
    # record is session.json, with the host's runs in it; the watch tree
    # is the trace's.
    r"|harness\.json"
    r"|kapso watch[^\n`]*--tree"
    # The config package (wp4-config.md): the modes and their loader, the
    # mode flag and argument, the two agent blocks, the presets file, the
    # build's free context, and a retired key read as a config key.
    r"|default_mode\b"
    r"|load_mode_config"
    r"|\bmode_config\b"
    r"|^\s*modes:"
    r"|\[[\"']modes[\"']\]"
    r"|--mode\b"
    r"| -m [A-Z][A-Z_]*\b"
    r"|mode=[\"'](?:GENERIC|MINIMAL)"
    r"|^\s*(?:feedback_generator|coding_agent):\s*$"
    r"|strategies\.yaml"
    r"|additional_context"
    r"|design_axes"
    # The deploy package (wp5-deploy.md): the strategy enum and its
    # factory, the selector, the adapter and its validator, the runners
    # and their aliases, the instruction files, the run-interface tags,
    # the adapted copy beside the campaign, the old block's agent key, the
    # verb's old flags (scoped to the deploy verb: RelBench's own
    # --strategy is a search strategy).
    r"|DeployStrategy\b"
    r"|DeploymentFactory"
    r"|StrategyRegistry"
    r"|DeployStrategyConfig"
    r"|DeploymentSetting\b"
    r"|AdaptationResult"
    r"|AdaptationValidator"
    r"|DeploymentInfo\b"
    r"|DeployConfig\b"
    r"|DeployedSoftware"
    r"|SelectorAgent"
    r"|AdapterAgent"
    r"|(?:Local|Docker|Modal|BentoML|LangGraph|Function|HTTP|BentoCloud)Runner\b"
    r"|selector_instruction"
    r"|adapter_instruction"
    r"|run_interface"
    r"|required_files"
    r"|_adapted_"
    r"|deployment\.coding_agent"
    r"|kapso deploy[^\n`]*--strategy"
    r"|kapso deploy[^\n`]*--interactive"
    + r"|[\"'](?:" + "|".join(RETIRED_KEYS) + r")[\"']\s*[\]:]"
)
# In every text a person or a model reads (the pages, READMEs, skills and
# configs) a retired key is a leftover wherever it stands; in code the
# strategy keeps attributes and arguments of these names for what it
# resolved, which only the quoted-key form above reaches.
RETIRED_IN_PROSE = re.compile(r"(?<!\w)(?:" + "|".join(RETIRED_KEYS_IN_PROSE) + r")(?!\w|\.md)")
ALLOWED_PATHS = (
    "benchmarks/relbench/data/learning_behavior/",
    "tests/test_bank_retriever.py",
    # The trace fixtures' generator reads the archives' old record name.
    "tests/fixtures/trace/build_fixture.py",
    # The refusals of a config with `modes:`, of a retired parameter and of
    # the build's free context are negative tests: they name what they refuse.
    "tests/test_config_resolution.py",
    "tests/test_session_roles.py",
    "tests/test_problem_text.py",
    "tests/test_cli_errors.py",
)


def _files():
    for entry in SCOPE:
        path = ROOT / entry
        if path.is_file():
            yield path
            continue
        for candidate in sorted(path.rglob("*")):
            if (
                candidate.is_file()
                and candidate.suffix in SUFFIXES
                and not any(part in EXCLUDED_PARTS for part in candidate.parts)
                and candidate != Path(__file__)
            ):
                yield candidate


def test_nothing_names_a_retired_form():
    offenders = []
    for path in _files():
        relative = path.relative_to(ROOT).as_posix()
        if relative.startswith(ALLOWED_PATHS):
            continue
        prose = path.suffix in PROSE_SUFFIXES
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if RETIRED.search(line) or (prose and RETIRED_IN_PROSE.search(line)):
                offenders.append(f"{relative}:{number}: {line.strip()}")
    assert offenders == [], "\n".join(offenders)
