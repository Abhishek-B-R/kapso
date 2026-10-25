"""`kapso learn <campaign>` is the verb's plain form (WP2's hand-over to
the experience package): it learns through the facade, loading the harness
`--harness` names first; the learning system's own nine tools live under
`kapso learn dev`, with their flags; `init-bank` is gone (`kapso
experience add mine`)."""

import argparse
import sys
from types import SimpleNamespace

import pytest

import kapso.cli.learn as learn_cli
from kapso.cli import main


def _run(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["kapso", "learn", *argv])
    main()


def _dev_subparsers():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    learn_cli.add_parser(subparsers)
    learn = subparsers.choices["learn"]
    forms = next(a for a in learn._actions if isinstance(a, argparse._SubParsersAction))
    dev = forms.choices["dev"]
    dev_sub = next(a for a in dev._actions if isinstance(a, argparse._SubParsersAction))
    return sorted(forms.choices), {name: {a.dest for a in p._actions if a.dest != "help"} for name, p in dev_sub.choices.items()}


def test_the_plain_form_is_the_campaign_and_the_tools_sit_under_dev():
    assert learn_cli.normalize_argv(["learn", "./campaign"]) == ["learn", "campaign", "./campaign"]
    assert learn_cli.normalize_argv(["learn", "./campaign", "--harness", "./h"]) == ["learn", "campaign", "./campaign", "--harness", "./h"]
    assert learn_cli.normalize_argv(["learn", "dev", "mine", "--all"]) == ["learn", "dev", "mine", "--all"]
    assert learn_cli.normalize_argv(["learn", "--help"]) == ["learn", "--help"]
    assert learn_cli.normalize_argv(["build", "./campaign"]) == ["build", "./campaign"]
    forms, dev = _dev_subparsers()
    assert forms == ["campaign", "dev"]
    assert set(dev) == {"import", "mine", "grade", "update", "develop", "codify", "ingest", "gauntlet", "behave"}
    assert "init-bank" not in dev
    assert dev["import"] == {"subset", "archive", "id", "config", "no_upload"}
    assert dev["grade"] == {"bank", "bank_head", "split", "learner_version", "trajectory", "config"}


def test_learning_from_a_campaign_goes_through_the_facade(monkeypatch, capsys):
    calls = []

    class FakeKapso:
        def __init__(self, config=None):
            calls.append(("init", config))

        def load_harness(self, ref):
            calls.append(("harness", ref))

        def learn(self, source):
            calls.append(("learn", source))
            return SimpleNamespace(explain=lambda: "Lesson from: x\nBank: a -> b (admitted: True)")

    monkeypatch.setattr(learn_cli, "Kapso", FakeKapso)
    _run(monkeypatch, "./campaign")
    assert calls == [("init", None), ("learn", "./campaign")]
    assert capsys.readouterr().out.startswith("Lesson from: x")
    calls.clear()
    _run(monkeypatch, "./campaign", "--harness", "./harness", "--config", "c.yaml")
    assert calls == [("init", "c.yaml"), ("harness", "./harness"), ("learn", "./campaign")]


def test_a_dev_tool_still_refuses_a_bad_combination(monkeypatch, capsys):
    monkeypatch.setattr(learn_cli, "load_config", lambda path: {"learning": {}})
    monkeypatch.setattr(learn_cli, "MiningFrame", SimpleNamespace(from_config=lambda config: SimpleNamespace()))
    with pytest.raises(SystemExit) as stop:
        _run(monkeypatch, "dev", "mine")
    assert stop.value.code == 1
    assert "exactly one of --trajectory or --all" in capsys.readouterr().out
