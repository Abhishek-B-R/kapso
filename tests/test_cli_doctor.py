"""`kapso doctor` — the command surface over the preflight resolver.

The doctor is the first thing a new engineer runs; a check that lies
(false OK, a failure without its fix, or a requirement the config never
asked for) costs exactly the support round-trip the command exists to
prevent. The resolver's own behaviour is pinned in test_preflight.py —
what lives here is the CLI contract: scope, exit code, and --config.
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import kapso.core.preflight as preflight
from kapso.cli.doctor import cmd_doctor
from kapso.kapso import DEFAULT_CONFIG_PATH


def args(verb=None, models=False, config=None, json=False, show_config=False):
    return SimpleNamespace(verb=verb, models=models, config=config, json=json, show_config=show_config)


@pytest.fixture
def full_machine(monkeypatch):
    monkeypatch.setattr(
        preflight.shutil, "which", lambda name, *a, **k: f"/usr/bin/{name}")
    monkeypatch.setattr(preflight, "port_open", lambda *a, **k: True)
    monkeypatch.setattr(preflight, "claude_logged_in", lambda: True)
    monkeypatch.setattr(preflight, "codex_authenticated", lambda: True)
    monkeypatch.setattr(preflight, "bank_origin", lambda home: None)
    for name in ("OPENAI_API_KEY", "GH_TOKEN", "LEEROOPEDIA_API_KEY"):
        monkeypatch.setenv(name, "set")


@pytest.fixture
def bare_machine(monkeypatch):
    monkeypatch.setattr(preflight.shutil, "which", lambda name, *a, **k: None)
    monkeypatch.setattr(preflight, "port_open", lambda *a, **k: False)
    monkeypatch.setattr(preflight, "claude_logged_in", lambda: False)
    monkeypatch.setattr(preflight, "codex_authenticated", lambda: False)
    monkeypatch.setattr(preflight, "bank_origin", lambda home: None)
    for name in ("OPENAI_API_KEY", "GH_TOKEN", "LEEROOPEDIA_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def test_a_ready_machine_passes_and_optional_gaps_never_fail_it(
    full_machine, monkeypatch, capsys,
):
    # An engineer without modal or bentoml must still get a passing doctor
    # for the core loop — optional targets are reported, never required.
    real_which = preflight.shutil.which
    monkeypatch.setattr(
        preflight.shutil, "which",
        lambda name, *a, **k: None if name in ("modal", "bentoml")
        else real_which(name),
    )
    cmd_doctor(args())  # no SystemExit
    out = capsys.readouterr().out
    assert "Required checks passed" in out
    assert "[-- ] deploy target modal" in out


def test_missing_requirements_exit_nonzero_with_a_fix_for_each(
    bare_machine, capsys,
):
    with pytest.raises(SystemExit) as excinfo:
        cmd_doctor(args())
    assert excinfo.value.code == 1
    out = capsys.readouterr().out
    assert "[FAIL] codex CLI" in out
    assert "npm install -g @openai/codex" in out
    # Every failed line is actionable: what wants it, and what to do.
    assert "needed by" in out and "fix" in out
    assert "required check(s) failed" in out


def test_naming_a_verb_narrows_the_report_to_that_verb(full_machine, capsys):
    """`kapso doctor learn` must show learn's requirements only — the
    grading crew needs both CLIs, and the graph stores belong to
    `experience`, so a Neo4j row here would mean the doctor and the verb
    disagree about what a call needs."""
    cmd_doctor(args(verb="learn"))
    out = capsys.readouterr().out
    assert "kapso doctor learn" in out
    assert "codex CLI" in out and "claude CLI" in out
    assert "Neo4j" not in out


def test_bare_doctor_reports_the_union_across_verbs(full_machine, capsys):
    cmd_doctor(args())
    out = capsys.readouterr().out
    # learn's claude+codex crews, experience's stores, deploy's targets.
    for expected in ("codex CLI", "claude CLI", "Neo4j (localhost:7687)",
                     "deploy target docker"):
        assert expected in out


def test_config_flag_drives_the_requirements_including_the_bank_row(
    full_machine, monkeypatch, tmp_path, capsys,
):
    """Regression: the bank rows used to read the PACKAGED config even
    under --config, so `kapso doctor --config mine.yaml` reported someone
    else's bank. Everything the doctor says must come from the config it
    was handed."""
    (tmp_path / "mine.git").mkdir()
    # An override file: the bank's home, and an all-codex build (the
    # default host), so the claude rows must disappear with it.
    path = tmp_path / "mine.yaml"
    path.write_text(yaml.safe_dump({
        "learning": {"bank": {"local_path": str(tmp_path / "mine.git")}},
        "search_strategy": {"params": {"host": "codex"}},
    }))

    cmd_doctor(args(verb="build", config=str(path)))
    out = capsys.readouterr().out
    assert "codex CLI" in out
    assert "claude CLI" not in out

    capsys.readouterr()
    cmd_doctor(args(verb="learn", config=str(path)))
    assert str(tmp_path / "mine.git") in capsys.readouterr().out


def test_models_flag_adds_the_live_tier_and_can_fail_the_doctor(
    full_machine, monkeypatch, capsys,
):
    """A capped model is invisible to every static check — it is precisely
    why the live tier exists (onboarding E2E finding #5), so it has to be
    able to fail the doctor."""
    monkeypatch.setattr(
        preflight, "probe_model_access",
        lambda cli, model: (False, "You've reached your Fable 5 limit"),
    )
    with pytest.raises(SystemExit) as excinfo:
        cmd_doctor(args(verb="learn", models=True))
    assert excinfo.value.code == 1
    out = capsys.readouterr().out
    assert "codex can serve gpt-5.6-sol" in out
    assert "You've reached your Fable 5 limit" in out


def test_without_models_no_live_probe_is_ever_spent(full_machine, monkeypatch):
    """The static tier is free; the live tier costs quota. A plain
    `kapso doctor` must never spend it."""
    monkeypatch.setattr(
        preflight, "probe_model_access",
        lambda cli, model: pytest.fail("live probe fired without --models"),
    )
    cmd_doctor(args())


def test_json_is_the_same_report_as_data(full_machine, bare_machine_rows, capsys):
    """`--json`: the scope, this install's facts and every row, nothing
    else on stdout; the exit code is the text form's."""
    cmd_doctor(args(verb="build", json=True))
    report = json.loads(capsys.readouterr().out)
    assert report["scope"] == "kapso doctor build" and report["ok"] is True
    assert report["python"] == sys.executable and report["version"] and report["kapso"]
    assert report["config_path"] == str(DEFAULT_CONFIG_PATH)
    labels = {row["label"] for row in report["requirements"]}
    assert "claude CLI" in labels and "git" in labels
    assert set(report["requirements"][0]) == {"label", "ok", "fix", "origin", "required", "detail"}

    bare_machine_rows()
    with pytest.raises(SystemExit) as excinfo:
        cmd_doctor(args(verb="build", json=True))
    assert excinfo.value.code == 1
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is False
    failed = [row for row in report["requirements"] if not row["ok"] and row["required"]]
    assert failed and all(row["fix"] for row in failed)


@pytest.fixture
def bare_machine_rows(monkeypatch):
    """The bare machine, applied on demand after the full one."""
    def apply():
        monkeypatch.setattr(preflight.shutil, "which", lambda name, *a, **k: None)
        monkeypatch.setattr(preflight, "port_open", lambda *a, **k: False)
        monkeypatch.setattr(preflight, "claude_logged_in", lambda: False)
        monkeypatch.setattr(preflight, "codex_authenticated", lambda: False)
    return apply
