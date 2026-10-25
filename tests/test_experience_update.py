"""`update` and `remove` (wp3-experience.md, change 15): loading never
pulls, so `update_experience` is the network step — `mine` takes its
remote's main, a bank you read at a moving reference is fetched again, a
pinned commit never moves, and `None` updates every bank; `remove`
deletes a fetched bank's clone and record, or an index with its backend
namespace, and refuses what is not the store's to remove."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from kapso.experience import ExperienceError, ExperienceReferenceError, ExperienceStore, IndexRecord
from tests.handles_support import facade, git
from tests.test_experience_reference import bank_home, settings_for


def _kapso(tmp_path):
    kapso = facade()
    kapso._experience_settings = settings_for(tmp_path)
    return kapso


def _shared_mine(tmp_path):
    """`mine` with a remote whose main is one commit ahead."""
    home = bank_home(tmp_path, cards=1)
    remote = tmp_path / "team.git"
    git(tmp_path, "clone", "-q", "--bare", str(home), str(remote))
    work = tmp_path / "work-team"
    git(tmp_path, "clone", "-q", str(remote), str(work))
    (work / "insights" / "from-the-team.md").write_text("# a colleague's card\n")
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "the team's card")
    git(work, "push", "-q", "origin", "main")
    git(home, "remote", "add", "origin", str(remote))
    return home, git(work, "rev-parse", "main")


def _fetched_bank(tmp_path, kapso):
    """A bank you read, fetched once by its git reference on a branch."""
    origin = bank_home(tmp_path, name="acme-bank.git", cards=1)
    reference = f"git+file://{origin}@main"
    kapso.load_experience(reference)
    return origin, reference


def test_update_pulls_mine_and_refetches_a_moving_reference(tmp_path, capsys):
    kapso = _kapso(tmp_path)
    home, ahead = _shared_mine(tmp_path)
    origin, reference = _fetched_bank(tmp_path, kapso)
    first = kapso.experience[-1].head
    # the remote of the bank you read moves on
    work = tmp_path / "work-acme"
    git(tmp_path, "clone", "-q", str(origin), str(work))
    (work / "insights" / "later.md").write_text("# later\n")
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "later")
    git(work, "push", "-q", "origin", "main")
    moved = git(work, "rev-parse", "main")

    kapso.update_experience()
    out = capsys.readouterr().out
    assert git(home, "rev-parse", "main") == ahead
    assert f"mine: now at {ahead[:12]}" in out
    assert f"{reference}: now at {moved[:12]} (was {first[:12]})" in out
    # the clone sits at the new head; loading pins it there
    assert kapso.load_experience(reference).head == moved
    kapso.update_experience("mine")
    assert f"mine: at {ahead[:12]}, up to date" in capsys.readouterr().out


def test_a_pinned_commit_never_moves_and_what_is_read_in_place_has_nothing_to_update(tmp_path, capsys):
    kapso = _kapso(tmp_path)
    origin = bank_home(tmp_path, name="acme-bank.git", cards=1)
    head = git(origin, "rev-parse", "main")
    reference = f"git+file://{origin}@{head}"
    kapso.load_experience(reference)
    kapso.update_experience(reference)
    assert f"{reference}: at {head[:12]}: a tag or a commit never moves" in capsys.readouterr().out
    bank_home(tmp_path, cards=0)
    kapso.update_experience("mine")
    assert "mine: no remote (`kapso experience share <url>`)" in capsys.readouterr().out
    with pytest.raises(ExperienceError, match="has nothing to update"):
        kapso.update_experience(str(origin))


def test_remove_deletes_a_fetched_bank_or_an_index_and_refuses_the_rest(tmp_path, monkeypatch, capsys):
    kapso = _kapso(tmp_path)
    origin, reference = _fetched_bank(tmp_path, kapso)
    settings = settings_for(tmp_path)
    store = ExperienceStore(settings["banks"], settings["indexes"])
    [bank] = store.banks()
    kapso.remove_experience(reference)
    assert f"removed {bank['path']}" in capsys.readouterr().out
    assert store.banks() == [] and not Path(bank["path"]).exists() and kapso.experience == []
    with pytest.raises(ExperienceReferenceError, match="was never fetched; nothing to remove"):
        kapso.remove_experience(reference)

    store.write_index_record(IndexRecord(
        name="org-x", id="3f9a0c1d2e4b", created_at="2026-10-25T12:00:00+00:00", source="https://github.com/org/x",
        search_backend="kg_graph_search", backend_refs={"weaviate_collection": "KapsoOrgX3f9a0c1d2e4b", "corpus": "3f9a0c1d2e4b"},
        page_count=3, path=store.index_dir("org-x"),
    ))
    cleared = []
    search = SimpleNamespace(clear=lambda: cleared.append("clear"), close=lambda: cleared.append("close"))
    monkeypatch.setattr("kapso.kapso.search_for", lambda record, config, config_path: search)
    kapso.load_experience("org-x")
    kapso.remove_experience("org-x")
    assert cleared == ["clear", "close"] and not store.index_dir("org-x").exists() and kapso.experience == []
    assert "index 3f9a0c1d2e4b; its collection and corpus cleared" in capsys.readouterr().out

    bank_home(tmp_path, cards=0)
    with pytest.raises(ExperienceError, match="your bank is yours"):
        kapso.remove_experience("mine")
    with pytest.raises(ExperienceError, match="a bank by path is read in place"):
        kapso.remove_experience(str(origin))
