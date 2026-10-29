"""The MLE-bench integration on build() (docs/plans/redesign/wp8-harness-ports.md,
change 12): the Brief from the competition's facts, and the provided grader's
contract on a fixture candidate (the debug run as the gate, the held-out
score read from the tag and oriented, the violations that refuse a score)."""

import importlib.util
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("mlebench")

from kapso.handles import Brief
from benchmarks.mle.context import build_brief

REPO_ROOT = Path(__file__).parents[1]
GRADER = REPO_ROOT / "benchmarks" / "mle" / "data" / "generic_eval" / "grader.py"
COMPUTE = {"has_gpu": True, "gpu_name": "NVIDIA H100 80GB HBM3, 81559 MiB", "num_cpus": 30, "mem_gb": 300}


def fake_competition():
    return SimpleNamespace(
        id="spooky-author-identification", name="Spooky Author Identification", competition_type="simple",
        description="# Overview\n\nWho wrote each sentence?\n\n## Evaluation\n\nMulti-class log loss.",
    )


class TestBrief:
    def brief(self, tmp_path, higher=False):
        data_dir = tmp_path / "data"
        (data_dir / "images").mkdir(parents=True)
        for index in range(7):
            (data_dir / f"part{index}.csv").write_text("a,b\n1,2\n")
        (data_dir / "images" / "x.png").write_bytes(b"png")
        return build_brief(fake_competition(), data_dir, higher, 1200, 28800, 1e9 if not higher else 0.0,
                           ["torchaudio", "faiss"], tmp_path / "shared", compute=COMPUTE)

    def test_the_objective_holds_the_description_the_layout_and_the_paths(self, tmp_path):
        brief = self.brief(tmp_path)
        assert "Who wrote each sentence?" in brief.objective and "## Evaluation" in brief.objective
        assert f"Data directory: {tmp_path / 'data'}" in brief.objective
        assert "... (2 more files)" in brief.objective and "images/" in brief.objective
        assert str(tmp_path / "shared") in brief.objective and "NVIDIA H100" in brief.objective

    def test_measured_by_and_the_rules_carry_the_held_out_protocol_and_the_contract(self, tmp_path):
        brief = self.brief(tmp_path)
        assert brief.measured_by.startswith("the held-out score your program prints")
        assert "lower is better" in brief.measured_by and "negated" in brief.measured_by
        assert any("ten percent" in rule and "<score>" in rule for rule in brief.rules)
        assert any("final_submission.csv" in rule and "committed" in rule for rule in brief.rules)
        assert any("20 minutes" in rule and "8.0 hours" in rule for rule in brief.rules)
        assert any("torchaudio, faiss" in rule for rule in brief.rules)
        assert "floor score 1000000000.0" in brief.baseline and "medal" in brief.target

    def test_no_standing_guidance_rides_in_the_brief(self, tmp_path):
        brief = self.brief(tmp_path, higher=True)
        text = brief.render()
        for phrase in ("early stopping", "MINI TRAINING", "STAGE", "LightGB", "never train a heavy model"):
            assert phrase not in text, phrase
        assert "floor score 0.0" in brief.baseline and "as it is" in brief.measured_by
        assert Brief.parse(text) == brief


def load_grader(repo: Path, higher_is_better: bool, monkeypatch):
    """The grader as the maintainer stages it: under the candidate's
    kapso_evaluation/ with the task's settings beside it, the competition's
    validator and registry stubbed."""
    suite = repo / "kapso_evaluation"
    suite.mkdir(parents=True)
    shutil.copy2(GRADER, suite / "grader.py")
    (suite / "task.json").write_text(json.dumps({
        "competition_id": "spooky-author-identification", "higher_is_better": higher_is_better,
        "data_dir": str(repo / "data"), "full_timeout": 60, "debug_timeout": 60, "floor_score": 1e9,
    }))
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    spec = importlib.util.spec_from_file_location("mle_grader", suite / "grader.py")
    grader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(grader)
    monkeypatch.setattr(grader.registry, "get_competition", lambda competition_id: object())
    monkeypatch.setattr(grader, "validate_submission", lambda path, competition: (True, ""))
    return grader


def manifest_of(out: str) -> dict:
    line = [line for line in out.splitlines() if line.startswith("KAPSO_EVAL_MANIFEST")][-1]
    return json.loads(line.split(" ", 1)[1])


