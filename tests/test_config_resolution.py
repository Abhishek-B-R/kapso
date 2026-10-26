"""The config as two layers (docs/plans/redesign/wp4-config.md): the
packaged defaults, and one override file deep-merged over them. These
pin the resolver's contract: the defaults alone without a path, the
merge semantics (nested mappings merge, scalars and lists replace), the
refusal of a top-level key the packaged file does not name (a stale
`modes:` included), the reserved `benchmark:` key the engine never reads,
the dotted paths the doctor prints, and the packaged file's own shape
(every strategy parameter a known one, every role on a host the table
names)."""

from pathlib import Path

import pytest
import yaml

from kapso.core import config as config_module
from kapso.core.config import ConfigError, PACKAGED_CONFIG_PATH, deep_merge, load_config, override_paths, read_yaml
from kapso.core.roles import ROLES, check_params, resolve_role


def _write(tmp_path, payload, name="kapso-config.yaml"):
    path = tmp_path / name
    path.write_text(yaml.safe_dump(payload))
    return str(path)


def test_no_path_is_the_packaged_defaults():
    assert load_config() == read_yaml(PACKAGED_CONFIG_PATH)
    assert load_config(str(PACKAGED_CONFIG_PATH)) == load_config()
    assert override_paths() == [] and override_paths(str(PACKAGED_CONFIG_PATH)) == []


def test_override_merges_nested_mappings_and_replaces_scalars_and_lists(tmp_path):
    path = _write(tmp_path, {
        "search_strategy": {"params": {"host": "codex", "ideation": {"gates": ["repo_memory"]}}},
        "budget": {"minutes": 45},
    })
    config = load_config(path)
    params = config["search_strategy"]["params"]
    assert params["host"] == "codex"
    assert params["ideation"]["gates"] == ["repo_memory"]
    # The rest of the block is the packaged one: a key set does not forfeit its siblings.
    assert params["ideation"]["candidates_per_member"] == load_config()["search_strategy"]["params"]["ideation"]["candidates_per_member"]
    assert params["implementation"]["gates"] == load_config()["search_strategy"]["params"]["implementation"]["gates"]
    assert config["budget"]["minutes"] == 45 and config["budget"]["experiments"] == load_config()["budget"]["experiments"]
    assert sorted(override_paths(path)) == ["budget.minutes", "search_strategy.params.host", "search_strategy.params.ideation.gates"]


def test_an_unknown_top_level_key_is_refused_by_name(tmp_path):
    path = _write(tmp_path, {"modes": {"GENERIC": {}}, "default_mode": "GENERIC", "budget": {}})
    with pytest.raises(ValueError, match=r"unknown keys default_mode, modes; the keys are budget, "):
        load_config(path)
    with pytest.raises(ValueError, match="unknown key budgets;"):
        load_config(_write(tmp_path, {"budgets": {}}, "typo.yaml"))


def test_the_benchmark_key_is_the_runners_own(tmp_path):
    path = _write(tmp_path, {"benchmark": {"final_eval": {"timeout_seconds": 900}}, "inbox": {"enabled": False}})
    config = load_config(path)
    assert config["benchmark"] == {"final_eval": {"timeout_seconds": 900}}
    assert config["inbox"]["enabled"] is False
    assert override_paths(path) == ["inbox.enabled"]


def test_an_empty_or_non_mapping_file(tmp_path):
    empty = tmp_path / "empty.yaml"
    empty.write_text("")
    assert load_config(str(empty)) == load_config()
    wrong = tmp_path / "list.yaml"
    wrong.write_text("- a\n")
    with pytest.raises(ConfigError, match="a config file is a mapping"):
        load_config(str(wrong))
    with pytest.raises(ConfigError, match="missing.yaml: no such file"):
        load_config(str(tmp_path / "missing.yaml"))


def test_deep_merge_mutates_neither_input():
    base = {"retry": {"max_attempts": 2}}
    override = {"retry": {"jitter": True}}
    assert deep_merge(base, override) == {"retry": {"max_attempts": 2, "jitter": True}}
    assert base == {"retry": {"max_attempts": 2}} and override == {"retry": {"jitter": True}}


def test_the_packaged_file_resolves_its_own_roles():
    """Every parameter the packaged file sets is one the strategy reads,
    and every role resolves on a host the table names."""
    config = load_config()
    params = config["search_strategy"]["params"]
    check_params(params)
    for role in ROLES:
        resolved = resolve_role(config["hosts"], params, role)
        assert resolved.cli == params["host"] and resolved.model == config["hosts"][params["host"]]["model"]
    assert "modes" not in config and "default_mode" not in config
    assert config["evaluation_maintainer"]["enabled"] is False
    assert config["budget"]["experiments"] > 0 and config["budget"]["reserve_minutes"] is None


def test_the_benchmark_override_files_resolve():
    """The benchmark configs are override files: each resolves with no
    unknown key, its strategy parameters known, its roles on named hosts."""
    root = Path(__file__).resolve().parents[1]
    for relative in (
        "benchmarks/relbench/config.yaml", "benchmarks/ioai2026/config.yaml",
        "benchmarks/mle/config.yaml", "benchmarks/ale/config.yaml",
        "benchmarks/ioai2026/past_learning/config.yaml",
        "examples/ml_model_development/e2e/config.e2e.yaml",
        "examples/ml_model_development/e2e/config.e2e-fidelity-off.yaml",
        "examples/ml_model_development/e2e/config.gate.yaml",
    ):
        config = load_config(str(root / relative))
        params = config["search_strategy"]["params"]
        check_params(params)
        for role in ROLES:
            resolve_role(config["hosts"], params, role)


def test_a_tilde_path_is_the_persons_home(tmp_path, monkeypatch):
    """`--config ~/kapso-config.yaml` quoted by a shell, or `Kapso(config="~/…")`:
    expanded once, by the resolver, for the read as for the existence check."""
    monkeypatch.setenv("HOME", str(tmp_path))
    _write(tmp_path, {"budget": {"experiments": 3}})
    assert load_config("~/kapso-config.yaml")["budget"]["experiments"] == 3
    assert override_paths("~/kapso-config.yaml") == ["budget.experiments"]


def test_a_mapping_where_a_value_stood_is_refused_by_name(tmp_path):
    """A nested typo (`enabled: {typo: false}`) would otherwise read as the
    value and be true, since a mapping is truthy."""
    path = _write(tmp_path, {"preflight": {"enabled": {"typo": False}}})
    with pytest.raises(ConfigError, match=r"kapso-config.yaml: preflight\.enabled: bool expected, got a mapping"):
        load_config(path)


def test_the_adapters_own_settings_are_open_namespaces(tmp_path):
    """`agent_specific` is the adapter's own map (an endpoint's base_url):
    its keys are the person's, under the inference default and the
    learner's two sessions alike."""
    path = _write(tmp_path, {
        "inference": {"default": {"agent_specific": {"base_url": "http://x"}}},
        "learner": {"merger": {"agent_specific": {"base_url": "http://y"}}},
    })
    config = load_config(path)
    assert config["inference"]["default"]["agent_specific"] == {"base_url": "http://x"}
    assert config["learner"]["merger"]["agent_specific"] == {"base_url": "http://y"}
