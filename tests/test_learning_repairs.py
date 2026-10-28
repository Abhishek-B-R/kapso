"""The learn completes on the two cases the plugin round found
(docs/plans/redesign/wp9-semantic-suite.md, change 1): a flow file whose
unquoted reference carries a colon in its fragment is a finding for the
repair round, not a parse error the round never sees; a role session
that writes no artifact is run once more and then fails loud with what
each session said."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from kapso.learning.graders.frame import GradingFrame
from kapso.learning.mining import _split_frontmatter, _unquoted_colon_fragments

FLOW = (
    "---\nflow: it-1/flow-1\nstatus: judged\nsources:\n"
    "  idea: runs/run_0001/stream.jsonl#\"rows: 3000  seconds: 11.4\"\n---\nbody\n"
)


def test_an_unquoted_reference_with_a_colon_in_its_fragment_is_a_finding_not_a_parse_error():
    assert _unquoted_colon_fragments(FLOW) == [
        "frontmatter line 4: the reference `runs/run_0001/stream.jsonl#\"rows: 3000  seconds: 11.4\"` is unquoted and its "
        "fragment holds a colon; quote the whole reference"
    ]
    with pytest.raises(yaml.YAMLError):
        _split_frontmatter(FLOW)
    quoted = FLOW.replace("idea: runs", "idea: 'runs").replace("11.4\"\n", "11.4\"'\n")
    assert _unquoted_colon_fragments(quoted) == []
    assert _split_frontmatter(quoted)["sources"]["idea"].endswith("11.4\"")
    # A fragment without a colon, or a colon with no whitespace after it, is YAML's to read.
    plain = FLOW.replace("#\"rows: 3000  seconds: 11.4\"", "#L12-L30")
    assert _unquoted_colon_fragments(plain) == [] and _split_frontmatter(plain)["sources"]["idea"].endswith("#L12-L30")


def test_a_role_session_that_writes_no_artifact_is_run_once_more_then_fails_loud_with_what_it_said(tmp_path):
    frame = GradingFrame.__new__(GradingFrame)
    calls = []

    def run_role(role, prompt, cwd):
        calls.append(role)
        return SimpleNamespace(output="", error="Codex CLI exited with code 1: Quota exceeded", refused=False, success=False)

    frame._run_role = run_role
    with pytest.raises(FileNotFoundError) as raised:
        frame._run_role_for_artifact("report_writer", "write the report", tmp_path, tmp_path / "report.md")
    assert calls == ["report_writer", "report_writer"]
    assert str(raised.value) == (
        f"report_writer produced no report.md at {tmp_path / 'report.md'} after 2 session(s): "
        "error: Codex CLI exited with code 1: Quota exceeded; error: Codex CLI exited with code 1: Quota exceeded"
    )
    # A session that wrote the file the second time is the retry working.
    wrote = []

    def run_role_then_write(role, prompt, cwd):
        wrote.append(role)
        if len(wrote) == 2:
            (tmp_path / "verdict.yaml").write_text("decision: accept\n")
        return SimpleNamespace(output="", error=None, refused=True, success=False)

    frame._run_role = run_role_then_write
    frame._run_role_for_artifact("assessor", "assess", tmp_path, tmp_path / "verdict.yaml")
    assert wrote == ["assessor", "assessor"]


def test_a_session_that_ends_without_the_artifact_has_its_last_words_in_the_line(tmp_path):
    # S6 on a fresh machine (2026-10-28): both report_writer sessions ended
    # saying the workspace rejected writes, and the line said only "ended
    # without writing it" — the one fact that explained the failure was lost.
    frame = GradingFrame.__new__(GradingFrame)
    frame._run_role = lambda role, prompt, cwd: SimpleNamespace(
        output="Unable to create report.md:\n the workspace rejected writes due to a sandbox permission error.", error=None, refused=False, success=True,
    )
    with pytest.raises(FileNotFoundError) as raised:
        frame._run_role_for_artifact("report_writer", "write the report", tmp_path, tmp_path / "report.md")
    said = "ended without writing it, saying: ...Unable to create report.md: the workspace rejected writes due to a sandbox permission error."
    assert str(raised.value).count(said) == 2
    frame._run_role = lambda role, prompt, cwd: SimpleNamespace(output="", error=None, refused=False, success=True)
    with pytest.raises(FileNotFoundError, match="saying nothing; ended without writing it, saying nothing"):
        frame._run_role_for_artifact("report_writer", "write the report", tmp_path, tmp_path / "report.md")
