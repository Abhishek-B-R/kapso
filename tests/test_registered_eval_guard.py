"""Tests for the registered-evaluation teardown guard (relbench Issue 2).

Contract: runs BEFORE finalize_session's rmtree; when the session output
carries no manifest, it waits for a live grader (bounded) and recovers the
manifest line from the durable run archive the grader wrote outside the
workspace.
"""

import os
import time

import kapso.execution.search_strategies.generic.strategy as strategy_module
from kapso.execution.evaluation_archive_sandbox import write_selection_label
from kapso.execution.evaluation_maintainer.maintainer import MANIFEST_MARKER
from kapso.execution.search_strategies.generic.strategy import GenericSearch


def make_stub(tmp_path, archive_glob):
    s = GenericSearch.__new__(GenericSearch)
    s.registered_evaluation_command = (
        "python kapso_evaluation/kapso_eval.py --fidelity full"
    )
    s.registered_evaluation_archive_glob = archive_glob
    s.implementation_timeout = 10
    s.budget_snapshot = None
    s.budget_snapshot_monotonic = None
    s._last_session_started_ts = time.time() - 3600
    return s


def _write_archive(tmp_path, name, line, session="candidate"):
    runs = tmp_path / "work" / "runs"
    run_dir = runs / name
    (run_dir / "private").mkdir(parents=True)
    write_selection_label(run_dir, session=session, evaluator_id="evaluator")
    (run_dir / "manifest.txt").write_text(line + "\n")
    return runs


def test_recovers_manifest_from_durable_archive(tmp_path):
    line = MANIFEST_MARKER + ' {"fidelity": "full", "score": 0.2334}'
    _write_archive(tmp_path, "run_0001", line)
    stub = make_stub(tmp_path, str(tmp_path / "work" / "runs"))

    recovered = stub._await_registered_evaluation("session died, no manifest", "candidate")

    assert recovered == line


def test_manifest_already_in_output_short_circuits(tmp_path):
    _write_archive(tmp_path, "run_0001", MANIFEST_MARKER + " {}")
    stub = make_stub(tmp_path, str(tmp_path / "work" / "runs"))

    out = MANIFEST_MARKER + ' {"score": 0.5}'
    assert stub._await_registered_evaluation(out, "candidate") is None


def test_stale_archives_are_ignored(tmp_path):
    line = MANIFEST_MARKER + ' {"score": 0.9}'
    runs = _write_archive(tmp_path, "run_0001", line)
    # Archive predates the session: must not be recovered.
    old = time.time() - 7200
    os.utime(runs / "run_0001", (old, old))
    stub = make_stub(tmp_path, str(runs))
    stub._last_session_started_ts = time.time() - 60

    assert stub._await_registered_evaluation("no manifest", "candidate") is None


def test_no_registered_command_is_a_noop(tmp_path):
    stub = make_stub(tmp_path, None)
    stub.registered_evaluation_command = None
    assert stub._await_registered_evaluation("anything", "candidate") is None


def test_a_lane_recovers_only_its_own_sessions_archive(tmp_path, monkeypatch):
    """Parallel lanes share one archive root: a lane whose session died
    without its manifest must not take a sibling lane's score of record."""
    sibling = MANIFEST_MARKER + ' {"fidelity": "full", "score": 0.9}'
    _write_archive(tmp_path, "run_0001", sibling, session="generic_exp_1")
    stub = make_stub(tmp_path, str(tmp_path / "work" / "runs"))
    stub.__dict__.update(
        expansion_lane_env=None, workspace=None, llm=None,
        registered_evaluation_manifest=None, implementation_gates=[],
        gate_failure_policy="skip", bank_serving=None, kg_index_path=None,
        implementation_cli="claude_code", implementation_model="m",
        implementation_fallback_model=None, implementation_web=False,
        _claude_auth_settings={}, env_strip=[], env_defaults={},
        session_effort=None, previous_errors=[], recent_error_count=3,
        node_expansion_value=2,
    )

    def died_without_manifest(**kwargs):
        recovered = kwargs["await_registered_evaluation"]("session died")
        return "session died", {}, recovered, None, "provider kill"

    monkeypatch.setattr(strategy_module, "run_implementation", died_without_manifest)

    def recovered_for(branch_name):
        return stub._implement(
            solution="s", problem="p", branch_name=branch_name,
        )[2]

    assert recovered_for("generic_exp_0") is None
    assert recovered_for("generic_exp_1") == sibling
