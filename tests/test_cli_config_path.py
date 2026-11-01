"""The public commands pass --config through to the Kapso facade."""

import sys
from unittest.mock import Mock

import pytest

import kapso.cli.build as build_cli
import kapso.cli.experience as experience_cli
from kapso.cli import main

VERB_MODULES = {"build": build_cli, "experience": experience_cli}


@pytest.mark.parametrize(
    "verb,argv_tail,method",
    [
        ("build", ["--goal", "test objective"], "build"),
        ("experience", ["add", "--repo", "https://github.com/org/x", "--name", "org-x"], "add_experience"),
    ],
)
@pytest.mark.parametrize("config_path", [None, "/tmp/kapso-config.yaml"])
def test_command_passes_config_to_facade(
    monkeypatch, verb, argv_tail, method, config_path
):
    facade = Mock()
    facade.add_experience.return_value = "org-x"
    constructor = Mock(return_value=facade)
    monkeypatch.setattr(VERB_MODULES[verb], "Kapso", constructor)
    monkeypatch.setattr(build_cli, "_print_build_summary", lambda _: None)
    argv = ["kapso", verb, *argv_tail]
    if config_path:
        argv.extend(["--config", config_path])
    monkeypatch.setattr(sys, "argv", argv)
    main()
    assert constructor.call_args.kwargs["config"] == config_path
    getattr(facade, method).assert_called_once()
