"""Pin the platform-default MCP gate lists of the generic strategy.

Design decision #4 (platform unification): `research` STAYS in the
platform default ideation gates — benchmarks not wanting the proxy trim
it in their own mode config, never by shrinking the platform default.
"""

from contextlib import contextmanager
from types import SimpleNamespace

from kapso.execution.search_strategies.generic.strategy import GenericSearch
from strategy_support import generic_params, packaged_hosts


def config(**overrides):
    return SimpleNamespace(params=generic_params(**overrides), hosts=packaged_hosts())


@contextmanager
def _patched_super_init(workspace_dir):
    from kapso.execution.search_strategies.base import SearchStrategy

    original = SearchStrategy.__init__

    def fake_init(self, config, wd=None, import_from_checkpoint=False):
        self.params = config.params or {}
        self.workspace_dir = workspace_dir
        self.feedback_generator = None
        self.budget_snapshot = None
        self.budget_snapshot_monotonic = None

    SearchStrategy.__init__ = fake_init
    yield
    SearchStrategy.__init__ = original


def test_default_gates_include_research(tmp_path):
    with _patched_super_init(str(tmp_path)):
        strategy = GenericSearch(config(), str(tmp_path))
    assert strategy.ideation_gates == [
        "research", "experiment_history", "repo_memory",
    ]
    assert strategy.implementation_gates == ["research", "repo_memory"]


def test_the_hosted_gate_rides_on_the_loaded_source_never_on_a_config_list(tmp_path):
    # Regression: a config list naming leeroopedia mounted it with no
    # source loaded, so a campaign was served what its records did not
    # name. What is loaded is what is served: the list's entry is dropped,
    # the loaded source appends the gate with its own address.
    with _patched_super_init(str(tmp_path)):
        listed = GenericSearch(config(
            ideation={"gates": ["research", "leeroopedia"]}, implementation={"gates": ["leeroopedia", "repo_memory"]},
        ), str(tmp_path))
    assert listed.ideation_gates == ["research"] and listed.implementation_gates == ["repo_memory"]
    assert listed.hosted is None
    hosted = {"url": "https://staging.example/mcp?token={LEEROOPEDIA_API_KEY}", "tool_timeout_seconds": 45}
    with _patched_super_init(str(tmp_path)):
        loaded = GenericSearch(config(hosted=hosted), str(tmp_path))
    assert loaded.ideation_gates[-1] == "leeroopedia" and loaded.implementation_gates[-1] == "leeroopedia"
    assert loaded.hosted == hosted


def test_staged_memory_stores_mount_their_own_gates(tmp_path):
    # Regression (E2E review 2026-08-24, blockers 1+2): serving injects an
    # intro naming bank_index / bank_get_card / bank_get_card_with_evidence
    # and an ingest writes pages the wiki-search gates read. Both are
    # reachable only if the providing gate is mounted, so the gate list
    # FOLLOWS the staged store instead of being an independent config
    # choice — the live run advertised bank tools no session had.
    params = {
        "bank_serving": {"KAPSO_BANKS": "[]"},
        "kg_index_path": "/tmp/wikis/.index",
        "hosted": True,
    }
    with _patched_super_init(str(tmp_path)):
        strategy = GenericSearch(config(**params), str(tmp_path))
    for gates in (strategy.ideation_gates, strategy.implementation_gates):
        assert "bank" in gates
        assert {"idea", "code"} <= set(gates)
        # the hosted source mounts its server the same way: loading it
        # is the switch, no config list names it (wp3-experience.md)
        assert "leeroopedia" in gates


def test_gates_unchanged_without_staged_stores(tmp_path):
    # The mount is conditional: no staged store, no extra gates.
    with _patched_super_init(str(tmp_path)):
        strategy = GenericSearch(config(), str(tmp_path))
    for gates in (strategy.ideation_gates, strategy.implementation_gates):
        assert "bank" not in gates
        assert "idea" not in gates and "code" not in gates
