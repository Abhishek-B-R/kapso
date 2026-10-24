"""`kapso build`: every flag the parser defines is accounted for and
reaches where it belongs (the facade call, the budget, the constructor,
the brief, or the detach handling), so a flag that stops reaching the
facade fails here; a brief file arrives as a `Brief`; a resume without a
brief passes none; and the errors a person can hit say what to do."""

import argparse
import sys
from unittest.mock import Mock

import pytest

import kapso.cli.build as build_cli
from kapso.cli import main
from kapso.handles import Brief, Budget

FACADE_KWARGS = {"evaluation", "data", "repo", "output", "resume", "mode", "coding_agent"}
BUDGET_FIELDS = {"budget_minutes": "minutes", "budget_experiments": "experiments",
                 "budget_usd": "usd", "budget_reserve_minutes": "reserve_minutes"}
CONSTRUCTOR = {"config", "kg_index"}
BRIEF = {"goal", "goal_file", "brief"}
DETACH = {"detach", "log"}


def _parser_dests():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    build_cli.add_parser(subparsers)
    return {action.dest for action in subparsers.choices["build"]._actions if action.dest != "help"}


def _mock_facade(monkeypatch):
    facade = Mock()
    constructor = Mock(return_value=facade)
    monkeypatch.setattr(build_cli, "Kapso", constructor)
    monkeypatch.setattr(build_cli, "_print_build_summary", lambda _: None)
    return constructor, facade


def _run(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["kapso", "build", *argv])
    main()


def test_every_flag_of_the_parser_is_accounted_for():
    assert _parser_dests() == FACADE_KWARGS | set(BUDGET_FIELDS) | CONSTRUCTOR | BRIEF | DETACH


def test_every_flag_reaches_where_it_belongs(monkeypatch):
    constructor, facade = _mock_facade(monkeypatch)
    _run(
        monkeypatch, "--goal", "g", "--evaluation", "ev", "--data", "da", "--repo", "re",
        "--output", "out", "--budget-experiments", "3", "--budget-minutes", "30", "--budget-usd", "5",
        "--budget-reserve-minutes", "2", "--resume", "--mode", "MINIMAL", "--coding-agent", "codex",
        "--config", "c.yaml", "--kg-index", "k.index",
    )
    assert constructor.call_args.kwargs == {"config": "c.yaml", "kg_index": "k.index"}
    args, kwargs = facade.build.call_args
    assert args == ("g",)
    assert kwargs == {
        "evaluation": "ev", "data": "da", "repo": "re", "output": "out",
        "budget": Budget(minutes=30, experiments=3, usd=5, reserve_minutes=2),
        "resume": True, "mode": "MINIMAL", "coding_agent": "codex",
    }


def test_a_brief_file_reaches_build_as_a_brief(monkeypatch, tmp_path):
    path = tmp_path / "kapso-brief.md"
    path.write_text("Objective    Raise AUC above 0.85\nRules\n  - no peeking\nBudget       minutes=5\n")
    _, facade = _mock_facade(monkeypatch)
    _run(monkeypatch, "--brief", str(path), "--output", "out")
    assert facade.build.call_args.args == (Brief.read(path),)
    assert facade.build.call_args.kwargs["budget"] == Budget()   # the brief's budget applies in the facade


def test_a_goal_file_is_plain_text(monkeypatch, tmp_path):
    path = tmp_path / "problem.txt"
    path.write_text("Raise AUC\nTarget: 0.9, by any means\n")
    _, facade = _mock_facade(monkeypatch)
    _run(monkeypatch, "--goal-file", str(path), "--output", "out")
    assert facade.build.call_args.args == ("Raise AUC\nTarget: 0.9, by any means\n",)


def test_a_resume_without_a_brief_passes_none(monkeypatch):
    _, facade = _mock_facade(monkeypatch)
    _run(monkeypatch, "--output", "out", "--resume")
    assert facade.build.call_args.args == (None,)
    assert facade.build.call_args.kwargs["resume"] is True


def test_no_brief_and_no_resume_exits_one(monkeypatch, capsys):
    _mock_facade(monkeypatch)
    with pytest.raises(SystemExit) as stop:
        _run(monkeypatch, "--output", "out")
    assert stop.value.code == 1
    assert "--goal, --goal-file or --brief is required" in capsys.readouterr().out


def test_a_missing_brief_exits_one(monkeypatch, capsys, tmp_path):
    _mock_facade(monkeypatch)
    with pytest.raises(SystemExit) as stop:
        _run(monkeypatch, "--brief", str(tmp_path / "none.md"), "--output", "out")
    assert stop.value.code == 1
    assert "brief not found" in capsys.readouterr().out


def test_the_brief_forms_exclude_each_other(monkeypatch, capsys, tmp_path):
    path = tmp_path / "kapso-brief.md"
    path.write_text("Objective a\n")
    _mock_facade(monkeypatch)
    with pytest.raises(SystemExit) as stop:
        _run(monkeypatch, "--goal", "g", "--brief", str(path))
    assert stop.value.code == 2
    assert "not allowed with" in capsys.readouterr().err
