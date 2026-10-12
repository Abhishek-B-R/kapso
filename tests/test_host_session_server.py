"""`kapso-mcp`: the bundled gates served to a host session — the engineer's
own coding-agent session — with the configuration derived from where the
session runs, the way get_mcp_config() derives it for a campaign session.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

import kapso.gated_mcp.host_session as host_module
from kapso.execution.memories.repo_memory import RepoMemoryManager
from kapso.gated_mcp.host_session import (
    DEFAULT_GATES,
    INDEX_GATES,
    campaign_directory,
    prepare_host_gates,
    repository_root,
)
from kapso.gated_mcp.presets import resolve_gates
from tests.test_bank_retriever import card_text
from tests.test_update_frame import seed_bank_home


def _config(tmp_path, serving=True):
    return {
        "default_mode": "GENERIC",
        "learning": {
            "serving": {"enabled": serving, "session_root": str(tmp_path / "sessions")},
            "bank": {"local_path": str(tmp_path / "bank-home.git")},
            "retriever": {"probe_budget": 1},
        },
    }


def _prepare(tmp_path, root, *, requested=DEFAULT_GATES, serving=False, kg_index=None,
             mode_config=None):
    return prepare_host_gates(
        root=root,
        requested=list(requested),
        config=_config(tmp_path, serving=serving),
        mode_config=mode_config or {"models": {"embedding": None}},
        kg_index=kg_index,
        family="generic",
        session_dir=tmp_path / "sessions" / "s1",
    )


@pytest.fixture
def codex_on_path(monkeypatch):
    monkeypatch.setattr(host_module.shutil, "which", lambda name: "/usr/bin/codex")


def _git_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


# ------------------------------------------------------------ decisions


def test_an_empty_directory_gets_research_only_and_says_why(tmp_path, codex_on_path):
    root = tmp_path / "project"
    root.mkdir()
    gates = _prepare(tmp_path, root)
    assert gates.enabled == ["research"] and gates.env == {}
    assert [note.split(":")[0] for note in gates.notes] == [
        "repo_memory", "experiment_history", "bank",
    ]


def test_without_the_codex_cli_research_is_off(tmp_path, monkeypatch):
    monkeypatch.setattr(host_module.shutil, "which", lambda name: None)
    gates = _prepare(tmp_path, tmp_path, requested=["research"])
    assert gates.enabled == [] and gates.notes == ["research: off (the codex CLI is not on PATH)"]


def test_repo_memory_rides_when_the_repository_has_one(tmp_path, codex_on_path):
    repo = _git_repo(tmp_path / "repo")
    memory = repo / RepoMemoryManager.MEMORY_REL_PATH
    memory.parent.mkdir(parents=True)
    memory.write_text(json.dumps({"schema_version": 2}))
    inside = repo / "src" / "pkg"
    inside.mkdir(parents=True)

    gates = _prepare(tmp_path, inside, requested=["repo_memory"])
    assert gates.enabled == ["repo_memory"]
    assert gates.env == {"REPO_MEMORY_ROOT": str(repo.resolve())}
    assert repository_root(inside) == repo.resolve()
    assert repository_root(tmp_path / "nowhere-git") == tmp_path / "nowhere-git"


def test_experiment_history_rides_inside_a_campaign_directory(tmp_path, codex_on_path):
    campaign = tmp_path / "campaign"
    (campaign / ".kapso").mkdir(parents=True)
    (campaign / ".kapso" / "experiment_history.json").write_text("[]")
    deep = campaign / "src"
    deep.mkdir()
    assert campaign_directory(deep) == campaign
    assert campaign_directory(tmp_path) is None

    gates = _prepare(
        tmp_path, deep, requested=["experiment_history"],
        mode_config={"models": {"embedding": "text-embedding-3-small"}},
    )
    assert gates.enabled == ["experiment_history"]
    assert gates.env == {
        "EXPERIMENT_HISTORY_PATH": str(campaign / ".kapso" / "experiment_history.json"),
        "EXPERIMENT_EMBEDDING_MODEL": "text-embedding-3-small",
    }


def test_the_bank_is_staged_for_the_session_when_serving_is_on(tmp_path, codex_on_path):
    seed_bank_home(tmp_path, {"a-card": card_text("a-card")})
    gates = _prepare(tmp_path, tmp_path, requested=["bank"], serving=True)
    assert gates.enabled == ["bank"]
    env = gates.env
    session_dir = tmp_path / "sessions" / "s1"
    assert Path(env["KAPSO_BANK_DIR"]) == session_dir / "bank"
    assert (session_dir / "bank" / "insights" / "a-card.md").is_file()
    assert (session_dir / "serving-record.yaml").is_file()
    assert env["KAPSO_SERVING_PULL_LOG"] == str(session_dir / "serving-pull.jsonl")
    assert env["KAPSO_TASK_FAMILY"] == "generic" and env["KAPSO_PROBE_BUDGET"] == "1"
    head = subprocess.run(
        ["git", "-C", env["KAPSO_BANK_DIR"], "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    assert env["KAPSO_BANK_HEAD"] == head
    # The bundled server resolves every served gate from exactly this env.
    resolution = resolve_gates(gates.enabled, policy="error", env={**os.environ, **env})
    assert resolution.unavailable_gates == ()


def test_the_bank_stays_off_while_serving_is_off_or_there_is_no_home(tmp_path, codex_on_path):
    seed_bank_home(tmp_path, {"a-card": card_text("a-card")})
    off = _prepare(tmp_path, tmp_path, requested=["bank"], serving=False)
    assert off.enabled == [] and "learning.serving.enabled" in off.notes[0]
    no_home = prepare_host_gates(
        root=tmp_path, requested=["bank"],
        config={**_config(tmp_path, serving=True),
                "learning": {**_config(tmp_path)["learning"],
                             "serving": {"enabled": True, "session_root": str(tmp_path)},
                             "bank": {"local_path": str(tmp_path / "absent.git")},
                             "retriever": {"probe_budget": 1}}},
        mode_config={}, kg_index=None, family="generic", session_dir=tmp_path / "s",
    )
    assert no_home.enabled == [] and "no bank home" in no_home.notes[0]


def test_an_index_adds_the_search_gates(tmp_path, codex_on_path):
    index = tmp_path / "ml.index"
    index.write_text("{}")
    gates = _prepare(tmp_path, tmp_path, requested=list(INDEX_GATES), kg_index=str(index))
    assert gates.enabled == ["idea", "code"]
    assert gates.env == {"KG_INDEX_PATH": str(index.resolve())}
    without = _prepare(tmp_path, tmp_path, requested=list(INDEX_GATES))
    assert without.enabled == [] and without.notes == ["idea: off (no --kg-index)", "code: off (no --kg-index)"]


def test_unknown_and_campaign_only_gates_are_configuration_errors(tmp_path, codex_on_path):
    with pytest.raises(ValueError, match="unknown gate"):
        _prepare(tmp_path, tmp_path, requested=["telepathy"])
    with pytest.raises(ValueError, match="campaign-only"):
        _prepare(tmp_path, tmp_path, requested=["inbox"])


def test_duplicates_are_dropped_and_order_kept(tmp_path, codex_on_path):
    gates = _prepare(tmp_path, tmp_path, requested=["research", "research"])
    assert gates.enabled == ["research"]


# ------------------------------------------------------------------ main


def test_main_serves_what_it_can_and_exits_when_nothing_is_left(tmp_path, monkeypatch, capsys):
    served = {}

    async def fake_server():
        served.update(gates=os.environ["MCP_ENABLED_GATES"],
                      policy=os.environ["MCP_GATE_FAILURE_POLICY"])

    monkeypatch.setattr(host_module, "run_server", fake_server)
    monkeypatch.setattr(host_module.shutil, "which", lambda name: "/usr/bin/codex")
    monkeypatch.chdir(tmp_path)
    for name in ("MCP_ENABLED_GATES", "MCP_GATE_FAILURE_POLICY"):
        monkeypatch.delenv(name, raising=False)

    host_module.main([])
    assert served == {"gates": "research", "policy": "error"}
    err = capsys.readouterr().err
    assert "kapso-mcp: serving research for" in err and "bank: off" in err

    monkeypatch.setattr(host_module.shutil, "which", lambda name: None)
    with pytest.raises(SystemExit) as stop:
        host_module.main(["--gates", "research"])
    assert stop.value.code == 1
    assert "nothing to serve here" in capsys.readouterr().err
