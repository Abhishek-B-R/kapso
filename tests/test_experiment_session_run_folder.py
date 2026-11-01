"""The engine's run folder is committed whatever the candidate's ignore
rules say (wp8-harness-ports.md, what the arms found): a session that adds
`output_data_<id>/` to the repository's .gitignore, as the ALE arm's
implementation session did, must not lose the run data the record and the
evaluation are built from."""
import git

from kapso.execution.experiment_workspace.experiment_session import ExperimentSession


def test_an_ignore_rule_does_not_keep_the_run_folder_out_of_the_record(tmp_path):
    repo = git.Repo.init(tmp_path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "test")
        config.set_value("user", "email", "test@example.com")
    (tmp_path / ".gitignore").write_text("output_data_generic_exp_1/\n", encoding="utf-8")
    repo.git.add(".gitignore")
    repo.git.commit("-m", "the session's ignore rules")
    run_dir = tmp_path / "output_data_generic_exp_1"
    run_dir.mkdir()
    (run_dir / "scores.json").write_text("{}", encoding="utf-8")

    session = object.__new__(ExperimentSession)
    session.repo = repo
    session.commit_folder(str(run_dir))

    assert "output_data_generic_exp_1/scores.json" in repo.git.ls_files().split("\n")
    assert repo.head.commit.message.strip() == "chore: commit run data"
