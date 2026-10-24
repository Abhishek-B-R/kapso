"""The public commands pass --config through to the Kapso facade."""

import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import kapso.cli.build as build_cli
import kapso.cli.research as research_cli
from kapso.cli import main

VERB_MODULES = {"build": build_cli, "research": research_cli}


@pytest.mark.parametrize(
    "verb,argument",
    [
        ("build", "--goal"),
        ("research", "--objective"),
    ],
)
@pytest.mark.parametrize("config_path", [None, "/tmp/kapso-config.yaml"])
def test_command_passes_config_to_facade(
    monkeypatch, verb, argument, config_path
):
    facade = Mock()
    facade.research.return_value = SimpleNamespace()
    constructor = Mock(return_value=facade)
    monkeypatch.setattr(VERB_MODULES[verb], "Kapso", constructor)
    monkeypatch.setattr(build_cli, "_print_build_summary", lambda _: None)
    argv = ["kapso", verb, argument, "test objective"]
    if config_path:
        argv.extend(["--config", config_path])
    monkeypatch.setattr(sys, "argv", argv)
    main()
    assert constructor.call_args.kwargs["config"] == config_path
    getattr(facade, verb).assert_called_once()
