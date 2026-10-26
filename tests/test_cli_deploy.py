"""`kapso deploy` (docs/plans/redesign/wp5-deploy.md, "The verb"): the
flags to the call, the summary a person reads, the lifecycle through the
record, a bare key refused by name."""

import argparse
from types import SimpleNamespace

import pytest

import kapso.cli.deploy as deploy_module
from kapso.cli.deploy import add_parser, cmd_deploy, lifecycle, pairs, summary
from kapso.deployment.errors import DeployError
from kapso.deployment.record import RUNNING, STOPPED, open_record
from tests.test_software import deployed


def parser():
    root = argparse.ArgumentParser()
    add_parser(root.add_subparsers(dest="command"))
    return root


def arguments(campaign, **overrides):
    fields = dict(
        campaign=str(campaign), target=None, env=None, option=None, coding_agent=None, config=None, harness=None,
        status=False, stop=False, start=False, logs=False, number=None,
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def test_pairs_take_key_equals_value_and_refuse_a_bare_key():
    assert pairs(["A=1", "B=x=y"], "--env") == {"A": "1", "B": "x=y"}
    assert pairs(None, "--option") == {}
    with pytest.raises(DeployError, match="--env takes KEY=VALUE, got 'FOO'"):
        pairs(["FOO"], "--env")


def test_the_target_is_not_an_argparse_choice():
    """A harness target is known once the harness loads; the refusal of an
    unknown name is the engine's one line, not argparse's."""
    args = parser().parse_args(["deploy", "campaign", "--target", "paper-trading", "--option", "schedule=daily", "--env", "A=1"])
    assert args.target == "paper-trading" and args.option == ["schedule=daily"] and args.env == ["A=1"]
    with pytest.raises(SystemExit):
        parser().parse_args(["deploy", "campaign", "--strategy", "local"])


def test_the_flags_reach_the_call_and_the_summary_pins_the_number(tmp_path, monkeypatch, capsys):
    software = deployed(tmp_path, run={"kind": "function", "module": "main", "callable": "predict"})
    seen = {}

    class FakeKapso:
        def __init__(self, config=None):
            seen["config"] = config

        def load_harness(self, reference):
            seen["harness"] = reference

        def deploy(self, solution, **kwargs):
            seen["solution"] = solution
            seen.update(kwargs)
            return software

    monkeypatch.setattr(deploy_module, "Kapso", FakeKapso)
    monkeypatch.setattr(deploy_module.Solution, "open", staticmethod(lambda path: f"solution at {path}"))
    cmd_deploy(arguments(
        software.campaign, target="docker", env=["API_KEY=x"], option=["schedule=daily"], coding_agent="codex",
        config="kapso-config.yaml", harness="./trading",
    ))
    assert seen == {
        "config": "kapso-config.yaml", "harness": "./trading", "solution": f"solution at {software.campaign}",
        "target": "docker", "env": {"API_KEY": "x"}, "options": {"schedule": "daily"}, "coding_agent": "codex",
    }
    out = capsys.readouterr().out
    assert f"DEPLOYED: deployment 1 of {software.campaign}" in out
    assert "  Target:    t\n" in out and "  State:     running (healthy)" in out
    assert "  Run:       function — main.predict in a worker process" in out
    assert '  Proof:     {"x": 1} -> {"y": 2}' in out
    assert f"  Software.open('{software.campaign}', 1).run({{\"x\": 1}})   # from Python" in out
    assert f"  kapso deploy {software.campaign} --stop --number 1" in out
    software.stop()


def test_the_lifecycle_flags_act_through_the_record(tmp_path, capsys):
    first = deployed(tmp_path, run={"kind": "script"}, scripts={"logs.sh": "echo the logs of the first\n"})
    second = deployed(tmp_path, run={"kind": "script"})
    lifecycle(arguments(first.campaign, status=True))
    rows = capsys.readouterr().out.splitlines()
    assert rows[0].startswith("  1  running") and rows[1].startswith("  2  running") and "  t  " in rows[0]
    lifecycle(arguments(first.campaign, stop=True, number=1))
    assert capsys.readouterr().out.strip() == f"stopped deployment 1 of {first.campaign}"
    assert open_record(first.campaign, 1).state == STOPPED and open_record(first.campaign, 2).state == RUNNING
    lifecycle(arguments(first.campaign, logs=True, number=1))
    assert "the logs of the first" in capsys.readouterr().out
    lifecycle(arguments(first.campaign, start=True, number=1))
    assert capsys.readouterr().out.startswith(f"started deployment 1 of {first.campaign}")
    assert open_record(first.campaign, 1).state == RUNNING
    with pytest.raises(DeployError, match="has no deployment"):
        lifecycle(arguments(tmp_path / "nowhere", status=True))


def test_the_summary_says_what_the_session_chose_under_auto(tmp_path):
    software = deployed(tmp_path, run={"kind": "script"}, scripts={"run.py": "import sys\nprint('{}')\n"})
    record = software._record
    record.data.update(target_requested="auto", reasoning="the machine has docker")
    record.write()
    lines = summary(software, str(software.campaign))
    assert "  Target:    t (chosen: the machine has docker)" in lines
    assert "  Run:       script — the target's scripts/run.py" in lines
