"""Shared pytest wiring.

Live suites — tests that spawn real coding-agent sessions and spend real
subscription quota — are skipped unless --run-live is passed, so a plain
`pytest tests/...` stays safe and free for contributors (onboarding E2E
finding #4: an unmarked live suite hung a gate run for 10 minutes while
silently burning quota)."""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-live", action="store_true", default=False,
        help="run live suites that spawn real claude/codex sessions",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live: spawns real coding-agent sessions (skipped without --run-live)",
    )
    # Used by test_relbench_integration, which warned on every run while
    # nothing registered it.
    config.addinivalue_line(
        "markers",
        "integration: needs external infrastructure such as Weaviate or Neo4j",
    )
    config.addinivalue_line(
        "markers",
        "requirements_check: the harness requirements check runs for real against python3 on PATH",
    )
    config.addinivalue_line(
        "markers",
        "preflight: the verb's preflight runs for real against the CLIs on PATH",
    )


@pytest.fixture(autouse=True)
def harness_requirements_are_not_the_machines(request, monkeypatch):
    """A harness's Python requirements are checked against `python3` on
    PATH, which the test machine need not satisfy (the trading example
    wants mcp, pandas and pyarrow); a test about anything else loads the
    example without that machine-dependent need. A test about the check
    itself carries the `requirements_check` marker and gets the real one."""
    if request.node.get_closest_marker("requirements_check") is None:
        monkeypatch.setattr("kapso.harness.check._Checker.requirements", lambda self, file: None)


@pytest.fixture(autouse=True)
def the_preflight_is_not_the_machines(request, monkeypatch):
    """A verb's preflight reads the effective config's hosts against the
    CLIs on PATH, which the test machine need not have (CI installs Claude
    Code alone; the packaged inference runs on Codex). A test about
    anything else runs its verb without the preflight; the preflight's own
    tests drive the resolver directly, and a test of a verb's preflight
    carries the `preflight` marker and gets the real one."""
    if request.node.get_closest_marker("preflight") is None:
        monkeypatch.setattr("kapso.kapso.run_preflight", lambda *args, **kwargs: None)


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-live"):
        return
    skip_live = pytest.mark.skip(reason="live suite — pass --run-live to run")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