CANDIDATE = (
    "import sys\n"
    "open('run.log', 'a').write(' '.join(sys.argv[1:]) + '\\n')\n"
    "open('final_submission.csv', 'w').write('id,EAP,HPL,MWS\\nid1,0.4,0.3,0.3\\n')\n"
    "print('<score>0.62</score>' if '--debug' in sys.argv else '<score>0.42</score>')\n"
)


class TestProvidedGrader:
    def test_fast_runs_the_debug_mode_and_orients_the_reported_score(self, tmp_path, monkeypatch, capsys):
        repo = tmp_path / "repo"
        grader = load_grader(repo, higher_is_better=False, monkeypatch=monkeypatch)
        (repo / "main.py").write_text(CANDIDATE)
        monkeypatch.setattr(sys, "argv", ["grader.py", "--fidelity", "fast"])
        grader.main()
        manifest = manifest_of(capsys.readouterr().out)
        assert manifest["fidelity"] == "fast" and manifest["raw_score"] == 0.62
        assert manifest["score"] == -0.62 and manifest["higher_is_better"] is False
        assert (repo / "run.log").read_text() == "--debug\n"

    def test_full_runs_the_debug_gate_then_the_full_mode_and_reads_the_last_score(self, tmp_path, monkeypatch, capsys):
        repo = tmp_path / "repo"
        grader = load_grader(repo, higher_is_better=True, monkeypatch=monkeypatch)
        (repo / "main.py").write_text(CANDIDATE)
        monkeypatch.setattr(sys, "argv", ["grader.py", "--fidelity", "full"])
        grader.main()
        manifest = manifest_of(capsys.readouterr().out)
        assert manifest["score"] == manifest["raw_score"] == 0.42
        assert (repo / "run.log").read_text() == "--debug\n\n"

    @pytest.mark.parametrize("candidate, problem", [
        ("open('final_submission.csv', 'w').write('id\\n')\n", "no <score>"),
        ("print('<score>0.5</score>')\n", "was not written"),
    ])
    def test_a_run_without_a_score_or_a_file_is_a_contract_violation(self, tmp_path, monkeypatch, capsys, candidate, problem):
        repo = tmp_path / "repo"
        grader = load_grader(repo, higher_is_better=True, monkeypatch=monkeypatch)
        (repo / "main.py").write_text(candidate)
        monkeypatch.setattr(sys, "argv", ["grader.py", "--fidelity", "fast"])
        with pytest.raises(SystemExit) as stopped:
            grader.main()
        assert stopped.value.code == 6 and problem in capsys.readouterr().out

    def test_the_competitions_validator_refuses_a_bad_file(self, tmp_path, monkeypatch, capsys):
        repo = tmp_path / "repo"
        grader = load_grader(repo, higher_is_better=True, monkeypatch=monkeypatch)
        (repo / "main.py").write_text(CANDIDATE)
        monkeypatch.setattr(grader, "validate_submission", lambda path, competition: (False, "wrong columns"))
        monkeypatch.setattr(sys, "argv", ["grader.py", "--fidelity", "fast"])
        with pytest.raises(SystemExit) as stopped:
            grader.main()
        assert stopped.value.code == 6 and "wrong columns" in capsys.readouterr().out

    def test_the_seeded_baseline_satisfies_the_grader(self, tmp_path, monkeypatch, capsys):
        """The maintainer's calibration runs the baseline: the sample
        submission unchanged and the floor score."""
        repo = tmp_path / "repo"
        grader = load_grader(repo, higher_is_better=False, monkeypatch=monkeypatch)
        (repo / "data").mkdir()
        (repo / "data" / "sample_submission.csv").write_text("id,EAP,HPL,MWS\nid1,0.4,0.3,0.3\n")
        shutil.copy2(REPO_ROOT / "benchmarks" / "mle" / "data" / "generic_baseline" / "main.py", repo / "main.py")
        monkeypatch.setattr(sys, "argv", ["grader.py", "--fidelity", "fast"])
        grader.main()
        manifest = manifest_of(capsys.readouterr().out)
        assert manifest["raw_score"] == 1e9 and manifest["score"] == -1e9
        assert (repo / "final_submission.csv").read_text() == "id,EAP,HPL,MWS\nid1,0.4,0.3,0.3\n"
